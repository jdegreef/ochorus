"""Integrity guard for the split content fixtures (``fixtures/content/``).

One file per work — ``authors.json``, ``books/<slug>.<lang>.json`` (book +
chapters), ``sermons/<slug>.<lang>.json``, ``plans.json`` — so parallel
sessions adding content touch different files and cannot conflict, and a new
translation reviews as one small file. See ``library.content_fixtures``.

The rows are **natural-key format**: rows carry no integer primary keys, and
references are self-describing tuples — a book's author is ``["slug"]``, a
chapter's book is ``["slug", "language"]``. Identity is content-derived, so two
parallel branches appending different content *cannot* collide on a key the way
hand-assigned integer pks did (two PRs claimed the same pks in one week,
2026-07-17 — the incident this architecture retires).

What can still go wrong, and what this suite (CI, every PR, ~0.1s, no DB)
catches loudly:

* an old-format (pk) row added by a stale branch — under ``loaddata`` a
  non-colliding pk row can load silently with the WRONG author (integer FKs
  resolve against re-assigned auto-pks); the seeds hard-fail on it, and so
  does this suite, earlier;
* the same work added twice (duplicate natural key) — ``loaddata`` is silent
  last-write-wins, and the DB's unique constraints brick a fresh load;
* a reference to a row that isn't in the file (author lost in a merge);
* foreign models leaking in from a bare ``dumpdata library`` on a seeded dev DB
  (the regen recipe pins exactly these six models —
  ``backend/scripts/regen_fixture.py``).
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from library.contemporize import MODERN_LANGUAGE
from library.content_fixtures import (
    ARTICLES_DIR,
    AUTHORS_FILE,
    BOOKS_DIR,
    PLANS_FILE,
    SERIES_FILE,
    SERMONS_DIR,
    authors_by_slug,
    load_all_rows,
    ordered_fixture_paths,
    rows_by_file,
    unexpected_files,
    work_filename,
)
from library.covers import (
    _FRAME_INSET,
    AUTHOR_MIN_CONTRAST,
    COVER_WIDTHS,
    RASTER_SUFFIXES,
    H,
    W,
    art_url,
    author_ink_contrast,
    shares_a_ground,
    twin_path,
    variant_url,
)
from library.curated_art import (
    CURATED,
    CURATED_GROUND,
    ORIGINAL_GROUND,
    ORIGINAL_SVG_GROUND,
    ORIGINAL_SVG_SCRIM,
)
from library.designed_covers import (
    DERIVED_GROUND,
    DESIGNED,
    DESIGNED_BY_SLUG,
    digest,
)
from library.ingest import (
    strip_numbering_prefix,
    strip_restated_heading,
    word_count,
)
from library.quote_marks import mark_counts, mispaired_marks
from library.text import html_to_text

EXPECTED_MODELS = {
    "library.author",
    "library.book",
    "library.chapter",
    "library.sermon",
    "library.article",
    "library.plan",
    "library.planday",
    "library.series",
    "library.seriestranslation",
}


def _dupes(counter: Counter) -> list:
    return sorted(k for k, n in counter.items() if n > 1)


@lru_cache(maxsize=1)
def files_by_path() -> dict:
    """`rows_by_file()`, parsed once for the whole suite.

    Same reason `all_rows` is cached: the bare call re-reads and re-parses all
    166 fixture files (~250MB of transient garbage, 0.14s), and three gates in
    this module want the per-file view.
    """
    return rows_by_file()


@lru_cache(maxsize=1)
def work_bodies() -> tuple[tuple[str, str], ...]:
    """(file name, the work's body_html joined) for every work file.

    Quote style is a fact about the WORK, so both quote guards read each work
    whole — and read it here, once, so the two cannot disagree about what a
    work is.
    """
    return tuple(
        (path.name, "".join(r["fields"].get("body_html", "") or "" for r in rows))
        for path, rows in files_by_path().items()
        if path.name not in {"authors.json", "series.json", "plans.json"}
    )


@lru_cache(maxsize=1)
def all_rows() -> list:
    """Every content row, parsed once for the whole module.

    ``load_all_rows`` re-reads all ~690 files on each call (~170MB of transient
    allocation), and several classes here want the same rows. Cached in the test
    module rather than in ``content_fixtures`` because the whole-corpus list is
    exactly the allocation the deploy seeds now avoid — they stream with
    ``iter_work_files`` — so caching it there would reintroduce it.
    """
    return load_all_rows()


def _cover(fields: dict) -> str:
    """A book row's cover_url, absent-or-null normalised to ''."""
    return fields.get("cover_url") or ""


def _cover_color(fields: dict) -> str:
    """A book row's cover_color, absent-or-null normalised to ''."""
    return fields.get("cover_color") or ""


def _cover_title(fields: dict) -> str:
    """The title a book row's cover sets — the twin of ``coverTitle.ts``."""
    return fields.get("cover_title") or fields["title"]


class FixtureIntegrityTests(SimpleTestCase):
    """File-level invariants every content append must preserve."""

    rows: list = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = all_rows()
        cls.by_model = {}
        for r in cls.rows:
            cls.by_model.setdefault(r["model"], []).append(r)

    def test_no_unloaded_files(self):
        # A file outside the sanctioned layout (content/ root, .json.new, a
        # nested dir) is silently invisible to loaddata AND the seeds — the
        # work would merge green and never ship.
        stray = [str(p) for p in unexpected_files()]
        self.assertEqual(
            stray, [],
            f"file(s) under fixtures/content/ that nothing loads: {stray[:5]} — "
            "books go in books/<slug>.<lang>.json, sermons in sermons/, authors "
            "in authors.json, plans in plans.json.",
        )

    def test_only_expected_models(self):
        extra = set(self.by_model) - EXPECTED_MODELS
        missing = EXPECTED_MODELS - set(self.by_model)
        self.assertEqual(
            extra, set(),
            "Unexpected model in the content fixtures — a bare `dumpdata library` from a "
            "seeded dev DB leaks Topic/translation rows; use the pinned "
            "regen recipe (backend/scripts/regen_fixture.py).",
        )
        self.assertEqual(
            missing, set(),
            "A content model has no rows in the content fixtures — if intentional, "
            "update EXPECTED_MODELS consciously.",
        )

    def test_regen_dumps_every_content_model(self):
        # regen_fixture.py dumps a pinned MODELS list, then replaces content/
        # wholesale. A model the fixture holds but MODELS omits fails its row
        # count on every run — and were that check ever loosened, the swap
        # would delete that model's files. Articles went unnoticed this way
        # until someone ran a regen; this makes it the adding PR's failure.
        # Read by ast: the script is a CLI, not an importable module.
        path = settings.BASE_DIR / "scripts" / "regen_fixture.py"
        models = next(
            ast.literal_eval(node.value)
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.Assign)
            and any(getattr(t, "id", None) == "MODELS" for t in node.targets)
        )
        self.assertEqual(
            set(models), EXPECTED_MODELS,
            "regen_fixture.MODELS must list exactly the content models — add the "
            "new model there (with an identity() branch and a split_layout "
            "destination) when you add it to EXPECTED_MODELS.",
        )

    def test_no_integer_pk_rows(self):
        # The fixture is natural-key format. A stale old-format row is the one
        # remaining silent-corruption path: its integer FK resolves against
        # whatever auto-pks the target DB happens to have (experimentally shown
        # attributing a sermon to the wrong author). Reject it outright.
        stale = [
            (r["model"], r["fields"].get("slug", "?"))
            for r in self.rows if "pk" in r
        ]
        self.assertEqual(
            stale[:5], [],
            f"{len(stale)} old-format (integer-pk) row(s), first {stale[:5]}. "
            "Re-serialize with Django's serializer using natural keys "
            "(CLAUDE.md: The fixture) — never hand-assign pks.",
        )

    def test_prose_rows_carry_a_word_count(self):
        # `word_count` drives the per-chapter reading-time estimate in the TOC
        # drawer and the length sort on the books shelf. `save()` derives it, but
        # `loaddata` does not call `save()` — so a fixture row is exactly the
        # case the model hook cannot cover, and a zero shipped here stays zero
        # in every fresh build until the release backfill happens to catch it.
        #
        # 32 chapters shipped this way — all 20 of all-of-grace.es, all 11 of
        # prevailing-prayer.es, and one of the-inner-chamber.lg — so both
        # Spanish books showed no reading times at all and sorted as the
        # shortest in the library.
        blank = []
        for r in self.rows:
            if r["model"] not in ("library.chapter", "library.sermon"):
                continue
            f = r["fields"]
            if f.get("word_count"):
                continue
            # A body with no words in it is legitimately zero.
            words = word_count(f.get("body_html") or "")
            if words:
                blank.append((r["model"], f.get("book") or f.get("slug"), f.get("order"), words))
        self.assertEqual(
            blank[:5], [],
            f"{len(blank)} prose row(s) ship with word_count 0 but have prose, first "
            f"{blank[:5]} — the reader shows no reading time and sorts them shortest. "
            "Run `manage.py backfill_word_count` against a seeded DB and re-serialize, "
            "or set the count when the row is written.",
        )

    def test_natural_identity_unique(self):
        # Content identity: what the DB's unique constraints enforce at load
        # time. A duplicate here is the same work added twice — loaddata is
        # silent last-write-wins, so only this check makes it loud.
        checks = {
            "library.author": lambda f: f["slug"],
            "library.series": lambda f: f["slug"],
            "library.seriestranslation": lambda f: (tuple(f["series"]), f["language"]),
            "library.book": lambda f: (f["slug"], f.get("language", "en")),
            "library.sermon": lambda f: (f["slug"], f.get("language", "en")),
            "library.plan": lambda f: (f["slug"], f.get("language", "en")),
            "library.chapter": lambda f: (tuple(f["book"]), f["order"]),
            "library.planday": lambda f: (tuple(f["plan"]), f["day"]),
        }
        for model, key in checks.items():
            dupes = _dupes(
                Counter(key(r["fields"]) for r in self.by_model.get(model, []))
            )
            self.assertEqual(
                dupes, [],
                f"{model}: duplicate natural identity {dupes[:5]} — the same "
                "content exists twice; the DB's unique constraint will reject it.",
            )

    def test_references_resolve(self):
        # Every natural-key reference must resolve within the file — loaddata
        # runs as ONE call over all the files, and all FKs here are NOT NULL, so a
        # dangling reference aborts a fresh-database load.
        author_keys = {
            (r["fields"]["slug"],) for r in self.by_model.get("library.author", [])
        }
        book_keys = {
            (r["fields"]["slug"], r["fields"].get("language", "en"))
            for r in self.by_model.get("library.book", [])
        }
        plan_keys = {
            (r["fields"]["slug"], r["fields"].get("language", "en"))
            for r in self.by_model.get("library.plan", [])
        }

        refs = [
            ("library.book", "author", author_keys),
            ("library.sermon", "author", author_keys),
            ("library.chapter", "book", book_keys),
            ("library.planday", "plan", plan_keys),
        ]
        # Nullable, so a book outside every series carries no reference at all.
        series_keys = {
            (r["fields"]["slug"],) for r in self.by_model.get("library.series", [])
        }
        refs.append(("library.book", "series", series_keys))
        refs.append(("library.seriestranslation", "series", series_keys))
        for model, field, valid in refs:
            dangling = sorted(
                {
                    tuple(r["fields"][field])
                    for r in self.by_model.get(model, [])
                    if r["fields"].get(field) is not None
                }
                - valid
            )
            self.assertEqual(
                dangling, [],
                f"{model}.{field}: dangling reference(s) {dangling[:5]} — the "
                "target row is missing from the fixture.",
            )

        # PlanDay's soft references: the slug must at least exist as a book in
        # SOME language (checking the plan's exact language would false-fail a
        # translated plan shipping ahead of its books).
        book_slugs = {r["fields"]["slug"] for r in self.by_model.get("library.book", [])}
        stray = sorted(
            {r["fields"]["book_slug"] for r in self.by_model.get("library.planday", [])}
            - book_slugs
        )
        self.assertEqual(
            stray, [],
            f"library.planday.book_slug: unknown book slug(s) {stray[:5]} — a "
            "plan day points at a book that isn't in the fixture.",
        )

    def test_reference_shapes(self):
        # Natural-key references are lists of the right arity. A malformed
        # reference (say, an integer FK surviving a hand edit) would otherwise
        # surface as a confusing TypeError above — or worse, load.
        shapes = [
            ("library.book", "author", 1),
            ("library.sermon", "author", 1),
            ("library.chapter", "book", 2),
            ("library.planday", "plan", 2),
        ]
        shapes.append(("library.book", "series", 1))
        shapes.append(("library.seriestranslation", "series", 1))
        # Absent or null is a book in no series, which is well-formed.
        nullable = {("library.book", "series")}
        for model, field, arity in shapes:
            refs = [r["fields"].get(field) for r in self.by_model.get(model, [])]
            if (model, field) in nullable:
                refs = [ref for ref in refs if ref is not None]
            bad = [
                ref for ref in refs
                if not (isinstance(ref, list) and len(ref) == arity)
            ][:3]
            self.assertEqual(
                bad, [],
                f"{model}.{field}: malformed natural-key reference(s) {bad} — "
                f"expected a {arity}-element list.",
            )

    def test_required_content_fields_present(self):
        # Rows missing slug/order/day would defeat the identity checks above
        # and break the seed commands' joins.
        for model, required in {
            "library.author": ("slug", "name"),
            "library.book": ("slug", "title", "author"),
            "library.chapter": ("book", "order", "body_html"),
            "library.sermon": ("slug", "title", "author", "body_html"),
            "library.plan": ("slug", "title"),
            "library.planday": ("plan", "day", "book_slug", "chapter_order"),
            "library.series": ("slug", "title"),
            "library.seriestranslation": ("series", "language", "title"),
        }.items():
            for r in self.by_model.get(model, []):
                missing = [k for k in required if k not in r["fields"]]
                self.assertEqual(
                    missing, [],
                    f"{model} {r['fields'].get('slug', '?')}: missing required "
                    f"field(s) {missing}",
                )


