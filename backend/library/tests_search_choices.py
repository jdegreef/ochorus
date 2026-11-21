"""Readers' choices: the result opened again and again for a query rises."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, SearchClickLog


class ChoicesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        for slug, title in (
            ("abide-in-christ", "Abide in Christ"),
            ("with-christ", "With Christ in the School of Prayer"),
            ("the-spirit-of-christ", "The Spirit of Christ"),
        ):
            Book.objects.create(author=murray, slug=slug, language="en", title=title)

    def books(self, q="christ"):
        res = self.client.get("/api/library/search/", {"q": q, "language": "en"})
        return [h for h in res.data["results"] if h["type"] == "book"]

    def click(self, key, times, q="christ"):
        for _ in range(times):
            self.client.post(
                "/api/library/search-click/?language=en",
                {"query": q, "type": key.split(":")[0], "position": 2, "key": key},
                format="json",
            )

    def test_the_key_is_recorded_only_when_shaped_like_one(self):
        self.click("book:abide-in-christ", 1)
        self.click("book:<script>", 1)
        self.click("chapter:abide-in-christ:3", 1)
        self.assertEqual(
            sorted(SearchClickLog.objects.values_list("result_key", flat=True)),
            ["", "book:abide-in-christ", "chapter:abide-in-christ:3"],
        )

    def test_a_result_opened_again_and_again_rises_and_then_leads(self):
        before = [b["book_slug"] for b in self.books()]
        last = before[-1]
        self.click(f"book:{last}", 2)
        self.assertEqual([b["book_slug"] for b in self.books()], before)  # two isn't enough
        self.click(f"book:{last}", 1)
        lifted = self.books()
        self.assertEqual(lifted[0]["book_slug"], last)
        self.assertNotIn("chosen", lifted[0])
        self.click(f"book:{last}", 2)
        self.assertTrue(self.books()[0].get("chosen"))
        # Another query's clicks don't count.
        self.assertEqual([b["book_slug"] for b in self.books("spirit of christ")][0], "the-spirit-of-christ")
