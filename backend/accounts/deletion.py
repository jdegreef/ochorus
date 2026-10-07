"""Deleting an account outright: the Supabase sign-in, then every Ochorus row.

Distinct from the reader's own ``DELETE /api/auth/me/``, which clears their
data but keeps the sign-in (so the address stays taken). This is the full
removal, which frees the email for a new sign-up.
"""

from __future__ import annotations

from . import supabase_admin
from .models import UserProfile


def delete_account(profile: UserProfile) -> bool:
    """Delete ``profile``'s Supabase auth user, then its Django ``User`` — which
    owns the profile (CASCADE), which owns the rest.

    Supabase goes first: if it fails, :class:`supabase_admin.SupabaseDeleteError`
    propagates and nothing local is touched, so a retry finds the account whole.
    Returns whether a Supabase user was deleted (``False`` only where Supabase
    isn't configured).
    """
    auth_deleted = supabase_admin.delete_user(profile.supabase_uid)
    profile.user.delete()
    return auth_deleted
