"""Upsert the fixture's books into an already-seeded database.

``seed_if_empty`` only populates a *fresh* database, so neither a NEW book nor
an edit to an existing one reaches an existing production DB on its own. This
command reads the same fixture and upserts every book row — a missing
``(slug, language)`` is created (with its chapters, and its author if absent),
a changed one is updated, an untouched one is left alone. Runs on every deploy
(see the release command); idempotent, and the fixture stays the single source
of truth for book metadata.

Until 2026-07-22 this command only CREATED. Every edit to a book field —
``cover_url``, ``title``, ``description``, ``sort_order``, … — therefore needed
a hand-written data migration to reach prod, and forgetting one made the change
invisible in production while looking fine locally (PR #355: 18 covers set by
``generate_covers`` never shipped). The update branch below is the fix, and
mirrors ``seed_sermons``.

SCOPE: the Book row only. An existing book's CHAPTERS are still left alone —
chapter text is owned by the import/repair pipeline and by the transforms that
data migrations have already applied to live rows, so re-asserting the fixture
over them every deploy is a much larger blast radius than this command should
carry. Chapter changes continue to ship as data migrations (or
``apply_body_corrections``).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.content_fixtures import load_all_rows
from library.models import Author, Book, Chapter

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

# Seeded when the row is first created, then owned by workflows that act on the
# live DB — re-asserting the fixture's value on every deploy would silently walk
# either one back:
#   source_type — the translation review gate. approve_translation flips
#     ai_unreviewed -> ai_reviewed once a native speaker signs off (and only the
#     user decides to run it); the fixture still says ai_unreviewed, so
#     re-asserting it would restore the "awaiting review" badge on the next
#     deploy and make approve_translation useless.
#   is_published — an urgent unpublish (a copyright complaint) happens directly
#     in the live DB; the fixture must not resurrect the book.
# Same set, and the same reasoning, as seed_sermons.CREATE_ONLY_FIELDS.
CREATE_ONLY_FIELDS = frozenset({"source_type", "is_published"})
UPDATE_FIELDS = tuple(f for f in BOOK_FIELDS if f not in CREATE_ONLY_FIELDS)


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
            f"{command_name}: {len(stale)} old-format row(s) in the content fixtures "
            f"(first: {first.get('model')} "
            f"{first.get('fields', {}).get('slug', first.get('pk'))!r}). The "
            "fixture is natural-key format — re-serialize without pks/integer "
            "FKs (see CLAUDE.md: The fixture)."
        )


class Command(BaseCommand):
    help = "Upsert the fixture's books into an existing DB (deploy step)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            rows = load_all_rows()
        except OSError:
            self.stdout.write("No content fixtures available — nothing to seed.")
            return
        # A ValueError (corrupt file, path named) propagates: with 119 files,
        # "one file is broken" must abort the deploy, not skip all content.

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

        created = updated = 0
        for row in rows:
            if row.get("model") != "library.book":
                continue
            f = row["fields"]
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
            language = f.get("language", "en")
            book = Book.objects.filter(slug=f["slug"], language=language).first()

            if book is None:
                book = Book.objects.create(
                    author=author,
                    slug=f["slug"],
                    language=language,
                    # Omit fields the fixture row doesn't carry so the model
                    # default applies (e.g. older rows predating a field).
                    **{k: f[k] for k in BOOK_FIELDS if k in f},
                )
                for cf in sorted(
                    chapters_by_book.get((f["slug"], language), []),
                    key=lambda c: c["order"],
                ):
                    # .create() runs save(), which derives body_text.
                    Chapter.objects.create(
                        book=book, **{k: cf[k] for k in CHAPTER_FIELDS if k in cf}
                    )
                created += 1
                self.stdout.write(f"  + {book.slug} ({book.chapters.count()} chapters)")
                continue

            # A field absent from the fixture row (an older serialization
            # predating it) is not "changed to the default" — leave it be.
            changed = [
                k for k in UPDATE_FIELDS if k in f and getattr(book, k) != f[k]
            ]
            if book.author_id != author.id:
                book.author = author
                changed.append("author")
            if changed:
                for k in changed:
                    if k in BOOK_FIELDS:
                        setattr(book, k, f[k])
                # save(), never queryset.update(): the book's title, language
                # and author are baked into its chapters' stored search
                # vectors, and only Book.save()'s hook ripples the change into
                # them (library/fts.py). A bulk update would leave those
                # vectors STALE rather than NULL, so the backfill_search_vectors
                # release step — which fills NULLs only — would not repair them.
                book.save()
                updated += 1
                self.stdout.write(
                    f"  ~ {book.slug} [{book.language}] ({', '.join(changed)})"
                )

        if created or updated:
            self.stdout.write(
                self.style.SUCCESS(f"Books: {created} created, {updated} updated.")
            )
        else:
            self.stdout.write("Books already up to date.")