class SeriesMembershipTests(SimpleTestCase):
    """What a series means, held where a hand edit to one book file would break it.

    The DB enforces two of these (a volume number is unique per series and
    language, and needs a series); they are here as well so the break names the
    file in CI rather than surfacing as an IntegrityError mid-deploy.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.series = {
            r["fields"]["slug"] for r in all_rows() if r["model"] == "library.series"
        }
        cls.members = [
            r["fields"] for r in all_rows()
            if r["model"] == "library.book" and r["fields"].get("series")
        ]

    def test_volume_numbers_count_from_one(self):
        # The DB's check constraint says the same; this names the file.
        bad = sorted(
            f["slug"] for f in self.members
            if (pos := f.get("series_position")) is not None
            and not (isinstance(pos, int) and pos >= 1)
        )
        self.assertEqual(bad, [], "a volume number must be a whole number from 1")

    def test_a_position_needs_a_series(self):
        stray = sorted(
            f["slug"] for r in all_rows()
            if r["model"] == "library.book"
            and (f := r["fields"]).get("series_position") is not None
            and not f.get("series")
        )
        self.assertEqual(stray, [], "a volume number outside any series means nothing")

    def test_volume_numbers_are_unique_per_language(self):
        seen = Counter(
            (f["series"][0], f.get("language", "en"), f["series_position"])
            for f in self.members if f.get("series_position") is not None
        )
        self.assertEqual(_dupes(seen), [], "two editions claim the same volume")

    def test_a_series_is_ordered_or_not_throughout(self):
        # Half-numbered is neither a reading order nor a collection: the covers
        # would set a numeral on some volumes and not their neighbours.
        kinds: dict[str, set[bool]] = {}
        for f in self.members:
            kinds.setdefault(f["series"][0], set()).add(
                f.get("series_position") is not None
            )
        mixed = sorted(slug for slug, k in kinds.items() if len(k) > 1)
        self.assertEqual(mixed, [], "series with some volumes numbered and some not")

    def test_young_reader_editions_stay_out_of_series(self):
        # An edition is the same work in another form; it joins its full text's
        # family through the slug (see CLAUDE.md), never a series of its own.
        editions = sorted(
            f["slug"] for f in self.members
            if f["slug"].endswith(("-children", "-teens"))
        )
        self.assertEqual(editions, [])

    def test_every_language_holding_a_volume_can_name_its_series(self):
        # The series line on a book page shows only where the series has a name
        # in the edition's language (no English fallback), so a missing
        # translation silently drops the line from a whole language.
        named = {(s, "en") for s in self.series} | {
            (r["fields"]["series"][0], r["fields"]["language"])
            for r in all_rows() if r["model"] == "library.seriestranslation"
        }
        unnamed = sorted(
            {(f["series"][0], f.get("language", "en")) for f in self.members} - named
        )
        self.assertEqual(unnamed, [], "series with volumes in a language it has no name in")

    def test_every_series_has_a_book(self):
        used = {f["series"][0] for f in self.members}
        self.assertEqual(sorted(self.series - used), [], "a series with no books")


class SeedFieldCoverageTests(SimpleTestCase):
    """The seed commands' field lists must cover the models they create.

    seed_books once silently dropped ``attribution``/``publication_year`` (added
    in migration 0028, never added to BOOK_FIELDS) — the first fixture book
    carrying them would have reached production stripped. This pins the lists to
    the models, so a new model field fails CI until the seed learns it.
    """

    def _content_fields(self, model, exclude):
        return {
            f.name for f in model._meta.concrete_fields
            if f.name not in exclude and not f.auto_created
        }

    def test_book_fields_cover_model(self):
        from library.management.commands.seed_books import BOOK_FIELDS
        from library.models import Book

        expected = self._content_fields(
            Book,
            exclude={"id", "author", "series", "slug", "language", "created_at", "updated_at"},
        )
        self.assertEqual(set(BOOK_FIELDS), expected)

    def test_series_fields_cover_model(self):
        from library.management.commands.seed_books import (
            SERIES_FIELDS,
            SERIES_TRANSLATION_FIELDS,
        )
        from library.models import Series, SeriesTranslation

        expected = self._content_fields(
            Series, exclude={"id", "slug", "created_at", "updated_at"}
        )
        self.assertEqual(set(SERIES_FIELDS), expected)
        expected = self._content_fields(
            SeriesTranslation,
            exclude={"id", "series", "language", "created_at", "updated_at"},
        )
        self.assertEqual(set(SERIES_TRANSLATION_FIELDS), expected)

    def test_chapter_fields_cover_model(self):
        from library.management.commands.seed_books import CHAPTER_FIELDS
        from library.models import Chapter

        # body_text, word_count and search_vector are derived by save(); the
        # seed must not set them directly. citations_indexed_at must stay unset
        # so the index_citations release step scans freshly seeded chapters.
        expected = self._content_fields(
            Chapter,
            exclude={"id", "book", "body_text", "word_count", "search_vector",
                     "citations_indexed_at", "created_at", "updated_at"},
        )
        self.assertEqual(set(CHAPTER_FIELDS), expected)

    def test_sermon_fields_cover_model(self):
        from library.management.commands.seed_sermons import SERMON_FIELDS
        from library.models import Sermon

        # preached_on is handled separately (date parsing); body_text,
        # word_count and search_vector are derived. A derived field listed here
        # is not merely redundant: the seed compares it against the fixture, so
        # it re-writes every row where the two disagree and save() derives the
        # value straight back — see SeedSermonsTests.test_second_run_updates_nothing.
        expected = self._content_fields(
            Sermon,
            exclude={"id", "author", "slug", "language", "preached_on",
                     "body_text", "word_count", "search_vector",
                     "created_at", "updated_at"},
        )
        self.assertEqual(set(SERMON_FIELDS), expected)

    def test_create_only_fields_are_real_seeded_fields(self):
        # Both seeds carve UPDATE_FIELDS out of their field tuple by set
        # difference, so a renamed or typo'd entry in CREATE_ONLY_FIELDS fails
        # silently: it matches nothing, the guard evaporates, and the next
        # deploy starts overwriting a workflow-owned field (re-gating an
        # approved translation, or republishing a book pulled for copyright).
        from library.management.commands import seed_books, seed_sermons

        for mod, fields in (
            (seed_books, seed_books.BOOK_FIELDS),
            (seed_sermons, seed_sermons.SERMON_FIELDS),
        ):
            with self.subTest(command=mod.__name__):
                self.assertTrue(set(fields) >= mod.CREATE_ONLY_FIELDS)

    def test_fill_only_fields_are_real_author_fields(self):
        # Same silent-failure shape as CREATE_ONLY_FIELDS above: author_sync
        # reads each name off the fixture row with .get(), so a typo'd or
        # renamed entry yields None, the truthiness check skips it, and that
        # field simply never syncs again — no error, on any deploy, ever.
        from library.author_sync import (
            FILL_ONLY_FIELDS,
            FIXTURE_WINS_TEXT,
            SYNCED_FIELDS,
        )
        from library.models import Author

        model_fields = {f.name for f in Author._meta.concrete_fields}
        self.assertTrue(set(FILL_ONLY_FIELDS) <= model_fields)
        self.assertTrue(set(FIXTURE_WINS_TEXT) <= model_fields)
        # SYNCED_FIELDS (`same_as`, `faq`) reads off the row the same way, so the
        # same typo silently stops the sync — guard them too.
        self.assertTrue(set(SYNCED_FIELDS) <= model_fields)
        self.assertFalse(set(FILL_ONLY_FIELDS) & set(SYNCED_FIELDS))
        # The prose fields are fixture-wins; listing one as fill-only too would
        # read as "protected" and mislead the next reader.
        self.assertFalse(set(FIXTURE_WINS_TEXT) & set(FILL_ONLY_FIELDS))



class CopyrightBlockedTests(SimpleTestCase):
    """No edition of a copyright-blocked work may be published, in any language.

    `seed_books` treats `is_published` as create-only, so a fixture that ships
    `true` publishes the row the moment it is created, and nothing afterwards
    walks it back. That is how *Grace for Grace*'s es/fr/pt translations went
    live on 2026-09-24, derivatives of a protected English compilation, months
    after migration 0022 unpublished the English. A translation fixture of one
    of these works fails here instead.
    """

    def test_no_blocked_work_is_published_in_any_language(self):
        from library.corrections import COPYRIGHT_BLOCKED_SLUGS

        published = []
        for path, rows in files_by_path().items():
            for row in rows:
                f = row.get("fields", {})
                if (
                    row.get("model") == "library.book"
                    and f.get("slug") in COPYRIGHT_BLOCKED_SLUGS
                    and f.get("is_published", True)
                ):
                    published.append(path.name)
        self.assertEqual(
            published,
            [],
            "these editions of a copyright-blocked work are published — set "
            "is_published: false (corrections.COPYRIGHT_BLOCKED_SLUGS; no "
            "translation of these may ship without the rights holder's permission)",
        )

class FileCoherenceTests(SimpleTestCase):
    """Each file must contain exactly what its name and role promise.

    A mismatched file (a book file whose slug differs from its name, chapters
    of another book, an author row in a book file) would load fine — the layout
    is a convention loaddata doesn't know about — so only this check keeps the
    per-work structure honest.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.files = files_by_path()

    def test_authors_file_is_authors_only(self):
        models = {r["model"] for r in self.files.get(AUTHORS_FILE, [])}
        self.assertEqual(models, {"library.author"})

    def test_series_file_is_series_only(self):
        rows = self.files.get(SERIES_FILE, [])
        self.assertEqual(
            {r["model"] for r in rows}, {"library.series", "library.seriestranslation"}
        )
        # A translation after its series: seed_books and loaddata both read the
        # file in order, and a natural key to a row not yet seen won't resolve.
        seen = set()
        for r in rows:
            f = r["fields"]
            if r["model"] == "library.series":
                seen.add(f["slug"])
            else:
                self.assertIn(
                    f["series"][0], seen,
                    f"series translation {f['series']} [{f['language']}] precedes its series",
                )

    def test_plans_file_shape(self):
        rows = self.files.get(PLANS_FILE, [])
        self.assertEqual(
            {r["model"] for r in rows}, {"library.plan", "library.planday"}
        )
        # Every planday must FOLLOW its plan row (one loaddata call, NOT NULL
        # FK — order inside the file is load order).
        seen_plans = set()
        for r in rows:
            f = r["fields"]
            if r["model"] == "library.plan":
                seen_plans.add((f["slug"], f.get("language", "en")))
            else:
                self.assertIn(
                    tuple(f["plan"]), seen_plans,
                    f"planday day={f['day']} appears before its plan {f['plan']}",
                )

    def test_book_files_coherent(self):
        for path, rows in self.files.items():
            if path.parent != BOOKS_DIR:
                continue
            books = [r for r in rows if r["model"] == "library.book"]
            self.assertEqual(
                len(books), 1, f"{path.name}: expected exactly one book row"
            )
            f = books[0]["fields"]
            self.assertEqual(
                path.name, work_filename(f["slug"], f.get("language", "en")),
                f"{path.name}: file name doesn't match its book row",
            )
            self.assertEqual(rows[0]["model"], "library.book",
                             f"{path.name}: the book row must come first")
            key = [f["slug"], f.get("language", "en")]
            for r in rows[1:]:
                self.assertEqual(r["model"], "library.chapter",
                                 f"{path.name}: only chapters may follow the book")
                self.assertEqual(
                    r["fields"]["book"], key,
                    f"{path.name}: chapter order={r['fields']['order']} belongs "
                    f"to {r['fields']['book']}, not this file's book",
                )

    def test_sermon_files_coherent(self):
        for path, rows in self.files.items():
            if path.parent != SERMONS_DIR:
                continue
            self.assertEqual(
                [r["model"] for r in rows], ["library.sermon"],
                f"{path.name}: a sermon file holds exactly one sermon row",
            )
            f = rows[0]["fields"]
            self.assertEqual(
                path.name, work_filename(f["slug"], f.get("language", "en")),
                f"{path.name}: file name doesn't match its sermon row",
            )

    def test_english_chapter_titles_are_title_cased(self):
        """No English chapter title left with a capitalised little word — "The
        Glory Of The Creature". migration 0121 corrected the corpus and this
        keeps a re-import or a new book from reintroducing the pattern. Mirrors
        recase_title exactly, so the fixture and the backfill cannot drift."""
        from library.titlecase import recase_title

        offenders = []
        for path, rows in self.files.items():
            if path.parent != BOOKS_DIR or not path.name.endswith(".en.json"):
                continue
            for r in rows:
                if r["model"] != "library.chapter":
                    continue
                title = (r["fields"].get("title") or "").strip()
                if title and recase_title(title) != title:
                    offenders.append(f"{path.name} ch{r['fields']['order']}: {title!r}")
        self.assertEqual(
            offenders, [],
            "English chapter titles still in raw Title Case (run recase_title):\n"
            + "\n".join(offenders),
        )


class AuthorBioDataIntegrityTests(SimpleTestCase):
    """The translated author bios (migrations/data/author_bios_<lang>/) are
    delivered by the seed_author_translations deploy step, which soft-skips a
    slug with no matching Author — deliberately deploy-safe, which means a
    misnamed <slug>.short.txt or <slug>.html would silently never ship.
    This suite makes that loud at CI time instead (the same strict-check role
    FixtureIntegrityTests plays for the fixture's own references)."""

    def test_every_bio_slug_resolves_against_the_fixture_authors(self):
        from library.management.commands.seed_author_translations import (
            language_dirs,
            read_bios,
        )

        author_slugs = set(authors_by_slug())
        dirs = language_dirs()
        self.assertGreaterEqual(len(dirs), 3)  # es, sw, lg at minimum
        for lang, d in dirs:
            # A stray dir ("author_bios_es 2", "author_bios_es_old") would
            # seed bogus rows under a junk language code — max_length=10 on
            # the model, and real codes are short and lowercase.
            self.assertRegex(
                lang, r"^[a-z]{2,3}(-[a-z0-9]{1,6})?$",
                f"{d.name}: suffix doesn't look like a language code",
            )
            dangling = sorted(set(read_bios(d)) - author_slugs)
            self.assertEqual(
                dangling, [],
                f"{d.name}: bios for slugs missing from authors.json — the "
                "seed would soft-skip these forever",
            )

    def test_short_json_files_stay_frozen_migration_inputs(self):
        """The two surviving short.json files are empty, and no new ones appear.

        Short bios ship as per-slug ``<slug>.short.txt`` files; nothing reads a
        ``short.json`` any more. The sw/lg copies exist EMPTY only because
        migration ``0024`` opens them unguarded and migrations are immutable
        (see migrations/data/README.md). An entry added to one — the natural
        habit for anyone who shipped a bio before the split — is a bio that
        silently never ships, and a new short.json anywhere is the shared-file
        conflict this split deleted, growing back.
        """
        from library.management.commands.seed_author_translations import (
            DATA_DIR,
            language_dirs,
        )

        allowed = {"author_bios_sw", "author_bios_lg"}
        found = {p.parent.name: p for p in DATA_DIR.glob("author_bios_*/short.json")}
        self.assertEqual(
            sorted(set(found) - allowed),
            [],
            "New short.json files — short bios are per-slug <slug>.short.txt now",
        )
        for name in sorted(allowed):
            path = found.get(name)
            self.assertIsNotNone(path, f"{name}/short.json is migration 0024's "
                                 "input and must exist (empty) or migrate crashes")
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {},
                f"{name}/short.json must stay EMPTY — an entry here never ships",
            )
        # And every language now has per-slug shorts where it has bios at all.
        for _lang, d in language_dirs():
            self.assertTrue(
                list(d.glob("*.short.txt")) or list(d.glob("*.html")),
                f"{d.name}: no bio files at all — an empty dir seeds nothing",
            )


def assert_qa_wellformed(test, items, keys, label):
    """Shared shape / plain-text guard for editorial Q&A.

    Q&A (author ``faq``, book/topic ``qa``) ships as plain-text JSON and is
    rendered — on the page and as FAQPage JSON-LD — with no sanitize step, so it
    must carry no markup and must talk about the CONTENT, not the platform.
    ``items`` is the stored list, ``keys`` the exact key set each entry must have
    ({"q", "a"} for authors, {"question", "answer"} for books/topics), ``label``
    a human tag for the failure message. One helper so the two callers cannot
    drift (backend/CLAUDE.md: "a second copy drifts — it already did once").
    """
    test.assertIsInstance(items, list, f"{label}: Q&A must be a list")
    # A present set is an editorial one: the spec is 6–10 entries.
    test.assertTrue(
        6 <= len(items) <= 10,
        f"{label}: Q&A has {len(items)} entries — the spec is 6 to 10",
    )
    for i, item in enumerate(items):
        test.assertEqual(set(item), keys, f"{label}[{i}]: each entry is exactly {keys}")
        for key in keys:
            val = item[key]
            test.assertIsInstance(val, str, f"{label}[{i}].{key}: string")
            test.assertTrue(val.strip(), f"{label}[{i}].{key}: non-empty")
            # Plain text: the render escapes it and the JSON-LD carries it raw,
            # so a stray tag or entity would ship literally.
            test.assertIsNone(_TAG.search(val), f"{label}[{i}].{key}: contains a tag")
            test.assertIsNone(
                _ENTITY.search(val),
                f"{label}[{i}].{key}: HTML entity — write the character",
            )
            # The Q&A is about the content, not where to read it.
            low = val.lower()
            test.assertNotIn("ochorus", low, f"{label}[{i}].{key}: names the site")
            test.assertNotIn("http", low, f"{label}[{i}].{key}: carries a URL")


class AuthorFaqTranslationShapeTests(SimpleTestCase):
    """The TRANSLATED editorial Q&A — ``<slug>.faq.json`` files under
    ``migrations/data/author_bios_<lang>/``, seeded into ``AuthorTranslation.faq``
    (like the ``.short.txt`` / ``.html`` bios). Each file must pass the same shape
    guard as the English set AND carry the same number of pairs — a translation
    answers every English question, no more and no fewer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rows = json.loads(AUTHORS_FILE.read_text(encoding="utf-8"))
        cls.en_faq_len = {
            r["fields"]["slug"]: len(r["fields"]["faq"])
            for r in rows
            if r["fields"].get("faq")
        }

    def test_translated_faq_files_are_well_formed_and_match_english(self):
        from library.management.commands.seed_author_translations import (
            DATA_DIR,
            PREFIX,
        )

        files = sorted(DATA_DIR.glob(f"{PREFIX}*/*.faq.json"))
        for path in files:
            lang = path.parent.name.removeprefix(PREFIX)
            slug = path.name.removesuffix(".faq.json")
            with self.subTest(faq=f"{slug} [{lang}]"):
                faq = json.loads(path.read_text(encoding="utf-8"))
                assert_qa_wellformed(self, faq, {"q", "a"}, f"{slug} [{lang}]")
                # A translation exists only for an author who has an English set,
                # and answers exactly its questions.
                self.assertIn(
                    slug, self.en_faq_len,
                    f"{slug} [{lang}]: translated faq for an author with no "
                    "English faq in authors.json",
                )
                self.assertEqual(
                    len(faq), self.en_faq_len[slug],
                    f"{slug} [{lang}]: {len(faq)} pairs vs "
                    f"{self.en_faq_len.get(slug)} in English — must match",
                )


class BookQaShapeTests(SimpleTestCase):
    """The editorial Q&A on ``Book.qa`` — the unified ``{question, answer}``
    contract new types adopt (docs/questions-and-answers-plan.md). Book qa rides
    the per-language row, so this checks every book file, not only English.
    """

    def test_qa_entries_are_well_formed_plain_text(self):
        # The whole corpus is already parsed once behind files_by_path()'s cache;
        # the book row is guaranteed first (test_book_files_coherent).
        for path, rows in files_by_path().items():
            if path.parent != BOOKS_DIR:
                continue
            qa = rows[0]["fields"].get("qa")
            if not qa:  # absent or [] — a book with no set yet
                continue
            with self.subTest(book=path.name):
                assert_qa_wellformed(self, qa, {"question", "answer"}, path.name)


class TopicQaShapeTests(SimpleTestCase):
    """The editorial Q&A on ``Topic.qa`` — same ``{question, answer}`` contract as
    books. Topics have no fixture; the English set lives in ``topic_seed.TOPIC_QA``
    (seeded onto the row, translated in ``TopicTranslation.qa``). Every slug must
    name a real topic, and every set must pass the shared shape guard.
    """

    def test_qa_entries_are_well_formed_plain_text(self):
        from library.topic_seed import TOPIC_QA, TOPICS

        slugs = {t[0] for t in TOPICS}
        for slug, qa in TOPIC_QA.items():
            with self.subTest(topic=slug):
                self.assertIn(slug, slugs, f"TOPIC_QA[{slug}] names no topic in TOPICS")
                assert_qa_wellformed(self, qa, {"question", "answer"}, slug)


class AuthorFaqShapeTests(SimpleTestCase):
    """The editorial Q&A on ``Author.faq``, shipped as plain-text JSON in
    ``authors.json``. The house rule: the Q&A talks about the PERSON, never the
    platform. Shares the shape guard with book qa via ``assert_qa_wellformed``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = json.loads(AUTHORS_FILE.read_text(encoding="utf-8"))

    def test_faq_entries_are_well_formed_plain_text(self):
        for row in self.rows:
            f = row["fields"]
            faq = f.get("faq")
            if not faq:  # absent or [] — an author with no set yet
                continue
            with self.subTest(slug=f["slug"]):
                assert_qa_wellformed(self, faq, {"q", "a"}, f["slug"])

    # Roughly two sentences. A tripwire for "someone pasted the real biography
    # in here", not a style rule — the biography belongs in authors.json.
    MAX_STUB_BIO = 320

    def test_catalog_bios_stay_short_stubs(self):
        """A catalog bio must not grow into a copy of the one in authors.json.

        `upsert_book` and `import_sermons` apply an `AuthorEntry.bio` only when
        the author row is first created (PR #449). Before that they overwrote on
        every import, so a short stub truncated the author's real bio — and the
        workaround each time was to paste the long `authors.json` text into the
        catalog, until most entries were hand-synced duplicates. The write is
        fixed; this keeps the duplicates from coming back.
        """
        from library.catalog import AUTHORS
        from library.sermon_catalog import SERMON_AUTHORS

        for entry in (*AUTHORS.values(), *SERMON_AUTHORS.values()):
            with self.subTest(slug=entry.slug):
                # Non-empty: for an author imported before they exist in
                # authors.json, this is the only bio they get.
                self.assertTrue(entry.bio.strip(), f"{entry.slug} has no bio")
                self.assertLessEqual(
                    len(entry.bio), self.MAX_STUB_BIO,
                    f"{entry.slug}'s bio reads like a full biography — that "
                    f"belongs in fixtures/content/authors.json, not catalog.py",
                )

    def test_every_catalog_slug_exists_in_authors_json(self):
        """A catalog author slug that authors.json doesn't have forks the author.

        `upsert_book` / `import_sermons` create whatever slug the `AuthorEntry`
        names. If that slug isn't the fixture's, a re-import doesn't update the
        real author — it creates a SECOND row holding only the catalog stub, no
        `bio_html`, no photo, and re-points the book at it. It can't fail at
        deploy (release seeds from the fixture), so nothing catches it until a
        local re-import plus a fixture regen commits the duplicate. That is
        exactly how `charles-spurgeon` drifted from the fixture's
        `charles-h-spurgeon` while five books pointed at it.
        """
        from library.catalog import AUTHORS
        from library.sermon_catalog import SERMON_AUTHORS

        fixture_slugs = set(authors_by_slug())
        dangling = sorted((set(AUTHORS) | set(SERMON_AUTHORS)) - fixture_slugs)
        self.assertEqual(
            dangling, [],
            "catalog author slugs missing from authors.json — importing one of "
            "their books would create a duplicate author instead of updating "
            "the real one",
        )


