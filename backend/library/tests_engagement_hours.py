"""The Engagement page's "When people read" grid: minutes by weekday and
hour on each reader's own clock.

The edges that matter: a sitting lands in its reader's local hour, not the
server's; an hour with too few readers shows nothing; and a reader with no
time zone is left out and counted, never placed on UTC by default.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from reading.models import ReadingSession

from .engagement_trends import HOURS_DAYS, HOURS_MIN_READERS, reading_hours

User = get_user_model()


class ReadingHoursTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.n = 0

    def _reader(self, tz="America/New_York"):
        return UserProfile.objects.create(
            user=User.objects.create(username=str(uuid.uuid4())),
            supabase_uid=uuid.uuid4(),
            timezone=tz,
        )

    def _sit(self, p, local: datetime, seconds=600):
        self.n += 1
        ReadingSession.objects.create(
            profile=p, client_id=f"s{self.n}", started_at=local, last_seen_at=local, seconds=seconds
        )

    def _recent(self, tz, weekday, hour):
        """A recent moment that is ``weekday`` ``hour``:15 on ``tz``'s clock."""
        local = self.now.astimezone(ZoneInfo(tz)) - timedelta(days=7)
        local = local.replace(hour=hour, minute=15, second=0, microsecond=0)
        return local - timedelta(days=(local.weekday() - weekday) % 7)

    def test_a_sitting_lands_in_its_readers_local_hour(self):
        # 6:15am Sunday in New York and in Tokyo: one cell, though the two
        # are 13 hours apart on the server's clock.
        for tz in ("America/New_York", "Asia/Tokyo", "Asia/Tokyo"):
            self._sit(self._reader(tz), self._recent(tz, 6, 6))
        grid = reading_hours(self.now)
        self.assertEqual(grid["minutes"][6][6], 30)
        self.assertEqual(sum(v or 0 for row in grid["minutes"] for v in row), 30)
        self.assertEqual(grid["readers"], 3)

    def test_an_hour_with_too_few_readers_shows_nothing(self):
        for _ in range(HOURS_MIN_READERS - 1):
            p = self._reader()
            self._sit(p, self._recent("America/New_York", 2, 23))
            self._sit(p, self._recent("America/New_York", 2, 23) - timedelta(weeks=1))
        self.assertIsNone(reading_hours(self.now)["minutes"][2][23])

    def test_a_reader_without_a_time_zone_is_counted_not_placed(self):
        for tz in ("", "Not/AZone"):
            self._sit(self._reader(tz), self.now - timedelta(days=1))
        grid = reading_hours(self.now)
        self.assertEqual((grid["readers"], grid["without_zone"]), (0, 2))

    def test_old_future_and_unread_sittings_are_left_out(self):
        for _ in range(HOURS_MIN_READERS):
            p = self._reader()
            self._sit(p, self.now - timedelta(days=HOURS_DAYS + 1))
            self._sit(p, self.now + timedelta(days=30))  # a device clock set ahead
            self._sit(p, self.now - timedelta(days=1), seconds=0)
        self.assertEqual(reading_hours(self.now)["readers"], 0)

    def test_a_few_seconds_of_reading_is_not_zero_minutes(self):
        for _ in range(HOURS_MIN_READERS):
            self._sit(self._reader(), self._recent("America/New_York", 0, 7), seconds=10)
        self.assertEqual(reading_hours(self.now)["minutes"][0][7], 1)
