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


def is_configured() -> bool:
    """Whether Supabase admin lookups are wired up (URL + service-role key).

    Callers use this to tell "no Supabase here, use a local fallback" apart from
    "Supabase is configured but this lookup returned nothing" — the two must not
    be conflated, or a transient failure silently downgrades to an unverified
    address.
    """
    return bool((settings.SUPABASE_URL or "").strip() and settings.SUPABASE_SERVICE_ROLE_KEY)


def _admin_user_request(method: str, uid, *, timeout: float) -> requests.Response:
    """One service-role call on ``/auth/v1/admin/users/<uid>``. The caller
    checks :func:`is_configured` first."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return requests.request(
        method,
        f"{settings.SUPABASE_URL.strip().rstrip('/')}/auth/v1/admin/users/{uid}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=timeout,
    )


def verified_email(profile) -> str | None:
    """The profile's confirmed email from Supabase, or ``None``.

    Returns an address only when Supabase reports it *confirmed* — an
    unconfirmed address is a deliverability and consent risk. ``None`` also when
    Supabase isn't configured (local, tests) or the lookup fails, so callers can
    fall back to whatever local address they hold.
    """
    uid = getattr(profile, "supabase_uid", None)
    if not (is_configured() and uid):
        return None
    try:
        resp = _admin_user_request("get", uid, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        logger.warning("Supabase admin email lookup failed for %s", uid, exc_info=True)
        return None
    email = (data.get("email") or "").strip()
    confirmed = data.get("email_confirmed_at") or data.get("confirmed_at")
    return email if (email and confirmed) else None


class SupabaseDeleteError(Exception):
    """Supabase refused or failed to delete an auth user (not "already gone")."""


def delete_user(uid) -> bool:
    """Delete the Supabase auth user ``uid`` — the sign-in itself, which is what
    frees its email address for a fresh sign-up.

    Returns ``True`` once the user is gone (a 404 counts: it already was), and
    ``False`` when Supabase isn't configured here (local, tests), so there was no
    auth user to remove. Raises :class:`SupabaseDeleteError` on any other
    failure, so a caller can stop before deleting its own rows and leave the
    account whole rather than half-deleted.
    """
    if not is_configured():
        return False
    try:
        resp = _admin_user_request("delete", uid, timeout=_TIMEOUT * 2)
    except requests.RequestException as exc:
        raise SupabaseDeleteError(str(exc)) from exc
    if resp.status_code == 404 or resp.ok:
        return True
    raise SupabaseDeleteError(f"Supabase answered {resp.status_code}")
