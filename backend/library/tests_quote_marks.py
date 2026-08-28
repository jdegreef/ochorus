"""The quote converter, which now has two callers that must not diverge.

`scripts/normalize_quotes.py` writes the committed fixture; migration 0084
writes the rows a deployed database already holds. Both call
`library.quote_marks.convert`, so these tests pin the decision itself rather than
either caller's output.
"""

from __future__ import annotations

import importlib
import json
from unittest import skipUnless

from django.contrib.postgres.search import SearchVector
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Value
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
from library.ingest import word_count
from library.models import Author, Book, Chapter, Sermon
from library.quote_marks import (
    assert_punctuation_only,
    convert,
    uses_guillemets,
)
from library.text import html_to_text

MIGRATION = importlib.import_module("library.migrations.0084_repair_mixed_quotes")

# Read off the migration rather than restated beside it: a slug added to 0084
# would otherwise leave this test quietly checking the old set.
MIGRATION_0084 = [
    BOOKS_DIR / f"{slug}.{MIGRATION.LANGUAGE}.json" for slug in MIGRATION.BOOK_SLUGS
]

# The Spanish sermon #1132 also converted is deliberately NOT here, and not in
# the migration: `seed_sermons` upserts `body_html` and calls a real `save()`
# (only `source_type` and `is_published` are create-only), so a sermon's fixture
# edit DOES reach a deployed database on the next deploy — with better fidelity
# than a migration, since `save()` re-derives `body_text` and the vector through
# the model's own hooks. Only chapters are stranded.
SERMON_ALREADY_SEEDED = SERMONS_DIR / "unfailing-springs.es.json"


class QuoteConversionTests(SimpleTestCase):
    def test_a_work_without_guillemets_takes_the_curly_pair(self):
        """Every English work. The case `convert`'s first version got wrong."""
        out, changed = convert(
            '<p>He said, "Come and see," and they came.</p>', outer_guillemets=False
        )
        self.assertEqual(out, "<p>He said, “Come and see,” and they came.</p>")
        self.assertEqual(changed, 2)

    def test_inside_a_guillemet_span_the_straight_mark_is_the_NESTED_level(self):
        """The Spanish rule: « » outside, “ ” nested — decided by depth.

        Converting these outer quotations to “ ” would have swapped one
        inconsistency for another rather than fixing it, which is why depth is
        tracked at all.
        """
        out, _ = convert(
            '<p>«Él dijo: "ven", y vino.» Luego "se fue".</p>', outer_guillemets=True
        )
        self.assertEqual(out, "<p>«Él dijo: “ven”, y vino.» Luego «se fue».</p>")

    def test_depth_does_not_survive_an_unclosed_span(self):
        """These books leave quotations open across a chapter; depth is per call."""
        first, _ = convert('<p>«Una cita que no cierra: "aquí".</p>', outer_guillemets=True)
        second, _ = convert('<p>Y aquí "otra".</p>', outer_guillemets=True)
        self.assertIn("“aquí”", first)
        self.assertIn("«otra»", second)

    def test_a_mark_opening_a_paragraph_opens(self):
        """`<p>` and nothing else to its left."""
        out, _ = convert('<p>"Come and see," he said.</p>', outer_guillemets=False)
        self.assertTrue(out.startswith("<p>“Come"))

    def test_quotes_inside_a_tag_are_left_alone(self):
        """Attribute values are quoted too."""
        out, changed = convert(
            '<p class="lead">nothing to convert</p>', outer_guillemets=False
        )
        self.assertEqual(out, '<p class="lead">nothing to convert</p>')
        self.assertEqual(changed, 0)

    def test_the_entity_form_converts_and_the_guard_still_passes(self):
        """The entity form, and the guard reading through it rather than at it."""
        before = "<p>He said, &quot;Come.&quot;</p>"
        after, changed = convert(before, outer_guillemets=False)
        self.assertEqual(after, "<p>He said, “Come.”</p>")
        self.assertEqual(changed, 2)
        assert_punctuation_only(before, after, "entity")

    def test_conversion_is_idempotent(self):
        once, _ = convert('<p>«Él dijo: "ven".»</p>', outer_guillemets=True)
        twice, changed = convert(once, outer_guillemets=True)
        self.assertEqual(twice, once)
        self.assertEqual(changed, 0)

    def test_the_guard_rejects_a_change_to_the_wording(self):
        with self.assertRaises(AssertionError):
            assert_punctuation_only("<p>the word</p>", "<p>the words</p>", "wording")
        with self.assertRaises(AssertionError):
            assert_punctuation_only("<p>a</p>", "<p><b>a</b></p>", "tags")

    def test_the_guard_reads_scripts_the_old_allowlist_dropped(self):
        """It listed Latin, Arabic and Cyrillic. Devanagari fell through it, so
        on the Hindi editions it compared "" with "" and guarded nothing."""
        for before, after in [
            ("<p>नम्रता है</p>", "<p>नम्रता हैं</p>"),   # Devanagari (hi)
            ("<p>ตัวอย่าง</p>", "<p>ตัวอย่างๆ</p>"),      # a script nothing listed
            ("<p>a b</p>", "<p>a  b</p>"),               # whitespace
            ("<p>one, two</p>", "<p>one; two</p>"),      # punctuation
        ]:
            with self.subTest(before=before), self.assertRaises(AssertionError):
                assert_punctuation_only(before, after, "script")


