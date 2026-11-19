"""A topic's "In the Bible" row — the Bible chapters its own classics return to.

What is pinned here is the RULE (``scripture_graph.topic_bible_chapters``):
distinct voices not raw citations, the floor, the second-work floor that keeps
one book's favourite chapter off the row, only chapters the library's Bible
prints, sermons through their own text, and English only.
"""

from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Series, Sermon, Topic, TopicBook, TopicSermon
from .scripture_graph import TOPIC_BIBLE_FLOOR, topic_bible_chapters


def chapter(book, order, *refs):
    Chapter.objects.create(
        book=book,
        order=order,
        title=f"Chapter {order}",
        body_html="<p>" + " ".join(f"A passage that dwells on {r}." for r in refs) + "</p>",
    )


class TopicBibleChaptersTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        bible = Series.objects.create(slug="the-bible", title="The Bible")
        # The library's Bible prints Matthew 6 and Romans 5 and 8 — not Luke.
        matthew = Book.objects.create(
            author=author, slug="matthew", language="en", title="Matthew",
            series=bible, series_position=40,
        )
        Chapter.objects.create(book=matthew, order=1, title="Introduction", body_html="<p>x</p>")
        Chapter.objects.create(
            book=matthew, order=7, title="Matthew 6", body_html="<p>x</p>",
            summary="The Lord's Prayer.",
        )
        romans = Book.objects.create(
            author=author, slug="romans", language="en", title="Romans",
            series=bible, series_position=45,
        )
        for n in (5, 8):
            Chapter.objects.create(book=romans, order=n + 1, title=f"Romans {n}", body_html="<p>x</p>")

        self.a = Book.objects.create(author=author, slug="a", language="en", title="Book A")
        b = Book.objects.create(author=author, slug="b", language="en", title="Book B")
        # Book A's three chapters each treat Matthew 6 — the first quoting it
        # three times — and Romans 8, which nobody else on the shelf cites.
        chapter(self.a, 1, "Matthew 6:9", "Matthew 6:9", "Matthew 6:10", "Romans 8:28")
        chapter(self.a, 2, "Matthew 6:6", "Romans 8:26")
        chapter(self.a, 3, "Matthew 6:9", "Romans 8:28", "Luke 11:2", "Romans 5:1")
        chapter(b, 1, "Matthew 6:9", "Luke 11:2", "Romans 5:1")
        chapter(b, 2, "Luke 11:9")
        # A translated edition of A: never a voice (the index is English).
        es = Book.objects.create(author=author, slug="a", language="es", title="Libro A")
        chapter(es, 1, "Romans 5:1")
        self.sermon = Sermon.objects.create(
            author=author, slug="s", language="en", title="On Asking",
            scripture_ref="Matthew 6:5-15", body_html="<p>Text.</p>",
        )
        call_command("index_citations", "--all", verbosity=0)

        self.topic = Topic.objects.create(slug="prayer", title="Prayer")
        for i, slug in enumerate(("a", "b", "matthew")):
            TopicBook.objects.create(topic=self.topic, book_slug=slug, sort_order=i)
        TopicSermon.objects.create(topic=self.topic, sermon_slug="s")

    def test_ranks_by_distinct_voices_and_links_the_bible_chapter(self):
        rows = topic_bible_chapters(self.topic)
        self.assertEqual(
            rows[0],
            {
                "reference": "Matthew 6",
                "slug": "matthew",
                "order": 7,
                "summary": "The Lord's Prayer.",
                # A's three chapters + B's one + the sermon: one chapter quoting
                # Matthew 6:9 three times is still one voice.
                "count": 5,
            },
        )

    def test_one_works_favourite_chapter_never_makes_the_row(self):
        # Romans 8: three of Book A's chapters, but no other work — a
        # hobbyhorse, not something the topic returns to.
        refs = [r["reference"] for r in topic_bible_chapters(self.topic)]
        self.assertNotIn("Romans 8", refs)

    def test_under_the_floor_is_left_off(self):
        # Romans 5: one chapter of A, one of B — two works, two voices, one
        # under the floor. The Spanish edition's citation would be the third;
        # it is not a voice.
        self.assertEqual(TOPIC_BIBLE_FLOOR, 3)
        refs = [r["reference"] for r in topic_bible_chapters(self.topic)]
        self.assertNotIn("Romans 5", refs)

    def test_a_chapter_the_bible_does_not_print_is_never_linked(self):
        # Luke 11: three voices across two works, but no Luke in the library.
        refs = [r["reference"] for r in topic_bible_chapters(self.topic)]
        self.assertEqual(refs, ["Matthew 6"])

    def test_a_chapter_at_both_floors_joins_the_row_after_the_stronger_one(self):
        luke = Book.objects.create(
            author=self.a.author, slug="luke", language="en", title="Luke",
            series=Series.objects.get(slug="the-bible"), series_position=42,
        )
        Chapter.objects.create(book=luke, order=12, title="Luke 11", body_html="<p>x</p>")
        rows = topic_bible_chapters(self.topic)
        self.assertEqual([(r["reference"], r["count"]) for r in rows], [("Matthew 6", 5), ("Luke 11", 3)])
        self.assertEqual((rows[1]["slug"], rows[1]["order"], rows[1]["summary"]), ("luke", 12, ""))

    def test_the_payload_carries_it_in_english_only(self):
        from .models import TopicTranslation

        TopicTranslation.objects.create(topic=self.topic, language="es", title="Oración")
        en = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual([r["reference"] for r in en.data["bible_chapters"]], ["Matthew 6"])
        es = self.client.get("/api/library/topics/prayer/?language=es")
        self.assertEqual(es.status_code, 200)
        self.assertEqual(es.data["bible_chapters"], [])

    def test_a_topic_with_no_shared_chapter_gets_an_empty_row(self):
        lone = Topic.objects.create(slug="lone", title="Lone", sort_order=1)
        TopicBook.objects.create(topic=lone, book_slug="a")
        self.assertEqual(topic_bible_chapters(lone), [])


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class TopicBibleCacheTests(TestCase):
    def test_computed_once_per_revision(self):
        from unittest import mock

        from django.core.cache import cache

        from . import scripture_graph
        from .models import ContentRevision

        cache.clear()
        topic = Topic.objects.create(slug="t", title="T")
        with mock.patch.object(
            scripture_graph, "_topic_bible_ranking", wraps=scripture_graph._topic_bible_ranking
        ) as computed:
            topic_bible_chapters(topic)
            topic_bible_chapters(topic)
            self.assertEqual(computed.call_count, 1)
            ContentRevision.bump()
            topic_bible_chapters(topic)
            self.assertEqual(computed.call_count, 2)
