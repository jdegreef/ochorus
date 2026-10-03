"""Run the content audit, record it, and alert if data integrity got worse.

The nightly form is ``audit_scan --if-due``, called by ``send_email_cron`` (the
existing 15-minute Render cron) — it does nothing except once per UTC day, at or
after ``AUDIT_SCAN_HOUR_UTC``. Without ``--if-due`` it scans now, which also
counts as the day's scheduled scan. Either way it uses the same scan as the
admin audit page (``library.content_audit``), stores an ``AuditScan``, emails the
super admins if an integrity check rose since the previous scheduled scan, and
prunes rows older than the retention window. Safe to run repeatedly.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.content_audit import run_scheduled_scan


class Command(BaseCommand):
    help = "Scan the library (content audit), record the scan, alert on new integrity defects."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-due",
            action="store_true",
            help="Only scan if today's scheduled scan hasn't run yet (the cron's form).",
        )

    def handle(self, *args, **opts):
        row = run_scheduled_scan(if_due=opts["if_due"])
        if row is None:
            self.stdout.write("audit_scan: not due")
            return
        self.stdout.write(
            f"audit_scan: {row.editions_scanned} editions, {row.chapters_scanned} chapters "
            f"in {row.duration_ms} ms; integrity {row.integrity}; "
            f"alert={row.alert or '-'} {row.alert_note}".rstrip()
        )
