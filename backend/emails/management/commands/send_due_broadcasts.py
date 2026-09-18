"""Send scheduled broadcasts whose time has come.

Phase 1's cron runs this alongside the lifecycle sweep. Safe to run repeatedly —
each recipient's send is idempotent, and a broadcast moves to ``sent`` when done.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from emails.broadcasts import due_broadcasts, send_broadcast


class Command(BaseCommand):
    help = "Send scheduled broadcasts whose scheduled_at has passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--id", type=int, help="Send this broadcast now, regardless of schedule."
        )

    def handle(self, *args, **opts):
        if opts.get("id"):
            from emails.models import Broadcast

            broadcast = Broadcast.objects.filter(pk=opts["id"]).first()
            if broadcast is None:
                self.stderr.write(f"no broadcast #{opts['id']}")
                return
            tally = send_broadcast(broadcast)
            self.stdout.write(self.style.SUCCESS(f"broadcast #{broadcast.pk}: {tally}"))
            return

        due = list(due_broadcasts())
        for broadcast in due:
            tally = send_broadcast(broadcast)
            self.stdout.write(
                self.style.SUCCESS(f"broadcast #{broadcast.pk} ({broadcast.name}): {tally}")
            )
        self.stdout.write(self.style.SUCCESS(f"due broadcasts sent: {len(due)}"))