# Anchored on settings, like generate_covers' COVERS_DIR — walking up from the
# fixture dir would encode the content layout's depth into a fact about the
# frontend tree. Read by the cover and share-card gates below.
STATIC_DIR = settings.BASE_DIR.parent / "frontend" / "static"


class CoverAssetTests(SimpleTestCase):
    """Covers must be served by Ochorus and must actually exist.

    Two silent failures preceded PR #355. 28 books hotlinked ochorus.com's
    WordPress media — the site being retired — and those URLs also fed
    ``og:image``. And 18 had no ``cover_url`` at all, because
    ``generate_covers`` writes the SVG *and* sets the field, but only in the
    developer's local db; the artwork was committed and serving while the db
    half never had a vehicle to production. Neither surfaces as an error: a
    hotlink 200s until the day it doesn't, and an empty cover_url is a valid
    value that ``BookCover.svelte`` quietly papers over on most surfaces.

    These guard the fixture, which is where a *new* mistake enters. They cannot
    catch fixture-correct-but-prod-stale drift — that needs ``seed_books`` to
    upsert the way ``seed_sermons`` already does.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.books = [
            r["fields"] for r in all_rows() if r["model"] == "library.book"
        ]


    def test_every_painting_was_cut_from_its_entry(self):
        """A committed painting is kept across runs only while it was cut from
        the entry that credits it. Swap a work to a different artwork, or move
        its ``focus``, without redrawing, and the page would credit the new
        painter under the old picture — with every other gate green, since none
        of them look at what a museum image IS. ``art_sources.py`` records what
        each painting was drawn from; this holds it to the entries.
        """
        from library.art_sources import ART_SOURCES
        from library.covers import art_url
        from library.curated_art import crop_recipe

        entries = {**CURATED, **CURATED_GROUND}
        moved = sorted(
            f"{slug}: drawn from {ART_SOURCES.get(slug)}, entry is {crop_recipe(art)}"
            for slug, art in entries.items()
            if (STATIC_DIR / "covers" / art_url(slug)[1]).is_file()
            and ART_SOURCES.get(slug) != crop_recipe(art)
        )
        self.assertEqual(
            moved,
            [],
            "a painting no longer matches its CURATED entry — run "
            "`manage.py build_curated_covers <slug>` to redraw it",
        )
        stale = sorted(set(ART_SOURCES) - set(entries))
        self.assertEqual(stale, [], "art_sources.py names works that are no longer curated")
    def test_published_covers_are_self_hosted(self):
        external = sorted(
            (f["slug"], f["language"], _cover(f))
            for f in self.books
            if f.get("is_published") and "://" in _cover(f)
        )
        self.assertEqual(
            external, [],
            "published books must serve covers from Ochorus, not a third-party "
            "host — download into frontend/static/covers/ and repoint",
        )

    def test_cover_files_exist(self):
        missing = sorted(
            (f["slug"], f["language"], _cover(f))
            for f in self.books
            if _cover(f).startswith("/")
            and not (STATIC_DIR / _cover(f).lstrip("/")).is_file()
        )
        self.assertEqual(missing, [], "cover_url points at a file that isn't committed")

    def test_published_books_have_a_cover(self):
        blank = sorted(
            (f["slug"], f["language"])
            for f in self.books
            if f.get("is_published") and not _cover(f)
        )
        self.assertEqual(
            blank, [],
            "published book with no cover — flat colour on every surface that "
            "doesn't route through BookCover (CoverStrip, ContinueReading, /topics)",
        )

    def test_translated_editions_wear_their_own_cover(self):
        """A translated row may not point at another language's cover file.

        Covers are per ``(slug, language)`` and live at ``/covers/<lang>/<slug>``
        (English at the root). A translated row carrying the English path shows
        the English title over a translated card — "All of Grace" above "Todo por
        Gracia" — which for this library is the wrong thing to show.

        It keeps coming back because it is the *easy* mistake: a new translation
        is written by copying the English fixture row, ``cover_url`` included,
        and nothing downstream complains. ``generate_covers`` and
        ``scripts/localize_covers.py`` both write the right file; only this
        catches a row that never got repointed at it. 58 rows were fixed by hand
        in PR #355's follow-up and 21 had drifted back within the month, which is
        why the rule is now a test rather than a paragraph.
        """
        # Pinned as "under this language's directory, named for this slug"
        # rather than equality with cover_path(): the extension is left open so
        # a translated edition can carry designed artwork of its own the day one
        # is drawn, which equality would forbid. Directory and identity are the
        # parts that were actually wrong.
        #
        # `covers/art/` is exempt, and the exemption is the whole point of that
        # tier: a painting carries NO WORDS, so it is language-neutral and every
        # edition shares one file — the type is drawn over it, per language, by
        # BookCover. This rule exists because a cover with English words baked in
        # was appearing over a Swahili card; a cover with no words in it cannot
        # commit that mistake.
        wrong = sorted(
            (f["slug"], f["language"], _cover(f))
            for f in self.books
            if f["language"] != "en"
            and _cover(f).startswith("/covers/")
            and not _cover(f).startswith("/covers/art/")
            and not _cover(f).startswith(f"/covers/{f['language']}/{f['slug']}.")
        )
        self.assertEqual(
            wrong, [],
            "translated edition wearing another edition's cover — expected "
            "/covers/<lang>/<slug>.<ext> (see library.covers.cover_path); run "
            "`uv run python scripts/localize_covers.py` to draw and repoint it",
        )

    def test_translated_editions_set_their_own_cover_title(self):
        """A translated edition never sets another language's words on its
        cover — which an edition written by copying the English file would."""
        english = {
            f["slug"]: f.get("cover_title") for f in self.books if f["language"] == "en"
        }
        copied = sorted(
            f"{f['slug']}.{f['language']}: {f['cover_title']!r}"
            for f in self.books
            if f["language"] not in ("en", MODERN_LANGUAGE)
            and f.get("cover_title")
            and f["cover_title"] == english.get(f["slug"])
        )
        self.assertEqual(
            copied, [], "translated edition sets the English cover title — translate it or blank it"
        )

    def test_cover_title_is_trimmed_and_shorter_than_the_title(self):
        """It exists to be shorter; one that is not is a typo in the wrong field.
        Trimmed here rather than at render, so ``coverTitle.ts`` and
        ``_cover_title`` need not agree on what counts as whitespace."""
        bad = sorted(
            f"{f['slug']}.{f['language']}"
            for f in self.books
            if f.get("cover_title")
            and (
                f["cover_title"] != f["cover_title"].strip()
                or len(f["cover_title"]) >= len(f["title"])
            )
        )
        self.assertEqual(bad, [], "cover_title should be trimmed and shorter than title")

    def test_plate_colours_can_carry_white_type(self):
        """Every stored `cover_color` must be dark enough for the white byline.

        The type on a cover is always white, so a plate colour is only legible
        if white can sit on it — and 6 of the library's 45 colours could not,
        down to 3.16:1 against the 4.5:1 AA asks of a 23px line.

        This gates the DATA, where the mistake is made: a hex typed into
        `catalog.py` or minted by `palette_from_artwork`. `covers.ink_safe`
        floors both on the way in, so a failure here means a colour that reached
        the fixture some other way — hand-edited, or imported before the floor
        existed. Run it through `ink_safe` and commit the result.
        """
        pale = sorted(
            (f["slug"], f["language"], _cover_color(f), f"{author_ink_contrast(_cover_color(f)):.2f}:1")
            for f in self.books
            if _cover_color(f) and author_ink_contrast(_cover_color(f)) < AUTHOR_MIN_CONTRAST
        )
        self.assertEqual(
            pale, [],
            "cover_color too pale to carry the white author line at WCAG AA — "
            "floor it with covers.ink_safe",
        )

    def test_generated_plates_carry_white_type_at_aa(self):
        """Every committed plate must be dark enough for the white byline.

        The author line is 23px — not "large text" under WCAG 1.4.3 — so AA asks
        4.5:1 of it, and 16 committed covers gave less, down to 3.16:1 on
        `the-unselfishness-of-god`. A plate colour is DATA (hand-picked, or
        sampled from the English artwork) and nothing between the two ever asked
        whether white could sit on it; `covers.ink_safe` now floors it as it
        draws, and this fails any committed file drawn before that or by hand.

        Reads the artwork rather than the fixture on purpose: the fixture holds
        the book's chosen colour, which stays its own, while the file holds what
        a reader actually sees. Curated covers are skipped — their type sits on a
        painting under a scrim, which this arithmetic can't speak for — and they
        are recognised by the CURATED manifest, the same key `generate_covers`
        uses, rather than by sniffing the embedded image: `build_curated_covers`
        is one `sips` flag away from emitting something other than JPEG, and a
        sniff would then fail every curated cover instead of skipping it.
        """
        failures = []
        for svg in sorted((STATIC_DIR / "covers").rglob("*.svg")):
            if svg.stem in CURATED:
                continue
            source = svg.read_text(encoding="utf-8")
            stop = re.search(r'<stop offset="0" stop-color="(#[0-9a-f]{6})"', source)
            if not stop:
                failures.append((str(svg.relative_to(STATIC_DIR)), "no plate gradient"))
                continue
            ratio = author_ink_contrast(stop.group(1))
            if ratio < AUTHOR_MIN_CONTRAST:
                failures.append((str(svg.relative_to(STATIC_DIR)), f"{ratio:.2f}:1"))
        self.assertEqual(
            failures, [],
            "generated cover whose author line fails WCAG AA (4.5:1) — redraw it "
            "with `generate_covers --force` / `scripts/localize_covers.py --force`, "
            "which floors the plate through covers.ink_safe",
        )

    def test_committed_plates_carry_no_words(self):
        """A plate on disk is a GROUND: colour, vignette, emblem, no type.

        The words moved to `BookCover.svelte` so a cover could be set in a real
        webfont — an SVG served through `<img>` renders in a document that
        cannot reach the page's fonts, so every generated cover in the library
        used to come out in Georgia. A file that still has a `<text>` node in it
        is one drawn before that (or by hand) and would show a second title
        under the one the browser sets — in English, over a translated card, on
        seven locales out of eight.

        Reads the artwork rather than the generator, like the AA gate above it:
        `build_ground` cannot emit type any more, so what this can still catch
        is a STALE committed file. Run `generate_covers --force` and
        `scripts/localize_covers.py --force` to redraw them.
        """
        wordy = sorted(
            str(svg.relative_to(STATIC_DIR))
            for svg in (STATIC_DIR / "covers").rglob("*.svg")
            if "<text" in svg.read_text(encoding="utf-8")
        )
        self.assertEqual(
            wordy, [],
            "committed plate with type baked into it — redraw it with "
            "`generate_covers --force` / `scripts/localize_covers.py --force`",
        )

    def test_raster_covers_ship_their_responsive_variants(self):
        """Every raster cover must have the webp variants `srcset` promises.

        `BookCover` derives `<slug>-320.webp` / `-640.webp` by convention rather
        than from a manifest, so a missing variant is a broken image on the
        shelf, not a graceful fallback. The 27 raster covers a reader can fetch
        weighed 1.5 MB at full size and 346 KB at the width they are painted;
        this is what keeps that true as covers are added.

        Run `uv run python scripts/build_cover_assets.py` to fill the gaps.
        """
        missing = []
        for f in self.books:
            cover = _cover(f)
            if not cover.endswith(RASTER_SUFFIXES):
                continue
            for width in COVER_WIDTHS:
                variant = variant_url(cover, width)
                if not (STATIC_DIR / variant.lstrip("/")).is_file():
                    missing.append(variant)
        self.assertEqual(
            sorted(set(missing)), [],
            "raster cover without its webp variants — run "
            "`uv run python scripts/build_cover_assets.py`",
        )

    def test_curated_editions_share_one_painting(self):
        """A shared-picture work ships ONE image, and every language points at it.

        Covers both all-language tiers — ``CURATED`` (a museum painting) and
        ``ORIGINAL_GROUND`` (an illustration drawn for the work). The invariant
        is identical: one wordless file under ``covers/art/``, worn by every
        edition including English, because neither tier keeps a designed cover.

        The artwork used to be embedded in a per-language SVG, because an SVG
        served through <img> cannot fetch a sibling file — so `waiting-on-god`
        carried six copies of one painting (430 KB), and a reader who switched
        locale downloaded it again under a new URL. The type moved to HTML, so
        the painting is now a plain image: one file, one cache entry, one
        download, whatever language you read in.
        """
        shared = set(CURATED) | set(ORIGINAL_GROUND)
        wrong = sorted(
            (f["slug"], f["language"], _cover(f))
            for f in self.books
            if f["slug"] in shared and _cover(f) != art_url(f["slug"])[0]
        )
        self.assertEqual(
            wrong, [],
            "shared-picture edition not pointing at its one image "
            "(/covers/art/<slug>.jpg) — run scripts/build_cover_assets.py",
        )
        absent = sorted(
            slug for slug in shared
            if any(f["slug"] == slug for f in self.books)
            and not (STATIC_DIR / "covers" / art_url(slug)[1]).is_file()
        )
        self.assertEqual(absent, [], "shared-picture work with no committed image")

    def test_every_twin_was_made_from_the_cover_it_stands_in_for(self):
        """Existence was never the hard part — staleness was.

        The twin check above passes on a file from any era, and for months every
        one of them was a design generation out of date: "OCHORUS" at the top and
        the author at the foot, the layout `covers.py` abandoned. Nothing noticed,
        because a share card is only ever seen by someone who is not us.

        `npm run og:covers` records what each twin was drawn from; this recomputes
        those digests. Redraw a plate or retitle a book and the build fails until
        the twins are re-run. It cannot see a change to the SCRIPT's own
        composition — only re-running that can — so this is a floor, not a proof.

        HALF THE SUBJECT, ON PURPOSE. A card is made from its ground, its
        strings, and the house style its author's century is set in. The first
        two are here; the style is decided by a TypeScript table
        (`coverStyles.ts`) and applied by a CSS class, and parsing either from
        Python to fold into this digest would be a worse copy than the one it
        replaced — it is not that this test cannot reach `frontend/` (it reads
        `STATIC_DIR` throughout), it is that it cannot evaluate that table. So
        the manifest records the style beside the digest and
        `coverOgManifest.test.ts` checks it from the side that owns it. Each
        half is checked where it can actually be derived.
        """
        manifest_file = STATIC_DIR / "covers" / "og-manifest.json"
        self.assertTrue(
            manifest_file.is_file(),
            "frontend/static/covers/og-manifest.json is missing — run "
            "`cd frontend && npm run og:covers`",
        )
        recorded = json.loads(manifest_file.read_text())["twins"]

        # EVERY EDITION, not the English rows. A card carries the title in its
        # pixels, so each language has its own; checking only English left 93 of
        # the 130 committed cards unverified, and this gate reported green with
        # a translated twin deleted from disk.
        editions = {
            (f["slug"], f["language"]): f for f in self.books
        }
        # Hoisted: `authors_by_slug` re-reads and re-parses authors.json on every
        # call, and this loop runs over every row.
        names = authors_by_slug()
        stale, unrecorded = [], []
        for (slug, language), fields in sorted(editions.items()):
            key = twin_path(slug, language)[1].removesuffix(".png")
            cover = _cover(fields)
            art = cover.startswith("/covers/art/")
            # Under `/covers/` on BOTH arms, which is what `needTwins` in the
            # generator tests (`isArtCover` / `isPlateCover`). Without the prefix
            # this demanded a twin for a `.svg` hosted anywhere — an unpublished
            # row can carry one, since the self-hosting gate only checks
            # published books — and the generator, which reads the ground off
            # disk, can never produce it. That is a red build no re-run fixes.
            if not cover.startswith("/covers/") or not (art or cover.endswith(".svg")):
                continue  # a designed raster, or not ours; twins are ensure_og_twin's
            if key not in recorded:
                unrecorded.append(key)
                continue
            # The row's OWN cover_url on both arms: a translated plate already
            # names its language directory, and a painting is one shared file for
            # every edition. The plate arm used to rebuild the path from the slug,
            # which was the English one whatever row it was looking at.
            source = STATIC_DIR / cover.lstrip("/")
            if not source.is_file():
                continue  # the twin gate above owns "the file isn't there"
            # The type is drawn over the ground at render time — for BOTH tiers
            # now, since a plate carries no words either — so the strings are
            # part of what the card was made from.
            author = names.get(fields["author"][0], {}).get("name", fields["author"][0])
            blob = source.read_bytes() + "\0{}\0{}\0{}".format(
                _cover_title(fields), fields.get("subtitle") or "", author
            ).encode()
            if hashlib.sha256(blob).hexdigest() != recorded[key].get("ground"):
                stale.append(key)

        self.assertEqual(
            unrecorded, [], "cover with no entry in og-manifest.json — run `npm run og:covers`"
        )
        self.assertEqual(
            stale, [],
            "the cover changed but its og:image twin did not — a shared link "
            "would show the previous design. Run `cd frontend && npm run og:covers`",
        )

    # ── The hand-made covers ────────────────────────────────────────────────
    # `library.designed_covers` states the rule and holds the digests; these two
    # are what make it a rule rather than a paragraph.

    def test_designed_covers_are_never_changed(self):
        """A registered hand-made cover must be byte-for-byte what we drew.

        Every other cover in the library is output — a plate ground, a webp
        variant, an og twin — and each of its tools decides what a book should
        look like from the book's data. A designed cover carries a judgement no
        data records, so nothing may redraw it.

        Existence was never the hard part. `test_cover_files_exist` has always
        passed on a file from any era, which is exactly how a whole generation
        of stale share cards stayed green for months
        (`test_every_twin_was_made_from_the_cover_it_stands_in_for` is the same
        lesson, one tier over). This pins the BYTES, so an overwrite, a
        re-compression or a well-meaning optimisation pass fails here naming the
        file it touched.

        Replacing one on purpose is a two-line diff — new file, new digest.
        """
        missing, changed = [], []
        for url, recorded in sorted(DESIGNED.items()):
            path = STATIC_DIR / url.lstrip("/")
            if not path.is_file():
                missing.append(url)
            elif digest(path) != recorded:
                changed.append(url)
        self.assertEqual(
            missing, [], "registered designed cover is not committed"
        )
        self.assertEqual(
            changed, [],
            "a hand-made cover changed. Nothing may redraw one of these — if a "
            "script did, that script has a bug (see "
            "library/designed_covers.py). If you meant to replace the artwork, "
            "update its digest in DESIGNED in the same commit",
        )

    def test_every_designed_cover_is_registered(self):
        """A row wearing a designed raster must have an entry in `DESIGNED`.

        Registering is how a cover becomes protected, so a new hand-made cover
        that nobody wrote down is one the gate above cannot defend. Scoped to
        rasters under `/covers/` that are not `covers/art/`: a painting and a
        derived ground ARE output — `build_curated_covers` and
        `build_derived_grounds` can draw them again from their recipes — and
        freezing those would forbid the redraw their scripts exist to do.
        """
        unregistered = set()
        for f in self.books:
            url = _cover(f)
            if (
                url.startswith("/covers/")
                and not url.startswith("/covers/art/")
                and url.endswith(RASTER_SUFFIXES)
                and url not in DESIGNED
            ):
                unregistered.add(url)
        unregistered = sorted(unregistered)
        self.assertEqual(
            unregistered, [],
            "designed cover with no entry in library.designed_covers.DESIGNED "
            "— add it with its sha256 so nothing can redraw it",
        )

    def test_original_grounds_are_frozen(self):
        """An Ochorus Original's ground is a hand-made file nothing can redraw.

        The gate above deliberately EXEMPTS `covers/art/` — a museum painting
        and a derived crop are output their scripts can draw again, so freezing
        the bytes would forbid the redraw. An `ORIGINAL_GROUND` file is the
        exception in that exemption: it is an illustration drawn for the work,
        with no museum to re-fetch and no designed cover to re-crop, so it is as
        un-redrawable as a designed cover — and frozen the same way, by the
        SHA-256 recorded beside it in `curated_art.ORIGINAL_GROUND`.

        Without this, an Original ground would be the one raster in the library
        that no gate pins: outside `DESIGNED` because it is wordless, inside
        `covers/art/` where the digest gate does not look. Replacing one on
        purpose stays a two-line diff — new file, new digest.
        """
        missing, changed = [], []
        for slug, art in sorted(ORIGINAL_GROUND.items()):
            path = STATIC_DIR / "covers" / art_url(slug)[1]
            if not path.is_file():
                missing.append(slug)
            elif digest(path) != art.sha256:
                changed.append(slug)
        self.assertEqual(
            missing, [],
            "an ORIGINAL_GROUND names a work with no committed illustration at "
            "covers/art/<slug>.jpg",
        )
        self.assertEqual(
            changed, [],
            "an Ochorus Original's ground changed but its recorded sha256 did "
            "not — nothing may redraw one of these. If you replaced the artwork "
            "on purpose, update its digest in curated_art.ORIGINAL_GROUND in the "
            "same commit",
        )

    def test_original_svg_grounds_are_frozen(self):
        """The SVG Originals under `covers/art/` are frozen like the raster ones.

        The two gates around this one glob `*.jpg` only, so a hand-drawn SVG
        ground — the Key Teachings trees — was pinned by nothing: a script or a
        tidy-up could redraw it and CI would stay green. Every SVG there must be
        registered in `curated_art.ORIGINAL_SVG_GROUND`, and its bytes must
        still match the digest recorded beside it.
        """
        art = STATIC_DIR / "covers" / "art"
        present = {p.stem for p in art.glob("*.svg")}
        self.assertEqual(
            sorted(present - set(ORIGINAL_SVG_GROUND)), [],
            "an SVG ground under covers/art/ is unregistered — add it to "
            "curated_art.ORIGINAL_SVG_GROUND with its sha256",
        )
        self.assertEqual(
            sorted(set(ORIGINAL_SVG_GROUND) - present), [],
            "an ORIGINAL_SVG_GROUND names a file that is not in covers/art/",
        )
        changed = sorted(
            slug for slug, original in ORIGINAL_SVG_GROUND.items()
            if digest(art / f"{slug}.svg") != original.sha256
        )
        self.assertEqual(
            changed, [],
            "an SVG Original changed but its recorded sha256 did not — nothing "
            "may redraw one. If you replaced it on purpose, update its digest in "
            "curated_art.ORIGINAL_SVG_GROUND in the same commit",
        )

    def test_original_svg_grounds_carry_their_measured_scrim(self):
        """Each SVG Original has a measured scrim, and the table ships it as-is.

        The raster gate below re-measures every `.jpg` against `ART_SCRIM`; it
        cannot open an SVG, so these are measured outside it (see
        `curated_art.ORIGINAL_SVG_SCRIM`) and pinned by the digest above. What
        this holds is the join: no SVG Original without a measurement, and the
        generated table carrying exactly that value — so a hand edit to
        `art_scrim.py` can't quietly darken or lighten one.
        """
        from library.art_scrim import ART_SCRIM

        self.assertEqual(sorted(ORIGINAL_SVG_SCRIM), sorted(ORIGINAL_SVG_GROUND))
        drift = {
            slug: (ART_SCRIM.get(slug), k)
            for slug, k in ORIGINAL_SVG_SCRIM.items()
            if ART_SCRIM.get(slug) != k
        }
        self.assertEqual(
            drift, {},
            "art_scrim.ART_SCRIM disagrees with curated_art.ORIGINAL_SVG_SCRIM — "
            "re-run scripts/tune_art_scrim.py, which carries these in",
        )

    def test_every_art_file_belongs_to_a_tier(self):
        """Every file under `covers/art/` is claimed by a shared-ground tier.

        `covers/art/` is the one raster directory the `DESIGNED` digest gate
        skips, on the promise that everything in it is either re-drawable
        (`CURATED`, `CURATED_GROUND`, `DERIVED_GROUND`) or frozen by its own tier
        (`ORIGINAL_GROUND`). An unclaimed file breaks that promise: an Original
        dropped here without its `ORIGINAL_GROUND` entry `shares_a_ground` cannot
        see, so `build_cover_assets` treats its row as a plain raster and
        `test_original_grounds_are_frozen` never freezes it — the un-redrawable
        illustration ships with nothing pinning its bytes. This is the gate that
        makes registering an Original the only way to add one.
        """
        # `shares_a_ground` IS the four-tier union, and re-spelling it here would
        # be the fifth hand-kept copy its docstring exists to prevent — so a
        # future tier is covered by this gate the moment it joins the predicate.
        orphans = sorted(
            p.stem
            for p in (STATIC_DIR / "covers" / "art").glob("*.jpg")
            if not shares_a_ground(p.stem)
        )
        self.assertEqual(
            orphans, [],
            "a file under covers/art/ belongs to no shared-ground tier — an "
            "original illustration must be registered in "
            "curated_art.ORIGINAL_GROUND (with its sha256) so it is frozen, and "
            "a museum painting in CURATED/CURATED_GROUND",
        )

    def test_derived_grounds_clothe_every_translation(self):
        """A work with a derived ground: English keeps the designed cover, and
        every other language wears the ground.

        This is the split the tier exists for, and both halves are load-bearing.
        If a translated row drifts back to a plate — which is what happens by
        default, since `translate_book` copies `cover_url` from the English file
        — that edition is a coloured slab again while its siblings carry the
        photograph. And if the ENGLISH row were ever repointed at the ground, the
        work would silently lose the hand-made cover this whole tier was built to
        preserve.
        """
        # `test_cover_files_exist` would also catch a missing ground, but only
        # once a row points at it. This catches the state in between — added to
        # DERIVED_GROUND, never drawn — and names the script that draws it.
        absent = sorted(
            slug for slug in DERIVED_GROUND
            if not (STATIC_DIR / "covers" / art_url(slug)[1]).is_file()
        )
        self.assertEqual(
            absent, [],
            "derived ground not committed — run "
            "`uv run python scripts/build_derived_grounds.py`",
        )
        wrong = []
        for f in self.books:
            slug = f["slug"]
            if slug not in DERIVED_GROUND:
                continue
            expected = (
                DESIGNED_BY_SLUG[slug] if f["language"] == "en" else art_url(slug)[0]
            )
            if _cover(f) != expected:
                wrong.append((slug, f["language"], _cover(f), expected))
        self.assertEqual(
            wrong, [],
            "a derived-ground work wearing the wrong cover — English wears the "
            "designed file, every other language wears /covers/art/<slug>.jpg "
            "(run `uv run python scripts/localize_covers.py`)",
        )

    def test_designed_covers_index_cleanly(self):
        """`DESIGNED_BY_SLUG` must lose nothing, and every ground must resolve.

        Three one-line invariants that the code around them assumes and nothing
        else states.

        The index is keyed by stem, so two designed covers with the same stem
        would collapse into one entry and the loser would vanish silently. That
        is not hypothetical: `test_translated_editions_wear_their_own_cover`
        deliberately leaves the extension open so a translated edition can carry
        designed artwork of its own at `/covers/<lang>/<slug>.<ext>`, and the
        day one is drawn its stem is a slug already in here.

        `DERIVED_GROUND ⊆ DESIGNED_BY_SLUG` because three sites index it
        unguarded — an entry added before its cover is registered would surface
        as a bare `KeyError`, including from inside the gate whose message names
        the fix.

        And the two shared-ground tiers must not overlap: both write
        `covers/art/<slug>.jpg`, so a slug in `CURATED` and `DERIVED_GROUND`
        alike lets `build_derived_grounds --force` overwrite a licensed museum
        painting with a crop of a ministry photograph.
        """
        stems = [
            url.removeprefix("/covers/").rsplit(".", 1)[0]
            for url in DESIGNED
            if "/" not in url.removeprefix("/covers/")
        ]
        self.assertEqual(
            sorted(s for s, n in Counter(stems).items() if n > 1), [],
            "two designed covers share a slug — DESIGNED_BY_SLUG would keep "
            "only one of them",
        )
        self.assertEqual(
            sorted(set(DERIVED_GROUND) - set(DESIGNED_BY_SLUG)), [],
            "a derived ground names a work with no registered designed cover",
        )
        # THREE tiers write `covers/art/<slug>.jpg` now, so the exclusivity is
        # pairwise rather than a single intersection. `CURATED_GROUND` overlaps
        # the other two in the two different ways that are each wrong: with
        # `DERIVED_GROUND` it is two recipes for one file, and with `CURATED` it
        # is a disagreement about whether English keeps a designed cover — which
        # `keeps_english_designed` would answer yes to while the curated gate
        # demands every edition point at the painting.
        for a, b in (
            ("CURATED", "DERIVED_GROUND"),
            ("CURATED", "CURATED_GROUND"),
            ("CURATED_GROUND", "DERIVED_GROUND"),
            ("CURATED", "ORIGINAL_GROUND"),
            ("CURATED_GROUND", "ORIGINAL_GROUND"),
            ("DERIVED_GROUND", "ORIGINAL_GROUND"),
        ):
            tiers = {
                "CURATED": CURATED,
                "DERIVED_GROUND": DERIVED_GROUND,
                "CURATED_GROUND": CURATED_GROUND,
                "ORIGINAL_GROUND": ORIGINAL_GROUND,
            }
            self.assertEqual(
                sorted(set(tiers[a]) & set(tiers[b])), [],
                f"a work is in both {a} and {b} — the two tiers write the same "
                "file, so one would overwrite the other's artwork",
            )

        # A ground for a work with no designed cover has nothing to be the
        # ground FOR: `keeps_english_designed` would send its English edition to
        # a hand-made raster that does not exist, and `build_cover_assets`
        # hard-exits on the missing file. Such a work belongs in `CURATED`.
        self.assertEqual(
            sorted(set(CURATED_GROUND) - set(DESIGNED_BY_SLUG)), [],
            "a curated ground names a work with no registered designed cover — "
            "it wants CURATED, which points every edition at the painting",
        )

    def test_derived_grounds_were_cut_from_the_current_cover(self):
        """A ground must record the digest of the cover it was cut from.

        This is what keeps "replacing a hand-made cover is a two-line diff"
        true for the fourteen works that have one. Swap the artwork and update
        its digest, and every other gate stays green over a ground and an og
        twin still cut from the RETIRED photograph — the digest gate re-reads
        whatever you just wrote, the twin-staleness gate skips designed
        rasters by design, and both writers bail on `dest.exists()`. Every
        translated edition would go on wearing the old picture.

        Same lesson `og-manifest.json` records one tier over: existence was
        never what went wrong, staleness was.
        """
        stale = sorted(
            slug for slug, cut in DERIVED_GROUND.items()
            if slug in DESIGNED_BY_SLUG
            and cut.source != DESIGNED[DESIGNED_BY_SLUG[slug]]
        )
        self.assertEqual(
            stale, [],
            "the designed cover changed but the ground cut from it did not — "
            "every translated edition still wears the retired artwork. Run "
            "`uv run python scripts/build_derived_grounds.py --force <slug>`, "
            "then update that work's Ground(source=...)",
        )

    def test_a_translated_designed_work_has_a_ground(self):
        """A designed cover + a translation must mean a derived ground.

        THIS IS THE GATE THAT MAKES THE FIX DEFAULT-ON, and without it the whole
        tier is a one-time cleanup rather than a rule.

        `DERIVED_GROUND`'s membership silently encodes "has translations today".
        Eleven registered designed covers are English-only and rightly have no
        ground — drawing one nobody points at is how a file with no reader gets
        committed. But the day one of those eleven is translated,
        `localize_covers` falls into its artwork branch and draws exactly the
        flat coloured plate this tier exists to replace, and every other gate
        stays green: `test_translated_editions_wear_their_own_cover` is
        perfectly satisfied by `/covers/<lang>/<slug>.svg`.

        So the regression would arrive silently, in the same shape, through the
        same door it came in the first time. This closes it: translate such a
        work and the build asks for its ground.
        """
        translated = {
            f["slug"] for f in self.books
            if f.get("language") != "en" and f["slug"] in DESIGNED_BY_SLUG
        }
        # EITHER designed-cover ground satisfies this. The requirement is that
        # a wordless ground EXISTS for the translations, not that it was cut
        # from the cover: `CURATED_GROUND` is the tier for a designed cover with
        # no croppable picture in it, and a work there is as covered as one in
        # `DERIVED_GROUND`.
        self.assertEqual(
            sorted(translated - set(DERIVED_GROUND) - set(CURATED_GROUND)), [],
            "a work with a designed English cover now has a translation, and "
            "no wordless ground for it to wear — that edition would fall back "
            "to a flat plate. Add it to DERIVED_GROUND with its crop, then run "
            "`uv run python scripts/build_derived_grounds.py` — or, if nothing "
            "croppable survives losing the words, to CURATED_GROUND with a "
            "painting and run `manage.py build_curated_covers`",
        )

    def test_a_curated_ground_leaves_english_on_its_designed_cover(self):
        """The whole point of the tier, asserted where it can actually fail.

        `CURATED_GROUND` exists so a work can have BOTH: the hand-made English
        cover someone drew, and a real painting for the languages that cover
        cannot serve. Those are two claims about `cover_url`, and each fails
        differently and quietly.

        Point English at the painting and the designed cover is retired — no
        error anywhere, because a row pointing at a painting that exists is
        exactly what the curated tier looks like. Leave a translation on the
        designed cover and that reader is back to English words baked into a
        raster, which is the defect the whole ground system was built for.

        `test_every_edition_points_at_a_cover_that_exists` would pass on both.
        """
        wrong = []
        for f in self.books:
            slug, language, cover = f["slug"], f.get("language"), _cover(f)
            if slug not in CURATED_GROUND:
                continue
            wants = (
                DESIGNED_BY_SLUG[slug] if language == "en" else art_url(slug)[0]
            )
            if cover != wants:
                wrong.append((slug, language, cover, wants))
        self.assertEqual(
            wrong, [],
            "a curated-ground edition wears the wrong cover — English keeps its "
            "designed raster, every other language takes /covers/art/<slug>.jpg. "
            "Run `uv run python scripts/build_cover_assets.py`",
        )
        absent = sorted(
            slug for slug in CURATED_GROUND
            if any(f["slug"] == slug for f in self.books)
            and not (STATIC_DIR / "covers" / art_url(slug)[1]).is_file()
        )
        self.assertEqual(
            absent, [],
            "curated-ground work with no committed painting — run "
            "`manage.py build_curated_covers <slug>`",
        )

    def test_every_painting_still_carries_white_type(self):
        """The scrim is light enough that this is no longer a tautology.

        `.cover-plate.over-art` used to be heavy enough that a sheet of pure
        WHITE cleared AA under it — so measuring the committed paintings proved
        nothing, and the frontend gate says so in as many words. It was also why
        a translated cover looked dark beside its English one: every painting
        was shown at 38.7% of its own brightness, and at the foot as little as
        21%, because a single even wash had to serve the brightest artwork in
        the library.

        The scrim now follows the type — three overlapping bands, air between —
        and the paintings read at 53.4%. The guarantee narrows with it: white
        type is safe over THESE paintings, not over any painting. So the
        measurement has to be real, and this is it. Add a pale painting and this
        fails with its name before a reader finds it.

        Pillow is a dev-group dependency, like the rest of `CoverAssetTests`'
        image work; the whole sweep is well under a second.
        """
        from PIL import Image

        from library.art_scrim import ART_SCRIM
        from library.covers import INK_REGIONS, scrimmed

        def relative_luminance(channels):
            def channel(v):
                v /= 255
                return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

            r, g, b = (channel(c) for c in channels)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        def worst(band, opacity):
            """Least white-on-artwork contrast anywhere in a band."""
            out = 1e9
            for px in band.getdata():
                ink = tuple(round(255 * opacity + c * (1 - opacity)) for c in px)
                a, b = relative_luminance(ink) + 0.05, relative_luminance(px) + 0.05
                out = min(out, max(a, b) / min(a, b))
            return out

        art_dir = STATIC_DIR / "covers" / "art"
        # WHICH WORKS DRAW A SUBTITLE, because that decides both the scrim curve
        # and whether there is a subtitle strip to measure. Any language: the
        # painting is one file for every edition, so a Spanish subtitle needs the
        # band as much as an English one.
        subtitled = {
            f["slug"] for f in self.books if (f.get("subtitle") or "").strip()
        }
        thin, untuned = [], []
        for path in sorted(art_dir.glob("*.jpg")):
            # AT ITS OWN STRENGTH, which is the thing being checked. A painting
            # with no entry falls back to the full scrim — the safe end, and what
            # every painting carried before the table existed — but it is still
            # reported, because an untuned painting is carrying the weight the
            # palest artwork in the library needs.
            if path.stem not in ART_SCRIM:
                untuned.append(path.stem)
            has_sub = path.stem in subtitled
            plate = scrimmed(
                Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS),
                ART_SCRIM.get(path.stem, 1.0),
                has_sub,
            )
            # EVERY STRIP THAT CARRIES INK, from the one table the tuner reads.
            # This used to measure the byline and the title and stop. The byline
            # band was also 8px short of the real byline, so five paintings were
            # failing in rows nothing looked at; the subtitle and the brandmark
            # were not measured at all, and 36 of 38 paintings were under 4.5:1
            # under the subtitle. `INK_REGIONS` is shared with
            # `scripts/tune_art_scrim.py` so the bar this gate holds and the bar
            # that script tunes to cannot drift apart.
            bad = []
            for name, top, bottom, opacity, bar in INK_REGIONS:
                if name == "subtitle" and not has_sub:
                    continue
                got = worst(
                    plate.crop((_FRAME_INSET, top, W - _FRAME_INSET, bottom)), opacity
                )
                if got < bar:
                    bad.append(f"{name} {got:.2f}:1 (needs {bar})")
            if bad:
                thin.append(f"{path.stem}: {', '.join(bad)}")
        self.assertEqual(
            thin, [],
            "a painting too pale for the ink it carries under the scrim it is "
            "given — re-run `cd backend && uv run python scripts/tune_art_scrim.py`, "
            "or recrop the artwork if no strength carries it",
        )
        self.assertEqual(
            untuned, [],
            "a painting with no measured scrim strength — it is wearing the "
            "weight the palest artwork needs. Run "
            "`cd backend && uv run python scripts/tune_art_scrim.py`",
        )

    def test_covers_that_cannot_be_shared_have_a_raster_twin(self):
        """og:image falls back to an edition's twin — that file must exist.

        Two covers can't stand in for themselves on a social card: a generated
        `.svg`, which every platform refuses, and a `covers/art/` painting,
        which carries no words because the title is drawn over it in the
        browser. Both fall back to the twin (books/[slug]/+page.svelte).

        The art tier is the newer half of this rule and the reason it is worth
        stating: nothing writes a twin for a curated work — `localize_covers`'
        `ensure_og_twin` only fires for the artwork tier — so the ten that pass
        today do so on leftovers from when curated covers were SVGs. Without
        this, the eleventh curated work would ship a 404 og:image with every
        gate green.
        """
        # PER EDITION. This iterated every row and then looked for the ENGLISH
        # twin of each, so an Arabic row was satisfied by the English card — the
        # same file og:image was wrongly serving it. Deleting a translated twin
        # outright left this green; it is what `twin_path` was extracted for.
        missing = sorted(
            twin_path(f["slug"], f["language"])[0]
            for f in self.books
            if (_cover(f).endswith(".svg") or _cover(f).startswith("/covers/art/"))
            and not (STATIC_DIR / "covers" / twin_path(f["slug"], f["language"])[1]).is_file()
        )
        self.assertEqual(
            missing, [],
            "an edition whose cover can't be its own og:image, with no .png twin — "
            "run `cd frontend && npm run og:covers`",
        )


def _sermon_content_digest(fields: dict, names: dict) -> str:
    """The ``content`` digest a sermon's share card is drawn from.

    Mirrors ``contentDigest`` in ``generate-sermon-og.mjs`` — the strings the
    card sets, in the order it joins them. Shared by the English and the
    localized freshness checks so the three (with the generator) cannot drift.
    """
    author_slug = fields["author"][0]
    blob = "\0".join(
        (
            fields["title"],
            fields.get("scripture_ref") or "",
            names.get(author_slug, {}).get("name", author_slug),
            (fields.get("preached_on") or "")[:4],
        )
    )
    return hashlib.sha256(blob.encode()).hexdigest()


class SermonShareCardTests(SimpleTestCase):
    """Every sermon must have its Open Graph share card committed.

    Same shape as ``CoverAssetTests``'s raster-twin check, and for the same
    reason: the sermon page points ``og:image`` unconditionally at
    ``/og/sermons/<slug>.png`` because a prerendered page cannot test for a
    file, so the guarantee has to live here. Without it, adding a sermon and
    forgetting to run the generator ships a share preview that 404s — invisible
    until someone forwards the link.

    English only, one card per slug: see ``frontend/scripts/og-card.mjs``.
    """

    def test_every_sermon_has_a_share_card(self):
        missing = sorted(
            r["fields"]["slug"]
            for r in all_rows()
            if r["model"] == "library.sermon"
            and r["fields"].get("language", "en") == "en"
            and not (STATIC_DIR / "og" / "sermons" / f"{r['fields']['slug']}.png").is_file()
        )
        self.assertEqual(
            missing, [],
            "sermon with no og:image share card — run `cd frontend && "
            "npm run og:sermons` and commit frontend/static/og/sermons/<slug>.png",
        )

    def test_every_card_was_drawn_from_the_sermon_it_stands_in_for(self):
        """Existence was never the hard part — staleness was.

        The check above passes on a card from any era. Retitle a sermon, correct
        its passage or fix a preacher's name and the old card keeps shipping,
        seen only by people who are not us — which is exactly how the book twins
        sat a design generation out of date for months.

        `npm run og:sermons` records what each card was drawn from; this
        recomputes the half that lives in the fixture. The other half — which
        emblem the slug resolves to and its drawing — is recomputed by
        `sermonCards.test.ts`, because the catalogue is TypeScript and this side
        cannot read it. Neither sees a change to the generator's own
        composition; only re-running it can.
        """
        manifest_file = STATIC_DIR / "og" / "sermons" / "og-manifest.json"
        self.assertTrue(
            manifest_file.is_file(),
            "frontend/static/og/sermons/og-manifest.json is missing — run "
            "`cd frontend && npm run og:sermons`",
        )
        recorded = json.loads(manifest_file.read_text())["cards"]
        names = authors_by_slug()

        stale, unrecorded = [], []
        for row in sorted(all_rows(), key=lambda r: str(r["fields"].get("slug"))):
            if row["model"] != "library.sermon":
                continue
            fields = row["fields"]
            if fields.get("language", "en") != "en":
                continue
            slug = fields["slug"]
            if slug not in recorded:
                unrecorded.append(slug)
                continue
            if _sermon_content_digest(fields, names) != recorded[slug]["content"]:
                stale.append(slug)

        self.assertEqual(
            unrecorded, [],
            "sermon with no entry in og-manifest.json — run `npm run og:sermons`",
        )
        self.assertEqual(
            stale, [],
            "the sermon changed but its share card did not — a forwarded link "
            "would show the previous title. Run `cd frontend && npm run og:sermons`",
        )

    def test_every_localized_sermon_has_a_fresh_card(self):
        """The locales that opt into their own cards keep the same guarantee.

        `SERMON_OG_LOCALES` (a French exception to the English-only default) draw
        a card per translated sermon at ``/og/sermons/<lang>/<slug>.png``, and the
        reader page points a French sermon's ``og:image`` there. So existence and
        freshness have to hold per language too: every translated sermon in an
        opted-in locale needs a card matching its French title and passage, or a
        forwarded link 404s or shows the English words.

        The opted-in locales are read from the manifest's ``localized`` block,
        which the generator writes from ``SERMON_OG_LOCALES``; ``sermonCards.test.ts``
        pins that block's locale set to the frontend constant, closing the loop
        this side cannot read.
        """
        manifest_file = STATIC_DIR / "og" / "sermons" / "og-manifest.json"
        localized = json.loads(manifest_file.read_text()).get("localized", {})
        names = authors_by_slug()

        sermons_by_lang: dict = {}
        for row in all_rows():
            if row["model"] != "library.sermon":
                continue
            f = row["fields"]
            sermons_by_lang.setdefault(f.get("language", "en"), {})[f["slug"]] = f

        missing_file, unrecorded, stale = [], [], []
        for lang, cards in localized.items():
            fixtures = sermons_by_lang.get(lang, {})
            # Both directions: every translated sermon has a card, and no card
            # outlives the sermon it stood in for.
            for slug in sorted(set(fixtures) | set(cards)):
                if slug not in fixtures or slug not in cards:
                    unrecorded.append(f"{lang}/{slug}")
                    continue
                if not (STATIC_DIR / "og" / "sermons" / lang / f"{slug}.png").is_file():
                    missing_file.append(f"{lang}/{slug}")
                    continue
                if _sermon_content_digest(fixtures[slug], names) != cards[slug]["content"]:
                    stale.append(f"{lang}/{slug}")

        self.assertEqual(
            missing_file, [],
            "localized sermon card missing its PNG — run `cd frontend && "
            "npm run og:sermons` and commit frontend/static/og/sermons/<lang>/<slug>.png",
        )
        self.assertEqual(
            unrecorded, [],
            "a translated sermon and its localized card disagree (one exists "
            "without the other) — run `cd frontend && npm run og:sermons`",
        )
        self.assertEqual(
            stale, [],
            "a translated sermon changed but its localized share card did not — "
            "run `cd frontend && npm run og:sermons`",
        )


class TopicShareCardTests(SimpleTestCase):
    """Every topic must have its Open Graph share card committed and current.

    The topic page points ``og:image`` unconditionally at
    ``/og/topics/<slug>.png`` (one card per slug, English — a prerendered page
    cannot test for a file), so the guarantee lives here. Same two-sided split
    as the sermon cards: this recomputes the strings off ``topic_seed.py`` — the
    side that can read that module — while ``topicCards.test.ts`` recomputes the
    emblem + curated accent and the generator's own composition.
    """

    def _recorded(self):
        manifest_file = STATIC_DIR / "og" / "topics" / "og-manifest.json"
        self.assertTrue(
            manifest_file.is_file(),
            "frontend/static/og/topics/og-manifest.json is missing — run "
            "`cd frontend && npm run og:topics`",
        )
        return json.loads(manifest_file.read_text())["cards"]

    def test_every_topic_has_a_share_card(self):
        from library.topic_seed import TOPICS

        missing = sorted(
            slug
            for slug, *_ in TOPICS
            if not (STATIC_DIR / "og" / "topics" / f"{slug}.png").is_file()
        )
        self.assertEqual(
            missing, [],
            "topic with no og:image share card — run `cd frontend && "
            "npm run og:topics` and commit frontend/static/og/topics/<slug>.png",
        )

    def test_every_card_was_drawn_from_the_topic_it_stands_in_for(self):
        from library.topic_seed import TOPIC_SCRIPTURE, TOPICS

        recorded = self._recorded()
        stale, unrecorded = [], []
        for slug, title, description, _books in sorted(TOPICS, key=lambda t: t[0]):
            if slug not in recorded:
                unrecorded.append(slug)
                continue
            ref, text = TOPIC_SCRIPTURE.get(slug, ("", ""))
            # Mirrors `contentDigest` in generate-topic-og.mjs: the strings the
            # card sets, in the order it joins them.
            blob = "\0".join((title, description, ref, text))
            if hashlib.sha256(blob.encode()).hexdigest() != recorded[slug]["content"]:
                stale.append(slug)

        self.assertEqual(
            unrecorded, [],
            "topic with no entry in og-manifest.json — run `npm run og:topics`",
        )
        self.assertEqual(
            stale, [],
            "the topic's title/description/scripture changed but its share card "
            "did not — a forwarded link would show the previous text. Run "
            "`cd frontend && npm run og:topics`",
        )


class SermonBriefCoverageTests(SimpleTestCase):
    """Every sermon on the shelf should carry its "In brief".

    The sermons shelf lists one sermon per line and prints the brief under each
    (STYLE_GUIDE §5, `.sermon-row`), so a sermon with an empty ``summary``
    renders as a bare title — finished-looking, but useless for deciding whether
    to read or listen, which is the job that page exists to do.

    Two ways the gap opens, and this guard closes both:

    * a NEW English sermon shipped without a brief;
    * a TRANSLATION that drops the brief its English source has. This was a real
      defect, not carelessness — ``translate_sermon`` built the translated row
      without a ``summary`` field at all, so every AI translation silently got
      "" and es/lg/sw ended up with none across the board.

    The allow-lists below are the debt that already existed when the guard was
    added; they are exact, so a new sermon cannot join them by accident — only
    by deliberately editing this file. **They should only ever shrink.**
    """

    # Empty: every English sermon now has a brief. Keep it that way — a new
    # English sermon without one fails the guard rather than joining a list.
    EN_WITHOUT_BRIEF: set[str] = set()

    # Empty: every translated sermon now carries the brief its English source
    # has. Keep it that way — a translation that drops the summary fails the
    # guard rather than joining a list.
    TRANSLATIONS_WITHOUT_BRIEF: set[str] = set()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sermons = [
            r["fields"] for r in all_rows() if r["model"] == "library.sermon"
        ]
        cls.brief = {
            (f["slug"], f.get("language", "en")): bool((f.get("summary") or "").strip())
            for f in cls.sermons
        }

    def test_english_sermons_have_a_brief(self):
        missing = sorted(
            slug
            for (slug, lang), has in self.brief.items()
            if lang == "en" and not has and slug not in self.EN_WITHOUT_BRIEF
        )
        self.assertEqual(
            missing, [],
            "English sermon with no 'summary' — the shelf will show a bare title. "
            "Write the brief (300-410 chars, one paragraph, in the voice of the "
            "existing ones) into the sermon's fixture file.",
        )

    def test_translations_keep_the_brief(self):
        missing = sorted(
            f"{slug}.{lang}"
            for (slug, lang), has in self.brief.items()
            if lang != "en"
            and not has
            and self.brief.get((slug, "en"))  # nothing to carry over if EN has none
            and f"{slug}.{lang}" not in self.TRANSLATIONS_WITHOUT_BRIEF
        )
        self.assertEqual(
            missing, [],
            "translated sermon dropped the brief its English source has. "
            "translate_sermon translates 'summary' — re-run it with --force, or "
            "write the brief by hand if the row was made another way.",
        )

    def test_allow_lists_have_no_stale_entries(self):
        """A brief that has since been written must leave the list.

        Without this the lists would quietly stop shrinking: an entry whose gap
        was filled would sit there forever, still licensing a future regression
        on that exact slug.
        """
        stale_en = sorted(
            s for s in self.EN_WITHOUT_BRIEF if self.brief.get((s, "en"))
        )
        self.assertEqual(
            stale_en, [], "EN_WITHOUT_BRIEF lists a sermon that now HAS a brief — remove it"
        )
        stale_tr = sorted(
            k for k in self.TRANSLATIONS_WITHOUT_BRIEF
            if self.brief.get((k.rsplit(".", 1)[0], k.rsplit(".", 1)[1]))
        )
        self.assertEqual(
            stale_tr, [],
            "TRANSLATIONS_WITHOUT_BRIEF lists a row that now HAS a brief — remove it",
        )


class PlanTranslationCoverageTests(SimpleTestCase):
    """Every plan row a deploy could CREATE must have prose in its language.

    `seed_plans` creates a Plan per language in which the source books are
    published, and takes its title/description from
    `data/plan_translations/<language>.json`. That lookup used to fall back to the
    English tuple, and nothing failed when it did: the row was valid, the page
    rendered, and it read "A Month in the Inner Chamber" to a Swahili reader,
    invisible until somebody opened that locale. `seed_plans` now refuses
    instead, so the failure has moved rather than gone — the plan is simply
    ABSENT from that language, which is quieter but still not what anyone
    wanted. This test is what makes it neither.

    The trigger is a BOOK, not a plan. Shipping `the-inner-chamber` in Swahili
    published a Swahili plan nobody had written prose for, and the plan job for
    it sat in the queue looking unrelated. So this cannot be a habit; it has to
    be a check. Three locales had drifted by the time anyone looked (es, sw, uk
    — all on the same plan).

    Fixture-only, so it runs without a database: which books exist per language
    is exactly what the committed content files say.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.published: dict[str, set[str]] = {}
        for row in all_rows():
            if row["model"] != "library.book":
                continue
            f = row["fields"]
            if f.get("is_published", True):
                cls.published.setdefault(f.get("language", "en"), set()).add(f["slug"])

    def test_every_creatable_plan_row_has_its_own_prose(self):
        from library.management.commands.seed_plans import (
            CURATED_PLANS,
            LAUNCH_PLANS,
        )
        from library.plan_translations import plan_translations

        # (plan slug, the books it needs) for both plan kinds.
        needs = [(p[0], [p[1]]) for p in LAUNCH_PLANS]
        needs += [(p[0], list(p[3])) for p in CURATED_PLANS]

        missing = sorted(
            f"{language}/{slug}"
            for slug, books in needs
            for language, have in self.published.items()
            if language != "en"
            and all(b in have for b in books)
            and slug not in plan_translations().get(language, {})
        )
        self.assertEqual(
            missing,
            [],
            "Every source book of these plans is published in these languages, "
            "so the plan belongs there — but data/plan_translations/<language>.json "
            "has no entry, so "
            "seed_plans will skip it and the language gets no plan at all. Add "
            "the prose to that file",
        )


