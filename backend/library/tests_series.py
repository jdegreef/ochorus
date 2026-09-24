"""`series_block` — the book page's "Book 2 of 6 in Rooted" line and the last
chapter's "next in series", from `Book.series` / `series_position`.

Pinned here: the no-English-fallback rule (an unnamed series shows nothing),
that "of N" counts the SERIES' volume numbers rather than this language's rows,
that previous/next skip a volume this language lacks, and that a collection
(no positions) has no previous or next at all.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Author, Book, Series, SeriesTranslation
from .serializers import BookDetailSerializer, series_block


class SeriesBlockTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(slug="brave-for-god", title="Brave for God")

    def _book(self, slug, position, *, language="en", published=True, series=None):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=f"{slug} [{language}]",
            series=series or self.series, series_position=position,
            is_published=published,
        )

    def test_a_middle_volume_knows_its_neighbours_and_the_total(self):
        self._book("bfg-1", 1)
        two = self._book("bfg-2", 2)
        self._book("bfg-3", 3)
        self.assertEqual(
            series_block(two),
            {
                "slug": "brave-for-god",
                "title": "Brave for God",
                "position": 2,
                "total": 3,
                "previous": {"slug": "bfg-1", "title": "bfg-1 [en]"},
                "next": {"slug": "bfg-3", "title": "bfg-3 [en]"},
            },
        )

    def test_the_last_volume_has_no_next(self):
        self._book("bfg-1", 1)
        last = self._book("bfg-2", 2)
        self.assertIsNone(series_block(last)["next"])

    def test_no_series_is_no_block(self):
        book = Book.objects.create(author=self.author, slug="solo", title="Solo")
        self.assertIsNone(series_block(book))

    def test_an_unnamed_series_shows_nothing_in_that_language(self):
        # No English fallback: a Swahili reader is not shown an English name.
        sw = self._book("bfg-1", 1, language="sw")
        self.assertIsNone(series_block(sw))
        SeriesTranslation.objects.create(
            series=self.series, language="sw", title="Jasiri kwa ajili ya Mungu"
        )
        self.assertEqual(series_block(sw)["title"], "Jasiri kwa ajili ya Mungu")

    def test_next_skips_a_volume_this_language_lacks_but_the_total_does_not(self):
        SeriesTranslation.objects.create(series=self.series, language="lg", title="Abavumu")
        for n in (1, 2, 3):
            self._book(f"bfg-{n}", n)
        one = self._book("bfg-1", 1, language="lg")
        self._book("bfg-3", 3, language="lg")  # no Luganda volume 2 yet
        block = series_block(one)
        self.assertEqual(block["next"], {"slug": "bfg-3", "title": "bfg-3 [lg]"})
        self.assertEqual(block["total"], 3)

    def test_unpublished_volumes_are_neither_linked_nor_counted(self):
        one = self._book("bfg-1", 1)
        self._book("bfg-2", 2, published=False)
        block = series_block(one)
        self.assertIsNone(block["next"])
        self.assertEqual(block["total"], 1)

    def test_a_collection_counts_its_books_and_has_no_order(self):
        collection = Series.objects.create(slug="key-teachings", title="The Key Teachings")
        nee = self._book("kt-nee", None, series=collection)
        self._book("kt-baxter", None, series=collection)
        block = series_block(nee)
        self.assertEqual(
            (block["position"], block["total"], block["previous"], block["next"]),
            (None, 2, None, None),
        )

    def test_the_detail_payload_carries_it(self):
        book = self._book("bfg-1", 1)
        self.assertEqual(BookDetailSerializer(book).data["series"]["position"], 1)
