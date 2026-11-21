"""Suggestions as you type: a few letters open a person, a work or a shelf."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, SearchQueryLog, Sermon, Topic


class CompleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        moody = Author.objects.create(slug="dwight-l-moody", name="Dwight L. Moody")
        Book.objects.create(author=moody, slug="the-way-to-god", language="en", title="The Way to God")
        Book.objects.create(author=moody, slug="secret-power", language="en", title="Secret Power")
        spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="Charles H. Spurgeon")
        Sermon.objects.create(author=spurgeon, slug="s", language="en", title="S", body_html="<p>x</p>")
        Topic.objects.create(slug="prayer", title="Prayer", is_published=True)
        Book.objects.create(author=moody, slug="prevailing-prayer", language="en", title="Prevailing Prayer")

    def complete(self, q, language="en"):
        res = self.client.get("/api/library/search/complete/", {"q": q, "language": language})
        self.assertEqual(res.status_code, 200)
        return res.data["results"]

    def names(self, q, language="en"):
        out = []
        for h in self.complete(q, language):
            out.append(h.get("author_name") if h["type"] == "author"
                       else h.get("book_title") or h.get("topic_title"))
        return out

    def test_two_letters_of_a_surname_find_the_person(self):
        self.assertEqual(self.names("mo")[0], "Dwight L. Moody")
        self.assertEqual(self.names("spur")[0], "Charles H. Spurgeon")
        self.assertEqual(self.names("d l mo")[0], "Dwight L. Moody")

    def test_titles_and_shelves_open_by_their_first_letters(self):
        self.assertEqual(self.names("the way to g"), ["The Way to God"])
        self.assertEqual(self.names("pra")[0], "Prayer")  # the shelf, shortest
        self.assertIn("Prevailing Prayer", self.names("pra"))

    def test_another_language_spelling(self):
        self.assertEqual(self.names("Муд"), ["Dwight L. Moody"])

    def test_too_short_or_nothing_and_never_logged(self):
        self.assertEqual(self.complete("m"), [])
        self.assertEqual(self.complete("zzq"), [])
        self.assertEqual(SearchQueryLog.objects.count(), 0)
