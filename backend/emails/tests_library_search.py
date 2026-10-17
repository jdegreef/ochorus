"""The designer's "Insert from the library" search (emails/library_search.py)."""

from __future__ import annotations

from django.test import TestCase, override_settings

from library.models import (
    Author,
    Book,
    Chapter,
    Plan,
    Quote,
    Sermon,
    Topic,
    TopicTranslation,
)

from . import blocks as blocks_mod
from . import library_search


def _library():
    murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray", bio="Pastor.")
    Author.objects.create(slug="murray-imprint", name="Murray Press", is_imprint=True)
    for lang, title in (("en", "Humility"), ("es", "Humildad")):
        Book.objects.create(author=murray, slug="humility-2", language=lang, title=title, cover_url="/covers/humility-2.png")
    book = Book.objects.get(slug="humility-2", language="en")
    chapter = Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
    Quote.objects.create(slug="q1", author=murray, text="Humility is the only soil in which the graces root.", chapter=chapter, paragraph=0, reviewed=True)
    Quote.objects.create(slug="q2", author=murray, text="Humility unreviewed.", chapter=chapter, paragraph=1)
    Sermon.objects.create(author=murray, slug="the-humble", language="en", title="On humility")
    Plan.objects.create(slug="humility-12-days", language="en", title="Humility in 12 days")
    topic = Topic.objects.create(slug="humility", title="Humility")
    TopicTranslation.objects.create(topic=topic, language="es", title="Humildad")


class SearchTests(TestCase):
    def setUp(self):
        _library()

    def test_one_query_finds_every_kind_with_its_block(self):
        data = library_search.search("humil")
        kinds = [r["kind"] for r in data["results"]]
        self.assertEqual(kinds, ["book", "sermon", "plan", "topic", "quote"])
        self.assertEqual(data["counts"]["quote"], 1)  # the unreviewed one is not offered
        book = data["results"][0]
        self.assertEqual(book["title"], "Humility")
        self.assertEqual(book["languages"], ["en", "es"])
        self.assertEqual(book["block"], {"type": "book", "slug": "humility-2", "label": ""})
        self.assertEqual(book["image"], "/covers/humility-2.png")
        quote = data["results"][-1]
        self.assertEqual(quote["block"]["type"], "quote")
        self.assertEqual(quote["block"]["attribution"], "Andrew Murray, Humility")
        self.assertEqual(quote["languages"], ["en"])
        topic = next(r for r in data["results"] if r["kind"] == "topic")
        self.assertEqual(topic["languages"], ["en", "es"])

    def test_an_author_name_finds_their_works_but_not_an_imprint(self):
        data = library_search.search("murray")
        kinds = {r["kind"] for r in data["results"]}
        self.assertTrue({"author", "book", "sermon", "quote"} <= kinds)
        self.assertEqual([r["title"] for r in data["results"] if r["kind"] == "author"], ["Andrew Murray"])

    def test_every_result_block_is_already_clean(self):
        for r in library_search.search("humil")["results"]:
            self.assertEqual(blocks_mod.clean([r["block"]]), [r["block"]])

    def test_short_queries_return_nothing(self):
        self.assertEqual(library_search.search("h")["results"], [])

    @override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
    def test_api(self):
        res = self.client.get("/api/admin/emails/library/search/?q=humil")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["counts"]["book"], 1)


class QuoteSourceTests(TestCase):
    def test_a_quote_from_an_unpublished_work_is_not_offered(self):
        author = Author.objects.create(slug="a", name="A")
        book = Book.objects.create(author=author, slug="hidden", language="en", title="Hidden", is_published=False)
        chapter = Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
        Quote.objects.create(slug="h", author=author, text="Grace upon grace", chapter=chapter, paragraph=0, reviewed=True)
        self.assertEqual(library_search.search("grace upon")["counts"]["quote"], 0)
