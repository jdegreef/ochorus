"""Tests for the email programme: consent, idempotent sending, rendering,
one-click unsubscribe, and signed webhook ingest."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import time
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import UserProfile
from library.models import Author, Book, Series
from reading.models import PlanProgress, ReadingProgress, WorkKind

from .lifecycle import (
    CLASSIC_STEP,
    COMEBACK_STEP,
    FIRST_BOOK_STEP,
    PLAN_STEP,
    WELCOME_STEP,
    WINBACK_STEP,
    due_step,
    send_due,
    send_welcome,
    welcome_key,
)
from .management.commands.send_lifecycle_emails import _parse_cutoff
from .milestones import MILESTONES, due_milestone, finished_book_count
from .milestones import send_due as send_milestone_due
from .models import (
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    SendStatus,
)
from .recipient import verified_email as resolve_recipient_email
from .rendering import render_milestone, render_series_nudge, render_welcome
from .series_nudge import next_series_volume
from .series_nudge import send_due as send_series_due
from .streams import STREAM_KEYS
from .sweeps import recent_book_finishers as series_candidate_profiles

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
    EMAIL_SEND_RATE=0,  # no pacing sleeps in tests
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

    def test_wants_stream_q_mirrors_wants_stream(self):
        # The ORM mirror must select exactly the rows wants_stream() is true for,
        # across the per-stream choice, its legacy fallback, and the blockers.
        cases = [
            {},
            {"stream_prefs": {"announcements": False}},
            {"stream_prefs": {"announcements": True}, "newsletter_opt_in": False},
            {"newsletter_opt_in": False},
            {"unsubscribed_all": True},
            {"stream_prefs": {"announcements": True}, "unsubscribed_all": True},
            {"suppressed_at": timezone.now()},
        ]
        for i, fields in enumerate(cases):
            sub = EmailSubscription.objects.create(
                profile=_make_profile(email=f"case{i}@example.com"), **fields
            )
            selected = EmailSubscription.objects.filter(
                EmailSubscription.wants_stream_q("announcements"), pk=sub.pk
            ).exists()
            self.assertEqual(
                selected, sub.wants_stream("announcements"), msg=f"case {i}: {fields}"
            )

    def test_unknown_stream_raises(self):
        # A typo'd key must fail loudly in both forms, not silently resolve ON.
        with self.assertRaises(ValueError):
            self.sub.wants_stream("announcments")
        with self.assertRaises(ValueError):
            EmailSubscription.wants_stream_q("announcments")

    def test_every_real_stream_is_accepted(self):
        for key in STREAM_KEYS:
            self.sub.wants_stream(key)  # must not raise
            EmailSubscription.wants_stream_q(key)  # must not raise


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

    def test_get_asks_and_changes_nothing(self):
        # Mail scanners and link previewers GET every URL in a message; a GET
        # must never opt the reader out on their behalf.
        res = self.client.get(f"/api/emails/unsubscribe/{self.sub.unsubscribe_token}/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"<form method='post'>", res.content)
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.unsubscribed_all)

    def test_confirm_button_opts_out_and_renders_confirmation(self):
        res = self.client.post(
            f"/api/emails/unsubscribe/{self.sub.unsubscribe_token}/", {"confirm": "1"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"unsubscribed", res.content.lower())
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.unsubscribed_all)

    def test_post_one_click_opts_out(self):
        # RFC 8058: the inbox provider POSTs `List-Unsubscribe=One-Click`.
        res = self.client.post(
            f"/api/emails/unsubscribe/{self.sub.unsubscribe_token}/",
            {"List-Unsubscribe": "One-Click"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True})
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.unsubscribed_all)

    def test_unknown_token_is_neutral(self):
        res = self.client.post("/api/emails/unsubscribe/not-a-real-token/", {"confirm": "1"})
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

    def _start_book(self, profile, *, slug="b1", finished=False):
        ReadingProgress.objects.create(
            profile=profile,
            kind=WorkKind.BOOK,
            book_slug=slug,
            language="en",
            finished_at=timezone.now() if finished else None,
        )

    def test_finish_first_book_due_when_started_but_unfinished(self):
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        self._start_book(profile)  # opened, not finished
        self.assertEqual(due_step(profile, timezone.now()).name, FIRST_BOOK_STEP)

    def test_finish_first_book_skipped_without_a_started_book(self):
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        # Nothing opened yet — the finish nudge doesn't apply; classic waits day 4.
        self.assertIsNone(due_step(profile, timezone.now()))

    def test_finish_first_book_skipped_after_a_finish(self):
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        self._start_book(profile, slug="done", finished=True)
        self.assertIsNone(due_step(profile, timezone.now()))

    def test_finish_first_book_precedes_classic(self):
        # A reader with a book in hand is pointed back to it, not at a new classic.
        profile = self._profile(age_days=5)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        self._start_book(profile)
        self.assertEqual(due_step(profile, timezone.now()).name, FIRST_BOOK_STEP)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_finish_first_book_sends_end_to_end(self, send):
        # Exercises the render path (copy + CTA), not just the due predicate.
        profile = self._profile(age_days=3)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP)
        # Back-date the earlier steps past the 20h gap so this one can send now.
        EmailMessage.objects.filter(recipient=profile).update(
            sent_at=timezone.now() - timedelta(hours=48)
        )
        self._start_book(profile)
        message = send_due(profile)
        self.assertEqual(message.lifecycle_step, FIRST_BOOK_STEP)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(send.call_count, 1)

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

    def test_winback_when_deeply_dormant(self):
        profile = self._profile(age_days=90, seen_days_ago=35)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP, CLASSIC_STEP, COMEBACK_STEP)
        self.assertEqual(due_step(profile, timezone.now()).name, WINBACK_STEP)

    def test_winback_not_due_before_thirty_days(self):
        # 20 days quiet: comeback already sent, winback needs 30 → nothing due.
        profile = self._profile(age_days=90, seen_days_ago=20)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP, CLASSIC_STEP, COMEBACK_STEP)
        self.assertIsNone(due_step(profile, timezone.now()))

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_winback_sends_end_to_end(self, send):
        profile = self._profile(age_days=90, seen_days_ago=35)
        self._mark_sent(profile, WELCOME_STEP, PLAN_STEP, CLASSIC_STEP, COMEBACK_STEP)
        # Back-date the earlier steps past the 20h gap so winback can send now.
        EmailMessage.objects.filter(recipient=profile).update(
            sent_at=timezone.now() - timedelta(hours=48)
        )
        message = send_due(profile)
        self.assertEqual(message.lifecycle_step, WINBACK_STEP)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(send.call_count, 1)

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


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class AdminEmailMetricsTests(TestCase):
    """The admin open/click/bounce rollup endpoint."""

    def _sent(self, profile, step, key):
        return EmailMessage.objects.create(
            recipient=profile,
            to_email="a@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step=step,
            idempotency_key=key,
            status=SendStatus.SENT,
            sent_at=timezone.now(),
        )

    def _event(self, message, event_type, eid):
        EmailEvent.objects.create(
            message=message,
            type=event_type,
            occurred_at=timezone.now(),
            provider_event_id=eid,
        )

    def test_step_rollup_and_rates(self):
        profile = _make_profile()
        opened = self._sent(profile, WELCOME_STEP, "lifecycle:welcome:1")
        self._event(opened, EventType.OPENED, "e1")
        self._event(opened, EventType.CLICKED, "e2")
        bounced = self._sent(profile, WELCOME_STEP, "lifecycle:welcome:2")
        self._event(bounced, EventType.BOUNCED, "e3")

        res = self.client.get("/api/admin/email-metrics/")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        welcome = next(r for r in data["by_step"] if r["step"] == WELCOME_STEP)
        self.assertEqual(welcome["sent"], 2)
        self.assertEqual(welcome["delivered"], 1)  # 2 sent − 1 bounce
        self.assertEqual(welcome["opens"], 1)
        self.assertEqual(welcome["clicks"], 1)
        self.assertEqual(welcome["bounces"], 1)
        self.assertEqual(welcome["open_rate"], 1.0)  # 1 open / 1 delivered
        self.assertEqual(welcome["click_rate"], 1.0)
        self.assertEqual(welcome["bounce_rate"], 0.5)  # 1 bounce / 2 sent

    def test_overview_and_subscribers(self):
        profile = _make_profile()
        EmailSubscription.objects.create(profile=profile)
        self._sent(profile, WELCOME_STEP, "lifecycle:welcome:1")

        data = self.client.get("/api/admin/email-metrics/").json()
        self.assertEqual(data["overview"]["sent"], 1)
        self.assertEqual(data["subscribers"]["total"], 1)
        self.assertEqual(data["subscribers"]["announcements"], 1)

    def test_announcements_count_follows_stream_prefs(self):
        # The "announcements" subscriber count must track the preference center's
        # per-stream choice (stream_prefs), not the legacy newsletter_opt_in
        # boolean — mirroring EmailSubscription.wants_stream("announcements").
        # A reader who never set the stream (default ON).
        EmailSubscription.objects.create(profile=_make_profile(email="default@example.com"))
        # A reader who turned Announcements OFF in the preference center while the
        # legacy boolean is still its default True — must be excluded.
        EmailSubscription.objects.create(
            profile=_make_profile(email="off@example.com"),
            stream_prefs={"announcements": False},
        )
        # A reader who turned Announcements ON explicitly — included even though
        # the legacy boolean happens to be False.
        EmailSubscription.objects.create(
            profile=_make_profile(email="on@example.com"),
            newsletter_opt_in=False,
            stream_prefs={"announcements": True},
        )
        # Legacy opt-out, no explicit stream choice — default falls back to the
        # boolean, so excluded.
        EmailSubscription.objects.create(
            profile=_make_profile(email="legacy-off@example.com"),
            newsletter_opt_in=False,
        )

        data = self.client.get("/api/admin/email-metrics/").json()
        self.assertEqual(data["subscribers"]["total"], 4)
        self.assertEqual(data["subscribers"]["announcements"], 2)


from .audience import count as audience_count  # noqa: E402
from .audience import resolve as audience_resolve  # noqa: E402
from .broadcasts import send_broadcast  # noqa: E402
from .models import Broadcast, BroadcastStatus  # noqa: E402
from .rendering import render_broadcast  # noqa: E402


def _broadcast(**kw):
    defaults = {
        "name": "September news",
        "subject": {"en": "Hello from Ochorus"},
        "content": {
            "en": {
                "heading": "This month",
                "paragraphs": ["A new classic is live."],
                "cta_label": "Read it",
                "cta_path": "books",
            }
        },
        "audience": {},
    }
    defaults.update(kw)
    return Broadcast.objects.create(**defaults)


class AudienceTests(TestCase):
    def test_empty_audience_is_everyone(self):
        _make_profile()
        _make_profile()
        self.assertEqual(audience_count({}), 2)

    def test_locale_filter(self):
        _make_profile(locale="en")
        _make_profile(locale="es")
        self.assertEqual(audience_count({"locale": "es"}), 1)
        self.assertEqual(audience_count({"locale": ["en", "es"]}), 2)

    def test_has_plan_filter(self):
        planned = _make_profile()
        _make_profile()  # no plan
        PlanProgress.objects.create(
            profile=planned, plan_slug="humility-plan", started_at=timezone.now(), done=[]
        )
        self.assertEqual([p.pk for p in audience_resolve({"has_plan": True})], [planned.pk])
        self.assertEqual(audience_count({"has_plan": False}), 1)


@SENDING
class BroadcastSendTests(TestCase):
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_sends_to_opted_in_audience(self, send):
        _make_profile(email="a@example.com")
        _make_profile(email="b@example.com")
        tally = send_broadcast(_broadcast())
        self.assertEqual(tally["sent"], 2)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(
            EmailMessage.objects.filter(kind=EmailKind.BROADCAST, status=SendStatus.SENT).count(), 2
        )

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_custom_from_address_is_used(self, send):
        _make_profile()
        send_broadcast(_broadcast(from_address="News <news@ochorus.test>"))
        self.assertEqual(send.call_args.kwargs["from_email"], "News <news@ochorus.test>")

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_default_from_when_unset(self, send):
        _make_profile()
        send_broadcast(_broadcast())  # no from_address
        self.assertIsNone(send.call_args.kwargs["from_email"])

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_skips_opted_out_reader(self, send):
        profile = _make_profile()
        EmailSubscription.objects.create(profile=profile, newsletter_opt_in=False)
        tally = send_broadcast(_broadcast())
        self.assertEqual(tally, {"sent": 0, "skipped": 1, "failed": 0})
        send.assert_not_called()

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_send_is_idempotent(self, send):
        _make_profile()
        broadcast = _broadcast()
        send_broadcast(broadcast)
        send_broadcast(broadcast)  # re-run
        self.assertEqual(send.call_count, 1)  # not 2
        self.assertEqual(EmailMessage.objects.filter(kind=EmailKind.BROADCAST).count(), 1)

    def test_render_falls_back_to_english(self):
        profile = _make_profile(locale="es")  # broadcast has only en content
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_broadcast(_broadcast(), profile, sub)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.subject, "Hello from Ochorus")
        self.assertIn("This month", rendered.html)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_one_recipient_failing_does_not_strand_the_broadcast(self, send):
        _make_profile(email="a@example.com")
        _make_profile(email="b@example.com")
        broadcast = _broadcast()
        # The first recipient's render raises; the second renders nothing.
        with mock.patch(
            "emails.broadcasts.render_broadcast", side_effect=[ValueError("boom"), None]
        ), self.assertLogs("emails.broadcasts", "ERROR"):
            tally = send_broadcast(broadcast)
        self.assertEqual(tally, {"sent": 0, "skipped": 1, "failed": 1})
        broadcast.refresh_from_db()
        self.assertEqual(broadcast.status, "sent")

    def test_greeting_braces_are_literal_not_format_fields(self):
        from emails.rendering import _render

        profile = _make_profile()
        sub = EmailSubscription.objects.create(profile=profile)
        text = {"subject": "s", "greeting": "Hi {name} {0} {name.__class__} }{", "paragraphs": []}
        rendered = _render(text, profile, sub, "en")
        self.assertIn("{0}", rendered.html)
        self.assertNotIn("<class", rendered.html)

    def test_render_none_when_no_content(self):
        profile = _make_profile()
        sub = EmailSubscription.objects.create(profile=profile)
        # subject present but content empty → nothing to render
        self.assertIsNone(render_broadcast(_broadcast(content={}), profile, sub))


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class BroadcastAdminTests(TestCase):
    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def test_create_and_list(self):
        res = self._post(
            "/api/admin/broadcasts/",
            {"name": "Draft one", "subject": {"en": "Hi"}, "content": {"en": {"heading": "H"}}},
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["status"], BroadcastStatus.DRAFT)
        listing = self.client.get("/api/admin/broadcasts/").json()["broadcasts"]
        self.assertEqual(len(listing), 1)

    def test_create_requires_name(self):
        res = self._post("/api/admin/broadcasts/", {"subject": {"en": "Hi"}})
        self.assertEqual(res.status_code, 400)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_send_action_queues_and_the_cron_sends(self, send):
        _make_profile()
        b = _broadcast()
        res = self._post(f"/api/admin/broadcasts/{b.pk}/action/", {"action": "send"})
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        # The request only queues: nothing has been mailed yet.
        self.assertEqual(b.status, BroadcastStatus.SENDING)
        send.assert_not_called()
        call_command("send_due_broadcasts", stdout=io.StringIO())
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.SENT)
        self.assertEqual(b.send_tally["sent"], 1)
        self.assertIsNotNone(b.send_finished_at)

    def test_schedule_and_cancel(self):
        b = _broadcast()
        res = self._post(
            f"/api/admin/broadcasts/{b.pk}/action/",
            {"action": "schedule", "scheduled_at": "2099-01-01T09:00:00Z"},
        )
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.SCHEDULED)

        res = self._post(f"/api/admin/broadcasts/{b.pk}/action/", {"action": "cancel"})
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.CANCELED)

    def test_audience_preview(self):
        _make_profile(locale="sw")
        res = self._post("/api/admin/broadcasts/audience-preview/", {"audience": {"locale": "sw"}})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_sent_broadcast_cannot_be_edited(self, send):
        _make_profile()
        b = _broadcast()
        send_broadcast(b)
        res = self.client.patch(
            f"/api/admin/broadcasts/{b.pk}/",
            data=json.dumps({"name": "renamed"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 409)


from django.core.management import call_command  # noqa: E402


class EmailCronCommandTests(TestCase):
    def test_send_email_cron_runs_both_steps(self):
        # With no due readers/broadcasts and sending off, it completes cleanly —
        # the point is that the single command exists and chains the two steps.
        _make_profile()
        with mock.patch("emails.broadcasts.run_send") as run:
            call_command("send_email_cron", stdout=io.StringIO())
            run.assert_not_called()  # nothing scheduled or queued


@override_settings(
    EMAIL_ENABLED=True,
    RESEND_API_KEY="test-key",
    API_PUBLIC_URL="https://api.test",
    PUBLIC_SITE_URL="https://ochorus.test",
    SUPABASE_URL="",
    SUPABASE_SERVICE_ROLE_KEY="",
    EMAIL_ALLOWLIST={"me@example.com", "@staff.test"},
)
class AllowlistReviewModeTests(TestCase):
    """When EMAIL_ALLOWLIST is set, only listed addresses (or domains) send."""

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_reader_not_on_allowlist_is_skipped(self, send):
        profile = _make_profile(email="reader@example.com")
        message = send_welcome(profile)
        send.assert_not_called()
        self.assertEqual(message.status, SendStatus.SKIPPED)
        self.assertIn("ALLOWLIST", message.error)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_exact_allowlisted_address_sends(self, send):
        profile = _make_profile(email="me@example.com")
        message = send_welcome(profile)
        send.assert_called_once()
        self.assertEqual(message.status, SendStatus.SENT)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_domain_entry_matches(self, send):
        profile = _make_profile(email="anyone@staff.test")
        message = send_welcome(profile)
        send.assert_called_once()
        self.assertEqual(message.status, SendStatus.SENT)


class AllowlistEmptyMeansEveryoneTests(TestCase):
    @override_settings(
        EMAIL_ENABLED=True,
        RESEND_API_KEY="test-key",
        API_PUBLIC_URL="https://api.test",
        PUBLIC_SITE_URL="https://ochorus.test",
        SUPABASE_URL="",
        SUPABASE_SERVICE_ROLE_KEY="",
        EMAIL_ALLOWLIST=set(),
    )
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_empty_allowlist_sends_to_anyone(self, send):
        profile = _make_profile(email="reader@example.com")
        message = send_welcome(profile)
        send.assert_called_once()
        self.assertEqual(message.status, SendStatus.SENT)


class StreamPreferenceTests(TestCase):
    """Per-stream consent: the preference center's model layer."""

    def setUp(self):
        self.profile = _make_profile()
        self.sub = EmailSubscription.objects.create(profile=self.profile)

    def test_streams_default_on_opt_out_posture(self):
        for key in STREAM_KEYS:
            self.assertTrue(self.sub.wants_stream(key), key)

    def test_explicit_off_is_honored(self):
        self.sub.stream_prefs = {"digest": False}
        self.assertFalse(self.sub.wants_stream("digest"))
        # Untouched streams stay on.
        self.assertTrue(self.sub.wants_stream("announcements"))

    def test_legacy_boolean_is_the_stream_default(self):
        # A reader who turned the old newsletter switch off defaults the
        # announcements stream off until they set it explicitly.
        self.sub.newsletter_opt_in = False
        self.assertFalse(self.sub.wants_stream("announcements"))
        self.sub.stream_prefs = {"announcements": True}
        self.assertTrue(self.sub.wants_stream("announcements"))

    def test_master_switch_and_suppression_block_every_stream(self):
        self.sub.stream_prefs = dict.fromkeys(STREAM_KEYS, True)
        self.sub.unsubscribed_all = True
        for key in STREAM_KEYS:
            self.assertFalse(self.sub.wants_stream(key), key)
        self.sub.unsubscribed_all = False
        self.sub.suppressed_at = timezone.now()
        for key in STREAM_KEYS:
            self.assertFalse(self.sub.wants_stream(key), key)

    def test_kind_maps_to_its_stream(self):
        self.sub.stream_prefs = {"announcements": False}
        self.assertFalse(self.sub.wants(EmailKind.BROADCAST))
        self.assertTrue(self.sub.wants(EmailKind.LIFECYCLE))


