"""Topic search must match the language the reader is actually reading in.

Topics are the one content type that is a single row plus a translation
side-table (books, sermons and plans are per-language ROWS). The Postgres search
vector was built from ``Topic.title`` / ``Topic.description`` — the ENGLISH
columns — whatever language was asked for, so a Spanish reader searching
*oración* never found the prayer shelf. A whole content type was unreachable by
search in every non-English locale, on a site whose point is multilingual
reading.

It stayed hidden because the two backends disagreed: the SQLite dev fallback
(``_lite_q``) *does* search ``translations__title``, so a developer checking the
behaviour locally saw it work. These tests therefore run on **Postgres**, which
is the production path and the only one that was broken. CI runs the suite twice
— once on SQLite, once on Postgres — and it is the second pass that gates this.
"""

from __future__ import annotations

from unittest import skipUnless

from django.db import connection
from django.test import TestCase

from library.models import Topic, TopicTranslation
from library.search import count_by_type, page_by_type, search_library


def _slugs(hits):
    """The topic slugs in a result list. Topic hits key their slug as
    ``topic_slug`` (see ``_topic_hit``), not ``slug``."""
    return {h["topic_slug"] for h in hits if h.get("type") == "topic"}


@skipUnless(connection.vendor == "postgresql", "Postgres is the production path")
class LocalizedTopicSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            description="Classics on the inner life of prayer.",
            is_published=True,
        )
        TopicTranslation.objects.create(
            topic=cls.topic,
            language="es",
            title="Sobre la oración",
            description="Clásicos sobre la vida interior de oración.",
        )
        # A second shelf, translated only into Swahili — it must not surface for
        # Spanish just because a sibling row exists.
        cls.other = Topic.objects.create(
            slug="humility",
            title="On Humility",
            description="The root of every virtue.",
            is_published=True,
        )
        TopicTranslation.objects.create(
            topic=cls.other,
            language="sw",
            title="Kuhusu unyenyekevu",
            description="Mzizi wa kila fadhila.",
        )

    def test_spanish_query_finds_the_spanish_shelf(self):
        """The regression: this returned nothing before the fix."""
        hits = search_library("oración", "es")
        self.assertIn("prayer", _slugs(hits))

    def test_spanish_query_matches_the_translated_description_too(self):
        hits = search_library("interior", "es")
        self.assertIn("prayer", _slugs(hits))

    def test_english_query_still_finds_the_english_shelf(self):
        hits = search_library("prayer", "en")
        self.assertIn("prayer", _slugs(hits))

    def test_english_title_does_not_match_in_spanish(self):
        """No English fallback: a Spanish reader is never shown English prose.

        `TopicListSerializer` renders `title_for("es")`, so matching the English
        column would surface a shelf whose title the reader cannot read — and
        whose text is nowhere on the page they land on.
        """
        hits = search_library("Humility", "es")
        self.assertNotIn("humility", _slugs(hits))

    def test_a_shelf_untranslated_in_this_language_never_matches(self):
        # "unyenyekevu" exists only as Swahili; searching Spanish must not find
        # it, and searching Swahili must.
        self.assertNotIn("humility", _slugs(search_library("unyenyekevu", "es")))
        self.assertIn("humility", _slugs(search_library("unyenyekevu", "sw")))

    def test_counts_agree_with_the_results(self):
        """count_by_type re-derives the match; it must not disagree with the list.

        The two call `_match` separately, so a vector fixed in one place and not
        the other shows a "1 topic" chip that opens an empty list.
        """
        counts, _ = count_by_type("oración", "es", None)
        self.assertEqual(counts.get("topic"), 1)

    def test_paged_results_agree_with_the_results(self):
        """The 'show more' page is a third path through the same vector."""
        page = page_by_type("oración", "es", "topic")
        self.assertIn("prayer", _slugs(page))

    def test_unpublished_shelf_stays_hidden_in_every_language(self):
        Topic.objects.filter(slug="prayer").update(is_published=False)
        self.assertNotIn("prayer", _slugs(search_library("oración", "es")))
