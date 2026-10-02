"""Send an admin-composed broadcast to its audience — in batches, resumably.

Reuses the same delivery choke point as lifecycle mail, so consent, suppression,
idempotency, and the unsubscribe headers all apply identically. A broadcast is
send-once per recipient (``broadcast:<id>:<profile>``), so re-running a send
never doubles it; a test send uses a throwaway key so it can be repeated.

Sending is a queue, not a request. "Send now" (or a schedule coming due) only
marks the broadcast SENDING; the email cron then walks the audience in profile-pk
order, a batch at a time, paced to ``EMAIL_SEND_RATE`` and bounded by a time
budget per run. Between batches it re-reads the broadcast, so a pause or cancel
from the admin takes effect within one batch, and it checks the bounce/complaint
guardrail (emails/health.py), pausing itself if the send is going badly.
``send_cursor`` keeps its place, so an interrupted send resumes where it
stopped — and a recipient it reaches twice is still mailed once, by the key.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from . import health, preflight
from .audience import resolve
from .models import (
    Broadcast,
    BroadcastStatus,
    EmailKind,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import render_broadcast
from .sending import deliver

logger = logging.getLogger(__name__)

#: Readers fetched and sent per batch. The pause/cancel/guardrail checks run
#: between batches, so this is also the most a pause can overshoot by.
BATCH_SIZE = 50
#: How long a worker's claim on a broadcast lasts without renewal. Renewed every
#: batch; long enough that a slow batch can't lose it, short enough that a
#: crashed worker's send is picked up by the next cron run.
LEASE = timedelta(minutes=5)

def broadcast_key(broadcast, profile) -> str:
    return idempotency_key(EmailKind.BROADCAST, str(broadcast.id), profile)


class _Pacer:
    """Space calls at least ``1/rate`` seconds apart (no-op for rate <= 0)."""

    def __init__(self, rate: float):
        self.interval = 1.0 / rate if rate > 0 else 0.0
        self.next_at = 0.0

    def wait(self) -> None:
        if not self.interval:
            return
        now = time.monotonic()
        if now < self.next_at:
            time.sleep(self.next_at - now)
            now = self.next_at
        self.next_at = now + self.interval


def _send_one(broadcast, profile, subscription, pacer: _Pacer | None = None) -> str:
    """Send the broadcast to one recipient. Returns a tally bucket name."""
    if not subscription.wants(EmailKind.BROADCAST):
        return "skipped"
    to_email = verified_email(profile)
    if not to_email:
        return "skipped"
    rendered = render_broadcast(broadcast, profile, subscription)
    if rendered is None:  # no content in the reader's language (nor a fallback)
        return "skipped"
    if pacer is not None:
        pacer.wait()
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.BROADCAST,
        rendered=rendered,
        idempotency_key=broadcast_key(broadcast, profile),
        to_email=to_email,
        locale=(profile.locale or "en"),
        broadcast=broadcast,
        from_email=broadcast.from_address or None,
    )
    if message.status == SendStatus.SENT:
        return "sent"
    if message.status == SendStatus.SKIPPED:
        return "skipped"
    return "failed"


# --- State transitions --------------------------------------------------------


def transition(broadcast, from_statuses, to_status, **fields) -> bool:
    """Move ``broadcast`` to ``to_status`` only if it is still in one of
    ``from_statuses`` — a compare-and-set, so an admin's pause or cancel and the
    worker's finish can't overwrite each other. Refreshes ``broadcast`` and
    returns whether it moved."""
    n = Broadcast.objects.filter(pk=broadcast.pk, status__in=from_statuses).update(
        status=to_status, updated_at=timezone.now(), **fields
    )
    broadcast.refresh_from_db()
    return n == 1


def start_send(broadcast, *, override_guardrail: bool = False) -> None:
    """Queue ``broadcast`` for the batched sender (the cron picks it up);
    ``override_guardrail`` resumes it past a guardrail pause for good."""
    broadcast.status = BroadcastStatus.SENDING
    broadcast.status_reason = ""
    if broadcast.send_started_at is None:
        broadcast.send_started_at = timezone.now()
    fields = ["status", "status_reason", "send_started_at", "updated_at"]
    if override_guardrail:
        broadcast.guardrail_override = True
        fields.append("guardrail_override")
    broadcast.save(update_fields=fields)


def pause(broadcast, reason: str) -> bool:
    """Stop a SENDING broadcast where it is. Returns whether it was sending."""
    return transition(
        broadcast, [BroadcastStatus.SENDING], BroadcastStatus.PAUSED, status_reason=reason[:200]
    )


def promote_due() -> int:
    """Move scheduled broadcasts whose time has come into the send queue.

    The content checks run again first: a scheduled broadcast can still be
    edited, so the version that passed when it was scheduled may not be the one
    about to go out. One that now fails goes back to DRAFT (editable, and
    reschedulable once fixed) with the reason, instead of being sent.
    """
    due = list(
        Broadcast.objects.filter(
            status=BroadcastStatus.SCHEDULED, scheduled_at__lte=timezone.now()
        ).order_by("scheduled_at")
    )
    for broadcast in due:
        errors = preflight.content_errors(broadcast)
        if errors:
            transition(
                broadcast,
                [BroadcastStatus.SCHEDULED],
                BroadcastStatus.DRAFT,
                status_reason=f"The schedule didn't start: {errors[0]['message']}"[:200],
            )
        else:
            start_send(broadcast)
    return len(due)


def sending_queue():
    """Broadcasts the cron should be working on, oldest first."""
    return Broadcast.objects.filter(status=BroadcastStatus.SENDING).order_by(
        "send_started_at", "pk"
    )


# --- The worker -----------------------------------------------------------------


def _subscriptions_for(profiles) -> dict:
    """``{profile_pk: EmailSubscription}`` for a batch, creating the missing
    ones — two queries a batch instead of one per reader."""
    pks = [p.pk for p in profiles]
    found = EmailSubscription.objects.in_bulk(pks, field_name="profile_id")
    missing = [EmailSubscription(profile=p) for p in profiles if p.pk not in found]
    if missing:
        EmailSubscription.objects.bulk_create(missing, ignore_conflicts=True)
        found = EmailSubscription.objects.in_bulk(pks, field_name="profile_id")
    return found


def _claim(broadcast) -> bool:
    now = timezone.now()
    n = (
        Broadcast.objects.filter(pk=broadcast.pk, status=BroadcastStatus.SENDING)
        .filter(Q(send_lease_until__isnull=True) | Q(send_lease_until__lt=now))
        .update(send_lease_until=now + LEASE)
    )
    return n == 1


def _checkpoint(broadcast) -> None:
    """Persist progress and renew the lease — never touching ``status``, which
    an admin may have changed (pause/cancel) while this batch was sending."""
    Broadcast.objects.filter(pk=broadcast.pk).update(
        send_cursor=broadcast.send_cursor,
        send_tally=broadcast.send_tally,
        send_lease_until=timezone.now() + LEASE,
    )


def run_send(broadcast, *, deadline: float | None = None, rate: float | None = None) -> dict:
    """Work through a SENDING broadcast's audience until it is done, paused,
    canceled, or ``deadline`` (a ``time.monotonic()`` value) passes.

    Returns this run's tally. Does nothing (an empty tally) if the broadcast
    isn't SENDING or another worker holds it.
    """
    run = {"sent": 0, "skipped": 0, "failed": 0}
    if not _claim(broadcast):
        return run
    pacer = _Pacer(settings.EMAIL_SEND_RATE if rate is None else rate)
    try:
        while True:
            current = (
                Broadcast.objects.filter(pk=broadcast.pk)
                .values("status", "guardrail_override")
                .first()
            )
            if current is None or current["status"] != BroadcastStatus.SENDING:
                break
            broadcast.guardrail_override = current["guardrail_override"]
            reason = health.broadcast_breach(broadcast)
            if reason:
                logger.warning("broadcast %s paused by guardrail: %s", broadcast.pk, reason)
                pause(broadcast, f"Paused automatically: {reason}.")
                break
            if deadline is not None and time.monotonic() >= deadline:
                break

            batch = list(
                resolve(broadcast.audience)
                .filter(pk__gt=broadcast.send_cursor)
                .order_by("pk")[:BATCH_SIZE]
            )
            if not batch:
                transition(
                    broadcast,
                    [BroadcastStatus.SENDING],
                    BroadcastStatus.SENT,
                    send_finished_at=timezone.now(),
                )
                break

            tally = broadcast.progress
            subscriptions = _subscriptions_for(batch)
            for profile in batch:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                subscription = subscriptions[profile.pk]
                try:
                    bucket = _send_one(broadcast, profile, subscription, pacer)
                except Exception:
                    # One recipient's failure (a render error, a provider hiccup)
                    # is a "failed" tally, not an abort that strands the rest.
                    logger.exception(
                        "broadcast %s: send to profile %s failed", broadcast.pk, profile.pk
                    )
                    bucket = "failed"
                run[bucket] += 1
                tally[bucket] += 1
                broadcast.send_cursor = profile.pk
            broadcast.send_tally = tally
            _checkpoint(broadcast)
    finally:
        Broadcast.objects.filter(pk=broadcast.pk).update(send_lease_until=None)
    return run


def send_broadcast(broadcast) -> dict:
    """Send ``broadcast`` through to the end in this process, ignoring the time
    budget — queuing it first unless it is already in the queue. For the
    ``send_due_broadcasts --id`` command and tests; the admin queues instead
    (:func:`start_send`) and lets the cron do the work."""
    if broadcast.status != BroadcastStatus.SENDING:
        start_send(broadcast)
    return run_send(broadcast)


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
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.BROADCAST,
        rendered=rendered,
        # A fresh key per test, so a test can be repeated.
        idempotency_key=idempotency_key(
            EmailKind.BROADCAST, f"{broadcast.id}-test-{uuid.uuid4().hex}", profile
        ),
        to_email=to_email,
        locale=(profile.locale or "en"),
        broadcast=broadcast,
        from_email=broadcast.from_address or None,
        is_test=True,
    )
    if message.status != SendStatus.SENT:
        return False
    # Remember what was tested, so the pre-send checks can say whether the copy
    # has changed since. A queryset update: ``updated_at`` means "edited".
    broadcast.tested_digest = broadcast.content_digest()
    Broadcast.objects.filter(pk=broadcast.pk).update(tested_digest=broadcast.tested_digest)
    return True
