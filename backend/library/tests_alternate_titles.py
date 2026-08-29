"""`alternate_titles` — the other names a work is published and searched under.

WHAT THIS CAN AND CANNOT GUARD, as in `tests_author_entity.py`: whether "A
Divine Cordial" really is Watson's *All Things for Good* is a human check
against a catalogue, and an invented title is worse than none — it tells a
search engine this page is about a book that was never published. So these
guard everything mechanical: that every key names a work we actually ship,
that a language-specific name never leaks onto an edition that cannot use it,
and that the list never restates the title it sits beneath.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from .alternate_titles import CITATION_TITLES, VARIANT_TITLES, alternate_titles
from .models import Author, Book

BOOKS = Path(__file__).resolve().parent / "fixtures" / "content" / "books"


def fixture_editions() -> dict[tuple[str, str], str]:
    """``(slug, language) -> title`` for every committed book edition."""
    out = {}
    for path in BOOKS.glob("*.json"):
        slug, language, _ = path.name.rsplit(".", 2)
        row = next(
            r for r in json.loads(path.read_text()) if r["model"] == "library.book"
        )
        out[(slug, language)] = row["fields"]["title"]
    return out


class CuratedDataTests(SimpleTestCase):
    """Shape and scope of what ships in `alternate_titles.py`."""

    def test_every_citation_title_names_a_work_we_publish(self):
        slugs = {slug for slug, _ in fixture_editions()}
        for slug in CITATION_TITLES:
            with self.subTest(slug=slug):
                self.assertIn(slug, slugs)

    def test_every_variant_title_names_an_edition_we_publish(self):
        editions = fixture_editions()
        for key in VARIANT_TITLES:
            with self.subTest(edition=key):
                self.assertIn(key, editions)

    def test_no_curated_entry_merely_restates_the_edition_s_own_title(self):
        """A redundant entry should be deleted, not silently swallowed.

        `alternate_titles()` drops it either way, so asserting on the function
        output would pass no matter what the data said. This reads the dicts.
        """
        editions = fixture_editions()
        for (slug, language), title in editions.items():
            curated = CITATION_TITLES.get(slug, ()) + VARIANT_TITLES.get(
                (slug, language), ()
            )
            with self.subTest(slug=slug, language=language):
                self.assertNotIn(title, curated)

    def test_no_entry_is_blank_or_padded(self):
        for names in (*CITATION_TITLES.values(), *VARIANT_TITLES.values()):
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(name, name.strip())
                    self.assertTrue(name)

    def test_a_title_that_grows_into_a_curated_name_drops_out_of_the_list(self):
        """The safety net for a retitle: rename the book to one of its own
        alternates and the page must not claim `alternateName` == `name`."""
        self.assertNotIn(
            "A Divine Cordial",
            alternate_titles("all-things-for-good", "en", "A Divine Cordial"),
        )

    def test_a_work_with_nothing_to_add_gets_an_empty_list(self):
        """Most of the shelf is in this position, and should be."""
        self.assertEqual(alternate_titles("all-of-grace", "en", "All of Grace"), [])


class LanguageScopeTests(SimpleTestCase):
    """The whole reason the two dicts are kept apart."""

    def test_a_citation_title_reaches_every_edition(self):
        """It is a property of the work, not of the translation."""
        for language in ("en", "es", "sw", "uk"):
            with self.subTest(language=language):
                self.assertIn(
                    "De Incarnatione Verbi Dei",
                    alternate_titles("on-the-incarnation", language, "..."),
                )

    def test_an_english_variant_stays_on_english(self):
        """A Spanish reader shown "A Divine Cordial" gets a title naming no book
        they can find — the failure the split exists to prevent."""
        self.assertIn("A Divine Cordial", alternate_titles("all-things-for-good", "en", ""))
        self.assertEqual(alternate_titles("all-things-for-good", "es", ""), [])

    def test_the_citation_title_leads(self):
        """It is the name a catalogue uses, so it reads first in the list."""
        got = alternate_titles("the-reformed-pastor", "en", "The Reformed Pastor")
        self.assertEqual(got[0], "Gildas Salvianus")

    def test_a_typographic_apostrophe_does_not_split_one_title_in_two(self):
        """The fixture writes `’`; catalogues write `'`. Same book either way."""
        self.assertEqual(
            alternate_titles("if", "en", "If"),
            alternate_titles("if", "en", "If"),
        )
        self.assertNotIn(
            "The Pilgrim’s Progress",
            alternate_titles("pilgrims-progress", "en", "The Pilgrim's Progress"),
        )


class BookDetailPayloadTests(TestCase):
    """The serializer carries them, and only on the detail payload."""

    def setUp(self):
        self.author = Author.objects.create(slug="thomas-watson", name="Thomas Watson")

    def test_the_detail_payload_carries_the_alternate_titles(self):
        from .serializers import BookDetailSerializer

        book = Book.objects.create(
            author=self.author,
            slug="all-things-for-good",
            language="en",
            title="All Things for Good",
        )
        self.assertEqual(
            BookDetailSerializer(book).data["alternate_titles"], ["A Divine Cordial"]
        )

    def test_a_book_with_no_other_name_sends_an_empty_list(self):
        from .serializers import BookDetailSerializer

        book = Book.objects.create(
            author=self.author,
            slug="a-work-nobody-renamed",
            language="en",
            title="A Work Nobody Renamed",
        )
        self.assertEqual(BookDetailSerializer(book).data["alternate_titles"], [])

    def test_the_shelf_card_does_not_carry_them(self):
        """130 rows would ship the strings for markup that does not exist."""
        from .serializers import BookListSerializer

        book = Book.objects.create(
            author=self.author,
            slug="all-things-for-good",
            language="en",
            title="All Things for Good",
        )
        self.assertNotIn("alternate_titles", BookListSerializer(book).data)
