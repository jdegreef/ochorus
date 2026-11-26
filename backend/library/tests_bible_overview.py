"""The overview card on a Bible book's page (library/bible_overview.py)."""

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from . import bible_overview
from .bible_overview import FIELDS, OVERVIEWS, overview, table, trim_borrowed_quotes
from .models import Author, Book, Chapter, Series
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


class OverviewDataTests(TestCase):
    def setUp(self):
        bible_overview.key_verse.cache_clear()
        self.addCleanup(bible_overview.key_verse.cache_clear)

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

    def test_the_data_file_lists_the_books_in_canonical_order(self):
        books = bible_books()
        self.assertEqual(list(OVERVIEWS), sorted(books, key=books.get))

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
                # No reader chapters in this database: no anchor to promise.
                self.assertIsNone(verse["verse"])
                # Set as the reader sets it: no straight double quotes.
                self.assertNotIn('"', verse["text"])

    def test_romans_quotes_its_key_verse_live(self):
        card = overview("romans")
        self.assertEqual(card["author"], "Paul")
        self.assertEqual(card["key_verse"]["reference"], "Romans 1:16")
        self.assertEqual(card["key_verse"]["chapter"], 1)
        self.assertIn("not ashamed of the gospel", card["key_verse"]["text"])

    def test_a_range_is_quoted_whole(self):
        text = overview("ephesians")["key_verse"]["text"]
        self.assertIn("saved, through faith", text)  # 2:8
        self.assertIn("no room for anyone to boast", text)  # 2:9

    def test_quotes_are_curled_as_the_reader_curls_them(self):
        text = overview("exodus")["key_verse"]["text"]
        self.assertIn("“", text)
        self.assertNotIn('"', text)


class TrimBorrowedQuotesTests(SimpleTestCase):
    def test_a_closer_from_an_earlier_verse_goes(self):
        self.assertEqual(trim_borrowed_quotes("a ransom for many.”"), "a ransom for many.")

    def test_an_opener_left_last_goes(self):
        self.assertEqual(trim_borrowed_quotes("And he said, “"), "And he said,")

    def test_paired_marks_stay_wherever_the_stray_one_is(self):
        # The stray closer is the last mark; the paired speech before it stays.
        self.assertEqual(
            trim_borrowed_quotes("“Go,” he said, “for I am with you.” for many.”"),
            "“Go,” he said, “for I am with you.” for many.",
        )
        self.assertEqual(trim_borrowed_quotes("He said, “Go.”"), "He said, “Go.”")

    def test_a_speech_that_runs_on_keeps_its_opening_mark(self):
        self.assertEqual(trim_borrowed_quotes("Ruth said, “Stop."), "Ruth said, “Stop.")


class KeyVerseAnchorTests(TestCase):
    def setUp(self):
        bible_overview.key_verse.cache_clear()
        self.addCleanup(bible_overview.key_verse.cache_clear)
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        self.book = Book.objects.create(
            author=owb, slug="romans", language="en", title="Romans", is_published=True
        )

    def test_links_the_verse_where_the_reader_prints_its_number(self):
        Chapter.objects.create(
            book=self.book, order=2, title="Romans 1",
            body_html='<p><sup class="v" id="v16">16</sup>I am not ashamed.</p>',
        )
        self.assertEqual(overview("romans")["key_verse"]["verse"], 16)

    def test_links_the_chapter_where_it_does_not(self):
        # A verse inside a range ("15–16" carries only v15) or printed in the
        # chapter before has no anchor here: the card opens the chapter's top.
        Chapter.objects.create(
            book=self.book, order=2, title="Romans 1",
            body_html='<p><sup class="v" id="v15">15–16</sup>I am not ashamed.</p>',
        )
        self.assertIsNone(overview("romans")["key_verse"]["verse"])


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


class OtherLanguageOverviewTests(TestCase):
    """A Bible edition in another language gets the card in its own words, its
    key verse from that language's OWB, and no English anywhere."""

    def setUp(self):
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        bible = Series.objects.create(slug="the-bible", title="The Bible")
        for lang, title in [("es", "Romanos"), ("fr", "Romains"), ("pt", "Romanos"), ("sw", "Warumi"), ("am", "ሮሜ")]:
            book = Book.objects.create(
                author=owb, slug="romans", language=lang, title=title,
                series=bible, series_position=45, is_published=True,
            )
            Chapter.objects.create(
                book=book, order=2, title=f"{title} 1",
                body_html='<p><sup class="v" id="v16">16</sup>x</p>',
            )
        # A Bible edition in a language with no overview words: no card.
        Book.objects.create(
            author=owb, slug="romans", language="ko", title="로마서",
            series=bible, series_position=45, is_published=True,
        )

    def detail(self, language):
        return self.client.get(f"/api/library/books/romans/?language={language}").json()["bible_overview"]

    def test_each_language_has_its_own_card(self):
        from .bible_overview import OVERVIEWS, words
        from .scripture import owb_verse

        for lang, name in [("es", "Romanos"), ("fr", "Romains"), ("pt", "Romanos"), ("sw", "Warumi"), ("am", "ሮሜ")]:
            with self.subTest(lang):
                card = self.detail(lang)
                self.assertEqual(card["theme"], words(lang)["romans"]["theme"])
                self.assertNotEqual(card["theme"], OVERVIEWS["romans"]["theme"])
                self.assertEqual(card["key_verse"]["reference"], f"{name} 1:16")
                self.assertEqual(card["key_verse"]["verse"], 16)
                self.assertIn(owb_verse(45001016, lang)[1][:20], card["key_verse"]["text"])

    def test_a_language_without_words_has_no_card(self):
        self.assertIsNone(self.detail("ko"))

    def test_every_language_file_covers_the_66_books(self):
        from .bible_overview import OVERVIEWS, words

        for lang in ("es", "fr", "pt", "sw", "am"):
            with self.subTest(lang):
                self.assertEqual(list(words(lang)), list(OVERVIEWS))
                for slug, card in words(lang).items():
                    self.assertEqual(set(card), {"author", "date", "theme"}, slug)
                    self.assertTrue(all(v.strip() for v in card.values()), slug)


