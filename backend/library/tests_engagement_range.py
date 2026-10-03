"""The Engagement page's date range (``?range=``).

It moves the figures that are about a period, compares each with the
same-length period before it, and leaves everything else alone; an unknown
range falls back to the default rather than erroring.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from library.admin_views.analytics import AdminEngagementView
from reading.models import Favorite, ReadingSession

User = get_user_model()


@override_settings(DEBUG=True)
class EngagementRangeTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.p = UserProfile.objects.create(
            user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4()
        )

    def _get(self, rng=None):
        url = "/api/admin/engagement/" + (f"?range={rng}" if rng else "")
        res = APIClient().get(url)
        self.assertEqual(res.status_code, 200)
        return res.data

    def _heart(self, slug, days_ago):
        f = Favorite.objects.create(profile=self.p, kind="book", slug=slug)
        Favorite.objects.filter(pk=f.pk).update(created_at=self.now - timedelta(days=days_ago))

    def _sit(self, cid, days_ago, seconds):
        at = self.now - timedelta(days=days_ago)
        ReadingSession.objects.create(
            profile=self.p, client_id=cid, started_at=at, last_seen_at=at, seconds=seconds
        )

    def test_the_period_and_the_one_before_it(self):
        self._heart("a", 2)
        self._heart("b", 10)  # in 7d's previous period, and in 30d's current one
        self._heart("c", 50)
        week = self._get("7d")["period"]
        self.assertEqual((week["range"], week["days"]), ("7d", 7))
        self.assertEqual(week["hearts"], {"value": 1, "prev": 1})
        self.assertEqual(self._get("30d")["period"]["hearts"], {"value": 2, "prev": 1})
        self.assertEqual(self._get("all")["period"]["hearts"], {"value": 3, "prev": None})

    def test_an_unknown_range_is_the_default(self):
        self.assertEqual(
            self._get("forever")["period"]["range"], AdminEngagementView.DEFAULT_RANGE
        )
        self.assertEqual(self._get()["period"]["range"], AdminEngagementView.DEFAULT_RANGE)

    def test_the_reading_time_card_follows_the_range_and_the_fixed_windows_dont(self):
        self._sit("recent", 2, 120)
        self._sit("older", 40, 600)
        week, every = self._get("7d"), self._get("all")
        self.assertEqual((week["time"]["total_seconds"], week["time"]["sessions"]), (120, 1))
        self.assertEqual(every["time"]["total_seconds"], 720)
        self.assertEqual(week["time"]["seconds_30d"], every["time"]["seconds_30d"])
        self.assertEqual(week["period"]["seconds"], {"value": 120, "prev": 0})

    def test_when_people_read_follows_the_range(self):
        self.assertEqual(self._get("90d")["hours"]["days"], 90)
        self.assertIsNone(self._get("all")["hours"]["days"])
