"""The admin inventory lists (``/api/admin/catalog/<kind>/``) and the admin's
shared cache (``library.admin_cache``)."""

from unittest.mock import patch

import requests
from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from . import admin_cache
from .models import (
    Article,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Plan,
    Quote,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
)

_LOCMEM = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "admin": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "t",
    },
}


@override_settings(DEBUG=True)
class AdminCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.murray = Author.objects.create(
            slug="am", name="Andrew Murray", bio="Preacher.", bio_html="<p>Bio</p>"
        )
        self.ryle = Author.objects.create(slug="jcr", name="J. C. Ryle")
        Author.objects.create(slug="oo", name="Ochorus Originals", is_imprint=True)
        AuthorTranslation.objects.create(
            author=self.murray, language="es", bio="Predicador."
        )

        en = Book.objects.create(
            author=self.murray, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(book=en, order=1, title="One", body_html="<p>a b c</p>")
        Chapter.objects.create(book=en, order=2, title="Two", body_html="<p>d e</p>")
        es = Book.objects.create(
            author=self.murray,
            slug="humility",
            language="es",
            title="Humildad",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(book=es, order=1, title="Uno", body_html="<p>x</p>")
        Book.objects.create(
            author=self.ryle,
            slug="holiness",
            language="en",
            title="Holiness",
            is_published=False,
        )
        for i in range(3):
            Sermon.objects.create(
                author=self.ryle,
                slug=f"s{i}",
                language="en",
                title=f"Sermon {i}",
                body_html="<p>x</p>",
            )

        topic = Topic.objects.create(slug="prayer", title="Prayer")
        TopicBook.objects.create(topic=topic, book_slug="humility")
        TopicBook.objects.create(topic=topic, book_slug="holiness")
        TopicSermon.objects.create(topic=topic, sermon_slug="s0")

    def get(self, kind, **params):
        res = self.client.get(f"/api/admin/catalog/{kind}/", params)
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def test_books_list_with_counts(self):
        d = self.get("books", sort="title")
        self.assertEqual(d["total"], 3)
        humility = next(
            r for r in d["results"] if r["language"] == "en" and r["slug"] == "humility"
        )
        self.assertEqual(humility["chapters"], 2)
        self.assertEqual(humility["words"], 5)
        self.assertEqual(humility["author"], {"slug": "am", "name": "Andrew Murray"})
        self.assertEqual(
            {f["code"]: f["count"] for f in d["facets"]["languages"]},
            {"en": 2, "es": 1},
        )
        self.assertEqual(d["facets"]["statuses"], {"published": 2, "unpublished": 1})

    def test_filters_combine_and_facets_ignore_their_own_filter(self):
        d = self.get("books", language="en", status="published")
        self.assertEqual([r["title"] for r in d["results"]], ["Humility"])
        # The language counts keep every language (under the status filter)…
        self.assertEqual(
            {f["code"]: f["count"] for f in d["facets"]["languages"]},
            {"en": 1, "es": 1},
        )
        # …and the status counts are within the chosen language.
        self.assertEqual(d["facets"]["statuses"], {"published": 1, "unpublished": 1})

    def test_search_matches_author_and_source_filter(self):
        self.assertEqual(self.get("books", q="ryle")["total"], 1)
        d = self.get("books", source="ai_unreviewed")
        self.assertEqual([r["title"] for r in d["results"]], ["Humildad"])

    def test_pagination_clamps(self):
        d = self.get("sermons", page_size=2, page=99, sort="title")
        self.assertEqual((d["page"], d["pages"], d["total"]), (2, 2, 3))
        self.assertEqual([r["title"] for r in d["results"]], ["Sermon 2"])

    def test_authors_count_distinct_works_not_join_products(self):
        d = self.get("authors", sort="title")
        rows = {r["slug"]: r for r in d["results"]}
        # Two Humility rows are one work; one translation; no cross-multiplying.
        self.assertEqual(rows["am"]["books"], 1)
        self.assertEqual(rows["am"]["translations"], 1)
        self.assertEqual((rows["jcr"]["books"], rows["jcr"]["sermons"]), (1, 3))
        # The imprint never counts as missing a bio.
        self.assertEqual(d["facets"]["statuses"]["no_bio"], 1)

    def test_topics_count_each_relation(self):
        row = self.get("topics")["results"][0]
        self.assertEqual((row["books"], row["sermons"], row["articles"]), (2, 1, 0))

    def test_other_kinds_answer(self):
        Plan.objects.create(slug="p", language="en", title="A plan")
        Article.objects.create(
            slug="a", language="en", h1="An article", body_html="<p>x</p>"
        )
        chapter = Chapter.objects.get(book__language="es")
        Quote.objects.create(
            slug="q",
            author=self.murray,
            text="Humility is…",
            chapter=chapter,
            paragraph=1,
        )
        self.assertEqual(self.get("plans")["results"][0]["days"], 0)
        self.assertEqual(self.get("articles")["results"][0]["title"], "An article")
        quote = self.get("quotes", language="es")["results"][0]
        self.assertEqual(quote["source"]["title"], "Humildad")
        self.assertEqual(self.get("series")["total"], 0)

    def test_unknown_kind_is_404_and_bad_sort_falls_back(self):
        self.assertEqual(self.client.get("/api/admin/catalog/nope/").status_code, 404)
        self.assertEqual(self.get("books", sort="nonsense")["sort"], "title")


@override_settings(CACHES=_LOCMEM)
class AdminCacheTests(SimpleTestCase):
    def setUp(self):
        caches["admin"].clear()

    def test_read_through_reuses_then_falls_back_to_last_good(self):
        state = [["job"]]

        def fetcher():
            value = state[0]
            if isinstance(value, Exception):
                raise value
            return value

        first = admin_cache.read_through("k", fetcher, fresh_seconds=60)
        self.assertEqual((first.value, first.stale), (["job"], False))

        state[0] = ["changed"]
        self.assertEqual(
            admin_cache.read_through("k", fetcher, fresh_seconds=60).value, ["job"]
        )

        # After the fresh copy is dropped and GitHub fails: the last good copy, stale.
        admin_cache.forget("k")
        state[0] = requests.ConnectionError("down")
        down = admin_cache.read_through("k", fetcher, fresh_seconds=60)
        self.assertEqual(
            (down.value, down.stale, down.read_at), (["job"], True, first.read_at)
        )

    def test_read_through_raises_with_nothing_to_fall_back_on(self):
        def fetcher():
            raise requests.ConnectionError("down")

        with self.assertRaises(requests.RequestException):
            admin_cache.read_through("cold", fetcher, fresh_seconds=60)

    def test_revision_memo_follows_the_content_revision(self):
        calls = []

        def compute():
            calls.append(1)
            return {"n": len(calls)}

        with patch("library.models.ContentRevision.current", return_value=1):
            self.assertEqual(
                admin_cache.revision_memo("s", compute, timeout=60), {"n": 1}
            )
            self.assertEqual(
                admin_cache.revision_memo("s", compute, timeout=60), {"n": 1}
            )
            self.assertEqual(
                admin_cache.revision_memo("s", compute, timeout=60, refresh=True),
                {"n": 2},
            )
        with patch("library.models.ContentRevision.current", return_value=2):
            self.assertEqual(
                admin_cache.revision_memo("s", compute, timeout=60), {"n": 3}
            )
