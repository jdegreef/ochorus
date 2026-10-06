"""`Chapter.study_questions` — the young-reader editions' "Talk about it".

Pinned here: the seed upserts the field from the fixture and leaves a chapter
alone when its fixture row carries no key; the chapter API serves it; and every
shipped set is well formed (plain text, answered, three per chapter), so a bad
batch fails the build rather than reaching a family's reading.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import TestCase

from .management.commands.seed_books import sync_chapters
from .models import Author, Book, Chapter

BOOKS = Path(__file__).parent / "fixtures" / "content" / "books"
QA = [{"question": "Why did Christian run?", "answer": "To reach the light."}]


class SyncChapterQuestionsTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="bunyan", name="John Bunyan")
        self.book = Book.objects.create(author=author, slug="pp-children", title="PP")
        Chapter.objects.create(book=self.book, order=1, title="One", body_html="<p>Run.</p>")

    def _fixture(self, **extra):
        return [{"order": 1, "title": "One", "body_html": "<p>Run.</p>", **extra}]

    def test_the_fixture_sets_and_then_changes_the_questions(self):
        self.assertEqual(sync_chapters(self.book, self._fixture(study_questions=QA))[1], 1)
        self.assertEqual(Chapter.objects.get().study_questions, QA)
        # Converged: a second pass writes nothing.
        self.assertEqual(sync_chapters(self.book, self._fixture(study_questions=QA))[1], 0)

    def test_a_row_without_the_key_leaves_the_questions_alone(self):
        Chapter.objects.update(study_questions=QA)
        self.assertEqual(sync_chapters(self.book, self._fixture())[1], 0)
        self.assertEqual(Chapter.objects.get().study_questions, QA)

    def test_a_new_chapter_arrives_with_its_questions(self):
        sync_chapters(
            self.book,
            [*self._fixture(), {"order": 2, "title": "Two", "body_html": "<p>On.</p>", "study_questions": QA}],
        )
        self.assertEqual(Chapter.objects.get(order=2).study_questions, QA)

    def test_the_chapter_api_serves_them(self):
        Chapter.objects.update(study_questions=QA)
        self.book.is_published = True
        self.book.save()
        response = self.client.get("/api/library/books/pp-children/chapters/1/?language=en")
        self.assertEqual(response.json()["study_questions"], QA)


class ShippedChapterQuestionsTests(TestCase):
    def test_every_shipped_set_is_three_plain_answered_questions(self):
        bad, books = [], 0
        for path in sorted(BOOKS.glob("*.json")):
            rows = json.loads(path.read_text(encoding="utf-8"))
            chapters = [r for r in rows if r["model"] == "library.chapter"]
            sets = [c["fields"]["study_questions"] for c in chapters if c["fields"].get("study_questions")]
            if not sets:
                continue
            books += 1
            if len(sets) != len(chapters):
                bad.append(f"{path.name}: {len(sets)} of {len(chapters)} chapters have questions")
            for qa_set in sets:
                ok = len(qa_set) == 3 and all(
                    set(qa) == {"question", "answer"}
                    and all(isinstance(v, str) and v.strip() and "<" not in v for v in qa.values())
                    for qa in qa_set
                )
                if not ok:
                    bad.append(f"{path.name}: malformed set {qa_set!r:.80}")
        self.assertEqual(bad, [])
        self.assertGreaterEqual(books, 10)  # the ten young-reader editions