class SettledBodyIdempotenceTests(SimpleTestCase):
    """The deploy converges only because the corrections are a fixed point.

    `manage.py release` corrects every stored body and then runs the seeds,
    which compare the fixture's SETTLED form against the DB. That loop is
    stable only while `settled(settled(x)) == settled(x)`: a correction whose
    output re-matches its own input would be re-applied on every deploy, the
    seed would see a difference every deploy, and the pair would churn forever
    — the exact failure the settled form was introduced to end, reintroduced
    one rung down where no seed test would see it.

    Cheap to get wrong: a replacement pair whose replacement still contains the
    string it replaces ("Yohana 10" -> "Yohana 10:1") does it. So does a new
    rule-shaped correction. This asserts the property over the whole corpus, so
    the entry that breaks it fails the build that adds it.
    """

    def test_every_fixture_body_is_a_fixed_point(self):
        from library.corrections import settled_chapter_body, settled_sermon_body

        for row in all_rows():
            f = row["fields"]
            body = f.get("body_html") or ""
            if row["model"] == "library.chapter":
                slug = f["book"][0]
                once = settled_chapter_body(slug, f["order"], body)
                twice = settled_chapter_body(slug, f["order"], once)
            elif row["model"] == "library.sermon":
                slug = f["slug"]
                once = settled_sermon_body(slug, body)
                twice = settled_sermon_body(slug, once)
            else:
                continue
            with self.subTest(model=row["model"], slug=slug):
                self.assertEqual(twice, once)


