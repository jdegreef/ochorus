"""Run the whole email cron in one process: lifecycle sweep, series nudges,
milestone cards, then due broadcasts — and, once a day, the nightly content
audit (``audit_scan``).

A single command exists so the cron's ``dockerCommand`` needs **no shell** —
Render runs a cron command argv-style (it does not wrap it in a shell), and it
keeps literal quotes, so chaining two commands with ``&&`` (unrecognized-args
crash) or wrapping in ``sh -c '…'`` (status 127, the quoted string treated as one
command name) both fail. Chaining here in Python sidesteps all of that: the cron
runs ``uv run python manage.py send_email_cron`` with no operators or quotes.
"""

from __future__ import annotations

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Run the lifecycle sweep, event sweeps (series, milestones), then broadcasts, "
        "then the nightly content audit if due."
    )

    def handle(self, *args, **options):
        # Order is priority: every lifecycle-kind sweep shares the 20h min-gap, so
        # whichever runs first claims a reader's slot for the day. Onboarding, then
        # the "keep reading" series nudge, then the milestone celebration.
        call_command("send_lifecycle_emails")
        call_command("send_series_nudges")
        call_command("send_milestone_cards")
        call_command("send_due_broadcasts")
        # The nightly content audit rides this cron rather than a second paid
        # Render cron service: `--if-due` makes it a no-op on all but one tick a
        # day. Isolated so an audit failure can never fail the email sweep (and
        # the next tick simply retries — "due" holds until a scan is recorded).
        try:
            call_command("audit_scan", "--if-due")
        except Exception:
            logger.exception("audit_scan failed")
