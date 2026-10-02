"""Run the whole email cron in one process: lifecycle sweep, series nudges,
milestone cards, then due broadcasts.

A single command exists so the cron's ``dockerCommand`` needs **no shell** —
Render runs a cron command argv-style (it does not wrap it in a shell), and it
keeps literal quotes, so chaining two commands with ``&&`` (unrecognized-args
crash) or wrapping in ``sh -c '…'`` (status 127, the quoted string treated as one
command name) both fail. Chaining here in Python sidesteps all of that: the cron
runs ``uv run python manage.py send_email_cron`` with no operators or quotes.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the lifecycle sweep, event sweeps (series, milestones), then broadcasts."

    def handle(self, *args, **options):
        # Order is priority: every lifecycle-kind sweep shares the 20h min-gap, so
        # whichever runs first claims a reader's slot for the day. Onboarding, then
        # the "keep reading" series nudge, then the milestone celebration.
        call_command("send_lifecycle_emails")
        call_command("send_series_nudges")
        call_command("send_milestone_cards")
        call_command("send_due_broadcasts")
