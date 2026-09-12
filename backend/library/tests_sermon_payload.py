"""A sermon CARD must not cost a sermon BODY.

`SermonListSerializer` renders a line of text — title, scripture reference, the
"In brief" summary, word count, author. It emits no body. Yet every list path
fetched `body_html`, `body_text` AND the query-time tsvector, roughly 100 KB a
row, to draw that line.

The identical bug was found and fixed for chapters on the book-detail page — its
`Prefetch(... .only(...))` carries the note about the 2026-08-14 OOM — and the
lesson never reached sermons. There were four such paths.

These tests assert the SQL the real endpoints issue, not a queryset rebuilt
here: rebuilding one would test Django's `defer()` rather than this change.
"""

from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Author, AuthorTranslation, Sermon, Topic, TopicSermon

HEAVY = ("body_html", "body_text", "search_vector")

# A body big enough that fetching it would be obvious in a payload comparison.
BODY = "<p>" + ("Consider the loving-kindness of the Lord. " * 400) + "</p>"


def _sermon_selects(captured) -> list[str]:
    return [
        q["sql"]
        for q in captured.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT")
        and "library_sermon" in q["sql"]
        and "library_sermon_" not in q["sql"]  # not the join tables
    ]


class SermonCardPayloadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray", bio="A bio.")
        AuthorTranslation.objects.create(author=cls.author, language="es", bio="Una bio.")
        for n in range(5):
            Sermon.objects.create(
                author=cls.author,
                slug=f"sermon-{n}",
                language="en",
                title=f"Sermon {n}",
                summary="In brief.",
                body_html=BODY,
                is_published=True,
            )
        cls.topic = Topic.objects.create(
            slug="prayer", title="On Prayer", is_published=True
        )
        for n in range(5):
            TopicSermon.objects.create(
                topic=cls.topic, sermon_slug=f"sermon-{n}", sort_order=n
            )

    def setUp(self):
        self.client = APIClient()

    def _get(self, url):
        with CaptureQueriesContext(connection) as captured:
            res = self.client.get(url)
        self.assertEqual(res.status_code, 200, url)
        return res, captured

    def _assert_no_bodies(self, captured, url):
        selects = _sermon_selects(captured)
        self.assertTrue(selects, f"{url} issued no sermon SELECT")
        for sql in selects:
            for column in HEAVY:
                self.assertNotIn(
                    column, sql, f"{url} still fetches {column} to render cards"
                )

    def test_the_sermon_shelf_fetches_no_bodies(self):
        _, captured = self._get(reverse("sermon-list"))
        self._assert_no_bodies(captured, "sermon-list")

    def test_the_topic_shelf_fetches_no_bodies(self):
        _, captured = self._get(reverse("topic-list"))
        self._assert_no_bodies(captured, "topic-list")

    def test_the_topic_page_fetches_no_bodies(self):
        _, captured = self._get(reverse("topic-detail", args=["prayer"]))
        self._assert_no_bodies(captured, "topic-detail")

    def test_the_author_page_fetches_no_bodies(self):
        _, captured = self._get(reverse("author-detail", args=["am"]))
        self._assert_no_bodies(captured, "author-detail")

    def test_the_shelf_still_renders_everything_a_card_shows(self):
        """Deferring must not cost the reader a field."""
        res, _ = self._get(reverse("sermon-list"))
        row = res.data[0]
        for field in ("slug", "title", "scripture_ref", "summary", "word_count", "author"):
            self.assertIn(field, row)
        self.assertEqual(row["summary"], "In brief.")
        self.assertNotIn("body_html", row)

    def test_the_shelf_carries_each_sermons_topics(self):
        """The card's topic chips power the shelf's topic filter (mirrors books)."""
        res, _ = self._get(reverse("sermon-list"))
        row = next(r for r in res.data if r["slug"] == "sermon-0")
        self.assertEqual(row["topics"], [{"slug": "prayer", "title": "On Prayer"}])

    def test_the_author_page_threads_topics_into_its_sermon_cards(self):
        """The author page carries the same chips, from its one shared topic walk
        (not a second per-page fetch — see the query budget in tests.py)."""
        res, _ = self._get(reverse("author-detail", args=["am"]))
        row = next(s for s in res.data["sermons"] if s["slug"] == "sermon-0")
        self.assertEqual(row["topics"], [{"slug": "prayer", "title": "On Prayer"}])

    def test_the_sermon_page_still_serves_its_body(self):
        """The DETAIL endpoint must be untouched — it exists to serve the body."""
        res, _ = self._get(reverse("sermon-detail", args=["sermon-1"]))
        self.assertIn("Consider the loving-kindness", res.data["body_html"])

    def test_the_sermon_page_serves_study_questions(self):
        """The detail endpoint carries the answered study questions verbatim —
        the source for both the reflection section and the FAQPage JSON-LD."""
        qa = [
            {"question": "What is the point?", "answer": "That God does not change."},
            {"question": "Why does it comfort?", "answer": "His people are not consumed."},
        ]
        Sermon.objects.create(
            author=self.author,
            slug="with-questions",
            language="en",
            title="With Questions",
            body_html=BODY,
            study_questions=qa,
            is_published=True,
        )
        res, _ = self._get(reverse("sermon-detail", args=["with-questions"]))
        self.assertEqual(res.data["study_questions"], qa)

    def test_the_shelf_omits_study_questions(self):
        """Study questions are a detail-only field — a card never carries them."""
        res, _ = self._get(reverse("sermon-list"))
        self.assertNotIn("study_questions", res.data[0])

    def test_the_fallback_queryset_prefetches_author_translations(self):
        """The fallback was the one sermon path without the prefetch.

        Honest about what this does and does not show. Reading a localized
        author bio over the fallback's sermons costs one query PER SERMON
        without `author__translations` and two in total with it — measured
        below. But no serializer reads those bios today: `TopicListSerializer`
        renders only `{kind, slug, title}` per sermon, and rendering the topic
        page takes a constant 17 queries either way.

        So this is parity with the other three sermon paths and a guard against
        the N+1 that appears the moment a sermon card shows an author bio — not
        a live bug being fixed. The audit reported it as a live N+1; it is not
        one yet.
        """
        from .serializers import TopicListSerializer

        # Spanish members, because bio_for("en") returns the base column
        # without ever touching translations — the N+1 cannot show in English.
        for n in range(4):
            Sermon.objects.create(
                author=self.author,
                slug=f"es-sermon-{n}",
                language="es",
                title=f"Sermón {n}",
                body_html=BODY,
                is_published=True,
            )
            TopicSermon.objects.create(
                topic=self.topic, sermon_slug=f"es-sermon-{n}", sort_order=100 + n
            )

        topic = Topic.objects.get(slug="prayer")
        self.assertIsNone(getattr(topic, "sermons_in_language", None))
        serializer = TopicListSerializer(topic, context={"language": "es"})
        sermons = serializer._sermons(topic)
        self.assertTrue(sermons)

        # Translations must already be in memory: reading every sermon's
        # localized bio should cost nothing further.
        with CaptureQueriesContext(connection) as captured:
            for sermon in sermons:
                sermon.author.bio_for("es")
        self.assertEqual(
            len(captured.captured_queries),
            0,
            "reading author bios queried per sermon — author__translations is "
            "not prefetched on the fallback path",
        )
