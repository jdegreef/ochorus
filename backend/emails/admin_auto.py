"""Admin API for the campaigns the system builds itself — the monthly digest and
"new in your language" (emails/auto_emails.py): their switches and settings,
the campaigns they have built, and "build a draft now".

Super-admin-only like the rest of the Emails section. A built campaign is an
ordinary broadcast; it is opened, approved (scheduled) and sent from Compose.
"""

from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, actor_email
from library.models import AdminAction

from . import auto_emails
from .admin_views import _serialize_broadcast
from .models import AutoEmail, AutoEmailConfig, Broadcast

#: How many built campaigns the page lists.
RECENT_LIMIT = 24


def _serialize_config(config: AutoEmailConfig) -> dict:
    data = {
        "key": config.key,
        "label": AutoEmail(config.key).label,
        "enabled": config.enabled,
        "enabled_at": config.enabled_at.isoformat() if config.enabled_at else None,
        "require_approval": config.require_approval,
        "updated_by": config.updated_by,
    }
    if config.key == AutoEmail.DIGEST:
        data["sections"] = {s: bool((config.sections or {}).get(s, True)) for s in auto_emails.SECTIONS}
    return data


def _payload() -> dict:
    from django.utils import timezone

    next_send = auto_emails.next_issue(timezone.now())
    recent = Broadcast.objects.exclude(auto_key="").order_by("-created_at")[:RECENT_LIMIT]
    return {
        "configs": [_serialize_config(AutoEmailConfig.get(key)) for key in AutoEmail.values],
        "digest_next_send": next_send.isoformat(),
        "digest_builds_at": (next_send - auto_emails.DRAFT_LEAD).isoformat(),
        "recent": [_serialize_broadcast(b) for b in recent],
    }


class AdminAutoEmailsView(AdminAudited, APIView):
    """``GET`` the switches and what they built; ``PATCH {"key", "enabled"?,
    "require_approval"?, "sections"?}`` changes one."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_AUTO_SETTINGS

    def audit_entry(self, request, response):
        key = str(request.data.get("key", ""))
        fields = {f: request.data[f] for f in ("enabled", "require_approval", "sections") if f in request.data}
        return (f"auto-email:{key}", fields)

    def get(self, request):
        return Response(_payload())

    def patch(self, request):
        key = str(request.data.get("key", ""))
        if key not in AutoEmail.values:
            return Response(
                {"detail": f"key must be one of {', '.join(AutoEmail.values)}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        config = AutoEmailConfig.get(key)
        if "enabled" in request.data:
            auto_emails.set_enabled(config, bool(request.data["enabled"]))
        if "require_approval" in request.data:
            config.require_approval = bool(request.data["require_approval"])
        sections = request.data.get("sections")
        if isinstance(sections, dict):
            config.sections = {
                s: bool(sections[s]) for s in auto_emails.SECTIONS if s in sections
            }
        config.updated_by = actor_email(request)[:254]
        config.save()
        return Response(_payload())


class AdminAutoEmailBuildView(AdminAudited, APIView):
    """``POST {"key": "digest"}`` builds this month's digest now, as a draft that
    waits for approval — to see it before its date, or to send one early."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_AUTO_BUILD

    def audit_entry(self, request, response):
        return (f"auto-email:{request.data.get('key', '')}", {"built": response.data.get("built")})

    def post(self, request):
        if str(request.data.get("key", "")) != AutoEmail.DIGEST:
            return Response(
                {"detail": "only the digest can be built by hand"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        broadcast = auto_emails.build_digest(force=True)
        if broadcast is None:
            return Response(
                {
                    "detail": "Nothing was built: this month's digest already exists, or no "
                    "language has anything new, a quote or a plan to show.",
                },
                status=http_status.HTTP_409_CONFLICT,
            )
        return Response({"built": broadcast.id, **_payload()}, status=http_status.HTTP_201_CREATED)
