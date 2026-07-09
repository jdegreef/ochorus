"""Create fixture books that are missing from an already-seeded database.

``seed_if_empty`` only populates a *fresh* database, so a NEW book added to the
committed fixture never reaches an existing production DB on its own. This
command creates any fixture book (with its chapters, and its author if absent)
whose ``(slug, language)`` doesn't exist yet. Existing books are left entirely
alone — transforms of existing rows still ship as data migrations.

Runs on every deploy (see the release command); idempotent. Companion to
``seed_sermons``, which does the same for sermons (and also updates them).
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Author, Book, Chapter

FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "launch.json"

BOOK_FIELDS = (
    "title",
    "subtitle",
    "description",
    "source_type",
    "source_url",
    "cover_url",
    "pdf_url",
    "cover_color",
    "sort_order",
    "is_published",
)
CHAPTER_FIELDS = ("order", "title", "body_html", "word_count")


class Command(BaseCommand):
    help = "Create fixture books missing from an existing DB (deploy step)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            rows = json.loads(FIXTURE.read_text())
        except (OSError, ValueError):
            self.stdout.write("No fixture available — nothing to seed.")
            return

        authors = {
            r["pk"]: r["fields"] for r in rows if r.get("model") == "library.author"
        }
        chapters_by_book_pk: dict[int, list[dict]] = {}
        for r in rows:
            if r.get("model") == "library.chapter":
                chapters_by_book_pk.setdefault(r["fields"]["book"], []).append(
                    r["fields"]
                )

        created = 0
        for row in rows:
            if row.get("model") != "library.book":
                continue
            f = row["fields"]
            if Book.objects.filter(
                slug=f["slug"], language=f.get("language", "en")
            ).exists():
                continue
            af = authors.get(f["author"])
            if af is None:
                continue
            author, _ = Author.objects.get_or_create(
                slug=af["slug"],
                defaults={
                    "name": af.get("name", ""),
                    "bio": af.get("bio", ""),
                    "bio_html": af.get("bio_html", ""),
                    "photo_url": af.get("photo_url", ""),
                    "birth_year": af.get("birth_year"),
                    "death_year": af.get("death_year"),
                },
            )
            book = Book.objects.create(
                author=author,
                slug=f["slug"],
                language=f.get("language", "en"),
                **{k: f.get(k) for k in BOOK_FIELDS},
            )
            for cf in sorted(
                chapters_by_book_pk.get(row["pk"], []), key=lambda c: c["order"]
            ):
                # .create() runs save(), which derives body_text.
                Chapter.objects.create(
                    book=book, **{k: cf.get(k) for k in CHAPTER_FIELDS}
                )
            created += 1
            self.stdout.write(f"  + {book.slug} ({book.chapters.count()} chapters)")

        if created:
            self.stdout.write(self.style.SUCCESS(f"Books: {created} created."))
        else:
            self.stdout.write("Books already up to date.")
