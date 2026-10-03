"""Tests for AI-drafted email translations: filing the job, the worker's
translation, pulling the draft in (words only), approval, and the send gate."""

from __future__ import annotations

import io
import json
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from library.models import AdminAction

from . import translation_jobs as jobs
from .models import Broadcast
from .preflight import run as run_checks
from .tests import _broadcast, _make_profile
from .translate import TranslateError, reply_comment, translate_payload

BLOCKS = [
    {"type": "heading", "text": "Wait for the Lord"},
    {"type": "text", "text": "Dear {name},\n\nAdvent is a season of waiting."},
    {"type": "book", "slug": "the-inner-chamber", "label": "Start reading"},
    {"type": "button", "label": "Begin the plan", "path": "plans/humility-12-days/"},
    {"type": "divider"},
]


def _campaign(**kw):
    return _broadcast(
        subject={"en": "Wait for the Lord this Advent"},
        content={"en": {"preheader": "24 days", "blocks": BLOCKS}},
        **kw,
    )


def _spanish(payload):
    """A worker's reply: the same blocks with Spanish words."""
    words = {
        "Wait for the Lord": "Espera en el Señor",
        "Dear {name},\n\nAdvent is a season of waiting.": "Querido {name},\n\nEl Adviento es tiempo de espera.",
        "Start reading": "Empieza a leer",
        "Begin the plan": "Comienza el plan",
    }
    return {
        "broadcast": payload["broadcast"],
        "target": "es",
        "source_digest": payload["source_digest"],
        "subject": "Espera en el Señor este Adviento",
        "preheader": "24 días",
        "blocks": [
            {**b, **{f: words.get(b.get(f), b.get(f)) for f in ("text", "label") if f in b}}
            for b in payload["blocks"]
        ],
    }


class _GitHub:
    """A fake of the two GitHub calls: file an issue, list its comments."""

    def __init__(self):
        self.filed = []
        self.comments = []

    def post(self, url, json=None, **kw):
        self.filed.append(json)
        return mock.Mock(
            status_code=201,
            raise_for_status=lambda: None,
            json=lambda: {"number": 4242, "html_url": "https://github.com/x/y/issues/4242"},
        )

    def get(self, url, **kw):
        return mock.Mock(raise_for_status=lambda: None, json=lambda: self.comments)

    def payload(self):
        body = self.filed[-1]["body"]
        return json.loads(body.split("```json", 1)[1].split("```", 1)[0])


@override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t", GITHUB_TRANSLATION_REPO="x/y")
class TranslationJobTests(TestCase):
    def setUp(self):
        _make_profile()
        self.gh = _GitHub()
        patcher = mock.patch.multiple(
            "emails.translation_jobs.requests", post=self.gh.post, get=self.gh.get
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _act(self, broadcast, action, language="es"):
        return self.client.post(
            f"/api/admin/broadcasts/{broadcast.pk}/translations/",
            data=json.dumps({"action": action, "language": language}),
            content_type="application/json",
        )

    def test_request_files_one_job_with_the_source(self):
        b = _campaign()
        res = self._act(b, "request")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["translations"]["es"]["state"], "requested")
        issue = self.gh.filed[0]
        self.assertEqual(issue["title"], f"[translation] email:broadcast-{b.pk} -> es")
        self.assertEqual(issue["labels"], ["translation-job"])
        payload = self.gh.payload()
        self.assertEqual(payload["blocks"], BLOCKS)
        self.assertEqual(payload["subject"], "Wait for the Lord this Advent")
        # Pressing again doesn't file a second job.
        self._act(b, "request")
        self.assertEqual(len(self.gh.filed), 1)
        self.assertTrue(
            AdminAction.objects.filter(action=AdminAction.Action.EMAIL_TRANSLATION_REQUEST).exists()
        )

    @override_settings(GITHUB_TRANSLATION_TOKEN="")
    def test_request_explains_a_missing_token(self):
        res = self._act(_campaign(), "request")
        self.assertEqual(res.status_code, 409)
        self.assertIn("GITHUB_TRANSLATION_TOKEN", res.json()["detail"])

    def test_request_refuses_english_and_unknown_languages(self):
        b = _campaign()
        self.assertEqual(self._act(b, "request", "en").status_code, 409)
        self.assertEqual(self._act(b, "request", "xx").status_code, 409)

    def test_draft_round_trip_gates_sending_until_approved(self):
        b = _campaign()
        self._act(b, "request")
        # Nothing back yet: stays requested, nothing changes.
        res = self._act(b, "fetch")
        self.assertEqual(res.json()["translations"]["es"]["state"], "requested")

        self.gh.comments = [
            {"body": "Claiming this."},
            {"body": reply_comment(_spanish(self.gh.payload()))},
        ]
        res = self._act(b, "fetch")
        self.assertEqual(res.status_code, 200, res.content)
        b.refresh_from_db()
        self.assertEqual(b.translations["es"]["state"], "draft")
        self.assertEqual(b.subject["es"], "Espera en el Señor este Adviento")
        self.assertEqual(b.content["es"]["blocks"][2]["slug"], "the-inner-chamber")
        self.assertEqual(b.content["es"]["blocks"][2]["label"], "Empieza a leer")

        # An unapproved AI draft blocks sending.
        errors = {c["code"] for c in run_checks(b) if c["level"] == "error"}
        self.assertIn("translation:es", errors)
        send = self.client.post(
            f"/api/admin/broadcasts/{b.pk}/action/",
            data=json.dumps({"action": "send"}),
            content_type="application/json",
        )
        self.assertEqual(send.status_code, 409)

        res = self._act(b, "approve")
        self.assertEqual(res.json()["translations"]["es"]["state"], "approved")
        b.refresh_from_db()
        errors = {c["code"] for c in run_checks(b) if c["level"] == "error"}
        self.assertNotIn("translation:es", errors)

    def test_a_reply_that_changes_more_than_words_is_refused(self):
        b = _campaign()
        self._act(b, "request")
        bad = _spanish(self.gh.payload())
        bad["blocks"][2]["slug"] = "another-book"
        self.gh.comments = [{"body": reply_comment(bad)}]
        res = self._act(b, "fetch")
        self.assertEqual(res.status_code, 409)
        self.assertIn("slug", res.json()["detail"])
        b.refresh_from_db()
        self.assertNotIn("es", b.content)
        self.assertEqual(b.translations["es"]["state"], "requested")

    def test_editing_the_source_marks_the_draft_stale(self):
        b = _campaign()
        self._act(b, "request")
        self.gh.comments = [{"body": reply_comment(_spanish(self.gh.payload()))}]
        self._act(b, "fetch")
        b.refresh_from_db()
        b.subject = {**b.subject, "en": "A new subject"}
        b.save()
        warnings = {c["code"] for c in run_checks(b) if c["level"] == "warning"}
        self.assertIn("translation-stale:es", warnings)

    def test_approve_needs_a_draft(self):
        self.assertEqual(self._act(_campaign(), "approve").status_code, 409)


