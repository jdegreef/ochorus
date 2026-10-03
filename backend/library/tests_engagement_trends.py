"""The weekly lines behind the Engagement page's pulse tiles.

What matters: each line's weeks are the chart's weeks, a running total ends on
the tile's own number, and a week with nothing in it reads as zero rather than
dropping out of the series.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import (
    Favorite,
    ReadingDay,
    ReadingProgress,
    ReadingSession,
    WorkKind,
)

from .weeks import day_of, week_start

User = get_user_model()


def profile():
    user = User.objects.create(username=str(uuid.uuid4()))
    return UserProfile.objects.create(user=user, supabase_uid=uuid.uuid4())


@override_settings(DEBUG=True)
class PulseTrendTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.today = day_of(self.now)
        # One reader from before the reading-day log, so the page has tiles.
        ReadingProgress.objects.create(
            profile=profile(), kind=WorkKind.BOOK, book_slug="x", language="en", chapter_order=1
        )

    def _trends(self):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_every_line_is_on_the_charts_weeks(self):
        data = self._trends()
        weeks = [w["week"] for w in data["weekly_active"]]
        t = data["trends"]
        for key in ("hearts", "reading_seconds", "readers", "users"):
            self.assertEqual(len(t[key]), len(weeks), key)
        self.assertEqual(len(t["active_30d"]), 6)

    def test_hearts_and_reading_time_are_counted_in_their_week(self):
        p = profile()
        Favorite.objects.create(profile=p, kind="book", slug="a")
        old = Favorite.objects.create(profile=p, kind="book", slug="b")
        Favorite.objects.filter(pk=old.pk).update(created_at=self.now - timedelta(weeks=2))
        ReadingSession.objects.create(
            profile=p, client_id="x", started_at=self.now, last_seen_at=self.now, seconds=600
        )
        t = self._trends()["trends"]
        self.assertEqual(t["hearts"][-1], 1)
        self.assertEqual(t["hearts"][-3], 1)
        self.assertEqual(t["hearts"][-2], 0)
        self.assertEqual(t["reading_seconds"][-1], 600)

    def test_running_totals_end_on_the_tiles_number(self):
        old, new = profile(), profile()
        UserProfile.objects.filter(pk=old.pk).update(created_at=self.now - timedelta(weeks=20))
        for p, first in ((old, self.today - timedelta(weeks=20)), (new, self.today)):
            ReadingDay.objects.create(profile=p, day=first)
            ReadingProgress.objects.create(
                profile=p, kind=WorkKind.BOOK, book_slug="x", language="en", chapter_order=1
            )
        data = self._trends()
        t = data["trends"]
        self.assertEqual(t["readers"][-1], data["overview"]["readers"])
        self.assertEqual(t["users"][-1], data["overview"]["total_users"])
        # The new reader arrived this week; the others were there all along.
        self.assertEqual(t["readers"], [2] * 7 + [3])

    def test_a_reading_day_without_saved_progress_is_not_an_arrival(self):
        # The tile counts readers with saved progress; someone who only has a
        # reading day isn't one of them, so the line can't dip below zero.
        for _ in range(3):
            ReadingDay.objects.create(profile=profile(), day=self.today)
        t = self._trends()["trends"]
        self.assertEqual(t["readers"], [1] * 8)

    def test_a_reader_active_in_two_weeks_counts_in_both(self):
        # The bug this fixes: saved progress keeps only each work's latest
        # touch, so a reader who read last week AND this week used to count
        # only this week, shrinking last week and inflating the rise.
        p = profile()
        ReadingProgress.objects.create(
            profile=p, kind=WorkKind.BOOK, book_slug="y", language="en", chapter_order=2
        )
        for back in (0, 8):
            ReadingDay.objects.create(profile=p, day=self.today - timedelta(days=back))
        data = self._trends()
        ov = data["overview"]
        self.assertEqual((ov["active_7d"], ov["active_7d_prev"]), (1, 1))
        weekly = [w["readers"] for w in data["weekly_active"]]
        self.assertEqual(weekly[-1], 1)
        self.assertEqual(sum(weekly[:-1]), 1)  # last week (or the one before, by weekday)

    def test_the_30_day_line_ends_on_the_tile(self):
        p = profile()
        for back in (0, 20, 40):
            ReadingDay.objects.create(profile=p, day=self.today - timedelta(days=back))
        data = self._trends()
        self.assertEqual(data["trends"]["active_30d"][-1]["readers"], data["overview"]["active_30d"])

    def test_an_empty_page_gets_no_lines(self):
        ReadingProgress.objects.all().delete()
        self.assertIsNone(self._trends()["trends"])

    def test_the_last_30_day_window_ends_today(self):
        p = profile()
        ReadingDay.objects.create(profile=p, day=self.today)
        ReadingDay.objects.create(profile=p, day=self.today - timedelta(days=45))
        windows = self._trends()["trends"]["active_30d"]
        self.assertEqual(windows[-1]["end"], self.today.isoformat())
        self.assertEqual([w["readers"] for w in windows[-2:]], [1, 1])
        self.assertEqual(windows[0]["readers"], 0)

    def test_a_sign_up_lands_in_the_same_week_on_both_charts(self):
        profile()
        users = self._trends()["trends"]["users"]
        weekly = APIClient().get("/api/admin/users/").data["weekly_signups"]
        # Two this week: setUp's reader and this one.
        self.assertEqual(users[-1] - users[-2], 2)
        self.assertEqual(weekly[-1], {"week": week_start(self.today).isoformat(), "count": 2})