class BodyTextDerivationTests(SimpleTestCase):
    """`body_text` must be exactly what `save()` would derive from `body_html`.

    It is a DERIVED column — `Chapter.save()` and `Sermon.save()` both set it to
    `html_to_text(body_html)` — and it is what full-text search indexes and what
    snippets are rendered from. The fixture is the one place it can drift:
    `loaddata` writes it verbatim (it never calls `save()`), and
    `backfill_body_text` only fills an EMPTY one, so a value that is present but
    wrong self-corrects nowhere — not in a fresh build, not on a deploy.

    490 rows across 58 files had drifted, in four ways and none of them visible
    on a page: quote marks left behind by a sweep that converted `body_html`
    only; `man&#x27;s` where the rule gives `man's`; `الخيرات. »` for
    `الخيرات.»`, from an older derivation that spaced every tag rather than the
    block-level ones; and 36 chapters of `the-inner-chamber.lg` with no
    `body_text` at all.

    Nothing was watching, which is why it accumulated. This is the watch.
    """

    def test_every_body_text_is_derived_from_its_body_html(self):
        stale = []
        for path in ordered_fixture_paths():
            if path.name in {"authors.json", "series.json", "plans.json"}:
                continue
            for row in json.loads(path.read_text()):
                fields = row.get("fields", {})
                body_html = fields.get("body_html")
                # `is None`, not falsy: a row whose body_text is "" is precisely
                # one of the rows this exists to catch.
                if not body_html or fields.get("body_text") is None:
                    continue
                if html_to_text(body_html) != fields["body_text"]:
                    stale.append(f"{path.name} #{fields.get('order', '-')}")
        self.assertEqual(
            stale[:20],
            [],
            f"{len(stale)} rows carry a body_text their own body_html no longer "
            f"derives — search indexes one thing and the page shows another. Run "
            f"`manage.py rederive_body_text --write`.",
        )


