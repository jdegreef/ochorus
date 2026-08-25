"""The admin import endpoints — the only admin API that CREATES content rows.

`AdminAuthorCreateView` and `AdminImportPublishView` write Authors, Books,
Chapters and Sermons straight into the library, behind ten distinct validation
branches, and had no tests at all. Everything else under /api/admin/ reads or
flips a flag; these two are how content gets in.

Covers each refusal, both create paths, and the collision loop in
`_unique_author_slug` — which nothing exercised, so a second author of the same
name was an untested code path on a column with a unique constraint.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Author, Book, Sermon


@override_settings(DEBUG=True)
class AdminAuthorCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _post(self, payload):
        return self.client.post("/api/admin/authors/", payload, format="json")

    def test_creates_a_stub_author(self):
        res = self._post({"name": "Amy Carmichael"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["slug"], "amy-carmichael")
        self.assertEqual(res.data["book_count"], 0)
        self.assertTrue(Author.objects.filter(slug="amy-carmichael").exists())

    def test_a_blank_name_is_refused(self):
        for payload in ({"name": ""}, {"name": "   "}, {}):
            with self.subTest(payload=payload):
                res = self._post(payload)
                self.assertEqual(res.status_code, 400)
                self.assertIn("name", res.data["detail"].lower())

    def test_a_second_author_of_the_same_name_gets_a_distinct_slug(self):
        """The collision loop — untested, on a column with a unique constraint."""
        first = self._post({"name": "John Smith"})
        second = self._post({"name": "John Smith"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["slug"], second.data["slug"])
        self.assertEqual(second.data["slug"], "john-smith-2")

    def test_a_name_that_slugifies_to_nothing_still_gets_a_slug(self):
        res = self._post({"name": "上帝"})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["slug"])

    def test_the_name_is_capped_to_the_column(self):
        res = self._post({"name": "A" * 400})
        self.assertEqual(res.status_code, 201)
        author = Author.objects.get(slug=res.data["slug"])
        self.assertLessEqual(len(author.name), 200)
        self.assertLessEqual(len(author.slug), 120)


@override_settings(DEBUG=True)
class AdminImportPublishTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")

    def setUp(self):
        self.client = APIClient()

    def _publish(self, **payload):
        return self.client.post("/api/admin/import/publish/", payload, format="json")

    # -- the refusals ---------------------------------------------------------

    def test_an_unknown_kind_is_refused(self):
        for kind in ("", "plan", "Book"):
            with self.subTest(kind=kind):
                res = self._publish(kind=kind, title="T", author_slug="am")
                self.assertEqual(res.status_code, 400)

    def test_a_missing_title_is_refused(self):
        res = self._publish(kind="book", title="   ", author_slug="am")
        self.assertEqual(res.status_code, 400)
        self.assertIn("title", res.data["detail"].lower())

    def test_an_unknown_author_is_refused(self):
        res = self._publish(kind="book", title="T", author_slug="nobody")
        self.assertEqual(res.status_code, 400)
        self.assertIn("author", res.data["detail"].lower())

    def test_a_book_with_no_chapters_is_refused(self):
        for chapters in ([], None, "not-a-list"):
            with self.subTest(chapters=chapters):
                res = self._publish(
                    kind="book", title="T", author_slug="am", chapters=chapters
                )
                self.assertEqual(res.status_code, 400)

    def test_a_sermon_with_an_empty_body_is_refused(self):
        res = self._publish(kind="sermon", title="T", author_slug="am", body_html="  ")
        self.assertEqual(res.status_code, 400)
        self.assertIn("empty", res.data["detail"].lower())

    def test_a_non_string_sermon_body_is_refused_not_a_500(self):
        """`(d.get("body_html") or "").strip()` assumed a string.

        A client sending a number reached `.strip()` on an int and raised
        AttributeError — a 500 from a validation branch, on an endpoint whose
        whole job is to validate.
        """
        res = self._publish(kind="sermon", title="T", author_slug="am", body_html=123)
        self.assertEqual(res.status_code, 400)

    # -- the create paths -----------------------------------------------------

    def test_publishing_a_book_creates_it_with_its_chapters(self):
        res = self._publish(
            kind="book",
            title="Humility",
            author_slug="am",
            # NB: the chapter key is `html`, not `body_html` — and a chapter
            # with fewer than five readable words is skipped by create_book.
            chapters=[
                {"title": "One", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"},
                {"title": "Two", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"},
            ],
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["kind"], "book")
        self.assertEqual(res.data["chapters"], 2)
        book = Book.objects.get(slug=res.data["slug"])
        self.assertEqual(book.author, self.author)
        self.assertEqual(book.chapters.count(), 2)

    def test_publishing_a_sermon_creates_it(self):
        res = self._publish(
            kind="sermon",
            title="On Humility",
            author_slug="am",
            body_html="<p>Consider the grace of humility, and the Lord who taught it.</p>",
            scripture_ref="Phil 2:5",
        )
        self.assertEqual(res.status_code, 201)
        sermon = Sermon.objects.get(slug=res.data["slug"])
        self.assertEqual(sermon.scripture_ref, "Phil 2:5")
        self.assertIn("humility", sermon.body_html)

    def test_two_books_of_the_same_title_do_not_collide(self):
        payload = {
            "kind": "book",
            "title": "Humility",
            "author_slug": "am",
            "chapters": [{"title": "One", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"}],
        }
        first = self._publish(**payload)
        second = self._publish(**payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["slug"], second.data["slug"])

    # -- the language gap -----------------------------------------------------

    def test_an_unknown_language_is_refused(self):
        """Free-text language put content in a locale that does not exist.

        `create_book` also stamps every upload PUBLIC_DOMAIN, so a book landing
        under a bogus code is presented as a public-domain original — invisible
        to the review queue, which lists only ai_unreviewed rows.
        """
        res = self._publish(
            kind="book",
            title="T",
            author_slug="am",
            language="klingon",
            chapters=[{"title": "One", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"}],
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Book.objects.filter(language="klingon").exists())

    def test_a_known_language_is_accepted(self):
        res = self._publish(
            kind="book",
            title="Humildad",
            author_slug="am",
            language="es",
            chapters=[{"title": "Uno", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"}],
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Book.objects.get(slug=res.data["slug"]).language, "es")