class Migration0084FidelityTests(SimpleTestCase):
    """The rows the migration repairs must land on the text the fixture holds.

    The migration and `scripts/normalize_quotes.py` run the SAME converter over
    the SAME works, one against the database and one against the file. If the
    converter is ever changed, a fresh build (which loads the fixture) and a
    deployed database (which the migration repaired) would start showing the
    reader different marks for the same edition — and nothing else would say so.
    """

    def test_the_named_works_are_in_the_fixture_and_need_no_conversion(self):
        for path in [*MIGRATION_0084, SERMON_ALREADY_SEEDED]:
            with self.subTest(path.name):
                self.assertTrue(path.exists(), f"{path.name} is named by 0084 but missing")
                rows = json.loads(path.read_text(encoding="utf-8"))
                bodies = [
                    body
                    for r in rows
                    if (body := r["fields"].get("body_html"))
                ]
                self.assertTrue(bodies, f"{path.name} carries no prose")
                outer = uses_guillemets("".join(bodies))
                self.assertTrue(
                    outer, f"{path.name} is repaired as a « »-quoting work but sets none"
                )
                for i, body in enumerate(bodies):
                    out, changed = convert(body, outer_guillemets=outer)
                    self.assertEqual(
                        changed,
                        0,
                        f"{path.name} row {i} still holds straight marks the "
                        f"migration would convert — the fixture and the deployed "
                        f"database would disagree",
                    )
                    self.assertEqual(out, body)

    def test_both_body_fields_carry_the_same_marks(self):
        """`body_text` is what search indexes, and `loaddata` writes it VERBATIM.

        The first sweep converted `body_html` only, so these four works shipped
        a `body_text` still holding all 299 of their pre-conversion straight
        marks — a fresh database indexed and snippeted straight quotes while its
        pages rendered « ». `backfill_body_text` would not have caught it: it
        fills an EMPTY `body_text`, never a wrong one.

        Scoped to these works deliberately. The same drift is corpus-wide (46
        files, ~12,000 marks) and repairing it is its own change; this pins the
        part repaired here so it cannot regress.
        """
        for path in [*MIGRATION_0084, SERMON_ALREADY_SEEDED]:
            with self.subTest(path.name):
                for row in json.loads(path.read_text(encoding="utf-8")):
                    body_html = row["fields"].get("body_html")
                    body_text = row["fields"].get("body_text")
                    if not body_html or body_text is None:
                        continue
                    self.assertEqual(html_to_text(body_html), body_text)


