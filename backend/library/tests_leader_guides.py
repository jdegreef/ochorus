"""Printable leader's guides — ``data/leader_guides/<slug>.<language>.json``.

The files are keyed by slug + language, not joined to a row, so nothing in the
schema stops one pointing at a renamed edition or skipping a chapter. The file
gates below do; the API tests pin ``/api/library/books/<slug>/guide/``, the
book detail's ``has_guide`` and the audience hub's ``guides`` shelf.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase

from . import leader_guides
from .leader_guides import chapter_extras, guides, problems
from .models import Author, Book, Chapter, Topic, TopicBook

BOOKS = Path(__file__).parent / "fixtures" / "content" / "books"


def _week(order: int) -> dict:
    return {
        "chapter": order,
        "summary": f"What happens in chapter {order}.",
        "memory_verse": {
            "text": "Your word is a lamp to my feet.",
            "reference": "Psalm 119:105",
        },
        "activity": {
            "title": "Lamp walk",
            "materials": "Nothing",
            "steps": ["Stand in a line.", "Walk slowly.", "Stop at the door."],
        },
    }


def _guide(orders) -> dict:
    return {
        "intro": [
            "For leaders of a small group.",
            "Each session runs about 30 minutes.",
        ],
        "weeks": [_week(o) for o in orders],
    }


class GuideFileTests(SimpleTestCase):
    """Every shipped guide names a published edition and covers it whole."""

    def test_every_guide_names_a_published_edition_and_covers_it(self):
        for (slug, language), guide in sorted(guides().items()):
            with self.subTest(guide=f"{slug}.{language}"):
                path = BOOKS / f"{slug}.{language}.json"
                self.assertTrue(path.exists(), f"no fixture edition {path.name}")
                rows = json.loads(path.read_text(encoding="utf-8"))
                book = rows[0]
                self.assertEqual(book["model"], "library.book")
                self.assertTrue(
                    book["fields"].get("is_published"), "the edition is unpublished"
                )
                orders = sorted(
                    r["fields"]["order"]
                    for r in rows
                    if r["model"] == "library.chapter"
                )
                self.assertEqual(problems(guide, orders), [])

    def test_file_names_are_slug_dot_language(self):
        for path in leader_guides.DATA_DIR.glob("*.json"):
            with self.subTest(path=path.name):
                slug, _, language = path.stem.rpartition(".")
                self.assertTrue(slug and language and "." not in slug)


class GuideProblemTests(SimpleTestCase):
    def test_a_whole_guide_has_no_problems(self):
        self.assertEqual(problems(_guide([1, 2, 3]), [1, 2, 3]), [])

    def test_a_skipped_repeated_or_reordered_chapter_is_caught(self):
        for orders in ([1, 3], [1, 2, 2, 3], [2, 1, 3]):
            with self.subTest(orders=orders):
                self.assertTrue(problems(_guide(orders), [1, 2, 3]))

    def test_empty_fields_and_step_counts_are_caught(self):
        guide = _guide([1])
        guide["weeks"][0]["summary"] = " "
        guide["weeks"][0]["memory_verse"]["reference"] = ""
        guide["weeks"][0]["activity"]["steps"] = ["One.", "Two."]
        found = problems(guide, [1])
        self.assertEqual(len(found), 3, found)
        guide = _guide([1])
        guide["weeks"][0]["activity"]["steps"] = ["Step."] * 6
        self.assertTrue(problems(guide, [1]))

    def test_intro_must_be_a_list_of_strings(self):
        for intro in ([], "One paragraph.", [""], [1]):
            with self.subTest(intro=intro):
                guide = _guide([1])
                guide["intro"] = intro
                self.assertTrue(problems(guide, [1]))

    def test_html_anywhere_is_caught(self):
        guide = _guide([1])
        guide["weeks"][0]["activity"]["steps"][1] = "Walk <em>slowly</em>."
        self.assertTrue(any("HTML" in p for p in problems(guide, [1])))
        # A lone angle bracket in prose is not markup.
        guide["weeks"][0]["activity"]["steps"][1] = "Count 3 < 5 together."
        self.assertEqual(problems(guide, [1]), [])


class ChapterExtrasTests(SimpleTestCase):
    def test_the_opening_verse_and_closing_prayer(self):
        body = (
            "<blockquote>“What must I do to be saved?” — from Acts 16</blockquote> "
            "<p>Christian ran.</p> <p><em>Dear God, help me run to you. Amen.</em></p>"
        )
        self.assertEqual(
            chapter_extras(body),
            {
                "verse": "“What must I do to be saved?” — from Acts 16",
                "prayer": "Dear God, help me run to you. Amen.",
            },
        )

    def test_a_partly_emphasised_last_paragraph_is_not_a_prayer(self):
        body = "<p>He said <em>no</em> and left.</p>"
        self.assertEqual(chapter_extras(body), {"verse": "", "prayer": ""})

    def test_a_blockquote_that_does_not_lead_is_not_the_verse(self):
        body = "<p>First.</p><blockquote>Later quote.</blockquote><p>End.</p>"
        self.assertEqual(chapter_extras(body)["verse"], "")

    def test_an_empty_body(self):
        self.assertEqual(chapter_extras(""), {"verse": "", "prayer": ""})


class _GuideDirMixin:
    """Point the loader at a temp directory holding one guide."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.object(leader_guides, "DATA_DIR", Path(self._tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.author = Author.objects.create(slug="john-bunyan", name="John Bunyan")

    def write_guide(self, slug, language, guide):
        Path(self._tmp.name, f"{slug}.{language}.json").write_text(
            json.dumps(guide), encoding="utf-8"
        )
        leader_guides._load.cache_clear()
        self.addCleanup(leader_guides._load.cache_clear)

    def book(self, slug, language="en", *, chapters=2, published=True):
        book = Book.objects.create(
            author=self.author,
            slug=slug,
            language=language,
            title=f"{slug} title",
            is_published=published,
        )
        for order in range(1, chapters + 1):
            Chapter.objects.create(
                book=book,
                order=order,
                title=f"Chapter {order}",
                study_questions=[{"question": f"Q{order}?", "answer": f"A{order}."}],
                body_html=(
                    f"<blockquote>“Verse {order}” — from Psalm 23</blockquote> "
                    f"<p>Story {order}.</p> <p><em>Dear God, prayer {order}. Amen.</em></p>"
                ),
            )
        return book


