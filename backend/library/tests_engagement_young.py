"""The admin engagement's young-reader rollup (``_young_readers``).

Each hub counts the books it shows (``views.hub_book_slugs``) and the plans
that read nothing but them — the hub page's own rules, so the dashboard's
"Young readers" is the page's audience, not a second guess at it.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import PlanProgress, ReadingProgress, WorkKind

from .models import Author, Book, Plan, PlanDay

User = get_user_model()


@override_settings(DEBUG=True)
class YoungReadersEngagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(slug="bunyan", name="John Bunyan")
        for slug, title in (
            ("pilgrims-progress", "The Pilgrim's Progress"),
            ("pilgrims-progress-children", "The Pilgrim's Progress (For Children)"),
            ("pilgrims-progress-teens", "The Pilgrim's Progress (For Teens)"),
        ):
            Book.objects.create(
                author=author, slug=slug, language="en", title=title, is_published=True
            )
        family = Plan.objects.create(slug="family", language="en", title="Family", is_published=True)
        PlanDay.objects.create(plan=family, day=1, book_slug="pilgrims-progress-children", chapter_order=1)
        PlanDay.objects.create(plan=family, day=2, book_slug="pilgrims-progress-children", chapter_order=2)
        mixed = Plan.objects.create(slug="mixed", language="en", title="Mixed", is_published=True)
        PlanDay.objects.create(plan=mixed, day=1, book_slug="pilgrims-progress-children", chapter_order=1)
        PlanDay.objects.create(plan=mixed, day=2, book_slug="pilgrims-progress", chapter_order=1)

        def reader(n):
            user = User.objects.create(username=f"00000000-0000-0000-0000-00000000000{n}")
            return UserProfile.objects.create(
                user=user, supabase_uid=user.username, email=f"r{n}@example.com"
            )

        one, two, three = reader(1), reader(2), reader(3)
        ReadingProgress.objects.create(
            profile=one, kind=WorkKind.BOOK, book_slug="pilgrims-progress-children",
            finished_at=timezone.now(),
        )
        ReadingProgress.objects.create(
            profile=two, kind=WorkKind.BOOK, book_slug="pilgrims-progress-children"
        )
        # The full text is no hub's book.
        ReadingProgress.objects.create(profile=three, kind=WorkKind.BOOK, book_slug="pilgrims-progress")
        PlanProgress.objects.create(profile=one, plan_slug="family", done=[1, 2], started_at=timezone.now())
        PlanProgress.objects.create(profile=two, plan_slug="mixed", done=[1], started_at=timezone.now())

    def _hubs(self):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        return {row["audience"]: row for row in res.data["young_readers"]}

    def test_each_hub_counts_its_own_books_readers_and_finishers(self):
        kids = self._hubs()["young_readers"]
        self.assertEqual((kids["readers"], kids["finishers"]), (2, 1))
        [book] = kids["books"]
        self.assertEqual(
            (book["slug"], book["title"], book["readers"], book["finishers"]),
            ("pilgrims-progress-children", "The Pilgrim's Progress (For Children)", 2, 1),
        )

    def test_only_a_plan_of_nothing_but_the_hubs_books_is_its_plan(self):
        plans = self._hubs()["young_readers"]["plans"]
        self.assertEqual((plans["started"], plans["completed"]), (1, 1))
        self.assertEqual([p["slug"] for p in plans["by_plan"]], ["family"])

    def test_a_hub_nobody_has_read_still_reports_zero(self):
        teens = self._hubs()["teens"]
        self.assertEqual((teens["readers"], teens["finishers"], teens["books"]), (0, 0, []))
