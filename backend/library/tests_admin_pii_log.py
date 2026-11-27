"""Privacy-sensitive reads leave a trace in the admin log.

A reader's page with their email in the clear (``user.view``) and every reader
list export (``user.export``) append an ``AdminAction`` — the only GETs the log
records. A masked view (a language admin's) isn't PII, so it records nothing.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.admin_roles import apply_grant
from accounts.models import UserProfile

from .models import AdminAction

User = get_user_model()
VERIFIED = {"email_verified": True}
CONTENT = "maika@example.com"
LANG = "lang@example.com"


class PiiReadLogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        apply_grant(CONTENT, role="content_admin")
        apply_grant(LANG, capability="users", verb="view")
        self.content = User.objects.create(username="c-uid", email=CONTENT)
        self.lang = User.objects.create(username="l-uid", email=LANG)
        reader = User.objects.create(username="r-uid", email="reader@example.com")
        self.reader = UserProfile.objects.create(
            user=reader,
            supabase_uid=uuid.uuid4(),
            email="reader@example.com",
            display_name="R",
        )

    def _as(self, user):
        self.client.force_authenticate(user=user, token=VERIFIED)

    def _rows(self, action):
        return list(AdminAction.objects.filter(action=action))

    def test_opening_a_reader_in_the_clear_is_logged_once_per_half_hour(self):
        self._as(self.content)
        url = f"/api/admin/users/{self.reader.supabase_uid}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        rows = self._rows(AdminAction.Action.USER_VIEW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].actor, CONTENT)
        self.assertEqual(rows[0].target, f"user:{self.reader.supabase_uid}")
        # Past the fold window, the next look is a new row.
        AdminAction.objects.update(at=rows[0].at - timedelta(hours=1))
        self.client.get(url)
        self.assertEqual(len(self._rows(AdminAction.Action.USER_VIEW)), 2)

    def test_a_masked_view_records_nothing(self):
        self._as(self.lang)
        res = self.client.get(f"/api/admin/users/{self.reader.supabase_uid}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.json()["profile"]["email"], "reader@example.com")
        self.assertEqual(self._rows(AdminAction.Action.USER_VIEW), [])

    def test_every_export_is_logged_with_its_shape(self):
        self._as(self.content)
        for _ in range(2):
            res = self.client.get(
                "/api/admin/users/directory/", {"fmt": "csv", "q": "R"}
            )
            self.assertEqual(res.status_code, 200)
        rows = self._rows(AdminAction.Action.USER_EXPORT)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].detail["emails"], "clear")
        self.assertEqual(rows[0].detail["rows"], 1)
        self.assertEqual(rows[0].detail["q"], "R")

    def test_a_masked_export_is_still_logged(self):
        self._as(self.lang)
        self.client.get("/api/admin/users/directory/", {"fmt": "csv"})
        (row,) = self._rows(AdminAction.Action.USER_EXPORT)
        self.assertEqual(row.detail["emails"], "masked")
        self.assertEqual(row.actor, LANG)

    def test_the_log_titles_a_reader_by_name_not_email(self):
        self._as(self.content)
        self.client.get(f"/api/admin/users/{self.reader.supabase_uid}/")
        rows = self.client.get("/api/admin/activity/").json()["actions"]
        (row,) = [r for r in rows if r["action"] == "user.view"]
        self.assertEqual(row["title"], "R")