class BookGuideApiTests(_GuideDirMixin, TestCase):
    URL = "/api/library/books/{}/guide/?language={}"

    def test_the_guide_joins_each_week_to_its_chapter(self):
        self.book("pilgrims-progress-children")
        self.write_guide("pilgrims-progress-children", "en", _guide([1, 2]))
        res = self.client.get(self.URL.format("pilgrims-progress-children", "en"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["book"]["slug"], "pilgrims-progress-children")
        self.assertEqual(data["book"]["title"], "pilgrims-progress-children title")
        self.assertEqual(data["book"]["author"]["slug"], "john-bunyan")
        self.assertIn("cover_url", data["book"])
        self.assertEqual(data["available_languages"], ["en"])
        self.assertEqual(data["intro"], _guide([1])["intro"])
        self.assertEqual([w["chapter"] for w in data["weeks"]], [1, 2])
        week = data["weeks"][1]
        self.assertEqual(week["title"], "Chapter 2")
        self.assertEqual(week["summary"], "What happens in chapter 2.")
        self.assertEqual(week["memory_verse"]["reference"], "Psalm 119:105")
        self.assertEqual(len(week["activity"]["steps"]), 3)
        self.assertEqual(week["questions"], [{"question": "Q2?", "answer": "A2."}])
        self.assertEqual(week["verse"], "“Verse 2” — from Psalm 23")
        self.assertEqual(week["prayer"], "Dear God, prayer 2. Amen.")

    def test_no_guide_file_is_a_404(self):
        self.book("pilgrims-progress-children")
        res = self.client.get(self.URL.format("pilgrims-progress-children", "en"))
        self.assertEqual(res.status_code, 404)

    def test_an_unpublished_edition_is_a_404(self):
        self.book("pilgrims-progress-children", published=False)
        self.write_guide("pilgrims-progress-children", "en", _guide([1, 2]))
        res = self.client.get(self.URL.format("pilgrims-progress-children", "en"))
        self.assertEqual(res.status_code, 404)

    def test_no_english_fallback(self):
        self.book("pilgrims-progress-children")
        self.book("pilgrims-progress-children", "es")
        self.write_guide("pilgrims-progress-children", "en", _guide([1, 2]))
        res = self.client.get(self.URL.format("pilgrims-progress-children", "es"))
        self.assertEqual(res.status_code, 404)

    def test_the_book_detail_says_whether_a_guide_exists(self):
        self.book("pilgrims-progress-children")
        self.book("pilgrims-progress-teens")
        self.write_guide("pilgrims-progress-children", "en", _guide([1, 2]))
        detail = "/api/library/books/{}/?language=en"
        self.assertIs(
            self.client.get(detail.format("pilgrims-progress-children")).json()[
                "has_guide"
            ],
            True,
        )
        self.assertIs(
            self.client.get(detail.format("pilgrims-progress-teens")).json()[
                "has_guide"
            ],
            False,
        )


class AudienceGuidesTests(_GuideDirMixin, TestCase):
    URL = "/api/library/audiences/{}/?language={}"

    def test_the_hub_lists_its_guided_books_in_shelf_order(self):
        for slug in (
            "pilgrims-progress",
            "pilgrims-progress-children",
            "north-wind",
            "a-retrospect",
            "a-retrospect-children",
            "elsewhere",
        ):
            self.book(slug)
        topic = Topic.objects.create(
            slug="for-young-readers", title="For Young Readers"
        )
        TopicBook.objects.create(topic=topic, book_slug="north-wind")
        for slug in ("north-wind", "pilgrims-progress-children", "elsewhere"):
            self.write_guide(slug, "en", _guide([1, 2]))
        data = self.client.get(self.URL.format("young_readers", "en")).json()
        editions = [b["slug"] for b in data["editions"]]
        self.assertIn("pilgrims-progress-children", editions)
        # Editions before the topic's remainder; a guided book not on the hub
        # ("elsewhere") is not listed.
        self.assertEqual(
            [b["slug"] for b in data["guides"]],
            ["pilgrims-progress-children", "north-wind"],
        )
        self.assertIn("cover_url", data["guides"][0])

    def test_no_guides_in_another_language(self):
        self.book("pilgrims-progress", "es")
        self.book("pilgrims-progress-children", "es")
        self.write_guide("pilgrims-progress-children", "en", _guide([1, 2]))
        data = self.client.get(self.URL.format("young_readers", "es")).json()
        self.assertEqual(data["guides"], [])
