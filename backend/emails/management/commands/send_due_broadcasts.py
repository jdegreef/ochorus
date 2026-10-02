"""Work the broadcast send queue: start due schedules, then send in batches.

The email cron runs this after the lifecycle sweep. A scheduled broadcast whose
time has come is moved into the queue (SENDING); every queued broadcast is then
sent in batches (emails/broadcasts.py) until it finishes or this run's time
budget (``EMAIL_SEND_BUDGET_SECONDS``) is spent — a large send simply continues
on the next run. Safe to run repeatedly and concurrently: each recipient's send
is idempotent and a lease keeps one worker per broadcast.
"""

from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from emails.broadcasts import promote_due, run_send, send_broadcast, sending_queue


class Command(BaseCommand):
    help = "Start due scheduled broadcasts and send queued ones in batches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            type=int,
            help="Queue this broadcast now (if it isn't already) and send it to the end, "
            "ignoring the time budget.",
        )

    def handle(self, *args, **opts):
        if opts.get("id"):
            from emails.models import Broadcast, BroadcastStatus

            broadcast = Broadcast.objects.filter(pk=opts["id"]).first()
            if broadcast is None:
                self.stderr.write(f"no broadcast #{opts['id']}")
                return
            if not (broadcast.can_send or broadcast.status == BroadcastStatus.SENDING):
                self.stderr.write(f"broadcast #{broadcast.pk} is {broadcast.status}; not sending")
                return
            tally = send_broadcast(broadcast)
            broadcast.refresh_from_db()
            self.stdout.write(
                self.style.SUCCESS(f"broadcast #{broadcast.pk} ({broadcast.status}): {tally}")
            )
            return

        started = promote_due()
        deadline = time.monotonic() + settings.EMAIL_SEND_BUDGET_SECONDS
        worked = 0
        for broadcast in sending_queue():
            if time.monotonic() >= deadline:
                break
            tally = run_send(broadcast, deadline=deadline)
            broadcast.refresh_from_db()
            worked += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"broadcast #{broadcast.pk} ({broadcast.name}): {tally} → {broadcast.status}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(f"broadcasts started: {started}; worked on: {worked}")
        )
