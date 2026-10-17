"""Run the admin-built automations (emails/automations.py): enrol readers whose
trigger happened since the last pass, then advance every run that is due.

Runs each email-cron pass. Safe to repeat: a reader enters an automation once,
and each email step is send-once per reader.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from emails.automations import run_due


class Command(BaseCommand):
    help = "Enrol readers into automations and advance the runs that are due."

    def handle(self, *args, **options):
        tally = run_due()
        self.stdout.write(f"automations: {tally['enrolled']} enrolled, {tally['advanced']} advanced")
