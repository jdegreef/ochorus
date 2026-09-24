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

SERIES ride along: ``series.json`` is upserted first (every field — nothing
owns a series after creation), then each book's ``series`` / ``series_position``
like any other field. A book row WITHOUT a ``series`` key is out of every series:
membership is the fixture's fact, and reading absence as "leave it" would strand
a book the fixture had taken out.

CHAPTERS sync by ``order``, additively. Chapter ``order`` is a public contract
— ``PlanDay.chapter_order``, readers' saved positions, prerendered URLs — so
this command never deletes or renumbers a chapter (see migration 0009, which
excluded a book from re-chapterization for exactly that reason). Within that
rule the fixture is the truth: a chapter whose title or settled body differs is
updated in place, and an order the DB lacks is created. Until 2026-09-23 it did
neither, so every fixture-only chapter fix silently skipped prod — 379 chapters
across 60 editions (straight quotes, OCR slips, a whole index page), plus
Stepping Stones' four new chapters, which needed migration 0162. A chapter
set that must shrink or renumber still ships as a data migration; the
report-only ``chapter_drift`` warning names any book whose DB still disagrees
after the sync (in practice: a DB chapter the fixture no longer has).
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.author_sync import sync_all_authors
from library.content_fixtures import (
    AUTHORS_FILE,
    SERIES_FILE,
    authors_by_slug,
    iter_work_files,
)
from library.corrections import settled_chapter_body
from library.models import Author, Book, Chapter, Series, SeriesTranslation

BOOK_FIELDS = (
    "title",
    "subtitle",
    "cover_title",
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
    "series_position",
    "sort_order",
    "is_published",
)
# Every Series field the fixture owns (all of them — see the module docstring).
SERIES_FIELDS = ("title", "description", "sort_order")
SERIES_TRANSLATION_FIELDS = ("title", "description")
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


def _upsert(model, lookup: dict, values: dict, label: str, stdout):
    """get_or_create ``model`` by ``lookup``, then bring ``values`` up to date.

    Saves (and so moves ``updated_at``) only when a value really changed, so a
    no-op deploy leaves every row untouched."""
    row, created = model.objects.get_or_create(**lookup, defaults=values)
    if created:
        stdout.write(f"  + {label}")
    elif changed := [k for k, v in values.items() if getattr(row, k) != v]:
        for k in changed:
            setattr(row, k, values[k])
        row.save()
        stdout.write(f"  ~ {label} ({', '.join(changed)})")
    return row


def sync_series(stdout) -> dict[str, Series]:
    """Upsert every ``series.json`` row; return the series keyed by slug.

    A series the fixture no longer lists is left in the DB: ``Book.series`` is
    PROTECT, and a series still holding live books is not this seed's to drop.
    Its translations are the fixture's outright, though — one the file no
    longer carries is deleted, or a withdrawn name would stay on every page.
    """
    if not SERIES_FILE.exists():
        # Not an empty file: this function deletes the names the file doesn't
        # carry, so reading "missing" as "empty" would wipe every series name.
        raise CommandError(f"seed_books: {SERIES_FILE.name} is missing")
    rows = json.loads(SERIES_FILE.read_text())
    require_natural_format(rows, "seed_books")
    by_slug: dict[str, Series] = {}
    for row in rows:
        if row["model"] != "library.series":
            continue
        f = row["fields"]
        by_slug[f["slug"]] = _upsert(
            Series,
            {"slug": f["slug"]},
            {k: f[k] for k in SERIES_FIELDS if k in f},
            f"series {f['slug']}",
            stdout,
        )
    kept = set()
    for row in rows:
        if row["model"] != "library.seriestranslation":
            continue
        f = row["fields"]
        try:
            series = by_slug[f["series"][0]]
        except KeyError:
            raise CommandError(
                f"seed_books: series translation {f['series']} [{f['language']}] "
                "names a series series.json does not define"
            ) from None
        kept.add(
            _upsert(
                SeriesTranslation,
                {"series": series, "language": f["language"]},
                {k: f[k] for k in SERIES_TRANSLATION_FIELDS if k in f},
                f"series {series.slug} [{f['language']}]",
                stdout,
            ).pk
        )
    stale = SeriesTranslation.objects.exclude(pk__in=kept)
    for tr in stale.select_related("series"):
        stdout.write(f"  - series {tr.series.slug} [{tr.language}]")
    stale.delete()
    return by_slug


def series_of(f: dict, series: dict[str, Series]) -> Series | None:
    """The Series a fixture book row names, or None; raises on a dangling one."""
    ref = f.get("series")
    if ref is None:
        return None
    if not (isinstance(ref, list) and len(ref) == 1):
        raise CommandError(
            f"seed_books: book {f['slug']!r} has a malformed series reference "
            f"{ref!r} — expected a natural key, [\"<series-slug>\"]"
        )
    try:
        return series[ref[0]]
    except KeyError:
        raise CommandError(
            f"seed_books: book {f['slug']!r} references missing series {ref[0]!r}"
        ) from None


