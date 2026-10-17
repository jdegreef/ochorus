"""Editable automated emails (emails/lifecycle_copy.py): the original from code,
the working copy, publishing per language, statuses, reset and history, the
per-reader placeholders and link, AI drafts, and the admin API."""

from __future__ import annotations

import json
from unittest import mock

from django.test import TestCase, override_settings

from library.models import AdminAction

from . import lifecycle_copy as lc
from . import translation_jobs as jobs
from .models import EmailSubscription, LifecycleCopy, LifecycleCopyVersion
from .rendering import render_milestone, render_series_nudge, render_step
from .tests import SENDING, _make_profile
from .tests_translation import _GitHub


def _edit(step, lang, *, subject=None, text=None):
    """Change the working copy's subject and first text block in ``lang``."""
    copy = lc.row(step)
    content = dict(copy.content)
    email = lc.working(copy, lang)
    blocks = email["blocks"]
    if text is not None:
        for b in blocks:
            if b["type"] == "text":
                b["text"] = text
                break
    content[lang] = {"preheader": email["preheader"], "blocks": blocks}
    return lc.save_working(step, {lang: subject or email["subject"]}, content, actor="admin@example.com")


class _Clean(TestCase):
    def setUp(self):
        self.addCleanup(lc._LIVE.clear)  # the per-process memo outlives each test's rows


class OriginalTests(_Clean):
    def test_every_editable_step_has_an_english_original(self):
        for step in lc.STEPS:
            with self.subTest(step.key):
                email = lc.original(step.key, "en")
                self.assertTrue(email["subject"])
                self.assertTrue(email["blocks"])
                self.assertEqual(lc.check(step.key, "en", email), [])

    def test_a_per_reader_button_is_marked_as_the_link(self):
        email = lc.original("finish_series", "en")
        buttons = [b for b in email["blocks"] if b["type"] == "button"]
        self.assertEqual(buttons[0]["path"], "{link}")

    def test_an_unedited_email_is_all_original(self):
        statuses = lc.statuses(lc.row("welcome"))
        self.assertEqual({s["status"] for s in statuses.values()}, {"original"})
        self.assertIn("es", statuses)


@SENDING
class PublishTests(_Clean):
    def setUp(self):
        super().setUp()
        self.reader = _make_profile(name="Ana Reader")
        self.sub = EmailSubscription.objects.create(profile=self.reader)

    def test_saving_changes_nothing_readers_see_until_published(self):
        _edit("welcome", "en", subject="Welcome home, {first_name}", text="Hello {first_name}, this is new.")
        self.assertEqual(render_step("welcome", self.reader, self.sub).subject, "Welcome to Ochorus")
        self.assertEqual(lc.statuses(lc.row("welcome"))["en"]["status"], "edited")

        lc.publish("welcome", actor="admin@example.com")
        rendered = render_step("welcome", self.reader, self.sub)
        self.assertEqual(rendered.subject, "Welcome home, Ana")
        self.assertIn("Hello Ana, this is new.", rendered.html)
        statuses = lc.statuses(lc.row("welcome"))
        self.assertEqual(statuses["en"]["status"], "published")
        # Spanish still sends its original, and now needs a look.
        self.assertEqual(statuses["es"]["status"], "original")
        self.assertTrue(statuses["es"]["stale"])
        self.assertEqual(LifecycleCopyVersion.objects.count(), 1)

    def test_other_languages_keep_their_original(self):
        _edit("welcome", "en", subject="Welcome home")
        lc.publish("welcome")
        es = _make_profile(email="es@example.com", locale="es")
        sub = EmailSubscription.objects.create(profile=es)
        self.assertEqual(render_step("welcome", es, sub).subject, "Bienvenido a Ochorus")

    def test_placeholders_and_the_per_reader_link_survive_an_edit(self):
        _edit("finish_series", "en", subject="Next up: {next}", text="You finished {finished}.")
        lc.publish("finish_series")
        rendered = render_series_nudge(
            self.reader, self.sub, finished_title="Book One", next_title="Book Two", cta_path="books/book-two/"
        )
        self.assertEqual(rendered.subject, "Next up: Book Two")
        self.assertIn("You finished Book One.", rendered.html)
        self.assertIn('href="https://ochorus.test/books/book-two/"', rendered.html)

    def test_milestone_count(self):
        _edit("milestone", "en", subject="{count} books!")
        lc.publish("milestone")
        self.assertEqual(render_milestone(self.reader, self.sub, milestone=5).subject, "5 books!")

    def test_publish_refuses_a_broken_email(self):
        _edit("welcome", "en", subject=" ")
        with self.assertRaises(lc.CopyError):
            lc.publish("welcome")
        _edit("milestone", "en", subject="{next} books")  # not a milestone placeholder
        with self.assertRaisesRegex(lc.CopyError, "next"):
            lc.publish("milestone")

    def test_reset_goes_back_to_the_original(self):
        _edit("welcome", "en", subject="Welcome home")
        lc.publish("welcome")
        lc.reset("welcome", "en")
        self.assertEqual(render_step("welcome", self.reader, self.sub).subject, "Welcome to Ochorus")
        self.assertEqual(lc.statuses(lc.row("welcome"))["en"]["status"], "original")

    def test_restore_brings_a_version_back_into_the_working_copy(self):
        _edit("welcome", "en", subject="Version one")
        lc.publish("welcome")
        version = LifecycleCopyVersion.objects.get()
        _edit("welcome", "en", subject="Version two")
        lc.restore("welcome", version.id)
        self.assertEqual(lc.working(lc.row("welcome"), "en")["subject"], "Version one")


