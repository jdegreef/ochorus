"""Resolving the address to send to.

Decision (build plan, "key decisions"): the source of truth is the **verified**
email in Supabase's ``auth.users``, not ``UserProfile.email`` — which is
best-effort and can be blank until the reader signs in again. The Supabase
lookup itself lives in :mod:`accounts.supabase_admin` (identity is accounts'
domain); the fallback below is the emails app's own policy — when Supabase
isn't configured (local, tests) we use the profile's own email so the pipeline
still runs end to end.
"""

from __future__ import annotations

from accounts.supabase_admin import verified_email as _supabase_verified_email


def verified_email(profile) -> str | None:
    """The reader's confirmed email, or ``None`` if we can't establish one.

    Tries Supabase first (authoritative, tells us whether the address is
    verified); falls back to ``profile.email`` when Supabase isn't wired up.
    """
    email = _supabase_verified_email(profile)
    if email:
        return email
    fallback = (getattr(profile, "email", "") or "").strip()
    return fallback or None
