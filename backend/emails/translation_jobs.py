"""AI-drafted translations of a broadcast, through the translation job queue.

Prod holds no Anthropic credentials, and the worker sessions that translate can
reach GitHub but not this API (see ``library/admin_views/jobs.py``). So an
email translation travels the way book translations do — as a GitHub issue —
except that a broadcast lives only in this database, not in the repo, so the
draft comes BACK through GitHub too:

1. **request** — the admin presses "Draft <language> with AI". We file an issue
   ``[translation] email:broadcast-<id> -> <lang>`` (label ``translation-job``)
   whose body carries the source language's WORDS only — subject, preheader and
   each block's text, in order — never the layout.
2. A worker session (``pq``; email jobs go first — they're small and someone is
   waiting) translates them, formats the answer with ``manage.py
   translate_email_job``, posts it as a comment carrying :data:`MARKER`, and
   closes the issue.
3. **fetch** — the admin presses "Check for the draft". We read the comments and
   put the translated words back into the source's OWN blocks, so a reply can
   change words and nothing else (no works, links or block order). A reply made
   from an older version of the source is refused.
4. **approve** — the admin reads it (and edits it if they like) and approves.
   A draft is never approved automatically, and a broadcast with an unapproved
   draft cannot be sent (emails/preflight.py). The review state is admin-only.

Email jobs share the queue's label and title shape but not its dashboard: the
dashboard's queue (``jobs._TITLE_RE``) lists library content only, and an email
job is tracked on its broadcast instead.

State per language lives in ``Broadcast.translations``:
``{lang: {"state", "issue", "url", "source_locale", "source_digest", "approved_by"}}``.
"""

from __future__ import annotations

import hashlib
import json
import re

import requests
from django.conf import settings
from django.db import models

from library.admin_views.jobs import GITHUB_API, _headers, _job_title, file_issue
from library.languages import entry as language_entry
from library.languages import known_codes

from . import blocks as blocks_mod
from .rendering import sendable_locales


class State(models.TextChoices):
    REQUESTED = "requested", "Requested"
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"


#: The line a worker's reply comment starts with — what fetch looks for.
MARKER = "<!-- ochorus:email-translation -->"

#: The JSON block in an issue body or a reply comment.
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

#: How an email is translated — in every issue, so each worker follows the same rules.
INSTRUCTIONS = (
    "This is not a chapter: it is a short email from Ochorus to its readers. "
    "Translate its `subject`, its inbox `preheader` and each string in `texts`, "
    "keeping the strings in the same order and the same count, with the target "
    "language's glossary and register rules (`library.translation.system_prompt`). "
    "Keep `{name}` exactly as written (it becomes the reader's first name). Keep "
    "each string about the length of its source; a subject line must stay short. "
    "Book and sermon titles inside the text take their published title in the "
    "target language where one exists."
)


class TranslationJobError(ValueError):
    """Why a translation step can't go ahead — shown to the admin as is."""


def _entry(broadcast, target: str) -> dict:
    return (broadcast.translations or {}).get(target) or {}