class Migration0084BehaviourTests(TestCase):
    """The migration itself, run the way `migrate` runs it.

    `Migration0084FidelityTests` proves the fixture needs no conversion; that is
    the state AFTER this has run everywhere. This proves the step that gets a
    database there — and, just as much, that it leaves alone what it must:
    a deployed database holds eight other editions of
    `clothed-with-strength-and-dignity`, and the converter would give an English
    chapter's straight quotes the Spanish outer mark.

    HISTORICAL models, not `django.apps.apps`. Passing the live registry looks
    equivalent and quietly disarms two of these tests: a real `Chapter.save()`
    re-derives `body_text` itself, so `_derive` could be deleted outright and
    they would still pass; and it fires `fts.refresh_chapter`, which repopulates
    the very vector the migration nulls. The migration receives models with no
    hooks at all, so that is what it is given here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        executor = MigrationExecutor(connection)
        cls.historical = executor.loader.project_state(
            ("library", MIGRATION.Migration.dependencies[0][1])
        ).apps

    def _book(self, language, body):
        author = Author.objects.create(slug=f"a-{language}", name="A")
        book = Book.objects.create(
            slug=MIGRATION.BOOK_SLUGS[0], language=language, title="T", author=author
        )
        return Chapter.objects.create(book=book, order=1, title="One", body_html=body)

    def test_it_converts_the_spanish_edition_and_leaves_the_english_alone(self):
        es = self._book("es", '<p>«Él dijo: "ven".» Y luego "se fue".</p>')
        en = self._book("en", '<p>He said, "come." And then "he left."</p>')

        MIGRATION.repair(self.historical, None)

        es.refresh_from_db()
        en.refresh_from_db()
        self.assertEqual(es.body_html, "<p>«Él dijo: “ven”.» Y luego «se fue».</p>")
        self.assertEqual(
            en.body_html,
            '<p>He said, "come." And then "he left."</p>',
            "the English edition shares the slug and must not be touched",
        )

    def test_it_re_derives_what_save_would_have_derived(self):
        """No hook runs, so the repair must do by hand what `save()` would.

        Compared against a real `save()` rather than against itself: a local
        `<[^>]+>` sub passes self-consistency and still spaces every inline tag
        and leaves entities escaped.
        """
        chapter = self._book("es", '<p>«Él dijo: <i>"ven"</i>, y G&amp;C vino.»</p>')
        Chapter.objects.filter(pk=chapter.pk).update(body_text="stale", word_count=0)

        MIGRATION.repair(self.historical, None)

        chapter.refresh_from_db()
        self.assertIn("“ven”", chapter.body_text)

        witness = Chapter.objects.create(
            book=chapter.book, order=99, title="W", body_html=chapter.body_html
        )
        self.assertEqual(chapter.body_text, witness.body_text)
        # `word_count` gets no witness: `save()` does not set it — that is what
        # `backfill_word_count` exists for — so the import-time rule is the
        # reference, and a witness row would only prove 0 == 0.
        self.assertEqual(chapter.word_count, word_count(chapter.body_html))

    @skipUnless(connection.vendor == "postgresql", "tsvector is a Postgres type")
    def test_it_nulls_the_vector_it_invalidates(self):
        """Left alone the stored vector stays valid-LOOKING but stale, and
        search keeps matching text the page no longer shows. The release
        chain's `backfill_search_vectors` repairs NULLs, so nulling is what
        puts it back in step."""
        chapter = self._book("es", '<p>«Él dijo: "ven".»</p>')
        Chapter.objects.filter(pk=chapter.pk).update(
            search_vector=SearchVector(Value("stale"))
        )

        MIGRATION.repair(self.historical, None)

        chapter.refresh_from_db()
        self.assertIsNone(chapter.search_vector)

    def test_it_is_a_no_op_on_a_database_that_already_holds_the_repair(self):
        """Not merely "the text is unchanged" — the ROW must not be written.

        A repair that saved every row anyway would null every search vector it
        touched, queueing the whole corpus for a needless rebuild on a deploy
        where nothing changed. `body_text` is the witness: a save rewrites it
        from `body_html`, so a marker surviving proves no save happened.
        """
        chapter = self._book("es", "<p>«Él dijo: “ven”.»</p>")
        Chapter.objects.filter(pk=chapter.pk).update(body_text="untouched-marker")

        MIGRATION.repair(self.historical, None)

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_html, "<p>«Él dijo: “ven”.»</p>")
        self.assertEqual(chapter.body_text, "untouched-marker")


class Migration0085Tests(TestCase):
    """Re-deriving `body_text`, which nothing else in the release chain repairs.

    `backfill_body_text` filters on `body_text=""`, so a value that is present
    but WRONG is invisible to it — and `body_text` is what search indexes, so a
    wrong one means the index and the page disagree with nobody noticing.
    """

    def _repair(self):
        return importlib.import_module("library.migrations.0085_rederive_body_text").rederive

    def _historical(self):
        return MigrationExecutor(connection).loader.project_state(
            ("library", "0084_repair_mixed_quotes")
        ).apps

    def _chapter(self, body_html, body_text):
        author = Author.objects.create(slug="a-85", name="A")
        book = Book.objects.create(slug="b-85", language="en", title="T", author=author)
        chapter = Chapter.objects.create(
            book=book, order=1, title="One", body_html=body_html
        )
        Chapter.objects.filter(pk=chapter.pk).update(body_text=body_text)
        return chapter

    def test_it_repairs_a_present_but_wrong_body_text(self):
        """The case `backfill_body_text` cannot see, because it is not empty."""
        chapter = self._chapter("<p>God&#x27;s own “work”.</p>", "God&#x27;s own \"work\".")

        self._repair()(self._historical(), None)

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_text, "God's own “work”.")

    def test_it_fills_an_empty_one_too(self):
        chapter = self._chapter("<p>One.</p><p>Two.</p>", "")

        self._repair()(self._historical(), None)

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_text, "One. Two.")

    @skipUnless(connection.vendor == "postgresql", "tsvector is a Postgres type")
    def test_it_nulls_the_index_it_invalidates(self):
        """`body_text` IS the indexed text, so here this is the point of the
        migration rather than a precaution: a repaired row whose vector was left
        alone keeps matching searches for text it no longer holds."""
        chapter = self._chapter("<p>correct</p>", "stale")
        Chapter.objects.filter(pk=chapter.pk).update(
            search_vector=SearchVector(Value("stale"))
        )

        self._repair()(self._historical(), None)

        chapter.refresh_from_db()
        self.assertIsNone(chapter.search_vector)

    def test_a_row_already_in_step_issues_no_write_at_all(self):
        """Otherwise it would null every vector and citation stamp in the
        corpus, queueing the whole library for a needless re-index on a deploy
        where nothing changed.

        Asserted on the QUERIES, not on a column. The first version of this
        checked `word_count` survived — which `save(update_fields=[...])` never
        writes on any path, so it passed with the skip-guard deleted and proved
        nothing. Only a field `update_fields` carries can witness a save, and
        the cheapest witness is that no UPDATE is issued.
        """
        self._chapter("<p>Settled.</p>", "Settled.")

        with CaptureQueriesContext(connection) as queries:
            self._repair()(self._historical(), None)

        updates = [q["sql"] for q in queries if q["sql"].lstrip().upper().startswith("UPDATE")]
        self.assertEqual(updates, [], "an in-step row must not be written")

    def test_it_clears_the_citation_stamp_it_invalidates(self):
        """`index_citations` scans `body_text` and is INCREMENTAL on this stamp.

        `Chapter.save()` clears it whenever `body_html` moves; here `body_html`
        does NOT move and `body_text` does, which is the one case that rule does
        not cover — so a repaired chapter would keep the citations extracted
        from text it no longer holds, and a fresh build and the deployed
        database would disagree permanently.
        """
        chapter = self._chapter("<p>See Matthew 5:3 and John 3:16.</p>", "stale")
        Chapter.objects.filter(pk=chapter.pk).update(citations_indexed_at=timezone.now())

        self._repair()(self._historical(), None)

        chapter.refresh_from_db()
        self.assertIsNone(chapter.citations_indexed_at)

    def test_a_row_with_no_body_html_is_left_alone(self):
        """The fixture command and its gate both skip these; deriving from
        nothing would blank a `body_text` rather than repair it."""
        chapter = self._chapter("", "kept")

        self._repair()(self._historical(), None)

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_text, "kept")

    def test_it_repairs_sermons_as_well_as_chapters(self):
        author = Author.objects.create(slug="a-85s", name="A")
        sermon = Sermon.objects.create(
            author=author, slug="s-85", language="es", title="S",
            body_html="<p>«Ven», dijo.</p>",
        )
        Sermon.objects.filter(pk=sermon.pk).update(body_text="wrong")

        self._repair()(self._historical(), None)

        sermon.refresh_from_db()
        self.assertEqual(sermon.body_text, "«Ven», dijo.")
