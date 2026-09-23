"""Lifecycle emails — automated, triggered by reader state.

A small ordered registry of steps, each with a due-predicate over a per-profile
context. The sweep (:func:`candidate_profiles` → :func:`send_due`) sends **one**
lifecycle email per reader per run — the earliest unsent step that is due — so
the drip paces itself and an account that somehow missed earlier steps isn't hit
with all of them at once. Every step is send-once (the unique idempotency key).

Sending is kept out of the sign-in request path: the sweep runs from
``manage.py send_lifecycle_emails`` (Phase 1's Render cron), so nothing adds
latency to authentication and a failed send simply retries next pass.

The sequence:

* ``welcome``   — immediately (first sweep after sign-up).
* ``pick_plan`` — day 2+, only if the reader hasn't started a reading plan.
* ``classic``   — day 4+.
* ``comeback``  — the reader has been seen but has gone quiet 7+ days.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import UserProfile
from reading.models import PlanProgress

from .models import (
    EmailKind,
    EmailMessage,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import render_step
from .sending import deliver

WELCOME_STEP = "welcome"
PLAN_STEP = "pick_plan"
CLASSIC_STEP = "classic"
COMEBACK_STEP = "comeback"

# Day thresholds for the onboarding steps, and the inactivity window that
# triggers re-engagement. Module constants for now; easy to move to settings.
_PLAN_AFTER_DAYS = 2
_CLASSIC_AFTER_DAYS = 4
_COMEBACK_AFTER_DAYS = 7

# Never send a reader two lifecycle emails closer together than this, whatever
# the cron cadence or their account age. Without it, a back-dated account newly
# in the cohort (e.g. the cutoff moved) would get every due step in consecutive
# 15-minute runs; this keeps the drip to at most one email a day.
_MIN_GAP = timedelta(hours=20)


@dataclass(frozen=True)
class StepContext:
    """The facts a step's due-predicate needs, fetched once per profile."""

    age_days: float
    has_plan: bool
    days_since_seen: float | None


@dataclass(frozen=True)
class LifecycleStep:
    name: str
    due: Callable[[StepContext], bool]


#: Ordered — the sweep sends the first unsent step whose predicate is true.
STEPS: list[LifecycleStep] = [
    LifecycleStep(WELCOME_STEP, lambda c: True),
    LifecycleStep(
        PLAN_STEP, lambda c: c.age_days >= _PLAN_AFTER_DAYS and not c.has_plan
    ),
    LifecycleStep(CLASSIC_STEP, lambda c: c.age_days >= _CLASSIC_AFTER_DAYS),
    LifecycleStep(
        COMEBACK_STEP,
        lambda c: c.days_since_seen is not None
        and c.days_since_seen >= _COMEBACK_AFTER_DAYS,
    ),
]


def welcome_key(profile) -> str:
    return idempotency_key(EmailKind.LIFECYCLE, WELCOME_STEP, profile)


def _build_context(profile, now: datetime) -> StepContext:
    age_days = (now - profile.created_at).total_seconds() / 86400
    last_seen = profile.last_seen_at
    days_since_seen = (
        (now - last_seen).total_seconds() / 86400 if last_seen is not None else None
    )
    return StepContext(
        age_days=age_days,
        has_plan=PlanProgress.objects.filter(profile=profile).exists(),
        days_since_seen=days_since_seen,
    )


def _sent_steps(profile) -> set[str]:
    return set(
        EmailMessage.objects.filter(
            recipient=profile, kind=EmailKind.LIFECYCLE, status=SendStatus.SENT
        ).values_list("lifecycle_step", flat=True)
    )


def _last_lifecycle_sent_at(profile):
    return (
        EmailMessage.objects.filter(
            recipient=profile, kind=EmailKind.LIFECYCLE, status=SendStatus.SENT
        )
        .order_by("-sent_at")
        .values_list("sent_at", flat=True)
        .first()
    )


def due_step(profile, now: datetime) -> LifecycleStep | None:
    """The earliest unsent step whose predicate is true for ``profile``."""
    ctx = _build_context(profile, now)
    sent = _sent_steps(profile)
    for step in STEPS:
        if step.name in sent:
            continue
        if step.due(ctx):
            return step
    return None


def _send(profile, subscription, step_name: str) -> EmailMessage | None:
    to_email = verified_email(profile)
    if not to_email:
        return None
    rendered = render_step(step_name, profile, subscription)
    return deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=idempotency_key(EmailKind.LIFECYCLE, step_name, profile),
        to_email=to_email,
        locale=(profile.locale or "en"),
        lifecycle_step=step_name,
    )


def send_due(profile) -> EmailMessage | None:
    """Send the one lifecycle email this reader is due, if any.

    Returns the message, or ``None`` when the reader is opted out / suppressed,
    has no due step, or has no deliverable address.
    """
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants(EmailKind.LIFECYCLE):
        return None
    now = timezone.now()
    last_sent = _last_lifecycle_sent_at(profile)
    if last_sent is not None and now - last_sent < _MIN_GAP:
        return None
    step = due_step(profile, now)
    if step is None:
        return None
    return _send(profile, subscription, step.name)


def send_welcome(profile) -> EmailMessage | None:
    """Send the welcome step specifically, once. Retained as a focused entry
    point (and for the sign-up path); the sweep reaches it via :func:`send_due`."""
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    existing = EmailMessage.objects.filter(idempotency_key=welcome_key(profile)).first()
    if existing and existing.status == SendStatus.SENT:
        return existing
    if not subscription.wants(EmailKind.LIFECYCLE):
        return None
    return _send(profile, subscription, WELCOME_STEP)


def candidate_profiles(cutoff):
    """Profiles in scope for the sweep: accounts created on/after ``cutoff``.

    The cutoff is the rollout cohort gate — it stops a first run from mailing
    the entire back catalogue (onboarding *and* re-engagement). Fully-processed
    profiles stay in the set but cost only a due-step evaluation (which finds
    nothing) — a high-water mark is a fair Phase 2 optimization if the cohort
    grows large.
    """
    return UserProfile.objects.filter(created_at__gte=cutoff).order_by("created_at")
