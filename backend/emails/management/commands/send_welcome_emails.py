"""Send the welcome email to readers who are due one.

Run by hand for now; Phase 1's Render cron calls it on a timer. Safe to run
repeatedly — the idempotency key means no reader is welcomed twice.

The ``cutoff`` gate is a guard against a first run mailing the whole back
catalogue: only accounts created on/after it are in scope. It defaults to
``EMAIL_WELCOME_START`` (a setting), or, unset, to a short recent window. Reach
further back deliberately with ``--since`` or ``--days``.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from emails.lifecycle import profiles_awaiting_welcome, send_welcome
from emails.models import SendStatus

_DEFAULT_WINDOW_DAYS = 2


class Command(BaseCommand):
    help = "Send the welcome email to readers who have not received one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            help="ISO datetime; only welcome accounts created on/after it.",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="Welcome accounts created within the last N days.",
        )
        parser.add_argument(
            "--limit", type=int, default=500, help="Max readers per run."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List who would be welcomed without sending.",
        )

    def handle(self, *args, **opts):
        cutoff = self._cutoff(opts)
        limit = opts["limit"]
        dry = opts["dry_run"]

        due = profiles_awaiting_welcome(cutoff)[:limit]
        sent = skipped = failed = 0
        for profile in due:
            if dry:
                self.stdout.write(f"would welcome: {profile.pk} ({profile.locale})")
                continue
            message = send_welcome(profile)
            if message is None:
                skipped += 1
            elif message.status == SendStatus.SENT:
                sent += 1
            elif message.status == SendStatus.SKIPPED:
                skipped += 1
            else:
                failed += 1

        if dry:
            self.stdout.write(self.style.SUCCESS(f"dry run: {len(due)} due since {cutoff:%Y-%m-%d}"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"welcome sweep: sent={sent} skipped={skipped} failed={failed}"
                )
            )

    def _cutoff(self, opts):
        if opts.get("since"):
            parsed = parse_datetime(opts["since"])
            if parsed is None:
                raise CommandError(f"could not parse --since: {opts['since']!r}")
            return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        if opts.get("days") is not None:
            return timezone.now() - timedelta(days=opts["days"])
        configured = getattr(settings, "EMAIL_WELCOME_START", "")
        if configured:
            parsed = parse_datetime(configured)
            if parsed is not None:
                return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        return timezone.now() - timedelta(days=_DEFAULT_WINDOW_DAYS)