class SwahiliOverviewTests(TestCase):
    """Every Swahili Bible book's card: its words, and a key verse quoted from
    the Swahili OWB under the edition's own book name."""

    def setUp(self):
        bible_overview.key_verse.cache_clear()
        self.addCleanup(bible_overview.key_verse.cache_clear)
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        self.names = {}
        for path in FIXTURE.glob("*.sw.json"):
            rows = json.loads(path.read_text("utf-8"))
            if rows[0]["fields"].get("series") != ["the-bible"]:
                continue
            slug = rows[0]["fields"]["slug"]
            book = Book.objects.create(
                author=owb, slug=slug, language="sw", title=rows[0]["fields"]["title"],
                is_published=True,
            )
            for row in rows[1:]:
                Chapter.objects.create(
                    book=book, order=row["fields"]["order"], title=row["fields"]["title"],
                    body_html=row["fields"]["body_html"],
                )
            self.names[slug] = rows[2]["fields"]["title"].rsplit(" ", 1)[0]

    def test_every_book_has_a_swahili_card_with_a_resolving_key_verse(self):
        self.assertEqual(set(self.names), set(OVERVIEWS))
        for slug, meta in OVERVIEWS.items():
            with self.subTest(slug):
                card = overview(slug, "sw")
                self.assertIsNotNone(card)
                verse = card["key_verse"]
                self.assertIsNotNone(verse, "the Swahili OWB cannot resolve it")
                # The reference reads in Swahili: the edition's book name, the
                # English chapter and verse.
                english_ref = meta["key_verse"].rsplit(" ", 1)[1]
                self.assertEqual(verse["reference"], f"{self.names[slug]} {english_ref}")
                self.assertTrue(verse["text"].strip())
                self.assertNotIn('"', verse["text"])
                self.assertNotEqual(card["theme"], meta["theme"])
                self.assertTrue(card["theme"].endswith("."))


def bible_editions(language: str) -> list[list[dict]]:
    """Every Bible book the fixture ships in ``language``: its rows (book first)."""
    out = []
    for path in sorted(FIXTURE.glob(f"*.{language}.json")):
        rows = json.loads(path.read_text("utf-8"))
        if rows[0]["fields"].get("series") == ["the-bible"]:
            out.append(rows)
    return out


class AmharicOverviewTests(TestCase):
    """Every Amharic Bible book's card: its words, and a key verse quoted from
    the Amharic OWB under the edition's own book name, in « » as its reader
    prints it."""

    def setUp(self):
        bible_overview.key_verse.cache_clear()
        self.addCleanup(bible_overview.key_verse.cache_clear)
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        self.names = {}
        for rows in bible_editions("am"):
            slug = rows[0]["fields"]["slug"]
            book = Book.objects.create(
                author=owb, slug=slug, language="am", title=rows[0]["fields"]["title"],
                is_published=True,
            )
            for row in rows[1:]:
                Chapter.objects.create(
                    book=book, order=row["fields"]["order"], title=row["fields"]["title"],
                    body_html=row["fields"]["body_html"],
                )
            self.names[slug] = rows[2]["fields"]["title"].rsplit(" ", 1)[0]

    def test_every_book_has_an_amharic_card_with_a_resolving_key_verse(self):
        self.assertEqual(set(self.names), set(OVERVIEWS))
        for slug, meta in OVERVIEWS.items():
            with self.subTest(slug):
                card = overview(slug, "am")
                self.assertIsNotNone(card)
                verse = card["key_verse"]
                self.assertIsNotNone(verse, "the Amharic OWB cannot resolve it")
                # The reference reads in Amharic: the edition's book name, the
                # English chapter and verse.
                english_ref = meta["key_verse"].rsplit(" ", 1)[1]
                self.assertEqual(verse["reference"], f"{self.names[slug]} {english_ref}")
                self.assertTrue(verse["text"].strip())
                self.assertNotIn('"', verse["text"])
                self.assertNotEqual(card["theme"], meta["theme"])
                self.assertTrue(card["theme"].endswith("።"))
