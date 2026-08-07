"""Ingest public-domain books from direct PDF URLs (source="pdf" in the catalog).

For clean digital PDFs that exist nowhere in HTML (e.g. the official C&MA
editions of A. B. Simpson). Reuses the ochorus.com importer's PDF machinery —
PyMuPDF block extraction and the marker/font-size chapterizer — but resolves
the book from ``catalog.py`` instead of scraping a landing page, and upserts
through ``ingest.upsert_book`` like the other catalog importers.

    python manage.py import_pdf                        # all pdf-sourced books
    python manage.py import_pdf the-gospel-of-healing  # one book by slug
"""

from __future__ import annotations

import requests
from django.core.management.base import BaseCommand, CommandError

from library import english_audit
from library.catalog import BOOKS, BookEntry
from library.ingest import clean_title, upsert_book, word_count
from library.management.commands.import_ochorus import UA, chapterize, pdf_blocks


def fetch_pdf(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    resp.raise_for_status()
    return resp.content


class Command(BaseCommand):
    help = "Import public-domain books from direct PDF URLs."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all pdf books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "pdf" and (not wanted or b.slug in wanted)]
        unknown = wanted - {b.slug for b in BOOKS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (pdf:{entry.source_ref})")
        try:
            blocks, body_size = pdf_blocks(fetch_pdf(entry.source_ref))
        except (requests.RequestException, RuntimeError) as exc:
            self.stderr.write(self.style.ERROR(f"  PDF failed: {exc}"))
            return
        chapters = [(clean_title(t), b) for t, b in chapterize(blocks, body_size)]
        # Front matter (title page + CONTENTS) sometimes segments into a stub
        # chapter that steals a real chapter's heading from the contents list.
        # When a title occurs twice, keep only the substantive occurrence.
        best: dict[str, int] = {}
        for i, (t, b) in enumerate(chapters):
            if t not in best or word_count(b) > word_count(chapters[best[t]][1]):
                best[t] = i
        chapters = [c for i, c in enumerate(chapters) if best[c[0]] == i]
        if not chapters:
            self.stderr.write(self.style.ERROR("  no chapters detected — aborted"))
            return
        book = upsert_book(entry, chapters)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
