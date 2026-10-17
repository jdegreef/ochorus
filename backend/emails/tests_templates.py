"""The template gallery: the starter templates, saved templates' category and
description, and the pre-send check that stops a template hint going out."""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase, override_settings

from library.models import AdminAction

from . import blocks as blocks_mod
from . import starter_templates
from .models import EmailTemplate, TemplateCategory
from .preflight import PLACEHOLDER
from .preflight import run as run_checks
from .tests import _broadcast

CONTENT = Path(__file__).resolve().parent.parent / "library" / "fixtures" / "content"


class StarterTests(SimpleTestCase):
    def test_keys_are_unique_and_categories_known(self):
        keys = [s["key"] for s in starter_templates.STARTERS]
        self.assertEqual(len(keys), len(set(keys)))
        for s in starter_templates.STARTERS:
            self.assertIn(s["category"], TemplateCategory.values)

    def test_blocks_are_already_clean(self):
        # A starter that `clean` would change would lose words on first save.
        for s in starter_templates.STARTERS:
            with self.subTest(s["key"]):
                self.assertEqual(blocks_mod.clean(s["blocks"]), s["blocks"])

    def test_named_works_ship_in_the_fixture(self):
        plans = {
            row["fields"]["slug"]
            for row in json.loads((CONTENT / "plans.json").read_text())
            if row["model"] == "library.plan"
        }
        for s in starter_templates.STARTERS:
            for b in s["blocks"]:
                with self.subTest(s["key"], slug=b.get("slug")):
                    if b["type"] == "book":
                        self.assertTrue((CONTENT / "books" / f"{b['slug']}.en.json").exists())
                    elif b["type"] == "plan":
                        self.assertIn(b["slug"], plans)

    def test_hint_pattern(self):
        self.assertTrue(PLACEHOLDER.search("Now in the library: [Book title]"))
        self.assertFalse(PLACEHOLDER.search("Romans [sic] and [1]"))


class PlaceholderCheckTests(TestCase):
    def test_an_unedited_starter_cant_be_sent(self):
        starter = starter_templates.serialize(starter_templates.STARTERS[0])
        b = _broadcast(subject=starter["subject"], content=starter["content"])
        errors = {c["code"] for c in run_checks(b) if c["level"] == "error"}
        self.assertIn("placeholder:en", errors)

    def test_own_words_pass(self):
        b = _broadcast(
            subject={"en": "October news"},
            content={"en": {"blocks": [{"type": "text", "text": "Dear {name}, hello."}]}},
        )
        self.assertNotIn("placeholder:en", {c["code"] for c in run_checks(b)})


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class TemplateApiTests(TestCase):
    def test_list_has_starters_and_categories(self):
        data = self.client.get("/api/admin/emails/templates/").json()
        self.assertEqual(len(data["starters"]), len(starter_templates.STARTERS))
        self.assertEqual(data["starters"][0]["locales"], ["en"])
        self.assertIn({"key": "seasonal", "label": "Seasonal"}, data["categories"])

    def test_save_with_category_then_edit(self):
        b = _broadcast()
        res = self.client.post(
            "/api/admin/emails/templates/",
            data=json.dumps({"name": "Launch", "from_broadcast": b.pk, "category": "announcement", "description": "For launches"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["category"], "announcement")
        tid = res.json()["id"]
        res = self.client.patch(
            f"/api/admin/emails/templates/{tid}/",
            data=json.dumps({"name": "Book launch", "category": "bogus", "description": ""}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        t = EmailTemplate.objects.get(pk=tid)
        self.assertEqual((t.name, t.category, t.description), ("Book launch", "announcement", ""))
        self.assertEqual(
            self.client.patch(f"/api/admin/emails/templates/{tid}/", data=json.dumps({"name": " "}), content_type="application/json").status_code,
            400,
        )
        self.assertEqual(
            AdminAction.objects.filter(action=AdminAction.Action.EMAIL_TEMPLATE_SAVE).count(), 2
        )
