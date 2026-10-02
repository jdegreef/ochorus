"""Where readers stop (library.dropoff): per-chapter reach and the steepest drop.

These counts send an admin into a chapter to fix it, so the edges matter: what
"reached" means for a finished reader or an old row, that a reader still in
the middle of a chapter isn't counted as lost, and that the library-wide list
shows only groups big enough to mean something, fixable (flagged) ones first.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ReadingProgress, WorkKind

from . import dropoff
from .models import Author, Book, Chapter

NOW = timezone.now()
OLD = NOW - timedelta(days=dropoff.STALL_DAYS + 5)


def row(furthest=0, chapter=1, finished=False, updated=OLD):
    return {
        "furthest_order": furthest,
        "chapter_order": chapter,
        "finished_at": NOW if finished else None,
        "updated_at": updated,
    }


class ReachTests(SimpleTestCase):
    def test_reaching_a_chapter_means_reaching_every_one_before_it(self):
        curve = dropoff.reach([row(3), row(1), row(finished=True)], 4, now=NOW)
        self.assertEqual([p["reached"] for p in curve], [3, 2, 2, 1])

    def test_an_old_row_falls_back_to_its_current_chapter_and_is_clamped(self):
        # furthest_order 0 predates the field; 9 is past a re-imported end.
        curve = dropoff.reach([row(0, chapter=2), row(9)], 3, now=NOW)
        self.assertEqual([p["reached"] for p in curve], [2, 2, 1])

    def test_only_a_reader_gone_quiet_is_stopped(self):
        curve = dropoff.reach([row(2), row(2, updated=NOW), row(finished=True)], 3, now=NOW)
        self.assertEqual((curve[1]["stopped"], curve[1]["still"]), (1, 1))
        # Finishing isn't stopping.
        self.assertEqual((curve[2]["stopped"], curve[2]["still"]), (0, 0))

    def test_the_steepest_drop_skips_small_groups_and_the_last_chapter(self):
        curve = [
            {"chapter": 1, "reached": 10, "stopped": 2, "still": 0},
            {"chapter": 2, "reached": 8, "stopped": 4, "still": 0},
            {"chapter": 3, "reached": 4, "stopped": 3, "still": 0},
            {"chapter": 4, "reached": 1, "stopped": 1, "still": 0},
        ]
        self.assertEqual(dropoff.steepest_drop(curve, min_readers=5)["chapter"], 2)
        self.assertEqual(dropoff.steepest_drop(curve)["chapter"], 3)
        # Chapter 3 is reached by too few, and chapter 4 is the last.
        self.assertIsNone(dropoff.steepest_drop(curve[2:], min_readers=5))


@override_settings(DEBUG=True)
class DropOffViewTests(TestCase):
    """Two English books. In "Long Middle", 6 readers reach chapter 2 (a giant
    chapter) and 4 stop there. In "Plain", 6 reach chapter 1 (a normal chapter)
    and 5 stop there: a steeper drop, but nothing flagged."""

    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(slug="watson", name="Thomas Watson")
        normal = "<p>" + "Grace abounds to the chief of sinners. " * 25 + "</p>"

        def book(slug, title, bodies):
            b = Book.objects.create(author=author, slug=slug, language="en", title=title)
            for i, body in enumerate(bodies, start=1):
                Chapter.objects.create(book=b, order=i, title=f"Part {i} of {title}", body_html=body)

        book("long-middle", "Long Middle", [normal * 2, "<p>" + "word " * 9000 + "end.</p>", normal * 2])
        book("plain", "Plain", [normal * 2, normal * 2, normal * 2])

        User = get_user_model()

        def reader(slug, furthest, *, finished=False):
            user = User.objects.create(username=str(uuid.uuid4()))
            profile = UserProfile.objects.create(user=user, supabase_uid=uuid.uuid4())
            ReadingProgress.objects.create(
                profile=profile, kind=WorkKind.BOOK, book_slug=slug, language="en",
                chapter_order=furthest, furthest_order=furthest,
                finished_at=NOW if finished else None,
            )

        for f in (2, 2, 2, 2, 3, 3):
            reader("long-middle", f)
        for f in (1, 1, 1, 1, 1, 2):
            reader("plain", f)
        ReadingProgress.objects.update(updated_at=OLD)

    def test_the_book_page_carries_each_editions_curve(self):
        res = APIClient().get("/api/admin/books/long-middle/")
        self.assertEqual(res.status_code, 200)
        en = res.data["languages"][0]
        self.assertEqual([p["reached"] for p in en["reach"]], [6, 6, 2])
        self.assertEqual(en["steepest"]["chapter"], 2)
        self.assertEqual(en["steepest"]["stopped"], 4)
        self.assertEqual(res.data["stall_days"], dropoff.STALL_DAYS)

    def test_the_audit_list_puts_the_flagged_drop_first(self):
        res = APIClient().get("/api/admin/drop-off/?language=en")
        self.assertEqual(res.status_code, 200)
        drops = res.data["drops"]
        self.assertEqual([d["slug"] for d in drops], ["long-middle", "plain"])
        self.assertIn("giant", drops[0]["flags"])
        self.assertEqual(drops[1]["flags"], [])
        self.assertEqual((drops[0]["chapter"], drops[0]["reached"]), (2, 6))

    def test_without_a_language_every_language_is_listed(self):
        res = APIClient().get("/api/admin/drop-off/")
        self.assertEqual([d["slug"] for d in res.data["drops"]], ["long-middle", "plain"])
        self.assertEqual({d["language"] for d in res.data["drops"]}, {"en"})

    def test_a_group_under_the_minimum_is_not_listed(self):
        ReadingProgress.objects.filter(book_slug="plain", furthest_order=2).delete()
        ReadingProgress.objects.filter(book_slug="plain").first().delete()
        res = APIClient().get("/api/admin/drop-off/?language=en")
        self.assertEqual([d["slug"] for d in res.data["drops"]], ["long-middle"])
