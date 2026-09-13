"""The reading-sessions sync endpoint (PUT /api/reading/sessions/).

Sessions carry a client-owned id and accumulate active reading time; the sync
upserts them with a union rule (seconds grow, earliest start / latest last-seen
win). These tests cover the union, the clamps, the skips, and auth.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .models import ReadingSession
from .views import MAX_SESSION_SECONDS, _now_ms

User = get_user_model()


class SessionsSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000009")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="r@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.now = _now_ms()

    def put(self, sessions):
        return self.client.put(
            "/api/reading/sessions/", {"sessions": sessions}, format="json"
        )

    def test_requires_auth(self):
        res = APIClient().put("/api/reading/sessions/", {"sessions": []}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_creates_a_session(self):
        res = self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 600_000,
                    "last_seen_at": self.now,
                    "seconds": 480,
                    "kind": "book",
                    "book_slug": "humility",
                    "language": "en",
                }
            ]
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True, "count": 1})
        s = ReadingSession.objects.get(profile=self.profile, client_id="s1")
        self.assertEqual(s.seconds, 480)
        self.assertEqual(s.kind, "book")
        self.assertEqual(s.book_slug, "humility")
        self.assertEqual(s.language, "en")

    def test_union_grows_never_shrinks(self):
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 300_000,
                    "last_seen_at": self.now - 120_000,
                    "seconds": 120,
                }
            ]
        )
        # A later sync with more time and a later last-seen but an EARLIER start.
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 600_000,
                    "last_seen_at": self.now,
                    "seconds": 300,
                }
            ]
        )
        s = ReadingSession.objects.get(client_id="s1")
        self.assertEqual(s.seconds, 300)
        self.assertEqual(s.started_at.timestamp() * 1000, self.now - 600_000)
        self.assertEqual(s.last_seen_at.timestamp() * 1000, self.now)
        # A stale sync with smaller values must not shrink it.
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 100_000,
                    "last_seen_at": self.now - 50_000,
                    "seconds": 60,
                }
            ]
        )
        s.refresh_from_db()
        self.assertEqual(s.seconds, 300)
        self.assertEqual(s.last_seen_at.timestamp() * 1000, self.now)

    def test_context_is_write_once(self):
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 10,
                }
            ]
        )
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 20,
                    "kind": "sermon",
                    "book_slug": "all-of-grace",
                }
            ]
        )
        s = ReadingSession.objects.get(client_id="s1")
        # First sync had no context, so the second fills it.
        self.assertEqual(s.kind, "sermon")
        self.assertEqual(s.book_slug, "all-of-grace")
        # A third sync must NOT overwrite the now-set context.
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 30,
                    "kind": "book",
                    "book_slug": "humility",
                }
            ]
        )
        s.refresh_from_db()
        self.assertEqual(s.kind, "sermon")
        self.assertEqual(s.book_slug, "all-of-grace")

    def test_seconds_clamped(self):
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 10**9,
                }
            ]
        )
        s = ReadingSession.objects.get(client_id="s1")
        self.assertEqual(s.seconds, MAX_SESSION_SECONDS)

    def test_bad_rows_skipped(self):
        res = self.put(
            [
                {
                    "client_id": "",
                    "started_at": self.now,
                    "last_seen_at": self.now,
                    "seconds": 5,
                },  # blank id
                {
                    "client_id": "ok",
                    "started_at": "nope",
                    "last_seen_at": self.now,
                    "seconds": 5,
                },  # bad ts
                {
                    "client_id": "unknown-kind",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 5,
                    "kind": "podcast",
                },
            ]
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)  # only the third is valid
        self.assertFalse(ReadingSession.objects.filter(client_id="").exists())
        self.assertFalse(ReadingSession.objects.filter(client_id="ok").exists())
        # An unknown kind is dropped to blank, not stored.
        self.assertEqual(ReadingSession.objects.get(client_id="unknown-kind").kind, "")

    def test_last_seen_never_before_start(self):
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now,
                    "last_seen_at": self.now - 999_000,
                    "seconds": 5,
                }
            ]
        )
        s = ReadingSession.objects.get(client_id="s1")
        self.assertEqual(s.last_seen_at, s.started_at)

    def test_scoped_to_own_profile(self):
        self.put(
            [
                {
                    "client_id": "s1",
                    "started_at": self.now - 1000,
                    "last_seen_at": self.now,
                    "seconds": 5,
                }
            ]
        )
        other = User.objects.create(username="00000000-0000-0000-0000-00000000000a")
        UserProfile.objects.create(
            user=other, supabase_uid=other.username, email="o@example.com"
        )
        c2 = APIClient()
        c2.force_authenticate(other)
        c2.put(
            "/api/reading/sessions/",
            {
                "sessions": [
                    {
                        "client_id": "s1",
                        "started_at": self.now,
                        "last_seen_at": self.now,
                        "seconds": 99,
                    }
                ]
            },
            format="json",
        )
        # Same client_id, different profile → two distinct rows, unaffected.
        self.assertEqual(ReadingSession.objects.filter(client_id="s1").count(), 2)
        self.assertEqual(
            ReadingSession.objects.get(profile=self.profile, client_id="s1").seconds, 5
        )
