"""The recorded content audit: AuditScan rows, the nightly command, its alert.

The alert is the part that must be right in BOTH directions — an integrity
defect that lands overnight has to reach the admins, and a library that merely
stays broken (or gets better) must not mail them every night, or the mail gets
filtered and the real one is missed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import content_audit
from .models import AuditDismissal, AuditScan, Author, Book, Chapter, Plan, PlanDay

ALERTING = {
    "EMAIL_ENABLED": True,
    "RESEND_API_KEY": "re_test",
    "API_PUBLIC_URL": "https://api.example.com",
    "PUBLIC_SITE_URL": "https://ochorus.example.com",
    "EMAIL_ALLOWLIST": set(),
    "ADMIN_EMAILS": {"a@example.com", "b@example.com"},
}


def _scan(**opts) -> AuditScan | None:
    call_command("audit_scan", stdout=StringIO(), **opts)
    return AuditScan.objects.first()


@override_settings(**ALERTING, AUDIT_SCAN_HOUR_UTC=3)
class AuditScanCommandTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(book=self.book, order=1, title="One", body_html="<p>Fine.</p>")
        Chapter.objects.create(book=self.book, order=2, title="Two", body_html="<p>Also fine.</p>")
        patcher = mock.patch("emails.resend_client.send_email", return_value="msg_1")
        self.send = patcher.start()
        self.addCleanup(patcher.stop)

    def _break(self):
        """Land an integrity defect: an edition with no chapters."""
        Book.objects.create(author=self.author, slug="empty", language="en", title="Empty Book")

    def test_stores_scope_and_every_checks_total(self):
        row = _scan()
        self.assertEqual(row.trigger, AuditScan.Trigger.SCHEDULE)
        self.assertEqual((row.editions_scanned, row.chapters_scanned), (1, 2))
        self.assertGreaterEqual(row.duration_ms, 0)
        self.assertEqual(set(row.integrity), set(content_audit.INTEGRITY_CHECKS))
        self.assertEqual(
            set(row.quality), {*content_audit.QUALITY_CHAPTER_CHECKS, "duplicate_titles"}
        )
        self.assertEqual(set(row.quality_accepted), set(row.quality))
        self.assertEqual(sum(row.integrity.values()), 0)

    def test_first_scheduled_scan_is_only_a_baseline(self):
        self._break()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.NONE)
        self.assertIn("baseline", row.alert_note)
        self.send.assert_not_called()

    def test_emails_each_admin_once_when_an_integrity_check_rises(self):
        _scan()
        self._break()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.SENT)
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(
            sorted(c.kwargs["to"] for c in self.send.call_args_list),
            ["a@example.com", "b@example.com"],
        )
        kw = self.send.call_args.kwargs
        self.assertIn("1 integrity check worsened", kw["subject"])
        self.assertIn("Books with no chapters", kw["html"])
        self.assertIn("0 → 1", kw["html"])
        self.assertIn("empty [en]", kw["html"])
        self.assertIn("https://ochorus.example.com/admin/audit", kw["html"])
        self.assertIn("empty_books 0→1", row.alert_note)

    def test_no_email_when_unchanged(self):
        self._break()
        _scan()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.NONE)
        self.send.assert_not_called()

    def test_no_email_when_improving(self):
        self._break()
        _scan()
        Book.objects.filter(slug="empty").delete()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.NONE)
        self.send.assert_not_called()

    def test_a_rise_on_top_of_existing_defects_alerts(self):
        self._break()
        _scan()
        Book.objects.create(author=self.author, slug="empty-2", language="en", title="Another")
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.SENT)
        self.assertIn("1 → 2", self.send.call_args.kwargs["html"])

    def test_quality_findings_never_alert(self):
        _scan()
        Chapter.objects.create(book=self.book, order=3, title="Chapter 3", body_html="<p>tiny</p>")
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.NONE)
        self.send.assert_not_called()

    def test_examples_are_capped(self):
        _scan()
        for i in range(15):
            Book.objects.create(author=self.author, slug=f"e{i:02}", language="en", title=f"E{i}")
        _scan()
        self.assertEqual(self.send.call_args.kwargs["html"].count("<li>"), 1 + 10)

    def test_a_manual_scan_does_not_swallow_the_nightly_alert(self):
        _scan()
        self._break()
        cache.clear()
        with override_settings(DEBUG=True):
            APIClient().get("/api/admin/audit/?refresh=1")
        manual = AuditScan.objects.first()
        self.assertEqual(manual.trigger, AuditScan.Trigger.MANUAL)
        self.assertEqual(manual.alert, AuditScan.Alert.NOT_EVALUATED)
        self.send.assert_not_called()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.SENT)

    def test_a_failed_alert_is_retried_by_the_next_scan(self):
        from emails.resend_client import ResendError

        _scan()
        self._break()
        self.send.side_effect = ResendError("down")
        self.assertEqual(_scan().alert, AuditScan.Alert.FAILED)
        self.send.side_effect = None
        self.send.return_value = "msg_2"
        self.assertEqual(_scan().alert, AuditScan.Alert.SENT)

    @override_settings(EMAIL_ENABLED=False)
    def test_email_off_records_skipped(self):
        _scan()
        self._break()
        row = _scan()
        self.assertEqual(row.alert, AuditScan.Alert.SKIPPED)
        self.send.assert_not_called()

    @override_settings(EMAIL_ALLOWLIST={"someone@else.com"})
    def test_review_mode_allowlist_applies(self):
        _scan()
        self._break()
        self.assertEqual(_scan().alert, AuditScan.Alert.SKIPPED)
        self.send.assert_not_called()

    def test_quality_totals_are_net_of_accepted_findings(self):
        Chapter.objects.create(book=self.book, order=3, title="Chapter 3", body_html="<p>Tiny.</p>")
        AuditDismissal.objects.create(
            check_key="generic_titles", book="humility", language="en", ref="3"
        )
        row = _scan()
        self.assertEqual(row.quality["generic_titles"], 0)
        self.assertEqual(row.quality_accepted["generic_titles"], 1)

    def test_retention_prunes_old_rows(self):
        old = AuditScan.objects.create(
            started_at=datetime.now(UTC) - timedelta(days=content_audit.RETENTION_DAYS + 1),
            trigger=AuditScan.Trigger.MANUAL,
        )
        kept = AuditScan.objects.create(
            started_at=datetime.now(UTC) - timedelta(days=content_audit.RETENTION_DAYS - 1),
            trigger=AuditScan.Trigger.MANUAL,
        )
        _scan()
        self.assertFalse(AuditScan.objects.filter(pk=old.pk).exists())
        self.assertTrue(AuditScan.objects.filter(pk=kept.pk).exists())


@override_settings(AUDIT_SCAN_HOUR_UTC=3)
class AuditScanScheduleTests(TestCase):
    def _at(self, hour, minute=0, day=2):
        return datetime(2026, 10, day, hour, minute, tzinfo=UTC)

    def _run(self, now):
        with mock.patch("django.utils.timezone.now", return_value=now):
            return content_audit.run_scheduled_scan(if_due=True, now=now)

    def test_runs_once_a_day_at_or_after_the_hour(self):
        self.assertIsNone(self._run(self._at(2, 45)), "before the hour: not due")
        self.assertIsNotNone(self._run(self._at(3, 0)))
        self.assertIsNone(self._run(self._at(3, 15)), "already ran today")
        self.assertIsNone(self._run(self._at(23, 45)))
        self.assertIsNotNone(self._run(self._at(3, 5, day=3)), "next day")
        self.assertEqual(AuditScan.objects.count(), 2)

    def test_a_missed_window_runs_later_the_same_day(self):
        self.assertIsNotNone(self._run(self._at(14, 0)))

    def test_a_manual_scan_does_not_count_as_the_nightly(self):
        AuditScan.objects.create(started_at=self._at(4), trigger=AuditScan.Trigger.MANUAL)
        self.assertIsNotNone(self._run(self._at(5)))

    def test_schedule_status(self):
        with mock.patch("django.utils.timezone.now", return_value=self._at(4)):
            self.assertEqual(content_audit.next_scheduled_at(), self._at(3))
            status = content_audit.schedule_status()
        self.assertIsNone(status["last_at"])
        self.assertTrue(status["overdue"], "an hour past the mark with no scan")
        self._run(self._at(4))
        with mock.patch("django.utils.timezone.now", return_value=self._at(5)):
            status = content_audit.schedule_status()
        self.assertEqual(status["next_at"], self._at(3, day=3).isoformat())
        self.assertFalse(status["overdue"])
        self.assertEqual(status["last_alert"], AuditScan.Alert.NONE)

    def test_email_cron_runs_the_audit_if_due_and_survives_its_failure(self):
        def fake(name, *args, **kwargs):
            if name == "audit_scan":
                raise RuntimeError("scan blew up")

        with mock.patch(
            "emails.management.commands.send_email_cron.call_command", side_effect=fake
        ) as cc, self.assertLogs("emails.management.commands.send_email_cron", "ERROR"):
            call_command("send_email_cron")  # does not raise
        self.assertIn(mock.call("audit_scan", "--if-due"), cc.call_args_list)


@override_settings(
    DEBUG=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class AuditPayloadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>Fine.</p>")
        Book.objects.create(author=author, slug="empty", language="en", title="Empty")
        plan = Plan.objects.create(slug="p1", language="en", title="Plan One")
        PlanDay.objects.create(plan=plan, day=1, book_slug="humility", chapter_order=9)

    def test_scope_and_schedule_in_payload(self):
        res = APIClient().get("/api/admin/audit/")
        self.assertEqual(res.status_code, 200)
        scan = res.data["scan"]
        self.assertEqual((scan["editions"], scan["chapters"]), (2, 1))
        self.assertEqual(scan["trigger"], "view")
        self.assertIsInstance(scan["duration_ms"], int)
        self.assertEqual(
            set(res.data["schedule"]), {"hour_utc", "last_at", "last_alert", "next_at", "overdue"}
        )
        self.assertFalse(AuditScan.objects.exists(), "opening the page records nothing")

    def test_rerun_records_a_manual_scan(self):
        res = APIClient().get("/api/admin/audit/?refresh=1")
        self.assertEqual(res.data["scan"]["trigger"], "manual")
        row = AuditScan.objects.get()
        self.assertEqual(row.trigger, AuditScan.Trigger.MANUAL)
        self.assertEqual(row.integrity["empty_books"], 1)
        self.assertEqual(row.integrity["broken_plan_days"], 1)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_rerun_requires_admin(self):
        res = APIClient().get("/api/admin/audit/?refresh=1")
        self.assertIn(res.status_code, (401, 403))
        self.assertFalse(AuditScan.objects.exists())
