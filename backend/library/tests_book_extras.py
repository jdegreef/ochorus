"""`Book.parts`, `Book.quiz` and `Chapter.summary` — editorial structure a work
carries beside its text.

All three are plain text written for readers and shipped in the work's own
fixture file, so the gates here are SHAPE: a part that starts at a chapter the
book does not have, a quiz answer that points past its options, or a summary
grown into an essay would each render wrong (or not at all) on a live page with
no error anywhere. Whether a summary is TRUE to its chapter is a human check.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from .models import Author, Book, Chapter

BOOKS = Path(__file__).resolve().parent / "fixtures" / "content" / "books"

#: "One or two sentences": past this the "In this chapter" note stops being a
#: note, and the meta description it feeds is cut mid-thought.
SUMMARY_MAX_CHARS = 420
QUIZ_OPTIONS = 4
QUIZ_KEYS = {"question", "options", "answer_index", "explanation", "chapter"}
PART_KEYS = {"title", "first_chapter", "year", "subtitle"}


def _carrying(*keys: str):
    """``(path, book_fields, chapter_fields)`` for every work file whose text
    mentions one of ``keys`` — a cheap substring test first, so the scan parses
    the handful of files that carry them rather than the whole library."""
    for path in sorted(BOOKS.glob("*.json")):
        text = path.read_text()
        if not any(f'"{k}"' in text for k in keys):
            continue
        rows = json.loads(text)
        book = next(r["fields"] for r in rows if r["model"] == "library.book")
        chapters = [r["fields"] for r in rows if r["model"] == "library.chapter"]
        yield path, book, chapters


class ShippedShapeTests(SimpleTestCase):
    def test_the_pilot_carries_all_three(self):
        """Guards the guards: an empty corpus would pass everything below."""
        rows = json.loads((BOOKS / "pilgrims-progress.en.json").read_text())
        book = rows[0]["fields"]
        chapters = [r["fields"] for r in rows[1:]]
        self.assertEqual([p["first_chapter"] for p in book["parts"]], [1, 13])
        self.assertEqual(len(book["quiz"]), 5)
        self.assertTrue(all(c.get("summary") for c in chapters))

    def test_parts_start_at_real_chapters_in_order(self):
        for path, book, chapters in _carrying("parts"):
            parts = book.get("parts") or []
            if not parts:
                continue
            with self.subTest(path.name):
                orders = {c["order"] for c in chapters}
                starts = [p.get("first_chapter") for p in parts]
                self.assertEqual(starts, sorted(set(starts)), "parts out of order")
                self.assertTrue(set(starts) <= orders, f"no such chapter: {starts}")
                for p in parts:
                    self.assertTrue(set(p) <= PART_KEYS, sorted(p))
                    self.assertTrue(str(p.get("title", "")).strip())
                    self.assertNotIn("<", p["title"] + p.get("subtitle", ""))

    def test_quiz_questions_are_answerable(self):
        for path, book, chapters in _carrying("quiz"):
            orders = {c["order"] for c in chapters}
            for i, q in enumerate(book.get("quiz") or []):
                with self.subTest(f"{path.name} #{i + 1}"):
                    self.assertEqual(set(q), QUIZ_KEYS)
                    self.assertEqual(len(q["options"]), QUIZ_OPTIONS)
                    self.assertEqual(len(set(q["options"])), QUIZ_OPTIONS)
                    self.assertIn(q["answer_index"], range(QUIZ_OPTIONS))
                    self.assertIn(q["chapter"], orders)
                    for text in [q["question"], q["explanation"], *q["options"]]:
                        self.assertTrue(text.strip())
                        self.assertNotIn("<", text)

    def test_summaries_are_short_plain_text(self):
        for path, _book, chapters in _carrying("summary"):
            for c in chapters:
                summary = c.get("summary", "")
                if not summary:
                    continue
                with self.subTest(f"{path.name} ch {c['order']}"):
                    self.assertLessEqual(len(summary), SUMMARY_MAX_CHARS)
                    self.assertNotIn("<", summary)
                    self.assertEqual(summary, summary.strip())


class SeedTests(TestCase):
    def test_the_seed_keeps_them_current(self):
        """Fixture-owned like `qa` and `study_questions`: nothing edits them
        on the live DB, so an edit to the committed file must reach an
        existing row on the next deploy."""
        from library.management.commands.seed_books import (
            CHAPTER_EXTRA_FIELDS,
            UPDATE_FIELDS,
        )

        self.assertIn("parts", UPDATE_FIELDS)
        self.assertIn("quiz", UPDATE_FIELDS)
        self.assertIn("summary", CHAPTER_EXTRA_FIELDS)

    def test_a_summary_edit_reaches_an_existing_chapter(self):
        from library.management.commands.seed_books import sync_chapters

        author = Author.objects.create(slug="a", name="A")
        book = Book.objects.create(author=author, slug="b", title="B")
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
        added, updated, _ = sync_chapters(
            book, [{"order": 1, "title": "One", "body_html": "<p>x</p>", "summary": "New."}]
        )
        self.assertEqual((added, updated), (0, 1))
        self.assertEqual(book.chapters.get().summary, "New.")
        # A row with no `summary` key (most of the library) is not a blanking.
        sync_chapters(book, [{"order": 1, "title": "One", "body_html": "<p>x</p>"}])
        self.assertEqual(book.chapters.get().summary, "New.")


class ChapterPayloadTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="john-bunyan", name="John Bunyan")
        self.book = Book.objects.create(
            author=author,
            slug="pp",
            title="PP",
            parts=[
                {"title": "Part One", "year": 1678, "first_chapter": 1},
                {"title": "Part Two", "year": 1684, "subtitle": "Christiana", "first_chapter": 3},
            ],
        )
        for order, title, summary in [
            (1, "The First Stage", "Christian sets out."),
            (2, "Conclusion", ""),
            (3, "The First Stage", "Christiana sets out."),
        ]:
            Chapter.objects.create(
                book=self.book, order=order, title=title, body_html="<p>x</p>", summary=summary
            )

    def _chapter(self, order):
        return self.client.get(f"/api/library/books/pp/chapters/{order}/").json()

    def test_a_chapter_names_its_part_and_its_repeated_title(self):
        data = self._chapter(3)
        self.assertEqual(
            data["part"], {"title": "Part Two", "year": 1684, "subtitle": "Christiana"}
        )
        self.assertTrue(data["title_repeats"])
        self.assertEqual(data["summary"], "Christiana sets out.")
        self.assertFalse(self._chapter(2)["title_repeats"])
        self.assertEqual(self._chapter(2)["part"]["title"], "Part One")

    def test_previously_is_the_last_chapter_summary_and_nav_stays_lean(self):
        data = self._chapter(2)
        self.assertEqual(data["previously"], "Christian sets out.")
        self.assertEqual(data["prev"], {"order": 1, "title": "The First Stage"})
        self.assertEqual(data["next"], {"order": 3, "title": "The First Stage"})
        self.assertEqual(self._chapter(1)["previously"], "")

    def test_a_book_without_parts_says_nothing(self):
        self.book.parts = []
        self.book.save()
        data = self._chapter(3)
        self.assertIsNone(data["part"])
        self.assertFalse(data["title_repeats"])

    def test_the_book_page_carries_parts_and_quiz(self):
        data = self.client.get("/api/library/books/pp/").json()
        self.assertEqual(len(data["parts"]), 2)
        self.assertEqual(data["quiz"], [])

