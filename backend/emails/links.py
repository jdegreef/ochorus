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


def site_url(path: str = "") -> str:
    """A link into the reader site (defaults to the home page)."""
    return f"{site_base()}/{path.lstrip('/')}" if path else site_base() or "/"
