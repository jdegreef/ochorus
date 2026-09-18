"""Turn a reader + subscription into a rendered lifecycle email (subject + HTML).

Localized off the reader's ``locale`` (see :mod:`emails.copy`). Text direction
comes from the :class:`Language` registry — a language whose row has ``rtl`` set
gets ``dir="rtl"`` (so a language with no registry row, e.g. in an unseeded test
DB, falls back to LTR). Every lifecycle step shares one base layout and one body
template; only the copy and the CTA target differ.
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


def render_step(step: str, profile, subscription) -> RenderedEmail:
    """Render lifecycle ``step`` for ``profile`` in their language."""
    lang = copy_mod.base_lang(getattr(profile, "locale", "") or "en")
    text = copy_mod.step_copy(step, lang)

    context = {
        "copy": text,
        "subject": text["subject"],
        "preheader": text["preheader"],
        "greeting": str(text["greeting"]).format(name=_display_name(profile)),
        "cta_url": links.site_url(str(text.get("cta_path", ""))),
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if language_entry(lang).get("rtl") else "ltr",
    }
    html = render_to_string(_TEMPLATE, context)
    return RenderedEmail(subject=str(text["subject"]), html=html)


def render_welcome(profile, subscription) -> RenderedEmail:
    """Back-compat: render the welcome step."""
    return render_step("welcome", profile, subscription)
