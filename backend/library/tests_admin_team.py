"""The /admin/team access console: list, grant, revoke — super admin only.

Granting is undelegated (IsAdminEmail = the ADMIN_EMAILS allowlist), so a
capability grantee — even one with broad grants — cannot reach it.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability, AdminGrant, AdminVerb
from library.models import AdminAction

User = get_user_model()
VERIFIED = {"email_verified": True}


class AdminTeamTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_super_admin_can_list_grant_and_revoke(self):
        # GET options
        res = self.client.get("/api/admin/team/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("reviewer", res.data["roles"])
        self.assertEqual(res.data["members"], [])

        # Grant the reviewer preset scoped to Spanish.
        res = self.client.post(
            "/api/admin/team/",
            {"email": "Rev@Ochorus.com", "role": "reviewer", "languages": ["es"]},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["email"], "rev@ochorus.com")  # normalised
        review = next(s for s in res.data["scopes"] if s["capability"] == "review")
        self.assertEqual(review["verb"], AdminVerb.ACT)
        self.assertEqual(review["languages"], ["es"])
        self.assertEqual(AdminAction.objects.latest("id").action, AdminAction.Action.ROLE_GRANT)

        # It shows up as a member, then revoke removes it.
        self.assertIn("rev@ochorus.com", [m["email"] for m in self.client.get("/api/admin/team/").data["members"]])
        res = self.client.delete("/api/admin/team/?email=rev@ochorus.com")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(AdminGrant.objects.filter(email="rev@ochorus.com").exists())
        self.assertEqual(AdminAction.objects.latest("id").action, AdminAction.Action.ROLE_REVOKE)

    @override_settings(DEBUG=True)
    def test_a_single_capability_grant(self):
        res = self.client.post(
            "/api/admin/team/",
            {"email": "a@b.com", "capability": "reporting", "verb": "view"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["scopes"]), 1)

    @override_settings(DEBUG=True, ADMIN_EMAILS={"super@ochorus.com"})
    def test_cannot_grant_to_a_super_admin(self):
        res = self.client.post(
            "/api/admin/team/", {"email": "super@ochorus.com", "role": "reviewer"}, format="json"
        )
        self.assertEqual(res.status_code, 409)

    @override_settings(DEBUG=True)
    def test_bad_grant_is_rejected(self):
        res = self.client.post("/api/admin/team/", {"email": "a@b.com"}, format="json")
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True)
    def test_empty_language_selection_is_rejected_not_widened(self):
        # "Restrict, but pick nothing" must deny — never silently widen to all.
        res = self.client.post(
            "/api/admin/team/",
            {"email": "a@b.com", "role": "reviewer", "languages": []},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AdminGrant.objects.filter(email="a@b.com").exists())

    @override_settings(DEBUG=True)
    def test_unknown_capability_or_verb_is_rejected(self):
        res = self.client.post(
            "/api/admin/team/",
            {"email": "a@b.com", "capability": "bogus", "verb": "nope"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AdminGrant.objects.filter(email="a@b.com").exists())

    @override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
    def test_a_capability_grantee_cannot_manage_the_team(self):
        # A non-super user, even with a broad grant, can't reach the console —
        # granting is undelegated.
        user = User.objects.create(
            username="66666666-6666-6666-6666-666666666666", email="helper@ochorus.com"
        )
        AdminGrant.objects.create(
            email="helper@ochorus.com", capability=AdminCapability.REVIEW, verb=AdminVerb.APPROVE
        )
        self.client.force_authenticate(user=user, token=VERIFIED)
        self.assertIn(self.client.get("/api/admin/team/").status_code, (401, 403))
        self.assertIn(
            self.client.post("/api/admin/team/", {"email": "x@y.com", "role": "reviewer"}, format="json").status_code,
            (401, 403),
        )
