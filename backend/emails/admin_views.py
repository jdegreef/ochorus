"""Admin dashboard API — email campaign metrics.

Aggregate-only: sent / open / click / bounce rollups per lifecycle step and per
broadcast, plus subscription health. No recipient identities — this is the
open/click/bounce dashboard the build plan puts in the Ochorus admin (rather
than Resend's). Open and click *rates* are computed here from the mirrored
events, exactly as the plan intends.

Counts and rates come from emails/health.py, which states the conventions; the
guardrail reads the same numbers.
"""

from __future__ import annotations

from functools import cached_property

from django.db.models import Count
from django.utils.dateparse import parse_datetime
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.models import AdminAction

from . import audience as audience_mod
from . import broadcasts as broadcasts_mod
from . import direct as direct_mod
from . import health, preflight
from . import history as history_mod
from .models import (
    Broadcast,
    BroadcastStatus,
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    SendStatus,
)
from .rendering import sendable_locales


class AdminEmailMetricsView(APIView):
    """Open/click/bounce rollups per lifecycle step and per broadcast.

    Super-admin-only: the whole Emails section (reader broadcasts and their
    metrics) is reserved to the ``ADMIN_EMAILS`` allowlist. Language admins do
    reader-facing content QA, not outbound email (a founder decision, 2026-09-21)."""

    permission_classes = [IsAdminEmail]

    def get(self, request):
        sent_by_step = self._sent_counts("lifecycle_step", kind=EmailKind.LIFECYCLE)
        events_by_step = self._event_counts("message__lifecycle_step", kind=EmailKind.LIFECYCLE)

        sent_by_broadcast = self._sent_counts("broadcast_id", kind=EmailKind.BROADCAST)
        events_by_broadcast = self._event_counts("message__broadcast_id", kind=EmailKind.BROADCAST)

        return Response(
            {
                "overview": self._overview(),
                "by_step": self._rows(sent_by_step, events_by_step, self._step_label),
                "by_broadcast": self._rows(
                    sent_by_broadcast, events_by_broadcast, self._broadcast_label
                ),
                "subscribers": self._subscribers(),
            }
        )

    # --- aggregation helpers -------------------------------------------------

    @staticmethod
    def _sent_counts(field: str, *, kind: str) -> dict:
        rows = (
            health.real_sends(EmailMessage.objects.filter(kind=kind))
            .values(field)
            .annotate(n=Count("id"))
        )
        return {row[field]: row["n"] for row in rows}

    @staticmethod
    def _event_counts(field: str, *, kind: str) -> dict:
        """``{group_key: {event_type: distinct_message_count}}`` for sent
        messages of ``kind``."""
        rows = (
            EmailEvent.objects.filter(
                message__in=health.real_sends(EmailMessage.objects.filter(kind=kind))
            )
            .values(field, "type")
            .annotate(n=Count("message_id", distinct=True))
        )
        out: dict = {}
        for row in rows:
            out.setdefault(row[field], {})[row["type"]] = row["n"]
        return out

    def _rows(self, sent_counts: dict, event_counts: dict, label) -> list[dict]:
        keys = set(sent_counts) | set(event_counts)
        rows = []
        for key in keys:
            if key is None:
                continue
            row = health.assemble(sent_counts.get(key, 0), event_counts.get(key, {}))
            row.update(label(key))
            rows.append(row)
        rows.sort(key=lambda r: r["sent"], reverse=True)
        return rows

    @staticmethod
    def _step_label(step: str) -> dict:
        return {"step": step}

    def _broadcast_label(self, broadcast_id) -> dict:
        name = self._broadcast_names.get(broadcast_id, f"#{broadcast_id}")
        return {"id": broadcast_id, "name": name}

    @cached_property
    def _broadcast_names(self) -> dict:
        return dict(Broadcast.objects.values_list("id", "name"))

    def _overview(self) -> dict:
        overview = health.metrics(EmailMessage.objects.all())
        overview["failed"] = EmailMessage.objects.filter(status=SendStatus.FAILED).count()
        return overview

    @staticmethod
    def _subscribers() -> dict:
        # Count readers who want the "announcements" stream from the new source of
        # truth (``stream_prefs``, set by the preference center), not the legacy
        # ``newsletter_opt_in`` boolean the preference center never writes.
        return {
            "total": EmailSubscription.objects.count(),
            "announcements": EmailSubscription.objects.filter(
                EmailSubscription.wants_stream_q("announcements")
            ).count(),
            "unsubscribed": EmailSubscription.objects.filter(unsubscribed_all=True).count(),
            "suppressed": EmailSubscription.objects.filter(
                suppressed_at__isnull=False
            ).count(),
        }


