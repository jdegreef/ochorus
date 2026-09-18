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
        greeting = str(text["greeting"]).format(name=_display_name(profile))
    context = {
        "copy": text,
        "subject": text["subject"],
        "preheader": text.get("preheader", ""),
        "greeting": greeting,
        "cta_url": links.site_url(str(text.get("cta_path", ""))) if text.get("cta_label") else "",
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if language_entry(lang).get("rtl") else "ltr",
    }
    html = render_to_string(_TEMPLATE, context)
    return RenderedEmail(subject=str(text["subject"]), html=html)


def render_step(step: str, profile, subscription) -> RenderedEmail:
    """Render lifecycle ``step`` for ``profile`` in their language."""
    lang = copy_mod.base_lang(getattr(profile, "locale", "") or "en")
    text = copy_mod.step_copy(step, lang)
    return _render(text, profile, subscription, lang)


def render_welcome(profile, subscription) -> RenderedEmail:
    """Back-compat: render the welcome step."""
    return render_step("welcome", profile, subscription)


def render_broadcast(broadcast, profile, subscription) -> RenderedEmail | None:
    """Render ``broadcast`` for ``profile``, or ``None`` when the campaign has no
    content in the reader's language (nor a usable fallback)."""
    lang = copy_mod.base_lang(getattr(profile, "locale", "") or "en")
    resolved = resolve_broadcast_locale(broadcast, lang)
    if resolved is None:
        return None
    return _render(broadcast_text(broadcast, resolved), profile, subscription, resolved)


def resolve_broadcast_locale(broadcast, lang: str) -> str | None:
    """The locale to actually render: the reader's language, else English, else
    any locale the broadcast has BOTH a subject and content for."""
    for candidate in (lang, "en"):
        if candidate in broadcast.content and candidate in broadcast.subject:
            return candidate
    common = sorted(set(broadcast.content) & set(broadcast.subject))
    return common[0] if common else None


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
