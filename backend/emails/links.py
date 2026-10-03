"""Absolute URLs that go *into* emails.

Sending happens off-request (a sweep, a cron), so there is no ``request`` to
build absolute URLs from — they come from settings. Unsubscribe lives on the
API origin (``API_PUBLIC_URL``) because the one-click ``List-Unsubscribe-Post``
target must be a real POST endpoint; content links point at the reader
(``PUBLIC_SITE_URL``).
"""

from __future__ import annotations

from django.conf import settings


def api_base() -> str:
    return (getattr(settings, "API_PUBLIC_URL", "") or "").rstrip("/")


def site_base() -> str:
    return (getattr(settings, "PUBLIC_SITE_URL", "") or "").rstrip("/")


def unsubscribe_url(token: str) -> str:
    """The footer's one-click unsubscribe link for a subscription token."""
    return f"{api_base()}/api/emails/unsubscribe/{token}/"


def preferences_url(token: str) -> str:
    """The footer's "manage preferences" link — the reader-facing preference
    center, keyed by the same token as unsubscribe (no login needed)."""
    return f"{site_base()}/email/preferences/{token}"


def site_url(path: str = "") -> str:
    """A link into the reader site (defaults to the home page)."""
    return f"{site_base()}/{path.lstrip('/')}" if path else site_base() or "/"


def reader_path(section: str, slug: str, language: str) -> str:
    """The reader-site path for a work (``section`` is "books", "sermons" or
    "plans"), locale-prefixed and slash-terminated so it lands on the
    prerendered page (English is unprefixed)."""
    path = f"{section}/{slug}/"
    return path if language == "en" else f"{language}/{path}"
