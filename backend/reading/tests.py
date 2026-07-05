from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .models import ChapterMarks, ReadingProgress

User = get_user_model()


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

        # Upserting again updates the same row, not a new one.
        self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 5, "paragraph_index": 0},
            format="json",
        )
        self.assertEqual(ReadingProgress.objects.filter(profile=self.profile).count(), 1)

        state = self.client.get("/api/reading/state/").data
        self.assertEqual(len(state["progress"]), 1)
        self.assertEqual(state["progress"][0]["chapter_order"], 5)

    def test_marks_put_and_delete(self):
        res = self.client.put(
            "/api/reading/marks/humility/2/",
            {"highlights": [1, 4, 4], "notes": {"1": " keep ", "9": ""}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["highlights"], [1, 4])  # deduped + sorted
        self.assertEqual(res.data["notes"], {"1": "keep"})  # trimmed, empties dropped

        # Empty payload removes the row.
        self.client.put(
            "/api/reading/marks/humility/2/",
            {"highlights": [], "notes": {}},
            format="json",
        )
        self.assertEqual(ChapterMarks.objects.count(), 0)

    def test_merge_unions_marks_and_keeps_newer_progress(self):
        # Server already has some state.
        ReadingProgress.objects.create(
            profile=self.profile, book_slug="humility", chapter_order=2, paragraph_index=1
        )
        ChapterMarks.objects.create(
            profile=self.profile,
            book_slug="humility",
            chapter_order=1,
            highlights=[1],
            notes={"1": "short"},
        )

        payload = {
            "progress": [
                # Newer than the server row (year ~2286 in ms) → should win.
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
                    "highlights": [2],
                    "notes": {"1": "a much longer note", "5": "new"},
                }
            ],
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data

        prog = {p["book_slug"]: p for p in state["progress"]}
        self.assertEqual(prog["humility"]["chapter_order"], 7)  # local newer won
        self.assertIn("abide", prog)  # local-only book added

        marks = state["marks"][0]
        self.assertEqual(marks["highlights"], [1, 2])  # unioned
        self.assertEqual(marks["notes"]["1"], "a much longer note")  # longer wins
        self.assertEqual(marks["notes"]["5"], "new")

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/reading/state/").status_code, 401)
