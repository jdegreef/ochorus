"""A Book or Sermon can't be saved with a title that shows a reader nothing.

A Spurgeon book reached production with a blank title: the admin coverage
matrix drew it as just its author's name, still offering to queue translations
of it. The fixture gate (tests_fixture) only covers content that comes from the
fixture, and some forty other paths write these rows, so the rule lives in the
models' save(). These tests pin it there, plus the import endpoint's matching
check, so the admin gets a 400 rather than a 500.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import Author, Book, Sermon
from .text import is_blank_title

# Each renders as nothing; the last three survive str.strip().
BLANKS = ("", "   ", "\n\t", "​", " ﻿ ", "​⁠­")


class IsBlankTitleTests(SimpleTestCase):
    def test_invisible_titles_are_blank(self):
        for t in (*BLANKS, None):
            with self.subTest(t=t):
                self.assertTrue(is_blank_title(t))

    def test_real_titles_are_not(self):
        for t in ("Humility", " Abide in Christ ", "É", "​Grace"):
            with self.subTest(t=t):
                self.assertFalse(is_blank_title(t))


class SaveGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")

    def test_a_blank_book_title_is_refused(self):
        for t in BLANKS:
            with self.subTest(t=t), self.assertRaises(ValidationError):
                Book.objects.create(author=self.author, slug="b", language="en", title=t)
        self.assertFalse(Book.objects.exists())

    def test_a_blank_sermon_title_is_refused(self):
        for t in BLANKS:
            with self.subTest(t=t), self.assertRaises(ValidationError):
                Sermon.objects.create(
                    author=self.author, slug="s", language="en", title=t, body_html="<p>x</p>"
                )
        self.assertFalse(Sermon.objects.exists())

    def test_retitling_to_blank_is_refused(self):
        book = Book.objects.create(author=self.author, slug="b", language="en", title="Humility")
        book.title = "​"
        with self.assertRaises(ValidationError):
            book.save()
        with self.assertRaises(ValidationError):
            book.save(update_fields=["title"])

    def test_a_scoped_save_that_leaves_the_title_alone_passes(self):
        """A legacy blank row (written past the guard, e.g. by .update()) can
        still be published, approved or retitled — not wedged."""
        book = Book.objects.create(author=self.author, slug="b", language="en", title="Humility")
        Book.objects.filter(pk=book.pk).update(title="")
        book.refresh_from_db()
        book.is_published = False
        book.save(update_fields=["is_published"])  # no raise
        book.title = "Humility"
        book.save()  # the fix goes through
        self.assertEqual(Book.objects.get(pk=book.pk).title, "Humility")


@override_settings(DEBUG=True)
class ImportRefusesInvisibleTitlesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(slug="am", name="Andrew Murray")

    def test_an_invisible_title_is_a_400_not_a_book(self):
        res = APIClient().post(
            "/api/admin/import/publish/",
            {
                "kind": "book",
                "title": "​​",
                "author_slug": "am",
                "chapters": [{"title": "One", "html": "<p>Consider the grace of humility, and the Lord.</p>"}],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("title", res.data["detail"].lower())
        self.assertFalse(Book.objects.exists())