def sync_chapters(book, fixture_chapters) -> tuple[int, int, list[int]]:
    """Bring an existing ``book``'s chapters up to its fixture; return
    ``(added, updated, extra_orders)``.

    Additive by ``order`` (see the module docstring): an order the DB lacks is
    created, one whose title or settled body differs is updated in place, and
    nothing is ever deleted or renumbered — a DB chapter the fixture lacks is
    returned in ``extra_orders`` for the deploy log to report.

    The fixture WINS: a data migration that edits chapter rows without the
    matching fixture edit is reverted in the same release (``release`` runs
    ``migrate`` before this seed). Edit the fixture; a migration is only for
    what this may not do — deleting or renumbering chapters.

    An in-place body change that adds or removes top-level blocks shifts the
    ``paragraph_index`` readers' saved positions point at, by that many blocks,
    in that chapter only — the price of shipping the fix at all. Bodies are compared and written in
    their SETTLED form, the state ``apply_body_corrections`` (which runs just
    before this seed) leaves them in, so a corrected chapter is not reverted and
    a converged library costs no writes. Settling is computed only for a
    chapter whose raw body already disagrees, as in ``chapter_drift_reason``.
    """
    db = {
        c.order: c
        for c in book.chapters.only("id", "book_id", "order", "title", "body_html")
    }
    added = updated = 0
    for fc in sorted(fixture_chapters, key=lambda c: c["order"]):
        order = fc["order"]
        title = fc.get("title") or ""
        body = fc.get("body_html") or ""
        chapter = db.get(order)
        if chapter is None:
            # .create() runs save(), which derives body_text / word_count and
            # builds the search vector.
            Chapter.objects.create(
                book=book,
                order=order,
                title=title,
                body_html=settled_chapter_body(book.slug, order, body),
            )
            added += 1
            continue
        changed = []
        if (chapter.title or "") != title:
            chapter.title = title
            changed.append("title")
        if body != chapter.body_html:
            body = settled_chapter_body(book.slug, order, body)
            if body != chapter.body_html:
                chapter.body_html = body
                changed.append("body_html")
        if changed:
            # save(), not .update(): the hook re-derives body_text/word_count,
            # clears the citation stamp and refreshes the search vector.
            chapter.save(update_fields=changed)
            updated += 1
    return added, updated, sorted(set(db) - {fc["order"] for fc in fixture_chapters})


def chapter_drift_reason(book, fixture_chapters) -> str | None:
    """Report-only: why ``book``'s stored chapters differ from the fixture, or
    ``None`` when they agree.

    A read-only diagnostic, no longer run on deploy: ``sync_chapters``
    converges every chapter it may touch and reports the rest itself. Kept for
    tests and ad-hoc checks that a DB matches the fixture. It only READS.

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
    is a single work file: the whole-corpus scan this replaced is gone. Not run on deploy
    (``sync_chapters`` reports what it cannot fix); tests use it to prove
    convergence.
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
        series = sync_series(self.stdout)

        created = updated = chapters_synced = 0
        drifted = []
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
                book_series = series_of(f, series)

                if book is None:
                    book = Book.objects.create(
                        author=author,
                        series=book_series,
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

                added, retouched, extra = sync_chapters(
                    book, chapters_by_book.get((f["slug"], language), [])
                )
                if extra:
                    drifted.append(
                        (book, f"chapter order(s) {extra} in DB, not in fixture")
                    )
                if added or retouched:
                    chapters_synced += 1
                    self.stdout.write(
                        f"  ~ {book.slug} [{language}] chapters: "
                        f"{added} added, {retouched} updated"
                    )

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
                if book.series_id != (book_series and book_series.id):
                    book.series = book_series
                    changed.append("series")
                if book_series is None and book.series_position is not None:
                    # Out of the series, so out of its numbering too — the
                    # check constraint forbids a position without one.
                    book.series_position = None
                    changed.append("series_position")
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

        if created or updated or chapters_synced:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Books: {created} created, {updated} updated, "
                    f"{chapters_synced} with chapters synced."
                )
            )
        else:
            self.stdout.write("Books already up to date.")

        # Every fixture author, not just those reached by the book loop — the
        # biography-only authors have no book at all. See author_sync.
        for line in sync_all_authors(Author, author_rows):
            self.stdout.write(line)

        # Report-only: a DB chapter the fixture lacks, which sync never deletes
        # (order is a public contract) — only a data migration may retire it.
        if drifted:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Chapter drift: {len(drifted)} book(s) keep chapters the "
                    "fixture lacks. The chapter sync never deletes or renumbers "
                    "— ship a data migration (see the ship-content-fix skill)."
                )
            )
            for book, reason in drifted:
                self.stdout.write(
                    self.style.WARNING(f"    {book.slug} [{book.language}]: {reason}")
                )