@override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t", GITHUB_TRANSLATION_REPO="x/y")
class TranslationTests(_Clean):
    def setUp(self):
        super().setUp()
        self.gh = _GitHub()
        patcher = mock.patch.multiple(
            "emails.translation_jobs.requests", post=self.gh.post, get=self.gh.get, patch=self.gh.patch
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_an_ai_draft_must_be_approved_before_it_publishes(self):
        _edit("welcome", "en", text="Hello {first_name}, this is new.")
        lc.publish("welcome")
        copy = lc.row("welcome")
        jobs.request(copy, "en", "es")
        self.assertIn("email:lifecycle-welcome -> es", self.gh.filed[0]["title"])
        payload = self.gh.payload()
        self.assertEqual(payload["broadcast"], "lifecycle-welcome")
        texts = [t.replace("Hello", "Hola") for t in payload["texts"]]
        reply = jobs.check_answer(payload, {"subject": "Bienvenido", "preheader": "", "texts": texts})
        with mock.patch.object(jobs, "_replies", return_value=iter([reply])):
            jobs.fetch(copy, "es")
        self.assertEqual(lc.statuses(copy)["es"]["status"], "draft")
        with self.assertRaisesRegex(lc.CopyError, "approved"):
            lc.publish("welcome", ["es"])
        jobs.approve(copy, "es")
        lc.publish("welcome", ["es"])
        statuses = lc.statuses(lc.row("welcome"))
        self.assertEqual(statuses["es"]["status"], "published")
        self.assertFalse(statuses["es"]["stale"])


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class ApiTests(_Clean):
    def _post(self, step, payload):
        return self.client.post(
            f"/api/admin/emails/lifecycle/{step}/action/", data=json.dumps(payload), content_type="application/json"
        )

    def test_list_edit_publish_reset(self):
        steps = self.client.get("/api/admin/emails/lifecycle/").json()["steps"]
        self.assertEqual(steps[0]["key"], "welcome")
        self.assertEqual(steps[0]["counts"], {"original": steps[0]["languages"]})

        detail = self.client.get("/api/admin/emails/lifecycle/welcome/").json()
        self.assertEqual(detail["subject"]["en"], "Welcome to Ochorus")
        self.assertEqual(detail["versions"], [])
        content = detail["content"]
        content["en"]["blocks"][0]["text"] = "Welcome, friend"
        res = self.client.patch(
            "/api/admin/emails/lifecycle/welcome/",
            data=json.dumps({"subject": {"en": "Hello there"}, "content": {"en": content["en"]}}),
            content_type="application/json",
        )
        self.assertEqual(res.json()["statuses"]["en"]["status"], "edited")
        res = self._post("welcome", {"action": "publish"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["statuses"]["en"]["status"], "published")
        self.assertEqual(len(res.json()["versions"]), 1)
        self.assertEqual(self._post("welcome", {"action": "publish"}).status_code, 409)  # nothing to publish
        res = self._post("welcome", {"action": "reset", "language": "en"})
        self.assertEqual(res.json()["statuses"]["en"]["status"], "original")
        actions = set(AdminAction.objects.values_list("action", flat=True))
        self.assertTrue({AdminAction.Action.EMAIL_LIFECYCLE_EDIT, AdminAction.Action.EMAIL_LIFECYCLE_PUBLISH, AdminAction.Action.EMAIL_LIFECYCLE_RESET} <= actions)
        self.assertTrue(LifecycleCopy.objects.filter(step="welcome").exists())

    def test_unknown_step(self):
        self.assertEqual(self.client.get("/api/admin/emails/lifecycle/nope/").status_code, 404)


@SENDING
class ReviewFixTests(_Clean):
    def test_a_language_without_its_own_words_gets_the_edited_english(self):
        from . import copy as copy_mod

        reader = _make_profile(locale="de")
        sub = EmailSubscription.objects.create(profile=reader)
        self.assertNotIn("de", copy_mod.LIFECYCLE["welcome"])
        _edit("welcome", "en", subject="Welcome home")
        lc.publish("welcome")
        self.assertEqual(render_step("welcome", reader, sub).subject, "Welcome home")

    def test_step_placeholders_take_no_fallback(self):
        email = lc.original("finish_series", "en")
        email["subject"] = "Up next: {next|the next book}"
        self.assertTrue(any("drop the part" in p for p in lc.check("finish_series", "en", email)))

    def test_link_only_as_a_button_path_and_required_where_it_matters(self):
        email = lc.original("plan_reminder", "en")
        email["blocks"] = [b for b in email["blocks"] if b["type"] != "button"]
        self.assertTrue(any("{link}" in p for p in lc.check("plan_reminder", "en", email)))
        welcome = lc.original("welcome", "en")
        welcome["blocks"].append({"type": "text", "text": "Open it: {link}"})
        self.assertTrue(any("{link}" in p for p in lc.check("welcome", "en", welcome)))
