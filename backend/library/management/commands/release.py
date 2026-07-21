"""Run the pre-deploy / release steps in a single command.

Render's `preDeployCommand` runs one executable (not a shell), so we can't chain
`migrate && seed_if_empty` with `&&`. This command runs both in order: apply
migrations, then seed the library from the committed fixture if the DB is empty.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Apply migrations, then seed the library if empty (deploy step)."

    def handle(self, *args, **opts):
        self.stdout.write("→ migrate")
        call_command("migrate", interactive=False, verbosity=1)
        self.stdout.write("→ seed_if_empty")
        call_command("seed_if_empty")
        # Fixture loads bypass Chapter.save(), so derive search text afterwards.
        self.stdout.write("→ backfill_body_text")
        call_command("backfill_body_text")
        # Idempotent text repairs (no-op when the fixture is already fixed).
        self.stdout.write("→ apply_body_corrections")
        call_command("apply_body_corrections")
        # Create fixture books that are missing from an already-seeded DB.
        self.stdout.write("→ seed_books")
        call_command("seed_books")
        self.stdout.write("→ seed_plans")
        call_command("seed_plans")
        # Upsert fixture sermons into an already-seeded DB (new/updated ones).
        self.stdout.write("→ seed_sermons")
        call_command("seed_sermons")
        # Upsert unreviewed translated author bios from the in-repo data files
        # (AuthorTranslation has no fixture; reviewed rows are approver-owned).
        self.stdout.write("→ seed_author_translations")
        call_command("seed_author_translations")
        # Create/refresh the curated topical shelves.
        self.stdout.write("→ seed_topics")
        call_command("seed_topics")
        # Fixture loads bypass save(), so fill any NULL search vectors last —
        # after body_text exists and all seed steps have created their rows.
        # Citation index feeds scripture search; incremental after body edits.
        self.stdout.write("→ index_citations")
        call_command("index_citations")
        self.stdout.write("→ backfill_search_vectors")
        call_command("backfill_search_vectors")
        # Bound the anonymous search-analytics log (reads cover 30 days).
        self.stdout.write("→ trim_search_log")
        call_command("trim_search_log")
