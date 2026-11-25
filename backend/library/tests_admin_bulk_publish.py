"""Bulk publish / unpublish from the admin lists (``/api/admin/publish/bulk/``)."""

import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability, AdminGrant, AdminVerb

from .models import AdminAction, Author, Book, Sermon

URL = "/api/admin/publish/bulk/"
VERIFIED = {"email_verified": True}


@override_settings(ADMIN_EMAILS={"super@ochorus.com"})
class AdminBulkPublishTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        for slug in ("one", "two"):
            for lang in ("es", "sw"):
                Book.objects.create(
                    author=author,
                    slug=slug,
                    language=lang,
                    title=f"{slug} {lang}",
                    is_published=False,
                )
        Book.objects.create(
            author=author,
            slug="lord-teach-us-to-pray-2",
            language="es",
            title="Retired",
            is_published=False,
        )
        Sermon.objects.create(
            author=author, slug="s", language="es", title="S", body_html="<p>x</p>"
        )
        self.superu = User.objects.create(
            username=str(uuid.uuid4()), email="super@ochorus.com"
        )

    def post(self, user, body):
        c = APIClient()
        c.force_authenticate(user=user, token=VERIFIED)
        return c.post(URL, body, format="json")

    def items(self, *pairs):
        return [{"slug": s, "language": lang} for s, lang in pairs]

    def test_publishes_many_and_audits_each_edition(self):
        res = self.post(
            self.superu,
            {
                "kind": "book",
                "published": True,
                "items": self.items(("one", "es"), ("two", "sw")),
            },
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data["changed"]), 2)
        self.assertTrue(Book.objects.get(slug="one", language="es").is_published)
        self.assertFalse(Book.objects.get(slug="one", language="sw").is_published)
        targets = set(
            AdminAction.objects.filter(
                action=AdminAction.Action.CONTENT_PUBLISH
            ).values_list("target", flat=True)
        )
        self.assertEqual(targets, {"book:one:es", "book:two:sw"})

    def test_skips_what_the_toggle_would_refuse_and_answers_207(self):
        res = self.post(
            self.superu,
            {
                "kind": "book",
                "published": True,
                "items": self.items(
                    ("one", "es"), ("lord-teach-us-to-pray-2", "es"), ("nope", "es")
                ),
            },
        )
        self.assertEqual(res.status_code, 207)
        self.assertEqual([i["slug"] for i in res.data["changed"]], ["one"])
        reasons = {i["slug"]: i["reason"] for i in res.data["skipped"]}
        self.assertIn("retired", reasons["lord-teach-us-to-pray-2"])
        self.assertEqual(reasons["nope"], "No such edition.")

    def test_an_incomplete_item_is_reported_not_dropped(self):
        res = self.post(
            self.superu,
            {
                "kind": "book",
                "published": True,
                "items": [{"slug": "one", "language": ""}],
            },
        )
        self.assertEqual(res.status_code, 207)
        self.assertEqual(
            res.data["skipped"][0]["reason"], "Needs both a slug and a language."
        )

    def test_unpublish_and_unchanged_rows_record_nothing(self):
        res = self.post(
            self.superu,
            {"kind": "sermon", "published": False, "items": self.items(("s", "es"))},
        )
        self.assertEqual(res.data["changed"], [{"slug": "s", "language": "es"}])
        self.assertFalse(Sermon.objects.get(slug="s").is_published)
        again = self.post(
            self.superu,
            {"kind": "sermon", "published": False, "items": self.items(("s", "es"))},
        )
        self.assertEqual(again.data["unchanged"], [{"slug": "s", "language": "es"}])
        self.assertEqual(
            AdminAction.objects.filter(
                action=AdminAction.Action.CONTENT_UNPUBLISH
            ).count(),
            1,
        )

    def test_a_scoped_grant_publishes_only_its_languages(self):
        User.objects.create(username=str(uuid.uuid4()), email="sw@ochorus.com")
        AdminGrant.objects.create(
            email="sw@ochorus.com",
            capability=AdminCapability.PUBLISH,
            verb=AdminVerb.ACT,
            languages="sw",
        )
        sw_admin = User.objects.get(email="sw@ochorus.com")
        res = self.post(
            sw_admin,
            {
                "kind": "book",
                "published": True,
                "items": self.items(("one", "sw"), ("one", "es")),
            },
        )
        self.assertEqual(res.status_code, 207)
        self.assertEqual(res.data["changed"], [{"slug": "one", "language": "sw"}])
        self.assertFalse(Book.objects.get(slug="one", language="es").is_published)

    def test_rejects_bad_requests_and_strangers(self):
        self.assertEqual(
            self.post(self.superu, {"kind": "plan", "items": [{}]}).status_code, 400
        )
        self.assertEqual(
            self.post(self.superu, {"kind": "book", "items": []}).status_code, 400
        )
        self.assertEqual(
            self.post(self.superu, {"kind": "book", "items": ["one"]}).status_code, 400
        )
        stranger = User.objects.create(
            username=str(uuid.uuid4()), email="reader@example.com"
        )
        res = self.post(stranger, {"kind": "book", "items": self.items(("one", "es"))})
        self.assertIn(res.status_code, (401, 403))
