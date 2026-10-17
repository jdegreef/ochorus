"""Editable automated emails: the onboarding drip, the series nudge, milestones
and plan reminders, edited in the designer instead of in code.

The words in ``emails/copy.py`` stay the **original** — every language's
starting point and its fallback. An edit lives in a :class:`LifecycleCopy` row:
a working copy the admin saves freely, and a **live** copy that is what readers
get, set only by :func:`publish`. A language with no live copy keeps sending the
original, so editing the English doesn't touch the Spanish until a Spanish
version is published too; meanwhile the Spanish is shown as needing review.

Some emails fill in words per reader — ``{next}`` (the next volume),
``{plan}``, ``{day}``, ``{count}``… — listed per step in :data:`STEPS`, and the
three whose button goes somewhere chosen per reader (the next volume, today's
reading) mark that button's link as ``{link}``. Both work in an edited email
exactly as in the original, and the merge tags (``{first_name}`` and the rest)
work too.
"""

from __future__ import annotations

import copy as copylib
import hashlib
import json
import time
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from . import blocks as blocks_mod
from . import copy as copy_mod
from . import merge_tags, translation_jobs
from .models import LifecycleCopy, LifecycleCopyVersion
from .streams import STEP_STREAM

#: The button link an email fills per reader.
LINK = "{link}"


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    when: str
    placeholders: dict[str, str] = field(default_factory=dict)
    #: Whether its button goes somewhere chosen per reader (``{link}``).
    link: str = ""


#: The automated emails an admin can edit, in the order a reader meets them.
STEPS: list[Step] = [
    Step("welcome", "Welcome", "Right after sign-up"),
    Step("pick_plan", "Pick a plan", "Day 2, if they haven’t started a reading plan"),
    Step("finish_first_book", "Finish your first book", "Day 3, if they opened a book but finished none"),
    Step("classic", "A classic worth your time", "Day 4"),
    Step("comeback", "Come back", "Seen before, then quiet for 7 days"),
    Step("winback", "Win back", "Quiet for 30 days"),
    Step(
        "finish_series",
        "Continue the series",
        "When they finish a book in a series",
        {"finished": "the book they finished", "next": "the next volume"},
        link="the next volume",
    ),
    Step("milestone", "Reading milestone", "When they finish 1, 5, 10, 25… books", {"count": "how many books"}),
    Step(
        "plan_reminder",
        "Reading-plan reminder",
        "Each day of a plan they started, at their chosen time",
        {"plan": "the plan", "day": "today’s day", "total": "the plan’s days", "reading": "today’s reading"},
        link="today’s reading",
    ),
    Step(
        "plan_paused",
        "Reading-plan paused",
        "When they fall behind and reminders pause",
        {"plan": "the plan", "day": "the day they stopped at"},
        link="the day they stopped at",
    ),
]
STEP_BY_KEY = {s.key: s for s in STEPS}


class CopyError(ValueError):
    """Why an edit can't be published, worded for the admin."""


def stream_of(step: str) -> str:
    return STEP_STREAM.get(step, "onboarding")


# --- The original ------------------------------------------------------------------


def original(step: str, lang: str) -> dict | None:
    """The code's words for ``step`` in ``lang`` as an editable email —
    ``{"subject", "preheader", "blocks"}`` — or ``None`` if it has none."""
    text = copy_mod.LIFECYCLE[step].get(lang)
    if text is None:
        return None
    blocks = blocks_mod.legacy_blocks(text)
    if STEP_BY_KEY[step].link:
        for b in blocks:
            if b["type"] == blocks_mod.BlockType.BUTTON:
                b["path"] = LINK
    return {"subject": str(text["subject"]), "preheader": str(text.get("preheader", "")), "blocks": blocks_mod.clean(blocks)}


def languages(step: str) -> list[str]:
    """The languages ``step`` has words in (English first)."""
    codes = list(copy_mod.LIFECYCLE[step])
    return sorted(codes, key=lambda c: (c != "en", c))


def _email(subject: str, content: dict | None) -> dict:
    content = content or {}
    return {
        "subject": subject or "",
        "preheader": str(content.get("preheader", "")),
        "blocks": blocks_mod.blocks_for(content),
    }


