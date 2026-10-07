"""`/api/library/audiences/<audience>/` — the /young-readers/ and /teens/ hubs.

Pinned here: each book appears once (series, then retold editions, then the
curated topic's remainder); a suffix alone does not make a retelling (the full
text must exist); a plan is offered only when every book it reads is the hub's;
nothing falls back to English; and an unknown audience is a 404.
"""

from __future__ import annotations

from pathlib import Path

from django.test import TestCase

from .models import (
    Article,
    Author,
    Book,
    Plan,
    PlanDay,
    Series,
    Topic,
    TopicArticle,
    TopicBook,
    TopicTranslation,
)
from .serializers import AUDIENCE_EDITION_SUFFIX, EDITION_SUFFIXES
from .views import AUDIENCE_STARTS, AUDIENCE_TOPICS


class AudienceShelfTests(TestCase):
    URL = "/api/library/audiences/{}/?language={}"

    def setUp(self):
        self.author = Author.objects.create(slug="bunyan", name="John Bunyan")
        self.series = Series.objects.create(
            slug="brave-for-god", title="Brave for God", audience="young_readers",
            min_age=8, max_age=12,
        )
        self.topic = Topic.objects.create(slug="for-young-readers", title="For Young Readers")

    def _book(self, slug, *, language="en", series=None, published=True):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=slug,
            series=series, is_published=published,
        )

    def _get(self, audience="young_readers", language="en"):
        response = self.client.get(self.URL.format(audience, language))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _slugs(self, rows):
        return [r["slug"] for r in rows]

    def test_each_book_is_claimed_once_series_then_editions_then_topic(self):
        self._book("bfg-1", series=self.series)
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("north-wind")
        for slug in ("bfg-1", "pilgrims-progress-children", "north-wind"):
            TopicBook.objects.create(topic=self.topic, book_slug=slug)
        data = self._get()
        self.assertEqual(self._slugs(data["series"]), ["brave-for-god"])
        self.assertEqual(self._slugs(data["editions"]), ["pilgrims-progress-children"])
        self.assertEqual(self._slugs(data["more"]), ["north-wind"])
        self.assertEqual(data["topic"], {"slug": "for-young-readers", "title": "For Young Readers"})

    def test_a_suffix_alone_is_not_a_retelling(self):
        # Watts's Divine Songs for Children is an original: no "divine-songs-for".
        self._book("divine-songs-for-children")
        TopicBook.objects.create(topic=self.topic, book_slug="divine-songs-for-children")
        data = self._get()
        self.assertEqual(data["editions"], [])
        self.assertEqual(self._slugs(data["more"]), ["divine-songs-for-children"])

    def test_teens_gather_teen_editions_not_childrens(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("pilgrims-progress-teens")
        data = self._get("teens")
        self.assertEqual(self._slugs(data["editions"]), ["pilgrims-progress-teens"])
        self.assertEqual(data["series"], [])
        self.assertIsNone(data["topic"])  # no for-teens topic in this DB

    def test_a_plan_shows_only_when_it_reads_nothing_but_the_hubs_books(self):
        self._book("bfg-1", series=self.series)
        self._book("all-of-grace")
        kids = Plan.objects.create(slug="brave-24", language="en", title="Brave 24")
        PlanDay.objects.create(plan=kids, day=1, book_slug="bfg-1", chapter_order=1)
        mixed = Plan.objects.create(slug="mixed", language="en", title="Mixed")
        PlanDay.objects.create(plan=mixed, day=1, book_slug="bfg-1", chapter_order=1)
        PlanDay.objects.create(plan=mixed, day=2, book_slug="all-of-grace", chapter_order=1)
        self.assertEqual(self._slugs(self._get()["plans"]), ["brave-24"])

    def test_no_english_fallback(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        TopicBook.objects.create(topic=self.topic, book_slug="pilgrims-progress-children")
        data = self._get(language="sw")
        self.assertEqual(
            [data[k] for k in ("series", "editions", "more", "plans")], [[], [], [], []]
        )
        # The topic has no Swahili title, so the page links to no shelf.
        self.assertIsNone(data["topic"])

    def test_unpublished_books_are_left_out(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children", published=False)
        self.assertEqual(self._get()["editions"], [])

    def test_printable_names_the_export_editions_only(self):
        self._book("brave-for-god", series=self.series)  # in the export pilot
        self._book("north-wind")
        self._book("north-wind-children")  # not in it
        self.assertEqual(self._get()["printable"], ["brave-for-god"])

    def test_articles_are_the_topics_here_in_its_order(self):
        teens = Topic.objects.create(slug="for-teens", title="For Teens", is_published=True)
        for slug, order in (("is-the-bible-reliable", 2), ("can-i-have-doubts", 1)):
            TopicArticle.objects.create(topic=teens, article_slug=slug, sort_order=order)
            Article.objects.create(slug=slug, language="en", h1=slug, body_html="<p>x</p>", is_published=True)
        Article.objects.create(slug="can-i-have-doubts", language="sw", h1="sw", body_html="<p>x</p>", is_published=True)
        self.assertEqual(
            self._slugs(self._get("teens")["articles"]), ["can-i-have-doubts", "is-the-bible-reliable"]
        )
        # Swahili has one article, but no Swahili topic title: no shelf, no articles.
        self.assertEqual(self._get("teens", "sw")["articles"], [])
        TopicTranslation.objects.create(topic=teens, language="sw", title="Kwa Vijana")
        self.assertEqual(self._slugs(self._get("teens", "sw")["articles"]), ["can-i-have-doubts"])

    def test_an_unknown_audience_is_not_found(self):
        self.assertEqual(self.client.get(self.URL.format("adults", "en")).status_code, 404)

    def test_languages_name_every_language_with_something_to_show(self):
        self._book("bfg-1", series=self.series)  # en: a named series
        self._book("bfg-1", language="sw", series=self.series)  # sw: series unnamed there
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children", language="am")  # am: a retelling
        self._book("north-wind", language="lg")  # lg: a topic book, topic titled there
        self._book("north-wind", language="hi")  # hi: topic untitled there
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        TopicTranslation.objects.create(topic=self.topic, language="lg", title="Abaana")
        self.assertEqual(self._get()["languages"], ["am", "en", "lg"])

    def test_modern_english_is_never_a_language(self):
        self._book("north-wind")
        self._book("north-wind", language="en-modern")
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        self.assertEqual(self._get()["languages"], ["en"])

    def test_the_languages_index_answers_for_both_hubs_at_once(self):
        self._book("bfg-1", series=self.series)
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-teens", language="am")
        response = self.client.get("/api/library/audiences/")
        self.assertEqual(response.json(), {"young_readers": ["en"], "teens": ["am"]})

    def test_each_hub_audience_has_an_edition_suffix_of_the_convention(self):
        self.assertEqual(set(AUDIENCE_EDITION_SUFFIX.values()), set(EDITION_SUFFIXES))
        self.assertEqual(set(AUDIENCE_EDITION_SUFFIX), set(AUDIENCE_TOPICS))

    def test_start_is_the_first_preferred_book_the_hub_holds_else_its_first(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("north-wind")
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        self.assertEqual(self._get()["start"], "pilgrims-progress-children")
        Book.objects.filter(slug="pilgrims-progress-children").update(is_published=False)
        self.assertEqual(self._get()["start"], "north-wind")
        self.assertIsNone(self._get("teens")["start"])

    def test_every_start_pick_names_a_real_book(self):
        # A renamed or retired slug would fall through to the hub's first book
        # in silence. Checked against the fixture, so a content PR trips it.
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        missing = [
            slug
            for picks in AUDIENCE_STARTS.values()
            for slug in picks
            if not (books / f"{slug}.en.json").exists()
        ]
        self.assertEqual(missing, [])


class BookAgesTests(TestCase):
    """The book page's "Ages 8–12" (`serializers.book_ages`)."""

    def setUp(self):
        self.author = Author.objects.create(slug="bunyan", name="John Bunyan")

    def _ages(self, slug, *, series=None):
        Book.objects.create(
            author=self.author, slug=slug, language="en", title=slug, series=series,
            is_published=True,
        )
        response = self.client.get(f"/api/library/books/{slug}/?language=en")
        self.assertEqual(response.status_code, 200)
        return response.json()["ages"]

    def test_a_series_range_wins(self):
        series = Series.objects.create(
            slug="rooted", title="Rooted", audience="young_readers", min_age=9, max_age=12
        )
        self.assertEqual(self._ages("rooted-1", series=series), {"min_age": 9, "max_age": 12})

    def test_a_series_without_a_range_has_none_never_guessed(self):
        series = Series.objects.create(slug="straight-talk", title="Straight Talk", audience="teens")
        self.assertIsNone(self._ages("straight-talk-teens", series=series))

    def test_a_retold_edition_reads_its_audiences(self):
        Book.objects.create(author=self.author, slug="pilgrims-progress", title="PP", language="sw")
        self.assertEqual(self._ages("pilgrims-progress-children"), {"min_age": 8, "max_age": 12})

    def test_a_suffix_alone_and_everything_else_have_no_ages(self):
        self.assertIsNone(self._ages("divine-songs-for-children"))
        self.assertIsNone(self._ages("all-of-grace"))
        adults = Series.objects.create(slug="key-teachings", title="KT", audience="adults")
        self.assertIsNone(self._ages("kt-1", series=adults))
