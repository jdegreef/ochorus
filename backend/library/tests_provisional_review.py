"""Maker-checker on the review queue: a reviewer who holds only review:act
records a PROVISIONAL decision (no source_type flip); an approver (review:approve
or a super admin) confirms it, which flips it. Exercised with DEBUG off so the
real gate runs, and a granted non-super reviewer.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability, AdminGrant, AdminVerb
from library.models import Author, Book, Chapter, ReviewOutcome

User = get_user_model()
VERIFIED = {"email_verified": True}


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class ProvisionalReviewTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=author, slug="humility", language="es", title="Humildad",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(book=self.book, order=1, title="Uno", body_html="<p>x</p>")
        self.reviewer = User.objects.create(
            username="44444444-4444-4444-4444-444444444444", email="es-rev@ochorus.com"
        )
        AdminGrant.objects.create(
            email="es-rev@ochorus.com", capability=AdminCapability.REVIEW,
            verb=AdminVerb.ACT, languages="es", role_label="reviewer",
        )
        self.superu = User.objects.create(
            username="55555555-5555-5555-5555-555555555555", email="super@ochorus.com"
        )

    def _as(self, user):
        c = APIClient()
        c.force_authenticate(user=user, token=VERIFIED)
        return c

    def _approve(self, client):
        return client.post(
            "/api/admin/review-queue/",
            {"items": [{"kind": "book", "slug": "humility", "language": "es"}], "outcome": "approved"},
            format="json",
        )

    def test_reviewer_decision_is_provisional_and_does_not_flip(self):
        res = self._approve(self._as(self.reviewer))
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_UNREVIEWED)  # NOT flipped
        o = ReviewOutcome.objects.get(kind="book", slug="humility", language="es")
        self.assertTrue(o.is_provisional)
        self.assertEqual(o.reviewer, "es-rev@ochorus.com")
        self.assertEqual(o.confirmed_by, "")

    def test_approver_confirms_a_provisional_decision_and_flips(self):
        self._approve(self._as(self.reviewer))  # reviewer proposes
        res = self._approve(self._as(self.superu))  # super confirms
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)  # flipped
        o = ReviewOutcome.objects.get(kind="book", slug="humility", language="es")
        self.assertFalse(o.is_provisional)
        self.assertEqual(o.confirmed_by, "super@ochorus.com")
        # The original proposer is preserved — the two hands of the workflow.
        self.assertEqual(o.reviewer, "es-rev@ochorus.com")

    def test_an_approver_acting_directly_flips_immediately(self):
        res = self._approve(self._as(self.superu))
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        o = ReviewOutcome.objects.get(kind="book", slug="humility", language="es")
        self.assertFalse(o.is_provisional)
        self.assertEqual(o.confirmed_by, "super@ochorus.com")

    def _needs_work(self, client):
        return client.post(
            "/api/admin/review-queue/",
            {"items": [{"kind": "book", "slug": "humility", "language": "es"}], "outcome": "needs_work"},
            format="json",
        )

    def test_reviewer_cannot_needs_work_a_confirmed_item(self):
        self._approve(self._as(self.superu))  # confirmed → ai_reviewed
        self._needs_work(self._as(self.reviewer))  # review:act tries to reopen
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)  # unchanged
        o = ReviewOutcome.objects.get(kind="book", slug="humility", language="es")
        self.assertEqual(o.confirmed_by, "super@ochorus.com")  # attribution intact

    def test_reviewer_cannot_undo_a_confirmed_item(self):
        self._approve(self._as(self.superu))
        res = self._as(self.reviewer).delete(
            "/api/admin/review-queue/?kind=book&slug=humility&language=es"
        )
        self.assertEqual(res.status_code, 403)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)

    def test_reviewer_can_retract_their_own_provisional(self):
        self._approve(self._as(self.reviewer))  # provisional, not confirmed
        res = self._as(self.reviewer).delete(
            "/api/admin/review-queue/?kind=book&slug=humility&language=es"
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(
            ReviewOutcome.objects.filter(kind="book", slug="humility", language="es").exists()
        )

    def test_approver_can_reopen_a_confirmed_item(self):
        self._approve(self._as(self.superu))
        self._needs_work(self._as(self.superu))
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_UNREVIEWED)

    def test_queue_surfaces_the_provisional_state(self):
        self._approve(self._as(self.reviewer))
        res = self._as(self.superu).get("/api/admin/review-queue/")
        row = next(
            r for r in res.data["results"]
            if r["slug"] == "humility" and r["language"] == "es"
        )
        self.assertEqual(row["outcome"]["outcome"], "approved")
        self.assertTrue(row["outcome"]["provisional"])
