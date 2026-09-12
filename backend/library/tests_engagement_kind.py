"""Engagement analytics must not blend books, sermons and biographies.

``ReadingProgress.book_slug`` names a book, a sermon OR an author biography (see
``WorkKind``) — the column kept its historical name. The dashboard grouped by
that column alone, so:

* a sermon and a book sharing a slug merged into ONE row, labelled with the
  book's title and author;
* and the row linked to ``/books/<slug>``, which 404s for a sermon or a bio.

Finishers are counted from the stored ``finished_at`` stamp (the reader's real
completion), scoped by ``(kind, slug)`` — so a sermon or biography gets a real
finisher number too, and finishing the sermon never counts toward a book that
shares its slug.

These are the numbers content and translation priorities are chosen from, so
"roughly right" is not good enough.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ChapterMarks, ReadingProgress, WorkKind

from .models import Author, Book, Chapter, Sermon

User = get_user_model()


@override_settings(DEBUG=True)
class EngagementKindTests(TestCase):
    """A book and a sermon deliberately share the slug "humility"."""

    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")
        cls.book = Book.objects.create(
            author=cls.author, slug="humility", language="en", title="Humility"
        )
        for order in (1, 2):
            Chapter.objects.create(
                book=cls.book, order=order, title=f"Ch {order}", body_html="<p>x</p>"
            )
        cls.sermon = Sermon.objects.create(
            author=cls.author, slug="humility", language="en", title="A Sermon on Humility"
        )

        def reader(n):
            user = User.objects.create(username=f"00000000-0000-0000-0000-00000000000{n}")
            return UserProfile.objects.create(
                user=user, supabase_uid=user.username, email=f"r{n}@example.com"
            )

        # One reader of the BOOK, on chapter 1 of 2 — not a finisher.
        ReadingProgress.objects.create(
            profile=reader(1), kind=WorkKind.BOOK, book_slug="humility", chapter_order=1
        )
        # Two readers of the SERMON, which pins chapter_order to 1.
        for n in (2, 3):
            ReadingProgress.objects.create(
                profile=reader(n),
                kind=WorkKind.SERMON,
                book_slug="humility",
                chapter_order=1,
            )
        # One reader of a BIO, whose slug names the author.
        ReadingProgress.objects.create(
            profile=reader(4), kind=WorkKind.BIO, book_slug="am", chapter_order=1
        )

    def _rows(self, section="most_read"):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        return {(r["kind"], r["slug"]): r for r in res.data[section]}

    def test_the_book_and_the_sermon_are_separate_rows(self):
        rows = self._rows()
        self.assertIn(("book", "humility"), rows)
        self.assertIn(("sermon", "humility"), rows)
        self.assertEqual(rows[("book", "humility")]["readers"], 1)
        self.assertEqual(rows[("sermon", "humility")]["readers"], 2)

    def test_each_row_carries_its_own_title(self):
        rows = self._rows()
        self.assertEqual(rows[("book", "humility")]["title"], "Humility")
        self.assertEqual(
            rows[("sermon", "humility")]["title"], "A Sermon on Humility"
        )

    def test_a_biography_is_titled_with_the_person(self):
        rows = self._rows()
        self.assertEqual(rows[("bio", "am")]["title"], "Andrew Murray")

    def test_reading_without_a_finished_stamp_is_not_finishing(self):
        # Nobody in setUp has finished_at set — merely reading (even a sermon or
        # bio, a single document) is not finishing. Every kind reports a real 0,
        # not None: finishing counts for all kinds now.
        rows = self._rows()
        self.assertEqual(rows[("book", "humility")]["finishers"], 0)
        self.assertEqual(rows[("sermon", "humility")]["finishers"], 0)
        self.assertEqual(rows[("bio", "am")]["finishers"], 0)

    def test_finishers_count_the_stamp_for_every_kind(self):
        # A sermon and a biography can be finished now (the stored finished_at
        # stamp), not just a book — so each gets a real finisher count.
        now = timezone.now()
        ReadingProgress.objects.filter(kind=WorkKind.SERMON, book_slug="humility").update(
            finished_at=now
        )
        ReadingProgress.objects.filter(kind=WorkKind.BIO, book_slug="am").update(
            finished_at=now
        )
        rows = self._rows()
        self.assertEqual(rows[("sermon", "humility")]["finishers"], 2)
        self.assertEqual(rows[("bio", "am")]["finishers"], 1)

    def test_a_sermon_finish_is_not_counted_toward_a_book_sharing_its_slug(self):
        # The book and the sermon both use the slug "humility". Finishing the
        # sermon must not read as finishing the book — finishers are scoped by
        # (kind, slug).
        ReadingProgress.objects.filter(kind=WorkKind.SERMON, book_slug="humility").update(
            finished_at=timezone.now()
        )
        rows = self._rows()
        self.assertEqual(rows[("sermon", "humility")]["finishers"], 2)
        self.assertEqual(rows[("book", "humility")]["finishers"], 0)

    def test_highlights_are_separated_by_kind_too(self):
        profile = UserProfile.objects.first()
        ChapterMarks.objects.create(
            profile=profile,
            kind=WorkKind.SERMON,
            book_slug="humility",
            chapter_order=1,
            marks=[{"id": "a", "p": 0, "s": 0, "e": 4}],
        )
        rows = self._rows("most_marked")
        self.assertIn(("sermon", "humility"), rows)
        self.assertEqual(rows[("sermon", "humility")]["title"], "A Sermon on Humility")