class RestatedChapterHeadingTests(SimpleTestCase):
    """No stored body may open by repeating the title printed above it.

    The reader renders the chapter title above the body, so a body that leads
    with its own title prints it twice — `all-of-grace` chapter 1 is titled "To
    You" and its prose began "<h2>TO YOU</h2>". Migration 0092 has the census
    and the judgement calls; this is the watch. The importer's rule reaches no
    fixture edited by hand, so a restated heading committed here would ship to
    every edition's reader.

    A translated heading that PARAPHRASES its title rather than repeating it
    reads as clean here and is not this test's to catch — 0092 decides those by
    their English twin, and `tests_translation_markup` is what notices when a
    translation stops matching the English block for block.
    """

    def test_no_body_opens_by_restating_its_own_title(self):
        restated = []
        for path, rows in files_by_path().items():
            for row in rows:
                fields = row.get("fields", {})
                body_html, title = fields.get("body_html"), fields.get("title")
                if not body_html or not title:
                    continue
                if strip_restated_heading(body_html, title) != body_html:
                    restated.append(
                        f"{path.name} #{fields.get('order', '-')}: {title!r}"
                    )
        self.assertEqual(
            restated[:20],
            [],
            f"{len(restated)} body(ies) open with a heading that only repeats "
            f"the title the reader already prints above them — run "
            f"`uv run python scripts/strip_restated_headings.py --write`, "
            f"which applies the same rule and re-derives `body_text` and "
            f"`word_count` with it.",
        )


class WordCountDerivationTests(SimpleTestCase):
    """`word_count` must be exactly what `text.word_count` gives its `body_html`.

    It is a DERIVED column — `Chapter.save()`/`Sermon.save()` derive it, and so
    does every importer — and the reader spends it: the per-chapter reading-time
    estimate in the TOC drawer, the length sort on the shelf, the word totals
    under a book and under a reading plan.

    A fixture row is the one place that keeper cannot reach: `loaddata` never
    calls `save()`, so a committed count is simply whatever was last written
    into it. `backfill_word_count` deliberately fills only rows sitting at zero,
    so a count that is present but WRONG self-corrects nowhere — not in a fresh
    build, not on a deploy, not on the next prose repair. That is the gap this
    gate stands in.

    381 rows across 83 files had drifted, in two classes and neither of them
    visible on a page: 237 English rows whose count still described the
    `body_html` as it stood before a later prose repair (a closed line-break
    hyphen fuses two half-words and drops the count by one), and 144 translated
    rows — every non-English one — counted with `html_to_text`, the derivation
    `body_text` uses, which joins across inline tags where this one spaces them.

    Nothing was watching, which is why it accumulated. This is the watch — and
    it stays useful now that #1197 keeps the DATABASE in step, because a fresh
    build starts from this file rather than from a database.
    """

    def test_every_word_count_is_derived_from_its_body_html(self):
        stale = []
        for path in ordered_fixture_paths():
            if path.name in {"authors.json", "series.json", "plans.json"}:
                continue
            for row in json.loads(path.read_text()):
                fields = row.get("fields", {})
                body_html = fields.get("body_html")
                # `is None`, not falsy: a row whose word_count is 0 is precisely
                # one of the rows this exists to catch.
                if not body_html or fields.get("word_count") is None:
                    continue
                if word_count(body_html) != fields["word_count"]:
                    stale.append(f"{path.name} #{fields.get('order', '-')}")
        self.assertEqual(
            stale[:20],
            [],
            f"{len(stale)} rows carry a word_count their own body_html does not "
            f"give — the reading time, the length sort and the plan totals all "
            f"quote it. Run `manage.py rederive_word_count --write`.",
        )


class ChapterTitleNumberingTests(SimpleTestCase):
    """No stored title may carry the number the reader is about to add.

    The reader renders a chapter as `{order}. {title}` — TocDrawer,
    SearchDrawer and the notebook all do — so a title stored as "1. The God of
    Our Salvation" reached the page as "3. 1. The God of Our Salvation", the
    two numbers disagreeing because front matter occupies the first orders.
    245 rows were in that state: `waiting-on-god` in six languages, and the 59
    chapters of `selected-sermons-whitefield`, styled "01. ", "02. " …

    `clean_title` strips the prefix on import now, and migration 0090 stripped
    the rows already in the database. This is what keeps them from coming back:
    the importer's rule is not applied to a fixture edited by hand, so a
    numbered title committed here would ship straight to the reader.

    Every title in the corpus, not just chapters — a numeral in front of a book
    or sermon name is the same source artefact, and today there are none.

    One case this must NOT be obeyed blindly: `_NUMBERED_BOOKS` spells the
    numbered Bible books in English only, so a Spanish "1. Juan" or a Hindi
    "१. यूहन्ना" reads to the rule as a numbering prefix rather than a name.
    Nothing in the corpus is in that state, but a hand-written title that is
    would fail here, and stripping it would leave one chapter titled "Juan" —
    hence the second half of the message rather than a bare instruction.
    """

    def test_no_title_carries_a_redundant_numbering_prefix(self):
        numbered = []
        for path, rows in files_by_path().items():
            for row in rows:
                fields = row.get("fields", {})
                title = fields.get("title")
                if not title:
                    continue
                if strip_numbering_prefix(title) != title:
                    numbered.append(
                        f"{path.name} #{fields.get('order', '-')}: {title!r}"
                    )
        self.assertEqual(
            numbered[:20],
            [],
            f"{len(numbered)} title(s) begin with their own number, which the "
            f"reader prepends again — pass them through "
            f"`library.ingest.strip_numbering_prefix`. Unless the numeral is "
            f"part of a Bible book's NAME in a language `_NUMBERED_BOOKS` does "
            f"not spell ('1. Juan'), in which case widen that guard instead.",
        )


class QuoteStyleTests(SimpleTestCase):
    """No single work may mix straight and curly quotation marks.

    Quote style in the corpus is per-FILE: a work mirrors whichever style its
    own source used, and translations mirror their English. That rule is right,
    but it had no answer for the 23 of 94 English files that were internally
    MIXED — `talks-to-the-farmer` alone showed the reader 264 straight marks and
    1,132 curly ones, in the same book. Those 44 files (English and translated)
    were normalised to curly, which is 76% of the corpus already.

    This guard is deliberately about CONSISTENCY, not about curly. A work that
    is wholly straight-quoted reads fine and is left alone; what a reader must
    never meet is both styles inside one book.
    """

    def test_no_work_mixes_straight_and_curly_quotes(self):
        offenders = []
        for name, work in work_bodies():
            # `library.quote_marks` owns the counting rule, and the fixture sweep and
            # migration 0084 read it from there too. It used to be re-derived
            # here, which is the one place a drift would go unnoticed — this is
            # the guard, so nothing guards it. Widening it to count guillemets
            # is what surfaced four invisible es works AND a genuine defect the
            # narrow count could not see: susanna-wesley-clarke.en, wholly
            # straight-quoted, had ten OCR-damaged guillemets in it, two of them
            # corrupted letters.
            straight, curly = mark_counts(work)
            if straight and curly:
                offenders.append(f"{name}: {straight} straight, {curly} curly")
        self.assertEqual(
            offenders,
            [],
            "These works show the reader both quote styles. Run "
            "`uv run python scripts/normalize_quotes.py` to convert the straight "
            "marks, then re-read the diff: the opening/closing decision is made "
            "from context, and a source that sets a space inside its marks or "
            "leaves a quotation open across a paragraph can still fool it.",
        )

    def test_no_quotation_closes_with_the_wrong_mark(self):
        """A quotation opened curly must close curly, and close with a CLOSER.

        The counting test above could not see the 390 the 2026-09-11 sweep
        repaired; `quote_marks.mispaired_marks` says why, and owns the rule.
        """
        offenders = [
            f"{name}: …{excerpt}…"
            for name, work in work_bodies()
            for excerpt in mispaired_marks(work)
        ]
        self.assertEqual(
            offenders,
            [],
            "These quotations close with the wrong mark. Repair each with a "
            "`corrections.BODY_CORRECTIONS` pair (stored text is re-corrected on "
            "every deploy) and settle the fixture; see the 2026-09-11 block at the "
            "end of corrections.py.",
        )


_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
# C:V1-V2, optionally followed by ":V2b" for the cross-chapter form. The
# cross-chapter separator takes NO surrounding whitespace: with it, a citation
# list like "(Romans 8:1-4. 1 Corinthians 2:14)" reads as chapter 8 to chapter 4
# and a correct reference fails the gate.
_RANGE = re.compile(
    r"([0-9٠-٩]{1,3})\s*[:.]\s*([0-9٠-٩]{1,3})"
    r"\s*[-‐‑‒–—]\s*([0-9٠-٩]{1,3})"
    r"(?:[:.]([0-9٠-٩]{1,3}))?"
)
_TAG = re.compile(r"<[^>]+>")
# Named HTML entity refs (`&amp;`, `&quot;`), not a bare `&` — Q&A ships as plain
# text, so an entity would render literally. Shared by the Q&A shape guards.
_ENTITY = re.compile(r"&[a-zA-Z][a-zA-Z0-9]+;")
# A filename that plausibly names a language ("es", "en-modern") — shared by the
# per-language data-file gates; a shape check, deliberately not a registry lookup
# (the registry is DB-owned so an admin can add a language without a deploy).
_LANG_CODE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$")


def _digits(group: str | None) -> int | None:
    return None if group is None else int(group.translate(_ARABIC_INDIC))


@lru_cache(maxsize=1)
def descending() -> tuple[tuple[str, str, str], ...]:
    """(file, citation, surrounding text) for every verse range that runs back.

    Scans the whole body rather than parenthesised citations only. An earlier
    draft looked inside parentheses, on the theory that a citation is
    parenthesised — but 37% of the Arabic ranges in this corpus are not, and
    four real English defects sat in the unscanned remainder
    ("John 16:12-1", "Romans 4:19—2 1"). Across the whole corpus the wider scan
    finds seven ranges and none of them is a false positive: "C:V" is a
    distinctive enough shape in devotional prose that it needs no fence.

    Cached: both tests in ``CitationRangeTests`` want the same answer, and
    re-deriving it re-scans every body in the corpus. Same reasoning as
    ``all_rows`` above.
    """
    out: list[tuple[str, str, str]] = []
    for path, rows in rows_by_file().items():
        if path.name in {"authors.json", "series.json", "plans.json"}:
            continue
        for row in rows:
            html = row["fields"].get("body_html") or ""
            if not html:
                continue
            text = _TAG.sub(" ", html)
            for m in _RANGE.finditer(text):
                chapter, first, second, across = (_digits(g) for g in m.groups())
                # Cross-chapter (C1:V1-C2:V2): the CHAPTER must ascend, and the
                # verse legitimately restarts lower (2:11-3:1).
                ok = second > chapter if across is not None else second > first
                if not ok:
                    context = " ".join(text[max(0, m.start() - 45):m.end() + 15].split())
                    out.append((path.name, m.group(0), context))
    return tuple(out)


