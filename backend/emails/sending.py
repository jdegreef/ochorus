"""Deliver one rendered email, once, and record what happened.

This is the choke point every send goes through. It enforces the two invariants
the whole system leans on: **idempotency** (a unique key means a lifecycle step
is delivered at most once, however often the sweep runs) and **suppression /
consent** (a suppressed or opted-out reader is never contacted). It also attaches
the one-click ``List-Unsubscribe`` headers to every message.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from . import links
from .models import EmailMessage, SendStatus
from .rendering import RenderedEmail
from .resend_client import ResendError, send_email

logger = logging.getLogger(__name__)


def emails_enabled() -> bool:
    """Whether sends actually go out. Off by default so nothing leaves a dev box
    or CI; flip ``EMAIL_ENABLED`` on in production once the domain is verified.

    Also requires the base URLs, because an email whose unsubscribe link and CTA
    are relative is broken and its ``List-Unsubscribe`` header is invalid. If
    sending is switched on but a base URL is missing, refuse to send (recorded as
    SKIPPED) and warn, rather than mail dead links."""
    if not (settings.EMAIL_ENABLED and settings.RESEND_API_KEY):
        return False
    if not (settings.API_PUBLIC_URL and settings.PUBLIC_SITE_URL):
        logger.warning(
            "EMAIL_ENABLED is on but API_PUBLIC_URL/PUBLIC_SITE_URL is unset; "
            "not sending (links would be relative)."
        )
        return False
    return True


def unsubscribe_headers(subscription) -> dict:
    """RFC 8058 one-click unsubscribe headers — the inbox's native button."""
    url = links.unsubscribe_url(subscription.unsubscribe_token)
    return {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def deliver(
    *,
    profile,
    subscription,
    kind: str,
    rendered: RenderedEmail,
    idempotency_key: str,
    to_email: str,
    locale: str,
    lifecycle_step: str = "",
    broadcast=None,
) -> EmailMessage:
    """Send ``rendered`` to ``to_email`` at most once, keyed by ``idempotency_key``.

    The message row is created on first attempt and reused thereafter, so a
    retry after a transient failure re-sends, while an already-sent message is
    returned untouched. When email is disabled the row is recorded as SKIPPED —
    the pipeline is exercised without contacting Resend.
    """
    message, created = EmailMessage.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "recipient": profile,
            "to_email": to_email,
            "kind": kind,
            "lifecycle_step": lifecycle_step,
            "broadcast": broadcast,
            "locale": locale,
            "subject": rendered.subject[:300],
        },
    )
    if not created and message.status == SendStatus.SENT:
        return message

    if not emails_enabled():
        message.status = SendStatus.SKIPPED
        message.error = "email sending disabled"
        message.save(update_fields=["status", "error"])
        return message

    try:
        provider_id = send_email(
            to=to_email,
            subject=rendered.subject,
            html=rendered.html,
            headers=unsubscribe_headers(subscription),
            idempotency_key=idempotency_key,
        )
    except ResendError as exc:
        logger.warning("send failed for %s: %s", idempotency_key, exc)
        message.status = SendStatus.FAILED
        message.error = str(exc)[:300]
        message.save(update_fields=["status", "error"])
        return message

    message.provider_message_id = provider_id
    message.status = SendStatus.SENT
    message.sent_at = timezone.now()
    message.error = ""
    message.save(
        update_fields=["provider_message_id", "status", "sent_at", "error"]
    )
    return message
