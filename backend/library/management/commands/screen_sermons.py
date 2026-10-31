"""Screen catalog sermons before importing them (see ``library.sermon_screen``).

Add candidate ``SermonEntry`` rows to ``sermon_catalog.SERMONS``, screen them,
delete the rows that fail, then ``import_sermons`` the rest:

    python manage.py screen_sermons                 # every entry with no fixture yet
    python manage.py screen_sermons slug-a slug-b   # just these

Nothing is written. Each line gives words, archaisms and -eth verbs per 10,000
words, page splits, the library work sharing most of its wording, the ending,
and any flags; a line with no flags is fit to import.
"""

from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand, CommandError

from library import archive_ocr, sermon_screen
from library.content_fixtures import sermon_fixture_path
from library.management.commands.import_sermons import (
    DELAY,
    AmbiguousSectionError,
    extract_entry,
)
from library.sermon_catalog import SERMONS


class Command(BaseCommand):
    help = "Screen catalog sermons for modernised text, overlap and furniture before import."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Sermon slugs (default: those not yet imported).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        unknown = wanted - {e.slug for e in SERMONS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        if wanted:
            entries = [e for e in SERMONS if e.slug in wanted]
        else:
            entries = [e for e in SERMONS if not sermon_fixture_path(e.slug, "en").exists()]
        if not entries:
            self.stdout.write("Nothing to screen: every catalog entry is already imported.")
            return
        self.stdout.write(f"Indexing the English library for overlap… ({len(entries)} to screen)")
        index = sermon_screen.LibraryIndex()
        taken = sermon_screen.taken_slugs()
        fit = 0
        for entry in entries:
            time.sleep(DELAY)
            try:
                body, ref, date = extract_entry(entry)
            except (requests.RequestException, AmbiguousSectionError, archive_ocr.SliceError) as exc:
                self.stdout.write(self.style.ERROR(f"✗ {entry.slug}: {exc}"))
                continue
            imported = sermon_fixture_path(entry.slug, "en").exists()
            r = sermon_screen.screen(
                entry.slug, body, index, sermon_screen.collides(entry.slug, taken, imported)
            )
            arch, eth = r.archaisms
            work, pct = r.overlap
            line = (
                f"{entry.slug} | {entry.scripture_ref or ref or '—'} {entry.preached_on or date or ''}"
                f" | {r.words} words | arch {arch}, -eth {eth} | splits {r.splits}"
                f" | overlap {pct}% {work} | …{r.ending}"
            )
            if r.flags:
                self.stdout.write(self.style.WARNING(f"⚠ {line}\n    flags: {', '.join(r.flags)}"))
            else:
                fit += 1
                self.stdout.write(self.style.SUCCESS(f"✓ {line}"))
        self.stdout.write(f"{fit} of {len(entries)} fit to import.")
