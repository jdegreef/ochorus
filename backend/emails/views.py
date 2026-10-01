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

from library.languages import entry as language_entry
from library.languages import live_codes

from .models import (
    SUPPRESSING_EVENTS,
    EmailEvent,
    EmailMessage,
    EmailSubscription,
    EventType,
)
from .resend_client import verify_webhook
from .streams import STREAM_KEYS, STREAMS

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


@method_decorator(csrf_exempt, name="dispatch")
class EmailPreferencesView(View):
    """The reader-facing preference center, keyed by the unsubscribe token.

    No login: the 256-bit token in the link is the credential (same as
    :class:`UnsubscribeView`), so a reader manages their email from any device.
    GET returns the current state as JSON; POST saves per-stream choices, a
    language override, and the master off switch. CSRF-exempt because the token
    is the credential and the SvelteKit page (a different origin) calls it with
    JSON. An unknown token is a neutral 404 — it neither confirms nor denies the
    token existed.

    This is a plain Django view (not DRF) on purpose: like unsubscribe it is a
    public, token-gated write, and staying off the DRF ``APIView`` path keeps it
    out of the admin-gate authz walk without needing an exemption.
    """

    def get(self, request, token: str):
        subscription = self._find(token)
        if subscription is None:
            return JsonResponse({"detail": "unknown token"}, status=404)
        return JsonResponse(self._state(subscription, live_codes()))

    def post(self, request, token: str):
        subscription = self._find(token)
        if subscription is None:
            return JsonResponse({"detail": "unknown token"}, status=404)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"detail": "bad payload"}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "bad payload"}, status=400)

        # One registry read per request: both the locale check and the echoed
        # state use the same live-language list.
        live = live_codes()
        self._apply(subscription, payload, live)
        return JsonResponse(self._state(subscription, live))

    @staticmethod
    def _find(token: str) -> EmailSubscription | None:
        return EmailSubscription.objects.filter(unsubscribe_token=token).first()

    def _apply(
        self, subscription: EmailSubscription, payload: dict, live: list[str]
    ) -> None:
        fields: list[str] = []

        streams = payload.get("streams")
        if isinstance(streams, dict):
            prefs = dict(subscription.stream_prefs or {})
            for key, value in streams.items():
                if key in STREAM_KEYS:
                    prefs[key] = bool(value)
            subscription.stream_prefs = prefs
            fields.append("stream_prefs")

        if "email_locale" in payload:
            locale = str(payload.get("email_locale") or "").strip()
            # Empty clears the override; any other value must be a live language.
            if locale == "" or locale in live:
                subscription.email_locale = locale
                fields.append("email_locale")

        if "unsubscribed_all" in payload:
            subscription.unsubscribed_all = bool(payload.get("unsubscribed_all"))
            fields.append("unsubscribed_all")

        if fields:
            subscription.save(update_fields=[*fields, "updated_at"])

    @staticmethod
    def _state(subscription: EmailSubscription, live: list[str]) -> dict:
        streams = [
            {
                "key": s["key"],
                "label": s["label"],
                "description": s["description"],
                "enabled": subscription.stream_prefs.get(
                    s["key"], subscription.stream_default(s["key"])
                ),
            }
            for s in STREAMS
        ]
        locales = [
            {"code": code, "name": language_entry(code).get("native_name", code)}
            for code in live
        ]
        return {
            "streams": streams,
            "locales": locales,
            "email_locale": subscription.email_locale,
            "unsubscribed_all": subscription.unsubscribed_all,
            "suppressed": subscription.is_suppressed,
        }


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
