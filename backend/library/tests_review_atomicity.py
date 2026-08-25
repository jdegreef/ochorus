"""A review decision and its audit row must land together, or not at all.

Approving flips the underlying field (``Book.source_type`` → ai_reviewed, or
``AuthorTranslation.reviewed`` → True) and records the decision in
``ReviewOutcome``. Those were two unprotected writes. If the second failed — a
connection blip, a constraint surprise, a crash mid-batch — the first had already
committed, and the result was the worst kind of loss: an **invisible approval**.

The queue lists only ai_unreviewed rows, so the item disappeared from it, while
carrying no ReviewOutcome — no reviewer, no reason, and no way to undo from the
UI, because undo works off the row that was never written. A translation would
then be presented to readers as native-reviewed with nothing recording that
anyone had reviewed it, which is exactly the claim Ochorus must not make falsely
(backend/CLAUDE.md: never present an unreviewed translation as an original).
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Author, AuthorTranslation, Book, ReviewOutcome


@override_settings(DEBUG=True)
class ReviewDecisionAtomicityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        self.bio = AuthorTranslation.objects.create(
            author=self.author, language="sw", bio_html="<p>Wasifu.</p>", reviewed=False
        )

    def _approve(self, **item):
        return self.client.post("/api/admin/review-queue/", item, format="json")

    # -- the happy path still works -------------------------------------------

    def test_approval_writes_both_the_flip_and_the_outcome(self):
        res = self._approve(kind="book", slug="humility", language="sw")
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        self.assertTrue(
            ReviewOutcome.objects.filter(
                kind="book", slug="humility", language="sw"
            ).exists()
        )

    # -- the failure that used to approve invisibly ---------------------------

    def test_a_failed_audit_write_rolls_the_flip_back(self):
        """The book must stay in the queue rather than become a silent approval."""
        with mock.patch.object(
            ReviewOutcome.objects,
            "update_or_create",
            side_effect=RuntimeError("audit write failed"),
        ):
            with self.assertRaises(RuntimeError):
                self._approve(kind="book", slug="humility", language="sw")

        self.book.refresh_from_db()
        self.assertEqual(
            self.book.source_type,
            Book.SourceType.AI_UNREVIEWED,
            "the flip committed without its audit row — an invisible approval",
        )
        self.assertFalse(
            ReviewOutcome.objects.filter(slug="humility").exists()
        )

    def test_a_failed_audit_write_rolls_a_bio_approval_back(self):
        with mock.patch.object(
            ReviewOutcome.objects,
            "update_or_create",
            side_effect=RuntimeError("audit write failed"),
        ):
            with self.assertRaises(RuntimeError):
                self._approve(kind="bio", slug="am", language="sw")

        self.bio.refresh_from_db()
        self.assertFalse(self.bio.reviewed)

    # -- a refusal must not leave a half-applied decision ---------------------

    def test_a_refused_item_writes_nothing(self):
        """A public-domain original is refused; nothing may be recorded for it."""
        Book.objects.create(
            author=self.author, slug="abide", language="en", title="Abide"
        )  # public_domain by default
        res = self._approve(kind="book", slug="abide", language="en")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(ReviewOutcome.objects.filter(slug="abide").exists())
        self.assertEqual(
            Book.objects.get(slug="abide", language="en").source_type,
            Book.SourceType.PUBLIC_DOMAIN,
        )

    def test_a_refusal_still_reports_its_reason(self):
        """Raising through the atomic block must not swallow the message."""
        res = self._approve(kind="book", slug="nope", language="sw")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.data["skipped"])
        self.assertIn("No such", res.data["skipped"][0]["reason"])

    # -- batches stay partial, not all-or-nothing -----------------------------

    def test_one_bad_row_does_not_roll_back_the_good_ones(self):
        """Per-item atomicity: the documented 207 must survive the change.

        Uses `needs_work` rather than an approval because BULK approval is gated
        separately (`enforce_gate` — scripture notes must exist), and that gate
        would reject both rows before reaching the code under test here. The
        atomic block is identical for either outcome.
        """
        res = self.client.post(
            "/api/admin/review-queue/",
            {
                "outcome": ReviewOutcome.Outcome.NEEDS_WORK,
                "items": [
                    {"kind": "book", "slug": "humility", "language": "sw"},
                    {"kind": "book", "slug": "nope", "language": "sw"},
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 207)
        self.assertEqual(len(res.data["decided"]), 1)
        self.assertEqual(len(res.data["skipped"]), 1)
        # The good row kept BOTH of its writes; the bad row wrote neither.
        self.assertTrue(
            ReviewOutcome.objects.filter(slug="humility", language="sw").exists()
        )
        self.assertFalse(ReviewOutcome.objects.filter(slug="nope").exists())
