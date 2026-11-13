"""What the Church has said on a verse: a Bible chapter's catena, read back from
the catena's own chapters (library/catena), and the API that serves it."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .catena import catena_slugs, passages
from .models import Author, Book, Chapter, Series

CATENA_FIXTURE = (
    Path(settings.BASE_DIR) / "library" / "fixtures" / "content" / "books" / "catena-on-john.en.json"
)


def excerpt(name: str, work: str, *paras: str) -> str:
    return f"<p><strong>{name}</strong> · <em>{work}</em></p>" + "".join(f"<p>{p}</p>" for p in paras)


def block(text: str, cite: str) -> str:
    return f"<blockquote><p>{text}</p><p>— {cite}</p></blockquote>"


BODY = " ".join([
    "<h3>Jesus and Nicodemus</h3>",
    block("Now there was a man named Nicodemus.", "John 3:1–2"),
    excerpt("John Calvin", "Commentary on John", "Rabbi, we know.", "A second paragraph."),
    excerpt("Augustine", "Tractates on John", "Nicodemus came by night."),
    block("Jesus answered him.", "John 3:3"),  # no excerpt follows: left out
    "<h3>The Next Passage</h3>",
    "<p><em>The earliest manuscripts of John do not have John 7:53–8:11.</em></p>",
    block("They went each to his own house.", "John 7:53–8:11"),
    excerpt("J. C. Ryle", "Expository Thoughts on John", "word " * 80),
])


class PassagesTests(SimpleTestCase):
    def test_each_block_carries_the_excerpts_that_follow_it(self):
        found = passages(BODY)
        self.assertEqual([p["ref"] for p in found], ["3:1–2", "7:53–8:11"])
        first = found[0]
        self.assertEqual(first["reference"], "John 3:1–2")
        self.assertEqual(first["text"], "Now there was a man named Nicodemus.")
        self.assertEqual(
            first["excerpts"],
            [
                {"author": "John Calvin", "work": "Commentary on John", "text": "Rabbi, we know."},
                {"author": "Augustine", "work": "Tractates on John", "text": "Nicodemus came by night."},
            ],
        )

    def test_p_is_the_blocks_index_among_top_level_elements(self):
        # The reader's ?p= counts top-level elements, not the text nodes between them.
        self.assertEqual([p["p"] for p in passages(BODY)], [1, 10])

    def test_a_long_excerpt_is_cut_to_an_opening(self):
        text = passages(BODY)[1]["excerpts"][0]["text"]
        self.assertTrue(text.endswith("…"))
        self.assertLess(len(text.split()), 50)

    def test_an_empty_body_has_none(self):
        self.assertEqual(passages(""), ())


class ShippedCatenaTests(SimpleTestCase):
    """The index reads the real book the way build_catena lays it out — so a
    change to that layout fails here rather than emptying the reader's panel."""

    def test_every_chapter_of_john_has_commentary_on_its_verses(self):
        rows = json.loads(CATENA_FIXTURE.read_text("utf-8"))
        chapters = [r["fields"] for r in rows if r["model"] == "library.chapter"]
        johns = [c for c in chapters if c["title"].startswith("John ")]
        self.assertEqual(len(johns), 21)
        for c in johns:
            found = passages(c["body_html"])
            self.assertTrue(found, c["title"])
            for p in found:
                self.assertTrue(p["text"] and p["reference"].startswith("John "), p)
                self.assertTrue(1 <= len(p["excerpts"]) <= 6, p["reference"])
                for e in p["excerpts"]:
                    self.assertTrue(e["author"] and e["work"] and e["text"], (p["reference"], e))

    def test_the_bible_book_is_paired_with_its_catena_by_book_code(self):
        self.assertEqual(catena_slugs().get("gospel-of-john"), "catena-on-john")


class CatenaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        series = Series.objects.create(slug="the-bible", title="The Bible")
        self.john = Book.objects.create(
            author=author, slug="gospel-of-john", language="en", title="The Gospel of John",
            series=series, series_position=43,
        )
        for order, title in [(1, "Introduction"), (4, "John 3"), (5, "John 5")]:
            Chapter.objects.create(book=self.john, order=order, title=title, body_html="<p>x</p>")
        self.catena = Book.objects.create(
            author=author, slug="catena-on-john", language="en", title="A Catena on John",
        )
        Chapter.objects.create(book=self.catena, order=1, title="Introduction", body_html="<p>x</p>")
        Chapter.objects.create(book=self.catena, order=4, title="John 3", body_html=BODY)

    def _chapter(self, slug, order):
        res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/")
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_a_bible_chapter_names_its_catena_and_the_spans_it_comments_on(self):
        self.assertEqual(
            self._chapter("gospel-of-john", 4)["catena"],
            {
                "slug": "catena-on-john",
                "title": "A Catena on John",
                "chapter": 4,
                "verses": ["3:1–2", "7:53–8:11"],
            },
        )

    def test_the_endpoint_serves_the_excerpts(self):
        res = self.client.get("/api/library/books/gospel-of-john/chapters/4/catena/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["catena"], {"slug": "catena-on-john", "title": "A Catena on John", "chapter": 4})
        self.assertEqual(res.data["passages"], list(passages(BODY)))
        self.assertIn("Cache-Control", res)

    def test_chapters_the_catena_does_not_treat_have_none(self):
        # The introduction, a chapter the catena has no chapter on, and any
        # other book (the catena itself included).
        for slug, order in [("gospel-of-john", 1), ("gospel-of-john", 5), ("catena-on-john", 4)]:
            self.assertIsNone(self._chapter(slug, order)["catena"])
            res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/catena/")
            self.assertEqual(res.status_code, 404)

    def test_an_unpublished_catena_is_not_offered(self):
        self.catena.is_published = False
        self.catena.save()
        self.assertIsNone(self._chapter("gospel-of-john", 4)["catena"])

    def test_the_batch_agrees_with_the_single_endpoint(self):
        res = self.client.get("/api/library/books/gospel-of-john/chapters/?language=en")
        for chapter in res.data:
            self.assertEqual(chapter["catena"], self._chapter("gospel-of-john", chapter["order"])["catena"])
