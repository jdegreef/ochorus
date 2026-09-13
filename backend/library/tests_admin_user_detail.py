"""The per-user admin detail endpoint (/api/admin/users/<uid>/).

Builds one profile with a spread of activity — progress (in-progress + finished),
favorites across kinds, highlights, bookmarks, a plan, and reading days — and
asserts the payload the detail page renders, plus that titles resolve and the
timeline merges. Auth is the loopback DEBUG bypass, as the other admin tests use.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import (
    Bookmark,
    ChapterMarks,
    Favorite,
    PlanProgress,
    ReadingDay,
    ReadingProgress,
    ReadingSession,
)

from .models import Author, Book, Chapter, Plan, PlanDay, Sermon


@override_settings(DEBUG=True)
class AdminUserDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        author = Author.objects.create(slug="am", name="Andrew Murray", bio="Preacher.")
        book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=book, order=1, title="One", body_html="<p>a b c</p>"
        )
        Chapter.objects.create(
            book=book, order=2, title="Two", body_html="<p>d e f</p>"
        )
        # A Spanish edition of the same slug, so title resolution has to PREFER
        # the English row rather than whichever it sees first.
        Book.objects.create(
            author=author, slug="humility", language="es", title="Humildad"
        )
        Sermon.objects.create(
            author=author,
            slug="all-of-grace",
            language="en",
            title="All of Grace",
            body_html="<p>grace</p>",
        )
        plan = Plan.objects.create(slug="p1", language="en", title="Plan One")
        PlanDay.objects.create(plan=plan, day=1, book_slug="humility", chapter_order=1)
        PlanDay.objects.create(plan=plan, day=2, book_slug="humility", chapter_order=2)

        user = get_user_model().objects.create(
            username="reader1", email="reader@example.com"
        )
        self.uid = uuid.uuid4()
        self.profile = UserProfile.objects.create(
            user=user,
            supabase_uid=self.uid,
            email="reader@example.com",
            display_name="A Reader",
            locale="es",
            theme="dark",
            providers="email,google",
            timezone="America/New_York",
            last_seen_at=timezone.now(),
        )

        # In-progress book, finished sermon.
        ReadingProgress.objects.create(
            profile=self.profile,
            kind="book",
            book_slug="humility",
            language="en",
            chapter_order=2,
            paragraph_index=4,
        )
        ReadingProgress.objects.create(
            profile=self.profile,
            kind="sermon",
            book_slug="all-of-grace",
            language="en",
            chapter_order=1,
            finished_at=timezone.now(),
        )
        # Favorites across kinds.
        Favorite.objects.create(profile=self.profile, kind="book", slug="humility")
        Favorite.objects.create(profile=self.profile, kind="author", slug="am")
        Favorite.objects.create(profile=self.profile, kind="quote", slug="am-abc123")
        # Highlight with a note, and a bookmark.
        ChapterMarks.objects.create(
            profile=self.profile,
            kind="book",
            book_slug="humility",
            language="en",
            chapter_order=1,
            marks=[
                {"id": "m1", "p": 0, "s": 0, "e": 3, "text": "a b c", "note": "yes"}
            ],
        )
        Bookmark.objects.create(
            profile=self.profile,
            kind="book",
            book_slug="humility",
            chapter_order=1,
            paragraph_index=0,
            snippet="a b c",
            title="One",
        )
        # A plan in progress.
        PlanProgress.objects.create(
            profile=self.profile,
            plan_slug="p1",
            started_at=timezone.now(),
            done=[1],
        )
        # A live 3-day reading streak ending today.
        today = timezone.now().date()
        for i in range(3):
            ReadingDay.objects.create(
                profile=self.profile, day=today - timedelta(days=i)
            )
        # Two reading sittings (time on site): 8 min + 4 min.
        now = timezone.now()
        ReadingSession.objects.create(
            profile=self.profile,
            client_id="c1",
            started_at=now - timedelta(minutes=10),
            last_seen_at=now - timedelta(minutes=2),
            seconds=480,
            kind="book",
            book_slug="humility",
        )
        ReadingSession.objects.create(
            profile=self.profile,
            client_id="c2",
            started_at=now - timedelta(hours=3),
            last_seen_at=now - timedelta(hours=2, minutes=56),
            seconds=240,
            kind="sermon",
            book_slug="all-of-grace",
        )
        # A zero-second sitting must NOT count (matches the global avg denominator).
        ReadingSession.objects.create(
            profile=self.profile,
            client_id="c0",
            started_at=now,
            last_seen_at=now,
            seconds=0,
        )

    def get(self, uid=None):
        return self.client.get(f"/api/admin/users/{uid or self.uid}/")

    def test_unknown_uid_is_404(self):
        res = self.get(uuid.uuid4())
        self.assertEqual(res.status_code, 404)

    def test_profile_block(self):
        d = self.get().json()
        p = d["profile"]
        self.assertEqual(p["uid"], str(self.uid))
        self.assertEqual(p["display_name"], "A Reader")
        self.assertEqual(p["theme_label"], "Lamplight (dark)")
        self.assertEqual([x["code"] for x in p["providers"]], ["email", "google"])
        self.assertEqual(p["country"]["code"], "US")

    def test_stats(self):
        s = self.get().json()["stats"]
        self.assertEqual(s["works_started"], 2)
        self.assertEqual(s["works_finished"], 1)
        self.assertEqual(s["favorites"], 3)
        self.assertEqual(s["highlights"], 1)
        self.assertEqual(s["bookmarks"], 1)
        self.assertEqual(s["days_read"], 3)
        self.assertEqual(s["streak_current"], 3)
        self.assertEqual(s["streak_longest"], 3)

    def test_reading_split_and_titles(self):
        d = self.get().json()
        self.assertEqual(len(d["reading"]["in_progress"]), 1)
        self.assertEqual(d["reading"]["in_progress"][0]["title"], "Humility")
        self.assertEqual(len(d["reading"]["finished"]), 1)
        self.assertEqual(d["reading"]["finished"][0]["title"], "All of Grace")

    def test_favorites_labelled(self):
        favs = {
            (f["kind"], f["slug"]): f["label"] for f in self.get().json()["favorites"]
        }
        self.assertEqual(favs[("book", "humility")], "Humility")
        self.assertEqual(favs[("author", "am")], "Andrew Murray")
        # A quote keeps its opaque slug.
        self.assertEqual(favs[("quote", "am-abc123")], "am-abc123")

    def test_plan_progress(self):
        plans = self.get().json()["plans"]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["title"], "Plan One")
        self.assertEqual(plans[0]["done"], 1)
        self.assertEqual(plans[0]["total_days"], 2)
        self.assertEqual(plans[0]["pct"], 50)

    def test_activity_today_is_reader_local(self):
        # today is judged in the reader's own zone (profile.timezone), not UTC —
        # so the streak and the frontend heatmap align on the same day.
        from zoneinfo import ZoneInfo

        expected = (
            timezone.now().astimezone(ZoneInfo("America/New_York")).date().isoformat()
        )
        self.assertEqual(self.get().json()["activity"]["today"], expected)

    def test_reading_time(self):
        d = self.get().json()
        self.assertEqual(d["stats"]["reading_seconds"], 720)  # 480 + 240
        self.assertEqual(d["stats"]["sessions"], 2)
        self.assertEqual(d["stats"]["avg_session_seconds"], 360)
        # Sessions listed newest-first with a resolved title.
        self.assertEqual(len(d["sessions"]), 2)
        self.assertEqual(d["sessions"][0]["seconds"], 480)
        self.assertEqual(d["sessions"][0]["title"], "Humility")

    def test_highlights_carry_note(self):
        hl = self.get().json()["highlights"]
        self.assertEqual(len(hl), 1)
        self.assertEqual(hl[0]["marks"][0]["note"], "yes")

    def test_timeline_merges_and_sorts(self):
        tl = self.get().json()["timeline"]
        types = {e["type"] for e in tl}
        self.assertTrue(
            {"read", "finished", "favorite", "bookmark", "highlight", "plan_started"}
            <= types
        )
        stamps = [e["at"] for e in tl]
        self.assertEqual(stamps, sorted(stamps, reverse=True))

    def test_requires_admin(self):
        # Remote (non-loopback) request without a token is refused.
        res = self.client.get(
            f"/api/admin/users/{self.uid}/", REMOTE_ADDR="203.0.113.9"
        )
        self.assertIn(res.status_code, (401, 403))