def digest(email: dict | None) -> str:
    if not email:
        return ""
    payload = json.dumps([email.get("subject"), email.get("preheader"), email.get("blocks")], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# --- The working copy -------------------------------------------------------------------


def row(step: str) -> LifecycleCopy:
    """The step's row, unsaved and filled with the originals if never edited."""
    if step not in STEP_BY_KEY:
        raise CopyError(f"unknown email {step!r}")
    found = LifecycleCopy.objects.filter(step=step).first()
    if found is not None:
        return found
    fresh = LifecycleCopy(step=step)
    for lang in languages(step):
        email = original(step, lang)
        fresh.subject[lang] = email["subject"]
        fresh.content[lang] = {"preheader": email["preheader"], "blocks": email["blocks"]}
    return fresh


def working(copy: LifecycleCopy, lang: str) -> dict | None:
    if lang not in copy.content and lang not in copy.subject:
        return None
    return _email(copy.subject.get(lang, ""), copy.content.get(lang))


def save_working(step: str, subject: dict, content: dict, actor: str = "") -> LifecycleCopy:
    """Save the working copy (nothing a reader sees changes)."""
    copy = row(step)
    cleaned = blocks_mod.clean_content(content if isinstance(content, dict) else {})
    for lang, value in (subject or {}).items():
        if lang in cleaned or lang in copy.content:
            copy.subject[str(lang)[:10]] = str(value)[:300]
    for lang, value in cleaned.items():
        copy.content[lang] = {"preheader": str(value.get("preheader", ""))[:300], "blocks": value.get("blocks", [])}
    copy.updated_by = actor[:254]
    copy.save()
    _forget(step)
    return copy


# --- Where each language stands ---------------------------------------------------------


def statuses(copy: LifecycleCopy) -> dict[str, dict]:
    """``{lang: {"status", "stale", "published_at", "published_by"}}``.

    ``status`` is ``requested`` / ``draft`` (an AI draft not back / not
    reviewed), ``edited`` (saved, not published), ``published`` or ``original``.
    ``stale``: the English was published changed after this language was last
    published (or, never edited, at all) — it needs a look."""
    ai = translation_jobs.states(copy)
    en_live = digest(copy.live.get("en")) or digest(original(copy.step, "en"))
    out = {}
    for lang in sorted({*languages(copy.step), *copy.content}, key=lambda c: (c != "en", c)):
        live = copy.live.get(lang)
        current = working(copy, lang)
        state = ai.get(lang, {}).get("state")
        if state in (translation_jobs.State.REQUESTED, translation_jobs.State.DRAFT):
            status = state
        elif live is not None:
            status = "published" if digest(live) == digest(current) else "edited"
        else:
            status = "original" if digest(current) == digest(original(copy.step, lang)) else "edited"
        stale = False
        if lang != "en":
            if live is not None:
                stale = live.get("en_digest") != en_live
            else:
                stale = "en" in copy.live
        out[lang] = {
            "status": status,
            "stale": stale,
            "published_at": live.get("published_at") if live else None,
            "published_by": live.get("published_by", "") if live else "",
        }
    return out


# --- Publishing ---------------------------------------------------------------------


def _allowed_braces(step: str) -> set[str]:
    return {*merge_tags.TAGS, *merge_tags.ALIASES, *STEP_BY_KEY[step].placeholders, "link", "chapter"}


def check(step: str, lang: str, email: dict) -> list[str]:
    """What stops ``email`` going out, in words — empty when it can."""
    problems = []
    if not email["subject"].strip():
        problems.append("the subject line is empty")
    if not blocks_mod.has_body(email["blocks"]):
        problems.append("the email has no content")
    texts = [email["subject"], email["preheader"], *(b.get(f, "") for b in email["blocks"] for f in blocks_mod.WORD_FIELDS)]
    unknown = sorted(
        m.group(0) for t in texts for m in merge_tags.TAG.finditer(t or "") if m.group(1) not in _allowed_braces(step)
    )
    if unknown:
        problems.append(f"{', '.join(unknown)} isn't something this email can fill in")
    return problems


def publish(step: str, langs: list[str] | None = None, actor: str = "") -> LifecycleCopy:
    """Make the working copy what readers get, for ``langs`` (every language
    with unpublished changes when ``None``). Refuses an unapproved AI draft or a
    language whose email couldn't go out; keeps the version."""
    copy = row(step)
    if copy._state.adding:
        raise CopyError("There are no changes to publish.")
    current = statuses(copy)
    if langs is None:
        langs = [lang for lang, s in current.items() if s["status"] == "edited"]
    if not langs:
        raise CopyError("There are no changes to publish.")
    problems = []
    emails = {}
    for lang in langs:
        state = current.get(lang, {}).get("status")
        if state in (translation_jobs.State.REQUESTED, translation_jobs.State.DRAFT):
            problems.append(f"{lang}: the AI draft hasn't been approved")
            continue
        email = working(copy, lang)
        if email is None:
            problems.append(f"{lang}: there is nothing to publish")
            continue
        problems += [f"{lang}: {p}" for p in check(step, lang, email)]
        emails[lang] = email
    if problems:
        raise CopyError("; ".join(problems))
    now = timezone.now().isoformat()
    en_after = digest(emails.get("en") or copy.live.get("en") or original(step, "en"))
    with transaction.atomic():
        for lang, email in emails.items():
            copy.live[lang] = {**email, "published_at": now, "published_by": actor, "en_digest": en_after}
        copy.updated_by = actor[:254]
        copy.save()
        LifecycleCopyVersion.objects.create(copy=copy, live=copylib.deepcopy(copy.live), languages=sorted(emails), published_by=actor)
    _forget(step)
    return copy


def reset(step: str, lang: str | None = None, actor: str = "") -> LifecycleCopy:
    """Go back to the code's words — for one language, or the whole email (the
    version history is kept)."""
    copy = row(step)
    if copy._state.adding:
        return copy
    langs = [lang] if lang else list({*copy.content, *copy.subject, *copy.live, *copy.translations})
    with transaction.atomic():
        for code in langs:
            copy.live.pop(code, None)
            copy.translations.pop(code, None)
            email = original(step, code)
            if email is None:
                copy.subject.pop(code, None)
                copy.content.pop(code, None)
            else:
                copy.subject[code] = email["subject"]
                copy.content[code] = {"preheader": email["preheader"], "blocks": email["blocks"]}
        copy.updated_by = actor[:254]
        copy.save()
        LifecycleCopyVersion.objects.create(copy=copy, live=copylib.deepcopy(copy.live), languages=[f"reset:{c}" for c in sorted(langs)], published_by=actor)
    _forget(step)
    return copy


def restore(step: str, version_id: int, actor: str = "") -> LifecycleCopy:
    """Put an earlier version's words back into the working copy (publish to send)."""
    copy = row(step)
    version = LifecycleCopyVersion.objects.filter(copy__step=step, pk=version_id).first()
    if version is None:
        raise CopyError("That version doesn't exist.")
    for lang, email in version.live.items():
        copy.subject[lang] = email["subject"]
        copy.content[lang] = {"preheader": email["preheader"], "blocks": email["blocks"]}
    copy.updated_by = actor[:254]
    copy.save()
    return copy


# --- What readers get ---------------------------------------------------------------

#: Per-process memo of each step's live copies: a sweep renders the same step
#: for many readers, and a minute's lag after a publish is harmless.
_LIVE: dict[str, tuple[float, dict]] = {}
_LIVE_TTL = 60.0


def _forget(step: str) -> None:
    _LIVE.pop(step, None)


def live_email(step: str, lang: str) -> dict | None:
    """The published edit of ``step`` in ``lang``, or ``None`` (send the original)."""
    cached = _LIVE.get(step)
    if cached is None or time.monotonic() - cached[0] > _LIVE_TTL:
        live = LifecycleCopy.objects.filter(step=step).values_list("live", flat=True).first() or {}
        cached = (time.monotonic(), live)
        _LIVE[step] = cached
    email = cached[1].get(lang)
    return copylib.deepcopy(email) if email else None
