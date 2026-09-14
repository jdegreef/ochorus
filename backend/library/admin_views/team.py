"""Admin dashboard API — the team / access console.

The super admin (only) grants and revokes scoped admin access here — the UI
counterpart to the ``admin_grants`` command. Granting is deliberately NOT
delegated: this endpoint is gated by ``IsAdminEmail`` (the ``ADMIN_EMAILS``
allowlist), not by a capability grant, so the people who can hand out access are
exactly the bootstrap super admins — a grant can never widen the set that hands
out grants. Every grant/revoke is audited (``role.grant`` / ``role.revoke``).
"""

from __future__ import annotations

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.admin_roles import ROLE_NAMES, apply_grant, revoke_grant
from accounts.models import (
    ALL_LANGUAGES,
    AdminCapability,
    AdminGrant,
    AdminVerb,
    split_providers,
)
from accounts.permissions import IsAdminEmail

from ..audit import AdminAudited
from ..languages import known_codes
from ..models import AdminAction


class AdminTeamView(AdminAudited, APIView):
    """List / grant / revoke scoped admin access. Super admin only."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        return (
            AdminAction.Action.ROLE_REVOKE
            if request.method == "DELETE"
            else AdminAction.Action.ROLE_GRANT
        )

    def audit_entry(self, request, response):
        src = request.query_params if request.method == "DELETE" else request.data
        email = (src.get("email") or "").strip().lower()
        detail = {"capability": src.get("capability") or ""}
        if request.method != "DELETE":
            detail["role"] = request.data.get("role") or ""
            detail["languages"] = request.data.get("languages") or ALL_LANGUAGES
        return (f"user:{email}", detail)

    def get(self, request):
        """Everyone who holds a grant, with their scopes, plus the options the
        grant form needs."""
        emails = sorted(set(AdminGrant.objects.values_list("email", flat=True)))
        members = []
        for email in emails:
            scopes = AdminGrant.scopes_for(email)
            members.append(
                {
                    "email": email,
                    "scopes": scopes,
                    "roles": sorted({s["role"] for s in scopes if s["role"]}),
                }
            )
        return Response(
            {
                "members": members,
                "super_admins": sorted(settings.ADMIN_EMAILS),
                "roles": list(ROLE_NAMES),
                "capabilities": AdminCapability.choices,
                "verbs": AdminVerb.choices,
                "languages": sorted(known_codes()),
            }
        )

    def post(self, request):
        """Grant a role (or a single capability+verb) to an email."""
        email = (request.data.get("email") or "").strip().lower()
        if email in settings.ADMIN_EMAILS:
            return Response(
                {"detail": f"{email} is already a super admin — grants add nothing."},
                status=409,
            )
        try:
            apply_grant(
                email,
                role=request.data.get("role"),
                capability=request.data.get("capability"),
                verb=request.data.get("verb"),
                languages=self._languages(request.data.get("languages")),
                granted_by=getattr(request.user, "email", "") or "",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {"email": email, "scopes": AdminGrant.scopes_for(email)}, status=201
        )

    def delete(self, request):
        """Revoke a grantee's access — all of it, or just one capability."""
        email = (request.query_params.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "email is required."}, status=400)
        revoked = revoke_grant(email, capability=request.query_params.get("capability") or None)
        return Response(
            {"email": email, "revoked": revoked, "scopes": AdminGrant.scopes_for(email)}
        )

    @staticmethod
    def _languages(raw) -> str:
        """A codes list, a comma string, or ``"*"`` → the stored languages string.

        An EXPLICIT empty selection raises rather than defaulting to ``"*"`` — on
        a screen whose job is to *narrow* access, "restrict but pick nothing" must
        deny, not silently widen to every language."""
        if raw in (None, "", ALL_LANGUAGES) or raw == [ALL_LANGUAGES]:
            return ALL_LANGUAGES
        items = raw if isinstance(raw, list) else split_providers(str(raw))
        codes = sorted({str(c).strip().lower() for c in items if str(c).strip()})
        if not codes:
            raise ValueError("choose at least one language, or select all languages")
        return ",".join(codes)
