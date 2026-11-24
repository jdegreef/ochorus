from django.test import TestCase

from .chapter_urls import chapter_segment
from .models import Author, Book, Chapter, Series


class ChapterSegmentTests(TestCase):
    """The backend's chapter links agree with the frontend's ``chapterSegment``:
    a Bible book's follow the Bible's numbering (bug #15)."""

    def setUp(self):
        author = Author.objects.create(slug="open-word-bible", name="Open Word Bible")
        bible = Series.objects.create(slug="the-bible", title="The Bible")
        ruth = Book.objects.create(author=author, slug="ruth", language="en", title="Ruth", series=bible)
        titles = ["Introduction", "Ruth 1", "Ruth 2", "Ruth 3", "Ruth 4", "Conclusion"]
        for order, title in enumerate(titles, start=1):
            Chapter.objects.create(book=ruth, order=order, title=title, body_html="<p>x</p>")
        Book.objects.create(author=author, slug="humility", language="en", title="Humility")

    def test_a_bible_book_is_numbered_as_the_bible_is(self):
        self.assertEqual(chapter_segment("ruth", 1), "introduction")
        self.assertEqual(chapter_segment("ruth", 2), "1")
        self.assertEqual(chapter_segment("ruth", 5), "4")
        self.assertEqual(chapter_segment("ruth", 6), "conclusion")

    def test_every_other_book_keeps_its_order(self):
        self.assertEqual(chapter_segment("humility", 3), "3")
