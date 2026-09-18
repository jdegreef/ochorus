"""The email programme's data — sends, events, consent, and campaigns.

Four tables carry the whole system (see docs/email-system-build-plan):

* :class:`EmailSubscription` — one row per reader; consent + suppression.
* :class:`Broadcast` — an admin-composed campaign (Phase 2; the row exists now
  so the foundation is whole).
* :class:`EmailMessage` — one row per (email × recipient); the idempotency key
  is what makes a lifecycle step send exactly once.
* :class:`EmailEvent` — one row per provider webhook (open/click/bounce/…).

Ochorus owns these numbers: Resend does the sending and the tracking mechanics,
but every event is mirrored here so the admin never depends on Resend's
dashboard. Open/click *rates* are derived at read time from the events, never
stored twice.
"""

from __future__ import annotations

import secrets

from django.db import models
from django.utils import timezone


def _new_token() -> str:
    """An unguessable, URL-safe unsubscribe token stored per subscription.

    Random rather than a signed profile id so a token can be rotated (issue a
    new one) without changing how the endpoint resolves it — a plain lookup, no
    secret to verify.
    """
    return secrets.token_urlsafe(32)


class EmailKind(models.TextChoices):
    LIFECYCLE = "lifecycle", "Lifecycle"
    BROADCAST = "broadcast", "Broadcast"


class SendStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class BroadcastStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    SENDING = "sending", "Sending"
    SENT = "sent", "Sent"
    CANCELED = "canceled", "Canceled"


class EventType(models.TextChoices):
    """The Resend webhook event types we record. Stored as the bare noun (the
    part after ``email.``) so ``email.opened`` lands as ``opened``."""

    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    DELIVERY_DELAYED = "delivery_delayed", "Delivery delayed"
    OPENED = "opened", "Opened"
    CLICKED = "clicked", "Clicked"
    BOUNCED = "bounced", "Bounced"
    COMPLAINED = "complained", "Complained"
    FAILED = "failed", "Failed"


#: Events that mean "never mail this address again" — they set ``suppressed_at``.
SUPPRESSING_EVENTS = frozenset({EventType.BOUNCED, EventType.COMPLAINED})


