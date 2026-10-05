"""Turn a reader + content into a rendered email (subject + HTML).

Every email — lifecycle steps, nudges, direct email and admin broadcasts —
renders through ONE template (``emails/blocks.html``) from structured blocks
(emails/blocks.py), never raw HTML, so there is nothing to sanitize. The
fixed-copy emails supply a ``text`` dict (heading, greeting, paragraphs, a CTA,
signoff) that is read as the equivalent blocks. Text direction comes from the
:class:`Language` registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.template.loader import render_to_string

from library.languages import entry as language_entry

from . import blocks as blocks_mod
from . import copy as copy_mod
from . import links

_TEMPLATE = "emails/blocks.html"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str


def _display_name(profile, lang: str) -> str:
    """The reader's first name, or "friend" in the email's language."""
    name = (getattr(profile, "display_name", "") or "").strip()
    if name:
        return name.split()[0]
    return copy_mod.FRIEND.get(copy_mod.base_lang(lang), copy_mod.FRIEND["en"])


def _base_context(subscription, lang: str) -> dict:
    """What every email's frame needs: footer links and text direction."""
    return {
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "preferences_url": links.preferences_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if language_entry(lang).get("rtl") else "ltr",
    }


def _render(text: dict, profile, subscription, lang: str) -> RenderedEmail:
    """Render a fixed-copy email: its ``text`` fields read as blocks. Its CTA
    path is built by code that already chose the edition, so it is used as is."""
    return render_blocks(
        subject=str(text["subject"]),
        content={"preheader": text.get("preheader", ""), "blocks": blocks_mod.legacy_blocks(text)},
        profile=profile,
        subscription=subscription,
        lang=lang,
        localize_buttons=False,
    )


def email_language(profile, subscription) -> str:
    """The language to render in: the reader's email-locale preference when set,
    else their reading locale, else English."""
    override = (getattr(subscription, "email_locale", "") or "").strip()
    return copy_mod.base_lang(override or getattr(profile, "locale", "") or "en")


def render_step(step: str, profile, subscription) -> RenderedEmail:
    """Render lifecycle ``step`` for ``profile`` in their language."""
    lang = email_language(profile, subscription)
    text = copy_mod.step_copy(step, lang)
    return _render(text, profile, subscription, lang)


def render_welcome(profile, subscription) -> RenderedEmail:
    """Back-compat: render the welcome step."""
    return render_step("welcome", profile, subscription)


def _fill(value, mapping: dict[str, str]):
    """Substitute ``{placeholder}`` tokens in a string or list of strings.

    A literal replace, NOT str.format (same reason as the greeting in _render):
    a stray brace in a book title must never raise mid-send."""
    if isinstance(value, list):
        return [_fill(item, mapping) for item in value]
    if isinstance(value, str):
        for token, replacement in mapping.items():
            value = value.replace(token, replacement)
    return value


def render_series_nudge(
    profile, subscription, *, finished_title: str, next_title: str, cta_path: str
) -> RenderedEmail:
    """Render the finish-the-series nudge for ``profile`` in their language.

    Unlike the static lifecycle steps, this fills the just-finished and next-up
    book titles into the copy and points the CTA at the next volume (``cta_path``
    is resolved per reader by the caller)."""
    lang = email_language(profile, subscription)
    mapping = {"{finished}": finished_title, "{next}": next_title}
    text = {
        key: _fill(value, mapping)
        for key, value in copy_mod.step_copy("finish_series", lang).items()
    }
    text["cta_path"] = cta_path
    return _render(text, profile, subscription, lang)


def render_plan_reminder(
    profile,
    subscription,
    *,
    step: str,
    plan_title: str,
    day: int,
    total: int,
    reading_title: str,
    cta_path: str,
) -> RenderedEmail:
    """Render a reading-plan email (``plan_reminder`` or ``plan_paused``) for
    ``profile``: the plan, the day and today's reading filled into the copy, the
    CTA pointing at that day (``cta_path``, built by the caller)."""
    lang = email_language(profile, subscription)
    mapping = {
        "{plan}": plan_title,
        "{day}": str(day),
        "{total}": str(total),
        "{reading}": reading_title or plan_title,
    }
    text = {key: _fill(value, mapping) for key, value in copy_mod.step_copy(step, lang).items()}
    text["cta_path"] = cta_path
    return _render(text, profile, subscription, lang)


def render_milestone(profile, subscription, *, milestone: int) -> RenderedEmail:
    """Render the reading-milestone card for ``profile``, filling in the count."""
    lang = email_language(profile, subscription)
    mapping = {"{count}": str(milestone)}
    text = {
        key: _fill(value, mapping)
        for key, value in copy_mod.step_copy("milestone", lang).items()
    }
    return _render(text, profile, subscription, lang)


def render_broadcast(broadcast, profile, subscription, *, cards=None) -> RenderedEmail | None:
    """Render ``broadcast`` for ``profile``, or ``None`` when the campaign has no
    content in the reader's language (nor a usable fallback)."""
    lang = email_language(profile, subscription)
    resolved = resolve_broadcast_locale(broadcast, lang)
    if resolved is None:
        return None
    return render_blocks(
        subject=str(broadcast.subject.get(resolved, "")),
        content=broadcast.content.get(resolved) or {},
        profile=profile,
        subscription=subscription,
        lang=resolved,
        cards=cards,
    )


def render_blocks(
    *,
    subject: str,
    content: dict,
    profile,
    subscription,
    lang: str,
    cards=None,
    localize_buttons: bool = True,
) -> RenderedEmail:
    """Render one language's block content (emails/blocks.py) for ``profile``.
    Shared by every send and the admin's live preview, so the preview is the
    email. ``cards`` is the caller's library-card cache (``blocks.resolve``)."""
    context = {
        "subject": subject,
        "preheader": content.get("preheader", ""),
        "blocks": blocks_mod.resolve(
            blocks_mod.blocks_for(content),
            lang,
            name=_display_name(profile, lang),
            cards=cards,
            localize_buttons=localize_buttons,
        ),
        **_base_context(subscription, lang),
    }
    return RenderedEmail(subject=subject, html=render_to_string(_TEMPLATE, context))


def render_direct(text: dict, profile, subscription, lang: str) -> RenderedEmail:
    """Render an admin's one-to-one email through the same safe template.
    ``lang`` is the language the admin wrote it in — it sets the email's
    ``lang``/``dir``, so an English note to an Arabic reader stays left-to-right."""
    return _render(text, profile, subscription, lang)


def sendable_locales(broadcast) -> list[str]:
    """The locales a broadcast can be sent in: it has BOTH a subject and
    content for them."""
    return sorted(set(broadcast.subject) & set(broadcast.content))


def resolve_broadcast_locale(broadcast, lang: str) -> str | None:
    """The locale to actually render: the reader's language, else English, else
    the first locale the broadcast can be sent in."""
    locales = sendable_locales(broadcast)
    for candidate in (lang, "en"):
        if candidate in locales:
            return candidate
    return locales[0] if locales else None
