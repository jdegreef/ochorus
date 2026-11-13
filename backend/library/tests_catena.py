"""What the Church has said on a verse: a Bible chapter's catena, read back from
the catena's own chapters (library/catena), and the API that serves it."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .catena import CATENAS, _chapter_map, first_chapter, passages
from .management.commands.build_catena import BOOKS
from .models import Author, Book, Chapter, Series

LIBRARY = Path(settings.BASE_DIR) / "library"
EDITORIAL = LIBRARY / "data" / "catena"
FIXTURES = LIBRARY / "fixtures" / "content" / "books"


def shipped_catenas():
    """(book code, its editorial book.json, its fixture rows) for every catena
    whose fixture has shipped."""
    for meta_path in sorted(EDITORIAL.glob("*/book.json")):
        meta = json.loads(meta_path.read_text("utf-8"))
        fixture = FIXTURES / f"{meta['slug']}.en.json"
        if fixture.is_file():
            yield meta_path.parent.name, meta, json.loads(fixture.read_text("utf-8"))


def verse(ref: str) -> tuple[int, int]:
    """'3:14–16', '7:53–8:11' or an excerpt id's 'JHN.3.14-16' -> where it starts."""
    m = re.search(r"(\d+)[:.](\d+)", ref)
    return int(m[1]), int(m[2])


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
    """The index reads the real books the way build_catena lays them out — so a
    change to that markup fails here rather than silently emptying or
    misattributing the reader's panel."""

    def test_every_shipped_catena_is_paired_with_its_bible_book(self):
        shipped = list(shipped_catenas())
        self.assertTrue(shipped)
        for code, meta, _ in shipped:
            self.assertEqual(CATENAS.get(BOOKS[code][1]), meta["slug"], f"add {code} to catena.CATENAS")

    def test_the_index_agrees_with_the_selection(self):
        """Every excerpt selection.json chose sits under the block that quotes
        its first verse (the last commented block at or before it), within its
        own passage, attributed to its voice — and nothing else is there."""
        for code, meta, rows in shipped_catenas():
            voices = {v["id"]: (v["name"], v["work"]) for v in meta["voices"]}
            selection = json.loads((EDITORIAL / code / "selection.json").read_text("utf-8"))["passages"]
            blocks = [
                b
                for r in rows
                if r["model"] == "library.chapter"
                for b in passages(r["fields"]["body_html"])
            ]
            starts = [verse(b["ref"]) for b in blocks]
            self.assertEqual(starts, sorted(starts), code)
            expected = Counter()
            for k, passage in enumerate(selection):
                lo = verse(passage["start"])
                hi = verse(selection[k + 1]["start"]) if k + 1 < len(selection) else (999, 999)
                for excerpt_id in passage["excerpts"]:
                    at = verse(excerpt_id)
                    home = max(i for i, s in enumerate(starts) if s <= max(at, lo))
                    self.assertTrue(lo <= starts[home] < hi, (code, excerpt_id, blocks[home]["ref"]))
                    expected[(blocks[home]["ref"], *voices[excerpt_id.split(".")[0]])] += 1
            actual = Counter(
                (b["ref"], e["author"], e["work"]) for b in blocks for e in b["excerpts"]
            )
            self.assertEqual(actual, expected, code)
            for b in blocks:
                self.assertTrue(b["text"] and b["reference"].endswith(b["ref"]), b)
                for e in b["excerpts"]:
                    self.assertTrue(e["text"], (b["reference"], e))


def catena_chapter(*parts: str) -> str:
    return " ".join(parts)


