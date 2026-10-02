"""Tests for the batched broadcast send (pause/resume/cancel, the guardrail, the
lease), the pre-send checks, and direct one-to-one email."""

from __future__ import annotations

import io
import json
import time
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from library.models import AdminAction

from . import broadcasts as broadcasts_mod
from .broadcasts import _Pacer, run_send, send_test, start_send
from .models import (
    Broadcast,
    BroadcastStatus,
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    SendStatus,
)
from .preflight import run as run_checks
from .tests import SENDING, _broadcast, _make_profile


def _codes(checks, level):
    return {c["code"] for c in checks if c["level"] == level}


class _AdminClientMixin:
    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def _act(self, broadcast, action, **extra):
        return self._post(
            f"/api/admin/broadcasts/{broadcast.pk}/action/", {"action": action, **extra}
        )


@SENDING
@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
@mock.patch.object(broadcasts_mod, "BATCH_SIZE", 2)
class BatchedSendTests(_AdminClientMixin, TestCase):
    def setUp(self):
        self.profiles = [_make_profile(email=f"r{i}@example.com") for i in range(5)]

    def _sent_to(self):
        return sorted(
            EmailMessage.objects.filter(kind=EmailKind.BROADCAST, status=SendStatus.SENT)
            .values_list("to_email", flat=True)
        )

    def test_pause_stops_after_the_batch_and_resume_finishes_without_duplicates(self):
        b = _broadcast()
        start_send(b)
        calls = []

        def send(**kw):
            calls.append(kw["to"])
            if len(calls) == 2:  # the admin presses Pause during the first batch
                self._act(b, "pause")
            return "rid"

        with mock.patch("emails.sending.send_email", side_effect=send):
            run_send(b)
            b.refresh_from_db()
            self.assertEqual(b.status, BroadcastStatus.PAUSED)
            self.assertTrue(b.status_reason.startswith("Paused by"))
            self.assertEqual(len(calls), 2)
            self.assertEqual(b.send_cursor, self.profiles[1].pk)

            res = self._act(b, "resume")
            self.assertEqual(res.status_code, 200)
            run_send(Broadcast.objects.get(pk=b.pk))

        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.SENT)
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(set(calls)), 5)
        self.assertEqual(b.send_tally, {"sent": 5, "skipped": 0, "failed": 0})

    def test_cancel_mid_send_stops_and_stays_canceled(self):
        b = _broadcast()
        start_send(b)
        calls = []

        def send(**kw):
            calls.append(kw["to"])
            if len(calls) == 1:
                self._act(b, "cancel")
            return "rid"

        with mock.patch("emails.sending.send_email", side_effect=send):
            run_send(b)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.CANCELED)
        self.assertEqual(len(calls), 2)  # finishes the batch it was in, no more

    def test_deadline_leaves_it_sending_for_the_next_run(self):
        b = _broadcast()
        start_send(b)
        with mock.patch("emails.sending.send_email", return_value="rid"):
            run_send(b, deadline=time.monotonic() - 1)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.SENDING)
        self.assertEqual(self._sent_to(), [])
        self.assertIsNone(b.send_lease_until)  # released for the next run

    def test_a_held_lease_keeps_a_second_worker_out(self):
        b = _broadcast()
        start_send(b)
        Broadcast.objects.filter(pk=b.pk).update(
            send_lease_until=timezone.now() + timedelta(minutes=2)
        )
        with mock.patch("emails.sending.send_email", return_value="rid") as send:
            tally = run_send(b)
        send.assert_not_called()
        self.assertEqual(tally, {"sent": 0, "skipped": 0, "failed": 0})

    @override_settings(EMAIL_GUARDRAIL_MIN_SENT=2, EMAIL_GUARDRAIL_BOUNCE_RATE=0.05)
    @mock.patch.object(broadcasts_mod, "GUARDRAIL_EVERY", 1)
    def test_guardrail_pauses_a_bouncing_send_and_resume_needs_an_override(self):
        b = _broadcast()
        start_send(b)

        def bounce(**kw):
            message = EmailMessage.objects.get(idempotency_key=kw["idempotency_key"])
            EmailEvent.objects.create(
                message=message, type=EventType.BOUNCED, occurred_at=timezone.now()
            )
            return "rid"

        with mock.patch("emails.sending.send_email", side_effect=bounce):
            run_send(b)
            b.refresh_from_db()
            self.assertEqual(b.status, BroadcastStatus.PAUSED)
            self.assertIn("Bounce rate", b.status_reason)
            self.assertEqual(len(self._sent_to()), 2)

            res = self._act(b, "resume")
            self.assertEqual(res.status_code, 409)
            self.assertTrue(res.json()["needs_override"])

            res = self._act(b, "resume", override_guardrail=True)
            self.assertEqual(res.status_code, 200)
            run_send(Broadcast.objects.get(pk=b.pk))

        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.SENT)
        self.assertTrue(b.guardrail_override)
        self.assertEqual(len(self._sent_to()), 5)

    def test_a_cancel_beats_a_stale_start(self):
        b = _broadcast(status=BroadcastStatus.SCHEDULED)
        stale = Broadcast.objects.get(pk=b.pk)
        self._act(b, "cancel")
        self.assertFalse(start_send(stale, [BroadcastStatus.SCHEDULED]))
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.CANCELED)

    def test_a_stale_copy_resumes_from_the_stored_cursor(self):
        b = _broadcast()
        start_send(b)
        stale = Broadcast.objects.get(pk=b.pk)  # cursor 0, as the cron loaded it
        with mock.patch("emails.sending.send_email", return_value="rid") as send:
            Broadcast.objects.filter(pk=b.pk).update(
                send_cursor=self.profiles[2].pk, send_tally={"sent": 3, "skipped": 0, "failed": 0}
            )
            run_send(stale)
        self.assertEqual(send.call_count, 2)  # only the two after the cursor
        b.refresh_from_db()
        self.assertEqual(b.send_tally["sent"], 5)

    def test_a_worker_that_lost_its_lease_stops_and_leaves_the_new_one(self):
        b = _broadcast()
        start_send(b)

        def steal(**kw):
            # Another worker takes over (as if this one's lease had expired).
            Broadcast.objects.filter(pk=b.pk).update(
                send_lease_until=timezone.now() + timedelta(minutes=9)
            )
            return "rid"

        with mock.patch("emails.sending.send_email", side_effect=steal) as send:
            run_send(b)
        self.assertEqual(send.call_count, 2)  # stopped after its batch
        b.refresh_from_db()
        self.assertIsNotNone(b.send_lease_until)  # the new holder's lease is kept
        self.assertEqual(b.send_cursor, 0)  # and its progress isn't overwritten

    def test_an_edit_does_not_write_back_send_state(self):
        b = _broadcast(status=BroadcastStatus.SCHEDULED)
        original = Broadcast.save

        def save(self_, *a, **kw):
            # The cron starts it between the edit's read and its write.
            Broadcast.objects.filter(pk=self_.pk).update(status=BroadcastStatus.SENDING)
            return original(self_, *a, **kw)

        with mock.patch.object(Broadcast, "save", save):
            res = self.client.patch(
                f"/api/admin/broadcasts/{b.pk}/",
                data=json.dumps({"name": "renamed"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.name, "renamed")
        self.assertEqual(b.status, BroadcastStatus.SENDING)

    def test_cron_starts_a_due_schedule(self):
        b = _broadcast(
            status=BroadcastStatus.SCHEDULED, scheduled_at=timezone.now() - timedelta(minutes=1)
        )
        out = io.StringIO()
        from . import audience as aud
        with mock.patch("emails.sending.send_email", return_value="rid"), mock.patch.object(
            broadcasts_mod, "_claim", wraps=broadcasts_mod._claim
        ) as claim, mock.patch(
            "emails.management.commands.send_due_broadcasts.run_send",
            wraps=broadcasts_mod.run_send,
        ) as rs:
            call_command("send_due_broadcasts", stdout=out)
        b.refresh_from_db()
        diag = (
            f"out={out.getvalue()!r} run_send={rs.call_args_list} claims={claim.call_count} "
            f"lease={b.send_lease_until} cursor={b.send_cursor} tally={b.send_tally} "
            f"profiles={[p.pk for p in self.profiles]} "
            f"aud={list(aud.resolve(b.audience).order_by('pk').values_list('pk', flat=True))} "
            f"all_b={list(Broadcast.objects.values_list('pk', 'status', 'send_lease_until'))}"
        )
        self.assertEqual(b.status, BroadcastStatus.SENT, diag)
        self.assertEqual(len(self._sent_to()), 5, diag)

    def test_a_due_schedule_that_now_fails_its_checks_goes_back_to_draft(self):
        b = _broadcast(
            subject={"en": ""},
            status=BroadcastStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )
        with mock.patch("emails.sending.send_email", return_value="rid") as send:
            call_command("send_due_broadcasts", stdout=io.StringIO())
        send.assert_not_called()
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.DRAFT)
        self.assertIn("subject line is empty", b.status_reason)

    def test_a_canceled_schedule_can_be_rescheduled_but_a_canceled_send_cannot(self):
        b = _broadcast(status=BroadcastStatus.CANCELED)
        res = self._act(b, "schedule", scheduled_at="2099-01-01T09:00:00Z")
        self.assertEqual(res.status_code, 200)
        c = _broadcast(status=BroadcastStatus.CANCELED, send_started_at=timezone.now())
        self.assertEqual(self._act(c, "send").status_code, 409)

    def test_a_paused_broadcast_cannot_be_edited_or_sent_again(self):
        b = _broadcast(status=BroadcastStatus.PAUSED)
        res = self.client.patch(
            f"/api/admin/broadcasts/{b.pk}/",
            data=json.dumps({"name": "renamed"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self._act(b, "send").status_code, 409)

    def test_pause_and_resume_are_audited(self):
        b = _broadcast()
        start_send(b)
        self._act(b, "pause")
        self._act(b, "resume")
        actions = list(AdminAction.objects.values_list("action", flat=True))
        self.assertIn(AdminAction.Action.BROADCAST_PAUSE, actions)
        self.assertIn(AdminAction.Action.BROADCAST_RESUME, actions)


class PacerTests(TestCase):
    def test_spaces_calls_by_the_rate(self):
        pacer = _Pacer(rate=2)
        with mock.patch("emails.broadcasts.time.sleep") as sleep:
            pacer.wait()
            pacer.wait()
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.5, delta=0.05)

    def test_rate_zero_never_sleeps(self):
        pacer = _Pacer(rate=0)
        with mock.patch("emails.broadcasts.time.sleep") as sleep:
            pacer.wait()
            pacer.wait()
        sleep.assert_not_called()


@override_settings(DEBUG=True)
class PreflightTests(_AdminClientMixin, TestCase):
    def setUp(self):
        _make_profile()

    def test_a_complete_broadcast_has_no_errors(self):
        checks = run_checks(_broadcast())
        self.assertEqual(_codes(checks, "error"), set())
        self.assertIn("content", _codes(checks, "ok"))
        self.assertIn("audience", _codes(checks, "ok"))

    def test_empty_subject_blocks_send_and_schedule(self):
        b = _broadcast(subject={"en": "  "})
        self.assertIn("subject:en", _codes(run_checks(b), "error"))
        res = self._act(b, "send")
        self.assertEqual(res.status_code, 409)
        self.assertIn("checks", res.json())
        res = self._act(b, "schedule", scheduled_at="2099-01-01T09:00:00Z")
        self.assertEqual(res.status_code, 409)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.DRAFT)

    def test_full_url_button_link_is_an_error(self):
        b = _broadcast(
            content={
                "en": {
                    "heading": "H",
                    "cta_label": "Go",
                    "cta_path": "https://ochorus.com/books",
                }
            }
        )
        self.assertIn("cta:en", _codes(run_checks(b), "error"))

    def test_label_without_path_and_path_without_label_warn(self):
        b = _broadcast(
            subject={"en": "Hi", "es": "Hola"},
            content={
                "en": {"heading": "H", "cta_label": "Go"},
                "es": {"heading": "H", "cta_path": "books"},
            },
        )
        self.assertTrue({"cta:en", "cta:es"} <= _codes(run_checks(b), "warning"))

    def test_readers_in_an_unwritten_language_are_flagged(self):
        _make_profile(email="es@example.com", locale="es")
        self.assertIn("coverage:es", _codes(run_checks(_broadcast()), "warning"))

    def test_empty_audience_warns(self):
        b = _broadcast(audience={"locale": "uk"})
        self.assertIn("audience", _codes(run_checks(b), "warning"))

    def test_half_written_language_warns(self):
        b = _broadcast(subject={"en": "Hi", "fr": "Salut"})
        self.assertIn("half:fr", _codes(run_checks(b), "warning"))

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_test_send_check_tracks_the_tested_version(self, send):
        b = _broadcast()
        self.assertIn("test", _codes(run_checks(b), "warning"))
        admin = _make_profile(email="admin@example.com")
        self.assertTrue(send_test(b, admin))
        self.assertIn("test", _codes(run_checks(b), "ok"))
        b.subject = {"en": "A new subject"}
        b.save()
        self.assertIn("test", _codes(run_checks(b), "warning"))

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_test_sends_stay_out_of_the_results(self, send):
        b = _broadcast()
        admin = _make_profile(email="admin@example.com")
        self.assertTrue(send_test(b, admin))
        self.assertTrue(send_test(b, admin))  # repeatable
        self.assertEqual(EmailMessage.objects.filter(is_test=True).count(), 2)
        data = self.client.get(f"/api/admin/broadcasts/{b.pk}/").json()
        self.assertEqual(data["stats"]["sent"], 0)
        rows = self.client.get(f"/api/admin/users/{admin.supabase_uid}/emails/").json()["messages"]
        self.assertEqual(rows[0]["label"], "September news (test)")

    def test_coverage_follows_the_email_language_preference(self):
        reader = _make_profile(email="pt@example.com", locale="en")
        EmailSubscription.objects.create(profile=reader, email_locale="pt")
        self.assertIn("coverage:pt", _codes(run_checks(_broadcast()), "warning"))

    def test_detail_includes_checks_and_progress(self):
        b = _broadcast()
        data = self.client.get(f"/api/admin/broadcasts/{b.pk}/").json()
        self.assertTrue(data["checks"])
        self.assertEqual(data["progress"], {"sent": 0, "skipped": 0, "failed": 0})


@override_settings(DEBUG=True)
class DirectEmailTests(_AdminClientMixin, TestCase):
    def setUp(self):
        self.profile = _make_profile(email="ana@example.com", locale="pt")
        self.url = f"/api/admin/users/{self.profile.supabase_uid}/emails/"

    def _send(self, **payload):
        body = {"subject": "Your question", "paragraphs": ["Hello Ana.", "Here is the PDF."]}
        body.update(payload)
        return self._post(self.url, body)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_sends_records_and_audits(self, send):
        res = self._send(cta_label="Download", cta_path="books/the-inner-chamber")
        self.assertEqual(res.status_code, 201, res.content)
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["to"], "ana@example.com")
        self.assertIn("Here is the PDF.", send.call_args.kwargs["html"])
        message = EmailMessage.objects.get(kind=EmailKind.DIRECT)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(message.body_text, "Hello Ana.\n\nHere is the PDF.")
        self.assertEqual(message.locale, "pt")
        history = res.json()["messages"]
        self.assertEqual(history[0]["label"], "Direct email")
        self.assertTrue(
            AdminAction.objects.filter(
                action=AdminAction.Action.EMAIL_DIRECT, target=f"user:{self.profile.supabase_uid}"
            ).exists()
        )

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_two_sends_are_two_emails(self, send):
        self._send()
        self._send()
        self.assertEqual(send.call_count, 2)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_never_writes_to_an_unsubscribed_or_suppressed_reader(self, send):
        sub = EmailSubscription.objects.create(profile=self.profile, unsubscribed_all=True)
        self.assertEqual(self._send().status_code, 400)
        sub.unsubscribed_all = False
        sub.save()
        sub.suppress("bounced")
        res = self._send()
        self.assertEqual(res.status_code, 400)
        self.assertIn("suppressed", res.json()["detail"])
        send.assert_not_called()

    @SENDING
    def test_validation(self):
        self.assertEqual(self._send(subject="").status_code, 400)
        self.assertEqual(self._send(paragraphs=[]).status_code, 400)
        res = self._send(cta_label="Go", cta_path="http://evil.test")
        self.assertEqual(res.status_code, 400)

    def test_sending_off_is_reported_not_claimed(self):
        res = self._send()  # EMAIL_ENABLED is off outside SENDING
        self.assertEqual(res.status_code, 409)
        self.assertTrue(res.json()["detail"].startswith("Not sent"))
        self.assertEqual(EmailMessage.objects.get().status, SendStatus.SKIPPED)
        # A refused send is not a successful admin write, so nothing is audited.
        self.assertFalse(AdminAction.objects.filter(action=AdminAction.Action.EMAIL_DIRECT).exists())

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_written_in_sets_the_email_language_not_the_readers(self, send):
        reader = _make_profile(email="ar@example.com", locale="ar")
        url = f"/api/admin/users/{reader.supabase_uid}/emails/"
        state = self.client.get(url).json()
        self.assertEqual(state["email_lang"]["code"], "ar")
        res = self._post(url, {"subject": "Hello", "paragraphs": ["Hi."], "lang": "en"})
        self.assertEqual(res.status_code, 201, res.content)
        html = send.call_args.kwargs["html"]
        self.assertNotIn('dir="rtl"', html)
        self.assertEqual(EmailMessage.objects.get(recipient=reader).locale, "en")

    def test_history_labels_and_unknown_reader(self):
        b = _broadcast()
        EmailMessage.objects.create(
            recipient=self.profile,
            to_email="ana@example.com",
            kind=EmailKind.BROADCAST,
            broadcast=b,
            idempotency_key=f"broadcast:{b.pk}:{self.profile.pk}",
            status=SendStatus.SENT,
        )
        rows = self.client.get(self.url).json()["messages"]
        self.assertEqual(rows[0]["label"], "September news")
        res = self.client.get("/api/admin/users/00000000-0000-0000-0000-000000000000/emails/")
        self.assertEqual(res.status_code, 404)


class LegacyRowMigrationTests(TestCase):
    def test_settles_stranded_sends_and_flags_old_tests(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module("emails.migrations.0005_batched_send_and_direct_email")
        stranded = _broadcast(status=BroadcastStatus.SENDING)
        profile = _make_profile()
        EmailMessage.objects.create(
            recipient=profile,
            to_email=profile.email,
            kind=EmailKind.BROADCAST,
            broadcast=stranded,
            idempotency_key=f"broadcast-test:{stranded.pk}:{profile.pk}:123",
            status=SendStatus.SENT,
        )
        migration.settle_legacy_rows(apps, None)
        stranded.refresh_from_db()
        self.assertEqual(stranded.status, BroadcastStatus.PAUSED)
        self.assertTrue(EmailMessage.objects.get().is_test)
