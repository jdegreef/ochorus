"""The busiest public endpoints cost the same number of queries for 1 row as for 6.

Item 18 of the Nov 2026 code/speed/cost list: about a dozen query-count checks
in ~3,100 tests, so a serializer that starts touching a relation per row (an
N+1) would ship unnoticed and show up only as a slower prerender and a busier
Supabase. These do not pin exact numbers, which churn with every harmless
change; they pin the SHAPE: grow the list sixfold and the query count must not
move. The endpoints are the ones the prerender crawl and readers hit most.
"""

from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Language, Sermon


class QueryScalingTests(TestCase):
    def setUp(self):
        Language.objects.update_or_create(
            code="en", defaults={"name": "English", "status": Language.Status.LIVE}
        )
        self.n = 0

    # -- builders --------------------------------------------------------
    def author(self):
        self.n += 1
        return Author.objects.create(slug=f"author-{self.n}", name=f"Author {self.n}")

    def book(self, author, chapters=2):
        self.n += 1
        book = Book.objects.create(
            author=author,
            slug=f"book-{self.n}",
            language="en",
            title=f"Book {self.n}",
            is_published=True,
        )
        for order in range(1, chapters + 1):
            Chapter.objects.create(
                book=book,
                order=order,
                title=f"Ch {order}",
                body_html="<p>Grace and peace.</p>",
            )
        return book

    def sermon(self, author):
        self.n += 1
        return Sermon.objects.create(
            author=author,
            slug=f"sermon-{self.n}",
            language="en",
            title=f"Sermon {self.n}",
            body_html="<p>A word in season.</p>",
            is_published=True,
        )

    def queries(self, url):
        with CaptureQueriesContext(connection) as captured:
            res = APIClient().get(url)
        self.assertEqual(res.status_code, 200, url)
        return len(captured.captured_queries)

    def assert_flat(self, url, grow, what):
        first = self.queries(url)
        for _ in range(5):
            grow()
        grown = self.queries(url)
        self.assertLessEqual(
            grown,
            first,
            f"{url}: 6 {what} cost {grown} queries against {first} for 1 (an N+1)",
        )

    # -- the endpoints ---------------------------------------------------
    def test_book_list(self):
        a = self.author()
        self.book(a)
        self.assert_flat(
            reverse("book-list"), lambda: self.book(self.author()), "books"
        )

    def test_sermon_list(self):
        a = self.author()
        self.sermon(a)
        self.assert_flat(
            reverse("sermon-list"), lambda: self.sermon(self.author()), "sermons"
        )

    def test_author_list(self):
        self.book(self.author())
        self.assert_flat(
            reverse("author-list"), lambda: self.book(self.author()), "authors"
        )

    def test_author_detail_with_more_books_and_sermons(self):
        a = self.author()
        self.book(a)
        self.sermon(a)

        def grow():
            self.book(a)
            self.sermon(a)

        self.assert_flat(
            reverse("author-detail", args=[a.slug]), grow, "books and sermons"
        )

    def test_book_detail_with_more_chapters(self):
        a = self.author()
        book = self.book(a, chapters=1)
        state = {"order": 1}

        def grow():
            state["order"] += 1
            Chapter.objects.create(
                book=book, order=state["order"], title="More", body_html="<p>More.</p>"
            )

        self.assert_flat(reverse("book-detail", args=[book.slug]), grow, "chapters")
