"""Run the whole email cron in one process: lifecycle sweep, then due broadcasts.

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
    help = "Run the lifecycle email sweep, then send any due broadcasts."

    def handle(self, *args, **options):
        call_command("send_lifecycle_emails")
        call_command("send_due_broadcasts")