# --- Broadcast compose / schedule / send ------------------------------------


def _serialize_broadcast(b: Broadcast, *, detail: bool = False, checks=None) -> dict:
    """A broadcast for the admin. ``detail`` adds content, results and — while
    it can still be sent — the pre-send checks (``checks`` passes ones the
    caller already ran, so a request computes them once)."""
    data = {
        "id": b.id,
        "name": b.name,
        "status": b.status,
        "subject": b.subject,
        "audience": b.audience,
        "from_address": b.from_address,
        "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
        # Locales the campaign can actually send in (subject AND content present).
        "locales": sendable_locales(b),
        "audience_count": audience_mod.count(b.audience),
        # The batched send: how far it has got, why it's in this state, and
        # whether its copy is frozen (the client doesn't re-derive the rules).
        "progress": b.progress,
        "status_reason": b.status_reason,
        "send_started_at": b.send_started_at.isoformat() if b.send_started_at else None,
        "locked": b.is_locked,
    }
    if detail:
        data["content"] = b.content
        data["stats"] = health.metrics(EmailMessage.objects.filter(broadcast=b))
        if b.can_send:
            data["checks"] = preflight.run(b) if checks is None else checks
        else:
            data["checks"] = []
    return data


def _apply_fields(broadcast: Broadcast, data) -> None:
    """Copy editable fields from request data onto a broadcast (no send)."""
    if "name" in data:
        broadcast.name = str(data["name"]).strip()[:200]
    for field in ("subject", "content", "audience"):
        if field in data and isinstance(data[field], dict):
            setattr(broadcast, field, data[field])
    if "from_address" in data:
        broadcast.from_address = str(data["from_address"]).strip()[:200]


