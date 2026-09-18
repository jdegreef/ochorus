"""Tests for the email programme: consent, idempotent sending, rendering,
one-click unsubscribe, and signed webhook ingest."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import UserProfile
from reading.models import PlanProgress

from .lifecycle import (
    CLASSIC_STEP,
    COMEBACK_STEP,
    PLAN_STEP,
    WELCOME_STEP,
    due_step,
    send_due,
    send_welcome,
    welcome_key,
)
from .management.commands.send_lifecycle_emails import _parse_cutoff
from .models import (
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    SendStatus,
)
from .recipient import verified_email as resolve_recipient_email
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
    uid = uuid.uuid4()
    user = User.objects.create(username=str(uid))
    return UserProfile.objects.create(
        user=user,
        supabase_uid=uid,
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


class RecipientResolutionTests(TestCase):
    """Supabase-configured is authoritative; only an unconfigured Supabase
    falls back to the (possibly unverified) profile email."""

    def setUp(self):
        self.profile = _make_profile(email="profile@example.com")

    @mock.patch("emails.recipient.is_configured", return_value=False)
    def test_falls_back_to_profile_email_when_unconfigured(self, _cfg):
        self.assertEqual(resolve_recipient_email(self.profile), "profile@example.com")

    @mock.patch("emails.recipient._supabase_verified_email", return_value=None)
    @mock.patch("emails.recipient.is_configured", return_value=True)
    def test_configured_failure_does_not_fall_back(self, _cfg, _sv):
        # A None from Supabase (unconfirmed OR failed lookup) must NOT downgrade
        # to profile.email when Supabase is the configured source of truth.
        self.assertIsNone(resolve_recipient_email(self.profile))

    @mock.patch(
        "emails.recipient._supabase_verified_email", return_value="verified@supabase.co"
    )
    @mock.patch("emails.recipient.is_configured", return_value=True)
    def test_configured_returns_supabase_address(self, _cfg, _sv):
        self.assertEqual(resolve_recipient_email(self.profile), "verified@supabase.co")


@override_settings(
    EMAIL_ENABLED=True,
    RESEND_API_KEY="test-key",
    API_PUBLIC_URL="",
    PUBLIC_SITE_URL="",
    SUPABASE_URL="",
    SUPABASE_SERVICE_ROLE_KEY="",
)
class BaseUrlGuardTests(TestCase):
    def test_missing_base_urls_skips_send(self):
        profile = _make_profile()
        with mock.patch("emails.sending.send_email") as send:
            message = send_welcome(profile)
            send.assert_not_called()
        self.assertEqual(message.status, SendStatus.SKIPPED)


class CutoffParsingTests(TestCase):
    def test_parses_date_only(self):
        dt = _parse_cutoff("2026-09-17")
        self.assertIsNotNone(dt)
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 9, 17))

    def test_parses_datetime(self):
        self.assertIsNotNone(_parse_cutoff("2026-09-17T08:00:00"))

    def test_rejects_garbage(self):
        self.assertIsNone(_parse_cutoff("not-a-date"))


class LifecycleStepTests(TestCase):
    """The drip step registry: which step is due given account age and state."""

    def _profile(self, *, age_days=0, seen_days_ago=None, **kw):
        profile = _make_profile(**kw)
        created = timezone.now() - timedelta(days=age_days)
        last_seen = (
            timezone.now() - timedelta(days=seen_days_ago)
            if seen_days_ago is not None
            else None
        )
        # created_at is auto_now_add; bypass it with an UPDATE.
        UserProfile.objects.filter(pk=profile.pk).update(
            created_at=created, last_seen_at=last_seen
        )
        profile.refresh_from_db()
        return profile

    def _mark_sent(self, profile, *steps):
        for step in steps:
            EmailMessage.objects.create(
                recipient=profile,
                to_email="x@example.com",
                kind=EmailKind.LIFECYCLE,
                lifecycle_step=step,
                idempotency_key=f"lifecycle:{step}:{profile.pk}",
                status=SendStatus.SENT,
                sent_at=timezone.now(),
            )

    def test_fresh_account_is_due_welcome(self):
        profile = self._profile(age_days=0)
        self.assertEqual(due_step(profile, timezone.now()).name, WELCOME_STEP)

    def test_plan_nudge_after_welcome_when_no_plan(self):
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP)
        self.assertEqual(due_step(profile, timezone.now()).name, PLAN_STEP)

    def test_plan_nudge_skipped_when_reader_has_a_plan(self):
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP)
        PlanProgress.objects.create(
            profile=profile, plan_slug="humility-plan", started_at=timezone.now(), done=[]
        )
        # Day 3 with a plan: welcome sent, plan skipped, classic needs day 4+,
        # no last_seen for comeback → nothing due yet.
        self.assertIsNone(due_step(profile, timezone.now()))

    def test_classic_due_on_day_four(self):
        profile = self._profile(age_days=5)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        self.assertEqual(due_step(profile, timezone.now()).name, CLASSIC_STEP)

    def test_comeback_when_reader_has_lapsed(self):
        profile = self._profile(age_days=30, seen_days_ago=10)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP, CLASSIC_STEP)
        self.assertEqual(due_step(profile, timezone.now()).name, COMEBACK_STEP)

    def test_recently_active_reader_gets_no_comeback(self):
        profile = self._profile(age_days=30, seen_days_ago=1)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP, CLASSIC_STEP)
        self.assertIsNone(due_step(profile, timezone.now()))

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_sweep_sends_one_email_earliest_step_first(self, send):
        # An old account with nothing sent still gets welcome first, not classic.
        profile = self._profile(age_days=20)
        message = send_due(profile)
        self.assertEqual(message.lifecycle_step, WELCOME_STEP)
        self.assertEqual(send.call_count, 1)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_min_gap_defers_next_step(self, send):
        # A step sent an hour ago holds off the next, so a back-dated account
        # can't get the whole drip in consecutive cron runs.
        profile = self._profile(age_days=20)
        EmailMessage.objects.create(
            recipient=profile,
            to_email="x@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step=WELCOME_STEP,
            idempotency_key=welcome_key(profile),
            status=SendStatus.SENT,
            sent_at=timezone.now() - timedelta(hours=1),
        )
        self.assertIsNone(send_due(profile))
        send.assert_not_called()

    def test_every_registered_step_has_english_copy(self):
        # Guard the STEPS ↔ copy coupling: a step added without a copy block
        # should fail the build, not KeyError at send time.
        from emails.copy import LIFECYCLE
        from emails.lifecycle import STEPS

        for step in STEPS:
            self.assertIn(step.name, LIFECYCLE, f"no copy block for step {step.name!r}")
            self.assertIn("en", LIFECYCLE[step.name], f"no English copy for {step.name!r}")

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_next_step_sent_after_gap_elapses(self, send):
        profile = self._profile(age_days=20)
        EmailMessage.objects.create(
            recipient=profile,
            to_email="x@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step=WELCOME_STEP,
            idempotency_key=welcome_key(profile),
            status=SendStatus.SENT,
            sent_at=timezone.now() - timedelta(days=2),
        )
        message = send_due(profile)
        self.assertEqual(message.lifecycle_step, PLAN_STEP)
        send.assert_called_once()
