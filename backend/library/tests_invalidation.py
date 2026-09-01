"""The one content-changed channel: revision bump + throttled rebuild.

Import publish and review approval mutate reader-visible content without a deploy;
before this they rebuilt nothing (the repo digest can't see a DB change), so the
prerendered reader went stale. These assert the channel bumps the revision and
fires the deploy hook, coalescing a burst but never leaving a change un-deployed.
"""

from __future__ import annotations

from unittest import mock

import requests
from django.test import TestCase, override_settings

from rest_framework.test import APIClient

from library import invalidation
from library.models import Author, Book, ContentRevision

HOOK = "https://hook.test/deploy"


def _ok():
    return mock.Mock(ok=True, status_code=200)


@override_settings(RENDER_WEB_DEPLOY_HOOK=HOOK)
class InvalidationChannelTests(TestCase):
    def _rev(self) -> int:
        return ContentRevision.load().revision

    def test_marking_a_change_bumps_the_revision_and_fires_the_hook(self):
        with mock.patch("library.golive.requests.post", return_value=_ok()) as post:
            before = self._rev()
            result = invalidation.mark_content_changed()
        self.assertEqual(self._rev(), before + 1)
        self.assertEqual(result.status, "triggered")
        self.assertEqual(post.call_count, 1)

    def test_the_throttle_coalesces_a_burst_but_records_the_tail(self):
        with mock.patch("library.golive.requests.post", return_value=_ok()) as post:
            first = invalidation.mark_content_changed()   # fires (leading edge)
            second = invalidation.mark_content_changed()  # within cooldown: suppressed
            self.assertEqual(first.status, "triggered")
            self.assertIsNone(second)
            self.assertEqual(post.call_count, 1)
            # The suppressed change still bumped the revision, so it's recorded as
            # un-deployed — the trailing-edge tail the flush command catches.
            self.assertTrue(invalidation.has_undeployed_changes())

    def test_force_fires_even_within_the_cooldown(self):
        with mock.patch("library.golive.requests.post", return_value=_ok()) as post:
            invalidation.mark_content_changed()                 # fires, starts cooldown
            forced = invalidation.mark_content_changed(force=True)  # go-live: always fires
            self.assertEqual(forced.status, "triggered")
            self.assertEqual(post.call_count, 2)
            self.assertFalse(invalidation.has_undeployed_changes())

    def test_flush_fires_only_when_a_change_is_undeployed(self):
        with mock.patch("library.golive.requests.post", return_value=_ok()) as post:
            self.assertIsNone(invalidation.flush_deploy())  # nothing changed yet
            self.assertEqual(post.call_count, 0)
            invalidation.mark_content_changed()   # fires
            invalidation.mark_content_changed()   # suppressed -> undeployed tail
            flushed = invalidation.flush_deploy()  # fires the tail
            self.assertEqual(flushed.status, "triggered")
            self.assertFalse(invalidation.has_undeployed_changes())

    def test_never_raises_when_the_hook_errors(self):
        with mock.patch(
            "library.golive.requests.post", side_effect=requests.RequestException("boom")
        ):
            result = invalidation.mark_content_changed()
        # trigger_web_deploy caught it; the mutation neither crashes nor is undone,
        # and the revision still moved (the ETag must reflect the change).
        self.assertEqual(result.status, "failed")
        self.assertEqual(self._rev(), 1)


@override_settings(DEBUG=True)  # loopback admin bypass, as the other admin suites do
class InvalidationWiringTests(TestCase):
    """The reader-visible in-request mutations reach the channel."""

    def setUp(self):
        self.client = APIClient()
        Author.objects.create(slug="e-writer", name="E Writer")

    def test_import_publish_bumps_the_revision(self):
        before = ContentRevision.load().revision
        res = self.client.post(
            "/api/admin/import/publish/",
            {"kind": "sermon", "author_slug": "e-writer", "title": "Pub",
             "body_html": "<p>" + " ".join(["word"] * 60) + "</p>"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ContentRevision.load().revision, before + 1)

    def test_review_approval_bumps_the_revision(self):
        Book.objects.create(
            slug="humility", language="es", title="Humildad", is_published=True,
            author=Author.objects.get(slug="e-writer"),
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        before = ContentRevision.load().revision
        # A single top-level item (no bulk gate); outcome defaults to approved.
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "es", "outcome": "approved"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ContentRevision.load().revision, before + 1)
