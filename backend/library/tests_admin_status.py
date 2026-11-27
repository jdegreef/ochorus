"""System status: job heartbeats and the email switches (/api/admin/status/)."""

from __future__ import annotations

from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .heartbeat import beat
from .models import JobHeartbeat

LIVE = {
    "EMAIL_ENABLED": True,
    "RESEND_API_KEY": "re_test",
    "API_PUBLIC_URL": "https://api.example.com",
    "PUBLIC_SITE_URL": "https://ochorus.example",
}


class HeartbeatTests(TestCase):
    def test_a_good_run_stamps_start_finish_and_ok(self):
        with beat("job"):
            pass
        row = JobHeartbeat.objects.get(name="job")
        self.assertIsNotNone(row.last_ok_at)
        self.assertEqual(row.last_error, "")
        self.assertEqual(row.runs, 1)
        with beat("job"):
            pass
        row.refresh_from_db()
        self.assertEqual(row.runs, 2)

    def test_a_failure_is_recorded_and_re_raised(self):
        with beat("job"):
            pass
        ok_at = JobHeartbeat.objects.get(name="job").last_ok_at
        with self.assertRaises(RuntimeError):
            with beat("job"):
                raise RuntimeError("Resend is down")
        row = JobHeartbeat.objects.get(name="job")
        self.assertIn("Resend is down", row.last_error)
        # The last GOOD run is kept, so the page can say how long it's been.
        self.assertEqual(row.last_ok_at, ok_at)

    def test_the_email_cron_beats_every_step(self):
        call_command("send_email_cron")
        names = set(JobHeartbeat.objects.values_list("name", flat=True))
        self.assertTrue(
            {"send_lifecycle_emails", "send_due_broadcasts", "audit_scan"} <= names
        )


@override_settings(DEBUG=True)
class StatusViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _jobs(self):
        res = self.client.get("/api/admin/status/")
        self.assertEqual(res.status_code, 200)
        return res.data, {j["name"]: j for j in res.data["jobs"]}

    def test_with_sending_off_a_silent_cron_is_paused_not_late(self):
        data, jobs = self._jobs()
        self.assertFalse(data["sending"]["enabled"])
        self.assertEqual(jobs["send_lifecycle_emails"]["state"], "paused")
        self.assertEqual(jobs["release"]["state"], "never")

    @override_settings(**LIVE)
    def test_states_with_sending_on(self):
        now = timezone.now()
        JobHeartbeat.objects.create(
            name="send_lifecycle_emails", last_started_at=now, last_ok_at=now
        )
        JobHeartbeat.objects.create(
            name="send_due_broadcasts",
            last_started_at=now - timedelta(hours=3),
            last_ok_at=now - timedelta(hours=3),
        )
        JobHeartbeat.objects.create(
            name="run_automations", last_started_at=now, last_error="KeyError: x"
        )
        data, jobs = self._jobs()
        self.assertTrue(data["sending"]["enabled"])
        self.assertEqual(jobs["send_lifecycle_emails"]["state"], "ok")
        self.assertEqual(jobs["send_due_broadcasts"]["state"], "late")
        self.assertEqual(jobs["run_automations"]["state"], "failing")
        self.assertEqual(jobs["send_series_nudges"]["state"], "never")
        self.assertEqual(data["worst"], "failing")

    def test_it_never_shows_a_secret(self):
        with self.settings(RESEND_API_KEY="re_secret_value"):
            res = self.client.get("/api/admin/status/")
        self.assertNotIn("re_secret_value", res.content.decode())
        self.assertTrue(res.data["sending"]["provider_key_set"])

    def test_requires_admin(self):
        res = self.client.get("/api/admin/status/", REMOTE_ADDR="203.0.113.9")
        self.assertIn(res.status_code, (401, 403))
