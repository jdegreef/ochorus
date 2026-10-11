""""Read together" groups with totals: counts only, never who, opt-in, and no
count that could be turned back into what one person did (``reading.groups``)."""

from datetime import UTC, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from library.models import Plan, PlanDay
from reading.groups import LIFETIME, MAX_GROUPS_LED, MIN_COUNTED
from reading.models import PlanProgress, ReadingGroup, ReadingGroupMember

User = get_user_model()
PLAN = "school-of-prayer"
TODAY = datetime.now(UTC).date()
#: A daily group three days in: today is Day 4.
START = TODAY - timedelta(days=3)


def _reader(n: int):
    user = User.objects.create(username=f"00000000-0000-0000-0000-{n:012d}")
    profile = UserProfile.objects.create(
        user=user, supabase_uid=user.username, email=f"r{n}@example.com", display_name=f"Reader {n}"
    )
    client = APIClient()
    client.force_authenticate(user)
    return profile, client


class ReadingGroupTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(slug=PLAN, title="With Christ in the School of Prayer")
        PlanDay.objects.bulk_create(
            PlanDay(plan=plan, day=d, book_slug="school-of-prayer", chapter_order=d) for d in range(1, 11)
        )
        self.leader, self.client = _reader(1)

    def _create(self, **body):
        return self.client.post(
            "/api/reading/groups/",
            {"plan_slug": PLAN, "start_on": START.isoformat(), "reading_days": "daily", **body},
            format="json",
        )

    def _done(self, profile, days):
        PlanProgress.objects.update_or_create(
            profile=profile, plan_slug=PLAN, defaults={"started_at": datetime.now(UTC), "done": days}
        )

    def _group_of(self, n):
        """A group with `n` counted readers (the leader not among them)."""
        code = self._create().data["code"]
        readers = [_reader(i) for i in range(2, n + 2)]
        for _p, c in readers:
            c.put(f"/api/reading/groups/{code}/membership/")
        return code, readers

    def _get(self, code, day=None):
        return APIClient().get(f"/api/reading/groups/{code}/" + (f"?day={day}" if day else ""))

    def test_turning_totals_on_counts_nobody_and_carries_only_the_group_facts(self):
        res = self._create()
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.data["plan_slug"], res.data["start_on"]), (PLAN, START.isoformat()))
        self.assertEqual(res.data["members"], 0)
        self.assertFalse(res.data["counted"])
        self.assertGreaterEqual(len(res.data["code"]), 12)
        self.assertEqual(
            set(res.data),
            {"code", "plan_slug", "start_on", "reading_days", "members", "day", "done", "min_counted", "counted"},
        )

    def test_a_group_needs_a_published_plan_a_date_and_a_known_rule(self):
        self.assertEqual(self._create(plan_slug="no-such-plan").status_code, 400)
        self.assertEqual(self._create(start_on="next week").status_code, 400)
        self.assertEqual(self._create(reading_days="sometimes").status_code, 400)
        self.assertEqual(APIClient().post("/api/reading/groups/", {}, format="json").status_code, 401)

    def test_no_count_below_the_floor(self):
        code, readers = self._group_of(MIN_COUNTED - 1)
        for p, _c in readers:
            self._done(p, [1, 2, 3, 4])
        res = self._get(code, 4)
        self.assertEqual(res.data["members"], MIN_COUNTED - 1)
        self.assertIsNone(res.data["done"])

    def test_counts_who_read_the_day_the_group_is_on_and_no_other(self):
        code, readers = self._group_of(MIN_COUNTED)
        for p, _c in readers:
            self._done(p, [1, 2, 3])
        self._done(readers[0][0], [1, 2, 3, 4])
        self.assertEqual(self._get(code, 4).data["done"], 1)
        # A day either side (a reader's own date) is fine…
        self.assertEqual(self._get(code, 3).data["done"], MIN_COUNTED)
        # …but not the group's history: that would show who read what, by
        # comparing the totals before and after someone joined.
        self.assertIsNone(self._get(code, 1).data["done"])
        self.assertIsNone(self._get(code, 9).data["done"])

    def test_counts_only_what_a_reader_read_after_joining(self):
        code = self._create().data["code"]
        readers = [_reader(i) for i in range(2, MIN_COUNTED + 2)]
        # The first reader finished the whole plan last year.
        self._done(readers[0][0], list(range(1, 11)))
        for _p, c in readers:
            c.put(f"/api/reading/groups/{code}/membership/")
        self.assertEqual(self._get(code, 4).data["done"], 0)

    def test_a_reader_chooses_to_be_counted_and_leaving_stops_it(self):
        code = self._create().data["code"]
        p2, c2 = _reader(2)
        url = f"/api/reading/groups/{code}/membership/"
        self.assertEqual(c2.put(url).data["members"], 1)
        self.assertEqual(c2.put(url).data["members"], 1)
        self.assertTrue(c2.get(f"/api/reading/groups/{code}/").data["counted"])
        self.assertFalse(self.client.get(f"/api/reading/groups/{code}/").data["counted"])
        self.assertEqual(c2.delete(url).status_code, 204)
        self.assertFalse(ReadingGroupMember.objects.filter(group__code=code).exists())
        self.assertEqual(c2.put("/api/reading/groups/nope/membership/").status_code, 404)

    def test_only_the_leader_deletes_a_group_and_an_account_takes_its_rows_with_it(self):
        code, [(p2, c2)] = self._group_of(1)
        self.assertEqual(c2.delete(f"/api/reading/groups/{code}/").status_code, 404)
        p2.user.delete()
        self.assertFalse(ReadingGroupMember.objects.filter(group__code=code).exists())
        self.assertEqual(self.client.delete(f"/api/reading/groups/{code}/").status_code, 204)
        self.assertEqual(self._get(code).status_code, 404)

    def test_a_group_ends_and_is_cleared_away(self):
        code = self._create().data["code"]
        ReadingGroup.objects.filter(code=code).update(start_on=TODAY - LIFETIME)
        self.assertEqual(self._get(code).status_code, 404)
        self._create()
        self.assertFalse(ReadingGroup.objects.filter(code=code).exists())

    def test_bounds_how_many_groups_one_account_leads(self):
        for _ in range(MAX_GROUPS_LED):
            self.assertEqual(self._create().status_code, 201)
        self.assertEqual(self._create().status_code, 429)
