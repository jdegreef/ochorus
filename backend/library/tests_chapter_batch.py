"""The chapter batch endpoint — the web build's way to fetch a book's chapters.

The contract is that a batch is nothing but the single-chapter endpoint served
several at a time: the build answers each chapter page from it, so any field
that differed would bake a different page than the reader's own request gets.
These tests compare the two field for field on a book whose chapters exercise
every shared lookup (neighbours, languages, the modern edition, linked and
unlinked scripture).
"""

from __future__ import annotations

import re
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .contemporize import MODERN_LANGUAGE
from .models import Author, Book, Chapter
from .scripture_graph import VERSE_FLOOR
from .views import CHAPTER_BATCH_MAX


class ChapterBatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        self.book = Book.objects.create(
            author=author, slug="w", language="en", title="A Work"
        )
        # Romans 8:28 clears the verse floor (a linked reference and chip);
        # Obadiah 1:3 is cited once, so it is annotated but links nowhere.
        for order in range(1, VERSE_FLOOR + 2):
            Chapter.objects.create(
                book=self.book,
                order=order,
                title=f"Chapter {order}",
                body_html=f"<p>As Romans 8:28 says ({order}).</p>"
                + ("<p>And Obadiah 1:3.</p>" if order == 1 else ""),
            )
        Book.objects.create(author=author, slug="w", language="es", title="Una obra")
        Book.objects.create(
            author=author, slug="w", language=MODERN_LANGUAGE, title="A Work"
        )
        call_command("index_citations", "--all", verbosity=0)

    def _batch(self, query="", slug="w"):
        return self.client.get(f"/api/library/books/{slug}/chapters/{query}")

    def test_each_chapter_matches_the_single_endpoint(self):
        res = self._batch("?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), VERSE_FLOOR + 1)
        for chapter in res.data:
            single = self.client.get(
                f"/api/library/books/w/chapters/{chapter['order']}/?language=en"
            )
            self.assertEqual(chapter, single.data)
        # The fixture really exercises the shared lookups, so equality above is
        # not two empty answers agreeing.
        first = res.data[0]
        self.assertIsNone(first["prev"])
        self.assertEqual(first["next"]["order"], 2)
        self.assertEqual(first["available_languages"], ["en", "es"])
        self.assertTrue(first["has_modern_edition"])
        self.assertIn('href="/scripture/romans/8/28/"', first["body_html"])
        self.assertTrue(any(r["page"] for r in first["scripture_refs"]))
        self.assertTrue(any(r["page"] is None for r in first["scripture_refs"]))

    def test_from_and_limit_select_a_run_of_chapters(self):
        res = self._batch("?language=en&from=2&limit=2")
        self.assertEqual([c["order"] for c in res.data], [2, 3])
        # The run's edges still name the neighbours outside it.
        self.assertEqual(res.data[0]["prev"]["order"], 1)
        self.assertEqual(res.data[-1]["next"]["order"], 4)

    def test_limit_is_capped(self):
        for order in range(VERSE_FLOOR + 2, CHAPTER_BATCH_MAX + 10):
            Chapter.objects.create(book=self.book, order=order, title="", body_html="<p>x</p>")
        res = self._batch("?language=en&limit=1000")
        self.assertEqual(len(res.data), CHAPTER_BATCH_MAX)

    def test_bad_paging_is_clamped(self):
        res = self._batch("?language=en&from=zero&limit=-3")
        self.assertEqual([c["order"] for c in res.data], [1])
        # A huge ?from= is clamped before it reaches the database as an
        # out-of-range integer (a 500).
        res = self._batch("?language=en&from=" + "9" * 30)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_a_translated_run_links_scripture_but_lists_no_chips(self):
        es = Book.objects.get(slug="w", language="es")
        Chapter.objects.create(
            book=es, order=1, title="Uno", body_html="<p>Como dice Romans 8:28.</p>"
        )
        res = self._batch("?language=es")
        (chapter,) = res.data
        self.assertEqual(chapter, self.client.get("/api/library/books/w/chapters/1/?language=es").data)
        self.assertEqual(chapter["scripture_refs"], [])
        self.assertIn('href="/scripture/romans/8/28/"', chapter["body_html"])
        self.assertFalse(chapter["has_modern_edition"])
        self.assertFalse(chapter["is_modern_edition"])

    def test_a_modern_edition_run_is_marked_modern(self):
        modern = Book.objects.get(slug="w", language=MODERN_LANGUAGE)
        Chapter.objects.create(book=modern, order=1, title="One", body_html="<p>x</p>")
        (chapter,) = self._batch(f"?language={MODERN_LANGUAGE}").data
        self.assertTrue(chapter["is_modern_edition"])
        self.assertTrue(chapter["has_modern_edition"])
        self.assertEqual(chapter["scripture_refs"], [])

    def test_the_web_build_never_asks_for_more_than_the_cap(self):
        # The build's batcher asks for runs of CHAPTER_BATCH_SIZE and relies on
        # getting them whole: a smaller cap here would silently send the rest of
        # every run back to per-chapter requests.
        source = (
            Path(__file__).resolve().parents[2] / "frontend/src/lib/chapterBatch.ts"
        ).read_text()
        size = int(re.search(r"CHAPTER_BATCH_SIZE = (\d+);", source).group(1))
        self.assertLessEqual(size, CHAPTER_BATCH_MAX)

    def test_an_unpublished_or_missing_edition_is_a_404(self):
        # Same answer as the single endpoint, so the build's English fallback
        # (localizedWithLang) still sees a 404 for an edition that isn't there.
        self.assertEqual(self._batch("?language=fr").status_code, 404)
        self.assertEqual(self._batch(slug="nope").status_code, 404)
        self.book.is_published = False
        self.book.save(update_fields=["is_published"])
        self.assertEqual(self._batch("?language=en").status_code, 404)

    def test_a_run_past_the_last_chapter_is_empty(self):
        res = self._batch("?language=en&from=500")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_a_batch_costs_a_fixed_number_of_queries(self):
        # The point of the endpoint: the run's lookups are shared, so the query
        # count does not grow with the number of chapters served.
        with self.assertNumQueries(7):
            self._batch("?language=en&limit=2")
        for order in range(VERSE_FLOOR + 2, 20):
            Chapter.objects.create(book=self.book, order=order, title="", body_html="<p>x</p>")
        with self.assertNumQueries(7):
            self._batch("?language=en&limit=20")
