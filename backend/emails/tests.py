"""Tests for the email programme: consent, idempotent sending, rendering,
one-click unsubscribe, and signed webhook ingest."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import UserProfile

from .lifecycle import send_welcome, welcome_key
from .models import (
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    SendStatus,
)
from .rendering import render_welcome

User = get_user_model()

_SECRET_BYTES = b"a-thirty-two-byte-webhook-secret!"
_SECRET_B64 = base64.b64encode(_SECRET_BYTES).decode()
_WEBHOOK_SECRET = "whsec_" + _SECRET_B64

# Sending on, key present → emails_enabled() is True and send_email is the seam.
SENDING = override_settings(
    EMAIL_ENABLED=True,
    RESEND_API_KEY="test-key",
    API_PUBLIC_URL="https://api.test",
    PUBLIC_SITE_URL="https://ochorus.test",
    SUPABASE_URL="",
    SUPABASE_SERVICE_ROLE_KEY="",
)


def _make_profile(email="reader@example.com", locale="en", name="James Reader"):
    user = User.objects.create(username=f"uid-{email}")
    return UserProfile.objects.create(
        user=user,
        supabase_uid="00000000-0000-0000-0000-000000000001",
        email=email,
        display_name=name,
        locale=locale,
    )


@SENDING
class WelcomeSendingTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()

    @mock.patch("emails.sending.send_email", return_value="resend-abc")
    def test_welcome_sends_once_and_is_idempotent(self, send):
        message = send_welcome(self.profile)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(message.provider_message_id, "resend-abc")
        self.assertEqual(message.kind, EmailKind.LIFECYCLE)
        self.assertEqual(message.to_email, "reader@example.com")
        self.assertEqual(send.call_count, 1)

        # A second sweep must not send again.
        again = send_welcome(self.profile)
        self.assertEqual(again.pk, message.pk)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(EmailMessage.objects.count(), 1)

    @mock.patch("emails.sending.send_email", return_value="resend-abc")
    def test_welcome_attaches_one_click_unsubscribe_headers(self, send):
        send_welcome(self.profile)
        headers = send.call_args.kwargs["headers"]
        self.assertIn("List-Unsubscribe", headers)
        self.assertEqual(headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        sub = EmailSubscription.objects.get(profile=self.profile)
        self.assertIn(sub.unsubscribe_token, headers["List-Unsubscribe"])

    @mock.patch("emails.sending.send_email", return_value="resend-abc")
    def test_opted_out_reader_is_not_sent(self, send):
        EmailSubscription.objects.create(profile=self.profile, unsubscribed_all=True)
        self.assertIsNone(send_welcome(self.profile))
        send.assert_not_called()

    @mock.patch("emails.sending.send_email", return_value="resend-abc")
    def test_suppressed_reader_is_not_sent(self, send):
        sub = EmailSubscription.objects.create(profile=self.profile)
        sub.suppress("bounced")
        self.assertIsNone(send_welcome(self.profile))
        send.assert_not_called()

    @mock.patch("emails.sending.send_email", return_value="resend-abc")
    def test_reader_without_address_is_not_sent(self, send):
        self.profile.email = ""
        self.profile.save(update_fields=["email"])
        self.assertIsNone(send_welcome(self.profile))
        send.assert_not_called()

    def test_disabled_sending_records_skipped_without_calling_resend(self):
        with override_settings(EMAIL_ENABLED=False):
            with mock.patch("emails.sending.send_email") as send:
                message = send_welcome(self.profile)
                send.assert_not_called()
        self.assertEqual(message.status, SendStatus.SKIPPED)
        # Idempotency key is stable so it retries once enabled.
        self.assertEqual(message.idempotency_key, welcome_key(self.profile))


class SubscriptionConsentTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        self.sub = EmailSubscription.objects.create(profile=self.profile)

    def test_wants_respects_class_opt_in(self):
        self.assertTrue(self.sub.wants(EmailKind.LIFECYCLE))
        self.assertTrue(self.sub.wants(EmailKind.BROADCAST))
        self.sub.newsletter_opt_in = False
        self.assertFalse(self.sub.wants(EmailKind.BROADCAST))
        self.assertTrue(self.sub.wants(EmailKind.LIFECYCLE))

    def test_unsubscribe_all_blocks_everything(self):
        self.sub.unsubscribe()
        self.assertFalse(self.sub.wants(EmailKind.LIFECYCLE))
        self.assertFalse(self.sub.wants(EmailKind.BROADCAST))

    def test_suppress_blocks_everything(self):
        self.sub.suppress("complained")
        self.assertTrue(self.sub.is_suppressed)
        self.assertFalse(self.sub.wants(EmailKind.LIFECYCLE))


@SENDING
class RenderingTests(TestCase):
    def test_welcome_localizes_and_carries_unsubscribe_link(self):
        profile = _make_profile(locale="es", name="María")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_welcome(profile, sub)
        self.assertEqual(rendered.subject, "Bienvenido a Ochorus")
        self.assertIn("María", rendered.html)
        self.assertIn(sub.unsubscribe_token, rendered.html)
        self.assertIn('lang="es"', rendered.html)

    def test_unknown_locale_falls_back_to_english(self):
        profile = _make_profile(locale="xx")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_welcome(profile, sub)
        self.assertEqual(rendered.subject, "Welcome to Ochorus")


class UnsubscribeViewTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        self.sub = EmailSubscription.objects.create(profile=self.profile)

    def test_get_opts_out_and_renders_confirmation(self):
        res = self.client.get(f"/api/emails/unsubscribe/{self.sub.unsubscribe_token}/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"unsubscribed", res.content.lower())
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.unsubscribed_all)

    def test_post_one_click_opts_out(self):
        res = self.client.post(f"/api/emails/unsubscribe/{self.sub.unsubscribe_token}/")
        self.assertEqual(res.status_code, 200)
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.unsubscribed_all)

    def test_unknown_token_is_neutral(self):
        res = self.client.get("/api/emails/unsubscribe/not-a-real-token/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"no longer valid", res.content.lower())


def _signed_headers(body: bytes, *, svix_id="msg_1", ts=None):
    ts = ts or str(int(time.time()))
    signed = svix_id.encode() + b"." + ts.encode() + b"." + body
    sig = base64.b64encode(
        hmac.new(_SECRET_BYTES, signed, hashlib.sha256).digest()
    ).decode()
    return {
        "HTTP_SVIX_ID": svix_id,
        "HTTP_SVIX_TIMESTAMP": ts,
        "HTTP_SVIX_SIGNATURE": f"v1,{sig}",
    }


@override_settings(RESEND_WEBHOOK_SECRET=_WEBHOOK_SECRET)
class WebhookTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        self.message = EmailMessage.objects.create(
            recipient=self.profile,
            to_email="reader@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step="welcome",
            idempotency_key="lifecycle:welcome:1",
            provider_message_id="resend-xyz",
            status=SendStatus.SENT,
            sent_at=timezone.now(),
        )

    def _post(self, payload, headers=None):
        body = json.dumps(payload).encode()
        headers = headers if headers is not None else _signed_headers(body)
        return self.client.post(
            "/api/emails/webhook/",
            data=body,
            content_type="application/json",
            **headers,
        )

    def _payload(self, event_type, extra=None):
        data = {"email_id": "resend-xyz", "created_at": "2026-09-18T10:00:00Z"}
        if extra:
            data.update(extra)
        return {"type": event_type, "created_at": "2026-09-18T10:00:00Z", "data": data}

    def test_invalid_signature_rejected(self):
        res = self._post(self._payload("email.opened"), headers={})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_opened_event_recorded(self):
        res = self._post(self._payload("email.opened"))
        self.assertEqual(res.status_code, 200)
        event = EmailEvent.objects.get()
        self.assertEqual(event.type, EventType.OPENED)
        self.assertEqual(event.message, self.message)

    def test_clicked_event_captures_url(self):
        payload = self._payload(
            "email.clicked", extra={"click": {"link": "https://ochorus.test/humility"}}
        )
        self._post(payload)
        event = EmailEvent.objects.get(type=EventType.CLICKED)
        self.assertEqual(event.url, "https://ochorus.test/humility")

    def test_duplicate_delivery_is_deduped(self):
        # Same svix-id twice → one event.
        body = json.dumps(self._payload("email.opened")).encode()
        h = _signed_headers(body, svix_id="msg_dup")
        self.client.post("/api/emails/webhook/", data=body, content_type="application/json", **h)
        self.client.post("/api/emails/webhook/", data=body, content_type="application/json", **h)
        self.assertEqual(EmailEvent.objects.filter(type=EventType.OPENED).count(), 1)

    def test_bounce_suppresses_subscription(self):
        EmailSubscription.objects.create(profile=self.profile)
        self._post(self._payload("email.bounced"))
        sub = EmailSubscription.objects.get(profile=self.profile)
        self.assertTrue(sub.is_suppressed)
        self.assertEqual(sub.suppression_reason, "bounced")

    def test_unknown_message_is_acked_without_error(self):
        payload = self._payload("email.opened", extra={"email_id": "unknown"})
        payload["data"]["email_id"] = "unknown"
        res = self._post(payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(EmailEvent.objects.count(), 0)
