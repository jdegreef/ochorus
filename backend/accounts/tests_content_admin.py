"""The Content admin role — the tier between a language admin and the super admin.

It reaches email (including sending), readers' emails in the clear, document
import, the full Admin Manual and queuing translations, and adds/edits
languages; it does NOT reach Team & access, deleting a reader, or taking a
language live. A language admin, one tier below, reaches none of the new levers.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from accounts.admin_roles import PRESETS, ROLE_INFO, apply_grant
from accounts.models import AdminCapability as C
from accounts.models import AdminVerb as V
from accounts.permissions import has_capability, may_queue_translations, reveals_pii

User = get_user_model()
VERIFIED = {"email_verified": True}
CONTENT = "maika@example.com"
LANG = "lang@example.com"


class ContentAdminRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        apply_grant(CONTENT, role="content_admin")
        apply_grant(LANG, role="language_admin")
        self.content = User.objects.create(username="c-uid", email=CONTENT)
        self.lang = User.objects.create(username="l-uid", email=LANG)

    def _req(self, user):
        request = RequestFactory().get("/")
        request.user = user
        request.auth = VERIFIED
        return request

    def _as(self, user):
        self.client.force_authenticate(user=user, token=VERIFIED)

    def test_preset_is_labelled_and_sits_above_language_admin(self):
        self.assertIn("content_admin", ROLE_INFO)
        content, lang = dict(PRESETS["content_admin"]), dict(PRESETS["language_admin"])
        rank = {V.VIEW: 0, V.SUGGEST: 1, V.ACT: 2, V.APPROVE: 3}
        for cap, verb in lang.items():
            self.assertGreaterEqual(rank[content[cap]], rank[verb], cap)
        # The founder's own levers stay out of the bundle.
        self.assertEqual(content[C.LANGUAGE_ADMIN], V.ACT)

    def test_new_levers_reach_content_admin_but_not_language_admin(self):
        c, lang = self._req(self.content), self._req(self.lang)
        self.assertTrue(reveals_pii(c))
        self.assertFalse(reveals_pii(lang))
        self.assertTrue(may_queue_translations(c))
        self.assertFalse(may_queue_translations(lang))
        for cap, verb in [
            (C.EMAIL, V.APPROVE),
            (C.PUBLISH, V.APPROVE),
            (C.LANGUAGE_ADMIN, V.ACT),
        ]:
            self.assertTrue(has_capability(c, cap, verb), cap)
            self.assertFalse(has_capability(lang, cap, verb), cap)
        self.assertFalse(has_capability(c, C.LANGUAGE_ADMIN, V.APPROVE))

    def test_endpoints_open_to_content_admin(self):
        self._as(self.content)
        for url in (
            "/api/admin/broadcasts/",
            "/api/admin/import/languages/",
            "/api/admin/users/directory/",
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        # The manual's PDF may not be built in a test checkout — anything but a
        # permission refusal means the gate let her through.
        self.assertNotIn(self.client.get("/api/admin/manual/").status_code, (401, 403))

    def test_endpoints_closed_to_language_admin(self):
        self._as(self.lang)
        for url in (
            "/api/admin/broadcasts/",
            "/api/admin/import/languages/",
            "/api/admin/manual/",
        ):
            self.assertIn(self.client.get(url).status_code, (401, 403), url)

    def test_owner_levers_stay_with_the_super_admin(self):
        self._as(self.content)
        self.assertIn(self.client.get("/api/admin/team/").status_code, (401, 403))
        self.assertIn(
            self.client.post(
                "/api/admin/team/",
                {"email": "x@y.com", "role": "content_admin"},
                format="json",
            ).status_code,
            (401, 403),
        )
        uid = "11111111-1111-1111-1111-111111111111"
        self.assertIn(
            self.client.delete(f"/api/admin/users/{uid}/account/").status_code,
            (401, 403),
        )
