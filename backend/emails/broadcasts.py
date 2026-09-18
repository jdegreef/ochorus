"""Send an admin-composed broadcast to its audience.

Reuses the same delivery choke point as lifecycle mail, so consent, suppression,
idempotency, and the unsubscribe headers all apply identically. A broadcast is
send-once per recipient (``broadcast:<id>:<profile>``), so re-running a send
never doubles it; a test send uses a throwaway key so it can be repeated.
"""

from __future__ import annotations

from django.utils import timezone

from .audience import resolve
from .models import (
    BroadcastStatus,
    EmailKind,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import render_broadcast
from .sending import deliver


def broadcast_key(broadcast, profile) -> str:
    return idempotency_key(EmailKind.BROADCAST, str(broadcast.id), profile)


def _send_one(broadcast, profile, subscription) -> str:
    """Send the broadcast to one recipient. Returns a tally bucket name."""
    if not subscription.wants(EmailKind.BROADCAST):
        return "skipped"
    to_email = verified_email(profile)
    if not to_email:
        return "skipped"
    rendered = render_broadcast(broadcast, profile, subscription)
    if rendered is None:  # no content in the reader's language (nor a fallback)
        return "skipped"
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.BROADCAST,
        rendered=rendered,
        idempotency_key=broadcast_key(broadcast, profile),
        to_email=to_email,
        locale=(profile.locale or "en"),
        broadcast=broadcast,
    )
    if message.status == SendStatus.SENT:
        return "sent"
    if message.status == SendStatus.SKIPPED:
        return "skipped"
    return "failed"


def send_broadcast(broadcast, *, limit=None) -> dict:
    """Send ``broadcast`` to its whole audience, once each. Returns counts."""
    broadcast.status = BroadcastStatus.SENDING
    broadcast.save(update_fields=["status", "updated_at"])

    audience = resolve(broadcast.audience)
    if limit:
        audience = audience[:limit]

    tally = {"sent": 0, "skipped": 0, "failed": 0}
    # Subscriptions fetched per profile; get_or_create is a single indexed lookup.
    for profile in audience.iterator():
        subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
        tally[_send_one(broadcast, profile, subscription)] += 1

    broadcast.status = BroadcastStatus.SENT
    broadcast.save(update_fields=["status", "updated_at"])
    return tally


def send_test(broadcast, profile) -> bool:
    """Send a one-off preview of ``broadcast`` to ``profile`` (an admin),
    ignoring audience and opt-in. Repeatable — each test is its own row."""
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    to_email = verified_email(profile)
    if not to_email:
        return False
    rendered = render_broadcast(broadcast, profile, subscription)
    if rendered is None:
        return False
    stamp = int(timezone.now().timestamp())
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.BROADCAST,
        rendered=rendered,
        idempotency_key=f"broadcast-test:{broadcast.id}:{profile.pk}:{stamp}",
        to_email=to_email,
        locale=(profile.locale or "en"),
        broadcast=broadcast,
    )
    return message.status == SendStatus.SENT


def due_broadcasts():
    """Scheduled broadcasts whose time has come."""
    from .models import Broadcast

    return Broadcast.objects.filter(
        status=BroadcastStatus.SCHEDULED, scheduled_at__lte=timezone.now()
    ).order_by("scheduled_at")
