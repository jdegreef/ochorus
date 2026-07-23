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
