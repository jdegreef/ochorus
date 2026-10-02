"""Record today's language-health score for every language.

The admin scoreboard draws its weekly trend from these rows. The page writes
today's point itself when opened; this command lets a deploy (``release``) or a
scheduler write it too, so the trend has a point on days nobody looked.
Idempotent: one row per language per day, re-running updates it.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from library.admin_views.health import AdminLanguageHealthView, record_snapshots


class Command(BaseCommand):
    help = "Upsert today's per-language health score (the scoreboard's trend)."

    def handle(self, *args, **opts):
        rows = AdminLanguageHealthView.compute()["languages"]
        record_snapshots(rows, timezone.localdate())
        self.stdout.write(f"Recorded health for {len(rows)} languages.")
