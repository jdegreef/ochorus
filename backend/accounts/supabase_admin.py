"""Server-side Supabase admin lookups (service-role), off the request path.

Supabase identity is ``accounts``' domain: :mod:`accounts.authentication`
validates JWTs *on* a request; this is its off-request twin — reading a
profile's **verified** email straight from ``auth.users`` with the service-role
key, for senders and exports that hold no JWT to read claims from. Keeping it
here gives the backend one definition of "the reader's verified email".
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Short by design: this runs inside a per-recipient loop, so one slow or
# unreachable lookup must not stall the whole sweep.
_TIMEOUT = 4


def verified_email(profile) -> str | None:
    """The profile's confirmed email from Supabase, or ``None``.

    Returns an address only when Supabase reports it *confirmed* — an
    unconfirmed address is a deliverability and consent risk. ``None`` also when
    Supabase isn't configured (local, tests) or the lookup fails, so callers can
    fall back to whatever local address they hold.
    """
    base = (settings.SUPABASE_URL or "").rstrip("/")
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    uid = getattr(profile, "supabase_uid", None)
    if not (base and key and uid):
        return None
    try:
        resp = requests.get(
            f"{base}/auth/v1/admin/users/{uid}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        logger.warning("Supabase admin email lookup failed for %s", uid, exc_info=True)
        return None
    email = (data.get("email") or "").strip()
    confirmed = data.get("email_confirmed_at") or data.get("confirmed_at")
    return email if (email and confirmed) else None
