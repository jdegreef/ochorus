"""Client-cache headers, and the two endpoints memoised server-side.

The library API carried no ``Cache-Control`` at all: every shelf a reader paged
back to was recomputed from scratch. These assert both halves of the fix — the
header on the catalogue endpoints, and its ABSENCE everywhere it would be wrong.

A real LocMemCache is opted into here. The suite runs on a DummyCache by default
(see settings.CACHES) precisely so that memoised values cannot leak between
tests; a test that wants to observe caching has to ask for it, and clear it.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .http_cache import MAX_AGE
from .models import Author, Book, Chapter, Language, SearchQueryLog

REAL_CACHE = override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "http-cache-tests",
        },
        "throttle": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    }
)


class CacheControlHeaderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray", bio="Bio.")
        cls.book = Book.objects.create(
            author=cls.author,
            slug="humility",
            language="en",
            title="Humility",
            is_published=True,
        )
        Chapter.objects.create(
            book=cls.book, order=1, title="One", body_html="<p>Text.</p>"
        )

    def setUp(self):
        self.client = APIClient()

    def _cc(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, url)
        return res.headers.get("Cache-Control")

    def test_catalogue_endpoints_are_publicly_cacheable(self):
        for url in (
            reverse("book-list"),
            reverse("book-detail", args=["humility"]),
            reverse("chapter-detail", args=["humility", 1]),
            reverse("author-list"),
            reverse("author-detail", args=["am"]),
            reverse("sermon-list"),
            reverse("topic-list"),
            reverse("plan-list"),
            reverse("language-list"),
        ):
            with self.subTest(url=url):
                cc = self._cc(url)
                self.assertIsNotNone(cc, f"{url} has no Cache-Control")
                self.assertIn("public", cc)
                self.assertIn(f"max-age={MAX_AGE}", cc)

    def test_staleness_is_bounded_and_short(self):
        """A stuck cache is the failure mode being avoided; keep max-age small."""
        self.assertLessEqual(MAX_AGE, 300)

    def test_no_etag_is_offered(self):
        """Deliberate — see http_cache.py.

        An ETag keyed on the content digest cannot see an admin publishing a
        book, so it would answer 304 against an unchanged digest indefinitely.
        Bounded staleness is the safe half; conditional requests need an
        `updated_at` the content models do not all have.
        """
        res = self.client.get(reverse("book-list"))
        self.assertIsNone(res.headers.get("ETag"))

    def test_search_is_not_cached(self):
        """Query-dependent, and it writes a log row per call."""
        res = self.client.get(reverse("search"), {"q": "humility"})
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.headers.get("Cache-Control"))

    def test_a_missing_book_is_not_cached(self):
        """Caching a 404 would outlive the import that fixes it."""
        res = self.client.get(reverse("book-detail", args=["nope"]))
        self.assertEqual(res.status_code, 404)
        self.assertIsNone(res.headers.get("Cache-Control"))


@REAL_CACHE
class ServerSideMemoisationTests(TestCase):
    """The two endpoints that did real work on every single request."""

    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=cls.author,
            slug="humility",
            language="en",
            title="Humility",
            is_published=True,
        )
        Language.objects.update_or_create(
            code="en", defaults={"name": "English", "native_name": "English"}
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_the_language_list_stops_rescanning_every_book(self):
        url = reverse("language-list")
        with CaptureQueriesContext(connection) as first:
            self.assertEqual(self.client.get(url).status_code, 200)
        with CaptureQueriesContext(connection) as second:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertLess(
            len(second.captured_queries),
            len(first.captured_queries),
            "the second request re-ran the published-book scan",
        )

    def test_popular_searches_computes_its_month_long_aggregate_once(self):
        for _ in range(6):
            SearchQueryLog.objects.create(
                query="prayer", language="en", result_count=3
            )
        url = reverse("popular-searches")
        with CaptureQueriesContext(connection) as first:
            self.client.get(url)
        with CaptureQueriesContext(connection) as second:
            self.client.get(url)
        self.assertTrue(first.captured_queries)
        self.assertEqual(
            len(second.captured_queries),
            0,
            "the 30-day GROUP BY ran again for the second reader",
        )

    def test_each_language_is_memoised_separately(self):
        """A cache key that ignored language would serve one locale's chips to another."""
        url = reverse("popular-searches")
        self.client.get(url, {"language": "en"})
        with CaptureQueriesContext(connection) as other:
            self.client.get(url, {"language": "es"})
        self.assertTrue(
            other.captured_queries, "Spanish reused the English cache entry"
        )
