from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .marks import clean_mark_list, from_legacy, merge_mark_lists
from .models import ChapterMarks, Favorite, ReadingDay, ReadingProgress

User = get_user_model()


def mark(p, s, e, note=None, id=None):
    m = {"id": id or f"{p}:{s}:{e}", "p": p, "s": s, "e": e}
    if note:
        m["note"] = note
    return m


class ReadingSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000001")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="r@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_progress_upsert_and_state(self):
        res = self.client.put(
            "/api/reading/progress/humility/",
            {"language": "en", "chapter_order": 3, "paragraph_index": 12},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["chapter_order"], 3)

        self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 5, "paragraph_index": 0},
            format="json",
        )
        self.assertEqual(ReadingProgress.objects.filter(profile=self.profile).count(), 1)

        state = self.client.get("/api/reading/state/").data
        self.assertEqual(len(state["progress"]), 1)
        self.assertEqual(state["progress"][0]["chapter_order"], 5)

    def test_range_marks_put_and_delete(self):
        res = self.client.put(
            "/api/reading/marks/humility/2/",
            {"marks": [mark(1, 5, 42, note=" keep "), mark(1, 5, 42), {"p": -1}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # deduped by range, malformed dropped, note trimmed
        self.assertEqual(len(res.data["marks"]), 1)
        self.assertEqual(res.data["marks"][0]["note"], "keep")

        self.client.put("/api/reading/marks/humility/2/", {"marks": []}, format="json")
        self.assertEqual(ChapterMarks.objects.count(), 0)

    def test_marks_preserve_highlight_colour(self):
        # A valid colour survives; an unknown one is dropped (default = gold).
        cleaned = clean_mark_list(
            [{**mark(0, 0, 5), "color": "blue"}, {**mark(1, 0, 5), "color": "chartreuse"}]
        )
        self.assertEqual(cleaned[0].get("color"), "blue")
        self.assertNotIn("color", cleaned[1])

    def test_sermon_marks_shim_writes_unified_rows(self):
        # The pre-unification endpoint (PR #293 bundles) keeps working, but
        # its writes land in ChapterMarks(kind="sermon") and its response
        # keeps the old shape.
        res = self.client.put(
            "/api/reading/sermon-marks/himself/",
            {"marks": [{**mark(2, 0, 9, note="a"), "color": "green"}], "language": "en"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["sermon_slug"], "himself")
        self.assertEqual(res.data["marks"][0]["color"], "green")
        row = ChapterMarks.objects.get()
        self.assertEqual((row.kind, row.book_slug, row.chapter_order), ("sermon", "himself", 1))
        self.client.put("/api/reading/sermon-marks/himself/", {"marks": []}, format="json")
        self.assertEqual(ChapterMarks.objects.count(), 0)

    def test_sermon_marks_merge_and_state_compat(self):
        # Old-shape merge payloads fold into the unified table and the state
        # echo still carries the legacy field (old bundles rehydrate from it).
        ChapterMarks.objects.create(
            profile=self.profile, kind="sermon", book_slug="himself",
            chapter_order=1, marks=[mark(0, 0, 3)],
        )
        payload = {"sermon_marks": [{"sermon_slug": "himself", "marks": [mark(1, 0, 4)]}]}
        state = self.client.post("/api/reading/merge/", payload, format="json").data
        self.assertIn("sermon_marks", state)
        rows = {m["sermon_slug"]: m for m in state["sermon_marks"]}
        self.assertEqual(len(rows["himself"]["marks"]), 2)  # unioned, none dropped
        self.assertEqual(ChapterMarks.objects.get().kind, "sermon")

    def test_legacy_payload_converts(self):
        # An old client (cached SPA) still sends paragraph-level h/n.
        res = self.client.put(
            "/api/reading/marks/humility/1/",
            {"highlights": [3], "notes": {"5": "old note"}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        ranges = {(m["p"], m["s"], m["e"]) for m in res.data["marks"]}
        self.assertEqual(ranges, {(3, 0, -1), (5, 0, -1)})
        by_p = {m["p"]: m for m in res.data["marks"]}
        self.assertEqual(by_p[5]["note"], "old note")

    def test_merge_unions_ranges_and_keeps_newer_progress(self):
        ReadingProgress.objects.create(
            profile=self.profile, book_slug="humility", chapter_order=2, paragraph_index=1
        )
        ChapterMarks.objects.create(
            profile=self.profile,
            book_slug="humility",
            chapter_order=1,
            marks=[mark(1, 0, 20, note="short")],
        )

        payload = {
            "progress": [
                {
                    "book_slug": "humility",
                    "chapter_order": 7,
                    "paragraph_index": 3,
                    "updated_at": 10_000_000_000_000,
                },
                {"book_slug": "abide", "chapter_order": 1, "paragraph_index": 0},
            ],
            "marks": [
                {
                    "book_slug": "humility",
                    "chapter_order": 1,
                    "marks": [
                        mark(1, 0, 20, note="a much longer note"),
                        mark(2, 4, 9),
                    ],
                }
            ],
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data

        prog = {p["book_slug"]: p for p in state["progress"]}
        self.assertEqual(prog["humility"]["chapter_order"], 7)
        self.assertIn("abide", prog)

        ms = state["marks"][0]["marks"]
        self.assertEqual({(m["p"], m["s"], m["e"]) for m in ms}, {(1, 0, 20), (2, 4, 9)})
        self.assertEqual(ms[0]["note"], "a much longer note")  # longer note won

    def test_merge_folds_in_unconverted_server_row(self):
        # Server row predating the range conversion (only legacy fields set).
        ChapterMarks.objects.create(
            profile=self.profile,
            book_slug="humility",
            chapter_order=4,
            marks=[],
            highlights=[2],
            notes={"2": "legacy"},
        )
        payload = {
            "marks": [
                {"book_slug": "humility", "chapter_order": 4, "marks": [mark(0, 1, 9)]}
            ]
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data
        ms = state["marks"][0]["marks"]
        self.assertEqual(
            {(m["p"], m["s"], m["e"]) for m in ms}, {(0, 1, 9), (2, 0, -1)}
        )

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/reading/state/").status_code, 401)


class FavoriteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000002")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="f@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_save_idempotent_unsave_and_state(self):
        res = self.client.put("/api/reading/favorites/author/andrew-murray/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["kind"], res.data["slug"]), ("author", "andrew-murray"))
        # Saving twice keeps one row.
        self.client.put("/api/reading/favorites/author/andrew-murray/")
        self.client.put("/api/reading/favorites/plan/school-of-prayer/")
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 2)

        state = self.client.get("/api/reading/state/").data
        favs = {(f["kind"], f["slug"]) for f in state["favorites"]}
        self.assertEqual(
            favs, {("author", "andrew-murray"), ("plan", "school-of-prayer")}
        )

        res = self.client.delete("/api/reading/favorites/author/andrew-murray/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 1)

    def test_unknown_kind_rejected(self):
        res = self.client.put("/api/reading/favorites/topic/prayer/")
        self.assertEqual(res.status_code, 400)

    def test_merge_unions_favorites_and_skips_unknown(self):
        Favorite.objects.create(profile=self.profile, kind="book", slug="humility")
        res = self.client.post(
            "/api/reading/merge/",
            {
                "favorites": [
                    {"kind": "book", "slug": "humility"},  # already on server
                    {"kind": "author", "slug": "c-h-spurgeon"},  # offline heart
                    {"kind": "galaxy", "slug": "andromeda"},  # unknown kind
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        favs = {(f["kind"], f["slug"]) for f in res.data["favorites"]}
        self.assertEqual(favs, {("book", "humility"), ("author", "c-h-spurgeon")})

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.put("/api/reading/favorites/book/humility/").status_code, 401)


class MarkHelpersTests(TestCase):
    def test_from_legacy(self):
        ms = from_legacy([1, 3], {"3": "note on 3", "9": "solo note"})
        self.assertEqual(
            {(m["p"], m["s"], m["e"]) for m in ms}, {(1, 0, -1), (3, 0, -1), (9, 0, -1)}
        )
        by_p = {m["p"]: m for m in ms}
        self.assertEqual(by_p[3]["note"], "note on 3")
        self.assertNotIn("note", by_p[1])

    def test_merge_is_a_union(self):
        a = [mark(0, 0, 5), mark(1, 2, 8, note="x")]
        b = [mark(1, 2, 8, note="longer note"), mark(2, 0, -1)]
        merged = merge_mark_lists(a, b)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[1]["note"], "longer note")

    def test_clean_caps_count_and_lengths(self):
        from .marks import MAX_ID_LEN, MAX_MARKS_PER_CHAPTER, MAX_NOTE_LEN

        # One chapter can't store an unbounded number of marks…
        raw = [{"id": f"m{i}", "p": i, "s": 0, "e": 1} for i in range(MAX_MARKS_PER_CHAPTER + 50)]
        cleaned = clean_mark_list(raw)
        self.assertEqual(len(cleaned), MAX_MARKS_PER_CHAPTER)
        # …nor a giant note or id.
        big = clean_mark_list([{"id": "x" * 200, "p": 0, "s": 0, "e": 1, "note": "n" * 9000}])
        self.assertEqual(len(big), 1)
        self.assertLessEqual(len(big[0]["id"]), MAX_ID_LEN)
        self.assertEqual(len(big[0]["note"]), MAX_NOTE_LEN)

    def test_merge_holds_the_per_chapter_cap(self):
        from .marks import MAX_MARKS_PER_CHAPTER

        # Two full lists (disjoint ranges) union to 2× the cap; the result is held
        # at the cap so a merge can't grow past the bound.
        a = clean_mark_list([{"id": f"a{i}", "p": i, "s": 0, "e": 1} for i in range(MAX_MARKS_PER_CHAPTER)])
        b = clean_mark_list(
            [{"id": f"b{i}", "p": i, "s": 0, "e": 1} for i in range(10_000, 10_000 + MAX_MARKS_PER_CHAPTER)]
        )
        self.assertEqual(len(merge_mark_lists(a, b)), MAX_MARKS_PER_CHAPTER)


class WorkKindTests(TestCase):
    """Sermons in the reading layer (kind discriminator, roadmap #10)."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000002")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="k@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_sermon_and_book_progress_share_a_slug_without_colliding(self):
        self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 3, "paragraph_index": 5},
            format="json",
        )
        res = self.client.put(
            "/api/reading/progress/humility/?kind=sermon",
            {"paragraph_index": 40},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["kind"], "sermon")
        rows = ReadingProgress.objects.filter(profile=self.profile)
        self.assertEqual(rows.count(), 2)
        self.assertEqual(
            {(r.kind, r.chapter_order, r.paragraph_index) for r in rows},
            {("book", 3, 5), ("sermon", 1, 40)},
        )

    def test_unknown_kind_rejected_not_misfiled(self):
        res = self.client.put(
            "/api/reading/progress/humility/?kind=plan",
            {"paragraph_index": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ReadingProgress.objects.count(), 0)

    def test_sermon_marks_are_scoped_by_kind(self):
        self.client.put(
            "/api/reading/marks/free-grace/1/",
            {"marks": [mark(0, 0, 10)]},
            format="json",
        )
        self.client.put(
            "/api/reading/marks/free-grace/1/?kind=sermon",
            {"marks": [mark(2, 5, 20, note="amen")]},
            format="json",
        )
        self.assertEqual(ChapterMarks.objects.count(), 2)
        # Deleting the sermon's marks (empty payload) leaves the book row.
        self.client.put(
            "/api/reading/marks/free-grace/1/?kind=sermon", {"marks": []}, format="json"
        )
        remaining = ChapterMarks.objects.get()
        self.assertEqual(remaining.kind, "book")

    def test_bio_marks_are_a_valid_kind(self):
        # Biography highlights (roadmap #12): kind="bio", single document like
        # sermons (chapter_order pinned to 1), slug names the author.
        res = self.client.put(
            "/api/reading/marks/andrew-murray/1/?kind=bio",
            {"marks": [mark(0, 0, 12, note="what a life")]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        row = ChapterMarks.objects.get()
        self.assertEqual((row.kind, row.book_slug, row.chapter_order), ("bio", "andrew-murray", 1))
        # And the merge path carries it too.
        res = self.client.post(
            "/api/reading/merge/",
            {"marks": [{"book_slug": "c-h-spurgeon", "kind": "bio", "chapter_order": 1,
                        "marks": [mark(3, 2, 9)]}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        kinds = {(m.kind, m.book_slug) for m in ChapterMarks.objects.all()}
        self.assertEqual(kinds, {("bio", "andrew-murray"), ("bio", "c-h-spurgeon")})

    def test_merge_carries_kind_and_skips_unknown(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": [
                    {"book_slug": "humility", "chapter_order": 2},  # legacy: no kind
                    {"book_slug": "free-grace", "kind": "sermon", "paragraph_index": 7},
                    {"book_slug": "future", "kind": "plan", "paragraph_index": 1},
                ],
                "marks": [
                    {"book_slug": "free-grace", "kind": "sermon", "chapter_order": 1,
                     "marks": [mark(1, 0, 5)]},
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        kinds = {(p.kind, p.book_slug) for p in ReadingProgress.objects.all()}
        self.assertEqual(kinds, {("book", "humility"), ("sermon", "free-grace")})
        m = ChapterMarks.objects.get()
        self.assertEqual((m.kind, m.book_slug, m.chapter_order), ("sermon", "free-grace", 1))
        # The state echo includes kind so clients can rehydrate by kind.
        self.assertEqual(
            {r["kind"] for r in res.data["progress"]}, {"book", "sermon"}
        )


class ActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000003")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="a@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_record_day_idempotent_and_in_state(self):
        res = self.client.put("/api/reading/activity/2026-07-20/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["day"], "2026-07-20")
        # Recording the same day again keeps one row.
        self.client.put("/api/reading/activity/2026-07-20/")
        self.client.put("/api/reading/activity/2026-07-21/")
        self.assertEqual(ReadingDay.objects.filter(profile=self.profile).count(), 2)
        state = self.client.get("/api/reading/state/").data
        self.assertEqual(set(state["activity"]), {"2026-07-20", "2026-07-21"})

    def test_bad_date_rejected(self):
        res = self.client.put("/api/reading/activity/not-a-date/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ReadingDay.objects.count(), 0)

    def test_merge_unions_activity_and_skips_bad(self):
        ReadingDay.objects.create(profile=self.profile, day="2026-07-20")
        res = self.client.post(
            "/api/reading/merge/",
            {"activity": ["2026-07-20", "2026-07-22", "garbage"]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            {d.day.isoformat() for d in ReadingDay.objects.filter(profile=self.profile)},
            {"2026-07-20", "2026-07-22"},
        )
        self.assertEqual(set(res.data["activity"]), {"2026-07-20", "2026-07-22"})

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.put("/api/reading/activity/2026-07-20/").status_code, 401)

    def test_merge_ignores_a_non_list_activity_payload(self):
        # A dict's keys look like valid dates; without the type guard they'd be
        # iterated and (mis)merged. The guard makes a non-list a no-op.
        res = self.client.post(
            "/api/reading/merge/",
            {"activity": {"2026-07-20": 1}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ReadingDay.objects.filter(profile=self.profile).count(), 0)


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


class MalformedPayloadTests(TestCase):
    """A stale or buggy client can send a wrong-shaped body (a JSON array where
    a dict is expected, non-dict rows in a merge list). None of it may 500: the
    endpoints skip the junk and return normally, so a single bad field never
    aborts a reader's sign-in reconciliation."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000ff")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="m@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_merge_ignores_non_list_sections(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": "oops",
                "marks": "nope",
                "favorites": {"not": "a list"},
                "sermon_marks": 42,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_merge_skips_non_dict_rows(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": [42, "x", None],
                "marks": [7],
                "favorites": [1, 2, 3],
                "sermon_marks": ["nope"],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # Nothing junk was written.
        self.assertEqual(ReadingProgress.objects.filter(profile=self.profile).count(), 0)
        self.assertEqual(ChapterMarks.objects.filter(profile=self.profile).count(), 0)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_merge_with_a_json_array_body_does_not_500(self):
        res = self.client.post("/api/reading/merge/", [1, 2, 3], format="json")
        self.assertEqual(res.status_code, 200)

    def test_put_endpoints_reject_a_non_dict_body_without_losing_data(self):
        # A bare array/scalar body must be a clean 400 — NOT a 500, and crucially
        # NOT coerced to {} (which for marks means "delete" and for progress means
        # "reset to chapter 1"). Existing data must survive the malformed request.
        ReadingProgress.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            language="en", chapter_order=15, paragraph_index=4,
        )
        ChapterMarks.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            chapter_order=1, marks=[mark(0, 1, 5)],
        )
        ChapterMarks.objects.create(
            profile=self.profile, kind="sermon", book_slug="a-sermon",
            chapter_order=1, marks=[mark(0, 2, 6)],
        )

        for url in (
            "/api/reading/progress/humility/",
            "/api/reading/marks/humility/1/",
            "/api/reading/plan/school-of-prayer/",
            "/api/reading/sermon-marks/a-sermon/",
        ):
            self.assertEqual(
                self.client.put(url, [1, 2, 3], format="json").status_code,
                400,
                msg=url,
            )

        # Nothing was deleted or reset by the malformed requests.
        prog = ReadingProgress.objects.get(profile=self.profile, book_slug="humility")
        self.assertEqual(prog.chapter_order, 15)
        self.assertTrue(
            ChapterMarks.objects.filter(
                profile=self.profile, kind="book", book_slug="humility", chapter_order=1
            ).exists()
        )
        self.assertTrue(
            ChapterMarks.objects.filter(
                profile=self.profile, kind="sermon", book_slug="a-sermon"
            ).exists()
        )


class MergeHardeningTests(TestCase):
    """Wave 2: caps, atomicity, and input validation on the sync endpoints."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000aa")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="h@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_merge_caps_each_section(self):
        from .views import MAX_MERGE_ROWS

        favorites = [
            {"kind": "book", "slug": f"b{i}"} for i in range(MAX_MERGE_ROWS + 25)
        ]
        res = self.client.post(
            "/api/reading/merge/", {"favorites": favorites}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Favorite.objects.filter(profile=self.profile).count(), MAX_MERGE_ROWS
        )

    def test_merge_is_atomic_on_a_mid_phase_failure(self):
        from unittest.mock import patch

        from .views import MergeView

        # Favorites merge before activity; force activity to blow up and assert the
        # already-written favorites are rolled back (no half-merged account). The
        # client is configured to turn the unhandled error into a 500 response
        # rather than re-raise it into the test.
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.user)
        payload = {"favorites": [{"kind": "book", "slug": "humility"}], "activity": []}
        with patch.object(
            MergeView, "_merge_activity", side_effect=RuntimeError("boom")
        ):
            res = client.post("/api/reading/merge/", payload, format="json")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_merge_skips_negative_and_zero_chapter_orders(self):
        payload = {
            "marks": [
                {"book_slug": "humility", "chapter_order": -5, "marks": [{"p": 0, "s": 0, "e": 1}]},
                {"book_slug": "humility", "chapter_order": 0, "marks": [{"p": 0, "s": 0, "e": 1}]},
                {"book_slug": "humility", "chapter_order": 2, "marks": [{"p": 0, "s": 0, "e": 1}]},
            ]
        }
        self.client.post("/api/reading/merge/", payload, format="json")
        orders = list(
            ChapterMarks.objects.filter(profile=self.profile).values_list(
                "chapter_order", flat=True
            )
        )
        self.assertEqual(orders, [2])  # -5 and 0 dropped, no junk chapter-0 row

    def test_merge_skips_over_long_slugs(self):
        payload = {"favorites": [{"kind": "book", "slug": "x" * 300}]}
        res = self.client.post("/api/reading/merge/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_put_rejects_over_long_slug_and_out_of_range_order(self):
        # A 300-char slug is a 400, not a Postgres DataError 500.
        self.assertEqual(
            self.client.put(
                f"/api/reading/progress/{'x' * 300}/",
                {"chapter_order": 1},
                format="json",
            ).status_code,
            400,
        )
        # An order past the ceiling is a 400, not a 500.
        self.assertEqual(
            self.client.put(
                "/api/reading/marks/humility/999999/",
                {"marks": [{"p": 0, "s": 0, "e": 1}]},
                format="json",
            ).status_code,
            400,
        )

    def test_oversized_chapter_order_is_clamped_not_a_500(self):
        # A value past int4 max would DataError-500 on Postgres; it's clamped.
        from .views import MAX_CHAPTER_ORDER

        res = self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 3_000_000_000, "paragraph_index": 9_000_000_000},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(res.data["chapter_order"], MAX_CHAPTER_ORDER)
        # Same value inside a merge row must not 500 the reconciliation either.
        merged = self.client.post(
            "/api/reading/merge/",
            {"progress": [{"book_slug": "abide", "chapter_order": 3_000_000_000}]},
            format="json",
        )
        self.assertEqual(merged.status_code, 200)

    def test_non_string_language_is_not_a_500(self):
        # `(x or "en")[:10]` on a truthy non-string (5, []) would TypeError-500.
        res = self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 1, "language": 5},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["language"], "en")
        merged = self.client.post(
            "/api/reading/merge/",
            {"marks": [{"book_slug": "x", "chapter_order": 1, "language": [1],
                        "marks": [{"p": 0, "s": 0, "e": 1}]}]},
            format="json",
        )
        self.assertEqual(merged.status_code, 200)

    def test_reading_writes_are_throttled_per_account(self):
        from common.testing import enforcing_throttle

        from .views import _ReadingWriteThrottle

        # Squeezed to 2/min for this test; the 3rd write in the window 429s.
        # Throttles are inert under `manage.py test` — see common.throttling —
        # so this hands the class a real, private cache for the duration.
        with enforcing_throttle(_ReadingWriteThrottle, "2/min"):
            codes = [
                self.client.put(
                    "/api/reading/favorites/book/humility/", format="json"
                ).status_code
                for _ in range(3)
            ]
        self.assertEqual(codes[:2], [200, 200])
        self.assertEqual(codes[2], 429)
