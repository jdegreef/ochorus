"""The searchable user directory (/api/admin/users/directory/)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import ReadingProgress, ReadingSession

User = get_user_model()


@override_settings(DEBUG=True)
class AdminUserDirectoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()

        def make(username, name, email, joined_days_ago, seen=None, works=0, seconds=0):
            u = User.objects.create(username=username, email=email)
            p = UserProfile.objects.create(
                user=u,
                supabase_uid=uuid.uuid4(),
                email=email,
                display_name=name,
                providers="email",
                last_seen_at=seen,
            )
            # created_at is auto_now_add; nudge it for deterministic ordering.
            UserProfile.objects.filter(pk=p.pk).update(
                created_at=now - timedelta(days=joined_days_ago)
            )
            for i in range(works):
                ReadingProgress.objects.create(
                    profile=p, kind="book", book_slug=f"b{i}", chapter_order=1
                )
            if seconds:
                ReadingSession.objects.create(
                    profile=p,
                    client_id="c",
                    started_at=now,
                    last_seen_at=now,
                    seconds=seconds,
                )
            return p

        self.alice = make("u1", "Alice", "alice@example.com", 1, seen=now, works=3, seconds=600)
        self.bob = make("u2", "Bob", "bob@example.com", 10, seen=now - timedelta(days=5), works=1, seconds=120)
        self.carol = make("u3", "Carol", "carol@test.org", 30, seen=None, works=0, seconds=0)

    def get(self, **params):
        return self.client.get("/api/admin/users/directory/", params)

    def test_requires_admin(self):
        res = self.client.get(
            "/api/admin/users/directory/", REMOTE_ADDR="203.0.113.9"
        )
        self.assertIn(res.status_code, (401, 403))

    def test_lists_all_with_rollups(self):
        d = self.get().json()
        self.assertEqual(d["total"], 3)
        self.assertEqual(d["pages"], 1)
        by_name = {r["display_name"]: r for r in d["results"]}
        self.assertEqual(by_name["Alice"]["works"], 3)
        self.assertEqual(by_name["Alice"]["reading_seconds"], 600)
        self.assertEqual(by_name["Carol"]["works"], 0)
        self.assertEqual(by_name["Carol"]["reading_seconds"], 0)
        # Each row carries the uid to link on.
        self.assertEqual(by_name["Alice"]["uid"], str(self.alice.supabase_uid))

    def test_rollups_do_not_multiply(self):
        # Alice has 3 progress rows AND a session; a naive double-join would
        # inflate both. Subqueries keep them exact.
        alice = next(r for r in self.get().json()["results"] if r["display_name"] == "Alice")
        self.assertEqual(alice["works"], 3)
        self.assertEqual(alice["reading_seconds"], 600)

    def test_search_by_email_and_name(self):
        self.assertEqual(self.get(q="test.org").json()["total"], 1)  # Carol's email
        self.assertEqual(self.get(q="ali").json()["results"][0]["display_name"], "Alice")

    def test_sort_recent_default(self):
        names = [r["display_name"] for r in self.get().json()["results"]]
        self.assertEqual(names, ["Alice", "Bob", "Carol"])  # newest first

    def test_sort_active(self):
        names = [r["display_name"] for r in self.get(sort="active").json()["results"]]
        self.assertEqual(names[:2], ["Alice", "Bob"])  # by reading_seconds desc

    def test_sort_seen_puts_never_seen_last(self):
        names = [r["display_name"] for r in self.get(sort="seen").json()["results"]]
        self.assertEqual(names[-1], "Carol")  # last_seen_at is null → bottom

    def test_pagination_clamps(self):
        d = self.get(page=99).json()
        self.assertEqual(d["page"], 1)  # clamped to the only page
        d2 = self.get(page="nonsense").json()
        self.assertEqual(d2["page"], 1)

    def test_bad_sort_falls_back(self):
        self.assertEqual(self.get(sort="whatever").json()["sort"], "recent")

    def test_csv_export(self):
        res = self.get(fmt="csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("attachment", res["Content-Disposition"])
        self.assertIn(".csv", res["Content-Disposition"])
        body = res.content.decode()
        lines = [line for line in body.splitlines() if line]
        # Header + all three users (no pagination on export).
        self.assertEqual(lines[0], "name,email,providers,language,joined,last_seen,works,reading_seconds")
        self.assertEqual(len(lines), 4)
        # Email is in the clear in the export (unlike the masked UI).
        self.assertIn("alice@example.com", body)
        self.assertIn("600", body)  # Alice's reading_seconds

    def test_csv_respects_search(self):
        body = self.get(fmt="csv", q="test.org").content.decode()
        lines = [line for line in body.splitlines() if line]
        self.assertEqual(len(lines), 2)  # header + Carol only (carol@test.org)
        self.assertIn("carol@test.org", body)
        self.assertNotIn("alice@example.com", body)
