"""Deliverability health: bounce and complaint rates, and the guardrail on them.

One owner for "is this sending going badly?", read by two places: the batched
broadcast send (which pauses itself when its own rates cross the line) and the
pre-send checks (which warn when the sender's recent rates already have).

Rates are over messages SENT, counting each message once however many events it
drew — the same convention as the admin metrics.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .models import EmailEvent, EmailMessage, EventType, SendStatus


def rates(messages) -> dict:
    """``sent``, ``bounces``, ``complaints`` and the two rates for a queryset of
    :class:`EmailMessage`."""
    sent_qs = messages.filter(status=SendStatus.SENT)
    sent = sent_qs.count()
    counts = dict(
        EmailEvent.objects.filter(
            message__in=sent_qs, type__in=[EventType.BOUNCED, EventType.COMPLAINED]
        )
        .values_list("type")
        .annotate(n=Count("message_id", distinct=True))
    )
    bounces = counts.get(EventType.BOUNCED, 0)
    complaints = counts.get(EventType.COMPLAINED, 0)
    return {
        "sent": sent,
        "bounces": bounces,
        "complaints": complaints,
        "bounce_rate": bounces / sent if sent else 0.0,
        "complaint_rate": complaints / sent if sent else 0.0,
    }


def breach(r: dict) -> str | None:
    """Why these rates are over the guardrail, or ``None`` when they're fine (or
    too few messages have gone out to judge)."""
    if r["sent"] < settings.EMAIL_GUARDRAIL_MIN_SENT:
        return None
    if r["complaint_rate"] > settings.EMAIL_GUARDRAIL_COMPLAINT_RATE:
        return (
            f"Spam-complaint rate {r['complaint_rate']:.2%} is over the "
            f"{settings.EMAIL_GUARDRAIL_COMPLAINT_RATE:.2%} limit"
        )
    if r["bounce_rate"] > settings.EMAIL_GUARDRAIL_BOUNCE_RATE:
        return (
            f"Bounce rate {r['bounce_rate']:.1%} is over the "
            f"{settings.EMAIL_GUARDRAIL_BOUNCE_RATE:.1%} limit"
        )
    return None


def broadcast_breach(broadcast) -> str | None:
    """The guardrail verdict on one broadcast's own sends so far."""
    if broadcast.guardrail_override:
        return None
    return breach(rates(EmailMessage.objects.filter(broadcast=broadcast)))


def sender_breach(days: int = 30) -> str | None:
    """The guardrail verdict on everything sent in the last ``days`` days."""
    since = timezone.now() - timedelta(days=days)
    return breach(rates(EmailMessage.objects.filter(sent_at__gte=since)))
