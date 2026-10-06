"""`Chapter.study_questions` — the young-reader editions' "Talk about it".

Pinned here: the seed upserts the field from the fixture and leaves a chapter
alone when its fixture row carries no key, and the chapter API serves it. The
shipped sets' shape is ``tests_fixture.ChapterQuestionsShapeTests``.
"""

from __future__ import annotations

from django.test import TestCase

from .management.commands.seed_books import sync_chapters
from .models import Author, Book, Chapter

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
