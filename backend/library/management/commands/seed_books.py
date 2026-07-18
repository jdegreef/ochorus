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

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.models import Author, Book, Chapter

FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "launch.json"

BOOK_FIELDS = (
    "title",
    "subtitle",
    "description",
    "publication_year",
    "source_type",
    "source_url",
    "attribution",
    "cover_url",
    "pdf_url",
    "cover_color",
    "sort_order",
    "is_published",
)
CHAPTER_FIELDS = ("order", "title", "body_html", "word_count")


def require_natural_format(rows, command_name: str):
    """Hard-fail on an old-format (integer-pk) fixture row.

    After the natural-key switch a stale pk-format row could silently
    mis-resolve (an integer FK "means" a different row against re-assigned
    pks) or silently skip. Loud failure here — inside the atomic seed — aborts
    the deploy instead of shipping wrong or missing content.
    """
    stale = [r for r in rows if "pk" in r]
    if not stale:
        # Hybrid hand-edits: no pk key but an integer FK — equally dangerous
        # (loaddata would resolve it against arbitrary auto-pks).
        fk = {"library.book": "author", "library.sermon": "author",
              "library.chapter": "book", "library.planday": "plan"}
        stale = [r for r in rows
                 if r.get("model") in fk
                 and not isinstance(r["fields"].get(fk[r["model"]]), list)]
    if stale:
        first = stale[0]
        raise CommandError(
            f"{command_name}: {len(stale)} old-format row(s) in launch.json "
            f"(first: {first.get('model')} "
            f"{first.get('fields', {}).get('slug', first.get('pk'))!r}). The "
            "fixture is natural-key format — re-serialize without pks/integer "
            "FKs (see CLAUDE.md: The fixture (the sharp edge))."
        )


class Command(BaseCommand):
    help = "Create fixture books missing from an existing DB (deploy step)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            rows = json.loads(FIXTURE.read_text())
        except (OSError, ValueError):
            self.stdout.write("No fixture available — nothing to seed.")
            return

        require_natural_format(rows, "seed_books")

        # Natural-key joins: an author is referenced as ["slug"], a chapter's
        # book as ["slug", "language"] — self-describing, no pk map to build.
        authors = {
            r["fields"]["slug"]: r["fields"]
            for r in rows
            if r.get("model") == "library.author"
        }
        chapters_by_book: dict[tuple, list[dict]] = {}
        for r in rows:
            if r.get("model") == "library.chapter":
                chapters_by_book.setdefault(tuple(r["fields"]["book"]), []).append(
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
            af = authors.get(f["author"][0])
            if af is None:
                # The CI integrity test forbids dangling references, so this is
                # a corrupt fixture — abort the deploy rather than silently
                # skipping the book.
                raise CommandError(
                    f"seed_books: book {f['slug']!r} references missing author "
                    f"{f['author'][0]!r}"
                )
            author, _ = Author.objects.get_or_create(
                slug=af["slug"],
                defaults={
                    "name": af.get("name", ""),
                    "bio": af.get("bio", ""),
                    "bio_html": af.get("bio_html", ""),
                    "photo_url": af.get("photo_url", ""),
                    "birth_year": af.get("birth_year"),
                    "death_year": af.get("death_year"),
                    # Carry the flag through, else an imprint added to the
                    # fixture later is created unflagged on the existing prod DB
                    # (seed_if_empty no-ops there) and lands on Biographies.
                    "is_imprint": af.get("is_imprint", False),
                },
            )
            book = Book.objects.create(
                author=author,
                slug=f["slug"],
                language=f.get("language", "en"),
                # Omit fields the fixture row doesn't carry so the model
                # default applies (e.g. older rows predating a field).
                **{k: f[k] for k in BOOK_FIELDS if k in f},
            )
            for cf in sorted(
                chapters_by_book.get((f["slug"], f.get("language", "en")), []),
                key=lambda c: c["order"],
            ):
                # .create() runs save(), which derives body_text.
                Chapter.objects.create(
                    book=book, **{k: cf[k] for k in CHAPTER_FIELDS if k in cf}
                )
            created += 1
            self.stdout.write(f"  + {book.slug} ({book.chapters.count()} chapters)")

        if created:
            self.stdout.write(self.style.SUCCESS(f"Books: {created} created."))
        else:
            self.stdout.write("Books already up to date.")
