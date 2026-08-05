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

from collections import Counter
from functools import lru_cache

from django.conf import settings
from django.test import SimpleTestCase

from library.content_fixtures import (
    AUTHORS_FILE,
    authors_by_slug,
    BOOKS_DIR,
    PLANS_FILE,
    SERMONS_DIR,
    load_all_rows,
    rows_by_file,
    unexpected_files,
    work_filename,
)

EXPECTED_MODELS = {
    "library.author",
    "library.book",
    "library.chapter",
    "library.sermon",
    "library.plan",
    "library.planday",
}


def _dupes(counter: Counter) -> list:
    return sorted(k for k, n in counter.items() if n > 1)


@lru_cache(maxsize=1)
def all_rows() -> list:
    """Every content row, parsed once for the whole module.

    ``load_all_rows`` re-reads all 166 files on each call (~114MB of transient
    allocation), and several classes here want the same rows. Cached in the test
    module rather than in ``content_fixtures`` so the seed commands, which run in
    long-lived processes, don't hold the parsed tree forever.
    """
    return load_all_rows()


def _cover(fields: dict) -> str:
    """A book row's cover_url, absent-or-null normalised to ''."""
    return fields.get("cover_url") or ""


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
            "seeded dev DB leaks Topic/translation rows; use the pinned 6-model "
            "regen recipe (backend/scripts/regen_fixture.py).",
        )
        self.assertEqual(
            missing, set(),
            "A content model has no rows in the content fixtures — if intentional, "
            "update EXPECTED_MODELS consciously.",
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

    def test_natural_identity_unique(self):
        # Content identity: what the DB's unique constraints enforce at load
        # time. A duplicate here is the same work added twice — loaddata is
        # silent last-write-wins, so only this check makes it loud.
        checks = {
            "library.author": lambda f: f["slug"],
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
        for model, field, valid in refs:
            dangling = sorted(
                {tuple(r["fields"][field]) for r in self.by_model.get(model, [])}
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
        for model, field, arity in shapes:
            bad = [
                r["fields"][field]
                for r in self.by_model.get(model, [])
                if not (isinstance(r["fields"][field], list)
                        and len(r["fields"][field]) == arity)
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
        }.items():
            for r in self.by_model.get(model, []):
                missing = [k for k in required if k not in r["fields"]]
                self.assertEqual(
                    missing, [],
                    f"{model} {r['fields'].get('slug', '?')}: missing required "
                    f"field(s) {missing}",
                )


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
            Book, exclude={"id", "author", "slug", "language", "created_at", "updated_at"}
        )
        self.assertEqual(set(BOOK_FIELDS), expected)

    def test_chapter_fields_cover_model(self):
        from library.management.commands.seed_books import CHAPTER_FIELDS
        from library.models import Chapter

        # body_text and search_vector are derived by save(); the seed must
        # not set them directly. citations_indexed_at must stay unset so the
        # index_citations release step scans freshly seeded chapters.
        expected = self._content_fields(
            Chapter,
            exclude={"id", "book", "body_text", "search_vector",
                     "citations_indexed_at", "created_at", "updated_at"},
        )
        self.assertEqual(set(CHAPTER_FIELDS), expected)

    def test_sermon_fields_cover_model(self):
        from library.management.commands.seed_sermons import SERMON_FIELDS
        from library.models import Sermon

        # preached_on is handled separately (date parsing); body_text and
        # search_vector are derived.
        expected = self._content_fields(
            Sermon,
            exclude={"id", "author", "slug", "language", "preached_on",
                     "body_text", "search_vector", "created_at", "updated_at"},
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
                self.assertTrue(mod.CREATE_ONLY_FIELDS <= set(fields))

    def test_fill_only_fields_are_real_author_fields(self):
        # Same silent-failure shape as CREATE_ONLY_FIELDS above: author_sync
        # reads each name off the fixture row with .get(), so a typo'd or
        # renamed entry yields None, the truthiness check skips it, and that
        # field simply never syncs again — no error, on any deploy, ever.
        from library.author_sync import FILL_ONLY_FIELDS
        from library.models import Author

        model_fields = {f.name for f in Author._meta.concrete_fields}
        self.assertTrue(set(FILL_ONLY_FIELDS) <= model_fields)
        # `bio` has its own rule (empty-or-stub); it must not be fill-only too.
        self.assertNotIn("bio", FILL_ONLY_FIELDS)


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
        cls.files = rows_by_file()

    def test_authors_file_is_authors_only(self):
        models = {r["model"] for r in self.files.get(AUTHORS_FILE, [])}
        self.assertEqual(models, {"library.author"})

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


class AuthorBioDataIntegrityTests(SimpleTestCase):
    """The translated author bios (migrations/data/author_bios_<lang>/) are
    delivered by the seed_author_translations deploy step, which soft-skips a
    slug with no matching Author — deliberately deploy-safe, which means a
    typo'd short.json key or misnamed <slug>.html would silently never ship.
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

    # Anchored on settings, like generate_covers' COVERS_DIR — walking up from
    # the fixture dir would encode the content layout's depth into a fact about
    # the frontend tree.
    STATIC_DIR = settings.BASE_DIR.parent / "frontend" / "static"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.books = [
            r["fields"] for r in all_rows() if r["model"] == "library.book"
        ]

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
            and not (self.STATIC_DIR / _cover(f).lstrip("/")).is_file()
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

    def test_svg_covers_have_a_raster_twin_for_og_image(self):
        # og:image falls back to /covers/<slug>.png when the cover is an SVG —
        # social platforms refuse SVG previews (books/[slug]/+page.svelte).
        missing = sorted(
            f["slug"]
            for f in self.books
            if _cover(f).endswith(".svg")
            and not (self.STATIC_DIR / "covers" / f"{f['slug']}.png").is_file()
        )
        self.assertEqual(missing, [], "generated SVG cover without its .png twin")


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
