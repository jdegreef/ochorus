"""Reading-plan schedule choices (the plan calendar's start date, reading days
and reminder time): synced across devices, the newest choice winning."""

import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import PlanSchedule

User = get_user_model()

URL = "/api/reading/plan-schedule/daughters-of-the-king-three-months/"


def _ms(seconds_ago=0):
    return int((time.time() - seconds_ago) * 1000)


class PlanScheduleSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000bb")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="s@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _put(self, **body):
        return self.client.put(URL, body, format="json")

    def test_email_reminder_is_stored_only_when_asked_for(self):
        res = self._put(remind_at="07:00", email_reminder=True, updated_at=_ms())
        self.assertTrue(res.data["email_reminder"])
        # A client that doesn't send it (an older one) turns email off, never on.
        res = self._put(remind_at="07:00", updated_at=_ms() + 1000)
        self.assertFalse(res.data["email_reminder"])
        res = self._put(remind_at="07:00", email_reminder="yes", updated_at=_ms() + 2000)
        self.assertFalse(res.data["email_reminder"])

    def test_put_stores_the_choices_and_they_appear_in_state(self):
        res = self._put(start_on="2026-11-02", reading_days="weekdays", remind_at="06:30", updated_at=_ms())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            (res.data["start_on"], res.data["reading_days"], res.data["remind_at"]),
            ("2026-11-02", "weekdays", "06:30"),
        )
        state = self.client.get("/api/reading/state/").data
        self.assertEqual(
            [(s["plan_slug"], s["reading_days"]) for s in state["plan_schedules"]],
            [("daughters-of-the-king-three-months", "weekdays")],
        )

    def test_the_newest_choice_wins_and_an_older_one_is_ignored(self):
        self._put(reading_days="weekdays", updated_at=_ms(10))
        self._put(reading_days="monsat", updated_at=_ms(5))
        # A device that chose earlier, arriving late, does not undo the newer.
        res = self._put(reading_days="daily", updated_at=_ms(60))
        self.assertEqual(res.data["reading_days"], "monsat")
        self.assertEqual(PlanSchedule.objects.get(profile=self.profile).reading_days, "monsat")

    def test_a_clock_far_in_the_future_cannot_lock_other_devices_out(self):
        self._put(reading_days="weekdays", updated_at=_ms(-86_400 * 365))  # a year ahead
        # Held to a day of skew, so a correct device's write two days on wins.
        stored = PlanSchedule.objects.get(profile=self.profile).client_updated_at
        self.assertLess(stored.timestamp(), time.time() + 86_400 + 60)

    def test_a_merge_row_with_no_stamp_never_overwrites_the_account(self):
        # A device's choices from before they synced carry no stamp: stale.
        self._put(reading_days="weekdays", updated_at=_ms())
        res = self.client.post(
            "/api/reading/merge/",
            {"plan_schedules": [{"plan_slug": "daughters-of-the-king-three-months", "reading_days": "monsat"}]},
            format="json",
        )
        self.assertEqual(res.data["plan_schedules"][0]["reading_days"], "weekdays")
        # …but a live PUT with none is an older client acting now.
        self.assertEqual(self._put(reading_days="monsat").data["reading_days"], "monsat")

    def test_junk_falls_back_to_defaults(self):
        res = self._put(start_on="2026-02-30", reading_days="sundays", remind_at="25:00", updated_at=_ms())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            (res.data["start_on"], res.data["reading_days"], res.data["remind_at"]), (None, "daily", "")
        )

    def test_merge_applies_rows_newest_wins_and_skips_junk(self):
        self._put(reading_days="weekdays", updated_at=_ms(5))
        res = self.client.post(
            "/api/reading/merge/",
            {
                "plan_schedules": [
                    # Older than the server's: ignored.
                    {"plan_slug": "daughters-of-the-king-three-months", "reading_days": "daily", "updated_at": _ms(60)},
                    {"plan_slug": "school-of-prayer-31-days", "reading_days": "monsat", "remind_at": "07:15", "updated_at": _ms()},
                    # Too long for the column (the app's slug rule is length-only).
                    {"plan_slug": "x" * 161, "reading_days": "daily"},
                    "not a row",
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        got = {s["plan_slug"]: (s["reading_days"], s["remind_at"]) for s in res.data["plan_schedules"]}
        self.assertEqual(
            got,
            {
                "daughters-of-the-king-three-months": ("weekdays", ""),
                "school-of-prayer-31-days": ("monsat", "07:15"),
            },
        )

    def test_merge_ignores_a_malformed_payload(self):
        res = self.client.post("/api/reading/merge/", {"plan_schedules": "nope"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["plan_schedules"], [])

    def test_requires_auth_and_a_valid_slug(self):
        self.assertEqual(APIClient().put(URL, {}, format="json").status_code, 401)
        bad = self.client.put("/api/reading/plan-schedule/Not_A_Slug!/", {}, format="json")
        self.assertIn(bad.status_code, (400, 404))
