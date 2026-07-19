"""Access control for the admin content dashboard.

Ochorus has no ``is_staff`` concept of its own — every user is a Supabase
account mapped to a bare Django ``User`` (see ``accounts.authentication``). Admin
access is therefore an *email allowlist*: ``ADMIN_EMAILS`` in settings (driven by
the env var of the same name) lists the addresses allowed to see the dashboard
and hit ``/api/admin/*``.

In ``DEBUG`` (local dev, usually with auth unconfigured and no signed-in user)
the check is bypassed so the dashboard is reachable without wiring up Supabase —
but only for requests arriving from the loopback interface. The admin surface
mutates state (publish, author-create, translation jobs), so the bypass must
not turn a single misconfigured env var (``DJANGO_DEBUG=true`` on the host)
into a world-open admin API: a remote client never gets the bypass, DEBUG or
not. Production always requires an authenticated user whose email is on the
list.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import permissions

#: Client addresses that count as "the developer's own machine".
_LOOPBACK_ADDRS = frozenset({"127.0.0.1", "::1"})


def _is_loopback(request) -> bool:
    return (
        request is not None
        and request.META.get("REMOTE_ADDR") in _LOOPBACK_ADDRS
    )


def is_admin_user(user, request=None) -> bool:
    """True if ``user`` may view the admin dashboard.

    Under ``DEBUG`` the allowlist is skipped for loopback requests only (the
    local-dev convenience). Everywhere else — including any remote request on a
    DEBUG server — the user's email must be in ``settings.ADMIN_EMAILS``.
    """
    if settings.DEBUG and _is_loopback(request):
        return True
    email = (getattr(user, "email", "") or "").strip().lower()
    return bool(email) and email in settings.ADMIN_EMAILS


class IsAdminEmail(permissions.BasePermission):
    """Allow only allowlisted admins (see :func:`is_admin_user`)."""

    message = "Admin access is required for this endpoint."

    def has_permission(self, request, view) -> bool:
        return is_admin_user(request.user, request)
