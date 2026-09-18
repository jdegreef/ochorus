"""Resolving the address to send to.

Decision (build plan, "key decisions"): the source of truth is the **verified**
email in Supabase's ``auth.users``, not ``UserProfile.email`` — which is
best-effort and can be blank until the reader signs in again. We fetch it with
the service-role key via Supabase's admin API, and only trust a *confirmed*
address. When Supabase isn't configured (local, tests) we fall back to the
profile's own email so the pipeline still runs end to end.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10


def verified_email(profile) -> str | None:
    """The reader's confirmed email, or ``None`` if we can't establish one.

    Tries Supabase first (authoritative, tells us whether the address is
    verified); falls back to ``profile.email`` when Supabase isn't wired up.
    Never returns an unverified Supabase address — an unconfirmed address is a
    deliverability and consent risk.
    """
    email = _from_supabase(profile)
    if email is not None:
        return email
    fallback = (getattr(profile, "email", "") or "").strip()
    return fallback or None


def _from_supabase(profile) -> str | None:
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
        logger.warning("Supabase email lookup failed for %s", uid, exc_info=True)
        return None
    email = (data.get("email") or "").strip()
    confirmed = data.get("email_confirmed_at") or data.get("confirmed_at")
    if email and confirmed:
        return email
    return None
