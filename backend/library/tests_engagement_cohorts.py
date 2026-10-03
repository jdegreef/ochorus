"""The Engagement page's retention grid: who signed up each week, and how many
of them read in each week after.

The edges that matter: a cohort is its join week's sign-ups whether or not
they ever read, the week in progress never shows (it would read as a drop),
a reader counts once per week however many days they read, reading from
before the account isn't retention, and a join week under the floor sends
its size only. The grid is built from one ``now``, so the tests pass theirs
rather than racing the view's clock across a Monday midnight.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ReadingDay, ReadingProgress, WorkKind

from .engagement_trends import (
    COHORT_MIN_SIZE,
    COHORT_SPAN,
    COHORT_WEEKS,
    retention_cohorts,
)
from .weeks import day_of, start_of, week_start

User = get_user_model()


class RetentionCohortTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.this_week = week_start(day_of(self.now))
        self.join = self.this_week - timedelta(weeks=4)  # a Monday

    def _joiners(self, n, week=None, day=2):
        at = start_of((week or self.join) + timedelta(days=day)) + timedelta(hours=12)
        out = []
        for _ in range(n):
            p = UserProfile.objects.create(
                user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4()
            )
            UserProfile.objects.filter(pk=p.pk).update(created_at=at)
            ReadingProgress.objects.create(
                profile=p, kind=WorkKind.BOOK, book_slug="x", language="en", chapter_order=1
            )
            out.append(p)
        return out

    def _read(self, p, weeks_after, day=3):
        ReadingDay.objects.create(profile=p, day=self.join + timedelta(weeks=weeks_after, days=day))

    def _rows(self):
        return {r["week"]: r for r in retention_cohorts(self.now)["rows"]}

    def test_rows_are_the_finished_weeks_and_never_this_one(self):
        self._joiners(COHORT_MIN_SIZE, week=self.this_week, day=0)  # joined this week
        rows = retention_cohorts(self.now)["rows"]
        self.assertEqual(len(rows), COHORT_WEEKS)
        self.assertEqual(rows[-1]["week"], (self.this_week - timedelta(weeks=1)).isoformat())
        self.assertNotIn(self.this_week.isoformat(), self._rows())

    def test_a_cohort_counts_each_reader_once_per_week_after_joining(self):
        a, b, *_ = self._joiners(COHORT_MIN_SIZE)
        self._read(a, 0, day=3)
        self._read(a, 0, day=4)  # two days, one week: still one reader
        self._read(b, 0, day=3)
        self._read(a, 2)
        ReadingDay.objects.create(profile=a, day=day_of(self.now))  # this week: not shown
        row = self._rows()[self.join.isoformat()]
        self.assertEqual(row["size"], COHORT_MIN_SIZE)  # the three who never read count too
        self.assertEqual(row["active"], [2, 0, 1, 0])

    def test_reading_from_before_the_account_is_not_week_zero(self):
        a, b, *_ = self._joiners(COHORT_MIN_SIZE, day=4)  # joined on the Friday
        self._read(a, 0, day=0)  # Monday, on-device, merged in at sign-up
        self._read(b, -1, day=5)  # the week before
        self.assertEqual(self._rows()[self.join.isoformat()]["active"][0], 0)

    def test_a_reading_day_a_time_zone_behind_sign_up_still_counts(self):
        # Signed up early Monday on the site clock; still Sunday where they are.
        (a, *_) = self._joiners(COHORT_MIN_SIZE, day=0)
        self._read(a, -1, day=6)
        self.assertEqual(self._rows()[self.join.isoformat()]["active"][0], 1)

    def test_a_small_join_week_sends_its_size_only(self):
        (a, *_) = self._joiners(COHORT_MIN_SIZE - 1)
        self._read(a, 0)
        out = retention_cohorts(self.now)
        row = {r["week"]: r for r in out["rows"]}[self.join.isoformat()]
        self.assertEqual((row["size"], row["active"]), (COHORT_MIN_SIZE - 1, None))
        self.assertEqual(out["min_size"], COHORT_MIN_SIZE)

    def test_an_old_cohort_is_followed_for_the_span_only(self):
        oldest = self.this_week - timedelta(weeks=COHORT_WEEKS)
        self._joiners(COHORT_MIN_SIZE, week=oldest)
        self.assertEqual(len(self._rows()[oldest.isoformat()]["active"]), COHORT_SPAN)

    @override_settings(DEBUG=True)
    def test_the_engagement_api_sends_the_grid(self):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["cohorts"]["rows"]), COHORT_WEEKS)
