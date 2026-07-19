"""Fill stored search vectors that fixture loads left NULL.

loaddata bypasses Chapter.save()/Sermon.save() (the same gap backfill_body_text
covers for body_text), so a freshly seeded database has NULL search_vector on
every row. This runs on every deploy (release step) and is a cheap no-op when
nothing is missing. ``--all`` rebuilds every vector — needed only after an
author or book rename, whose text is baked into dependent vectors (fts.py).

Postgres-only; on SQLite it reports and exits (dev search never reads vectors).

Ordering: must run AFTER backfill_body_text in the release chain — the vector
is built from body_text, so filling vectors first would bake in empty bodies.
"""

from django.core.management.base import BaseCommand
from django.db import connection

from library import fts


class Command(BaseCommand):
    help = "Populate NULL chapter/sermon search vectors (--all rebuilds every row)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Rebuild every vector, not just NULL ones (after a rename).",
        )

    def handle(self, *args, **opts):
        if connection.vendor != "postgresql":
            self.stdout.write("SQLite: search vectors unused, nothing to do.")
            return
        chapters, sermons = fts.backfill(only_null=not opts["all"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Search vectors filled: {chapters} chapters, {sermons} sermons."
            )
        )
