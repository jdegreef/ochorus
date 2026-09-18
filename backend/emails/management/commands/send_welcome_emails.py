"""Send the welcome email to readers who are due one.

Run by hand for now; Phase 1's Render cron calls it on a timer. Safe to run
repeatedly — the idempotency key means no reader is welcomed twice.

The ``cutoff`` gate is a guard against a first run mailing the whole back
catalogue: only accounts created on/after it are in scope. It defaults to
``EMAIL_WELCOME_START`` (a setting), or, unset, to a short recent window. Reach
further back deliberately with ``--since`` or ``--days``.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from emails.lifecycle import profiles_awaiting_welcome, send_welcome
from emails.models import SendStatus

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW_DAYS = 2


def _parse_cutoff(value: str):
    """Parse an ISO datetime OR date (midnight) into an aware datetime.

    Accepting a bare date matters: a cutoff is naturally written '2026-09-17',
    which ``parse_datetime`` alone returns ``None`` for — silently dropping the
    value. Returns ``None`` only when the string is neither.
    """
    parsed = parse_datetime(value)
    if parsed is None:
        day = parse_date(value)
        if day is not None:
            parsed = datetime.combine(day, time.min)
    if parsed is None:
        return None
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


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
            parsed = _parse_cutoff(opts["since"])
            if parsed is None:
                raise CommandError(f"could not parse --since: {opts['since']!r}")
            return parsed
        if opts.get("days") is not None:
            return timezone.now() - timedelta(days=opts["days"])
        configured = getattr(settings, "EMAIL_WELCOME_START", "")
        if configured:
            parsed = _parse_cutoff(configured)
            if parsed is not None:
                return parsed
            # Set but unparseable: warn rather than silently narrow to the
            # default window (which would send to a wider set than intended).
            logger.warning(
                "EMAIL_WELCOME_START=%r is not a valid date/datetime; "
                "using the default %d-day window.",
                configured,
                _DEFAULT_WINDOW_DAYS,
            )
        return timezone.now() - timedelta(days=_DEFAULT_WINDOW_DAYS)
