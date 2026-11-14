"""Read alongside and Sermons on this chapter, on a Bible book and its chapters
(library/bible_companions.py, library/bible_sermons.sermons_on_chapter)."""

from django.test import SimpleTestCase, TestCase

from . import bible_companions
from .bible_companions import COMPANIONS, PASSAGES, title_chapters
from .models import Author, Book, Chapter, Series, Sermon


class TitleChaptersTests(SimpleTestCase):
    def test_reads_the_passage_a_companion_chapter_names(self):
        self.assertEqual(title_chapters("Romans 3", 45), (3,))
        self.assertEqual(title_chapters("Homily III: Romans 1:18", 45), (1,))
        self.assertEqual(title_chapters("John 1:29–51", 43), (1,))
        self.assertEqual(title_chapters("Homily I: 1 John 1:1–2:11", 62), (1, 2))
        self.assertEqual(title_chapters("The Vine (John 15:1)", 43), (15,))

    def test_names_no_chapter_for_a_title_on_the_whole_book_or_another(self):
        self.assertEqual(title_chapters("Homily I: The Gospel of Matthew", 40), ())
        self.assertEqual(title_chapters("Romans 9–16", 45), ())
        self.assertEqual(title_chapters("The Argument", 45), ())
        self.assertEqual(title_chapters("John 3", 45), ())
        self.assertEqual(title_chapters("", 45), ())

    def test_every_declared_work_ships_as_an_english_book(self):
        """A typo or a renamed book would silently drop from both shelves."""
        from .content_fixtures import book_fixture_path

        for slugs in COMPANIONS.values():
            for slug in slugs:
                self.assertTrue(book_fixture_path(slug, "en").exists(), slug)

    def test_every_passage_work_is_declared_on_its_book(self):
        for slug, (position, _) in PASSAGES.items():
            self.assertIn(slug, COMPANIONS[position], slug)


class ReadAlongsideTests(TestCase):
    def setUp(self):
        bible_companions._index.cache_clear()
        self.addCleanup(bible_companions._index.cache_clear)
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        series = Series.objects.create(slug="the-bible", title="The Bible")
        self.romans = Book.objects.create(
            author=owb, slug="romans", language="en", title="Romans",
            series=series, series_position=45, is_published=True,
        )
        for order, title in [(1, "Introduction"), (2, "Romans 1"), (9, "Romans 8"), (18, "Conclusion")]:
            Chapter.objects.create(book=self.romans, order=order, title=title, body_html="<p>x</p>")
        calvin = Author.objects.create(slug="john-calvin", name="John Calvin")
        chrys = Author.objects.create(slug="john-chrysostom", name="John Chrysostom")
        self.commentary = Book.objects.create(
            author=calvin, slug="commentary-on-romans", language="en",
            title="Commentary on Romans", is_published=True,
        )
        for order, title in [(1, "The Argument"), (2, "Romans 1"), (9, "Romans 8")]:
            Chapter.objects.create(book=self.commentary, order=order, title=title, body_html="<p>x</p>")
        homilies = Book.objects.create(
            author=chrys, slug="homilies-on-romans", language="en",
            title="Homilies on Romans", is_published=True,
        )
        for order, title in [(1, "Homily I: Romans 1:1, 2"), (14, "Homily XIII: Romans 7:14–8:2")]:
            Chapter.objects.create(book=homilies, order=order, title=title, body_html="<p>x</p>")
        # A catena: on the book's shelf, not in the chapter list (the chapter
        # page opens it verse by verse already).
        catena = Book.objects.create(
            author=calvin, slug="catena-on-romans", language="en",
            title="A Catena on Romans", is_published=True,
        )
        Chapter.objects.create(book=catena, order=9, title="Romans 8", body_html="<p>x</p>")

    def test_a_bible_book_lists_its_companions_in_declared_order(self):
        data = self.client.get("/api/library/books/romans/?language=en").json()
        self.assertEqual(
            [b["slug"] for b in data["read_alongside"]],
            ["commentary-on-romans", "homilies-on-romans", "catena-on-romans"],
        )
        self.assertEqual(data["read_alongside"][0]["author"]["name"], "John Calvin")

    def test_an_unpublished_companion_is_left_out(self):
        self.commentary.is_published = False
        self.commentary.save()
        data = self.client.get("/api/library/books/romans/?language=en").json()
        self.assertNotIn("commentary-on-romans", [b["slug"] for b in data["read_alongside"]])

    def test_any_other_book_has_none(self):
        data = self.client.get("/api/library/books/commentary-on-romans/?language=en").json()
        self.assertEqual(data["read_alongside"], [])

    def test_a_bible_chapter_lists_the_companion_chapters_on_it(self):
        data = self.client.get("/api/library/books/romans/chapters/9/?language=en").json()
        self.assertEqual(
            [(c["book"], c["order"], c["title"]) for c in data["read_alongside"]],
            [
                ("commentary-on-romans", 9, "Romans 8"),
                ("homilies-on-romans", 14, "Homily XIII: Romans 7:14–8:2"),
            ],
        )
        self.assertEqual(data["read_alongside"][0]["author_name"], "John Calvin")

    def test_an_unpublished_companion_drops_from_the_chapter_at_once(self):
        self.client.get("/api/library/books/romans/chapters/9/?language=en")  # warm the index
        self.commentary.is_published = False
        self.commentary.save()
        data = self.client.get("/api/library/books/romans/chapters/9/?language=en").json()
        self.assertEqual([c["book"] for c in data["read_alongside"]], ["homilies-on-romans"])

    def test_the_introduction_lists_none(self):
        data = self.client.get("/api/library/books/romans/chapters/1/?language=en").json()
        self.assertEqual(data["read_alongside"], [])
        self.assertIsNone(data["chapter_sermons"])


