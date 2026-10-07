"""Deleting a reader's account from the admin (/api/admin/users/<uid>/account/).

The Supabase call is mocked at ``requests.delete``: the endpoint must free the
sign-in before it touches local rows, and must leave everything in place when
Supabase fails. Auth is the loopback DEBUG bypass, as the other admin tests use.
"""

from __future__ import annotations

import uuid
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserProfile
from reading.models import Favorite

from .models import AdminAction

SUPABASE = {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "srk"}


def _resp(status, body=None):
    return mock.Mock(
        status_code=status, ok=200 <= status < 300, json=mock.Mock(return_value=body or {})
    )


@override_settings(DEBUG=True, **SUPABASE)
class AdminUserDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(username="u1", email="test1@example.com")
        self.uid = uuid.uuid4()
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.uid, email="test1@example.com"
        )
        Favorite.objects.create(profile=self.profile, kind="author", slug="andrew-murray")
        self.url = f"/api/admin/users/{self.uid}/account/"

    def _rows(self):
        return [
            UserProfile.objects.filter(supabase_uid=self.uid).exists(),
            get_user_model().objects.filter(pk=self.user.pk).exists(),
            Favorite.objects.filter(slug="andrew-murray").exists(),
        ]

    def _gone(self):
        return not any(self._rows())

    def _intact(self):
        return all(self._rows())

    @mock.patch("accounts.supabase_admin.requests.request", return_value=_resp(200))
    def test_deletes_supabase_user_then_local_rows(self, delete):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["auth_deleted"])
        method, url = delete.call_args.args
        self.assertEqual(method, "delete")
        self.assertTrue(url.endswith(f"/auth/v1/admin/users/{self.uid}"))
        self.assertTrue(self._gone())
        entry = AdminAction.objects.get(action=AdminAction.Action.USER_DELETE)
        self.assertEqual(entry.target, f"user:{self.uid}")
        self.assertNotIn("test1@example.com", str(entry.detail))  # masked

    @mock.patch(
        "accounts.supabase_admin.requests.request",
        return_value=_resp(404, {"code": 404, "error_code": "user_not_found"}),
    )
    def test_already_gone_in_supabase_still_deletes_locally(self, _):
        self.assertEqual(self.client.delete(self.url).status_code, 200)
        self.assertTrue(self._gone())

    @mock.patch("accounts.supabase_admin.requests.request", return_value=_resp(404))
    def test_a_bare_404_is_not_taken_as_gone(self, _):
        # A wrong SUPABASE_URL or a gateway 404s too; the sign-in may survive.
        self.assertEqual(self.client.delete(self.url).status_code, 502)
        self.assertTrue(self._intact())

    @mock.patch("accounts.supabase_admin.requests.request", return_value=_resp(500))
    def test_supabase_failure_deletes_nothing(self, _):
        self.assertEqual(self.client.delete(self.url).status_code, 502)
        self.assertTrue(self._intact())
        self.assertFalse(AdminAction.objects.exists())

    @mock.patch(
        "accounts.supabase_admin.requests.request",
        side_effect=requests.ConnectionError("down"),
    )
    def test_supabase_unreachable_deletes_nothing(self, _):
        self.assertEqual(self.client.delete(self.url).status_code, 502)
        self.assertTrue(self._intact())

    @override_settings(SUPABASE_URL="", SUPABASE_SERVICE_ROLE_KEY="")
    def test_without_supabase_deletes_local_rows_only(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["auth_deleted"])
        self.assertTrue(self._gone())

    def test_unknown_uid_is_404(self):
        self.assertEqual(self.client.delete(f"/api/admin/users/{uuid.uuid4()}/account/").status_code, 404)

    @mock.patch("accounts.supabase_admin.requests.request")
    def test_refuses_to_delete_own_account(self, delete):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(self.url).status_code, 400)
        delete.assert_not_called()
        self.assertTrue(self._intact())

    @override_settings(ADMIN_EMAILS={"test1@example.com"})
    @mock.patch("accounts.supabase_admin.requests.request")
    def test_refuses_to_delete_a_super_admin(self, delete):
        self.assertEqual(self.client.delete(self.url).status_code, 400)
        delete.assert_not_called()
        self.assertTrue(self._intact())

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    @mock.patch("accounts.supabase_admin.requests.request")
    def test_non_admin_is_refused(self, delete):
        other = get_user_model().objects.create(username="u2", email="someone@example.com")
        self.client.force_authenticate(other)
        self.assertIn(self.client.delete(self.url).status_code, (401, 403))
        delete.assert_not_called()
