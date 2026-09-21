"""Tests for reader feedback: the signed-in submit endpoint, the capability-gated
admin queue, and audited triage.

Enforcement runs with DEBUG off (no loopback bypass) and a granted account that
is NOT on ADMIN_EMAILS — the point of the scoped capability.
"""

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability as C
from accounts.models import AdminGrant, UserProfile
from accounts.models import AdminVerb as V
from library.models import AdminAction

from .models import Feedback, FeedbackStatus

User = get_user_model()
VERIFIED = {"email_verified": True}


def _profile(email="reader@example.com") -> UserProfile:
    uid = uuid.uuid4()
    user = User.objects.create(username=str(uid), email=email)
    return UserProfile.objects.create(
        user=user, supabase_uid=uid, email=email, display_name="A Reader"
    )


def _reader(email="reader@example.com"):
    return _profile(email).user


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class SubmitTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anonymous_is_denied(self):
        resp = self.client.post("/api/feedback/", {"body": "This is my feedback."}, format="json")
        self.assertIn(resp.status_code, (401, 403))
        self.assertEqual(Feedback.objects.count(), 0)

    def test_signed_in_reader_files_with_context(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        resp = self.client.post(
            "/api/feedback/",
            {
                "body": "Chapter 3 mistranslates the verse.",
                "category": "language",
                "page_url": "https://ochorus.com/lg/books/the-secret-of-guidance/",
                "content_kind": "book",
                "content_slug": "the-secret-of-guidance",
                "content_language": "lg",
                "chapter_ref": "3",
                "ui_locale": "lg",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        item = Feedback.objects.get()
        self.assertEqual(item.category, "language")
        self.assertEqual(item.content_slug, "the-secret-of-guidance")
        self.assertEqual(item.content_language, "lg")
        self.assertEqual(item.status, FeedbackStatus.NEW)
        self.assertEqual(item.submitter_role, "")  # ordinary reader

    def test_short_body_is_rejected(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        resp = self.client.post("/api/feedback/", {"body": "no"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_unknown_category_falls_back_to_other(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        resp = self.client.post(
            "/api/feedback/", {"body": "A perfectly good note.", "category": "bogus"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Feedback.objects.get().category, "other")

    def test_language_admin_submitter_is_badged(self):
        AdminGrant.objects.create(
            email="la@ochorus.com", capability=C.REVIEW, verb=V.APPROVE,
            languages="en,lg", role_label="language_admin",
        )
        self.client.force_authenticate(user=_reader("la@ochorus.com"), token=VERIFIED)
        resp = self.client.post("/api/feedback/", {"body": "A trusted note here."}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Feedback.objects.get().submitter_role, "language_admin")

    def test_super_admin_submitter_is_badged(self):
        self.client.force_authenticate(user=_reader("super@ochorus.com"), token=VERIFIED)
        resp = self.client.post("/api/feedback/", {"body": "Founder feedback here."}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Feedback.objects.get().submitter_role, "super_admin")


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class AdminQueueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # A submission to triage.
        self.item = Feedback.objects.create(
            submitter=_profile("r@example.com"),
            submitter_email="r@example.com",
            category="content",
            body="Something to look at.",
        )
        self.super = User.objects.create(
            username="99999999-9999-9999-9999-999999999999", email="super@ochorus.com"
        )
        self.helper = User.objects.create(username="uid-helper", email="helper@ochorus.com")

    def test_queue_requires_the_feedback_capability(self):
        self.client.force_authenticate(user=self.helper, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/feedback/").status_code, 403)

    def test_super_admin_sees_the_queue_with_counts(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        resp = self.client.get("/api/admin/feedback/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["items"]), 1)
        self.assertEqual(resp.data["counts"]["new"], 1)

    def test_granted_admin_can_view_but_view_cannot_triage(self):
        AdminGrant.objects.create(email="helper@ochorus.com", capability=C.FEEDBACK, verb=V.VIEW)
        self.client.force_authenticate(user=self.helper, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/feedback/").status_code, 200)
        # VIEW does not satisfy the ACT the triage POST requires.
        resp = self.client.post(
            f"/api/admin/feedback/{self.item.pk}/", {"status": "planned"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_triage_changes_status_and_is_audited(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        resp = self.client.post(
            f"/api/admin/feedback/{self.item.pk}/",
            {"status": "planned", "admin_note": "good idea"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "planned")
        self.assertEqual(self.item.admin_note, "good idea")
        self.assertTrue(
            AdminAction.objects.filter(action=AdminAction.Action.FEEDBACK_TRIAGE).exists()
        )

    def test_triage_rejects_unknown_status(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        resp = self.client.post(
            f"/api/admin/feedback/{self.item.pk}/", {"status": "bogus"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_triage_unknown_item_is_404(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        resp = self.client.post("/api/admin/feedback/999999/", {"status": "done"}, format="json")
        self.assertEqual(resp.status_code, 404)
