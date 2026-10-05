"""Send due reading-plan reminders.

The Render cron runs this every pass (``send_email_cron``, every 15 minutes).
A reader is due when their local time has reached the reminder time they set on
a plan they started (``PlanSchedule.remind_at``), on one of the plan's reading
days, and they haven't read yet today — see :mod:`emails.plan_reminders`. Safe
to run repeatedly: one plan email per reader per local day (idempotency key).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from emails.models import EmailSubscription
from emails.plan_reminders import candidates, due_plan_email, send_due
from emails.sweeps import run_sweep


class Command(BaseCommand):
    help = "Send reading-plan reminders that are due now."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="List who is due without sending."
        )

    def handle(self, *args, **opts):
        profiles = candidates()
        if opts["dry_run"]:
            now = timezone.now()
            due = 0
            for profile in profiles:
                sub, _ = EmailSubscription.objects.get_or_create(profile=profile)
                hit = due_plan_email(profile, sub, now)
                if hit is not None:
                    due += 1
                    self.stdout.write(f"would send {hit.step} to {profile.pk}: {hit.plan.slug} day {hit.day.day}")
            self.stdout.write(self.style.SUCCESS(f"dry run: {due} due"))
            return
        sent, skipped, failed = run_sweep(profiles, send_due)
        self.stdout.write(
            self.style.SUCCESS(f"plan reminders: sent={sent} skipped={skipped} failed={failed}")
        )
