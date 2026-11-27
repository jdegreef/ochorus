"""The dashboard's "Start here" steps (/api/admin/onboarding/)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.admin_roles import apply_grant

from .models import AdminAction

User = get_user_model()
VERIFIED = {"email_verified": True}


class OnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _steps(self, email, role):
        apply_grant(email, role=role)
        user = User.objects.create(username=email, email=email)
        self.client.force_authenticate(user=user, token=VERIFIED)
        res = self.client.get("/api/admin/onboarding/")
        self.assertEqual(res.status_code, 200)
        return {s["key"]: s["done"] for s in res.data["steps"]}

    def test_steps_follow_the_role_and_tick_from_the_log(self):
        AdminAction.objects.create(
            action=AdminAction.Action.FEEDBACK_TRIAGE, actor="maika@example.com"
        )
        steps = self._steps("maika@example.com", "content_admin")
        self.assertEqual(set(steps), {"review", "feedback", "fix", "email", "audit"})
        self.assertTrue(steps["feedback"])
        self.assertFalse(steps["email"])

    def test_a_contributor_gets_only_what_they_can_do(self):
        steps = self._steps("c@example.com", "contributor")
        self.assertEqual(set(steps), {"fix"})

    def test_someone_elses_work_does_not_tick_mine(self):
        AdminAction.objects.create(
            action=AdminAction.Action.REVIEW_DECIDE, actor="james@example.com"
        )
        self.assertFalse(self._steps("lang@example.com", "language_admin")["review"])

    @override_settings(DEBUG=True)
    def test_a_super_admin_gets_no_steps(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get("/api/admin/onboarding/").data["steps"], [])
