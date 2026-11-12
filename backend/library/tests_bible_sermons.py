"""The "Sermons on this book" shelf on a Bible book's page (library/bible_sermons.py)."""

from django.test import TestCase

from .models import Author, Book, Series, Sermon


class BibleSermonsTests(TestCase):
    def setUp(self):
        owb = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        bible = Series.objects.create(slug="the-bible", title="The Bible")
        self.psalms = Book.objects.create(
            author=owb, slug="psalms", language="en", title="The Psalms",
            series=bible, series_position=19, is_published=True,
        )
        self.john = Book.objects.create(
            author=owb, slug="gospel-of-john", language="en", title="John",
            series=bible, series_position=43, is_published=True,
        )
        other = Series.objects.create(slug="anchored", title="Anchored")
        self.classic = Book.objects.create(
            author=owb, slug="anchored-1", language="en", title="Anchored",
            series=other, series_position=19, is_published=True,
        )
        cs = Author.objects.create(slug="cs", name="Charles Spurgeon")

        def sermon(slug, ref, title=None, published=True, language="en"):
            Sermon.objects.create(
                author=cs, slug=slug, language=language, title=title or slug,
                scripture_ref=ref, body_html="<p>x</p>", is_published=published,
            )

        sermon("shepherd", "Psalm 23:1", title="The Shepherd")
        sermon("blessed", "Psalm 1", title="Blessed")
        sermon("deep", "Psalms 42:7")
        sermon("draft", "Psalm 51", published=False)
        sermon("swahili", "Psalm 90", language="sw")
        sermon("love", "John 3:16")
        sermon("no-text", "")

    def detail(self, slug):
        return self.client.get(f"/api/library/books/{slug}/?language=en").json()

    def test_lists_the_sermons_whose_text_is_in_the_book_in_canon_order(self):
        shelf = self.detail("psalms")["bible_sermons"]
        self.assertEqual(shelf["book"], "Psalms")
        self.assertEqual(shelf["count"], 3)
        # Psalm 1 before Psalm 23 before Psalm 42; unpublished and other
        # languages left out; full sermon cards for the shared SermonCard.
        self.assertEqual([s["slug"] for s in shelf["sermons"]], ["blessed", "shepherd", "deep"])
        self.assertEqual(shelf["sermons"][0]["author"]["slug"], "cs")
        self.assertIn("summary", shelf["sermons"][0])

    def test_caps_the_shelf_but_counts_them_all(self):
        cs = Author.objects.get(slug="cs")
        for n in range(2, 10):
            Sermon.objects.create(
                author=cs, slug=f"p{n}", language="en", title=f"P{n}",
                scripture_ref=f"Psalm {n + 100}", body_html="<p>x</p>", is_published=True,
            )
        shelf = self.detail("psalms")["bible_sermons"]
        self.assertEqual(shelf["count"], 11)
        self.assertEqual(len(shelf["sermons"]), 6)

    def test_null_off_the_bible_and_where_no_sermon_treats_the_book(self):
        # Same series_position as Psalms, but not a book of the Bible.
        self.assertIsNone(self.detail("anchored-1")["bible_sermons"])
        Sermon.objects.filter(slug="love").delete()
        self.assertIsNone(self.detail("gospel-of-john")["bible_sermons"])
