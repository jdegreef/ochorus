"""Shared scaffolding for the event-triggered email sweeps.

Two emails now fire when a reader *finishes a book* — the finish-the-series nudge
(:mod:`emails.series_nudge`) and the reading milestones (:mod:`emails.milestones`)
— so the parts they share live here rather than being copied a third time: the
candidate query (who finished a book lately), the 20h min-gap gate (an invariant
of the LIFECYCLE kind, so one reader never gets two LIFECYCLE emails a day), and
the send/skip/fail tally every sweep command prints.

Each sweep keeps its own *pick* logic (what to recommend / celebrate) and its own
consent stream; only the mechanical shell is shared.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from django.utils import timezone

from accounts.models import UserProfile
from reading.models import ReadingProgress, WorkKind

from .lifecycle import MIN_GAP, last_lifecycle_sent_at
from .models import EmailKind, EmailMessage, EmailSubscription, SendStatus


def recent_book_finishers(cutoff):
    """Profiles who finished a book on/after ``cutoff`` — the candidate set for any
    email triggered by finishing a book. Idempotency keeps a given email from
    repeating, so the window only bounds the scan; it doesn't decide who's new."""
    finisher_ids = (
        ReadingProgress.objects.filter(
            kind=WorkKind.BOOK, finished_at__isnull=False, finished_at__gte=cutoff
        )
        .values_list("profile_id", flat=True)
        .distinct()
    )
    return UserProfile.objects.filter(id__in=finisher_ids).order_by("id")


def blocked_by_min_gap(profile, now: datetime) -> bool:
    """Whether a LIFECYCLE email went out too recently to send another — the 20h
    gap shared across every LIFECYCLE sender (drip steps and event sweeps alike),
    so the day's one slot isn't double-filled."""
    last_sent = last_lifecycle_sent_at(profile)
    return last_sent is not None and now - last_sent < MIN_GAP


def eligible_subscription(profile, lifecycle_step: str) -> EmailSubscription | None:
    """The reader's subscription when they may receive a LIFECYCLE email of this
    step right now — consent for the step's stream and the 20h gap both pass —
    else ``None``. The shared front gate of every event sweep's ``send_due``."""
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants(EmailKind.LIFECYCLE, lifecycle_step):
        return None
    if blocked_by_min_gap(profile, timezone.now()):
        return None
    return subscription


def run_sweep(candidates, send: Callable[[object], EmailMessage | None]) -> tuple[int, int, int]:
    """Apply ``send`` to each candidate and tally (sent, skipped, failed)."""
    sent = skipped = failed = 0
    for profile in candidates:
        message = send(profile)
        if message is None:
            skipped += 1
        elif message.status == SendStatus.SENT:
            sent += 1
        elif message.status == SendStatus.SKIPPED:
            skipped += 1
        else:
            failed += 1
    return sent, skipped, failed
