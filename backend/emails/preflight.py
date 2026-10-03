"""Pre-send checks for a broadcast — the checklist the admin sees before sending.

Each check returns ``{"code", "level", "message"}``. ``level`` is ``"error"``
(blocks send and schedule), ``"warning"`` (shown, doesn't block) or ``"ok"`` (a
passed check, listed so the admin sees what was looked at, not only what
failed). The send and schedule actions refuse a broadcast with any error, so a
campaign with an empty subject line or a broken button link can't go out.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Count, F, Value
from django.db.models.functions import Coalesce, NullIf

from library.languages import entry as language_entry

from . import blocks as blocks_mod
from . import copy as copy_mod
from . import health, translation_jobs
from .audience import resolve
from .rendering import resolve_broadcast_locale, sendable_locales
from .sending import emails_enabled

ERROR = "error"
WARNING = "warning"
OK = "ok"

#: Inboxes cut subject lines at roughly this many characters.
SUBJECT_SOFT_LIMIT = 90


def _check(code: str, level: str, message: str) -> dict:
    return {"code": code, "level": level, "message": message}


def _lang_name(code: str) -> str:
    return language_entry(code).get("name") or code


def cta_path_problem(path: str) -> str | None:
    """Why a button's link path won't work, or ``None``. Paths are joined onto
    the reader site's origin (emails/links.py), so a full URL or a space breaks."""
    path = (path or "").strip()
    if "://" in path or path.startswith("//"):
        return "is a full web address; use a path on the site, like books/humility-2"
    if any(c.isspace() for c in path):
        return "contains a space"
    return None


def _content_checks(broadcast) -> list[dict]:
    out = []
    locales = sendable_locales(broadcast)
    if not locales:
        return [
            _check(
                "content",
                ERROR,
                "No language has both a subject line and content yet.",
            )
        ]
    blocks_by_locale = {
        code: blocks_mod.blocks_for(broadcast.content.get(code) or {}) for code in locales
    }
    library = _library_editions(blocks_by_locale)
    for code, blocks in blocks_by_locale.items():
        name = _lang_name(code)
        subject = str(broadcast.subject.get(code) or "").strip()
        if not subject:
            out.append(_check(f"subject:{code}", ERROR, f"{name}: the subject line is empty."))
        elif len(subject) > SUBJECT_SOFT_LIMIT:
            out.append(
                _check(
                    f"subject:{code}",
                    WARNING,
                    f"{name}: the subject is {len(subject)} characters; inboxes cut it "
                    f"at about {SUBJECT_SOFT_LIMIT}.",
                )
            )
        def reaches(block, code=code):
            return code in library.get(block["type"], {}).get(block["slug"], set())

        if not blocks_mod.has_body(blocks, reaches):
            out.append(_check(f"body:{code}", ERROR, f"{name}: the email has no content yet."))
        for i, block in enumerate(blocks):
            out.extend(_block_checks(block, f"{code}:{i}", name, code, library))
    out.extend(_untranslated_checks(blocks_by_locale))
    half = (set(broadcast.subject) ^ set(broadcast.content)) - set(locales)
    for code in sorted(half):
        out.append(
            _check(
                f"half:{code}",
                WARNING,
                f"{_lang_name(code)} has a subject or content but not both, so it won't be used.",
            )
        )
    if not out:
        out.append(
            _check(
                "content",
                OK,
                f"Subject and content are complete in {len(locales)} "
                f"language{'s' if len(locales) != 1 else ''}.",
            )
        )
    return out


def _words(blocks: list[dict]) -> set[str]:
    """The admin's own words in a block list, one entry per field — short ones
    (a name, "Amen") left out, since those are often the same in any language."""
    return {
        b[f].strip()
        for b in blocks
        for f in blocks_mod.WORD_FIELDS
        if len(b.get(f, "").strip()) >= 12
    }


def _untranslated_checks(blocks_by_locale: dict[str, list[dict]]) -> list[dict]:
    """Warn where a language repeats another language's words verbatim — what a
    layout copied with "add language" looks like until it is translated."""
    out = []
    words = {code: _words(blocks) for code, blocks in blocks_by_locale.items()}
    for code, mine in words.items():
        if code == "en" and len(words) > 1:
            continue  # English is where a copied layout comes from; flag the copies
        others = set().union(*(w for c, w in words.items() if c != code))
        same = len(mine & others)
        if same:
            out.append(
                _check(
                    f"untranslated:{code}",
                    WARNING,
                    f"{_lang_name(code)}: {same} piece{'s' if same != 1 else ''} of text "
                    "match another language word for word — not translated yet?",
                )
            )
    return out


def _library_editions(blocks_by_locale: dict[str, list[dict]]) -> dict[str, dict[str, set[str]]]:
    """``{kind: {slug: languages}}`` for every library block in the broadcast —
    one query per kind, shared by all its languages' checks."""
    wanted: dict[str, set[str]] = {}
    for blocks in blocks_by_locale.values():
        for kind, slugs in blocks_mod.library_refs(blocks).items():
            wanted.setdefault(kind, set()).update(slugs)
    return {kind: blocks_mod.editions(kind, slugs) for kind, slugs in wanted.items()}