#: A catena on John, cut down: its "John 8" opens with 7:53–8:11, which most
#: of its verses put there although it begins in John 7.
CATENA_BODIES = {
    (4, "John 3"): BODY.split("<h3>The Next Passage</h3>")[0],
    (8, "John 7"): catena_chapter(
        "<h3>At the Festival</h3>",
        block("After this Jesus went about in Galilee.", "John 7:1"),
        excerpt("Augustine", "Tractates on John", "He walked in Galilee."),
    ),
    (9, "John 8"): catena_chapter(
        "<h3>The Woman Caught in Adultery</h3>",
        block("They went each to his own house.", "John 7:53–8:11"),
        excerpt("J. C. Ryle", "Expository Thoughts on John", "A famous passage."),
        "<h3>The Light of the World</h3>",
        block("I am the light of the world.", "John 8:12"),
        excerpt("John Calvin", "Commentary on John", "Christ is the light."),
    ),
}
class CatenaApiTests(TestCase):
    def setUp(self):
        _chapter_map.cache_clear()  # per deploy in production; per test here
        self.client = APIClient()
        author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        series = Series.objects.create(slug="the-bible", title="The Bible")
        self.john = Book.objects.create(
            author=author, slug="gospel-of-john", language="en", title="The Gospel of John",
            series=series, series_position=43,
        )
        for order, title in [(1, "Introduction"), (4, "John 3"), (6, "John 5"), (8, "John 7"), (9, "John 8")]:
            Chapter.objects.create(book=self.john, order=order, title=title, body_html="<p>x</p>")
        self.catena = Book.objects.create(
            author=author, slug="catena-on-john", language="en", title="A Catena on John",
        )
        Chapter.objects.create(book=self.catena, order=1, title="Introduction", body_html="<p>x</p>")
        for (order, title), body in CATENA_BODIES.items():
            Chapter.objects.create(book=self.catena, order=order, title=title, body_html=body)

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
                "verses": ["3:1–2"],
            },
        )

    def test_a_span_belongs_to_the_chapter_its_first_verse_is_in(self):
        john7 = self._chapter("gospel-of-john", 8)["catena"]
        self.assertEqual((john7["chapter"], john7["verses"]), (8, ["7:1", "7:53–8:11"]))
        self.assertEqual(self._chapter("gospel-of-john", 9)["catena"]["verses"], ["8:12"])
        # Its link opens the catena chapter it is IN.
        res = self.client.get("/api/library/books/gospel-of-john/chapters/8/catena/")
        self.assertEqual([(p["ref"], p["chapter"]) for p in res.data["passages"]], [("7:1", 8), ("7:53–8:11", 9)])
        self.assertEqual(first_chapter("7:53–8:11"), 7)

    def test_the_endpoint_serves_the_excerpts(self):
        res = self.client.get("/api/library/books/gospel-of-john/chapters/4/catena/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["catena"], {"slug": "catena-on-john", "title": "A Catena on John", "chapter": 4})
        self.assertEqual(res.data["passages"], [{**p, "chapter": 4} for p in passages(BODY)[:1]])
        self.assertIn("Cache-Control", res)

    def test_chapters_the_catena_does_not_treat_have_none(self):
        # The introduction, a chapter the catena has no chapter on, and any
        # other book (the catena itself included).
        for slug, order in [("gospel-of-john", 1), ("gospel-of-john", 6), ("catena-on-john", 4)]:
            self.assertIsNone(self._chapter(slug, order)["catena"])
            res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/catena/")
            self.assertEqual(res.status_code, 404)

    def test_an_unpublished_catena_is_not_offered(self):
        self.catena.is_published = False
        self.catena.save()
        self.assertIsNone(self._chapter("gospel-of-john", 4)["catena"])

    def test_a_served_passage_cannot_change_the_cached_index(self):
        res = self.client.get("/api/library/books/gospel-of-john/chapters/4/catena/")
        res.data["passages"][0]["excerpts"].clear()
        again = self.client.get("/api/library/books/gospel-of-john/chapters/4/catena/")
        self.assertEqual(len(again.data["passages"][0]["excerpts"]), 2)

    def test_a_chapter_costs_one_query_for_its_catena(self):
        from .catena import CatenaLookup

        self._chapter("gospel-of-john", 4)  # the chapter map, once per deploy
        lookup_book = Book.objects.select_related("series").get(pk=self.john.pk)
        chapter = Chapter.objects.get(book=self.john, order=4)
        with self.assertNumQueries(1):
            self.assertIsNotNone(CatenaLookup(lookup_book).summary(chapter))

    def test_the_batch_agrees_with_the_single_endpoint(self):
        res = self.client.get("/api/library/books/gospel-of-john/chapters/?language=en")
        for chapter in res.data:
            self.assertEqual(chapter["catena"], self._chapter("gospel-of-john", chapter["order"])["catena"])
