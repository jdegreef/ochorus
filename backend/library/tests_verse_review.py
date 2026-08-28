"""Settling one flagged quotation, which is the unit the backlog moves in.

`ReviewQueueTests` covers the work-level decision. These cover the per-verse one
— the thing #972 is about: 187 translations are `ai_unreviewed` and none is
approved, because approving one means answering "is this whole book right" with
no way to work the specific lines the pipeline already identified.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import (
    Author,
    Book,
    Chapter,
    TranslationNote,
    VerseReview,
)


@override_settings(DEBUG=True)  # loopback admin bypass, as the other admin suites do
class VerseReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("admin-review-verse")
        cls.detail_url = reverse("admin-review-detail")
        cls.queue_url = reverse("admin-review-queue")
        cls.author = Author.objects.create(slug="a-murray", name="Andrew Murray")
        for lang, st in (
            ("en", Book.SourceType.PUBLIC_DOMAIN),
            ("sw", Book.SourceType.AI_UNREVIEWED),
        ):
            book = Book.objects.create(
                author=cls.author, slug="waiting", language=lang,
                title=f"Waiting {lang}", source_type=st,
            )
            # Two chapters, so the work-level block index has to cross a
            # chapter boundary to resolve — the case a per-chapter reading of
            # `block_index` gets silently wrong.
            Chapter.objects.create(
                book=book, order=1, title="One",
                body_html="<p>first block</p><p>second block</p>",
            )
            Chapter.objects.create(
                book=book, order=2, title="Two",
                body_html="<p>third block</p><p>Ps 62:5 — my soul waits</p>",
            )
        TranslationNote.objects.create(
            kind="book", slug="waiting", language="sw",
            reference="Psalm 62:5", status=TranslationNote.Status.SELF_RENDERED,
            block_index=3,
        )
        TranslationNote.objects.create(
            kind="book", slug="waiting", language="sw",
            reference="John 3:16", status=TranslationNote.Status.MINED,
            block_index=0,
        )

    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="a", email="admin@example.com", password="x"
        )
        self.client.force_login(self.admin)

    def _decide(self, **over):
        payload = {
            "kind": "book", "slug": "waiting", "language": "sw",
            "reference": "Psalm 62:5", "outcome": "approved",
        }
        payload.update(over)
        return self.client.post(self.url, payload, content_type="application/json")

    # ---- recording a decision ------------------------------------------------

    def test_a_decision_is_recorded(self):
        res = self._decide(note="Matches the Union Version.")
        self.assertEqual(res.status_code, 200)
        row = VerseReview.objects.get()
        self.assertEqual(row.outcome, "approved")
        self.assertEqual(row.note, "Matches the Union Version.")
        # Reviewer is whatever the TOKEN carries; the loopback bypass these
        # suites run under leaves DRF's user anonymous, so its value is not
        # assertable here. `test_a_decision_names_its_reviewer` proves it.
        self.assertIsInstance(row.reviewer, str)

    def test_deciding_twice_updates_rather_than_duplicates(self):
        self._decide()
        self._decide(outcome="needs_work", note="Verb tense is wrong.")
        row = VerseReview.objects.get()
        self.assertEqual(row.outcome, "needs_work")
        self.assertEqual(row.note, "Verb tense is wrong.")

    def test_a_verse_the_pipeline_never_flagged_is_refused(self):
        """Otherwise the settled count can exceed the count of things to settle
        — a progress bar that reads 14 of 12."""
        res = self._decide(reference="Habakkuk 2:4")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(VerseReview.objects.exists())

    def test_an_unknown_outcome_is_refused(self):
        self.assertEqual(self._decide(outcome="probably").status_code, 400)
        self.assertEqual(self._decide(outcome="").status_code, 400)

    def test_missing_identifiers_are_refused(self):
        self.assertEqual(self._decide(slug="").status_code, 400)
        self.assertEqual(self._decide(kind="anthology").status_code, 400)

    def test_a_decision_can_be_undone(self):
        self._decide()
        res = self.client.delete(
            f"{self.url}?kind=book&slug=waiting&language=sw&reference=Psalm+62:5"
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(VerseReview.objects.exists())
        self.assertEqual(
            self.client.delete(
                f"{self.url}?kind=book&slug=waiting&language=sw&reference=Psalm+62:5"
            ).status_code,
            404,
        )

    # ---- what the reviewer is shown -----------------------------------------

    def test_the_detail_view_resolves_the_verse_text_across_chapters(self):
        """`block_index` is WORK-level: block 3 is the second block of chapter
        TWO. Reading it as an offset into the chapter on screen would show the
        reviewer a sentence the note is not about."""
        data = self.client.get(
            self.detail_url, {"kind": "book", "slug": "waiting", "language": "sw"}
        ).json()
        note = next(n for n in data["notes"] if n["reference"] == "Psalm 62:5")
        self.assertEqual(note["text"], "Ps 62:5 — my soul waits")
        self.assertEqual(note["chapter"], 2, "so the reviewer can open the right chapter")

    def test_an_index_pointing_past_the_work_resolves_to_nothing(self):
        """0.3% of shipped indexes do, where the text was edited after the note
        was written. A neighbouring block would be a confident wrong answer."""
        TranslationNote.objects.filter(reference="Psalm 62:5").update(block_index=99)
        data = self.client.get(
            self.detail_url, {"kind": "book", "slug": "waiting", "language": "sw"}
        ).json()
        note = next(n for n in data["notes"] if n["reference"] == "Psalm 62:5")
        self.assertIsNone(note["text"])
        self.assertIsNone(note["chapter"])

    def test_the_detail_view_carries_the_decision(self):
        self._decide(note="Checked against the Union Version.")
        data = self.client.get(
            self.detail_url, {"kind": "book", "slug": "waiting", "language": "sw"}
        ).json()
        note = next(n for n in data["notes"] if n["reference"] == "Psalm 62:5")
        self.assertEqual(note["review"]["outcome"], "approved")
        self.assertEqual(note["review"]["note"], "Checked against the Union Version.")
        mined = next(n for n in data["notes"] if n["reference"] == "John 3:16")
        self.assertIsNone(mined["review"])

    def test_the_queue_reports_progress(self):
        rows = self.client.get(self.queue_url).json()["results"]
        row = next(r for r in rows if r["kind"] == "book" and r["language"] == "sw")
        self.assertEqual(row["notes"]["self_rendered"], 1)
        self.assertEqual(row["notes"]["settled"], 0)

        self._decide()
        rows = self.client.get(self.queue_url).json()["results"]
        row = next(r for r in rows if r["kind"] == "book" and r["language"] == "sw")
        self.assertEqual(row["notes"]["settled"], 1)

    def test_a_decision_names_its_reviewer(self):
        """Attribution is the point of recording a decision at all.

        `force_authenticate` puts a real user on the DRF request, which the
        loopback bypass alone does not — under it `request.user` is anonymous,
        which is why the suites above can only assert the field's type.
        """
        api = APIClient()
        api.force_authenticate(self.admin)
        res = api.post(self.url, {
            "kind": "book", "slug": "waiting", "language": "sw",
            "reference": "Psalm 62:5", "outcome": "approved",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(VerseReview.objects.get().reviewer, "admin@example.com")

    # ---- the reason this is a separate table ---------------------------------

    def test_a_decision_survives_the_notes_being_re_seeded(self):
        """`seed_translation_notes` re-seeds by delete-then-create. A decision
        held on `TranslationNote` would not merely be walked back on the next
        deploy — it would be destroyed."""
        self._decide()
        TranslationNote.objects.filter(
            kind="book", slug="waiting", language="sw"
        ).delete()
        TranslationNote.objects.create(
            kind="book", slug="waiting", language="sw",
            reference="Psalm 62:5", status=TranslationNote.Status.SELF_RENDERED,
            block_index=3,
        )
        data = self.client.get(
            self.detail_url, {"kind": "book", "slug": "waiting", "language": "sw"}
        ).json()
        note = next(n for n in data["notes"] if n["reference"] == "Psalm 62:5")
        self.assertEqual(note["review"]["outcome"], "approved")


class VerseReviewPermissionTests(TestCase):
    """Without the loopback bypass the other suites run under.

    Kept in its own class deliberately: `@override_settings(DEBUG=True)` grants
    admin to any loopback request, so an "admin only" assertion made inside that
    class would pass no matter what the permission said.
    """

    def setUp(self):
        self.url = reverse("admin-review-verse")
        self.payload = {
            "kind": "book", "slug": "waiting", "language": "sw",
            "reference": "Psalm 62:5", "outcome": "approved",
        }

    def test_an_anonymous_caller_cannot_settle_a_verse(self):
        res = self.client.post(self.url, self.payload, content_type="application/json")
        self.assertIn(res.status_code, (401, 403))
        self.assertFalse(VerseReview.objects.exists())

    def test_a_signed_in_non_admin_cannot_settle_a_verse(self):
        user = get_user_model().objects.create_user(
            username="reader", email="reader@example.com", password="x"
        )
        self.client.force_login(user)
        res = self.client.post(self.url, self.payload, content_type="application/json")
        self.assertIn(res.status_code, (401, 403))
        self.assertFalse(VerseReview.objects.exists())

    def test_an_anonymous_caller_cannot_undo_one(self):
        res = self.client.delete(
            f"{self.url}?kind=book&slug=waiting&language=sw&reference=Psalm+62:5"
        )
        self.assertIn(res.status_code, (401, 403))