def _block_checks(block: dict, key: str, name: str, code: str, library) -> list[dict]:
    """Problems with one block of one language's email."""
    kind = block["type"]
    if kind == blocks_mod.BlockType.BUTTON:
        label, path = block.get("label", ""), block.get("path", "")
        if label:
            bad = cta_path_problem(path)
            if bad:
                return [_check(f"cta:{key}", ERROR, f"{name}: the button link {bad}.")]
            if not path:
                return [
                    _check(
                        f"cta:{key}",
                        WARNING,
                        f"{name}: the button has no link path, so it opens the home page.",
                    )
                ]
        elif path:
            return [
                _check(
                    f"cta:{key}",
                    WARNING,
                    f"{name}: a button link is set but the button has no label, so no "
                    "button will show.",
                )
            ]
        return []
    if kind not in blocks_mod.LIBRARY_TYPES:
        return []
    label = blocks_mod.BlockType(kind).label.lower()
    slug = block.get("slug", "")
    if not slug:
        return [_check(f"library:{key}", ERROR, f"{name}: a {label} block has no {label} chosen.")]
    languages = library.get(kind, {}).get(slug)
    if not languages:
        return [
            _check(
                f"library:{key}",
                ERROR,
                f"{name}: there is no published {label} “{slug}”.",
            )
        ]
    if code not in languages:
        return [
            _check(
                f"library:{key}",
                WARNING,
                f"{name}: the {label} “{slug}” has no {name} edition, so that block is left "
                f"out of the {name} email.",
            )
        ]
    return []


def _audience_checks(broadcast) -> list[dict]:
    # One grouped query: readers per email language — the preference center's
    # email language when set, else the reading language, as the renderer
    # decides (rendering.email_language).
    rows = (
        resolve(broadcast.audience)
        .annotate(
            lang=Coalesce(NullIf(F("email_subscription__email_locale"), Value("")), F("locale"))
        )
        .values("lang")
        .annotate(n=Count("id"))
        .order_by()
    )
    by_lang: dict[str, int] = {}
    for row in rows:
        lang = copy_mod.base_lang(row["lang"] or "")
        by_lang[lang] = by_lang.get(lang, 0) + row["n"]
    total = sum(by_lang.values())
    if not total:
        # A warning, not an error: a schedule's audience can fill up before it
        # goes out (a "new this week" segment), and sending to nobody harms nobody.
        return [_check("audience", WARNING, "The audience is empty — no reader matches it right now.")]
    out = [_check("audience", OK, f"{total:,} readers match the audience.")]
    for lang, n in sorted(by_lang.items(), key=lambda kv: -kv[1]):
        got = resolve_broadcast_locale(broadcast, lang)
        if got and got != lang:
            out.append(
                _check(
                    f"coverage:{lang}",
                    WARNING,
                    f"{n:,} reader{'s' if n != 1 else ''} get email in {_lang_name(lang)}, which "
                    f"this email isn't written in; they'll get the {_lang_name(got)} version.",
                )
            )
    return out


#: What each AI-draft state means for sending: (level, message).
_TRANSLATION_STATE = {
    translation_jobs.State.DRAFT: (ERROR, "the AI draft hasn't been approved yet — read it and approve it."),
    translation_jobs.State.REQUESTED: (WARNING, "an AI draft has been asked for and isn't back yet (issue #{issue})."),
}


def _translation_checks(broadcast) -> list[dict]:
    """The AI-draft review state per language (admin-only; never shown to readers).
    An unapproved draft blocks sending: nothing AI-written reaches a reader's
    inbox until an admin has read it and pressed Approve."""
    out = []
    for lang, entry in sorted(translation_jobs.states(broadcast).items()):
        name = _lang_name(lang)
        state = entry.get("state")
        if state in _TRANSLATION_STATE:
            level, message = _TRANSLATION_STATE[state]
            out.append(_check(f"translation:{lang}", level, f"{name}: " + message.format(issue=entry.get("issue"))))
        if state != translation_jobs.State.REQUESTED and entry["stale"]:
            source = _lang_name(entry.get("source_locale", "en"))
            out.append(
                _check(
                    f"translation-stale:{lang}",
                    WARNING,
                    f"{name}: the {source} text changed after this translation was drafted.",
                )
            )
    return out


def _test_check(broadcast) -> dict:
    if not broadcast.tested_digest:
        return _check("test", WARNING, "No test email has been sent yet.")
    if broadcast.tested_digest != broadcast.content_digest():
        return _check("test", WARNING, "The email has changed since the last test send.")
    return _check("test", OK, "A test of this exact version was sent.")


def _delivery_checks() -> list[dict]:
    out = []
    if not emails_enabled():
        out.append(
            _check(
                "enabled",
                WARNING,
                "Sending is switched off on this server, so every email will be recorded as "
                "skipped and nobody will receive it.",
            )
        )
    elif settings.EMAIL_ALLOWLIST:
        out.append(
            _check(
                "allowlist",
                WARNING,
                "Review mode is on: only addresses on EMAIL_ALLOWLIST will receive it.",
            )
        )
    reason = health.sender_breach()
    if reason:
        out.append(
            _check(
                "health",
                WARNING,
                f"Sender health over the last 30 days: {reason}. Check the list before a big send.",
            )
        )
    else:
        out.append(_check("health", OK, "Bounce and complaint rates are within limits."))
    return out


def run(broadcast) -> list[dict]:
    """Every check for ``broadcast``, errors first, then warnings, then passes."""
    checks = [
        *_content_checks(broadcast),
        *_audience_checks(broadcast),
        *_translation_checks(broadcast),
        _test_check(broadcast),
        *_delivery_checks(),
    ]
    order = {ERROR: 0, WARNING: 1, OK: 2}
    return sorted(checks, key=lambda c: order[c["level"]])


def content_errors(broadcast) -> list[dict]:
    """Only the checks that can block, which are all about the copy (plus one
    library query per block type, to know the works still exist). What a due
    schedule re-checks before it starts."""
    return blocking([*_content_checks(broadcast), *_translation_checks(broadcast)])


def blocking(checks: list[dict]) -> list[dict]:
    return [c for c in checks if c["level"] == ERROR]
