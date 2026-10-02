"""Delivery numbers and deliverability health — one owner for both.

:func:`metrics` is the single definition of sent / delivered / open / click /
bounce / complaint counts and rates over a set of messages; the admin dashboard
reads it, and so does the guardrail, so the number that pauses a send is the
number the admin sees. On top of it, :func:`breach` is the guardrail: the
batched broadcast send pauses itself when its own rates cross the line, and the
pre-send checks warn when the sender's recent rates already have.

Conventions (as the dashboard has always shown them):

* Only real sends count: SENT messages, never a broadcast's test sends.
* ``delivered`` = sent − hard bounces (robust even if Resend "delivered" events
  aren't enabled), floored at 0.
* ``open_rate`` / ``click_rate`` = distinct messages with an open / click, over
  ``delivered``. Opens are undercounted by inbox privacy proxies.
* ``bounce_rate`` / ``complaint_rate`` = over ``sent``.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .models import EmailEvent, EmailMessage, EventType, SendStatus


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def real_sends(messages):
    """The messages that count: sent for real, tests excluded."""
    return messages.filter(status=SendStatus.SENT, is_test=False)


def event_counts(messages) -> dict[str, int]:
    """``{event_type: distinct messages with it}`` over ``messages``."""
    return dict(
        EmailEvent.objects.filter(message__in=messages)
        .values_list("type")
        .annotate(n=Count("message_id", distinct=True))
    )


def assemble(sent: int, counts: dict[str, int]) -> dict:
    """One row's numbers from its sent count and per-event-type counts."""
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


def metrics(messages) -> dict:
    """The full set of numbers for a queryset of :class:`EmailMessage`."""
    sent_qs = real_sends(messages)
    sent = sent_qs.count()
    return assemble(sent, event_counts(sent_qs) if sent else {})


def breach(m: dict) -> str | None:
    """Why these numbers are over the guardrail, or ``None`` when they're fine
    (or too few messages have gone out to judge)."""
    if m["sent"] < settings.EMAIL_GUARDRAIL_MIN_SENT:
        return None
    if m["complaint_rate"] > settings.EMAIL_GUARDRAIL_COMPLAINT_RATE:
        return (
            f"Spam-complaint rate {m['complaint_rate']:.2%} is over the "
            f"{settings.EMAIL_GUARDRAIL_COMPLAINT_RATE:.2%} limit"
        )
    if m["bounce_rate"] > settings.EMAIL_GUARDRAIL_BOUNCE_RATE:
        return (
            f"Bounce rate {m['bounce_rate']:.1%} is over the "
            f"{settings.EMAIL_GUARDRAIL_BOUNCE_RATE:.1%} limit"
        )
    return None


def _judge(messages) -> str | None:
    # Count first: below the minimum there's nothing to judge, and the events
    # aggregate (the expensive half) is skipped.
    sent_qs = real_sends(messages)
    sent = sent_qs.count()
    if sent < settings.EMAIL_GUARDRAIL_MIN_SENT:
        return None
    return breach(assemble(sent, event_counts(sent_qs)))


def broadcast_breach(broadcast) -> str | None:
    """The guardrail verdict on one broadcast's own sends so far."""
    if broadcast.guardrail_override:
        return None
    return _judge(EmailMessage.objects.filter(broadcast=broadcast))


def sender_breach(days: int = 30) -> str | None:
    """The guardrail verdict on everything sent in the last ``days`` days."""
    since = timezone.now() - timedelta(days=days)
    return _judge(EmailMessage.objects.filter(sent_at__gte=since))