@SENDING
class EmailLocaleOverrideTests(TestCase):
    def test_override_sets_the_rendered_language(self):
        profile = _make_profile(locale="en", name="Ana")
        sub = EmailSubscription.objects.create(profile=profile, email_locale="es")
        rendered = render_welcome(profile, sub)
        self.assertEqual(rendered.subject, "Bienvenido a Ochorus")
        self.assertIn('lang="es"', rendered.html)

    def test_blank_override_falls_back_to_reading_locale(self):
        profile = _make_profile(locale="es", name="Ana")
        sub = EmailSubscription.objects.create(profile=profile, email_locale="")
        rendered = render_welcome(profile, sub)
        self.assertEqual(rendered.subject, "Bienvenido a Ochorus")

    def test_footer_carries_manage_preferences_link(self):
        profile = _make_profile()
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_welcome(profile, sub)
        self.assertIn("/email/preferences/", rendered.html)
        self.assertIn(sub.unsubscribe_token, rendered.html)


class EmailPreferencesViewTests(TestCase):
    def setUp(self):
        self.profile = _make_profile(locale="en")
        self.sub = EmailSubscription.objects.create(profile=self.profile)
        self.url = f"/api/emails/preferences/{self.sub.unsubscribe_token}/"

    def test_get_returns_streams_and_state(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        keys = {s["key"] for s in body["streams"]}
        self.assertEqual(keys, set(STREAM_KEYS))
        self.assertTrue(all(s["enabled"] for s in body["streams"]))
        self.assertFalse(body["unsubscribed_all"])
        self.assertIn("pt", {loc["code"] for loc in body["locales"]})

    def test_post_saves_stream_choices(self):
        res = self.client.post(
            self.url,
            data=json.dumps({"streams": {"digest": False, "bogus": True}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.stream_prefs["digest"])
        # An unknown stream key is ignored, never stored.
        self.assertNotIn("bogus", self.sub.stream_prefs)

    def test_post_sets_and_clears_locale_override(self):
        self.client.post(
            self.url,
            data=json.dumps({"email_locale": "pt"}),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.email_locale, "pt")
        self.client.post(
            self.url,
            data=json.dumps({"email_locale": ""}),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.email_locale, "")

    def test_post_rejects_unknown_locale(self):
        self.client.post(
            self.url,
            data=json.dumps({"email_locale": "zz"}),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.email_locale, "")

    def test_post_toggles_master_switch(self):
        self.client.post(
            self.url,
            data=json.dumps({"unsubscribed_all": True}),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.unsubscribed_all)
        self.client.post(
            self.url,
            data=json.dumps({"unsubscribed_all": False}),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.unsubscribed_all)

    def test_unknown_token_is_404(self):
        self.assertEqual(self.client.get("/api/emails/preferences/nope/").status_code, 404)
        self.assertEqual(
            self.client.post(
                "/api/emails/preferences/nope/",
                data="{}",
                content_type="application/json",
            ).status_code,
            404,
        )

    def test_bad_payload_is_400(self):
        res = self.client.post(
            self.url, data="not json", content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)


def _series(slug="portraits", n=3, language="en", published=True):
    """A series with ``n`` numbered, published volumes. Returns (series, [books])."""
    series = Series.objects.create(slug=slug, title=slug.replace("-", " ").title())
    author = Author.objects.create(slug=f"auth-{slug}", name="Author")
    books = [
        Book.objects.create(
            author=author,
            slug=f"{slug}-{i}",
            language=language,
            title=f"Volume {i}",
            series=series,
            series_position=i,
            is_published=published,
        )
        for i in range(1, n + 1)
    ]
    return series, books


def _finish(profile, book, when=None):
    ReadingProgress.objects.create(
        profile=profile,
        kind=WorkKind.BOOK,
        book_slug=book.slug,
        language=book.language,
        finished_at=when or timezone.now(),
    )


def _start(profile, book):
    ReadingProgress.objects.create(
        profile=profile, kind=WorkKind.BOOK, book_slug=book.slug, language=book.language
    )


class NextSeriesVolumeTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()

    def test_recommends_the_volume_after_the_furthest_finished(self):
        _series(n=3)
        _finish(self.profile, Book.objects.get(slug="portraits-1"))
        pick = next_series_volume(self.profile)
        self.assertIsNotNone(pick)
        finished_book, next_book = pick
        self.assertEqual(finished_book.slug, "portraits-1")
        self.assertEqual(next_book.slug, "portraits-2")

    def test_uses_furthest_finished_not_earliest(self):
        _series(n=4)
        _finish(self.profile, Book.objects.get(slug="portraits-1"))
        _finish(self.profile, Book.objects.get(slug="portraits-2"))
        _, next_book = next_series_volume(self.profile)
        self.assertEqual(next_book.slug, "portraits-3")

    def test_none_when_next_already_opened(self):
        _series(n=3)
        _finish(self.profile, Book.objects.get(slug="portraits-1"))
        _start(self.profile, Book.objects.get(slug="portraits-2"))
        self.assertIsNone(next_series_volume(self.profile))

    def test_none_on_last_volume(self):
        _series(n=3)
        _finish(self.profile, Book.objects.get(slug="portraits-3"))
        self.assertIsNone(next_series_volume(self.profile))

    def test_none_for_unordered_collection(self):
        # A collection has no series_position, so there is no "next".
        series = Series.objects.create(slug="kt", title="Key Teachings")
        author = Author.objects.create(slug="auth-kt", name="A")
        b1 = Book.objects.create(author=author, slug="kt-1", language="en", title="One", series=series)
        Book.objects.create(author=author, slug="kt-2", language="en", title="Two", series=series)
        _finish(self.profile, b1)
        self.assertIsNone(next_series_volume(self.profile))

    def test_skips_unpublished_next_volume(self):
        series, books = _series(n=3)
        books[1].is_published = False  # volume 2 unpublished
        books[1].save(update_fields=["is_published"])
        _finish(self.profile, books[0])
        _, next_book = next_series_volume(self.profile)
        self.assertEqual(next_book.slug, "portraits-3")

    def test_next_must_exist_in_readers_language(self):
        # The series has en 1-2 but only pt 1; a pt reader finishing pt vol 1
        # has no pt vol 2 to go to.
        _series(n=2, language="en")
        series = Series.objects.get(slug="portraits")
        author = Author.objects.get(slug="auth-portraits")
        pt1 = Book.objects.create(
            author=author, slug="portraits-pt-1", language="pt", title="Vol 1",
            series=series, series_position=1,
        )
        _finish(self.profile, pt1)
        self.assertIsNone(next_series_volume(self.profile))

    def test_picks_the_most_recently_finished_series(self):
        _series(slug="alpha", n=2)
        _series(slug="beta", n=2)
        _finish(self.profile, Book.objects.get(slug="alpha-1"), when=timezone.now() - timedelta(days=5))
        _finish(self.profile, Book.objects.get(slug="beta-1"), when=timezone.now())
        _, next_book = next_series_volume(self.profile)
        self.assertEqual(next_book.slug, "beta-2")

    def test_volume_read_in_another_language_is_not_recommended(self):
        # Progress is one row per (profile, slug), so a volume read in any
        # language counts as read — don't recommend another edition of it.
        series = Series.objects.create(slug="x", title="X")
        author = Author.objects.create(slug="ax", name="A")
        for lang in ("en", "pt"):
            for i in (1, 2):
                Book.objects.create(
                    author=author, slug=f"x-{i}", language=lang, title=f"V{i} {lang}",
                    series=series, series_position=i,
                )
        _finish(self.profile, Book.objects.get(slug="x-1", language="pt"))
        _finish(self.profile, Book.objects.get(slug="x-2", language="en"))
        # The pt edition of volume 2 must NOT be offered — volume 2 is read.
        self.assertIsNone(next_series_volume(self.profile))


class SeriesCandidateProfilesTests(TestCase):
    def test_window_includes_recent_finishers_only(self):
        _series(n=2)
        vol1 = Book.objects.get(slug="portraits-1")
        recent = _make_profile(email="recent@example.com")
        old = _make_profile(email="old@example.com")
        unstarted = _make_profile(email="none@example.com")
        _finish(recent, vol1, when=timezone.now())
        _finish(old, vol1, when=timezone.now() - timedelta(days=60))
        _start(unstarted, vol1)  # started but not finished

        cutoff = timezone.now() - timedelta(days=30)
        ids = set(series_candidate_profiles(cutoff).values_list("id", flat=True))
        self.assertIn(recent.id, ids)
        self.assertNotIn(old.id, ids)
        self.assertNotIn(unstarted.id, ids)


@SENDING
class SeriesNudgeSendTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        _series(n=3)
        _finish(self.profile, Book.objects.get(slug="portraits-1"))

    @mock.patch("emails.sending.send_email", return_value="rid-series")
    def test_sends_once_and_is_idempotent(self, send):
        message = send_series_due(self.profile)
        self.assertIsNotNone(message)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(message.kind, EmailKind.LIFECYCLE)
        self.assertEqual(message.lifecycle_step, "finish_series")
        self.assertIn("finish_series:portraits-2", message.idempotency_key)
        # Same run: the 20h min-gap prevents a second nudge.
        self.assertIsNone(send_series_due(self.profile))
        # Even past the gap, the per-volume idempotency key means the same nudge
        # never re-sends — deliver returns the existing SENT row untouched.
        EmailMessage.objects.filter(pk=message.pk).update(
            sent_at=timezone.now() - timedelta(hours=48)
        )
        again = send_series_due(self.profile)
        self.assertEqual(again.pk, message.pk)
        self.assertEqual(send.call_count, 1)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_opting_out_of_series_stream_blocks_it(self, send):
        sub = EmailSubscription.objects.create(
            profile=self.profile, stream_prefs={"series": False}
        )
        self.assertIsNone(send_series_due(self.profile))
        send.assert_not_called()
        # Onboarding is a different stream and stays on.
        self.assertTrue(sub.wants(EmailKind.LIFECYCLE))

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_min_gap_blocks_a_nudge_right_after_a_drip(self, send):
        EmailMessage.objects.create(
            recipient=self.profile,
            to_email="reader@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step="welcome",
            idempotency_key="lifecycle:welcome:x",
            status=SendStatus.SENT,
            sent_at=timezone.now(),
        )
        self.assertIsNone(send_series_due(self.profile))
        send.assert_not_called()

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_no_next_volume_sends_nothing(self, send):
        other = _make_profile(email="other@example.com")
        self.assertIsNone(send_series_due(other))
        send.assert_not_called()


@SENDING
class SeriesNudgeRenderTests(TestCase):
    def test_fills_titles_and_points_cta_at_next_volume(self):
        profile = _make_profile(locale="en", name="Pat")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_series_nudge(
            profile, sub,
            finished_title="Watchman Nee: A Life",
            next_title="John Hyde: A Life",
            cta_path="books/john-hyde-a-life/",
        )
        self.assertIn("John Hyde: A Life", rendered.html)
        self.assertIn("Watchman Nee: A Life", rendered.html)
        self.assertIn("/books/john-hyde-a-life/", rendered.html)
        self.assertIn("John Hyde: A Life", rendered.subject)

    def test_localizes_to_reader_language(self):
        profile = _make_profile(locale="pt", name="Ana")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_series_nudge(
            profile, sub, finished_title="A", next_title="B", cta_path="pt/books/b/"
        )
        self.assertIn("A história continua", rendered.subject)


class SeriesStreamRoutingTests(TestCase):
    def setUp(self):
        self.sub = EmailSubscription.objects.create(profile=_make_profile())

    def test_finish_series_step_routes_to_series_stream(self):
        self.sub.stream_prefs = {"series": False}
        self.assertFalse(self.sub.wants(EmailKind.LIFECYCLE, "finish_series"))
        # A plain lifecycle email (no step) stays on the onboarding stream.
        self.assertTrue(self.sub.wants(EmailKind.LIFECYCLE))

    def test_onboarding_optout_does_not_block_series(self):
        self.sub.stream_prefs = {"onboarding": False}
        self.assertFalse(self.sub.wants(EmailKind.LIFECYCLE))
        self.assertTrue(self.sub.wants(EmailKind.LIFECYCLE, "finish_series"))


def _finish_n_books(profile, n, when=None):
    """Create ``n`` finished book-progress rows for a profile."""
    for i in range(n):
        ReadingProgress.objects.create(
            profile=profile,
            kind=WorkKind.BOOK,
            book_slug=f"bk-{i}",
            language="en",
            finished_at=when or timezone.now(),
        )


class MilestoneDueTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()

    def test_none_below_first_milestone(self):
        _finish_n_books(self.profile, 2)  # first milestone is 3
        self.assertIsNone(due_milestone(self.profile))

    def test_exact_milestone(self):
        _finish_n_books(self.profile, 3)
        self.assertEqual(due_milestone(self.profile), 3)

    def test_highest_reached_not_backfilled(self):
        # Jumping straight to 6 books celebrates 5, never 3 afterwards.
        _finish_n_books(self.profile, 6)
        self.assertEqual(due_milestone(self.profile), 5)

    def test_count_counts_only_finished_books(self):
        _finish_n_books(self.profile, 3)
        # An unfinished book and a finished sermon don't count toward book count.
        ReadingProgress.objects.create(
            profile=self.profile, kind=WorkKind.BOOK, book_slug="wip", language="en"
        )
        ReadingProgress.objects.create(
            profile=self.profile, kind=WorkKind.SERMON, book_slug="serm",
            language="en", finished_at=timezone.now(),
        )
        self.assertEqual(finished_book_count(self.profile), 3)
        self.assertEqual(due_milestone(self.profile), 3)

    def test_already_celebrated_milestone_is_not_repeated(self):
        _finish_n_books(self.profile, 5)
        EmailMessage.objects.create(
            recipient=self.profile,
            to_email="x@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step="milestone",
            idempotency_key=f"lifecycle:milestone:5:{self.profile.pk}",
            status=SendStatus.SENT,
            sent_at=timezone.now(),
        )
        self.assertIsNone(due_milestone(self.profile))

    def test_all_defined_milestones_are_ascending(self):
        self.assertEqual(list(MILESTONES), sorted(MILESTONES))


@SENDING
class MilestoneSendTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        _finish_n_books(self.profile, 5)

    @mock.patch("emails.sending.send_email", return_value="rid-m")
    def test_sends_once_and_is_idempotent(self, send):
        message = send_milestone_due(self.profile)
        self.assertIsNotNone(message)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(message.lifecycle_step, "milestone")
        self.assertIn("milestone:5", message.idempotency_key)
        self.assertIn("5", message.subject)
        # Same run the min-gap blocks a repeat; even past the gap, the milestone
        # is already celebrated, so nothing more sends.
        self.assertIsNone(send_milestone_due(self.profile))
        EmailMessage.objects.filter(pk=message.pk).update(
            sent_at=timezone.now() - timedelta(hours=48)
        )
        self.assertIsNone(send_milestone_due(self.profile))
        self.assertEqual(send.call_count, 1)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_opting_out_of_milestones_stream_blocks_it(self, send):
        sub = EmailSubscription.objects.create(
            profile=self.profile, stream_prefs={"milestones": False}
        )
        self.assertIsNone(send_milestone_due(self.profile))
        send.assert_not_called()
        self.assertTrue(sub.wants(EmailKind.LIFECYCLE))  # onboarding unaffected

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_below_milestone_sends_nothing(self, send):
        other = _make_profile(email="other@example.com")
        _finish_n_books(other, 1)
        self.assertIsNone(send_milestone_due(other))
        send.assert_not_called()


@SENDING
class MilestoneRenderTests(TestCase):
    def test_fills_count_and_localizes(self):
        profile = _make_profile(locale="en", name="Lee")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_milestone(profile, sub, milestone=10)
        self.assertIn("10 books", rendered.html)
        self.assertIn("10", rendered.subject)
        self.assertIn("Lee", rendered.html)

    def test_localizes_to_reader_language(self):
        profile = _make_profile(locale="pt", name="Ana")
        sub = EmailSubscription.objects.create(profile=profile)
        rendered = render_milestone(profile, sub, milestone=5)
        self.assertIn("livros", rendered.subject.lower())
