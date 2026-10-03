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
from django.db.models import F, Max, Min, Window
from django.db.models.functions import Lower, RowNumber
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.admin_roles import (
    ROLE_GRANTS,
    ROLE_INFO,
    ROLE_NAMES,
    apply_grant,
    restore_grants,
    revoke_grant,
    role_drift,
)
from accounts.models import (
    ALL_LANGUAGES,
    AdminCapability,
    AdminGrant,
    AdminVerb,
    UserProfile,
    split_providers,
)
from accounts.permissions import HasAnyAdminAccess, IsAdminEmail

from ..audit import AdminAudited
from ..languages import entry, known_codes, language_map
from ..models import AdminAction


def role_summaries() -> list[dict]:
    """Every role's code, plain name and one-line summary — one projection of
    ``ROLE_INFO`` for both the team console and the Help page."""
    return [
        {"code": code, "label": label, "summary": summary}
        for code, (label, summary) in ROLE_INFO.items()
    ]


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
            if request.data.get("restore") is not None:
                detail["restore"] = request.data["restore"]
            # A role grant drops the previous role's other rows — record them,
            # so the log shows when that access went.
            detail["removed"] = (getattr(response, "data", None) or {}).get("removed", [])
        return (f"user:{email}", detail)

    def get(self, request):
        """Everyone who holds a grant, with their scopes, plus the options the
        grant form needs."""
        # One read of the grant table: each member's scopes, when their access
        # began and who last changed it all come from the same rows.
        by_email: dict[str, list] = {}
        for g in AdminGrant.objects.order_by("email", "capability"):
            by_email.setdefault(g.email, []).append(g)
        emails = list(by_email)
        seen = self._last_seen(emails)
        history = self._history(emails)
        first_granted = self._first_granted(emails)
        members = []
        for email, rows in by_email.items():
            scopes = [AdminGrant.scope_dict(g) for g in rows]
            hist = history.get(email, [])
            # Rows are recreated by an Undo or a role swap, so their created_at
            # can be later than the first grant the audit log remembers.
            began = min(d for d in (first_granted.get(email), *(g.created_at for g in rows)) if d)
            members.append(
                {
                    "email": email,
                    "scopes": scopes,
                    "roles": sorted({s["role"] for s in scopes if s["role"]}),
                    "outdated": role_drift(scopes),
                    # A grant only works once that exact address signs in, so
                    # null here means "invited, never seen".
                    "last_seen_at": seen.get(email),
                    "granted_at": began,
                    # The newest logged change (a revoke deletes its rows, so
                    # the rows alone can't say who made it); else the rows.
                    "granted_by": hist[0]["actor"] if hist else max(rows, key=lambda g: g.updated_at).granted_by,
                    "history": hist,
                }
            )
        codes = known_codes()
        return Response(
            {
                "members": members,
                "super_admins": sorted(settings.ADMIN_EMAILS),
                "roles": list(ROLE_NAMES),
                "capabilities": AdminCapability.choices,
                "verbs": AdminVerb.choices,
                "languages": sorted(codes),
                # Plain names for the form's role cards and language chips —
                # the same source the Help page reads, so the two agree.
                "role_info": [r for r in role_summaries() if r["code"] in ROLE_NAMES],
                # entry() refreshes on a miss, so a language another worker just
                # created is named, not shown as a bare code.
                "language_names": {code: entry(code)["name"] for code in codes},
            }
        )

    @staticmethod
    def _last_seen(emails) -> dict:
        """email → the account's last authenticated request, for the members
        that have signed in. Matched case-insensitively: grants are stored
        lowercased, the auth user's email is whatever the provider sent.

        Supabase issues no session to an unconfirmed email sign-up, so a
        profile with a ``last_seen_at`` has signed in with that address. The
        lookup has no index to use, but it runs once per load of a super-admin
        page, not per reader request."""
        rows = (
            UserProfile.objects.annotate(addr=Lower("user__email"))
            .filter(addr__in=emails, last_seen_at__isnull=False)
            .values("addr")
            .annotate(seen=Max("last_seen_at"))
        )
        return {r["addr"]: r["seen"] for r in rows}

    @staticmethod
    def _first_granted(emails) -> dict:
        """email → its earliest logged grant, which survives the row rewrites."""
        rows = (
            AdminAction.objects.filter(
                target__in=[f"user:{e}" for e in emails],
                action=AdminAction.Action.ROLE_GRANT,
            )
            .values("target")
            .annotate(first=Min("at"))
        )
        return {r["target"].removeprefix("user:"): r["first"] for r in rows}

    #: Grant/revoke events shown per member in the Manage panel; the Activity
    #: page (linked, filtered to the member) has the rest.
    HISTORY_LIMIT = 10

    @classmethod
    def _history(cls, emails) -> dict:
        """email → its newest grant/revoke events, from the append-only
        AdminAction log this view writes. Capped per member in SQL — the log
        only grows, so it must not be read whole on every page load."""
        events = (
            AdminAction.objects.filter(
                target__in=[f"user:{e}" for e in emails],
                action__in=[AdminAction.Action.ROLE_GRANT, AdminAction.Action.ROLE_REVOKE],
            )
            .annotate(
                n=Window(RowNumber(), partition_by=F("target"), order_by=[F("at").desc(), F("id").desc()])
            )
            .filter(n__lte=cls.HISTORY_LIMIT)
            .order_by("target", "-at", "-id")
        )
        out: dict[str, list] = {}
        for a in events:
            d = a.detail or {}
            if a.action == AdminAction.Action.ROLE_REVOKE:
                kind = "revoke"
            else:
                kind = "restore" if d.get("restore") is not None else "grant"
            out.setdefault(a.target.removeprefix("user:"), []).append(
                {
                    "id": a.id,
                    "at": a.at,
                    "kind": kind,
                    "actor": a.actor,
                    "role": d.get("role") or "",
                    "capability": d.get("capability") or "",
                    "languages": d.get("languages") or "",
                    "removed": d.get("removed") or [],
                }
            )
        return out

    def post(self, request):
        """Grant a role (or a single capability+verb) to an email, or restore
        a revoked member's exact rows (``restore``)."""
        email = (request.data.get("email") or "").strip().lower()
        if email in settings.ADMIN_EMAILS:
            return Response(
                {"detail": f"{email} is already a super admin — grants add nothing."},
                status=409,
            )
        before = {s["capability"] for s in AdminGrant.scopes_for(email)}
        granted_by = getattr(request.user, "email", "") or ""
        try:
            if request.data.get("restore") is not None:
                # Undo of a revoke: put back the exact rows, not the roles.
                restore_grants(email, request.data["restore"], granted_by=granted_by)
            else:
                apply_grant(
                    email,
                    role=request.data.get("role"),
                    capability=request.data.get("capability"),
                    verb=request.data.get("verb"),
                    languages=self._languages(request.data.get("languages")),
                    granted_by=granted_by,
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        scopes = AdminGrant.scopes_for(email)
        removed = sorted(before - {s["capability"] for s in scopes})
        return Response({"email": email, "scopes": scopes, "removed": removed}, status=201)

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


class AdminRolesView(APIView):
    """The access model as data, for the Help & roles page: every capability
    with its label, each role's label, summary and grants, and language names.

    Read straight from ``PRESETS`` / ``ROLE_INFO`` so the help page cannot drift
    from the roles it explains. Open to anyone with any admin access — the Help
    page is in everyone's rail, including a holder of one raw grant — and it
    names no people, so there is nothing here a grantee shouldn't see."""

    permission_classes = [HasAnyAdminAccess]

    def get(self, request):
        return Response(
            {
                "capabilities": [
                    {"code": c, "label": label} for c, label in AdminCapability.choices
                ],
                "roles": [
                    {**r, "grants": ROLE_GRANTS[r["code"]]} for r in role_summaries()
                ],
                "languages": {code: e["name"] for code, e in language_map().items()},
            }
        )
