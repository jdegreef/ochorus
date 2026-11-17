"""The overview card on a Bible book's page (library/bible_overview.py)."""

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from .bible_overview import DIR, FIELDS, _trim_quotes, overview, table
from .models import Author, Book, Series
from .scripture import book_of

FIXTURE = Path(__file__).parent / "fixtures" / "content" / "books"


def bible_books() -> dict[str, int]:
    """{slug: canonical position} of every Bible book the fixture ships."""
    out = {}
    for path in FIXTURE.glob("*.en.json"):
        fields = json.loads(path.read_text("utf-8"))[0]["fields"]
        if fields.get("series") == ["the-bible"]:
            out[fields["slug"]] = fields["series_position"]
    return out


class OverviewDataTests(SimpleTestCase):
    def test_every_one_of_the_66_books_has_a_complete_overview(self):
        books = bible_books()
        self.assertEqual(len(books), 66)
        self.assertEqual(set(table()), set(books))
        for slug, meta in table().items():
            with self.subTest(slug):
                self.assertEqual(set(meta), set(FIELDS))
                for field in FIELDS:
                    self.assertTrue(meta[field].strip(), field)
                self.assertLessEqual(len(meta["theme"]), 90)
                self.assertTrue(meta["theme"].endswith("."))

    def test_every_editorial_file_carries_one(self):
        self.assertEqual(len(list(DIR.glob("*/book.json"))), 66)

    def test_every_key_verse_resolves_in_its_own_book(self):
        for slug, position in bible_books().items():
            with self.subTest(slug):
                card = overview(slug)
                verse = card["key_verse"]
                self.assertIsNotNone(verse, "the Bible lookup cannot resolve it")
                self.assertEqual(
                    book_of(verse["reference"].replace("–", "-"))[1], position
                )
                # A whole sentence from the Open Word Bible, not a fragment.
                self.assertRegex(verse["text"], r"[.!?]['’\"”]{0,2}$")
                self.assertLessEqual(len(verse["text"]), 320)
                self.assertGreaterEqual(verse["chapter"], 1)
                self.assertGreaterEqual(verse["verse"], 1)

    def test_romans_quotes_its_key_verse_live(self):
        card = overview("romans")
        self.assertEqual(card["author"], "Paul")
        self.assertEqual(card["key_verse"]["reference"], "Romans 1:16")
        self.assertEqual(
            (card["key_verse"]["chapter"], card["key_verse"]["verse"]), (1, 16)
        )
        self.assertIn("not ashamed of the gospel", card["key_verse"]["text"])

    def test_a_range_is_quoted_whole(self):
        text = overview("ephesians")["key_verse"]["text"]
        self.assertIn("saved, through faith", text)  # 2:8
        self.assertIn("no room for anyone to boast", text)  # 2:9

    def test_an_unpaired_edge_quote_is_dropped_and_an_inner_one_kept(self):
        self.assertEqual(_trim_quotes('a ransom for many."'), "a ransom for many.")
        self.assertEqual(_trim_quotes('"I am the LORD.'), "I am the LORD.")
        self.assertEqual(_trim_quotes('Ruth said, "Stop.'), 'Ruth said, "Stop.')
        self.assertEqual(_trim_quotes('He said, "Go."'), 'He said, "Go."')


class OverviewApiTests(TestCase):
    def setUp(self):
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        bible = Series.objects.create(slug="the-bible", title="The Bible")
        Book.objects.create(
            author=owb,
            slug="romans",
            language="en",
            title="Romans",
            series=bible,
            series_position=45,
            is_published=True,
        )
        Book.objects.create(
            author=owb,
            slug="anchored",
            language="en",
            title="Anchored",
            is_published=True,
        )
        # Same slug, outside the Bible series: no card.
        Book.objects.create(
            author=owb, slug="romans", language="sw", title="Warumi", is_published=True
        )

    def detail(self, slug, language="en"):
        return self.client.get(f"/api/library/books/{slug}/?language={language}").json()

    def test_a_bible_book_carries_its_card(self):
        card = self.detail("romans")["bible_overview"]
        self.assertEqual(card["date"], "c. AD 57")
        self.assertEqual(card["key_verse"]["reference"], "Romans 1:16")
        self.assertTrue(card["theme"])

    def test_null_on_every_other_book(self):
        self.assertIsNone(self.detail("anchored")["bible_overview"])
        self.assertIsNone(self.detail("romans", "sw")["bible_overview"])
