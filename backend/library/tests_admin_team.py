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


class AdminTeamRoleLifecycleTests(TestCase):
    """Changing a role replaces it, and a grant made before its preset grew is
    reported as out of date (with the languages to re-apply it on)."""

    def setUp(self):
        self.client = APIClient()

    def _member(self, email):
        members = self.client.get("/api/admin/team/").data["members"]
        return next(m for m in members if m["email"] == email)

    @override_settings(DEBUG=True)
    def test_changing_role_drops_the_old_roles_extra_rows(self):
        self.client.post(
            "/api/admin/team/", {"email": "a@b.com", "role": "language_admin", "languages": ["lg"]}, format="json"
        )
        AdminGrant.objects.create(email="a@b.com", capability=AdminCapability.USERS, verb=AdminVerb.VIEW)
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "reviewer", "languages": ["es"]}, format="json")
        caps = set(AdminGrant.objects.filter(email="a@b.com").values_list("capability", flat=True))
        self.assertNotIn(AdminCapability.PUBLISH, caps)
        self.assertNotIn(AdminCapability.FEEDBACK, caps)
        self.assertIn(AdminCapability.USERS, caps)  # a single-capability grant survives
        self.assertEqual(self._member("a@b.com")["roles"], ["reviewer"])

    @override_settings(DEBUG=True)
    def test_a_grant_older_than_its_preset_is_reported_and_regrant_fixes_it(self):
        self.client.post(
            "/api/admin/team/", {"email": "a@b.com", "role": "language_admin", "languages": ["en", "lg"]}, format="json"
        )
        self.assertEqual(self._member("a@b.com")["outdated"], [])
        AdminGrant.objects.filter(
            email="a@b.com", capability__in=[AdminCapability.FEEDBACK, AdminCapability.LANGUAGE_ADMIN]
        ).delete()
        self.assertEqual(
            self._member("a@b.com")["outdated"],
            [{"role": "language_admin", "missing": ["feedback", "language_admin"], "languages": ["en", "lg"]}],
        )
        self.client.post(
            "/api/admin/team/", {"email": "a@b.com", "role": "language_admin", "languages": ["en", "lg"]}, format="json"
        )
        self.assertEqual(self._member("a@b.com")["outdated"], [])

    @override_settings(DEBUG=True)
    def test_mixed_languages_give_no_single_regrant(self):
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "reviewer", "languages": ["es"]}, format="json")
        AdminGrant.objects.filter(email="a@b.com", capability=AdminCapability.AUDIT).update(languages="fr")
        AdminGrant.objects.filter(email="a@b.com", capability=AdminCapability.REVIEW).delete()
        self.assertEqual(self._member("a@b.com")["outdated"][0]["languages"], None)

    @override_settings(DEBUG=True)
    def test_restore_puts_back_the_exact_rows(self):
        # Mixed languages, a stale role, two roles and a single grant: re-applying
        # roles would change every one of these; a restore must not.
        scopes = [
            {"capability": "audit", "verb": "view", "languages": ["*"], "role": "reviewer"},
            {"capability": "review", "verb": "act", "languages": ["es"], "role": "reviewer"},
            {"capability": "publish", "verb": "act", "languages": ["lg"], "role": "language_admin"},
            {"capability": "users", "verb": "view", "languages": ["*"], "role": ""},
        ]
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "contributor", "languages": ["en"]}, format="json")
        res = self.client.post("/api/admin/team/", {"email": "a@b.com", "restore": scopes}, format="json")
        self.assertEqual(res.status_code, 201)
        key = lambda s: s["capability"]  # noqa: E731
        self.assertEqual(res.data["scopes"], sorted(scopes, key=key))

    @override_settings(DEBUG=True)
    def test_bad_restore_changes_nothing(self):
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "reviewer", "languages": ["es"]}, format="json")
        before = list(AdminGrant.objects.filter(email="a@b.com").values_list("capability", "verb"))
        for bad in ([], "x", [{"capability": "bogus", "verb": "act", "languages": ["es"], "role": ""}]):
            res = self.client.post("/api/admin/team/", {"email": "a@b.com", "restore": bad}, format="json")
            self.assertEqual(res.status_code, 400)
        self.assertEqual(list(AdminGrant.objects.filter(email="a@b.com").values_list("capability", "verb")), before)

    @override_settings(DEBUG=True)
    def test_a_role_change_records_what_it_removed(self):
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "language_admin", "languages": ["lg"]}, format="json")
        res = self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "reviewer", "languages": ["lg"]}, format="json")
        self.assertIn("publish", res.data["removed"])
        self.assertIn("publish", AdminAction.objects.latest("id").detail["removed"])

    @override_settings(DEBUG=True)
    def test_a_single_grant_over_a_role_capability_is_not_drift(self):
        self.client.post("/api/admin/team/", {"email": "a@b.com", "role": "reviewer", "languages": ["es"]}, format="json")
        self.client.post("/api/admin/team/", {"email": "a@b.com", "capability": "review", "verb": "approve"}, format="json")
        self.assertEqual(self._member("a@b.com")["outdated"], [])


class AdminRolesTests(TestCase):
    """/api/admin/roles/ — the access model the Help & roles page renders."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_serves_the_presets_and_labels(self):
        from accounts.admin_roles import PRESETS, ROLE_GRANTS, ROLE_INFO

        res = self.client.get("/api/admin/roles/")
        self.assertEqual(res.status_code, 200)
        roles = {r["code"]: r for r in res.data["roles"]}
        # The presets verbatim, so the help page can't drift from them…
        for name, pairs in PRESETS.items():
            self.assertEqual(roles[name]["grants"], dict(pairs))
        # …every preset has a label and summary, and the super admin holds all.
        self.assertEqual(set(ROLE_INFO), {*PRESETS, "super_admin"})
        self.assertEqual(set(ROLE_INFO), set(ROLE_GRANTS))
        self.assertEqual(set(roles["super_admin"]["grants"]), set(AdminCapability.values))
        self.assertEqual({c["code"] for c in res.data["capabilities"]}, set(AdminCapability.values))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
    def test_any_grant_can_read_it_and_outsiders_cannot(self):
        user = User.objects.create(
            username="77777777-7777-7777-7777-777777777777", email="c@ochorus.com"
        )
        self.client.force_authenticate(user=user, token=VERIFIED)
        self.assertIn(self.client.get("/api/admin/roles/").status_code, (401, 403))

        # A single raw grant that isn't reporting still opens Help, so it must
        # open the model the page renders.
        AdminGrant.objects.create(
            email="c@ochorus.com", capability=AdminCapability.FEEDBACK, verb=AdminVerb.ACT
        )
        self.assertEqual(self.client.get("/api/admin/roles/").status_code, 200)
