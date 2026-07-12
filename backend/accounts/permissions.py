"""Access control for the admin content dashboard.

Ochorus has no ``is_staff`` concept of its own — every user is a Supabase
account mapped to a bare Django ``User`` (see ``accounts.authentication``). Admin
access is therefore an *email allowlist*: ``ADMIN_EMAILS`` in settings (driven by
the env var of the same name) lists the addresses allowed to see the dashboard
and hit ``/api/admin/*``.

In ``DEBUG`` (local dev, usually with auth unconfigured and no signed-in user)
the check is bypassed so the dashboard is reachable without wiring up Supabase.
Production always requires an authenticated user whose email is on the list.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import permissions


def is_admin_user(user) -> bool:
    """True if ``user`` may view the admin dashboard.

    Always true under ``DEBUG`` (the dashboard is a read-only, local-dev
    convenience); otherwise the user's email must be in ``settings.ADMIN_EMAILS``.
    """
    if settings.DEBUG:
        return True
    email = (getattr(user, "email", "") or "").strip().lower()
    return bool(email) and email in settings.ADMIN_EMAILS


class IsAdminEmail(permissions.BasePermission):
    """Allow only allowlisted admins (see :func:`is_admin_user`)."""

    message = "Admin access is required for this endpoint."

    def has_permission(self, request, view) -> bool:
        return is_admin_user(request.user)
