"""Turn a reader + subscription into a rendered email (subject + HTML).

Localized off the reader's ``locale`` (see :mod:`emails.copy`); right-to-left
locales get ``dir="rtl"`` so Arabic renders correctly. The base layout adds the
Ochorus chrome and the unsubscribe footer.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.template.loader import render_to_string

from . import copy as copy_mod
from . import links

_RTL_LOCALES = frozenset({"ar", "he", "fa", "ur"})


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str


def _display_name(profile) -> str:
    name = (getattr(profile, "display_name", "") or "").strip()
    if name:
        return name.split()[0]
    return "friend"


def render_welcome(profile, subscription) -> RenderedEmail:
    """Render the welcome email for ``profile`` in their language."""
    locale = (getattr(profile, "locale", "") or "en").lower()
    text = copy_mod.welcome_copy(locale)
    lang = locale.split("-")[0]

    context = {
        "copy": text,
        "subject": text["subject"],
        "preheader": text["preheader"],
        "greeting": str(text["greeting"]).format(name=_display_name(profile)),
        "cta_url": links.site_url(str(text.get("cta_path", ""))),
        "unsubscribe_url": links.unsubscribe_url(subscription.unsubscribe_token),
        "lang": lang,
        "dir": "rtl" if lang in _RTL_LOCALES else "ltr",
    }
    html = render_to_string("emails/welcome.html", context)
    return RenderedEmail(subject=str(text["subject"]), html=html)
