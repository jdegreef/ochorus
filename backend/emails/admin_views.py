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
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from .models import (
    Broadcast,
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


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminEmailMetricsView(APIView):
    """Open/click/bounce rollups per lifecycle step and per broadcast."""

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
