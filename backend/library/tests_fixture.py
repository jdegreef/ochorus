"""Integrity guard for the content fixture (``launch.json``).

The fixture is **natural-key format**: rows carry no integer primary keys, and
references are self-describing tuples — a book's author is ``["slug"]``, a
chapter's book is ``["slug", "language"]``. Identity is content-derived, so two
parallel branches appending different content *cannot* collide on a key the way
hand-assigned integer pks did (two PRs claimed the same pks in one week,
2026-07-17 — the incident this architecture retires).

What can still go wrong, and what this suite (CI, every PR, ~0.1s, no DB)
catches loudly:

* an old-format (pk) row appended by a stale branch — under ``loaddata`` a
  non-colliding pk row can load silently with the WRONG author (integer FKs
  resolve against re-assigned auto-pks); the seeds hard-fail on it, and so
  does this suite, earlier;
* the same work added twice (duplicate natural key) — ``loaddata`` is silent
  last-write-wins, and the DB's unique constraints brick a fresh load;
* a reference to a row that isn't in the file (author lost in a merge);
* foreign models leaking in from a bare ``dumpdata library`` on a seeded dev DB
  (the regen recipe pins exactly these six models — see ship-content-fix).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from django.test import SimpleTestCase

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "launch.json"

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


class FixtureIntegrityTests(SimpleTestCase):
    """File-level invariants every content append must preserve."""

    rows: list = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = json.loads(FIXTURE.read_text())
        cls.by_model = {}
        for r in cls.rows:
            cls.by_model.setdefault(r["model"], []).append(r)

    def test_only_expected_models(self):
        extra = set(self.by_model) - EXPECTED_MODELS
        missing = EXPECTED_MODELS - set(self.by_model)
        self.assertEqual(
            extra, set(),
            "Unexpected model in launch.json — a bare `dumpdata library` from a "
            "seeded dev DB leaks Topic/translation rows; use the pinned 6-model "
            "regen recipe (backend/scripts/regen_fixture.py).",
        )
        self.assertEqual(
            missing, set(),
            "A content model has no rows in launch.json — if intentional, "
            "update EXPECTED_MODELS consciously.",
        )

    def test_no_integer_pk_rows(self):
        # The fixture is natural-key format. A stale old-format row is the one
        # remaining silent-corruption path: its integer FK resolves against
        # whatever auto-pks the target DB happens to have (experimentally shown
        # attributing a sermon to the wrong author). Reject it outright.
        stale = [r for r in self.rows if "pk" in r]
        self.assertEqual(
            stale, [],
            f"{len(stale)} old-format (integer-pk) row(s) — e.g. "
            f"{stale[0]['model'] if stale else ''}. Re-serialize with "
            "Django's serializer using natural keys (backend/CLAUDE.md: The "
            "fixture) — never hand-assign pks.",
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
        # runs as ONE call over one file, and all FKs here are NOT NULL, so a
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

        # body_text is derived by save(); the seed must not set it directly.
        expected = self._content_fields(
            Chapter, exclude={"id", "book", "body_text", "created_at", "updated_at"}
        )
        self.assertEqual(set(CHAPTER_FIELDS), expected)

    def test_sermon_fields_cover_model(self):
        from library.management.commands.seed_sermons import SERMON_FIELDS
        from library.models import Sermon

        # preached_on is handled separately (date parsing); body_text derived.
        expected = self._content_fields(
            Sermon,
            exclude={"id", "author", "slug", "language", "preached_on",
                     "body_text", "created_at", "updated_at"},
        )
        self.assertEqual(set(SERMON_FIELDS), expected)
