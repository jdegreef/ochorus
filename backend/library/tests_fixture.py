"""Integrity guard for the content fixture (``launch.json``).

The fixture is appended to by many parallel branches, each assigning integer
primary keys by hand. Git merges are textual, so two branches claiming the same
pk for different content can MERGE CLEANLY and only fail (or worse, silently
corrupt) at load time:

* under ``loaddata`` a duplicate pk silently replaces the earlier row;
* under ``seed_books``/``seed_sermons`` the pk is the join key between rows, so
  a collision merges one book's chapters into another and aborts the pre-deploy
  release command on the unique-constraint violation.

This suite runs in CI on every PR and on main, turning that silent corruption
into a loud red build. It validates the *file*, not the database, so it needs
no fixtures loaded and runs in ~a second.

Nearly happened for real: two PRs in one week both claimed book pk 90 and
chapters 4403+; only a manual remap during conflict resolution prevented one
Luganda book from overwriting another (2026-07-17).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from django.test import SimpleTestCase

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "launch.json"

# The fixture deliberately contains exactly these models. Anything else (Topic,
# TopicBook, AuthorTranslation, ...) means someone ran a bare `dumpdata library`
# from a seeded dev DB instead of the pinned 6-model regen recipe.
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
        self.assertEqual(
            set(self.by_model), EXPECTED_MODELS,
            "Unexpected model in launch.json — a bare `dumpdata library` from a "
            "seeded dev DB leaks Topic/translation rows; use the pinned 6-model "
            "regen recipe (see the ship-content-fix skill).",
        )

    def test_primary_keys_unique_per_model(self):
        # A duplicate pk is exactly the parallel-append collision: it merges
        # cleanly in git and silently overwrites (loaddata) or corrupts the
        # chapter join (seed commands) at load time.
        for model, rows in self.by_model.items():
            dupes = _dupes(Counter(r["pk"] for r in rows))
            self.assertEqual(
                dupes, [],
                f"{model}: duplicate primary key(s) {dupes[:5]} — two branches "
                "assigned the same pk. Re-key the newer rows to fresh pks.",
            )

    def test_natural_identity_unique(self):
        # Content identity is slug (+ language) — the DB enforces this with
        # unique constraints, so a duplicate here bricks loaddata on a fresh
        # database even when the pks differ.
        checks = {
            "library.author": lambda f, pk: f["slug"],
            "library.book": lambda f, pk: (f["slug"], f.get("language", "en")),
            "library.sermon": lambda f, pk: (f["slug"], f.get("language", "en")),
            "library.plan": lambda f, pk: (f["slug"], f.get("language", "en")),
            "library.chapter": lambda f, pk: (f["book"], f["order"]),
            "library.planday": lambda f, pk: (f["plan"], f["day"]),
        }
        for model, key in checks.items():
            dupes = _dupes(
                Counter(key(r["fields"], r["pk"]) for r in self.by_model[model])
            )
            self.assertEqual(
                dupes, [],
                f"{model}: duplicate natural identity {dupes[:5]} — the same "
                "content exists twice; the DB's unique constraint will reject it.",
            )

    def test_references_resolve(self):
        # A dangling reference means a row points at content that isn't in the
        # file (e.g. a book whose author row was lost in a merge).
        author_pks = {r["pk"] for r in self.by_model["library.author"]}
        book_pks = {r["pk"] for r in self.by_model["library.book"]}
        plan_pks = {r["pk"] for r in self.by_model["library.plan"]}

        refs = [
            ("library.book", "author", author_pks),
            ("library.sermon", "author", author_pks),
            ("library.chapter", "book", book_pks),
            ("library.planday", "plan", plan_pks),
        ]
        for model, field, valid in refs:
            dangling = sorted(
                {r["fields"][field] for r in self.by_model[model]} - valid
            )
            self.assertEqual(
                dangling, [],
                f"{model}.{field}: dangling reference(s) {dangling[:5]} — the "
                "target row is missing from the fixture.",
            )

    def test_required_content_fields_present(self):
        # Rows missing slug/order/day would defeat the identity checks above
        # and break the seed commands' joins.
        for model, required in {
            "library.author": ("slug", "name"),
            "library.book": ("slug", "title", "author"),
            "library.chapter": ("book", "order", "body_html"),
            "library.sermon": ("slug", "title", "author"),
            "library.plan": ("slug", "title"),
            "library.planday": ("plan", "day", "book_slug", "chapter_order"),
        }.items():
            for r in self.by_model[model]:
                missing = [k for k in required if k not in r["fields"]]
                self.assertEqual(
                    missing, [],
                    f"{model} pk={r['pk']}: missing required field(s) {missing}",
                )