class SermonsOnChapterTests(TestCase):
    def setUp(self):
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        series = Series.objects.create(slug="the-bible", title="The Bible")
        john = Book.objects.create(
            author=owb, slug="gospel-of-john", language="en", title="John",
            series=series, series_position=43, is_published=True,
        )
        for order, title in [(1, "Introduction"), (3, "John 2"), (4, "John 3")]:
            Chapter.objects.create(book=john, order=order, title=title, body_html="<p>x</p>")
        cs = Author.objects.create(slug="cs", name="Charles Spurgeon")
        for slug, ref, published, language in [
            ("love", "John 3:16", True, "en"),
            ("born-again", "John 3:3", True, "en"),
            ("wedding", "John 2:1-11", True, "en"),
            ("night", "John 2:23-3:2", True, "en"),
            ("draft", "John 3:5", False, "en"),
            ("swahili", "John 3:16", True, "sw"),
            ("romans", "Romans 3:16", True, "en"),
        ]:
            Sermon.objects.create(
                author=cs, slug=slug, language=language, title=slug, scripture_ref=ref,
                body_html="<p>x</p>", is_published=published,
            )

    def test_lists_the_sermons_whose_text_is_in_the_chapter_in_verse_order(self):
        found = self.client.get("/api/library/books/gospel-of-john/chapters/4/?language=en").json()
        shelf = found["chapter_sermons"]
        self.assertEqual(shelf["book"], "John")
        self.assertEqual(shelf["count"], 3)
        # A text running on from John 2 counts in John 3 too, at its first verse there.
        self.assertEqual([s["slug"] for s in shelf["sermons"]], ["night", "born-again", "love"])

    def test_a_chapter_no_sermon_is_on_has_none(self):
        Sermon.objects.filter(scripture_ref__startswith="John 2").delete()
        found = self.client.get("/api/library/books/gospel-of-john/chapters/3/?language=en").json()
        self.assertIsNone(found["chapter_sermons"])
