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

    def test_fresh_install_is_untouched(self):
        self.book.delete()
        self._run()  # no book row: nothing to reshape, and no error


class PositionTests(TestCase):
    """The paragraph matcher on its own."""

    def test_a_merge_searches_on_from_the_first_chapter(self):
        old = {
            1: ["Shared line", "A", "FOR REFLECTION AND ACTION", "A1"],
            2: ["B intro", "Shared line", "B", "FOR REFLECTION AND ACTION", "B1"],
        }
        # The merge keeps one closing set, at the end.
        new = {1: ["Shared line", "A", "B intro", "Shared line", "B", "FOR REFLECTION AND ACTION", "AB1"]}
        table = MIGRATION._positions(old, new, {1: 1, 2: 1})
        # The second chapter's copy of a shared line is its own, not the first's.
        self.assertEqual(table[(2, 1)], (1, 3))
        # The first chapter's closing label stays with its own text rather than
        # jumping past the second chapter to the merged chapter's end.
        self.assertEqual(table[(1, 2)], (1, 1))
        self.assertEqual(table[(1, 3)], (1, 1))


class PlanMoveTests(TestCase):
    """Migration 0171: a plan through reshaped books keeps its readers' days."""

    def test_days_follow_the_chapters_and_progress_follows_the_days(self):
        from django.utils import timezone

        from library.models import Plan, PlanDay
        from reading.models import PlanProgress

        mod = importlib.import_module("library.migrations.0171_reshape_first_key_teachings")
        author = Author.objects.create(slug="a", name="A")
        a = Book.objects.create(slug="book-a", language="en", title="A", author=author)
        Book.objects.create(slug="book-b", language="en", title="B", author=author)
        for order in (1, 2, 3):  # A's NEW chapters: old 2+3 merged into 2, a new 3
            Chapter.objects.create(book=a, order=order, title=f"A{order}", body_html="<p>x</p>")
        plan = Plan.objects.create(slug="p", title="P")
        for day, (book, order) in enumerate(
            [("book-a", 1), ("book-a", 2), ("book-a", 3), ("book-b", 1), ("book-b", 2)], start=1
        ):
            PlanDay.objects.create(plan=plan, day=day, book_slug=book, chapter_order=order)
        user = get_user_model().objects.create(username="00000000-0000-0000-0000-0000000000ac")
        profile = UserProfile.objects.create(user=user, supabase_uid=user.username, email="p@example.com")
        progress = PlanProgress.objects.create(
            profile=profile, plan_slug="p", started_at=timezone.now(), done=[1, 2, 3, 4]
        )
        partial = PlanProgress.objects.create(
            profile=UserProfile.objects.create(
                user=get_user_model().objects.create(username="00000000-0000-0000-0000-0000000000ad"),
                supabase_uid="00000000-0000-0000-0000-0000000000ad", email="q@example.com",
            ),
            plan_slug="p", started_at=timezone.now(), done=[1, 2],
        )

        mod.move_plans(django_apps, {"book-a": {1: 1, 2: 2, 3: 2}})

        self.assertEqual(
            list(plan.days.order_by("day").values_list("book_slug", "chapter_order")),
            [("book-a", 1), ("book-a", 2), ("book-a", 3), ("book-b", 1), ("book-b", 2)],
        )
        progress.refresh_from_db()
        # old 1 -> 1; old 2+3 (both done) -> 2; B1 was day 4 and stays 4. The
        # new A3 sits between done A2 and a day of another book: not read past.
        self.assertEqual(progress.done, [1, 2, 4])
        partial.refresh_from_db()
        # old day 3 was not done, so the merged day 2 is not either
        self.assertEqual(partial.done, [1])