class AdminBroadcastsView(AdminAudited, APIView):
    """List broadcasts, or create a draft. Super-admin-only (see AdminEmailMetricsView)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.BROADCAST_CREATE

    def audit_entry(self, request, response):
        return (f"broadcast:{response.data.get('id')}", {"name": response.data.get("name", "")})

    def get(self, request):
        rows = [_serialize_broadcast(b) for b in Broadcast.objects.all()]
        return Response({"broadcasts": rows})

    def post(self, request):
        broadcast = Broadcast(status=BroadcastStatus.DRAFT)
        _apply_fields(broadcast, request.data)
        if not broadcast.name:
            return Response(
                {"detail": "name is required"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        broadcast.save()
        return Response(
            _serialize_broadcast(broadcast, detail=True),
            status=http_status.HTTP_201_CREATED,
        )


class AdminBroadcastDetailView(AdminAudited, APIView):
    """Read, edit (draft/scheduled only), or delete a broadcast.

    Super-admin-only (see AdminEmailMetricsView)."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        return (
            AdminAction.Action.BROADCAST_DELETE
            if request.method == "DELETE"
            else AdminAction.Action.BROADCAST_EDIT
        )

    def audit_entry(self, request, response):
        return (f"broadcast:{self.kwargs.get('pk')}", {})

    def _get(self, pk):
        return Broadcast.objects.filter(pk=pk).first()

    def get(self, request, pk):
        broadcast = self._get(pk)
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        return Response(_serialize_broadcast(broadcast, detail=True))

    def patch(self, request, pk):
        broadcast = self._get(pk)
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        if broadcast.is_locked:
            return Response(
                {"detail": "a broadcast that has started sending can't be edited"},
                status=http_status.HTTP_409_CONFLICT,
            )
        _apply_fields(broadcast, request.data)
        broadcast.save()
        return Response(_serialize_broadcast(broadcast, detail=True))

    def delete(self, request, pk):
        broadcast = self._get(pk)
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        if broadcast.is_locked:
            return Response(
                {"detail": "a broadcast that has started sending can't be deleted"},
                status=http_status.HTTP_409_CONFLICT,
            )
        broadcast.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class AdminBroadcastActionView(AdminAudited, APIView):
    """Act on a broadcast: ``send`` now, ``schedule``, ``cancel``, ``test``,
    ``pause`` or ``resume``.

    ``send`` queues the broadcast; the email cron sends it in batches
    (emails/broadcasts.py), so the request returns at once however large the
    audience. ``send`` and ``schedule`` refuse while any pre-send check is an
    error (emails/preflight.py), returning the checks.

    Super-admin-only (see AdminEmailMetricsView)."""

    permission_classes = [IsAdminEmail]

    _ACTION_AUDIT = {
        "send": AdminAction.Action.BROADCAST_SEND,
        "schedule": AdminAction.Action.BROADCAST_SCHEDULE,
        "cancel": AdminAction.Action.BROADCAST_CANCEL,
        "test": AdminAction.Action.BROADCAST_TEST,
        "pause": AdminAction.Action.BROADCAST_PAUSE,
        "resume": AdminAction.Action.BROADCAST_RESUME,
    }

    def audit_action_for(self, request):
        action = str(request.data.get("action", "")).strip()
        return self._ACTION_AUDIT.get(action, AdminAction.Action.BROADCAST_SEND)

    def audit_entry(self, request, response):
        return (
            f"broadcast:{self.kwargs.get('pk')}",
            {"action": str(request.data.get("action", "")).strip()},
        )

    def post(self, request, pk):
        broadcast = Broadcast.objects.filter(pk=pk).first()
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)

        action = str(request.data.get("action", "")).strip()
        if action == "test":
            return self._test(request, broadcast)
        if action == "send":
            return self._send(broadcast)
        if action == "schedule":
            return self._schedule(request, broadcast)
        if action == "cancel":
            return self._cancel(broadcast)
        if action == "pause":
            return self._pause(request, broadcast)
        if action == "resume":
            return self._resume(request, broadcast)
        return Response(
            {"detail": f"unknown action {action!r}"},
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _refuse(broadcast) -> tuple[Response | None, list | None]:
        """``(409, None)`` when ``broadcast`` can't be sent or scheduled, else
        ``(None, checks)`` — the checks it passed, for the response."""
        if not broadcast.can_send:
            return Response(
                {"detail": f"a {broadcast.status} broadcast can't be sent again"},
                status=http_status.HTTP_409_CONFLICT,
            ), None
        checks = preflight.run(broadcast)
        errors = preflight.blocking(checks)
        if errors:
            return Response(
                {"detail": errors[0]["message"], "checks": checks},
                status=http_status.HTTP_409_CONFLICT,
            ), None
        return None, checks

    def _send(self, broadcast):
        refused, _ = self._refuse(broadcast)
        if refused:
            return refused
        broadcasts_mod.start_send(broadcast)
        return Response(_serialize_broadcast(broadcast, detail=True))

    def _schedule(self, request, broadcast):
        when = parse_datetime(str(request.data.get("scheduled_at", "")))
        if when is None:
            return Response(
                {"detail": "a valid scheduled_at is required"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        refused, checks = self._refuse(broadcast)
        if refused:
            return refused
        broadcast.scheduled_at = when
        broadcast.status = BroadcastStatus.SCHEDULED
        broadcast.status_reason = ""
        broadcast.save(update_fields=["scheduled_at", "status", "status_reason", "updated_at"])
        return Response(_serialize_broadcast(broadcast, detail=True, checks=checks))

    @staticmethod
    def _cancel(broadcast):
        """Cancel before or during a send. Mid-send, the worker stops at its next
        batch; whoever was already mailed stays mailed."""
        if not broadcasts_mod.transition(broadcast, Broadcast.CANCELABLE, BroadcastStatus.CANCELED):
            return Response(
                {"detail": f"a {broadcast.status} broadcast can't be canceled"},
                status=http_status.HTTP_409_CONFLICT,
            )
        return Response(_serialize_broadcast(broadcast, detail=True))

    @staticmethod
    def _pause(request, broadcast):
        who = actor_email(request) or "an admin"
        if not broadcasts_mod.pause(broadcast, f"Paused by {who}."):
            return Response(
                {"detail": "only a broadcast that is sending can be paused"},
                status=http_status.HTTP_409_CONFLICT,
            )
        return Response(_serialize_broadcast(broadcast, detail=True))

    @staticmethod
    def _resume(request, broadcast):
        if broadcast.status != BroadcastStatus.PAUSED:
            return Response(
                {"detail": "only a paused broadcast can be resumed"},
                status=http_status.HTTP_409_CONFLICT,
            )
        override = bool(request.data.get("override_guardrail"))
        reason = health.broadcast_breach(broadcast)
        if reason and not override:
            return Response(
                {
                    "detail": f"{reason}. Resume anyway to send past the guardrail.",
                    "needs_override": True,
                },
                status=http_status.HTTP_409_CONFLICT,
            )
        broadcasts_mod.start_send(broadcast, override_guardrail=bool(reason))
        return Response(_serialize_broadcast(broadcast, detail=True))

    @staticmethod
    def _test(request, broadcast):
        profile = UserProfile.objects.filter(
            supabase_uid=getattr(request.user, "username", "")
        ).first()
        if profile is None:
            return Response(
                {"detail": "a test send goes to your own account; none was found"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        ok = broadcasts_mod.send_test(broadcast, profile)
        if not ok:
            return Response(
                {"detail": "test send failed (no deliverable address or content, or sending disabled)"},
                status=http_status.HTTP_409_CONFLICT,
            )
        return Response(
            {"ok": True, "sent_to": profile.email, **_serialize_broadcast(broadcast, detail=True)}
        )


class AdminAudiencePreviewView(AdminNotAudited, APIView):
    """Count the readers an audience filter would target (compose-time preview).

    Super-admin-only (see AdminEmailMetricsView)."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only: counts an audience filter and writes nothing (POST only because the filter is a JSON body)."

    def post(self, request):
        audience = request.data.get("audience") or {}
        if not isinstance(audience, dict):
            return Response(
                {"detail": "audience must be an object"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        return Response({"count": audience_mod.count(audience)})


# --- One reader's email: history, and writing to them directly ----------------


class AdminReaderEmailsView(AdminAudited, APIView):
    """GET one reader's email history and consent state; POST a direct email to
    them (emails/direct.py).

    Super-admin-only, like the rest of the Emails section (see
    AdminEmailMetricsView): writing to a reader is outbound email."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_DIRECT

    def audit_entry(self, request, response):
        return (
            f"user:{self.kwargs.get('uid')}",
            {"subject": str(request.data.get("subject", ""))[:200]},
        )

    @staticmethod
    def _profile(uid):
        return UserProfile.objects.filter(supabase_uid=uid).first()

    @staticmethod
    def _state(profile) -> dict:
        subscription = EmailSubscription.objects.filter(profile=profile).first()
        return {
            "blocked_reason": subscription.block_reason() if subscription else None,
            "messages": history_mod.history(profile),
        }

    def get(self, request, uid):
        profile = self._profile(uid)
        if profile is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        return Response(self._state(profile))

    def post(self, request, uid):
        profile = self._profile(uid)
        if profile is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        try:
            message = direct_mod.send_direct(
                profile, request.data, sent_by=actor_email(request)
            )
        except direct_mod.DirectEmailError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        if message.status != SendStatus.SENT:
            # Recorded (it shows in the history) but not delivered: sending off,
            # review-mode allowlist, or a provider error. Not a success.
            return Response(
                {"detail": f"Not sent: {message.error or message.status}.", **self._state(profile)},
                status=http_status.HTTP_409_CONFLICT,
            )
        return Response({"ok": True, **self._state(profile)}, status=http_status.HTTP_201_CREATED)
