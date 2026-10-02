"""One-to-one email: an admin writes to a single reader from the admin.

Goes through the same choke point as every other send (``sending.deliver``), so
the review-mode allowlist, the master switch and the unsubscribe headers apply.
It is not a stream a reader opts into, so the per-stream preferences don't gate
it — but a suppressed address (hard bounce, spam complaint) or a reader who
pressed "unsubscribe from everything" is never written to, from here either.
"""

from __future__ import annotations

import uuid

from .models import EmailKind, EmailMessage, EmailSubscription, SendStatus, idempotency_key
from .preflight import cta_path_problem
from .recipient import verified_email
from .rendering import email_lang, render_direct
from .sending import deliver

#: The fields of the shared structured ``text`` shape an admin can write here.
FIELDS = ("subject", "heading", "greeting", "paragraphs", "cta_label", "cta_path", "signoff", "signature")


class DirectEmailError(ValueError):
    """Why a direct email can't be sent — shown to the admin as is."""


def blocked_reason(subscription) -> str | None:
    """Why this reader can't be written to, or ``None``."""
    if subscription.is_suppressed:
        return (
            "This address is suppressed after a bounce or spam complaint "
            f"({subscription.suppression_reason or 'no reason recorded'})."
        )
    if subscription.unsubscribed_all:
        return "This reader has unsubscribed from all email."
    return None


def clean_text(data: dict) -> dict:
    """Validate and normalise an admin's email into the shared ``text`` shape."""
    text = {}
    for field in FIELDS:
        value = data.get(field, "")
        if field == "paragraphs":
            if isinstance(value, str):
                value = value.split("\n")
            if not isinstance(value, list):
                raise DirectEmailError("paragraphs must be a list of strings")
            text[field] = [str(p).strip() for p in value if str(p).strip()]
        else:
            text[field] = str(value or "").strip()
    if not text["subject"]:
        raise DirectEmailError("A subject line is required.")
    if len(text["subject"]) > 300:
        raise DirectEmailError("The subject line is too long (300 characters at most).")
    if not text["paragraphs"]:
        raise DirectEmailError("Write at least one paragraph.")
    if text["cta_label"]:
        bad = cta_path_problem(text["cta_path"])
        if bad:
            raise DirectEmailError(f"The button link {bad}.")
    return text


def send_direct(profile, data: dict, *, sent_by: str) -> EmailMessage:
    """Write to ``profile`` and return the message row (check its ``status``).

    Raises :class:`DirectEmailError` when the email is invalid or the reader
    can't be written to.
    """
    text = clean_text(data)
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    reason = blocked_reason(subscription)
    if reason:
        raise DirectEmailError(reason)
    to_email = verified_email(profile)
    if not to_email:
        raise DirectEmailError("This reader has no verified email address.")
    rendered = render_direct(text, profile, subscription)
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.DIRECT,
        rendered=rendered,
        # A fresh key per send: a direct email is never deduplicated against an
        # earlier one to the same reader.
        idempotency_key=idempotency_key(EmailKind.DIRECT, uuid.uuid4().hex, profile),
        to_email=to_email,
        locale=email_lang(profile, subscription),
        sent_by=sent_by,
        body_text="\n\n".join(text["paragraphs"]),
    )
    return message


def history(profile, limit: int = 50) -> list[dict]:
    """The reader's recent email, newest first, with what happened to each."""
    messages = (
        EmailMessage.objects.filter(recipient=profile)
        .select_related("broadcast")
        .prefetch_related("events")[:limit]
    )
    rows = []
    for m in messages:
        if m.kind == EmailKind.BROADCAST:
            label = m.broadcast.name if m.broadcast else "Broadcast"
            if m.idempotency_key.startswith("broadcast-test:"):
                label = f"{label} (test)"
        elif m.kind == EmailKind.LIFECYCLE:
            label = m.lifecycle_step.replace("_", " ").capitalize()
        else:
            label = "Direct email"
        events = sorted({e.type for e in m.events.all()})
        rows.append(
            {
                "id": m.id,
                "kind": m.kind,
                "label": label,
                "subject": m.subject,
                "status": m.status,
                "error": m.error if m.status != SendStatus.SENT else "",
                "events": events,
                "sent_by": m.sent_by,
                "body_text": m.body_text,
                "created_at": m.created_at.isoformat(),
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
        )
    return rows