class EmailSubscription(models.Model):
    """A reader's email consent and suppression state — one row per profile.

    Consent posture is **opt-out**: a new subscription is opted in to both
    lifecycle and newsletter email (see the build plan's "key decisions"). A
    reader silences everything with one click via :attr:`unsubscribe_token`;
    a hard bounce or spam complaint sets :attr:`suppressed_at` automatically and
    no further mail is sent, whatever the opt-in flags say.
    """

    profile = models.OneToOneField(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="email_subscription",
    )
    # Opt-out defaults: subscribed until the reader says otherwise.
    lifecycle_opt_in = models.BooleanField(default=True)
    newsletter_opt_in = models.BooleanField(default=True)
    # The master off switch (the footer's one-click unsubscribe): stops
    # everything, lifecycle included.
    unsubscribed_all = models.BooleanField(default=False)
    # Set by a hard bounce or complaint; a suppressed address is never mailed.
    suppressed_at = models.DateTimeField(null=True, blank=True)
    suppression_reason = models.CharField(max_length=40, blank=True)

    unsubscribe_token = models.CharField(
        max_length=64, unique=True, default=_new_token, editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - repr only
        return f"subscription<{self.profile_id}>"

    @property
    def is_suppressed(self) -> bool:
        return self.suppressed_at is not None

    def wants(self, kind: str) -> bool:
        """Whether the reader will receive an email of ``kind`` right now.

        Suppression and the master off switch block everything; otherwise the
        per-class opt-in applies. Broadcasts obey ``newsletter_opt_in``; every
        lifecycle email obeys ``lifecycle_opt_in``.
        """
        if self.is_suppressed or self.unsubscribed_all:
            return False
        if kind == EmailKind.BROADCAST:
            return self.newsletter_opt_in
        return self.lifecycle_opt_in

    def suppress(self, reason: str) -> None:
        self.suppressed_at = timezone.now()
        self.suppression_reason = (reason or "")[:40]
        self.save(update_fields=["suppressed_at", "suppression_reason", "updated_at"])

    def unsubscribe(self) -> None:
        """The one-click footer action: turn everything off. Idempotent."""
        if not self.unsubscribed_all:
            self.unsubscribed_all = True
            self.save(update_fields=["unsubscribed_all", "updated_at"])


class Broadcast(models.Model):
    """An admin-composed campaign. Subject and body are keyed by locale so one
    campaign carries every language. Sent by the Phase 2 admin surface; the
    model exists now so the four-table foundation is complete and migrations
    don't churn later."""

    name = models.CharField(max_length=200)
    # {locale: "subject"} and {locale: "<html>"}.
    subject = models.JSONField(default=dict)
    body_html = models.JSONField(default=dict)
    # An audience filter, e.g. {"locale": "pt", "no_plan": true}. Interpreted by
    # the Phase 2 audience layer.
    audience = models.JSONField(default=dict, blank=True)
    from_address = models.CharField(max_length=200, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=BroadcastStatus.choices, default=BroadcastStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - repr only
        return f"broadcast<{self.name}>"


def idempotency_key(kind: str, discriminator: str, profile) -> str:
    """The send-once key for an (email × recipient), in ONE place.

    The unique column on :class:`EmailMessage` is the guarantee; this is the
    single owner of its *format*, so a new lifecycle step or the broadcast path
    can't drift the string and silently defeat uniqueness. ``discriminator`` is
    the step name (``"welcome"``) or the broadcast id.
    """
    return f"{kind}:{discriminator}:{profile.pk}"


class EmailMessage(models.Model):
    """One email sent (or attempted) to one recipient.

    The ``idempotency_key`` is the heart of the design: a lifecycle step keys on
    ``lifecycle:<step>:<profile_id>`` so a re-run of the sweep can never send it
    twice, and a broadcast keys on ``broadcast:<id>:<profile_id>``. Subject and
    the address are snapshotted so the record stays truthful even if the
    profile or template later changes.
    """

    recipient = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="email_messages",
    )
    to_email = models.EmailField()
    kind = models.CharField(max_length=20, choices=EmailKind.choices)
    # For lifecycle emails: the step name (e.g. "welcome"). Blank for broadcasts.
    lifecycle_step = models.CharField(max_length=60, blank=True)
    # For broadcasts: the campaign. Null for lifecycle emails.
    broadcast = models.ForeignKey(
        Broadcast,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    locale = models.CharField(max_length=10, default="en")
    subject = models.CharField(max_length=300, blank=True)

    idempotency_key = models.CharField(max_length=200, unique=True)
    provider_message_id = models.CharField(max_length=200, blank=True, db_index=True)
    status = models.CharField(
        max_length=20, choices=SendStatus.choices, default=SendStatus.QUEUED
    )
    error = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "lifecycle_step"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - repr only
        label = self.lifecycle_step or (self.broadcast_id and f"broadcast {self.broadcast_id}")
        return f"message<{label} → {self.to_email}>"


class EmailEvent(models.Model):
    """One provider webhook event for a message.

    ``provider_event_id`` is the webhook's own unique id; together with the
    message and type it dedupes retried deliveries (providers retry). Open and
    click *rates* are computed from these rows at read time — distinct opens over
    deliveries — never stored back onto the message.
    """

    message = models.ForeignKey(
        EmailMessage, on_delete=models.CASCADE, related_name="events"
    )
    type = models.CharField(max_length=30, choices=EventType.choices)
    url = models.TextField(blank=True)  # the clicked link, for click events
    occurred_at = models.DateTimeField()
    provider_event_id = models.CharField(max_length=200, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "type", "provider_event_id"],
                name="uniq_event_message_type_provider",
            ),
        ]
        indexes = [
            models.Index(fields=["message", "type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - repr only
        return f"event<{self.type} {self.message_id}>"
