"""The admin Activity endpoint: newest-first paging, per-target history, auth.

`AdminActivityView` is the "who changed what" log. These cover the two ways it
reaches past its window — a `before` id cursor and a `target` filter — plus the
shape the frontend reads and the admin gate.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .admin_views.activity import AdminActivityView
from .models import AdminAction

A = AdminAction.Action


class AdminActivityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _make(self, n, target="language:sw"):
        """Create n rows, ascending id; detail.n records creation order."""
        for i in range(n):
            AdminAction.objects.create(
                action=A.CONTENT_PUBLISH,
                actor="admin@example.com",
                target=target,
                detail={"n": i},
            )

    @override_settings(DEBUG=True)
    def test_newest_first_and_row_shape(self):
        self._make(3)
        res = self.client.get("/api/admin/activity/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total"], 3)
        self.assertEqual(res.data["limit"], 100)
        self.assertIsNone(res.data["next_cursor"])  # one page holds them all

        actions = res.data["actions"]
        self.assertEqual([a["detail"]["n"] for a in actions], [2, 1, 0])  # newest first
        first = actions[0]
        self.assertEqual(first["action"], A.CONTENT_PUBLISH.value)
        # The label rides with the choice, so it can't drift from the value.
        self.assertEqual(first["label"], A.CONTENT_PUBLISH.label)
        self.assertEqual(first["actor"], "admin@example.com")
        self.assertEqual(first["target"], "language:sw")
        self.assertIn("at", first)

    @override_settings(DEBUG=True)
    def test_cursor_walks_every_row_once_newest_first(self):
        self._make(5)
        collected: list[int] = []
        cursor = None
        with patch.object(AdminActivityView, "LIMIT", 2):
            for _ in range(10):  # safety bound; 5 rows / page 2 => 3 pages
                url = "/api/admin/activity/"
                if cursor is not None:
                    url += f"?before={cursor}"
                res = self.client.get(url)
                collected += [a["detail"]["n"] for a in res.data["actions"]]
                cursor = res.data["next_cursor"]
                if cursor is None:
                    break
        # Every row once, newest first, and the cursor terminated on its own.
        self.assertEqual(collected, [4, 3, 2, 1, 0])

    @override_settings(DEBUG=True)
    def test_next_cursor_present_only_while_more_remain(self):
        self._make(4)
        with patch.object(AdminActivityView, "LIMIT", 2):
            page1 = self.client.get("/api/admin/activity/").data
            self.assertIsNotNone(page1["next_cursor"])  # 2 of 4 shown
            page2 = self.client.get(
                f"/api/admin/activity/?before={page1['next_cursor']}"
            ).data
            self.assertIsNone(page2["next_cursor"])  # last two, nothing older

    @override_settings(DEBUG=True)
    def test_cursor_page_omits_the_total_count(self):
        self._make(4)
        with patch.object(AdminActivityView, "LIMIT", 2):
            first = self.client.get("/api/admin/activity/").data
            self.assertEqual(first["total"], 4)  # the first page carries it
            older = self.client.get(f"/api/admin/activity/?before={first['next_cursor']}").data
            # A cursor page skips the count — the client already has the total.
            self.assertIsNone(older["total"])

    @override_settings(DEBUG=True)
    def test_target_scopes_rows_and_total(self):
        self._make(2, target="language:sw")
        self._make(3, target="book:humility:es")
        res = self.client.get("/api/admin/activity/?target=language:sw")
        self.assertEqual(res.data["total"], 2)  # not the table's 5
        self.assertTrue(all(a["target"] == "language:sw" for a in res.data["actions"]))

    @override_settings(DEBUG=True)
    def test_target_history_stays_in_scope_across_pages(self):
        self._make(3, target="language:sw")
        self._make(3, target="book:humility:es")  # interleaved by id, must not leak
        collected: list[dict] = []
        cursor = None
        with patch.object(AdminActivityView, "LIMIT", 2):
            for _ in range(10):
                url = "/api/admin/activity/?target=language:sw"
                if cursor is not None:
                    url += f"&before={cursor}"
                res = self.client.get(url).data
                collected += res["actions"]
                cursor = res["next_cursor"]
                if cursor is None:
                    break
        # Every page kept the target filter — the other target's rows never leak
        # in, even though their ids sit above this target's.
        self.assertEqual(len(collected), 3)
        self.assertTrue(all(a["target"] == "language:sw" for a in collected))

    @override_settings(DEBUG=True)
    def test_bad_cursor_returns_newest_page_not_error(self):
        self._make(3)
        res = self.client.get("/api/admin/activity/?before=not-an-int")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["actions"]), 3)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_forbidden_without_admin_email(self):
        res = self.client.get("/api/admin/activity/")
        self.assertIn(res.status_code, (401, 403))
