"""'My work' (/api/admin/my-work/): what is waiting on the person looking."""

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.admin_roles import apply_grant
from accounts.models import UserProfile
from emails.models import Broadcast, BroadcastStatus
from feedback.models import Feedback

from .models import AdminAction, ReviewOutcome

User = get_user_model()
VERIFIED = {"email_verified": True}
MAIKA = "maika@example.com"
REV = "rev@example.com"


class MyWorkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        apply_grant(MAIKA, role="content_admin")
        apply_grant(REV, role="reviewer", languages="es")
        self.maika = User.objects.create(username="m", email=MAIKA)
        self.rev = User.objects.create(username="r", email=REV)
        reader = UserProfile.objects.create(
            user=User.objects.create(username="reader"), supabase_uid=uuid.uuid4()
        )
        Feedback.objects.create(
            submitter=reader,
            category="language",
            body="Typo in ch 3",
            assignee_email=MAIKA,
        )
        Feedback.objects.create(
            submitter=reader,
            category="language",
            body="Done one",
            assignee_email=MAIKA,
            status="done",
        )
        Feedback.objects.create(submitter=reader, category="language", body="Not mine")
        ReviewOutcome.objects.create(
            kind="book",
            slug="humility",
            language="es",
            outcome="approved",
            reviewer=REV,
        )
        ReviewOutcome.objects.create(
            kind="book",
            slug="prayer",
            language="es",
            outcome="approved",
            reviewer=REV,
            confirmed_by=MAIKA,
            confirmed_at=timezone.now(),
        )
        draft = Broadcast.objects.create(
            name="Advent letter", status=BroadcastStatus.DRAFT
        )
        sent = Broadcast.objects.create(name="Old letter", status=BroadcastStatus.SENT)
        for b in (draft, sent):
            AdminAction.objects.create(
                action=AdminAction.Action.BROADCAST_CREATE,
                actor=MAIKA,
                target=f"broadcast:{b.pk}",
            )

    def _sections(self, user):
        self.client.force_authenticate(user=user, token=VERIFIED)
        res = self.client.get("/api/admin/my-work/")
        self.assertEqual(res.status_code, 200)
        return {
            s["key"]: [i["label"] for i in s["items"]] for s in res.data["sections"]
        }

    def test_a_content_admin_sees_their_feedback_confirmations_and_emails(self):
        s = self._sections(self.maika)
        self.assertEqual(s["feedback"], ["Typo in ch 3"])
        self.assertEqual(s["confirm"], ["humility (es): approved"])
        self.assertEqual(s["emails"], ["Advent letter"])
        self.assertNotIn("proposed", s)  # Maika proposed nothing

    def test_a_reviewer_sees_their_own_proposal_waiting_and_nothing_to_confirm(self):
        s = self._sections(self.rev)
        self.assertEqual(s["proposed"], ["humility (es): approved"])
        self.assertNotIn("confirm", s)  # review:act can't confirm
        self.assertNotIn("emails", s)  # no email grant
        self.assertNotIn("feedback", s)  # no feedback grant

    def test_needs_some_admin_access(self):
        outsider = User.objects.create(username="o", email="o@example.com")
        self.client.force_authenticate(user=outsider, token=VERIFIED)
        self.assertIn(self.client.get("/api/admin/my-work/").status_code, (401, 403))
