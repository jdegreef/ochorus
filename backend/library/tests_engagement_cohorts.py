"""The Engagement page's retention grid: who signed up each week, and how many
of them read in each week after.

The edges that matter: a cohort is its join week's sign-ups whether or not
they ever read, the week in progress never shows (it would read as a drop),
a reader counts once per week however many days they read, and a join week
under the floor sends its size only.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ReadingDay

from .engagement_trends import COHORT_MIN_SIZE, COHORT_SPAN, COHORT_WEEKS
from .weeks import day_of, start_of, week_start

User = get_user_model()


@override_settings(DEBUG=True)
class RetentionCohortTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.this_week = week_start(day_of(self.now))
        # Four weeks ago, mid-week (site clock).
        self.join = self.this_week - timedelta(weeks=4)

    def _joiners(self, n, week=None):
        at = start_of((week or self.join) + timedelta(days=2))
        out = []
        for _ in range(n):
            p = UserProfile.objects.create(
                user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4()
            )
            UserProfile.objects.filter(pk=p.pk).update(created_at=at)
            out.append(p)
        return out

    def _read(self, p, weeks_after, day=0):
        ReadingDay.objects.create(profile=p, day=self.join + timedelta(weeks=weeks_after, days=day))

    def _cohorts(self):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        return {c["week"]: c for c in res.data["cohorts"]}

    def test_rows_are_the_finished_weeks_and_never_this_one(self):
        rows = APIClient().get("/api/admin/engagement/").data["cohorts"]
        self.assertEqual(len(rows), COHORT_WEEKS)
        self.assertEqual(rows[-1]["week"], (self.this_week - timedelta(weeks=1)).isoformat())
        self._joiners(COHORT_MIN_SIZE, week=self.this_week)  # joined this week
        self.assertNotIn(self.this_week.isoformat(), self._cohorts())

    def test_a_cohort_counts_each_reader_once_per_week_after_joining(self):
        a, b, *_ = self._joiners(COHORT_MIN_SIZE)
        self._read(a, 0, day=3)
        self._read(a, 0, day=4)  # two days, one week: still one reader
        self._read(b, 0, day=3)
        self._read(a, 2)
        self._read(a, 4)  # this week: in progress, so not shown
        row = self._cohorts()[self.join.isoformat()]
        self.assertEqual(row["size"], COHORT_MIN_SIZE)  # the three who never read count too
        self.assertEqual(row["active"], [2, 0, 1, 0])

    def test_reading_from_before_the_account_is_not_week_zero(self):
        (a, *_) = self._joiners(COHORT_MIN_SIZE)
        self._read(a, -1)  # on-device reading merged in at sign-up
        self.assertEqual(self._cohorts()[self.join.isoformat()]["active"][0], 0)

    def test_a_small_join_week_sends_its_size_only(self):
        (a, *_) = self._joiners(COHORT_MIN_SIZE - 1)
        self._read(a, 0)
        row = self._cohorts()[self.join.isoformat()]
        self.assertEqual((row["size"], row["active"]), (COHORT_MIN_SIZE - 1, None))

    def test_an_old_cohort_is_followed_for_the_span_only(self):
        oldest = self.this_week - timedelta(weeks=COHORT_WEEKS)
        self._joiners(COHORT_MIN_SIZE, week=oldest)
        self.assertEqual(len(self._cohorts()[oldest.isoformat()]["active"]), COHORT_SPAN)
