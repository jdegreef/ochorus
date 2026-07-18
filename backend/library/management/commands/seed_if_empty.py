"""Load the content fixtures, but only if the library is empty.

Run on every deploy (after `migrate`); it populates a fresh production database
on first boot and is a no-op thereafter. Idempotent and safe to re-run.

The content lives as per-work files (see ``library.content_fixtures``). They
are passed to ONE ``loaddata`` call in dependency order — every FK is NOT NULL,
so Django cannot defer a forward reference: authors must load before books and
sermons, a book row before its chapters (same file), a plan before its days.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from library.content_fixtures import ordered_fixture_paths
from library.models import Book


class Command(BaseCommand):
    help = "Seed the library from fixtures/content/ if no books exist yet."

    def handle(self, *args, **opts):
        if Book.objects.exists():
            self.stdout.write("Library already populated; skipping seed.")
            return
        paths = ordered_fixture_paths()
        if not paths:
            raise CommandError(
                "seed_if_empty: no content fixtures found under "
                "library/fixtures/content/ — the split layout is required "
                "(see backend/scripts/regen_fixture.py)."
            )
        self.stdout.write(f"Empty library — loading {len(paths)} content fixture files…")
        call_command("loaddata", *[str(p) for p in paths], verbosity=0)
        self.stdout.write(self.style.SUCCESS(f"Seeded {Book.objects.count()} books."))