def _fake_client(answer):
    message = SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(answer))]
    )
    return SimpleNamespace(messages=SimpleNamespace(create=mock.Mock(return_value=message)))


class TranslateWorkerTests(TestCase):
    def _payload(self):
        b = _campaign()
        return jobs.source_payload(Broadcast.objects.get(pk=b.pk), "en", "es")

    def test_only_words_are_sent_and_replaced(self):
        payload = self._payload()
        client = _fake_client(
            {"subject": "Asunto", "preheader": "Vista", "texts": ["T1", "T2", "T3", "T4"]}
        )
        reply = translate_payload(client, payload)
        sent = json.loads(client.messages.create.call_args.kwargs["messages"][0]["content"].split("\n\n", 1)[1])
        self.assertEqual(len(sent["texts"]), 4)  # heading, text, card label, button label
        self.assertEqual([b["type"] for b in reply["blocks"]], [b["type"] for b in BLOCKS])
        self.assertEqual(reply["blocks"][2]["slug"], "the-inner-chamber")
        self.assertEqual(reply["blocks"][3]["path"], "plans/humility-12-days/")
        self.assertEqual(reply["blocks"][0]["text"], "T1")
        # The reply validates as a words-only draft against the source.
        jobs.validate_draft(BLOCKS, reply)

    def test_a_short_answer_is_an_error(self):
        client = _fake_client({"subject": "A", "preheader": "", "texts": ["only one"]})
        with self.assertRaises(TranslateError):
            translate_payload(client, self._payload())

    def test_command_prints_a_comment_fetch_can_read(self):
        payload = self._payload()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("Issue body\n\n```json\n" + json.dumps(payload) + "\n```\n")
        client = _fake_client(
            {"subject": "Asunto", "preheader": "", "texts": ["a", "b", "c", "d"]}
        )
        out = io.StringIO()
        with mock.patch("emails.management.commands.translate_email_job.anthropic.Anthropic", return_value=client):
            call_command("translate_email_job", f.name, stdout=out)
        text = out.getvalue()
        self.assertTrue(text.startswith(jobs.MARKER))
        parsed = json.loads(jobs._JSON_BLOCK.search(text).group(1))
        self.assertEqual(parsed["subject"], "Asunto")


def _write_json(obj) -> str:
    """A temp file holding ``obj`` as JSON; returns its path."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(json.dumps(obj))
    return f.name


class InSessionWorkerTests(TestCase):
    """A worker session translates without an API key: print, translate, assemble."""

    def _job_file(self):
        b = _campaign()
        return _write_json(jobs.source_payload(Broadcast.objects.get(pk=b.pk), "en", "es"))

    def test_print_then_answer(self):
        job = self._job_file()
        out = io.StringIO()
        call_command("translate_email_job", job, "--print-texts", stdout=out)
        texts = json.loads(out.getvalue().split("\n\n", 1)[1])
        self.assertEqual(texts["texts"][0], "Wait for the Lord")
        answer = _write_json({"subject": "Asunto", "preheader": "", "texts": ["a", "b", "c", "d"]})
        out = io.StringIO()
        call_command("translate_email_job", job, "--answer", answer, stdout=out)
        self.assertTrue(out.getvalue().startswith(jobs.MARKER))

    def test_a_wrong_answer_is_refused(self):
        job = self._job_file()
        answer = _write_json({"subject": "", "preheader": "", "texts": ["a", "b", "c", "d"]})
        with self.assertRaises(CommandError):
            call_command("translate_email_job", job, "--answer", answer, stdout=io.StringIO())
