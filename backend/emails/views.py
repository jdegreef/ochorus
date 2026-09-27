"""Public email endpoints: the Resend webhook, and one-click unsubscribe.

Both are unauthenticated on purpose. The webhook is trusted by its Svix
signature, not a session; unsubscribe is trusted by an unguessable token in the
link, so it works with no sign-in from any device — which is what compliance
requires.
"""

from __future__ import annotations

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    SUPPRESSING_EVENTS,
    EmailEvent,
    EmailMessage,
    EmailSubscription,
    EventType,
)
from .resend_client import verify_webhook

logger = logging.getLogger(__name__)

_VALID_EVENTS = {e.value for e in EventType}


class ResendWebhookView(APIView):
    """Ingest Resend delivery events into :class:`EmailEvent`.

    Verified by Svix signature (never a session), so it takes no authentication
    and enforces no CSRF. Always answers 200 to a well-formed, authentic request
    — even when the referenced message is unknown — so Resend does not retry
    forever over something we simply can't attach.
    """

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        if not verify_webhook(request.body, request.headers):
            return Response(
                {"detail": "invalid signature"}, status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return Response(
                {"detail": "bad payload"}, status=status.HTTP_400_BAD_REQUEST
            )

        event_type = str(payload.get("type", ""))
        # "email.opened" -> "opened"
        bare = event_type.split(".", 1)[1] if "." in event_type else event_type
        if bare not in _VALID_EVENTS:
            return Response({"ok": True, "ignored": event_type})

        data = payload.get("data") or {}
        message = self._find_message(data)
        if message is None:
            logger.info("webhook %s for unknown message", event_type)
            return Response({"ok": True, "unmatched": True})

        self._record(message, bare, payload, data, request.headers)
        return Response({"ok": True})

    @staticmethod
    def _find_message(data: dict) -> EmailMessage | None:
        provider_id = data.get("email_id") or data.get("id")
        if not provider_id:
            return None
        return EmailMessage.objects.filter(provider_message_id=provider_id).first()

    @staticmethod
    def _record(message, bare, payload, data, headers) -> None:
        occurred = (
            parse_datetime(data.get("created_at") or payload.get("created_at") or "")
            or timezone.now()
        )
        url = ""
        if bare == EventType.CLICKED:
            url = ((data.get("click") or {}).get("link")) or ""

        EmailEvent.objects.get_or_create(
            message=message,
            type=bare,
            provider_event_id=headers.get("svix-id", ""),
            defaults={
                "url": url,
                "occurred_at": occurred,
                "raw": payload,
            },
        )

        if bare in SUPPRESSING_EVENTS:
            subscription = EmailSubscription.objects.filter(
                profile=message.recipient_id
            ).first()
            if subscription and not subscription.is_suppressed:
                subscription.suppress(reason=bare)


@method_decorator(csrf_exempt, name="dispatch")
class UnsubscribeView(View):
    """Unsubscribe by token — no login. Only a POST opts out.

    POST is the RFC 8058 one-click target that inbox providers call (JSON back),
    and also what the confirm button on the GET page submits (a page back). GET
    is what a person clicking the footer link lands on: it asks, and changes
    nothing. It used to opt out on GET, but corporate mail scanners (Safe Links,
    Mimecast, Proofpoint) and link previewers fetch every URL in a message, so
    readers were silently unsubscribed by their own inbox. RFC 8058 providers
    POST, so the inbox's native button is unaffected. CSRF-exempt because the
    256-bit token in the URL is the credential. An unknown token gets a neutral
    page rather than confirming or denying that it existed.
    """

    #: The confirm form's field — tells a button press (render a page) from an
    #: inbox provider's one-click POST (``List-Unsubscribe=One-Click``, JSON).
    CONFIRM_FIELD = "confirm"

    def post(self, request, token: str):
        found = self._opt_out(token)
        if self.CONFIRM_FIELD not in request.POST:
            return JsonResponse({"ok": True})
        if found:
            body = (
                "<p>You've been unsubscribed. You will no longer receive emails "
                "from Ochorus.</p>"
            )
        else:
            body = "<p>This unsubscribe link is no longer valid.</p>"
        return HttpResponse(_page(body), content_type="text/html; charset=utf-8")

    def get(self, request, token: str):
        # The form posts back to this same URL; the token never leaves it.
        body = (
            "<p>Unsubscribe from all Ochorus emails?</p>"
            "<form method='post'>"
            f"<button type='submit' name='{self.CONFIRM_FIELD}' value='1' "
            "style=\"font:inherit; padding:.6rem 1.2rem; border:1px solid #6b5b3e; "
            "background:#6b5b3e; color:#fff; border-radius:6px; cursor:pointer;\">"
            "Unsubscribe</button></form>"
        )
        return HttpResponse(_page(body), content_type="text/html; charset=utf-8")

    @staticmethod
    def _opt_out(token: str) -> bool:
        subscription = EmailSubscription.objects.filter(
            unsubscribe_token=token
        ).first()
        if subscription is None:
            return False
        subscription.unsubscribe()
        return True


def _page(body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Ochorus email preferences</title></head>"
        "<body style=\"font-family:Georgia,serif; max-width:32rem; margin:12vh auto; "
        "padding:0 1.5rem; color:#2b2b2b; line-height:1.6;\">"
        "<h1 style='color:#6b5b3e; font-size:1.4rem;'>Ochorus</h1>"
        f"{body}</body></html>"
    )
