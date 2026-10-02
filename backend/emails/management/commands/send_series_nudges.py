"""Send due finish-the-series nudges.

The Render cron runs this each pass (chained after the lifecycle sweep and
broadcasts, in ``send_email_cron``). Safe to run repeatedly — each nudge is
send-once per (reader, next volume) via its idempotency key, and the 20h min-gap
keeps a reader from getting a nudge and a drip email in the same window.

Scope is readers who finished a book within the look-back window
(``EMAIL_SERIES_LOOKBACK_DAYS``, default 30; widen with ``--days`` or a date with
``--since``) — the window only bounds the scan, idempotency decides who's new.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from emails.models import SendStatus
from emails.series_nudge import (
    candidate_profiles,
    lookback_cutoff,
    next_series_volume,
    send_due,
)

# Reuse the lifecycle command's date parser so --since accepts a bare date too.
from .send_lifecycle_emails import _parse_cutoff


class Command(BaseCommand):
    help = "Send finish-the-series nudges to readers who finished a series volume."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since", help="ISO date/datetime; include finishes on/after it."
        )
        parser.add_argument(
            "--days", type=int, help="Include books finished within the last N days."
        )
        parser.add_argument(
            "--limit", type=int, default=1000, help="Max readers per run."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List who would be nudged (and toward what) without sending.",
        )

    def handle(self, *args, **opts):
        cutoff = self._cutoff(opts)
        candidates = candidate_profiles(cutoff)[: opts["limit"]]

        if opts["dry_run"]:
            self._dry_run(candidates, cutoff)
            return

        sent = skipped = failed = 0
        for profile in candidates:
            message = send_due(profile)
            if message is None:
                skipped += 1
            elif message.status == SendStatus.SENT:
                sent += 1
            elif message.status == SendStatus.SKIPPED:
                skipped += 1
            else:
                failed += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"series nudges: sent={sent} skipped={skipped} failed={failed}"
            )
        )

    def _dry_run(self, candidates, cutoff):
        due = 0
        for profile in candidates:
            pick = next_series_volume(profile)
            if pick is not None:
                due += 1
                finished_book, next_book = pick
                self.stdout.write(
                    f"would nudge {profile.pk} ({next_book.language}): "
                    f"{finished_book.slug} → {next_book.slug}"
                )
        self.stdout.write(
            self.style.SUCCESS(f"dry run: {due} due since {cutoff:%Y-%m-%d}")
        )

    def _cutoff(self, opts):
        if opts.get("since"):
            parsed = _parse_cutoff(opts["since"])
            if parsed is None:
                raise CommandError(f"could not parse --since: {opts['since']!r}")
            return parsed
        if opts.get("days") is not None:
            return timezone.now() - timedelta(days=opts["days"])
        return lookback_cutoff()
