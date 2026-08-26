"""Reading-plan progress: the per-day sync, and what happens when two devices
write at once.

Split from reading/tests.py because the concurrency half needs a
TransactionTestCase — real transactions, real row locks — and running that
alongside the ordinary sync tests meant the whole file paid for it. It is also a
different question: the rest of that file asks whether a reader's marks and
progress round-trip, and this asks whether two of their devices can race."""

from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

# Module-level in reading/tests.py too — an assignment rather than an import, so
# it travels by hand. Ochorus users are bare Django Users mapped from Supabase.
User = get_user_model()


class PlanProgressSyncTests(TestCase):
    """Server-synced reading-plan progress (roadmap #6)."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000aa")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="p@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _ms(self, days_ago=0):
        import time

        return int(time.time() * 1000) - days_ago * 86_400_000

    def test_put_normalizes_done_and_appears_in_state(self):
        from reading.models import PlanProgress

        res = self.client.put(
            "/api/reading/plan/school-of-prayer/",
            {"started_at": self._ms(), "done": [3, 1, 2, "junk", 9999, 3, -1, 0]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # unique, sorted, 1..400 only
        self.assertEqual(res.data["done"], [1, 2, 3])
        self.assertEqual(PlanProgress.objects.filter(profile=self.profile).count(), 1)
        state = self.client.get("/api/reading/state/").data
        self.assertEqual(len(state["plan_progress"]), 1)
        self.assertEqual(state["plan_progress"][0]["plan_slug"], "school-of-prayer")

    def test_started_at_keeps_the_earliest(self):
        from reading.models import PlanProgress

        self.client.put(
            "/api/reading/plan/humility-12-days/",
            {"started_at": self._ms(days_ago=1), "done": [1]},
            format="json",
        )
        early = PlanProgress.objects.get().started_at
        # a later PUT with a NEWER start must not move the start forward
        self.client.put(
            "/api/reading/plan/humility-12-days/",
            {"started_at": self._ms(days_ago=0), "done": [1, 2]},
            format="json",
        )
        obj = PlanProgress.objects.get()
        self.assertEqual(obj.started_at, early)
        self.assertEqual(obj.done, [1, 2])

    def test_put_unions_and_never_loses_a_completion(self):
        # A stale device PUTting a shorter list must NOT wipe days completed
        # elsewhere — completions are monotonic (findings #1/#2).
        from reading.models import PlanProgress

        self.client.put(
            "/api/reading/plan/p/", {"started_at": self._ms(), "done": [1, 2, 3]}, format="json"
        )
        res = self.client.put(
            "/api/reading/plan/p/", {"started_at": self._ms(), "done": [1, 4]}, format="json"
        )
        self.assertEqual(res.data["done"], [1, 2, 3, 4])  # unioned, 2 & 3 kept
        self.assertEqual(PlanProgress.objects.get().done, [1, 2, 3, 4])

    def test_merge_ignores_a_malformed_plan_progress_payload(self):
        # A non-list must not 500 the whole sign-in reconciliation.
        res = self.client.post(
            "/api/reading/merge/", {"plan_progress": "garbage"}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_merge_unions_done_and_takes_earliest_start(self):
        from django.utils import timezone

        from reading.models import PlanProgress

        # server already has some progress (started "now")
        PlanProgress.objects.create(
            profile=self.profile,
            plan_slug="school-of-prayer",
            started_at=timezone.now(),
            done=[5, 6],
        )
        payload = {
            "plan_progress": [
                {"plan_slug": "school-of-prayer", "started_at": self._ms(days_ago=2), "done": [1, 2, 5]},
                {"plan_slug": "the-inner-chamber-month", "started_at": self._ms(), "done": [1]},
            ]
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data
        rows = {r["plan_slug"]: r for r in state["plan_progress"]}
        # union: nothing a reader finished on either side is dropped
        self.assertEqual(rows["school-of-prayer"]["done"], [1, 2, 5, 6])
        self.assertEqual(rows["the-inner-chamber-month"]["done"], [1])
        # the local start (2 days ago) is earlier than the server's, so it wins
        obj = PlanProgress.objects.get(plan_slug="school-of-prayer")
        self.assertLess(obj.started_at.timestamp(), self._ms() / 1000)

    def test_requires_auth(self):
        anon = APIClient()
        self.assertIn(
            anon.put("/api/reading/plan/x/", {"done": [1]}, format="json").status_code,
            (401, 403),
        )


class PlanProgressFirstWriteRaceTests(TestCase):
    """The union must hold on a plan's FIRST write, not only afterwards.

    `_upsert_plan_progress` promises a completed day is never lost. It locked the
    existing row with `select_for_update()` before merging — but a row that does
    not exist yet cannot be locked: there is no tuple, and a plain FOR UPDATE
    takes no gap lock in Postgres. So on the first write for a plan, two devices
    both saw `existing = None`, both skipped the union, and both tried to create.
    The loser caught the IntegrityError inside `update_or_create`, re-fetched, and
    applied its own defaults verbatim — overwriting the winner's day.

    The guarantee held only from the second write onward, which is exactly when
    nobody is racing.
    """

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000cc")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="race@example.com"
        )

    def _started(self):
        from datetime import UTC, datetime

        return datetime(2026, 8, 1, tzinfo=UTC)

    def test_second_writer_unions_into_a_row_it_did_not_create(self):
        """Device B's day must survive device A having created the row first."""
        from reading.models import PlanProgress
        from reading.views import _upsert_plan_progress

        _upsert_plan_progress(self.profile, "school-of-prayer", [1], self._started())
        _upsert_plan_progress(self.profile, "school-of-prayer", [2], self._started())

        self.assertEqual(PlanProgress.objects.get().done, [1, 2])

    def test_the_row_is_created_before_it_is_locked(self):
        """The mechanism, asserted directly.

        A pre-create lock is unobservable from behaviour alone on SQLite, so this
        pins the ordering the fix depends on: after the first call the row
        exists, so every subsequent writer has a real tuple to lock.
        """
        from reading.models import PlanProgress
        from reading.views import _upsert_plan_progress

        obj = _upsert_plan_progress(self.profile, "humility", [1], self._started())
        self.assertTrue(PlanProgress.objects.filter(pk=obj.pk).exists())
        self.assertEqual(obj.done, [1])

    def test_first_write_keeps_its_own_days(self):
        """The create path still records what it was given."""
        from reading.views import _upsert_plan_progress

        obj = _upsert_plan_progress(self.profile, "abide", [3, 1, 2], self._started())
        self.assertEqual(obj.done, [1, 2, 3])

    def test_earliest_start_wins_across_writers(self):
        from datetime import UTC, datetime

        from reading.models import PlanProgress
        from reading.views import _upsert_plan_progress

        late = datetime(2026, 8, 10, tzinfo=UTC)
        early = datetime(2026, 7, 1, tzinfo=UTC)
        _upsert_plan_progress(self.profile, "abide", [1], late)
        _upsert_plan_progress(self.profile, "abide", [2], early)
        self.assertEqual(PlanProgress.objects.get().started_at, early)

    def test_repeating_the_same_day_is_idempotent(self):
        from reading.models import PlanProgress
        from reading.views import _upsert_plan_progress

        for _ in range(3):
            _upsert_plan_progress(self.profile, "abide", [1], self._started())
        self.assertEqual(PlanProgress.objects.get().done, [1])
        self.assertEqual(PlanProgress.objects.count(), 1)


