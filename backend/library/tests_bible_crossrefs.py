"""A Bible chapter's related passages (OpenBible.info cross-references, CC BY):
the bundled data, and what the chapter API makes of it."""

from __future__ import annotations

import gzip
import json

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .bible_crossrefs import BIBLE_SERIES, BUNDLE
from .models import Author, Book, Chapter, Series


class BundleTests(SimpleTestCase):
    def setUp(self):
        self.data = json.loads(gzip.decompress(BUNDLE.read_bytes()))

    def test_it_carries_its_credit(self):
        # CC BY: the credit travels with the data, and the reader shows it.
        self.assertIn("OpenBible.info", self.data["credit"])
        self.assertIn("CC BY", self.data["license"])

    def test_every_book_and_chapter_of_the_bible(self):
        books = self.data["books"]
        self.assertEqual(len(books), 66)
        self.assertEqual(len(books["psalms"]), 150)
        # English numbering: Malachi has four chapters (Hebrew has three).
        self.assertEqual(sorted(books["malachi"], key=int), ["1", "2", "3", "4"])

    def test_each_chapter_is_a_short_row_of_other_chapters(self):
        for slug, chapters in self.data["books"].items():
            for chapter, rows in chapters.items():
                self.assertLessEqual(len(rows), 10)
                targets = [(b, n) for _, b, n in rows]
                self.assertEqual(len(targets), len(set(targets)), (slug, chapter))
                self.assertNotIn((slug, int(chapter)), targets)

    def test_the_series_slug_matches_the_builder(self):
        from .management.commands.build_owb_book import SERIES_SLUG

        self.assertEqual(BIBLE_SERIES, SERIES_SLUG)

    def test_small(self):
        self.assertLess(BUNDLE.stat().st_size, 80 * 1024)


class ChapterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="owb", name="Open Word Bible")
        series = Series.objects.create(slug=BIBLE_SERIES, title="The Bible")
        self.psalms = Book.objects.create(
            author=author, slug="psalms", language="en", title="The Psalms",
            series=series, series_position=19,
        )
        for order, title in [(1, "Introduction"), (24, "Psalm 23"), (25, "Psalm 22")]:
            Chapter.objects.create(book=self.psalms, order=order, title=title, body_html="<p>x</p>")
        Book.objects.create(
            author=author, slug="gospel-of-john", language="en", title="John",
            series=series, series_position=43,
        )
        plain = Book.objects.create(author=author, slug="w", language="en", title="A Work")
        Chapter.objects.create(book=plain, order=24, title="Psalm 23", body_html="<p>x</p>")

    def _related(self, slug, order):
        res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/")
        self.assertEqual(res.status_code, 200)
        return res.data["related_passages"]

    def test_a_bible_chapter_lists_passages_in_published_bible_books(self):
        related = self._related("psalms", 24)
        self.assertTrue(related)
        # Only the books the library has: Psalms and John here.
        self.assertTrue({r["book"] for r in related} <= {"psalms", "gospel-of-john"})
        self.assertIn({"reference": "John 10:11", "book": "gospel-of-john", "order": 11}, related)

    def test_a_full_library_shows_a_short_row(self):
        from .bible_crossrefs import PER_CHAPTER, related_passages

        chapter = Chapter.objects.get(book=self.psalms, order=24)
        everything = lambda: frozenset(json.loads(gzip.decompress(BUNDLE.read_bytes()))["books"])  # noqa: E731
        self.assertEqual(len(related_passages(self.psalms, chapter, everything)), PER_CHAPTER)

    def test_the_editorial_chapters_and_a_drifted_title_have_none(self):
        self.assertEqual(self._related("psalms", 1), [])
        self.assertEqual(self._related("psalms", 25), [])

    def test_any_other_book_has_none(self):
        self.assertEqual(self._related("w", 24), [])

    def test_the_batch_agrees_with_the_single_endpoint(self):
        res = self.client.get("/api/library/books/psalms/chapters/?language=en")
        for chapter in res.data:
            self.assertEqual(chapter["related_passages"], self._related("psalms", chapter["order"]))
