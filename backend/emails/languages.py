"""One email, every language: where each language of a broadcast stands.

The admin writes once (usually in English), asks for AI drafts of the rest in
one go, reads each draft beside its source, and approves it — the same
translate-then-review rule as the library. What this module adds over
:mod:`emails.translation_jobs` (one language at a time) is the whole picture:

* :func:`overview` — every language the site is live in, plus any the email is
  already written in: its state, how many readers in the audience get their
  email in it, and which of the email's books, sermons, plans… have no edition
  in it (those blocks are left out of that language's email).
* :func:`request_all` / :func:`fetch_all` — ask for every missing language, or
  check every outstanding request, at once.

The review state is admin-only, like the library's: never shown to readers.
"""

from __future__ import annotations

import requests

from library.languages import entry as language_entry
from library.languages import live_codes

from . import blocks as blocks_mod
from . import translation_jobs
from .audience import by_email_language
from .rendering import sendable_locales


class Status:
    SOURCE = "source"  # the language the email was written in
    APPROVED = "approved"  # an AI draft an admin approved
    DRAFT = "draft"  # an AI draft waiting for review
    REQUESTED = "requested"  # asked for, not back yet
    WRITTEN = "written"  # written by hand (no AI draft)
    INCOMPLETE = "incomplete"  # a subject or content, but not both
    MISSING = "missing"  # nothing yet


def source_locale(broadcast) -> str | None:
    """The language the others are translated from: English when the email is
    written in it, else the first complete language."""
    locales = sendable_locales(broadcast)
    if "en" in locales:
        return "en"
    return locales[0] if locales else None


def _status(code: str, broadcast, source: str | None, states: dict) -> str:
    if code == source:
        return Status.SOURCE
    entry = states.get(code)
    if entry and entry["state"] in (Status.APPROVED, Status.DRAFT, Status.REQUESTED):
        return entry["state"]
    if code in sendable_locales(broadcast):
        return Status.WRITTEN
    if code in broadcast.subject or code in broadcast.content:
        return Status.INCOMPLETE
    return Status.MISSING


def _gaps(blocks: list[dict], library: dict, code: str) -> list[dict]:
    """The library items in ``blocks`` with no edition in ``code``."""
    gaps = []
    for kind, slugs in blocks_mod.library_refs(blocks).items():
        for slug in sorted(slugs):
            if code not in library.get(kind, {}).get(slug, set()):
                gaps.append({"type": kind, "slug": slug})
    return gaps


def overview(broadcast) -> dict:
    """Every language's row for the Languages panel."""
    source = source_locale(broadcast)
    states = translation_jobs.states(broadcast)
    readers = by_email_language(broadcast.audience)
    codes = list(live_codes())
    for code in [*broadcast.content, *broadcast.subject, *states]:
        if code not in codes:
            codes.append(code)

    source_blocks = blocks_mod.blocks_for(broadcast.content.get(source) or {}) if source else []
    wanted: dict[str, set[str]] = {}
    for code in codes:
        blocks = blocks_mod.blocks_for(broadcast.content.get(code) or {}) or source_blocks
        for kind, slugs in blocks_mod.library_refs(blocks).items():
            wanted.setdefault(kind, set()).update(slugs)
    library = {kind: blocks_mod.editions(kind, slugs) for kind, slugs in wanted.items()}

    rows = []
    for code in codes:
        entry = language_entry(code)
        status = _status(code, broadcast, source, states)
        blocks = blocks_mod.blocks_for(broadcast.content.get(code) or {}) or source_blocks
        rows.append(
            {
                "code": code,
                "name": entry.get("name") or code,
                "native_name": entry.get("native_name") or code,
                "status": status,
                "stale": bool(states.get(code, {}).get("stale")) and status != Status.REQUESTED,
                "issue_url": states.get(code, {}).get("url", ""),
                "approved_by": states.get(code, {}).get("approved_by", ""),
                "readers": readers.get(code, 0),
                "gaps": _gaps(blocks, library, code),
                "sendable": status in (Status.SOURCE, Status.APPROVED, Status.WRITTEN),
            }
        )
    return {
        "source": source,
        "strict_locale": broadcast.strict_locale,
        "rows": rows,
        "missing": [r["code"] for r in rows if r["status"] == Status.MISSING],
    }


def request_all(broadcast, source: str | None = None) -> dict[str, str]:
    """Ask for an AI draft of every missing live language. Returns
    ``{language: "requested" or why not}`` — one failure doesn't stop the rest."""
    source = source or source_locale(broadcast)
    if source is None:
        raise translation_jobs.TranslationJobError("Write the email in one language first.")
    outcome: dict[str, str] = {}
    for code in overview(broadcast)["missing"]:
        try:
            translation_jobs.request(broadcast, source, code)
            outcome[code] = Status.REQUESTED
        except translation_jobs.TranslationJobError as exc:
            outcome[code] = str(exc)
        except requests.RequestException:
            outcome[code] = "GitHub didn't answer — try again shortly."
        broadcast.refresh_from_db()
    return outcome


def fetch_all(broadcast) -> dict[str, str]:
    """Check every outstanding request for its draft. ``{language: state or why not}``."""
    outcome: dict[str, str] = {}
    for code, entry in translation_jobs.states(broadcast).items():
        if entry.get("state") != Status.REQUESTED:
            continue
        try:
            outcome[code] = translation_jobs.fetch(broadcast, code)["state"]
        except translation_jobs.TranslationJobError as exc:
            outcome[code] = str(exc)
        except requests.RequestException:
            outcome[code] = "GitHub didn't answer — try again shortly."
        broadcast.refresh_from_db()
    return outcome
