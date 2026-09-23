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
        self.assertEqual(item.source, "menu")  # default when unspecified

    def test_source_is_recorded(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        self.client.post(
            "/api/feedback/", {"body": "From the floating button.", "source": "fab"}, format="json"
        )
        self.assertEqual(Feedback.objects.get().source, "fab")

    def test_highlight_selection_is_recorded(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        self.client.post(
            "/api/feedback/",
            {
                "body": "This line reads stiffly.",
                "source": "highlight",
                "selected_text": "the grace of God abounding",
                "suggested_text": "God's abounding grace",
                "anchor_block": 4,
            },
            format="json",
        )
        item = Feedback.objects.get()
        self.assertEqual(item.source, "highlight")
        self.assertEqual(item.selected_text, "the grace of God abounding")
        self.assertEqual(item.suggested_text, "God's abounding grace")
        self.assertEqual(item.anchor_block, 4)

    def test_bad_anchor_block_is_dropped(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        for bad in (True, -1, "3", 1.5):
            self.client.post(
                "/api/feedback/",
                {"body": "A note with a bad anchor.", "anchor_block": bad},
                format="json",
            )
        self.assertTrue(all(f.anchor_block is None for f in Feedback.objects.all()))

    def test_unknown_source_falls_back_to_menu(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        self.client.post(
            "/api/feedback/", {"body": "No valid source here.", "source": "bogus"}, format="json"
        )
        self.assertEqual(Feedback.objects.get().source, "menu")

    def test_non_http_page_url_is_dropped(self):
        # The admin queue renders page_url as a clickable link, so a
        # javascript:/data: scheme must never be stored.
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        resp = self.client.post(
            "/api/feedback/",
            {"body": "A note with a nasty url.", "page_url": "javascript:alert(1)"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Feedback.objects.get().page_url, "")

    def test_http_page_url_is_kept(self):
        self.client.force_authenticate(user=_reader(), token=VERIFIED)
        resp = self.client.post(
            "/api/feedback/",
            {"body": "A note with a good url.", "page_url": "https://ochorus.com/books/x/"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Feedback.objects.get().page_url, "https://ochorus.com/books/x/")

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

    # --- language scoping (Phase 3) ---

    def _lang_admin(self, languages="lg", email="la@ochorus.com"):
        AdminGrant.objects.create(email=email, capability=C.FEEDBACK, verb=V.ACT, languages=languages)
        u = User.objects.create(username=f"uid-{email}", email=email)
        self.client.force_authenticate(user=u, token=VERIFIED)
        return u

    def _mk(self, lang, body="a note to look at"):
        return Feedback.objects.create(
            submitter=_profile(f"{lang or 'none'}-{uuid.uuid4()}@x.com"),
            content_language=lang,
            category="language",
            body=body,
        )

    def test_language_admin_sees_only_their_languages(self):
        self._mk("lg")
        self._mk("en")
        # self.item is language-less (content_language "").
        self._lang_admin(languages="lg")
        data = self.client.get("/api/admin/feedback/").data
        self.assertEqual({i["content_language"] for i in data["items"]}, {"lg"})

    def test_language_admin_cannot_triage_out_of_scope(self):
        en_item = self._mk("en")
        self._lang_admin(languages="lg")
        resp = self.client.post(
            f"/api/admin/feedback/{en_item.pk}/", {"status": "planned"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_super_admin_sees_all_languages_and_language_less(self):
        self._mk("lg")
        self._mk("en")
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        langs = {i["content_language"] for i in self.client.get("/api/admin/feedback/").data["items"]}
        self.assertEqual(langs, {"lg", "en", ""})

    def test_source_filter(self):
        Feedback.objects.create(
            submitter=_profile("h@x.com"), category="content", body="from a highlight", source="highlight"
        )
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        data = self.client.get("/api/admin/feedback/?source=highlight").data
        self.assertTrue(data["items"] and all(i["source"] == "highlight" for i in data["items"]))

    def test_similar_nudge_counts_same_passage(self):
        for _ in range(3):
            self._mk("lg")  # same content: language 'lg', no slug → not clustered
        a = Feedback.objects.create(
            submitter=_profile("s1@x.com"), category="content", body="one",
            content_kind="book", content_slug="humility", chapter_ref="3", content_language="lg",
        )
        Feedback.objects.create(
            submitter=_profile("s2@x.com"), category="content", body="two",
            content_kind="book", content_slug="humility", chapter_ref="3", content_language="lg",
        )
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        items = self.client.get("/api/admin/feedback/").data["items"]
        hit = next(i for i in items if i["id"] == a.id)
        self.assertEqual(hit["similar"], 1)  # one other row on humility ch.3

    def test_language_admin_preset_opens_scoped_feedback(self):
        from accounts.admin_roles import apply_grant

        apply_grant("hannah@ochorus.com", role="language_admin", languages="lg")
        u = User.objects.create(username="uid-hannah", email="hannah@ochorus.com")
        self.client.force_authenticate(user=u, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/feedback/").status_code, 200)
