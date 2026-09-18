"""Lifecycle emails — automated, triggered by reader state.

Phase 0 ships one step, the **welcome**. It is sent to a reader who has no
*sent* welcome yet, is opted in, and has a deliverable address. Detection and
sending are deliberately kept out of the sign-in request path: a sweep
(:func:`profiles_awaiting_welcome` → :func:`send_welcome`) runs from a
management command, so nothing adds latency to authentication and a failed send
is simply retried on the next pass. Phase 1's cron calls the same command.
"""

from __future__ import annotations

from accounts.models import UserProfile

from .models import (
    EmailKind,
    EmailMessage,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import render_welcome
from .sending import deliver

WELCOME_STEP = "welcome"


def welcome_key(profile) -> str:
    return idempotency_key(EmailKind.LIFECYCLE, WELCOME_STEP, profile)


def send_welcome(profile) -> EmailMessage | None:
    """Send the welcome to one reader, once. Returns the message, or ``None``
    when the reader is not eligible (opted out / suppressed) or has no
    deliverable address."""
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)

    existing = EmailMessage.objects.filter(idempotency_key=welcome_key(profile)).first()
    if existing and existing.status == SendStatus.SENT:
        return existing

    if not subscription.wants(EmailKind.LIFECYCLE):
        return None

    to_email = verified_email(profile)
    if not to_email:
        return None

    rendered = render_welcome(profile, subscription)
    return deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=welcome_key(profile),
        to_email=to_email,
        locale=(profile.locale or "en"),
        lifecycle_step=WELCOME_STEP,
    )


def profiles_awaiting_welcome(cutoff):
    """Profiles created on/after ``cutoff`` that have no *sent* welcome yet.

    Gating on ``cutoff`` is what stops a first run from blasting the entire
    back catalogue — only recently created accounts are in scope. Rows with a
    failed or skipped welcome are still returned, so they retry once sending is
    enabled.
    """
    welcomed = EmailMessage.objects.filter(
        lifecycle_step=WELCOME_STEP, status=SendStatus.SENT
    ).values_list("recipient_id", flat=True)
    return (
        UserProfile.objects.filter(created_at__gte=cutoff)
        .exclude(pk__in=welcomed)
        .order_by("created_at")
    )
