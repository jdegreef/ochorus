"""Quotations as search results (library/search_quotes.py)."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Quote, Sermon


class QuoteSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="Charles H. Spurgeon")
        book = Book.objects.create(author=murray, slug="with-christ", language="en", title="With Christ")
        Book.objects.create(author=spurgeon, slug="all-of-grace", language="en", title="All of Grace")
        chapter = Chapter.objects.create(book=book, order=3, title="Lesson", body_html="<p>a</p>")
        sermon = Sermon.objects.create(
            author=spurgeon, slug="the-power-of-prayer", language="en",
            title="The Power of Prayer", body_html="<p>a</p>",
        )
        rows = [
            ("andrew-murray-a", murray, "A heart full of God has power for the prayer of faith.", chapter, None),
            ("andrew-murray-b", murray, "Humility before God is nothing if not proved before men.", chapter, None),
            ("charles-h-spurgeon-a", spurgeon, "One prayer from the soul is better than a myriad cold readings.", None, sermon),
        ]
        for slug, author, text, ch, ser in rows:
            Quote.objects.create(
                slug=slug, author=author, text=text, chapter=ch, sermon=ser, paragraph=2, reviewed=True
            )
        Quote.objects.create(
            slug="andrew-murray-hidden", author=murray, text="An unreviewed line on prayer.",
            chapter=chapter, paragraph=4, reviewed=False,
        )

    def search(self, q, language="en", **params):
        res = self.client.get("/api/library/search/", {"q": q, "language": language, **params})
        return res.data

    def quotes(self, q, **params):
        return [h for h in self.search(q, **params)["results"] if h["type"] == "quote"]

    def test_a_word_finds_the_lines_that_say_it_reviewed_only(self):
        found = self.quotes("prayer")
        self.assertEqual(
            sorted(h["quote_slug"] for h in found), ["andrew-murray-a", "charles-h-spurgeon-a"]
        )
        self.assertIn("⟦prayer⟧", found[0]["snippet"])
        self.assertEqual(self.search("prayer")["totals"]["quote"], 2)

    def test_a_prefix_of_four_letters_finds_the_word(self):
        self.assertEqual([h["quote_slug"] for h in self.quotes("humil")], ["andrew-murray-b"])

    def test_quoting_a_line_word_for_word_marks_it_as_a_phrase(self):
        found = self.quotes("a heart full of god")
        self.assertEqual(found[0]["quote_slug"], "andrew-murray-a")
        self.assertTrue(found[0]["phrase"])
        self.assertNotIn("phrase", self.quotes("faith heart")[0])

    def test_a_writer_and_a_theme_finds_that_writers_lines(self):
        self.assertEqual(
            [h["quote_slug"] for h in self.quotes("spurgeon quotes on prayer")],
            ["charles-h-spurgeon-a"],
        )
        source = self.quotes("spurgeon prayer")[0]["source"]
        self.assertEqual((source["kind"], source["slug"]), ("sermon", "the-power-of-prayer"))

    def test_only_common_words_find_nothing(self):
        self.assertEqual(self.quotes("the of god"), [])

    def test_english_only_and_the_tab_pages_them(self):
        self.assertEqual(
            [h for h in self.search("prayer", language="es")["results"] if h["type"] == "quote"], []
        )
        page = self.search("prayer", type="quote")["results"]
        self.assertEqual(len(page), 2)

    def test_a_scope_narrows_them(self):
        found = self.quotes("prayer", **{"in": "author:andrew-murray"})
        self.assertEqual([h["quote_slug"] for h in found], ["andrew-murray-a"])
        self.assertEqual(self.quotes("prayer", **{"in": "book:all-of-grace"}), [])
