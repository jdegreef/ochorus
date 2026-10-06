"""`/api/library/audiences/<audience>/` — the /young-readers/ and /teens/ hubs.

Pinned here: each book appears once (series, then retold editions, then the
curated topic's remainder); a suffix alone does not make a retelling (the full
text must exist); a plan is offered only when every book it reads is the hub's;
nothing falls back to English; and an unknown audience is a 404.
"""

from __future__ import annotations

from django.test import TestCase

from .models import (
    Author,
    Book,
    Plan,
    PlanDay,
    Series,
    Topic,
    TopicBook,
    TopicTranslation,
)


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
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")  # not in it
        self.assertEqual(self._get()["printable"], ["brave-for-god"])

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
