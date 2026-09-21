"""Admin dashboard API — email campaign metrics.

Aggregate-only: sent / open / click / bounce rollups per lifecycle step and per
broadcast, plus subscription health. No recipient identities — this is the
open/click/bounce dashboard the build plan puts in the Ochorus admin (rather
than Resend's). Open and click *rates* are computed here from the mirrored
events, exactly as the plan intends.

Rate conventions:
* ``delivered`` = sent − hard bounces (robust even if Resend "delivered" events
  aren't enabled), floored at 0.
* ``open_rate`` / ``click_rate`` = distinct messages with an open / click, over
  ``delivered``. Opens are undercounted by inbox privacy proxies, so treat click
  rate as the reliable signal (surfaced in the UI).
* ``bounce_rate`` / ``complaint_rate`` = over ``sent``.
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
from library.audit import AdminAudited, AdminNotAudited
from library.models import AdminAction

from . import audience as audience_mod
from . import broadcasts as broadcasts_mod
from .models import (
    Broadcast,
    BroadcastStatus,
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    SendStatus,
)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _metrics(sent: int, counts: dict[str, int]) -> dict:
    """Assemble one row's numbers from its sent count and per-event-type
    distinct-message counts."""
    bounces = counts.get(EventType.BOUNCED, 0)
    complaints = counts.get(EventType.COMPLAINED, 0)
    opens = counts.get(EventType.OPENED, 0)
    clicks = counts.get(EventType.CLICKED, 0)
    delivered = max(sent - bounces, 0)
    return {
        "sent": sent,
        "delivered": delivered,
        "opens": opens,
        "clicks": clicks,
        "bounces": bounces,
        "complaints": complaints,
        "open_rate": _rate(opens, delivered),
        "click_rate": _rate(clicks, delivered),
        "bounce_rate": _rate(bounces, sent),
        "complaint_rate": _rate(complaints, sent),
    }


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
            EmailMessage.objects.filter(kind=kind, status=SendStatus.SENT)
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
                message__kind=kind, message__status=SendStatus.SENT
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
            row = _metrics(sent_counts.get(key, 0), event_counts.get(key, {}))
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
        sent = EmailMessage.objects.filter(status=SendStatus.SENT).count()
        counts = {}
        rows = (
            EmailEvent.objects.filter(message__status=SendStatus.SENT)
            .values("type")
            .annotate(n=Count("message_id", distinct=True))
        )
        for row in rows:
            counts[row["type"]] = row["n"]
        overview = _metrics(sent, counts)
        overview["failed"] = EmailMessage.objects.filter(status=SendStatus.FAILED).count()
        return overview

    @staticmethod
    def _subscribers() -> dict:
        return {
            "total": EmailSubscription.objects.count(),
            "newsletter_opt_in": EmailSubscription.objects.filter(
                newsletter_opt_in=True, unsubscribed_all=False, suppressed_at__isnull=True
            ).count(),
            "unsubscribed": EmailSubscription.objects.filter(unsubscribed_all=True).count(),
            "suppressed": EmailSubscription.objects.filter(
                suppressed_at__isnull=False
            ).count(),
        }


# --- Broadcast compose / schedule / send ------------------------------------


def _broadcast_stats(broadcast) -> dict:
    sent = EmailMessage.objects.filter(
        broadcast=broadcast, status=SendStatus.SENT
    ).count()
    counts = {}
    rows = (
        EmailEvent.objects.filter(
            message__broadcast=broadcast, message__status=SendStatus.SENT
        )
        .values("type")
        .annotate(n=Count("message_id", distinct=True))
    )
    for row in rows:
        counts[row["type"]] = row["n"]
    return _metrics(sent, counts)


def _serialize_broadcast(b: Broadcast, *, detail: bool = False) -> dict:
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
        "locales": sorted(set(b.subject) & set(b.content)),
        "audience_count": audience_mod.count(b.audience),
    }
    if detail:
        data["content"] = b.content
        data["stats"] = _broadcast_stats(b)
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
        if broadcast.status in (BroadcastStatus.SENDING, BroadcastStatus.SENT):
            return Response(
                {"detail": "a sent broadcast can't be edited"},
                status=http_status.HTTP_409_CONFLICT,
            )
        _apply_fields(broadcast, request.data)
        broadcast.save()
        return Response(_serialize_broadcast(broadcast, detail=True))

    def delete(self, request, pk):
        broadcast = self._get(pk)
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        if broadcast.status in (BroadcastStatus.SENDING, BroadcastStatus.SENT):
            return Response(
                {"detail": "a sent broadcast can't be deleted"},
                status=http_status.HTTP_409_CONFLICT,
            )
        broadcast.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class AdminBroadcastActionView(AdminAudited, APIView):
    """Act on a broadcast: ``send`` now, ``schedule``, ``cancel``, or ``test``.

    Super-admin-only (see AdminEmailMetricsView)."""

    permission_classes = [IsAdminEmail]

    _ACTION_AUDIT = {
        "send": AdminAction.Action.BROADCAST_SEND,
        "schedule": AdminAction.Action.BROADCAST_SCHEDULE,
        "cancel": AdminAction.Action.BROADCAST_CANCEL,
        "test": AdminAction.Action.BROADCAST_TEST,
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
        return Response(
            {"detail": f"unknown action {action!r}"},
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _sendable(broadcast) -> str | None:
        if not (set(broadcast.subject) & set(broadcast.content)):
            return "broadcast has no subject/content in any language"
        if broadcast.status in (BroadcastStatus.SENDING, BroadcastStatus.SENT):
            return "broadcast has already been sent"
        return None

    def _send(self, broadcast):
        problem = self._sendable(broadcast)
        if problem:
            return Response({"detail": problem}, status=http_status.HTTP_409_CONFLICT)
        tally = broadcasts_mod.send_broadcast(broadcast)
        return Response({"tally": tally, **_serialize_broadcast(broadcast, detail=True)})

    def _schedule(self, request, broadcast):
        problem = self._sendable(broadcast)
        if problem:
            return Response({"detail": problem}, status=http_status.HTTP_409_CONFLICT)
        when = parse_datetime(str(request.data.get("scheduled_at", "")))
        if when is None:
            return Response(
                {"detail": "a valid scheduled_at is required"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        broadcast.scheduled_at = when
        broadcast.status = BroadcastStatus.SCHEDULED
        broadcast.save(update_fields=["scheduled_at", "status", "updated_at"])
        return Response(_serialize_broadcast(broadcast, detail=True))

    def _cancel(self, broadcast):
        if broadcast.status not in (BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED):
            return Response(
                {"detail": "only a draft or scheduled broadcast can be canceled"},
                status=http_status.HTTP_409_CONFLICT,
            )
        broadcast.status = BroadcastStatus.CANCELED
        broadcast.save(update_fields=["status", "updated_at"])
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
        return Response({"ok": True, "sent_to": profile.email})


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
