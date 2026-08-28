"""The quote converter, which now has two callers that must not diverge.

`scripts/normalize_quotes.py` writes the committed fixture; migration 0082
writes the rows a deployed database already holds. Both call
`library.quotes.convert`, so these tests pin the decision itself rather than
either caller's output.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest import skipUnless

from django.apps import apps
from django.contrib.postgres.search import SearchVector
from django.db import connection
from django.db.models import Value
from django.test import SimpleTestCase, TestCase

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
from library.models import Author, Book, Chapter
from library.quotes import (
    assert_punctuation_only,
    convert,
    quote_style,
    uses_guillemets,
)

# The works migration 0082 repairs, and the language it repairs them in.
MIGRATION_0082 = [
    (BOOKS_DIR / "clothed-with-strength-and-dignity.es.json", "book"),
    (BOOKS_DIR / "jesus-himself-2.es.json", "book"),
    (BOOKS_DIR / "prevailing-prayer.es.json", "book"),
    (SERMONS_DIR / "unfailing-springs.es.json", "sermon"),
]


class QuoteConversionTests(SimpleTestCase):
    def test_a_work_without_guillemets_takes_the_curly_pair(self):
        """Every English work this has ever touched.

        The first version decided this from guillemet DEPTH alone, so a
        guillemet-free work took « » — Spanish outer marks in English prose. It
        never fired (the English works were normalised before guillemets were
        understood, and none has been mixed since), but a single newly-imported
        mixed English book would have tripped it.
        """
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
        """Depth is per CALL, and a call is one chapter.

        Both callers convert a chapter at a time, so neither can carry an
        unclosed « into the next one — which is what makes the fixture sweep
        and the migration agree row for row.
        """
        first, _ = convert('<p>«Una cita que no cierra: "aquí".</p>', outer_guillemets=True)
        second, _ = convert('<p>Y aquí "otra".</p>', outer_guillemets=True)
        self.assertIn("“aquí”", first)
        self.assertIn("«otra»", second)

    def test_a_mark_opening_a_paragraph_opens(self):
        """`<p>` and nothing else to its left. Without ">" in the opening set
        EVERY paragraph-initial quotation became a closing mark."""
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
        """`&quot;` literally contains q-u-o-t, so a raw string comparison
        reports "letters changed" the moment an entity becomes a curly mark.
        The guard compares what the READER sees."""
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


class Migration0082FidelityTests(SimpleTestCase):
    """The rows the migration repairs must land on the text the fixture holds.

    The migration and `scripts/normalize_quotes.py` run the SAME converter over
    the SAME works, one against the database and one against the file. If the
    converter is ever changed, a fresh build (which loads the fixture) and a
    deployed database (which the migration repaired) would start showing the
    reader different marks for the same edition — and nothing else would say so.
    """

    def test_the_named_works_are_in_the_fixture_and_need_no_conversion(self):
        for path, kind in MIGRATION_0082:
            with self.subTest(path.name):
                self.assertTrue(path.exists(), f"{path.name} is named by 0082 but missing")
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
                        f"{path.name} row {i} ({kind}) still holds straight marks the "
                        f"migration would convert — the fixture and the deployed "
                        f"database would disagree",
                    )
                    self.assertEqual(out, body)

    def test_those_works_read_as_consistently_typographic(self):
        """The state the migration is driving a deployed database towards."""
        for path, _ in MIGRATION_0082:
            with self.subTest(path.name):
                rows = json.loads(path.read_text(encoding="utf-8"))
                joined = "".join(r["fields"].get("body_html") or "" for r in rows)
                self.assertEqual(quote_style(joined), "curly")


class Migration0082BehaviourTests(TestCase):
    """The migration itself, against real rows.

    `Migration0082FidelityTests` proves the fixture needs no conversion; that is
    the state AFTER this has run everywhere. This proves the step that gets a
    database there — and, just as much, that it leaves alone what it must:
    a deployed database holds eight other editions of
    `clothed-with-strength-and-dignity`, and the converter would give an English
    chapter's straight quotes the Spanish outer mark.
    """

    def _load_repair(self):
        path = Path(__file__).resolve().parent / "migrations" / "0082_repair_mixed_quotes.py"
        spec = importlib.util.spec_from_file_location("m0082", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.repair

    def _book(self, language, body):
        author = Author.objects.create(slug=f"a-{language}", name="A")
        book = Book.objects.create(
            slug="clothed-with-strength-and-dignity",
            language=language,
            title="T",
            author=author,
        )
        return Chapter.objects.create(book=book, order=1, title="One", body_html=body)

    def test_it_converts_the_spanish_edition_and_leaves_the_english_alone(self):
        es = self._book("es", '<p>«Él dijo: "ven".» Y luego "se fue".</p>')
        en = self._book("en", '<p>He said, "come." And then "he left."</p>')

        self._load_repair()(apps, None)

        es.refresh_from_db()
        en.refresh_from_db()
        self.assertEqual(es.body_html, "<p>«Él dijo: “ven”.» Y luego «se fue».</p>")
        self.assertEqual(
            en.body_html,
            '<p>He said, "come." And then "he left."</p>',
            "the English edition shares the slug and must not be touched",
        )

    def test_it_re_derives_what_save_would_have_derived(self):
        """A historical model runs no `save()` hook, so the repair has to do by
        hand what the hook would have done — otherwise `body_text` (what search
        indexes) still holds the old marks."""
        chapter = self._book("es", '<p>«Él dijo: "ven".»</p>')
        Chapter.objects.filter(pk=chapter.pk).update(body_text="stale", word_count=0)

        self._load_repair()(apps, None)

        chapter.refresh_from_db()
        self.assertIn("“ven”", chapter.body_text)
        self.assertEqual(chapter.word_count, len(chapter.body_text.split()))

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

        self._load_repair()(apps, None)

        chapter.refresh_from_db()
        self.assertIsNone(chapter.search_vector)

    def test_it_is_a_no_op_on_a_database_that_already_holds_the_repair(self):
        """Not merely "the text is unchanged" — the ROW must not be written.

        A repair that saved every row anyway would null every search vector it
        touched, queueing the whole corpus for a needless rebuild on a deploy
        where nothing changed. `body_text` is the witness: any save re-derives
        it from `body_html`, so a marker surviving proves no save happened.
        """
        chapter = self._book("es", "<p>«Él dijo: “ven”.»</p>")
        Chapter.objects.filter(pk=chapter.pk).update(body_text="untouched-marker")

        self._load_repair()(apps, None)

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_html, "<p>«Él dijo: “ven”.»</p>")
        self.assertEqual(chapter.body_text, "untouched-marker")
