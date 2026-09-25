"""The /originals shelf — the house imprint's own page (``OriginalsView``).

Pinned here: only the imprint's published books in the requested language;
series grouped in volume order, and only where the series has a name in that
language (no English fallback, the ``Series.title_for`` rule); and the
per-language counts the page uses to point readers at their own editions.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import body_of

from .models import Author, Book, Chapter, Series, SeriesTranslation


class OriginalsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.imprint = Author.objects.create(
            slug="ochorus-originals", name="Ochorus Originals", is_imprint=True
        )
        self.person = Author.objects.create(slug="john-bunyan", name="John Bunyan")
        self.series = Series.objects.create(
            slug="brave-for-god", title="Brave for God", description="True stories."
        )
        SeriesTranslation.objects.create(
            series=self.series, language="sw", title="Jasiri kwa ajili ya Mungu"
        )

    def _book(self, slug, *, language="en", author=None, series=None, position=None,
              published=True):
        book = Book.objects.create(
            author=author or self.imprint, slug=slug, language=language, title=slug,
            series=series, series_position=position, is_published=published,
        )
        Chapter.objects.create(book=book, order=1, title="One", body_html=body_of(40))
        return book

    def _get(self, language="en"):
        res = self.client.get(f"/api/library/originals/?language={language}")
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_lists_only_the_imprints_published_books_in_the_language(self):
        self._book("a-hidden-fire")
        self._book("draft", published=False)
        self._book("pilgrims-progress", author=self.person)
        self._book("a-hidden-fire", language="sw")
        body = self._get()
        self.assertEqual([b["slug"] for b in body["books"]], ["a-hidden-fire"])
        self.assertEqual(body["books"][0]["language"], "en")
        # A card, like every other shelf: the word count drives the read time.
        self.assertIn("word_count", body["books"][0])

    def test_groups_a_series_in_volume_order(self):
        self._book("brave-for-god-2", series=self.series, position=2)
        self._book("brave-for-god", series=self.series, position=1)
        self._book("tukutendereza")
        body = self._get()
        self.assertEqual(
            body["series"],
            [
                {
                    "slug": "brave-for-god",
                    "title": "Brave for God",
                    "description": "True stories.",
                    "books": ["brave-for-god", "brave-for-god-2"],
                }
            ],
        )

    def test_an_unnamed_series_leaves_its_books_standing_alone(self):
        rooted = Series.objects.create(slug="rooted", title="Rooted")
        self._book("brave-for-god", language="sw", series=self.series, position=1)
        self._book("rooted-1", language="sw", series=rooted, position=1)
        body = self._get("sw")
        # Both books are on the shelf; only the series named in Swahili groups.
        self.assertEqual(len(body["books"]), 2)
        self.assertEqual([s["slug"] for s in body["series"]], ["brave-for-god"])
        self.assertEqual(body["series"][0]["title"], "Jasiri kwa ajili ya Mungu")

    def test_counts_the_imprints_books_in_every_language(self):
        self._book("a")
        self._book("b")
        self._book("a", language="sw")
        self._book("c", language="lg", published=False)
        self._book("pilgrims-progress", language="fr", author=self.person)
        body = self._get()
        self.assertEqual(
            body["languages"], [{"code": "en", "count": 2}, {"code": "sw", "count": 1}]
        )
