"""AI-drafted translations of a broadcast, through the translation job queue.

Prod holds no Anthropic credentials, and the worker sessions that translate can
reach GitHub but not this API (see ``library/admin_views/jobs.py``). So an
email translation travels the way book translations do — as a GitHub issue —
except that a broadcast lives only in this database, not in the repo, so the
draft comes BACK through GitHub too:

1. **request** — the admin presses "Draft <language> with AI". We file an issue
   ``[translation] email:broadcast-<id> -> <lang>`` (label ``translation-job``)
   whose body carries the source language's subject and blocks as JSON.
2. A worker session (``pq``; email jobs go first — they're small and someone is
   waiting) translates the words with ``manage.py translate_email_job`` and posts
   the result as a comment carrying :data:`MARKER`, then closes the issue.
3. **fetch** — the admin presses "Check for the draft". We read the issue's
   comments, validate the reply against the source (same blocks, same works,
   same links — only the words may change) and store it as that language's
   content, marked ``draft``.
4. **approve** — the admin reads it (and edits it if they like) and approves.
   A draft is never approved automatically, and a broadcast with an unapproved
   draft cannot be sent (emails/preflight.py). The review state is admin-only.

State per language lives in ``Broadcast.translations``:
``{lang: {"state", "issue", "url", "source_locale", "source_digest", "at"}}``.
"""

from __future__ import annotations

import hashlib
import json
import re

import requests
from django.conf import settings
from django.utils import timezone

from . import blocks as blocks_mod
from .rendering import sendable_locales

REQUESTED = "requested"
DRAFT = "draft"
APPROVED = "approved"

#: The line a worker's reply comment starts with — what fetch looks for.
MARKER = "<!-- ochorus:email-translation -->"

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


class TranslationJobError(ValueError):
    """Why a translation step can't go ahead — shown to the admin as is."""


def job_title(broadcast_id: int, language: str) -> str:
    return f"[translation] email:broadcast-{broadcast_id} -> {language}"


