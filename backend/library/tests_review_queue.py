"""Review-queue tests: coverage, gating, decisions, undo.

The regression that motivated most of this: sermons were absent from the queue
while 74 of them shipped unreviewed — more than the books that *were* listed —
so clearing the screen implied an empty backlog that was not empty.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    ReviewOutcome,
    Sermon,
    TranslationNote,
)
from .qa import translation_flags


class TranslationFlagsTests(TestCase):
    def test_ordered_sequence_not_counts(self):
        """Equal tag COUNTS with a different order must not pass."""
        src = "<p>a</p><li>b</li>"
        tgt = "<li>a</li><p>b</p>"
        f = translation_flags(src, tgt, language="sw", kind="sermon")
        self.assertEqual(f["tag_counts"], [4, 4])
        self.assertFalse(f["tags_match"])

    def test_identical_sequence_matches(self):
        src = "<p>one two three</p>"
        tgt = "<p>moja mbili tatu</p>"
        self.assertTrue(translation_flags(src, tgt, language="sw", kind="sermon")["tags_match"])

    def test_ratio_reported_with_its_band(self):
        f = translation_flags(
            "<p>" + " ".join(["w"] * 100) + "</p>",
            "<p>" + " ".join(["n"] * 83) + "</p>",
            language="sw",
            kind="sermon",
        )
        self.assertEqual(f["ratio"], 83.0)
        self.assertEqual(f["band"], [73.6, 93.5])
        self.assertTrue(f["ratio_in_band"])

    def test_missing_band_is_none_not_a_neighbours(self):
        """An unmeasured (language, type) has no band — never borrow one."""
        f = translation_flags("<p>a</p>", "<p>b</p>", language="zz", kind="sermon")
        self.assertIsNone(f["band"])
        self.assertIsNone(f["ratio_in_band"])

    def test_mixed_quote_styles_flagged(self):
        mixed = '<p>“curly” and "straight"</p>'
        self.assertFalse(
            translation_flags("<p>x</p>", mixed, language="sw", kind="sermon")[
                "quote_style_consistent"
            ]
        )
        for body in ('<p>“curly” only</p>', '<p>"straight" only</p>'):
            self.assertTrue(
                translation_flags("<p>x</p>", body, language="sw", kind="sermon")[
                    "quote_style_consistent"
                ]
            )


@override_settings(DEBUG=True)  # loopback admin bypass, as the other admin suites do
class ReviewQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("admin-review-queue")
        cls.detail_url = reverse("admin-review-detail")
        cls.author = Author.objects.create(slug="a-b-simpson", name="A. B. Simpson")
        for lang, st in (
            ("en", Book.SourceType.PUBLIC_DOMAIN),
            ("sw", Book.SourceType.AI_UNREVIEWED),
        ):
            Sermon.objects.create(
                author=cls.author,
                slug="possibilities",
                language=lang,
                title=f"Possibilities {lang}",
                body_html="<p>one</p><p>two</p>",
                word_count=2,
                source_type=st,
            )
        for lang, st in (
            ("en", Book.SourceType.PUBLIC_DOMAIN),
            ("sw", Book.SourceType.AI_UNREVIEWED),
        ):
            b = Book.objects.create(
                author=cls.author, slug="waiting", language=lang, title=f"Waiting {lang}",
                source_type=st,
            )
            Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        AuthorTranslation.objects.create(
            author=cls.author, language="sw", bio="Fupi", bio_html="<p>Ndefu</p>", reviewed=False
        )

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="a", email="admin@example.com", password="x"
        )
        self.client.force_login(self.admin)

    def _get(self, **params):
        return self.client.get(self.url, params).json()

    def test_sermons_appear(self):
        """The regression this suite exists for."""
        kinds = {r["kind"] for r in self._get()["results"]}
        self.assertIn("sermon", kinds)
        self.assertEqual(kinds, {"book", "sermon", "bio"})

    def test_public_domain_originals_are_not_queued(self):
        slugs = {(r["kind"], r["language"]) for r in self._get()["results"]}
        self.assertNotIn(("sermon", "en"), slugs)

    def test_facets_and_filters(self):
        data = self._get()
        self.assertEqual(data["facets"]["kind"]["sermon"], 1)
        only = self._get(kind="sermon")
        self.assertEqual(only["filtered"], 1)
        self.assertEqual(only["results"][0]["kind"], "sermon")
        self.assertEqual(only["total"], 3, "total stays the unfiltered backlog")

    def test_mechanical_flags_attached_to_the_page(self):
        row = next(r for r in self._get(kind="sermon")["results"] if r["kind"] == "sermon")
        self.assertIsNotNone(row["flags"])
        self.assertTrue(row["flags"]["tags_match"])

    def test_approve_flips_source_type_and_records_who(self):
        res = self.client.post(
            self.url,
            {"items": [{"kind": "sermon", "slug": "possibilities", "language": "sw"}],
             "outcome": "approved"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        s = Sermon.objects.get(slug="possibilities", language="sw")
        self.assertEqual(s.source_type, Book.SourceType.AI_REVIEWED)
        o = ReviewOutcome.objects.get(kind="sermon", slug="possibilities", language="sw")
        self.assertEqual(o.outcome, "approved")
        self.assertIsInstance(o.reviewer, str)

    def test_needs_work_keeps_it_unreviewed_and_keeps_the_note(self):
        self.client.post(
            self.url,
            {"items": [{"kind": "sermon", "slug": "possibilities", "language": "sw"}],
             "outcome": "needs_work", "note": "Ezek 36:32 wording"},
            content_type="application/json",
        )
        s = Sermon.objects.get(slug="possibilities", language="sw")
        self.assertEqual(s.source_type, Book.SourceType.AI_UNREVIEWED)
        self.assertEqual(
            ReviewOutcome.objects.get(slug="possibilities").note, "Ezek 36:32 wording"
        )
        # It leaves the awaiting-review list, so it can't be mistaken for unopened.
        self.assertNotIn(
            "sermon", {r["kind"] for r in self._get()["results"]}
        )
        self.assertEqual(self._get(outcome="needs_work")["filtered"], 1)

    def test_undo_returns_it_to_the_queue(self):
        self.client.post(
            self.url,
            {"items": [{"kind": "sermon", "slug": "possibilities", "language": "sw"}],
             "outcome": "approved"},
            content_type="application/json",
        )
        res = self.client.delete(
            f"{self.url}?kind=sermon&slug=possibilities&language=sw"
        )
        self.assertEqual(res.status_code, 200)
        s = Sermon.objects.get(slug="possibilities", language="sw")
        self.assertEqual(s.source_type, Book.SourceType.AI_UNREVIEWED)
        self.assertFalse(ReviewOutcome.objects.filter(slug="possibilities").exists())
        self.assertIn("sermon", {r["kind"] for r in self._get()["results"]})

    def test_bulk_approve_skips_flagged_rows_server_side(self):
        """The gate must hold even if the client asks for a flagged row."""
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Ezekiel 36:32", status=TranslationNote.Status.SELF_RENDERED,
        )
        # The bio is examined-and-clean, so only the flagged sermon is held back.
        TranslationNote.objects.create(
            kind="bio", slug="a-b-simpson", language="sw",
            reference="John 3:16", status=TranslationNote.Status.MINED,
            source_file="the-way-to-god.sw.json",
        )
        res = self.client.post(
            self.url,
            {"items": [
                {"kind": "sermon", "slug": "possibilities", "language": "sw"},
                {"kind": "bio", "slug": "a-b-simpson", "language": "sw"},
            ], "outcome": "approved"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 207)
        body = res.json()
        self.assertEqual([d["kind"] for d in body["decided"]], ["bio"])
        self.assertEqual(body["skipped"][0]["kind"], "sermon")
        self.assertIn("unverified", body["skipped"][0]["reason"])
        self.assertEqual(
            Sermon.objects.get(slug="possibilities", language="sw").source_type,
            Book.SourceType.AI_UNREVIEWED,
        )

    def test_bulk_approve_fails_closed_when_nothing_is_recorded(self):
        """No notes must mean NOT eligible, never 'nothing found'.

        The gate shipped permissive: an item the pipeline had never examined
        carried no TranslationNote rows, was therefore not "flagged", and sailed
        through a bulk approve. With 148 of 149 items un-noted that inverted the
        gate's purpose — it waved through everything it existed to hold back.
        """
        res = self.client.post(
            self.url,
            {"items": [
                {"kind": "sermon", "slug": "possibilities", "language": "sw"},
                {"kind": "bio", "slug": "a-b-simpson", "language": "sw"},
            ], "outcome": "approved"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertEqual(body["decided"], [])
        self.assertEqual(len(body["skipped"]), 2)
        self.assertTrue(all("no scripture notes" in s["reason"] for s in body["skipped"]))
        self.assertEqual(
            Sermon.objects.get(slug="possibilities", language="sw").source_type,
            Book.SourceType.AI_UNREVIEWED,
        )

    def test_bulk_approve_allows_an_examined_and_clean_row(self):
        """Recorded notes with nothing self-rendered IS eligible."""
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Mark 9:23", status=TranslationNote.Status.MINED,
            source_file="jesus-himself-2.sw.json",
        )
        TranslationNote.objects.create(
            kind="bio", slug="a-b-simpson", language="sw",
            reference="John 3:16", status=TranslationNote.Status.MINED,
            source_file="the-way-to-god.sw.json",
        )
        res = self.client.post(
            self.url,
            {"items": [
                {"kind": "sermon", "slug": "possibilities", "language": "sw"},
                {"kind": "bio", "slug": "a-b-simpson", "language": "sw"},
            ], "outcome": "approved"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["decided"]), 2)

    def test_notes_recorded_is_exposed_so_the_ui_can_say_so(self):
        row = next(r for r in self._get()["results"] if r["kind"] == "sermon")
        self.assertFalse(row["notes_recorded"])
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Mark 9:23", status=TranslationNote.Status.MINED,
        )
        row = next(r for r in self._get()["results"] if r["kind"] == "sermon")
        self.assertTrue(row["notes_recorded"])

    def test_single_approve_of_a_flagged_row_is_allowed(self):
        """Gating is about BULK; an individual reviewer may still approve."""
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Ezekiel 36:32", status=TranslationNote.Status.SELF_RENDERED,
        )
        res = self.client.post(
            self.url,
            {"items": [{"kind": "sermon", "slug": "possibilities", "language": "sw"}],
             "outcome": "approved"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)

    def test_flagged_filter_and_counts(self):
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Ezekiel 36:32", status=TranslationNote.Status.SELF_RENDERED,
            job_issue=425, pull_request=910,
        )
        TranslationNote.objects.create(
            kind="sermon", slug="possibilities", language="sw",
            reference="Isaiah 1:18", status=TranslationNote.Status.MINED,
            source_file="prevailing-prayer.sw.json",
        )
        data = self._get(flagged="1")
        self.assertEqual(data["filtered"], 1)
        row = data["results"][0]
        self.assertEqual(row["notes"]["self_rendered"], 1)
        self.assertEqual(row["notes"]["mined"], 1)
        self.assertEqual(row["provenance"], {"job_issue": 425, "pull_request": 910})
        self.assertEqual(data["flagged_total"], 1)

    def test_detail_returns_aligned_blocks(self):
        data = self.client.get(
            self.detail_url,
            {"kind": "sermon", "slug": "possibilities", "language": "sw"},
        ).json()
        self.assertTrue(data["aligned"])
        self.assertEqual(data["block_counts"], [2, 2])
        self.assertEqual(data["source"]["blocks"], ["one", "two"])

    def test_detail_reports_misalignment_rather_than_pairing_anyway(self):
        s = Sermon.objects.get(slug="possibilities", language="sw")
        s.body_html = "<p>moja</p>"
        s.save()
        data = self.client.get(
            self.detail_url,
            {"kind": "sermon", "slug": "possibilities", "language": "sw"},
        ).json()
        self.assertFalse(data["aligned"])
        self.assertEqual(data["block_counts"], [2, 1])

    def test_pagination_reports_pages(self):
        data = self._get()
        self.assertEqual(data["page"], 1)
        self.assertGreaterEqual(data["pages"], 1)
        self.assertEqual(len(data["results"]), data["filtered"])
