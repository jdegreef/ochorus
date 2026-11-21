"""Typo forgiveness: a misspelt word is searched as typed AND as corrected to
the title word it is one slip from, and the response says so."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter
from .search import correction


class CorrectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        humility = Book.objects.create(
            author=murray, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=humility, order=1, title="The Glory of the Creature",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )
        prayer = Book.objects.create(
            author=murray, slug="prayer", language="en", title="The Ministry of Intercession"
        )
        Chapter.objects.create(
            book=prayer, order=1, title="One", body_html="<p>Prayer moves the hand of God.</p>",
        )
        Book.objects.create(author=murray, slug="oracion", language="es", title="La oración")

    def get(self, q, language="en"):
        res = self.client.get("/api/library/search/", {"q": q, "language": language})
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_a_misspelt_title_word_is_corrected(self):
        self.assertEqual(correction("humilty", "en"), "humility")
        self.assertEqual(correction("Humilty prayer", "en"), "humility prayer")

    def test_real_words_and_short_words_are_left_alone(self):
        self.assertIsNone(correction("humility", "en"))
        self.assertIsNone(correction("hand", "en"))  # occurs in the text
        self.assertIsNone(correction("humi", "en"))  # nothing close enough
        self.assertIsNone(correction("-humilty", "en"))  # an exclusion stays as typed

    def test_a_title_word_typed_without_accents(self):
        self.assertEqual(correction("oracion", "es"), "oración")

    def test_the_search_finds_the_corrected_word_and_says_so(self):
        data = self.get("humilty")
        self.assertIn("humility", {h.get("book_slug") for h in data["results"]})
        self.assertEqual(data["also_searched_for"], "humility")
        # A correctly spelt search says nothing extra.
        self.assertNotIn("also_searched_for", self.get("humility"))
