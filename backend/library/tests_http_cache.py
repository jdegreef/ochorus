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
from .models import Author, Book, Chapter, ContentRevision, Language, SearchQueryLog

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

    def test_a_conditional_request_returns_304_without_querying(self):
        url = reverse("book-list")
        first = self.client.get(url)
        etag = first.headers.get("ETag")
        self.assertTrue(etag and etag.startswith('W/"'), etag)

        with CaptureQueriesContext(connection) as full:
            self.client.get(url)
        with CaptureQueriesContext(connection) as conditional:
            res = self.client.get(url, HTTP_IF_NONE_MATCH=etag)

        self.assertEqual(res.status_code, 304)
        self.assertFalse(res.content)  # a 304 carries no body
        # The 304 is answered before the queryset — strictly fewer queries.
        self.assertLess(len(conditional.captured_queries), len(full.captured_queries))

    def test_a_content_change_busts_the_etag(self):
        # The whole point over a digest-only tag: an admin mutation (which bumps
        # ContentRevision) invalidates the client's cached tag, so it re-fetches.
        url = reverse("book-list")
        stale = self.client.get(url).headers["ETag"]
        ContentRevision.bump()
        res = self.client.get(url, HTTP_IF_NONE_MATCH=stale)
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.headers["ETag"], stale)

    def test_the_etag_is_per_url(self):
        # A client holding the /books tag must not be told 304 for /authors.
        books = self.client.get(reverse("book-list")).headers["ETag"]
        res = self.client.get(reverse("author-list"), HTTP_IF_NONE_MATCH=books)
        self.assertEqual(res.status_code, 200)

    def test_bump_command_busts_the_etag_after_a_direct_db_change(self):
        # A change made directly in the DB (e.g. an urgent copyright pull) bypasses
        # the revision channel, so the tag is unchanged and a conditional request
        # still 304s — until the admin runs bump_content_revision.
        from django.core.management import call_command

        url = reverse("book-list")
        etag = self.client.get(url).headers["ETag"]
        Book.objects.filter(slug="humility").update(is_published=False)
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=etag).status_code, 304)

        call_command("bump_content_revision")
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=etag).status_code, 200)

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