@skipUnless(connection.vendor == "postgresql", "row locking is a Postgres behaviour")
class PlanProgressConcurrentWriteTests(TransactionTestCase):
    """Two devices writing a plan's FIRST day at the same time.

    The sequential tests above document the merge contract but cannot prove this
    fix: run against the old code they pass, because the second call always found
    a row to lock. Only real concurrency reaches the window the bug lived in —
    between the existence check and the insert, when there is no tuple to lock.

    TransactionTestCase (not TestCase) because the threads need to see each
    other's COMMITs, which a test-wide transaction would hide. Postgres-only:
    SQLite serialises writers anyway, so the window does not exist there.

    Note what this test does and does not guarantee. It never fails on correct
    code — the fix is safe under every interleaving — so it is not flaky. Against
    the old code it fails only when the threads actually interleave, which is the
    honest limit of a concurrency test written without instrumenting the code
    under test.
    """

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000dd")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="conc@example.com"
        )

    def test_neither_device_loses_its_day(self):
        import threading
        from datetime import UTC, datetime

        from django.db import connections

        from reading.models import PlanProgress
        from reading.views import _upsert_plan_progress

        started = datetime(2026, 8, 1, tzinfo=UTC)
        ready = threading.Barrier(2, timeout=10)
        errors: list[BaseException] = []

        def write(day: int):
            try:
                ready.wait()  # both threads enter the critical section together
                _upsert_plan_progress(self.profile, "school-of-prayer", [day], started)
            except BaseException as exc:  # noqa: BLE001 — re-raised in the assertions
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=write, args=(d,)) for d in (1, 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        self.assertEqual(errors, [], f"a writer raised: {errors}")
        self.assertEqual(PlanProgress.objects.count(), 1)
        self.assertEqual(
            PlanProgress.objects.get().done,
            [1, 2],
            "a day completed on one device was lost to the other's write",
        )