class CitationRangeTests(SimpleTestCase):
    """A verse range must ascend — the one automatic handle on mangled citations.

    Bidirectional text reorders digit groups silently. A citation that entered
    as ``Psalm 20:7-8`` can be stored as ``(مزمور 7:20-8)``: the chapter and the
    first verse have swapped, the QUOTED VERSE beside it is still correct, and
    the reference reads as perfectly plausible Arabic. No scripture check sees
    it, because scripture checks compare wording — and the wording is right.

    What is left is an arithmetic invariant that holds in every language and
    every script: a range runs forwards. ``C:V1-V2`` needs ``V2 > V1``, and the
    cross-chapter form ``C1:V1-C2:V2`` needs ``C2 > C1``. Transposition breaks
    it about half the time, which is the entire detection budget available for
    this class of defect — a transposed SINGLE-verse reference stays invisible
    and still needs a reviewer reading citations against the English.

    Arabic-Indic digits are normalised before comparing, because the corpus is
    not uniform: the shipped Arabic books settle Western-to-Arabic-Indic 673 to
    3, and a check that only understood Western digits would skip the language
    the defect actually appears in.

    ``KNOWN_CITATIONS`` pins the cases that are NOT defects of this kind, each
    with its reason. It fails when an entry stops matching, so it can only
    shrink. Fixture-only, no DB.
    """

    # (fixture file, the citation text as stored) that this invariant flags and
    # that this PR does not repair. Keep the reason on every entry.
    #
    # Two are period convention rather than defects: Bunyan's printer elides the
    # tens digit, so "12:22-4" is Hebrews 12:22-24 and "15.21-8" is Matt.
    # 15:21-28 in the dot style he also used. english-qa's governing rule is
    # that period style is the text, not an error in it. Whoever first
    # translates `grace-abounding` will render these and will need entries for
    # that file too — that is the check working, not a nuisance.
    KNOWN_CITATIONS: set[tuple[str, str]] = {
        ("grace-abounding.en.json", "12:22-4"),
        ("grace-abounding.en.json", "15.21-8"),
        # The remaining five are REAL extraction defects in the English source,
        # reported and not repaired here: a body repair belongs in
        # corrections.BODY_CORRECTIONS via the english-qa channel, which reaches
        # production on the next deploy and wants its own review. None has
        # propagated — every one is English-only. See this PR's description.
        #
        # "(1 Peter 1:2-2, 1 Thessalonians 2:13)" beside the quoted phrase
        # "sanctification of the Spirit", which is verbatim 1 Peter 1:2 and
        # 2 Thessalonians 2:13; 1 Thessalonians 2:13 is about receiving the word
        # of God and does not contain the phrase. The extractor appears to have
        # welded the "2" of "2 Thessalonians" onto the previous reference.
        ("the-person-and-work-of-the-holy-spirit.en.json", "1:2-2"),
        # "John 16:12-1" — a truncated second verse.
        ("the-person-and-work-of-the-holy-spirit.en.json", "16:12-1"),
        # "Mark 8:32-25", in the list "Matthew 10:34-39; Mark 8:32-25; Luke
        # 17:32-34". Plainly wrong and NOT plainly repairable — 8:32-35 and
        # 8:34-35 are both plausible — so it needs the English source, not a
        # guess. english-qa: repair only what is unambiguous.
        ("the-normal-christian-life.en.json", "8:32-25"),
    }

    def test_every_verse_range_ascends(self):
        new = [
            (f, cite, ctx)
            for f, cite, ctx in descending()
            if (f, cite) not in self.KNOWN_CITATIONS
        ]
        detail = "\n".join(f"  {f} — …{ctx}…" for f, _, ctx in sorted(new))
        self.assertFalse(
            new,
            "These verse ranges run backwards:\n"
            f"{detail}\n\n"
            "In a right-to-left language this is usually a TRANSPOSITION — the "
            "chapter and first verse swapped when Western numerals were embedded "
            "in RTL text — and the verse quoted beside it is typically correct, "
            "so only the reference needs repairing. Check it against the English "
            "edition. If the range is right and the source simply writes it this "
            "way, add it to KNOWN_CITATIONS with the reason.",
        )

    def test_known_citations_contains_no_stale_entries(self):
        stale = sorted(
            self.KNOWN_CITATIONS - {(f, cite) for f, cite, _ in descending()}
        )
        self.assertFalse(
            stale,
            "These entries no longer match anything — delete them from "
            f"KNOWN_CITATIONS so the list can only shrink: {stale}",
        )


class PlanTranslationFileTests(SimpleTestCase):
    """The per-language plan prose files are well-formed and describe real plans.

    Splitting ``PLAN_TRANSLATIONS`` into ``data/plan_translations/<lang>.json``
    removed the conflict between plan jobs in different languages, but it also
    removed Python's own checking: a typo in a dict literal is a syntax error,
    while a typo in JSON is a file that loads fine and quietly ships nothing.
    These are the checks the language of the file no longer performs for us.

    The slug check is the one that matters most. A plan slug that matches no
    definition is prose nobody will ever see — ``_prose`` looks entries up BY
    the slugs in LAUNCH_PLANS/CURATED_PLANS, so a misspelt key is not an error,
    it is silence, and the language then falls back to no plan at all.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.plan_translations import raw_plan_translations

        cls.raw = raw_plan_translations()

    def test_every_entry_has_title_and_description(self):
        bad = [
            f"{lang}.json:{slug} missing {field}"
            for lang, entries in self.raw.items()
            for slug, entry in entries.items()
            for field in ("title", "description")
            if not (entry.get(field) or "").strip()
        ]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_notes_are_lists_of_paragraphs(self):
        bad = [
            f"{lang}.json:{slug} note is {type(entry['note']).__name__}, want a list of strings"
            for lang, entries in self.raw.items()
            for slug, entry in entries.items()
            if "note" in entry
            and not (
                isinstance(entry["note"], list)
                and all(isinstance(p, str) and p.strip() for p in entry["note"])
            )
        ]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_no_unknown_fields(self):
        allowed = {"title", "description", "note"}
        bad = [
            f"{lang}.json:{slug} has unknown field(s) {sorted(set(entry) - allowed)}"
            for lang, entries in self.raw.items()
            for slug, entry in entries.items()
            if set(entry) - allowed
        ]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_every_slug_names_a_real_plan(self):
        from library.management.commands.seed_plans import CURATED_PLANS, LAUNCH_PLANS

        known = {p[0] for p in LAUNCH_PLANS} | {p[0] for p in CURATED_PLANS}
        bad = [
            f"{lang}.json:{slug}"
            for lang, entries in self.raw.items()
            for slug in entries
            if slug not in known
        ]
        self.assertEqual(
            bad,
            [],
            "These entries name no plan in LAUNCH_PLANS or CURATED_PLANS, so "
            "seed_plans will never look them up and the prose is dead:\n  "
            + "\n  ".join(bad),
        )

    def test_no_english_file(self):
        """English prose lives in the plan definitions, not here.

        ``_prose`` returns the LAUNCH_PLANS/CURATED_PLANS tuple for "en" and any
        ``en-`` variant before it ever reads these files, so an ``en.json`` would
        be read by nothing and edited by someone expecting it to work — the same
        silent no-op the slug check above exists to prevent, one level up.
        """
        bad = sorted(lang for lang in self.raw if lang == "en" or lang.startswith("en-"))
        self.assertEqual(
            bad,
            [],
            f"{bad}: English prose belongs in LAUNCH_PLANS/CURATED_PLANS in "
            "seed_plans.py. _prose never reads these files for English.",
        )

    def test_language_files_are_named_like_language_codes(self):
        """A filename typo is prose that can never be found.

        Deliberately a SHAPE check, not a registry lookup. The Language registry
        lives in the DB precisely so an admin can add a language without a
        deploy, so a file may legitimately name a language this checkout has
        never heard of — validating against `language_seed` would reject exactly
        the case the registry exists to allow. What is always wrong is a name
        that is not a language code at all (`spanish.json`, `es-.json`).
        """
        bad = sorted(lang for lang in self.raw if not _LANG_CODE.fullmatch(lang))
        self.assertEqual(
            bad,
            [],
            f"Not language codes: {bad}. seed_plans looks these up by the "
            "content language of a Book row, so a file it cannot match is dead.",
        )


class TopicTranslationFileTests(SimpleTestCase):
    """The per-language topic files are well-formed and describe real shelves.

    Same reasoning as ``PlanTranslationFileTests`` above — JSON does not fail
    the way a dict literal does — with two additions the stakes demand. Topic
    prose has NO English fallback, so a lost entry is a shelf HIDDEN from that
    language (and its page 404s there); and a shelf's ``scripture`` must be the
    trusted Bible's wording fetched via Take Root, so its shape is pinned here
    while its wording stays a review-time question.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.topic_translations import raw_topic_translations

        cls.raw = {
            lang: {slug: e for slug, e in payload.items() if not slug.startswith("_")}
            for lang, payload in raw_topic_translations().items()
        }
        cls.meta = {
            lang: {slug: e for slug, e in payload.items() if slug.startswith("_")}
            for lang, payload in raw_topic_translations().items()
        }

    def test_every_entry_is_well_formed(self):
        allowed = {
            "title",
            "description",
            "seo_title",
            "meta_description",
            "scripture",
            "note",
        }
        bad = []
        for lang, entries in self.raw.items():
            for slug, e in entries.items():
                where = f"{lang}.json:{slug}"
                for field in ("title", "description"):
                    if not (e.get(field) or "").strip():
                        bad.append(f"{where} missing {field}")
                if set(e) - allowed:
                    bad.append(f"{where} unknown field(s) {sorted(set(e) - allowed)}")
                # seo_title / meta_description are optional but come as a pair:
                # a title with no blurb (or vice versa) is a half-written
                # override — topic_seo() reads both, so both must be present and
                # non-empty when either is.
                if (("seo_title" in e) or ("meta_description" in e)) and (
                    not (e.get("seo_title") or "").strip()
                    or not (e.get("meta_description") or "").strip()
                ):
                    bad.append(
                        f"{where} seo_title and meta_description must be a "
                        "non-empty pair"
                    )
                sc = e.get("scripture")
                if sc is not None and (
                    not isinstance(sc, dict)
                    or not (sc.get("reference") or "").strip()
                    or not (sc.get("text") or "").strip()
                    or set(sc) - {"reference", "text"}
                ):
                    bad.append(f"{where} malformed scripture (want reference + text)")
                note = e.get("note")
                if note is not None and not (
                    isinstance(note, list)
                    and all(isinstance(x, str) and x.strip() for x in note)
                ):
                    bad.append(f"{where} note must be a list of non-empty strings")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_language_level_keys_are_only_note(self):
        bad = [
            f"{lang}.json: {sorted(set(meta) - {'_note'})}"
            for lang, meta in self.meta.items()
            if set(meta) - {"_note"}
        ]
        bad += [
            f"{lang}.json: _note must be a list of non-empty strings"
            for lang, meta in self.meta.items()
            if "_note" in meta
            and not (
                isinstance(meta["_note"], list)
                and all(isinstance(x, str) and x.strip() for x in meta["_note"])
            )
        ]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_every_slug_names_a_real_topic_and_covers_all_of_them(self):
        """Both directions: no dead prose, and no hidden shelf.

        A slug naming no topic is prose nothing reads (the seed iterates the
        TOPICS definitions and looks entries up by their slugs). A topic
        missing from a language's file is a shelf HIDDEN from that language —
        no English fallback — which is why ``seed_topics`` carries a
        full-coverage test too; this one runs without a database and points at
        the file.
        """
        from library.management.commands.seed_topics import TOPICS
        from library.topic_seed import TRANSLATION_PENDING

        known = {t[0] for t in TOPICS}
        # A pending shelf ships live in English and is filled per-language by the
        # translation queue, so its absence is allowed; every other shelf must be
        # covered. (A pending slug that names no real topic is caught below.)
        required = known - TRANSLATION_PENDING
        dead = sorted(
            f"{lang}.json:{slug}"
            for lang, entries in self.raw.items()
            for slug in entries
            if slug not in known
        )
        hidden = sorted(
            f"{lang}.json missing {slug}"
            for lang, entries in self.raw.items()
            for slug in required - set(entries)
        )
        self.assertEqual(dead, [], f"Prose for no topic: {dead}")
        self.assertEqual(
            hidden,
            [],
            "Topic prose has no English fallback — these shelves would be "
            f"HIDDEN from their language: {hidden}",
        )
        stale = sorted(TRANSLATION_PENDING - known)
        self.assertEqual(
            stale,
            [],
            "TRANSLATION_PENDING names topics that don't exist — a stale entry "
            f"silently exempts a real coverage gap: {stale}",
        )

    def test_no_english_file_and_codes_look_like_languages(self):
        bad = sorted(
            lang
            for lang in self.raw
            if lang == "en" or lang.startswith("en-") or not _LANG_CODE.fullmatch(lang)
        )
        self.assertEqual(
            bad,
            [],
            f"{bad}: English shelf prose lives on the Topic row itself, and a "
            "file that is not a language code is prose the seed can never match.",
        )


