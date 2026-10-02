"""Reading-milestone celebrations — "you've finished N books".

An event-triggered email, like the series nudge: when a reader's count of
finished books reaches a milestone, congratulate them once. The very first
completion is already covered by the finish-your-first-book drip step, so
milestones start at 3.

Only the HIGHEST milestone reached is celebrated — a reader who races past
several at once gets the top one, not a backlog — and each milestone sends once
ever (the idempotency key carries the number). Shares the finisher candidate
query and the 20h min-gap with the series nudge (:mod:`emails.sweeps`); its own
"milestones" preference stream, so it can be silenced on its own.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from reading.models import ReadingProgress, WorkKind

from .models import (
    EmailKind,
    EmailMessage,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import email_language, render_milestone
from .sending import deliver
from .sweeps import blocked_by_min_gap

#: The lifecycle_step recorded on the message (groups the metric); the per-level
#: idempotency discriminator is ``milestone:<n>``.
MILESTONE_STEP = "milestone"

#: Finished-book counts worth marking. 1 and 2 are left to the finish-first-book
#: drip step; a reader who passes several at once gets only the highest.
MILESTONES: tuple[int, ...] = (3, 5, 10, 25, 50, 100)

DEFAULT_LOOKBACK_DAYS = 30


def finished_book_count(profile) -> int:
    return ReadingProgress.objects.filter(
        profile=profile, kind=WorkKind.BOOK, finished_at__isnull=False
    ).count()


def _milestone_sent(profile, milestone: int) -> bool:
    key = idempotency_key(EmailKind.LIFECYCLE, f"{MILESTONE_STEP}:{milestone}", profile)
    return EmailMessage.objects.filter(
        idempotency_key=key, status=SendStatus.SENT
    ).exists()


def due_milestone(profile) -> int | None:
    """The milestone to celebrate now, or ``None``.

    The highest milestone the reader has reached and not yet been congratulated
    for. Lower ones they blew past are not back-filled: a reader who jumps from 2
    to 6 books gets "5", never "3" after it.
    """
    count = finished_book_count(profile)
    reached = [m for m in MILESTONES if m <= count]
    if not reached:
        return None
    milestone = max(reached)
    return None if _milestone_sent(profile, milestone) else milestone


def _send(profile, subscription, milestone: int) -> EmailMessage | None:
    to_email = verified_email(profile)
    if not to_email:
        return None
    rendered = render_milestone(profile, subscription, milestone=milestone)
    return deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=idempotency_key(
            EmailKind.LIFECYCLE, f"{MILESTONE_STEP}:{milestone}", profile
        ),
        to_email=to_email,
        locale=email_language(profile, subscription),
        lifecycle_step=MILESTONE_STEP,
    )


def send_due(profile) -> EmailMessage | None:
    """Send the milestone card this reader is due, if any.

    ``None`` when opted out / suppressed, mailed too recently, below the first
    milestone (or already congratulated for the highest reached), or has no
    deliverable address.
    """
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants(EmailKind.LIFECYCLE, MILESTONE_STEP):
        return None
    if blocked_by_min_gap(profile, timezone.now()):
        return None
    milestone = due_milestone(profile)
    if milestone is None:
        return None
    return _send(profile, subscription, milestone)


def lookback_cutoff():
    """The default 'finished since' cutoff from settings (days before now)."""
    days = getattr(settings, "EMAIL_MILESTONE_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS)
    return timezone.now() - timedelta(days=days)
