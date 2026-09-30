"""Migration 0170: a reshaped Key Teachings volume keeps its readers' places."""

from __future__ import annotations

import importlib
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from library.models import Author, Book, Chapter
from reading.models import Bookmark, ChapterMarks, ReadingProgress, Removal

MIGRATION = importlib.import_module("library.migrations.0170_reshape_key_teachings")
SLUG = "key-teachings-of-test"


def _body(order: int, n: int = 3) -> str:
    return "".join(f"<p>Chapter {order} paragraph {i}.</p>" for i in range(n))


class ReshapeTests(TestCase):
    """Old 22 chapters -> 22: old 5 and 6 merge into new 5; a new chapter 12."""

    def setUp(self):
        author = Author.objects.create(slug="test-author", name="Test Author")
        self.book = Book.objects.create(
            slug=SLUG, language="en", title="The Key Teachings of Test", author=author
        )
        for order in range(1, 23):
            Chapter.objects.create(book=self.book, order=order, title=f"Old {order}", body_html=_body(order))
        user = get_user_model().objects.create(username="00000000-0000-0000-0000-0000000000ab")
        self.profile = UserProfile.objects.create(
            user=user, supabase_uid=user.username, email="r@example.com"
        )

        # New shape: 1-4 as before; 5 = old 5 then old 6 (old 6's first paragraph
        # rewritten); 6-10 = old 7-11; 11 = brand new; 12-22 = old 12-22.
        old_to_new, chapters = {}, []
        for old in range(1, 5):
            old_to_new[old] = old
            chapters.append((old, _body(old)))
        merged = _body(5) + "<p>A rewritten bridge.</p>" + "".join(
            f"<p>Chapter 6 paragraph {i}.</p>" for i in (1, 2)
        )
        old_to_new[5] = old_to_new[6] = 5
        chapters.append((5, merged))
        for old in range(7, 12):
            old_to_new[old] = old - 1
            chapters.append((old - 1, _body(old)))
        chapters.append((11, "<p>A new chapter.</p>"))
        for old in range(12, 23):
            old_to_new[old] = old
            chapters.append((old, _body(old)))

        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.data = tmp / "reshape.json"
        self.data.write_text(json.dumps({SLUG: {"old_to_new": old_to_new}}))
        self.fixture = tmp / "book.json"
        rows = [{"model": "library.book", "fields": {"slug": SLUG}}] + [
            {"model": "library.chapter", "fields": {"order": o, "title": f"New {o}", "body_html": b}}
            for o, b in sorted(chapters)
        ]
        self.fixture.write_text(json.dumps(rows))

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        with mock.patch.object(MIGRATION, "DATA", self.data), mock.patch.object(
            MIGRATION, "book_fixture_path", lambda slug, lang: self.fixture
        ):
            MIGRATION.reshape(django_apps, None)

    def test_rebuilds_to_the_new_shape(self):
        self._run()
        self.assertEqual(self.book.chapters.count(), 22)
        self.assertEqual(self.book.chapters.get(order=11).title, "New 11")
        self.assertIn("Chapter 6 paragraph 2", self.book.chapters.get(order=5).body_html)

    def test_positions_follow_their_paragraphs(self):
        progress = ReadingProgress.objects.create(
            profile=self.profile, book_slug=SLUG, chapter_order=6, paragraph_index=2, furthest_order=9
        )
        bm = Bookmark.objects.create(
            profile=self.profile, book_slug=SLUG, chapter_order=15, paragraph_index=1, title="Old 15"
        )
        ChapterMarks.objects.create(
            profile=self.profile, book_slug=SLUG, language="en", chapter_order=6,
            marks=[{"id": "m1", "p": 1}, {"id": "m2", "p": 0}],
        )
        self._run()

        progress.refresh_from_db()
        # old 6 p2 is new 5's sixth block (3 from old 5, the bridge, then 6's p1, p2)
        self.assertEqual((progress.chapter_order, progress.paragraph_index), (5, 5))
        self.assertEqual(progress.furthest_order, 8)
        bm.refresh_from_db()
        self.assertEqual((bm.chapter_order, bm.paragraph_index, bm.title), (15, 1, "New 15"))

        marks = ChapterMarks.objects.get(profile=self.profile, chapter_order=5)
        by_id = {m["id"]: m["p"] for m in marks.marks}
        self.assertEqual(by_id["m1"], 4)
        # old 6 p0 was rewritten, and opened its chapter: it lands on old 6's
        # first surviving paragraph, not on the end of old 5
        self.assertEqual(by_id["m2"], 4)
        # the old chapter-6 row fences both ids off
        fenced = ChapterMarks.objects.get(profile=self.profile, chapter_order=6)
        self.assertEqual(set(fenced.deleted), {"m1", "m2"})

    def test_a_vacated_bookmark_spot_is_tombstoned(self):
        Bookmark.objects.create(profile=self.profile, book_slug=SLUG, chapter_order=8, paragraph_index=0)
        self._run()
        self.assertTrue(Bookmark.objects.filter(chapter_order=7, paragraph_index=0).exists())
        self.assertTrue(
            Removal.objects.filter(domain="bookmark", slug=SLUG, chapter_order=8, paragraph_index=0).exists()
        )

    def test_rerun_and_fresh_install_are_noops(self):
        self._run()
        before = list(self.book.chapters.values_list("order", "title"))
        # Still 22 chapters here, so only the title check stops a second move.
        self._run()
        self.assertEqual(list(self.book.chapters.values_list("order", "title")), before)