def locale_digest(broadcast, locale: str) -> str:
    """A hash of one language's subject and content — what a draft was made from."""
    payload = json.dumps(
        [broadcast.subject.get(locale, ""), broadcast.content.get(locale, {})],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def source_payload(broadcast, source: str, target: str) -> dict:
    """What the worker needs: the source language's words and layout."""
    content = broadcast.content.get(source) or {}
    return {
        "type": "email",
        "broadcast": broadcast.pk,
        "source_locale": source,
        "target": target,
        "source_digest": locale_digest(broadcast, source),
        "subject": broadcast.subject.get(source, ""),
        "preheader": content.get("preheader", ""),
        "blocks": blocks_mod.blocks_for(content),
    }


def _issue_body(payload: dict) -> str:
    from library.languages import entry as language_entry

    target = language_entry(payload["target"])["name"]
    return f"""An admin asked for an AI draft of a broadcast email in **{target}**.

Translate the subject, the preheader, and every block's `text`, `label` and
`attribution` into {target}, with the language's glossary and register rules
(`library.translation.system_prompt`). Keep every block in order with the same
`type`, `slug` and `path` — library cards render each reader's own edition, and
links are rewritten per language by the server, so neither is yours to change.

Run `manage.py translate_email_job <file with the JSON below>`, post its output
as a comment on this issue exactly as printed (it starts with `{MARKER}`), and
close the issue. The admin pulls the draft into the email and approves it there.

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```
"""


def _api(path: str) -> str:
    from library.admin_views.jobs import GITHUB_API

    return f"{GITHUB_API}/repos/{settings.GITHUB_TRANSLATION_REPO}{path}"


def _headers() -> dict:
    from library.admin_views.jobs import _headers as job_headers

    return job_headers()


def _require_github() -> None:
    if not settings.GITHUB_TRANSLATION_TOKEN:
        raise TranslationJobError(
            "The translation queue isn't configured — set GITHUB_TRANSLATION_TOKEN "
            "in the API environment."
        )


def request(broadcast, source: str, target: str, *, actor: str = "") -> dict:
    """File (or return the already-open) translation job for ``target``."""
    from library.admin_views.jobs import LABEL
    from library.languages import known_codes

    if broadcast.is_locked:
        raise TranslationJobError("A broadcast that has started sending can't be translated.")
    if target == source or target not in known_codes():
        raise TranslationJobError("Choose a known language other than the source.")
    if source not in sendable_locales(broadcast):
        raise TranslationJobError("The source language needs a subject and content first.")
    current = (broadcast.translations or {}).get(target) or {}
    if current.get("state") == REQUESTED:
        return current  # one open job per language: pressing again doesn't re-file
    _require_github()

    payload = source_payload(broadcast, source, target)
    r = requests.post(
        _api("/issues"),
        headers=_headers(),
        json={
            "title": job_title(broadcast.pk, target),
            "body": _issue_body(payload),
            "labels": [LABEL],
        },
        timeout=15,
    )
    r.raise_for_status()
    issue = r.json()
    entry = {
        "state": REQUESTED,
        "issue": issue.get("number"),
        "url": issue.get("html_url", ""),
        "source_locale": source,
        "source_digest": payload["source_digest"],
        "requested_by": actor,
        "at": timezone.now().isoformat(),
    }
    _save_entry(broadcast, target, entry)
    return entry


def _save_entry(broadcast, target: str, entry: dict) -> None:
    translations = dict(broadcast.translations or {})
    translations[target] = entry
    broadcast.translations = translations
    broadcast.save(update_fields=["translations", "updated_at"])


def _reply(issue_number: int) -> dict | None:
    """The worker's reply on the issue — the newest marked comment — or None."""
    r = requests.get(
        _api(f"/issues/{issue_number}/comments"),
        headers=_headers(),
        params={"per_page": 100},
        timeout=15,
    )
    r.raise_for_status()
    for comment in reversed(r.json()):
        body = comment.get("body") or ""
        if MARKER not in body:
            continue
        match = _JSON_BLOCK.search(body)
        if not match:
            continue
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
    return None


def validate_draft(source_blocks: list[dict], draft: dict) -> dict:
    """The draft as ``{subject, preheader, blocks}``, or :class:`TranslationJobError`.

    A draft may change WORDS only: the same blocks in the same order, with the
    same works and links. Anything else is refused rather than half-applied.
    """
    blocks = blocks_mod.clean(draft.get("blocks"))
    if len(blocks) != len(source_blocks):
        raise TranslationJobError("The draft has a different number of blocks from the source.")
    for i, (src, new) in enumerate(zip(source_blocks, blocks, strict=True)):
        if src["type"] != new["type"]:
            raise TranslationJobError(f"Block {i + 1} changed type in the draft.")
        for field in blocks_mod.FIELDS[src["type"]]:
            if field not in blocks_mod.WORD_FIELDS and src.get(field, "") != new.get(field, ""):
                raise TranslationJobError(f"Block {i + 1}'s {field} changed in the draft.")
    subject = str(draft.get("subject") or "").strip()[:300]
    if not subject:
        raise TranslationJobError("The draft has no subject line.")
    return {
        "subject": subject,
        "preheader": str(draft.get("preheader") or "").strip()[:300],
        "blocks": blocks,
    }


def fetch(broadcast, target: str) -> dict:
    """Pull the worker's draft for ``target`` into the broadcast, if it's back.

    Returns the language's state entry. Leaves it ``requested`` when no reply is
    there yet."""
    entry = (broadcast.translations or {}).get(target) or {}
    if entry.get("state") != REQUESTED:
        raise TranslationJobError("There is no requested translation to check for.")
    if broadcast.is_locked:
        raise TranslationJobError("A broadcast that has started sending can't be changed.")
    _require_github()
    reply = _reply(entry["issue"])
    if reply is None:
        return entry
    if reply.get("broadcast") != broadcast.pk or reply.get("target") != target:
        raise TranslationJobError("The reply on the issue is for a different email or language.")
    source = entry["source_locale"]
    draft = validate_draft(
        blocks_mod.blocks_for(broadcast.content.get(source) or {}), reply
    )
    broadcast.subject = {**broadcast.subject, target: draft["subject"]}
    broadcast.content = {
        **broadcast.content,
        target: {"preheader": draft["preheader"], "blocks": draft["blocks"]},
    }
    entry = {**entry, "state": DRAFT, "drafted_at": timezone.now().isoformat()}
    translations = dict(broadcast.translations or {})
    translations[target] = entry
    broadcast.translations = translations
    broadcast.save(update_fields=["subject", "content", "translations", "updated_at"])
    return entry


def approve(broadcast, target: str, *, actor: str = "") -> dict:
    """Mark ``target``'s AI draft reviewed. Only an admin's press does this."""
    entry = (broadcast.translations or {}).get(target) or {}
    if entry.get("state") != DRAFT:
        raise TranslationJobError("Only an AI draft waiting for review can be approved.")
    entry = {
        **entry,
        "state": APPROVED,
        "approved_by": actor,
        "approved_at": timezone.now().isoformat(),
    }
    _save_entry(broadcast, target, entry)
    return entry


def is_stale(broadcast, target: str) -> bool:
    """Whether the source language changed after ``target``'s draft was asked for."""
    entry = (broadcast.translations or {}).get(target) or {}
    source = entry.get("source_locale")
    return bool(source) and entry.get("source_digest") != locale_digest(broadcast, source)