def locale_digest(broadcast, locale: str) -> str:
    """A hash of one language's subject and content — what a draft was made from."""
    payload = json.dumps(
        [broadcast.subject.get(locale, ""), broadcast.content.get(locale, {})],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _slots(blocks: list[dict]) -> list[tuple[int, str]]:
    """``(block index, field)`` for every piece of the admin's own words."""
    return [
        (i, field)
        for i, block in enumerate(blocks)
        for field in blocks_mod.FIELDS[block["type"]]
        if field in blocks_mod.WORD_FIELDS and block.get(field)
    ]


def _source_blocks(broadcast, source: str) -> list[dict]:
    return blocks_mod.blocks_for(broadcast.content.get(source) or {})


def job_payload(broadcast, source: str, target: str) -> dict:
    """What the worker translates: the source language's words, in block order."""
    blocks = _source_blocks(broadcast, source)
    return {
        "type": "email",
        "broadcast": broadcast.pk,
        "source_locale": source,
        "target": target,
        "source_digest": locale_digest(broadcast, source),
        "subject": broadcast.subject.get(source, ""),
        "preheader": (broadcast.content.get(source) or {}).get("preheader", ""),
        "texts": [blocks[i][field] for i, field in _slots(blocks)],
    }


def _issue_body(payload: dict) -> str:
    target = language_entry(payload["target"])["name"]
    return f"""An admin asked for an AI draft of a broadcast email in **{target}**.

{INSTRUCTIONS}

Write your answer as `{{"subject", "preheader", "texts": [...]}}` in a file, run
`manage.py translate_email_job <this issue's body in a file> --answer <your file>`,
post its output as a comment on this issue exactly as printed (it starts with
`{MARKER}`), and close the issue. The admin pulls the draft into the email and
approves it there.

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```
"""


def check_answer(payload: dict, answer: dict) -> dict:
    """A translator's answer as the reply to post, or :class:`TranslationJobError`.
    Run by the worker before posting and again by :func:`fetch` on what comes back."""
    texts = answer.get("texts")
    if not isinstance(texts, list) or len(texts) != len(payload["texts"]):
        got = len(texts) if isinstance(texts, list) else 0
        raise TranslationJobError(
            f"The draft has {got} translated strings; the source has {len(payload['texts'])}."
        )
    subject = str(answer.get("subject") or "").strip()[:300]
    if not subject:
        raise TranslationJobError("The draft has no subject line.")
    return {
        "broadcast": payload["broadcast"],
        "target": payload["target"],
        "source_digest": payload["source_digest"],
        "subject": subject,
        "preheader": str(answer.get("preheader") or "").strip()[:300],
        "texts": [str(t).strip()[: blocks_mod.MAX_TEXT] for t in texts],
    }


def reply_comment(reply: dict) -> str:
    """The issue comment a worker posts — what :func:`fetch` reads."""
    return (
        f"{MARKER}\nAI draft for review in the admin.\n\n```json\n"
        f"{json.dumps(reply, ensure_ascii=False, indent=2)}\n```\n"
    )


def _require_github() -> None:
    if not settings.GITHUB_TRANSLATION_TOKEN:
        raise TranslationJobError(
            "The translation queue isn't configured — set GITHUB_TRANSLATION_TOKEN "
            "in the API environment."
        )


def _save_entry(broadcast, target: str, entry: dict, *fields: str) -> None:
    broadcast.translations = {**(broadcast.translations or {}), target: entry}
    broadcast.save(update_fields=[*fields, "translations", "updated_at"])


def request(broadcast, source: str, target: str) -> dict:
    """File (or return the already-open) translation job for ``target``."""
    if broadcast.is_locked:
        raise TranslationJobError("A broadcast that has started sending can't be translated.")
    if target == source or target not in known_codes():
        raise TranslationJobError("Choose a known language other than the source.")
    if source not in sendable_locales(broadcast):
        raise TranslationJobError("The source language needs a subject and content first.")
    payload = job_payload(broadcast, source, target)
    current = _entry(broadcast, target)
    if current.get("state") == State.REQUESTED and current.get("source_digest") == payload["source_digest"]:
        return current  # one open job per language and source: pressing again doesn't re-file
    _require_github()

    issue = file_issue(_job_title("email", f"broadcast-{broadcast.pk}", target), _issue_body(payload))
    entry = {
        "state": State.REQUESTED,
        "issue": issue.get("number"),
        "url": issue.get("html_url", ""),
        "source_locale": source,
        "source_digest": payload["source_digest"],
    }
    _save_entry(broadcast, target, entry)
    return entry


def _replies(issue_number: int):
    """Every marked JSON reply on the issue, newest first."""
    url = f"{GITHUB_API}/repos/{settings.GITHUB_TRANSLATION_REPO}/issues/{issue_number}/comments"
    comments: list[dict] = []
    for page in range(1, 11):
        r = requests.get(url, headers=_headers(), params={"per_page": 100, "page": page}, timeout=15)
        r.raise_for_status()
        batch = r.json()
        comments.extend(batch)
        if len(batch) < 100:
            break
    for comment in reversed(comments):
        body = comment.get("body") or ""
        match = JSON_BLOCK.search(body) if MARKER in body else None
        if match:
            try:
                yield json.loads(match.group(1))
            except json.JSONDecodeError:
                continue


def fetch(broadcast, target: str) -> dict:
    """Pull the worker's draft for ``target`` into the broadcast, if it's back.

    Returns the language's state entry, left ``requested`` when no reply is
    there yet. The translated words go into the source's own blocks."""
    entry = _entry(broadcast, target)
    if entry.get("state") != State.REQUESTED:
        raise TranslationJobError("There is no requested translation to check for.")
    if broadcast.is_locked:
        raise TranslationJobError("A broadcast that has started sending can't be changed.")
    _require_github()
    reply = next(_replies(entry["issue"]), None)
    if reply is None:
        return entry
    if reply.get("broadcast") != broadcast.pk or reply.get("target") != target:
        raise TranslationJobError("The reply on the issue is for a different email or language.")
    source = entry["source_locale"]
    payload = job_payload(broadcast, source, target)
    if reply.get("source_digest") != payload["source_digest"]:
        raise TranslationJobError(
            "The source text changed after this draft was asked for — ask for a new draft."
        )
    draft = check_answer(payload, reply)
    blocks = _source_blocks(broadcast, source)
    for (i, field), text in zip(_slots(blocks), draft["texts"], strict=True):
        blocks[i][field] = text
    broadcast.subject = {**broadcast.subject, target: draft["subject"]}
    broadcast.content = {
        **broadcast.content,
        target: {"preheader": draft["preheader"], "blocks": blocks},
    }
    entry = {**entry, "state": State.DRAFT}
    _save_entry(broadcast, target, entry, "subject", "content")
    return entry


def approve(broadcast, target: str, *, actor: str = "") -> dict:
    """Mark ``target``'s AI draft reviewed. Only an admin's press does this."""
    entry = _entry(broadcast, target)
    if entry.get("state") != State.DRAFT:
        raise TranslationJobError("Only an AI draft waiting for review can be approved.")
    entry = {**entry, "state": State.APPROVED, "approved_by": actor}
    _save_entry(broadcast, target, entry)
    return entry


def states(broadcast) -> dict[str, dict]:
    """Every language's entry, with ``stale``: whether its source changed after
    the draft was asked for. Each source language is hashed once."""
    digests: dict[str, str] = {}
    out = {}
    for lang, entry in (broadcast.translations or {}).items():
        source = entry.get("source_locale", "")
        if source not in digests:
            digests[source] = locale_digest(broadcast, source)
        out[lang] = {**entry, "stale": entry.get("source_digest") != digests[source]}
    return out