class ContentSourceCoverageTests(SimpleTestCase):
    """The reader is a PRERENDERED site, so a source of its content is only as
    live as the thing that notices the source changed.

    Three lists have to agree, and they live in three languages: the roots in
    ``content_sources.json``, the digest built from them (served on
    ``/api/health/`` and recomputed by the web build's prebuild gate), and
    render.yaml's ``buildFilter``, which decides whether a commit rebuilds the
    reader at all. A root missing from the filter means content ships to the API
    and the pages that render it never rebuild — silently, until some unrelated
    commit triggers a build. That is exactly what happened when plan and topic
    prose moved out of ``seed_plans.py`` into ``data/``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.render_yaml = (cls.repo_root / "render.yaml").read_text()
        cls.roots = json.loads(
            (Path(__file__).resolve().parent / "content_sources.json").read_text()
        )["roots"]

    def test_every_declared_root_exists(self):
        # A directory OR a single file: the two seed modules are named
        # individually, because a `/**` over a Python package sweeps in
        # __pycache__ and the API image and the web build would then digest the
        # same content differently.
        for root in self.roots:
            with self.subTest(root=root):
                self.assertTrue(
                    (self.repo_root / "backend" / root).exists(),
                    f"content_sources.json names {root}, which is not there. "
                    "A root that doesn't exist digests to nothing, so the gate "
                    "silently stops covering whatever used to live there.",
                )

    def test_build_filter_covers_every_root(self):
        # The filter is what makes a content commit rebuild the reader at all.
        for root in self.roots:
            with self.subTest(root=root):
                # assertTrue, not assertIn: assertIn would print the whole of
                # render.yaml (30 KB) into the failure.
                named = f"- backend/{root}/**" if not root.endswith(".py") else f"- backend/{root}"
                self.assertTrue(
                    named in self.render_yaml,
                    f"backend/{root} holds reader content but render.yaml's "
                    "buildFilter doesn't name it, so changing it deploys the API "
                    "and leaves the prerendered pages on the previous prose.",
                )

    def test_every_module_the_serializers_reach_is_classified(self):
        """A NEW content-bearing module cannot join the graph unnoticed.

        The two tests above pin that three lists AGREE. Nothing pins that they
        are COMPLETE, and completeness is what actually failed: `curated_art.py`
        began feeding `artwork_credit` on 2026-08-22, was declared nowhere, and
        so `content_version` sat still while what the API returned changed. The
        prebuild gate matched on its first poll and #1150 prerendered six of
        twelve pages with no credit at all. Every other gate was green — they
        were all asking whether the declared list was self-consistent, and it
        was.

        So this asks the other question: is every module the serializers can
        reach either a declared root or explicitly exempt? The serializers are
        the seed because they are what renders every field a prerendered page
        shows. It is a REACHABILITY check, deliberately not a per-commit one —
        an import graph cannot tell a changed SQL query from a changed string,
        and a gate that rebuilt the reader for every `select_related` would be
        ignored within a month. It fails only when the SHAPE of the graph
        changes, which is exactly when a human should decide which list the new
        module belongs in.

        What it does not catch: prose added INSIDE an already-exempt module.
        The graph does not move, so this stays green. Closing that would take a
        post-deploy differential against the live API, which is a different
        piece of work with a different cost.
        """
        import ast

        lib = Path(__file__).resolve().parent

        def module_file(dotted):
            path = lib / (dotted.removeprefix("library.").replace(".", "/") + ".py")
            return path if path.is_file() else None

        def imported_by(path):
            """`library.*` modules one file imports, absolute or relative."""
            found = set()
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    if node.level == 1:  # `from .x import y` / `from . import x`
                        if node.module:
                            found.add(f"library.{node.module}")
                        else:
                            found.update(f"library.{a.name}" for a in node.names)
                    elif not node.level and node.module and node.module.startswith("library"):
                        found.add(node.module)
                elif isinstance(node, ast.Import):
                    found.update(a.name for a in node.names if a.name.startswith("library"))
            return found

        reachable, pending = set(), ["library.serializers"]
        while pending:
            dotted = pending.pop()
            if dotted in reachable:
                continue
            reachable.add(dotted)
            path = module_file(dotted)
            if path:
                pending.extend(imported_by(path))

        declared = {r for r in self.roots if r.endswith(".py")}
        sources = json.loads(
            (Path(__file__).resolve().parent / "content_sources.json").read_text()
        )
        exempt = set(sources.get("reader_exempt", {}))
        unclassified = sorted(
            f"library/{d.removeprefix('library.').replace('.', '/')}.py"
            for d in reachable
            if module_file(d) is not None
        )
        unclassified = [u for u in unclassified if u not in declared and u not in exempt]
        self.assertEqual(
            unclassified,
            [],
            "a module the serializers reach is neither a content root nor "
            "exempt, so nothing knows whether changing it stales a prerendered "
            "page. Add it to content_sources.json's `roots` (and render.yaml's "
            "buildFilter) if it carries reader prose, or to `reader_exempt` "
            "with the reason it does not.",
        )

    def test_every_exempt_module_gives_a_reason(self):
        """An exemption is a claim, and an unexplained one is just a silence.

        Empty strings would let the gate above be satisfied by listing every
        module — which is how a check gets neutralised without anyone deleting
        it. The reason is also what a reviewer reads when deciding whether the
        claim is still true.
        """
        sources = json.loads(
            (Path(__file__).resolve().parent / "content_sources.json").read_text()
        )
        exempt = sources.get("reader_exempt", {})
        self.assertEqual(
            sorted(m for m, why in exempt.items() if not (why or "").strip()),
            [],
            "an exempt module with no reason recorded",
        )
        # And nothing may be in both lists: the two make opposite claims about
        # whether a change there reaches a reader.
        self.assertEqual(
            sorted(set(exempt) & set(self.roots)),
            [],
            "a module is both a content root and reader-exempt",
        )

    def test_the_build_filter_names_no_undeclared_backend_path(self):
        """The other direction, which matters as much.

        A buildFilter path that is NOT a digest root rebuilds the reader on
        commits the gate knows nothing about — so the build starts, finds the
        API's content_version already matching, and prerenders immediately
        against an API that is still mid-deploy. That is the stale-prerender
        race the gate exists to prevent, reintroduced silently. render.yaml,
        backend/CLAUDE.md and DEPLOYMENT.md all promise these agree; this is the
        half that makes the promise true in both directions.
        """
        in_filter = re.findall(r"^\s*- (backend/\S+?)(?:/\*\*)?$", self.render_yaml, re.M)
        self.assertTrue(in_filter, "no backend paths found in render.yaml's buildFilter")
        declared = {f"backend/{r}" for r in self.roots}
        self.assertEqual(
            sorted(set(in_filter) - declared),
            [],
            "render.yaml's buildFilter rebuilds the reader for paths that are not "
            "content roots, so the prebuild gate cannot tell whether the API has "
            "caught up — add them to content_sources.json or drop them.",
        )

    def test_a_file_root_moves_the_digest_when_its_contents_change(self):
        """The whole point of naming the seed modules, in one assertion.

        Editing a topic's book list, a plan's description or a topic's epigraph
        has to rebuild the reader — those strings are prerendered onto
        /topics/<slug>/ and /plans/<slug>/. While they lived inside the seed
        COMMANDS nothing noticed: the API redeployed and the pages kept the
        previous prose until an unrelated commit happened to trigger a build.
        """
        import tempfile
        from unittest import mock

        from library.content_fixtures import compute_content_digest

        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "topic_seed.py"
            seed.write_text('TOPICS = [("prayer", "On Prayer", "", [])]\n')
            with mock.patch(
                "library.content_fixtures.content_roots",
                return_value=[("library/topic_seed.py", seed)],
            ):
                before = compute_content_digest()
                seed.write_text('TOPICS = [("prayer", "On Prayer", "", ["humility-2"])]\n')
                self.assertNotEqual(
                    before, compute_content_digest(),
                    "adding a book to a topic left the digest still, so the shelf "
                    "page it appears on would never rebuild",
                )

    def test_the_seed_data_modules_hold_no_imports_of_django(self):
        """A declared root must stay readable without a Django environment.

        `content_digest` runs in the web build's prebuild gate and in curation
        scripts, neither of which calls `django.setup()`. These modules are data
        with a `from __future__` line; the day one grows a `models` import is
        the day the gate starts raising instead of reporting.
        """
        import ast

        for name in ("topic_seed.py", "plan_seed.py"):
            with self.subTest(module=name):
                tree = ast.parse((Path(__file__).resolve().parent / name).read_text())
                # The import STATEMENTS, not the text: both modules name
                # `django.core.management` in their docstrings, explaining why
                # they exist, and a substring check reads that as an import.
                imported = {
                    node.module or ""
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                } | {
                    alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Import)
                    for alias in node.names
                }
                heavy = sorted(
                    m for m in imported
                    if m.split(".")[0] == "django" or m.startswith("library.models")
                )
                self.assertEqual(
                    heavy, [],
                    f"{name} is a declared content root, read by the prebuild gate "
                    "and by curation scripts that never call django.setup()",
                )

    def test_the_recurring_seeds_read_only_from_declared_roots(self):
        """Every directory the release's content seeds read must be declared.

        Pins the actual failure: a seed gains a new data directory, nothing
        watches it, and its prose goes stale on the reader while looking correct
        in the database and in the repo.
        """
        seeds = Path(__file__).resolve().parent
        read_dirs = {
            "library/data/plan_translations": seeds / "plan_translations.py",
            "library/data/topic_translations": seeds / "topic_translations.py",
            # The English definitions, split out of the seed commands so a root
            # could name them: the shelves and plans themselves, not the prose.
            "library/topic_seed.py": seeds / "topic_seed.py",
            "library/plan_seed.py": seeds / "plan_seed.py",
        }
        for root, module in read_dirs.items():
            with self.subTest(root=root):
                self.assertTrue(module.is_file(), f"{module} moved; update this test")
                self.assertIn(
                    root,
                    self.roots,
                    f"{module.name} seeds the reader from {root}, which is not a "
                    "declared content root — so editing it rebuilds nothing.",
                )
        # Author bios have no fixture and ship as files under migrations/data.
        self.assertTrue(
            any(r == "library/migrations/data" for r in self.roots),
            "seed_author_translations reads migrations/data/author_bios_<lang>/; "
            "that tree must be a declared content root.",
        )

    def test_digest_changes_when_any_root_changes(self):
        """The whole mechanism rests on this: touch content, digest moves.

        Exercised against a temporary root rather than by dropping a probe file
        into the real fixture tree — ``unexpected_files()`` treats a stray file
        there as a fixture-layout error, so the probe would fail a sibling test
        while it existed and survive any interrupted run.
        """
        import tempfile
        from pathlib import Path
        from unittest import mock

        from library.content_fixtures import compute_content_digest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            (root / "books").mkdir(parents=True)
            work = root / "books" / "a-book.en.json"
            work.write_text('[{"model": "library.book"}]')

            with mock.patch(
                "library.content_fixtures.content_roots",
                return_value=[("library/fixtures/content", root)],
            ):
                before = compute_content_digest()
                work.write_text('[{"model": "library.book", "fields": {}}]')
                after = compute_content_digest()
                self.assertNotEqual(before, after, "editing content left the digest still")

                # A NEW file counts too — that is how a new translation ships.
                (root / "books" / "a-book.sw.json").write_text("[]")
                self.assertNotEqual(after, compute_content_digest())


class ContentProseTests(SimpleTestCase):
    """Rendering a fixture as prose — the thing that makes a translation
    reviewable in a diff. See library/content_prose.py for why it exists."""

    def test_paragraphs_split_on_block_tags_and_strip_inline_ones(self):
        from library.content_prose import paragraphs

        html = (
            "<p>First <em>emphasised</em> line.</p>"
            "<p>Second with a <a href='#'>link</a>.</p>"
            "<blockquote>A quotation.</blockquote>"
        )
        self.assertEqual(
            paragraphs(html),
            ["First emphasised line.", "Second with a link.", "A quotation."],
        )

    def test_entities_become_the_characters_a_reviewer_reads(self):
        from library.content_prose import paragraphs

        self.assertEqual(
            paragraphs("<p>Ben &amp; Sons &mdash; &quot;quoted&quot;</p>"),
            ['Ben & Sons — "quoted"'],
        )

    def test_paragraphs_are_numbered_by_chapter(self):
        """The numbering is the point: a hunk has to say WHERE in the book."""
        from library.content_prose import render

        out = render([
            {"model": "library.chapter",
             "fields": {"order": 7, "title": "Seven", "body_html": "<p>One.</p><p>Two.</p>"}},
        ])
        self.assertIn("--- CHAPTER 7: Seven", out)
        self.assertIn("[7.1] One.", out)
        self.assertIn("[7.2] Two.", out)

    def test_a_one_word_edit_renders_as_a_one_line_change(self):
        """The measurement the whole thing rests on. Raw, this fixture's
        one-word edit is a 36 KB diff because the chapter body is a single
        12 KB JSON line; as prose it is one short line."""
        import difflib

        from library.content_fixtures import book_fixture_path
        from library.content_prose import render_file

        raw = book_fixture_path("humility-2", "en").read_text()
        edited = raw.replace(" the Lord, and he will exalt you", " teh Lord, and he will exalt you", 1)
        self.assertNotEqual(raw, edited, "fixture text moved; pick another phrase")

        changed_json = [
            line for line in difflib.unified_diff(
                raw.splitlines(), edited.splitlines(), n=0, lineterm=""
            ) if line[:1] in "+-" and not line.startswith(("+++", "---"))
        ]
        changed_prose = [
            line for line in difflib.unified_diff(
                render_file(raw).splitlines(), render_file(edited).splitlines(),
                n=0, lineterm="",
            ) if line[:1] in "+-" and not line.startswith(("+++", "---"))
        ]
        self.assertEqual(len(changed_prose), 2, "one line removed, one added")
        # The raw pair is the whole chapter body twice; the prose pair is a
        # sentence. Two orders of magnitude is the difference between a diff a
        # reviewer reads and one they skip.
        self.assertLess(
            sum(len(line) for line in changed_prose) * 10,
            sum(len(line) for line in changed_json),
        )
        self.assertIn("teh Lord", "\n".join(changed_prose))
        # It also says where, which the raw diff never does.
        self.assertTrue(any(line.startswith("+[12.") for line in changed_prose))
        # Sanity: the JSON really is one enormous line, so this isn't a
        # comparison against a strawman.
        self.assertGreater(max(len(line) for line in changed_json), 10_000)

    def test_render_file_passes_through_anything_that_is_not_a_fixture(self):
        # A textconv must never fail or return nothing: git shows its output AS
        # the file, so a raise here would make every fixture look empty.
        from library.content_prose import render_file

        self.assertEqual(render_file("not json at all"), "not json at all")
        self.assertEqual(render_file('{"a": 1}'), '{"a": 1}')

    def test_gitattributes_points_at_the_shipped_textconv(self):
        repo_root = Path(__file__).resolve().parents[2]
        attrs = (repo_root / ".gitattributes").read_text()
        self.assertIn("diff=ochorus-content", attrs)
        self.assertTrue(
            (repo_root / "backend" / "scripts" / "fixture-textconv.py").is_file(),
            ".gitattributes names a diff driver whose script is missing, so a "
            "clone that opts in gets empty diffs for every fixture.",
        )


class ReleaseProseSourceCoverageTests(SimpleTestCase):
    """Every module the DEPLOY reads to write reader prose must be a content root.

    ``ContentSourceCoverageTests`` above checks that the three lists agree with
    *each other*. It cannot catch the failure that actually happened: a source
    of reader prose that is in **none** of them. ``library/corrections.py`` was
    exactly that — ``apply_body_corrections`` runs on every deploy
    (``release.py``) and rewrites ``Chapter.body_html`` / ``Sermon.body_html``
    from it, so a one-word fix shipped to the API, moved no digest, and never
    rebuilt the prerendered page that shows it. Readers kept the defective text
    until some unrelated commit happened to trigger a build.

    This test comes at it from the other side. It walks the release chain,
    follows its ``library`` imports, and finds the modules that carry prose —
    long, natural-language string literals that are not docstrings. Each one
    must then be either a declared content root or explicitly exempt below.

    The point is that a NEW prose module cannot be quietly added: it lands in
    neither list, so the test fails and names it, and whoever added it has to
    decide which it is. That decision is the thing that was missing.
    """

    # Modules the walk finds that are deliberately NOT content roots. Each needs
    # a reason, because "it's fine" is what let corrections.py sit unlisted.
    NOT_READER_PROSE = {
        # One-line author stubs planted only when an IMPORT creates a new author
        # (the import_* commands are not in the release chain). The real bio
        # comes from the fixture, which author_sync writes over it on the next
        # deploy — so editing one changes nothing a reader sees.
        "library/catalog.py": "import-time author stubs; the fixture supersedes them",
        # Writes bios from the fixture; holds no prose of its own.
        "library/author_sync.py": "copies fixture prose, holds none",
        # bible_licence / attribution text. Admin-facing (AddLanguageForm) — it
        # is not in the public serializers and reaches no prerendered page.
        "library/language_seed.py": "admin-facing licence text, not reader prose",
        # A stopword list that happens to look like a sentence.
        "library/scripture.py": "stopword list, not prose",
    }

    # A literal counts as prose if it is long, reads like sentences, and carries
    # no regex metacharacters (which is what a pattern looks like).
    _MIN_CHARS = 60
    _MIN_WORDS = 10
    _NO_REGEX = re.compile(r"^[^\\^$*+?{}\[\]|]*$")

    @staticmethod
    def _library_imports(path: Path) -> set[str]:
        tree = ast.parse(path.read_text())
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("library"):
                    found.add(node.module)
            elif isinstance(node, ast.Import):
                found.update(a.name for a in node.names if a.name.startswith("library"))
        return found

    @classmethod
    def _release_reachable(cls) -> set[Path]:
        """Every ``library`` module the release chain can reach."""
        backend = Path(__file__).resolve().parent.parent
        release = backend / "library/management/commands/release.py"
        commands = re.findall(r'call_command\(\s*"([a-z_]+)"', release.read_text())

        queue = [
            p
            for c in commands
            if (p := backend / f"library/management/commands/{c}.py").exists()
        ]
        seen: set[Path] = set()
        while queue:
            for module in cls._library_imports(queue.pop()):
                candidate = backend / (module.replace(".", "/") + ".py")
                if candidate.exists() and candidate not in seen:
                    seen.add(candidate)
                    queue.append(candidate)
        return seen

    # Calls whose string arguments are addressed to an OPERATOR, not a reader:
    # command help, console output, error messages. A management command is full
    # of these and none of them ship to the site — but the module is still
    # checked for genuine data literals, because CLAUDE.md's rule is precisely
    # that reader-visible seed prose must not live in a `seed_*` command.
    _OPERATOR_SINKS = {
        "write",
        "CommandError",
        "SUCCESS",
        "WARNING",
        "ERROR",
        "NOTICE",
        "add_argument",
    }

    @classmethod
    def _operator_facing(cls, tree: ast.AST) -> set[int]:
        """ids() of string nodes that are console/CLI text rather than content."""
        out: set[int] = set()

        def mark(node: ast.AST) -> None:
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, str):
                    out.add(id(child))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else func.id
                    if isinstance(func, ast.Name)
                    else ""
                )
                if name in cls._OPERATOR_SINKS:
                    mark(node)
            # `help="…"` as an argument keyword…
            elif isinstance(node, ast.keyword) and node.arg == "help" or isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "help" for t in node.targets
            ):
                mark(node)
        return out

    @classmethod
    def _prose_literals(cls, path: Path) -> int:
        tree = ast.parse(path.read_text())
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    docstrings.add(doc)
        operator = cls._operator_facing(tree)
        return sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and len(node.value) >= cls._MIN_CHARS
            and len(node.value.split()) >= cls._MIN_WORDS
            and cls._NO_REGEX.match(node.value)
            and node.value not in docstrings
            and id(node) not in operator
        )

    def test_release_chain_prose_modules_are_roots_or_exempt(self):
        backend = Path(__file__).resolve().parent.parent
        roots = json.loads(
            (backend / "library/content_sources.json").read_text()
        )["roots"]

        reachable = self._release_reachable()
        # Guard against the walk silently finding nothing and passing vacuously.
        self.assertGreater(len(reachable), 5, "the release-chain import walk found almost nothing")

        unclassified = []
        for path in sorted(reachable):
            if not self._prose_literals(path):
                continue
            rel = path.relative_to(backend).as_posix()
            declared = any(
                rel == root or rel.startswith(root.rstrip("/") + "/") for root in roots
            )
            if not declared and rel not in self.NOT_READER_PROSE:
                unclassified.append(rel)

        self.assertEqual(
            unclassified,
            [],
            "These modules are read by the deploy and carry prose, but are "
            "neither a content root nor listed as exempt:\n  "
            + "\n  ".join(unclassified)
            + "\n\nIf a reader can see this text, add the module to "
            "library/content_sources.json AND render.yaml's buildFilter — "
            "otherwise its pages never rebuild and readers keep the old prose. "
            "If a reader cannot, add it to NOT_READER_PROSE with the reason.",
        )

    def test_corrections_is_a_declared_root(self):
        """The specific regression: prose fixes must rebuild the reader."""
        backend = Path(__file__).resolve().parent.parent
        roots = json.loads(
            (backend / "library/content_sources.json").read_text()
        )["roots"]
        self.assertIn("library/corrections.py", roots)

    def test_exempt_list_has_no_stale_entries(self):
        """An exemption for a module the walk no longer reaches is a lie."""
        backend = Path(__file__).resolve().parent.parent
        reachable = {p.relative_to(backend).as_posix() for p in self._release_reachable()}
        stale = sorted(set(self.NOT_READER_PROSE) - reachable)
        self.assertEqual(
            stale,
            [],
            f"NOT_READER_PROSE names modules the release chain no longer reaches: {stale}",
        )


class NoBiographyArticlesTests(SimpleTestCase):
    """Biographies belong on author pages, never in /articles.

    A person's life story is written with the ``write-biography`` skill and
    rendered on ``/authors/<slug>``; articles are about topics, questions and
    works, not people's lives. Eight biography-articles were once written and
    had to be retired (migrations 0118/0119, PRs #1547/#1549) because they
    duplicated the author-page bios and split search authority. This guard keeps
    those exact slugs from creeping back as article fixtures. New person-lives
    must not be added as articles at all — see the write-article skill.
    """

    RETIRED = frozenset({
        "george-mueller-and-the-god-who-answers-prayer",
        "charles-spurgeon-the-prince-of-preachers",
        "john-newton-from-slave-trader-to-amazing-grace",
        "william-carey-father-of-modern-missions",
        "corrie-ten-boom-forgiveness-in-the-darkness",
        "hudson-taylor-trusting-god-for-the-impossible",
        "amy-carmichael-and-the-cost-of-love",
        "samuel-crowther-from-captive-to-bishop",
    })

    def test_retired_biography_articles_do_not_return(self):
        present = sorted(
            p.name
            for slug in self.RETIRED
            for p in ARTICLES_DIR.glob(f"{slug}.*.json")
        )
        self.assertEqual(
            present,
            [],
            "Biographies belong on the author page, not in /articles — these "
            "retired biography-article fixtures must not be re-added: "
            f"{present}",
        )
