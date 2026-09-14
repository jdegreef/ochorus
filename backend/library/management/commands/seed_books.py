"""Upsert the fixture's books into an already-seeded database.

``seed_if_empty`` only populates a *fresh* database, so neither a NEW book nor
an edit to an existing one reaches an existing production DB on its own. This
command reads the same fixture and upserts every book row — a missing
``(slug, language)`` is created (with its chapters, and its author if absent),
a changed one is updated, an untouched one is left alone. Runs on every deploy
(see the release command); idempotent, and the fixture stays the single source
of truth for book metadata.

Until 2026-07-22 (PR #362) this command only CREATED, so every edit to a book
field needed a hand-written data migration to reach prod — and forgetting one
made the change invisible in production while looking fine locally (PR #355:
18 covers set by ``generate_covers`` never shipped).

SCOPE: the Book row only. An existing book's CHAPTERS are still left alone.
Chapter ``order`` is a public contract — ``PlanDay.chapter_order``, readers'
saved positions, prerendered URLs — so silently replacing a chapter set on
every deploy could shift all three library-wide (see migration 0009, which
excluded a book from re-chapterization for exactly that reason). Chapter
changes keep shipping as data migrations, or as ``apply_body_corrections``
entries for body repairs. That makes chapters the one thing this command does
NOT keep in sync, so it also emits a report-only ``chapter_drift`` warning
(never a failure) when a book's stored chapters have diverged from the fixture
— the signal that a live-DB transform needs a fixture regen.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.author_sync import sync_all_authors
from library.content_fixtures import AUTHORS_FILE, authors_by_slug, iter_work_files
from library.corrections import settled_chapter_body
from library.models import Author, Book, Chapter

BOOK_FIELDS = (
    "title",
    "subtitle",
    "description",
    "about_html",
    "qa",
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
# No `word_count`: `Chapter.save()` derives it from body_html, so passing the
# fixture's copy here would be discarded. See seed_sermons.SERMON_FIELDS, where
# the same entry also cost a re-write on every deploy.
CHAPTER_FIELDS = ("order", "title", "body_html")

# Seeded on create, then owned by workflows that act on the live DB:
# approve_translation flips source_type (37 fixture books still say
# ai_unreviewed), and an urgent copyright unpublish clears is_published there.
# Same set and same reasoning as seed_sermons.CREATE_ONLY_FIELDS, which spells
# it out; a fixture that re-asserted either would walk the decision back.
CREATE_ONLY_FIELDS = frozenset({"source_type", "is_published"})
UPDATE_FIELDS = tuple(f for f in BOOK_FIELDS if f not in CREATE_ONLY_FIELDS)


def chapter_drift_reason(book, fixture_chapters) -> str | None:
    """Report-only: why ``book``'s stored chapters differ from the fixture, or
    ``None`` when they agree.

    seed_books upserts the Book ROW but deliberately never touches an existing
    book's chapters (chapter ``order`` is a public contract — see the module
    docstring). That leaves one silent gap: a chapter-transform data migration,
    or a correction applied to the live DB, can diverge prod chapters from the
    fixture with nothing to detect it — ``regen_fixture`` rebuilds the fixture
    *from* the fixture, so neither side notices. Book metadata now auto-syncs,
    which makes chapters the lone exception, exactly the shape that gets
    forgotten. This surfaces the gap as a deploy-log warning; the fix is a
    fixture regen (or a migration), decided by a human. It only READS — never
    mutates a chapter or fails the deploy.

    ``fixture_chapters`` is the list of chapter ``fields`` from this book's own
    fixture file (one work per file), so the whole-corpus ``chapters_by_book``
    dict is gone. The DB side reads only the three columns it compares — order,
    title, body_html — for THIS book, one book at a time, so the whole-corpus
    chapter prefetch the 2026-08-14 OOM work had to trim is now never
    materialised at all.

    Stops at the first drifted chapter — the point is *which book* needs
    attention, not an exhaustive per-chapter diff.
    """
    fixture = {c["order"]: c for c in fixture_chapters}
    if not fixture:
        # A book with no fixture chapters at all (e.g. one added straight to
        # prod) — there's nothing to compare it against, so don't guess.
        return None
    db = {
        c.order: c
        for c in book.chapters.only("book_id", "order", "title", "body_html")
    }
    if fixture.keys() != db.keys():
        if len(db) == len(fixture):
            # Same count, different order numbers — a plain count would read as
            # "3 vs 3". Name the orders that don't line up instead.
            odd = sorted(set(db) ^ set(fixture))
            return f"chapter order(s) {odd} differ between DB and fixture"
        return f"{len(db)} chapter(s) in DB, {len(fixture)} in fixture"
    for order, fc in sorted(fixture.items()):
        dc = db[order]
        if (fc.get("title") or "") != (dc.title or ""):
            return (
                f"chapter {order} title {dc.title!r} (DB) != "
                f"{fc.get('title')!r} (fixture)"
            )
        fixture_body = fc.get("body_html") or ""
        # Two spellings count as faithful: the fixture's own text, and that text
        # corrected — the release corrects every stored chapter immediately
        # BEFORE this seed, so on a clean install ~13 books would otherwise read
        # as drifted (see `corrections.py`). Settling costs 0.26ms and is
        # computed only for a chapter that already disagrees, not every chapter.
        if fixture_body != dc.body_html and (
            settled_chapter_body(book.slug, order, fixture_body) != dc.body_html
        ):
            return f"chapter {order} body differs from fixture"
    return None


def iter_chapter_drift():
    """Yield ``(book, reason)`` for every book in the fixture whose stored
    chapters diverge from it, streaming one work file at a time.

    Only books already in the DB are compared — a just-created book matches by
    construction, and a fixture book with no DB row yet is skipped. Peak memory
    is a single work file: the whole-corpus scan this replaced is gone. This is
    the one place the drift report is produced — ``handle()`` calls it after
    seeding — so the "which books" logic lives here alone.
    """
    for _path, rows in iter_work_files():
        # Key by (slug, language) rather than lumping every chapter in the file
        # together: the layout is one book per file today, but a book must be
        # compared only against its own chapters even if that ever changes.
        chapters_by_book: dict[tuple, list[dict]] = {}
        for r in rows:
            if r.get("model") == "library.chapter":
                chapters_by_book.setdefault(
                    tuple(r["fields"]["book"]), []
                ).append(r["fields"])
        for r in rows:
            if r.get("model") != "library.book":
                continue
            f = r["fields"]
            language = f.get("language", "en")
            book = Book.objects.filter(slug=f["slug"], language=language).first()
            if book is None:
                continue
            reason = chapter_drift_reason(
                book, chapters_by_book.get((f["slug"], language), [])
            )
            if reason:
                yield book, reason


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
            author_rows = json.loads(AUTHORS_FILE.read_text())
        except OSError:
            self.stdout.write("No content fixtures available — nothing to seed.")
            return
        # A ValueError (corrupt file) propagates: "one file is broken" must abort
        # the deploy, not seed a partial library.

        require_natural_format(author_rows, "seed_books")
        # Natural-key joins: an author is referenced as ["slug"] — self-describing.
        authors = authors_by_slug(author_rows)

        created = updated = 0
        # Stream one work file at a time — books/<slug>.<lang>.json holds one Book
        # and its Chapters — so peak memory is a single file, not the whole
        # ~170 MB fixture parsed at once (the preDeploy allocation that grows
        # with the library). seed_books runs once per deploy after
        # apply_body_corrections.
        for _path, rows in iter_work_files():
            require_natural_format(rows, "seed_books")
            # Chapters share their book's file, so this grouping is local — no
            # whole-corpus chapters_by_book dict.
            chapters_by_book: dict[tuple, list[dict]] = {}
            for r in rows:
                if r.get("model") == "library.chapter":
                    chapters_by_book.setdefault(
                        tuple(r["fields"]["book"]), []
                    ).append(r["fields"])

            for row in rows:
                if row.get("model") != "library.book":
                    continue
                f = row["fields"]
                af = authors.get(f["author"][0])
                if af is None:
                    # The CI integrity test forbids dangling references, so this
                    # is a corrupt fixture — abort the deploy rather than silently
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
                        # Every fixture author is "en" today, so omitting this was
                        # invisible; a non-English author created on prod would
                        # have silently taken the model default and mis-fed
                        # _localized().
                        "original_language": af.get("original_language", "en"),
                        # Carry the flag through, else an imprint added to the
                        # fixture later is created unflagged on the existing prod
                        # DB (seed_if_empty no-ops there) and lands on Biographies.
                        "is_imprint": af.get("is_imprint", False),
                        # Same reasoning for the "withhold this person" flag.
                        "list_in_biographies": af.get("list_in_biographies", True),
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
                        fields = {k: cf[k] for k in CHAPTER_FIELDS if k in cf}
                        if "body_html" in fields:
                            # Corrected now: apply_body_corrections already ran
                            # this deploy (it precedes seed_books), so a book
                            # arriving today would otherwise sit live with a known
                            # defect until the NEXT deploy came round to it.
                            fields["body_html"] = settled_chapter_body(
                                f["slug"], cf["order"], cf["body_html"]
                            )
                        # .create() runs save(), which derives body_text.
                        Chapter.objects.create(book=book, **fields)
                    created += 1
                    self.stdout.write(
                        f"  + {book.slug} [{language}] "
                        f"({book.chapters.count()} chapters)"
                    )
                    continue

                # A field absent from the fixture row (an older serialization
                # predating it) is not "changed to the default" — leave it be.
                changed = [
                    k for k in UPDATE_FIELDS if k in f and getattr(book, k) != f[k]
                ]
                for k in changed:
                    setattr(book, k, f[k])
                if book.author_id != author.id:
                    book.author = author
                    changed.append("author")
                if changed:
                    # save(), never queryset.update(): Book.save()'s hook ripples
                    # a changed title/language/author into its chapters' stored
                    # search vectors (library/fts.py). A bulk update would leave
                    # them STALE rather than NULL, so backfill_search_vectors —
                    # which fills NULLs only — would never repair them.
                    book.save()
                    updated += 1
                    self.stdout.write(
                        f"  ~ {book.slug} [{language}] ({', '.join(changed)})"
                    )

        if created or updated:
            self.stdout.write(
                self.style.SUCCESS(f"Books: {created} created, {updated} updated.")
            )
        else:
            self.stdout.write("Books already up to date.")

        # Every fixture author, not just those reached by the book loop — the
        # biography-only authors have no book at all. See author_sync.
        for line in sync_all_authors(Author, author_rows):
            self.stdout.write(line)

        # Report-only: warn if any existing book's chapters have diverged from
        # the fixture (a live-DB transform that never got a fixture regen — the
        # fix is a fixture regen or a migration, decided by a human). Streams one
        # work file at a time and reads only the columns it compares. This is
        # diagnostics inside an @transaction.atomic handle(), so a bug in it must
        # NOT roll back a good seed — its reads are swallowed (only reads, so the
        # transaction stays usable) rather than allowed to propagate.
        try:
            drifted = list(iter_chapter_drift())
        except Exception as exc:  # noqa: BLE001 — never let diagnostics fail a deploy
            self.stdout.write(
                self.style.WARNING(f"⚠ Chapter-drift check skipped ({exc!r}).")
            )
            return
        if drifted:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Chapter drift: {len(drifted)} book(s) differ from the "
                    "fixture. seed_books does not sync chapters — regenerate the "
                    "fixture (scripts/regen_fixture.py) or ship a data migration "
                    "(see the ship-content-fix skill)."
                )
            )
            for book, reason in drifted:
                self.stdout.write(
                    self.style.WARNING(f"    {book.slug} [{book.language}]: {reason}")
                )
