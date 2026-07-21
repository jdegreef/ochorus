from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .marks import from_legacy, merge_mark_lists
from .models import ChapterMarks, ReadingProgress

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
