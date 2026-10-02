"""Turn a reader + content into a rendered email (subject + HTML).

Lifecycle steps and admin broadcasts share one safe body template and one
render path: both supply a structured ``text`` dict (heading, paragraphs, an
optional CTA and greeting), never raw HTML, so there is nothing to sanitize.
Text direction comes from the :class:`Language` registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.template.loader import render_to_string

from library.languages import entry as language_entry

from . import copy as copy_mod
from . import links

_TEMPLATE = "emails/lifecycle.html"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str


def _display_name(profile) -> str:
    name = (getattr(profile, "display_name", "") or "").strip()
    if name:
        return name.split()[0]
    return "friend"


def _render(text: dict, profile, subscription, lang: str) -> RenderedEmail:
    greeting = ""
    if text.get("greeting"):
        # A literal substitution, NOT str.format: broadcast greetings are
        # admin-written, and one stray "{" (or a "{name.__class__}") made
        # .format raise mid-send — or evaluate an attribute lookup.
        greeting = str(text["greeting"]).replace("{name}", _display_name(profile))
    context = {
        "copy": text,
        "subject": text["subject"],
        "preheader": text.get("preheader", ""),
        "greeting": greeting,
        "cta_url": links.site_url(str(text.get("cta_path", ""))) if text.get("cta_label") else "",
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "preferences_url": links.preferences_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if language_entry(lang).get("rtl") else "ltr",
    }
    html = render_to_string(_TEMPLATE, context)
    return RenderedEmail(subject=str(text["subject"]), html=html)


def email_lang(profile, subscription) -> str:
    """The language to render in: the reader's email-locale preference when set,
    else their reading locale, else English."""
    override = (getattr(subscription, "email_locale", "") or "").strip()
    return copy_mod.base_lang(override or getattr(profile, "locale", "") or "en")


def render_step(step: str, profile, subscription) -> RenderedEmail:
    """Render lifecycle ``step`` for ``profile`` in their language."""
    lang = email_lang(profile, subscription)
    text = copy_mod.step_copy(step, lang)
    return _render(text, profile, subscription, lang)


def render_welcome(profile, subscription) -> RenderedEmail:
    """Back-compat: render the welcome step."""
    return render_step("welcome", profile, subscription)


def render_broadcast(broadcast, profile, subscription) -> RenderedEmail | None:
    """Render ``broadcast`` for ``profile``, or ``None`` when the campaign has no
    content in the reader's language (nor a usable fallback)."""
    lang = email_lang(profile, subscription)
    resolved = resolve_broadcast_locale(broadcast, lang)
    if resolved is None:
        return None
    return _render(broadcast_text(broadcast, resolved), profile, subscription, resolved)


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


def broadcast_text(broadcast, locale: str) -> dict:
    """Flatten a broadcast's per-locale content into the shared ``text`` shape."""
    block = broadcast.content.get(locale, {})
    return {
        "subject": broadcast.subject.get(locale, ""),
        "preheader": block.get("preheader", ""),
        "heading": block.get("heading", ""),
        "greeting": block.get("greeting", ""),
        "paragraphs": block.get("paragraphs", []),
        "cta_label": block.get("cta_label", ""),
        "cta_path": block.get("cta_path", ""),
        "signoff": block.get("signoff", ""),
        "signature": block.get("signature", ""),
    }
