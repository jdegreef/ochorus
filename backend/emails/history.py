"""One reader's email history, for their admin page."""

from __future__ import annotations

from .models import EmailMessage, SendStatus


def history(profile, limit: int = 50) -> list[dict]:
    """The reader's recent email, newest first, with what happened to each."""
    messages = (
        EmailMessage.objects.filter(recipient=profile)
        .select_related("broadcast")
        .prefetch_related("events")[:limit]
    )
    return [
        {
            "id": m.id,
            "kind": m.kind,
            "label": m.label,
            "subject": m.subject,
            "status": m.status,
            "error": m.error if m.status != SendStatus.SENT else "",
            "events": sorted({e.type for e in m.events.all()}),
            "sent_by": m.sent_by,
            "body_text": m.body_text,
            "created_at": m.created_at.isoformat(),
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        }
        for m in messages
    ]
