"""Send due reading-milestone cards.

The Render cron runs this each pass (chained in ``send_email_cron``). Safe to run
repeatedly — each milestone is send-once per (reader, level) via its idempotency
key, and the 20h min-gap keeps a reader from getting a card and another lifecycle
email in the same window.

Scope is readers who finished a book within the look-back window
(``EMAIL_MILESTONE_LOOKBACK_DAYS``, default 30; widen with ``--days`` or a date
with ``--since``) — the window only bounds the scan, idempotency decides who's new.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from emails.milestones import due_milestone, lookback_cutoff, send_due
from emails.sweeps import recent_book_finishers, run_sweep

# Reuse the lifecycle command's date parser so --since accepts a bare date too.
from .send_lifecycle_emails import _parse_cutoff


class Command(BaseCommand):
    help = "Send reading-milestone cards to readers who reached a new milestone."

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
            help="List who would be congratulated (and at what level) without sending.",
        )

    def handle(self, *args, **opts):
        cutoff = self._cutoff(opts)
        candidates = recent_book_finishers(cutoff)[: opts["limit"]]

        if opts["dry_run"]:
            self._dry_run(candidates, cutoff)
            return

        sent, skipped, failed = run_sweep(candidates, send_due)
        self.stdout.write(
            self.style.SUCCESS(
                f"milestone cards: sent={sent} skipped={skipped} failed={failed}"
            )
        )

    def _dry_run(self, candidates, cutoff):
        due = 0
        for profile in candidates:
            milestone = due_milestone(profile)
            if milestone is not None:
                due += 1
                self.stdout.write(f"would congratulate {profile.pk}: {milestone} books")
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
