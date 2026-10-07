"""Deleting an account outright: the Supabase sign-in, then every Ochorus row.

Distinct from the reader's own ``DELETE /api/auth/me/``, which clears their
data but keeps the sign-in (so the address stays taken). This is the full
removal, which frees the email for a new sign-up.
"""

from __future__ import annotations

from django.db import transaction

from . import supabase_admin
from .models import AdminGrant, UserProfile


def delete_account(profile: UserProfile) -> dict:
    """Delete ``profile``'s Supabase auth user, then its Django ``User`` — which
    owns the profile (CASCADE), which owns the rest — and any scoped admin
    grants on its email. Grants are keyed by email, not by account, so without
    this they would wait for the address and re-arm on its next sign-up.

    Supabase goes first: if it fails, :class:`supabase_admin.SupabaseDeleteError`
    propagates and nothing local is touched, so a retry finds the account whole.
    Returns ``auth_deleted`` (``False`` only where Supabase isn't configured)
    and ``grants_revoked``.
    """
    auth_deleted = supabase_admin.delete_user(profile.supabase_uid)
    email = (profile.email or "").strip()
    with transaction.atomic():
        grants_revoked = (
            AdminGrant.objects.filter(email__iexact=email).delete()[0] if email else 0
        )
        profile.user.delete()
    return {"auth_deleted": auth_deleted, "grants_revoked": grants_revoked}
