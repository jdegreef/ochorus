"""Prune old SearchQueryLog rows (release step).

The log exists for roadmap analytics, not history — the admin view reads at
most 30 days. 180 days of retention keeps seasonal comparison possible while
bounding table growth on the small shared database. Idempotent; a no-op
deploy deletes nothing.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from library.models import SearchClickLog, SearchQueryLog

RETENTION_DAYS = 180


class Command(BaseCommand):
    help = f"Delete search-log rows older than {RETENTION_DAYS} days."

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        # Both halves of the search log, on the same clock: the click log is
        # only meaningful next to the queries it belongs to, so outliving them
        # would leave click-through rates computed against a truncated
        # denominator.
        queries, _ = SearchQueryLog.objects.filter(created_at__lt=cutoff).delete()
        clicks, _ = SearchClickLog.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(
            f"Trimmed {queries} search-log and {clicks} click-log rows "
            f"older than {RETENTION_DAYS}d."
        )
