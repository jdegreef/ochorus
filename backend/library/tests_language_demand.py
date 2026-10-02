"""Demand for one work in one language (admin_views.demand).

"Readers are asking for" on a language's admin page, and the "reading in
another language" count on Language health, both rest on one rule: a reader
whose site language is X, reading a work that has no X edition, is one vote
for that work in X. These tests pin the rule's edges, because these counts
decide what gets translated next.
"""

from __future__ import annotations

import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ReadingProgress, WorkKind

from .demand import readers_elsewhere, reading_elsewhere
from .models import Author, Book, Language, SearchQueryLog, Sermon

User = get_user_model()


def reader(locale):
    user = User.objects.create(username=str(uuid.uuid4()))
    return UserProfile.objects.create(user=user, supabase_uid=uuid.uuid4(), locale=locale)


def read(profile, slug, language="en", kind=WorkKind.BOOK):
    ReadingProgress.objects.create(profile=profile, kind=kind, book_slug=slug, language=language)


@override_settings(DEBUG=True)
class LanguageDemandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tozer = Author.objects.create(slug="tozer", name="A. W. Tozer")
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        Book.objects.create(author=tozer, slug="the-pursuit-of-god", language="en", title="The Pursuit of God")
        # Absolute Surrender already has a Swahili edition.
        for lang in ("en", "sw"):
            Book.objects.create(author=murray, slug="absolute-surrender", language=lang, title="Absolute Surrender")
        Sermon.objects.create(author=murray, slug="waiting-on-god", language="en", title="Waiting on God")
        for code, name in (("sw", "Swahili"), ("lg", "Luganda")):
            Language.objects.get_or_create(code=code, defaults={"name": name, "native_name": name})

        sw1, sw2, sw_home = reader("sw"), reader("sw"), reader("sw")
        read(sw1, "the-pursuit-of-god")
        read(sw1, "absolute-surrender")  # has a Swahili edition: not a vote
        read(sw1, "waiting-on-god", kind=WorkKind.SERMON)
        read(sw2, "the-pursuit-of-god")
        read(sw_home, "absolute-surrender", language="sw")  # reading in their own language
        read(reader("en"), "the-pursuit-of-god")  # site language English: never counted
        read(reader("lg"), "the-pursuit-of-god")

    def test_a_vote_is_a_reader_outside_their_language_on_a_work_it_lacks(self):
        wanted = reading_elsewhere(["sw", "lg"])
        self.assertEqual(
            wanted["sw"], {("book", "the-pursuit-of-god"): 2, ("sermon", "waiting-on-god"): 1}
        )
        self.assertEqual(wanted["lg"], {("book", "the-pursuit-of-god"): 1})
        # sw1 wants two works but is one reader.
        self.assertEqual(readers_elsewhere(["sw", "lg"]), {"sw": 2, "lg": 1})

    def test_english_is_never_a_target(self):
        self.assertNotIn("en", reading_elsewhere(["en", "sw"]))

    def test_the_language_page_lists_works_with_their_evidence(self):
        # Case-folded like the search report, these are one query, so one vote:
        # the log is anonymous, and one reader retrying mustn't outvote readers.
        SearchQueryLog.objects.create(query="Pursuit", language="sw", result_count=0)
        SearchQueryLog.objects.create(query="pursuit", language="sw", result_count=0)
        hit = {"type": "book", "book_slug": "the-pursuit-of-god", "book_title": "The Pursuit of God"}
        with mock.patch("library.search.search_library", return_value=[hit]) as search:
            res = APIClient().get("/api/admin/languages/sw/wanted/")
        self.assertEqual(res.status_code, 200)
        search.assert_called_once_with("pursuit", "en")
        top = res.data["works"][0]
        self.assertEqual(
            (top["slug"], top["title"], top["author"], top["readers"], top["searches"]),
            ("the-pursuit-of-god", "The Pursuit of God", "A. W. Tozer", 2, 1),
        )
        self.assertEqual([w["slug"] for w in res.data["works"]], ["the-pursuit-of-god", "waiting-on-god"])

    def test_a_search_for_a_work_the_language_already_has_is_not_a_vote(self):
        SearchQueryLog.objects.create(query="surrender", language="sw", result_count=0)
        hit = {"type": "book", "book_slug": "absolute-surrender", "book_title": "Absolute Surrender"}
        with mock.patch("library.search.search_library", return_value=[hit]):
            res = APIClient().get("/api/admin/languages/sw/wanted/")
        self.assertNotIn("absolute-surrender", [w["slug"] for w in res.data["works"]])

    def test_a_broad_query_votes_for_no_work(self):
        """"prayer" finding many books says readers want prayer, not any one."""
        SearchQueryLog.objects.create(query="prayer", language="sw", result_count=0)
        hits = [{"type": "book", "book_slug": f"prayer-{i}", "book_title": f"Prayer {i}"} for i in range(4)]
        with mock.patch("library.search.search_library", return_value=hits):
            res = APIClient().get("/api/admin/languages/sw/wanted/")
        self.assertFalse([w for w in res.data["works"] if w["searches"]])

    def test_language_health_counts_distinct_readers_reading_elsewhere(self):
        res = APIClient().get("/api/admin/language-health/")
        self.assertEqual(res.status_code, 200)
        by_code = {r["code"]: r["reading_elsewhere"] for r in res.data["languages"]}
        # sw1 wants two works but is one reader.
        self.assertEqual((by_code["sw"], by_code["lg"]), (2, 1))

    def test_coverage_cells_carry_the_demand_behind_each_gap(self):
        res = APIClient().get("/api/admin/coverage/")
        self.assertEqual(res.status_code, 200)
        books = {r["slug"]: r for r in res.data["books"]}
        sermons = {r["slug"]: r for r in res.data["sermons"]}
        # Only columns that exist count: Luganda has no content yet, so its one
        # reader's vote has no cell to sit on.
        self.assertEqual(books["the-pursuit-of-god"]["demand"], {"sw": 2})
        self.assertEqual(sermons["waiting-on-god"]["demand"], {"sw": 1})
        self.assertNotIn("demand", books["absolute-surrender"])
