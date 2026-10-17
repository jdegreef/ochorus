"""Build the system-made campaigns that are due: the monthly digest and "new in
your language" (emails/auto_emails.py).

Runs each email-cron pass, before ``send_due_broadcasts`` so one built without
approval goes out on the same pass. Safe to run repeatedly: each campaign is
built once per period (``Broadcast.auto_key`` is unique), and nothing is built
while its switch is off.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from emails.auto_emails import build_due


class Command(BaseCommand):
    help = "Build the monthly digest and 'new in your language' emails that are due."

    def handle(self, *args, **options):
        built = build_due()
        for broadcast in built:
            self.stdout.write(f"built {broadcast.auto_key} ({broadcast.status})")
        self.stdout.write(f"auto emails: {len(built)} built")
