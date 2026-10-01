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

    # --- filters and the summary: over the whole log, not the loaded page ---

    def _row(self, action, target="book:humility:es", actor="admin@example.com", **detail):
        return AdminAction.objects.create(action=action, actor=actor, target=target, detail=detail)

    @override_settings(DEBUG=True)
    def test_search_reaches_past_the_first_page(self):
        self._row(A.TRANSLATION_JOB, target="book:morning-and-evening:de", author="Spurgeon")
        self._make(5)  # newer rows bury it
        with patch.object(AdminActivityView, "LIMIT", 2):
            res = self.client.get("/api/admin/activity/?q=spurgeon").data
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["actions"][0]["target"], "book:morning-and-evening:de")

    @override_settings(DEBUG=True)
    def test_search_matches_target_label_and_detail(self):
        self._row(A.LANGUAGE_GO_LIVE, target="language:am")
        self._row(A.TRANSLATION_JOB, issue_url="https://github.com/o/r/issues/4821")

        def get(q):
            return self.client.get("/api/admin/activity/", {"q": q}).data["total"]

        self.assertEqual(get("language:am"), 1)
        self.assertEqual(get("taken live"), 1)  # the label, not the stored value
        self.assertEqual(get("4821"), 1)  # inside detail

    @override_settings(DEBUG=True)
    def test_category_filters_and_pages_within_the_category(self):
        for _ in range(3):
            self._row(A.REVIEW_DECIDE)
        self._row(A.ROLE_GRANT, target="user:x@example.com")
        self._make(4)
        with patch.object(AdminActivityView, "LIMIT", 2):
            p1 = self.client.get("/api/admin/activity/?category=review").data
            p2 = self.client.get(f"/api/admin/activity/?category=review&before={p1['next_cursor']}").data
        self.assertEqual(p1["total"], 3)
        self.assertEqual(len(p1["actions"]) + len(p2["actions"]), 3)
        self.assertTrue(all(a["action"] == A.REVIEW_DECIDE for a in p1["actions"] + p2["actions"]))
        access = self.client.get("/api/admin/activity/?category=access").data
        self.assertEqual(access["total"], 1)  # role.* files as access

    @override_settings(DEBUG=True)
    def test_actor_filter(self):
        self._row(A.REVIEW_DECIDE, actor="a@example.com")
        self._row(A.REVIEW_DECIDE, actor="b@example.com")
        res = self.client.get("/api/admin/activity/?actor=b@example.com").data
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["actions"][0]["actor"], "b@example.com")

    @override_settings(DEBUG=True)
    def test_summary_counts_the_whole_log(self):
        for _ in range(3):
            self._row(A.TRANSLATION_JOB)
        self._row(A.LANGUAGE_GO_LIVE, target="language:sw")
        self._row(A.REVIEW_DECIDE, actor="b@example.com")
        with patch.object(AdminActivityView, "LIMIT", 1):
            s = self.client.get("/api/admin/activity/").data["summary"]
        self.assertEqual(s["all"], 5)
        self.assertEqual(s["by_category"]["translation"], 3)
        self.assertEqual(s["by_category"]["language"], 1)
        self.assertEqual(s["by_category"]["review"], 1)
        self.assertEqual(s["today"], 5)
        self.assertEqual(s["today_reader_facing"], 1)
        self.assertEqual(s["week"], 5)
        self.assertEqual(s["actors"], [{"actor": "admin@example.com", "count": 4}, {"actor": "b@example.com", "count": 1}])
        self.assertEqual(s["last_go_live"]["target"], "language:sw")
        self.assertIsNone(s["last_publish"])

    @override_settings(DEBUG=True)
    def test_chip_counts_follow_search_but_not_category(self):
        self._row(A.TRANSLATION_JOB, target="book:grace:es")
        self._row(A.REVIEW_DECIDE, target="book:grace:es")
        self._row(A.REVIEW_DECIDE, target="book:holiness:es")
        s = self.client.get("/api/admin/activity/?q=grace&category=review").data["summary"]
        # Each chip says what clicking it would show for "grace".
        self.assertEqual(s["by_category"]["translation"], 1)
        self.assertEqual(s["by_category"]["review"], 1)

    @override_settings(DEBUG=True)
    def test_today_uses_the_callers_midnight(self):
        from datetime import timedelta

        from django.utils import timezone

        row = self._row(A.TRANSLATION_JOB)
        AdminAction.objects.filter(pk=row.pk).update(at=timezone.now() - timedelta(hours=3))
        self._row(A.TRANSLATION_JOB)
        midnight = (timezone.now() - timedelta(hours=1)).isoformat()
        s = self.client.get("/api/admin/activity/", {"day_start": midnight}).data["summary"]
        self.assertEqual(s["today"], 1)

    @override_settings(DEBUG=True)
    def test_cursor_page_omits_the_summary(self):
        self._make(3)
        with patch.object(AdminActivityView, "LIMIT", 1):
            first = self.client.get("/api/admin/activity/").data
            older = self.client.get(f"/api/admin/activity/?before={first['next_cursor']}").data
        self.assertIsNotNone(first["summary"])
        self.assertIsNone(older["summary"])

    @override_settings(DEBUG=True)
    def test_export_returns_every_match_unpaged(self):
        self._make(5)
        self._row(A.REVIEW_DECIDE)
        with patch.object(AdminActivityView, "LIMIT", 2):
            res = self.client.get("/api/admin/activity/?export=1&category=content").data
        self.assertEqual(len(res["actions"]), 5)
        self.assertFalse(res["truncated"])
        with patch.object(AdminActivityView, "EXPORT_LIMIT", 3):
            res = self.client.get("/api/admin/activity/?export=1").data
        self.assertEqual(len(res["actions"]), 3)
        self.assertTrue(res["truncated"])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_forbidden_without_admin_email(self):
        res = self.client.get("/api/admin/activity/")
        self.assertIn(res.status_code, (401, 403))


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class AdminActivityMaskingTests(TestCase):
    """Every role holds reporting:view, so the log must not hand the lowest of
    them the email and role of every admin on the team."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.admin_roles import apply_grant

        User = get_user_model()
        self.client = APIClient()
        AdminAction.objects.create(
            action=A.CONTENT_PUBLISH, actor="super@ochorus.com", target="user:hannah@example.com",
        )
        apply_grant("contrib@ochorus.com", role="contributor")
        self.contrib = User.objects.create(username="uid-contrib", email="contrib@ochorus.com")
        self.super = User.objects.create(username="uid-super", email="super@ochorus.com")

    def test_non_super_sees_actor_and_user_targets_masked(self):
        self.client.force_authenticate(user=self.contrib, token={"email_verified": True})
        row = self.client.get("/api/admin/activity/").data["actions"][0]
        self.assertNotIn("super@", row["actor"])
        self.assertTrue(row["target"].startswith("user:"))
        self.assertNotIn("hannah", row["target"])

    def test_non_super_cannot_probe_a_user_target(self):
        self.client.force_authenticate(user=self.contrib, token={"email_verified": True})
        res = self.client.get("/api/admin/activity/?target=user:hannah@example.com")
        self.assertEqual(res.data["total"], 0)

    def test_super_admin_sees_the_log_in_the_clear(self):
        self.client.force_authenticate(user=self.super, token={"email_verified": True})
        row = self.client.get("/api/admin/activity/?target=user:hannah@example.com").data["actions"][0]
        self.assertEqual(row["actor"], "super@ochorus.com")
        self.assertEqual(row["target"], "user:hannah@example.com")

    def test_non_super_search_cannot_probe_masked_addresses(self):
        self.client.force_authenticate(user=self.contrib, token={"email_verified": True})
        self.assertEqual(self.client.get("/api/admin/activity/?q=hannah").data["total"], 0)
        self.assertEqual(self.client.get("/api/admin/activity/?q=super@").data["total"], 0)

    def test_non_super_actor_list_is_masked_and_filters_by_the_mask(self):
        self.client.force_authenticate(user=self.contrib, token={"email_verified": True})
        actors = self.client.get("/api/admin/activity/").data["summary"]["actors"]
        self.assertEqual(len(actors), 1)
        masked = actors[0]["actor"]
        self.assertNotIn("super@", masked)
        self.assertEqual(self.client.get("/api/admin/activity/", {"actor": masked}).data["total"], 1)
        # The raw address is not a key for this caller.
        self.assertEqual(
            self.client.get("/api/admin/activity/", {"actor": "super@ochorus.com"}).data["total"], 0
        )
