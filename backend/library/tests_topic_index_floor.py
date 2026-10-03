"""A topical shelf is indexed in a language only once it holds enough there.

Below ``TOPIC_INDEX_MIN_WORKS`` works the page is a title and a card or two:
still served, but the list flags it ``indexable: False`` (the sitemap drops it,
the page adds noindex) and the other editions' hreflang stop naming it.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Author,
    Book,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from .serializers import TOPIC_INDEX_MIN_WORKS


class TopicIndexFloorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A", bio="A bio.")
        self.topic = Topic.objects.create(slug="prayer", title="Prayer", is_published=True)
        TopicTranslation.objects.create(topic=self.topic, language="sw", title="Maombi")
        # English reaches the floor with books alone; Swahili has one book and
        # one sermon — on the shelf, but below the floor.
        for n in range(TOPIC_INDEX_MIN_WORKS):
            Book.objects.create(
                author=author, slug=f"b{n}", language="en", title=f"B{n}", is_published=True
            )
            TopicBook.objects.create(topic=self.topic, book_slug=f"b{n}")
        Book.objects.create(author=author, slug="b0", language="sw", title="K", is_published=True)
        Sermon.objects.create(author=author, slug="s0", language="sw", title="H", is_published=True)
        TopicSermon.objects.create(topic=self.topic, sermon_slug="s0")

    def _list(self, lang):
        return {t["slug"]: t for t in self.client.get(f"/api/library/topics/?language={lang}").data}

    def test_the_list_flags_a_shelf_below_the_floor_and_keeps_it_listed(self):
        self.assertTrue(self._list("en")["prayer"]["indexable"])
        # Still on the Swahili shelf list — readers browse it — just not indexed.
        self.assertFalse(self._list("sw")["prayer"]["indexable"])

    def test_the_detail_carries_the_same_flag(self):
        res = self.client.get("/api/library/topics/prayer/?language=sw")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["indexable"])

    def test_hreflang_names_only_the_indexed_editions(self):
        res = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual(res.data["available_languages"], ["en"])
        # One more Swahili work reaches the floor, and the alternate appears.
        Book.objects.create(
            author=Author.objects.get(slug="a"),
            slug="b1",
            language="sw",
            title="K2",
            is_published=True,
        )
        res = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual(res.data["available_languages"], ["en", "sw"])

    def test_unpublished_works_do_not_count(self):
        Book.objects.filter(language="en").update(is_published=False)
        self.assertNotIn("prayer", self._list("en"))
        res = self.client.get("/api/library/topics/prayer/?language=sw")
        self.assertEqual(res.data["available_languages"], [])
