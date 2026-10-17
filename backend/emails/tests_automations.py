"""Automations (emails/automations.py): triggers, enrolment from the switch-on
baseline, waits, conditions, exits, the email step (consent, the 20-hour gap,
language, approval), send-once, and the admin API."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from library.models import AdminAction, Author, Book
from reading.models import PlanProgress, ReadingProgress, WorkKind

from . import automations as auto
from .models import (
    Automation,
    AutomationEmail,
    AutomationRun,
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    RunStatus,
    SendStatus,
)
from .tests import SENDING, _make_profile

EN = {"en": {"preheader": "", "blocks": [{"type": "text", "text": "Hello {first_name}."}]}}


def _flow(trigger, steps_fn, *, exit_=None, enabled=True, at=None):
    a = Automation.objects.create(name="Flow", trigger=trigger)
    email = AutomationEmail.objects.create(automation=a, subject={"en": "Hi"}, content=EN)
    a.steps = steps_fn(email)
    a.exit = exit_ or []
    if enabled:
        a.enabled = True
        a.enabled_at = a.scanned_to = at or timezone.now() - timedelta(days=1)
    a.save()
    return a, email


def _finish(profile, slug, when):
    return ReadingProgress.objects.create(
        profile=profile, kind=WorkKind.BOOK, book_slug=slug, language="en", finished_at=when
    )


@SENDING
@mock.patch("emails.sending.send_email", return_value="rid")
class EngineTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        Book.objects.create(author=murray, slug="surrender", language="en", title="Absolute Surrender")
        Book.objects.create(author=murray, slug="humility", language="en", title="Humility")
        self.reader = _make_profile(name="Ana Reader")

    def test_trigger_wait_condition_email(self, send):
        a, email = _flow(
            {"type": "finished_book", "author": "murray", "book": ""},
            lambda e: [
                {"id": "w", "type": "wait", "days": 2, "hours": 0},
                {"id": "c", "type": "condition", "check": "started_book", "book": "humility", "negate": True},
                {"id": "e", "type": "email", "email": e.pk},
            ],
        )
        _finish(self.reader, "surrender", self.now - timedelta(hours=1))
        self.assertEqual(auto.run_due(self.now)["enrolled"], 1)
        run = AutomationRun.objects.get()
        self.assertEqual(run.step_index, 1)  # past the wait, waiting
        self.assertEqual(run.context["book"], "surrender")
        send.assert_not_called()

        later = self.now + timedelta(days=2, minutes=1)
        auto.run_due(later)
        run.refresh_from_db()
        self.assertEqual(run.status, RunStatus.DONE)
        self.assertEqual(send.call_count, 1)
        self.assertIn("Hello Ana.", send.call_args.kwargs["html"])
        message = EmailMessage.objects.get()
        self.assertEqual((message.kind, message.lifecycle_step), (EmailKind.LIFECYCLE, f"automation:{a.pk}"))

        # Never twice: a second trigger doesn't re-enrol, a re-run doesn't re-send.
        _finish(self.reader, "humility", later)
        auto.run_due(later + timedelta(days=3))
        self.assertEqual(AutomationRun.objects.count(), 1)
        self.assertEqual(send.call_count, 1)

    def test_a_failed_condition_ends_the_run(self, send):
        _flow(
            {"type": "finished_book", "author": "", "book": "surrender"},
            lambda e: [
                {"id": "c", "type": "condition", "check": "started_book", "book": "humility", "negate": True},
                {"id": "e", "type": "email", "email": e.pk},
            ],
        )
        _finish(self.reader, "surrender", self.now - timedelta(hours=1))
        ReadingProgress.objects.create(profile=self.reader, kind=WorkKind.BOOK, book_slug="humility", language="en")
        auto.run_due(self.now)
        run = AutomationRun.objects.get()
        self.assertEqual(run.status, RunStatus.EXITED)
        send.assert_not_called()

    def test_nothing_from_before_it_was_switched_on(self, send):
        _flow({"type": "finished_book"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], at=self.now)
        _finish(self.reader, "surrender", self.now - timedelta(days=3))
        self.assertEqual(auto.run_due(self.now + timedelta(minutes=1))["enrolled"], 0)

    def test_off_enrols_nobody(self, send):
        _flow({"type": "signed_up"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], enabled=False)
        auto.run_due(self.now)
        self.assertFalse(AutomationRun.objects.exists())

    def test_the_20_hour_gap_holds_an_email_back(self, send):
        _flow({"type": "signed_up"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], at=self.now - timedelta(days=2))
        EmailMessage.objects.create(
            recipient=self.reader, to_email="x@example.com", kind=EmailKind.LIFECYCLE, lifecycle_step="welcome",
            idempotency_key="k", status=SendStatus.SENT, sent_at=self.now - timedelta(hours=2),
        )
        self.now += timedelta(minutes=1)  # the reader signed up after setUp's clock
        auto.run_due(self.now)
        run = AutomationRun.objects.get()
        self.assertEqual(run.status, RunStatus.ACTIVE)
        self.assertEqual(run.step_index, 0)
        sent_at = EmailMessage.objects.get(idempotency_key="k").sent_at
        self.assertEqual(run.next_at, sent_at + timedelta(hours=20))
        send.assert_not_called()
        auto.run_due(self.now + timedelta(hours=19))
        self.assertEqual(send.call_count, 1)

    def test_consent_language_and_approval(self, send):
        a, email = _flow({"type": "signed_up"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], at=self.now - timedelta(days=2))
        es = _make_profile(email="es@example.com", locale="es")
        muted = _make_profile(email="muted@example.com")
        EmailSubscription.objects.create(profile=muted, stream_prefs={"onboarding": False})
        email.subject["es"] = "Hola"
        email.content["es"] = {"preheader": "", "blocks": [{"type": "text", "text": "Hola."}]}
        email.translations = {"es": {"state": "draft", "issue": 1, "url": "", "source_locale": "en", "source_digest": "x"}}
        email.save()
        auto.run_due(self.now + timedelta(minutes=1))  # they signed up after setUp's clock
        self.assertEqual([c.kwargs["to"] for c in send.call_args_list], ["reader@example.com"])
        self.assertEqual(AutomationRun.objects.get(profile=es).status, RunStatus.DONE)  # skipped, carried on

    def test_exit_and_opened_last(self, send):
        a, email = _flow(
            {"type": "started_plan", "plan": ""},
            lambda e: [
                {"id": "e", "type": "email", "email": e.pk},
                {"id": "w", "type": "wait", "days": 1, "hours": 0},
                {"id": "c", "type": "condition", "check": "opened_last", "negate": True},
                {"id": "w2", "type": "wait", "days": 1, "hours": 0},
            ],
            exit_=[{"check": "finished_books", "count": 1, "negate": False}],
        )
        PlanProgress.objects.create(profile=self.reader, plan_slug="p", started_at=self.now - timedelta(hours=1))
        auto.run_due(self.now)
        message = EmailMessage.objects.get()
        EmailEvent.objects.create(message=message, type=EventType.OPENED, occurred_at=self.now)
        auto.run_due(self.now + timedelta(days=1, minutes=1))
        run = AutomationRun.objects.get()
        self.assertEqual(run.status, RunStatus.EXITED)  # opened → "not opened" fails

    def test_went_quiet(self, send):
        _flow({"type": "went_quiet", "days": 7}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], at=self.now - timedelta(days=1))
        self.reader.last_seen_at = self.now - timedelta(days=7, hours=12)
        self.reader.save()
        self.assertEqual(auto.run_due(self.now)["enrolled"], 1)


class ProblemTests(TestCase):
    def test_a_flow_that_cant_run(self):
        a = Automation.objects.create(name="x", trigger={})
        issues = auto.problems(a)
        self.assertTrue(any("starts it" in i for i in issues))
        self.assertTrue(any("at least one email" in i for i in issues))

    def test_clean_steps(self):
        steps = auto.clean_steps(
            [{"type": "wait", "days": "3", "evil": 1}, {"type": "boom"}, {"type": "condition", "check": "active_within", "days": "x"}]
        )
        self.assertEqual(steps[0], {"id": "", "type": "wait", "days": 3, "hours": 0})
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[1]["days"], 7)


@SENDING
@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class ApiTests(TestCase):
    def _json(self, method, url, payload=None):
        return getattr(self.client, method)(url, data=json.dumps(payload or {}), content_type="application/json")

    def test_build_switch_on_and_freeze(self):
        res = self._json("post", "/api/admin/automations/", {"name": "Murray readers"})
        self.assertEqual(res.status_code, 201)
        pk = res.json()["id"]
        self.assertTrue(res.json()["problems"])
        email = self._json("post", f"/api/admin/automations/{pk}/emails/", {"template": "book-recommendation"}).json()
        self.assertEqual(email["locales"], ["en"])
        steps = [{"id": "a", "type": "wait", "days": 1}, {"id": "b", "type": "email", "email": email["id"]}]
        res = self._json("patch", f"/api/admin/automations/{pk}/", {"steps": steps, "trigger": {"type": "finished_book", "author": "murray"}})
        self.assertEqual(res.json()["trigger"], {"type": "finished_book", "author": "murray", "book": ""})
        # The starter's hint has to be replaced before it can go out.
        self.assertEqual(self._json("post", f"/api/admin/automations/{pk}/action/", {"action": "enable"}).status_code, 409)
        content = email["content"]
        for b in content["en"]["blocks"]:
            if b["type"] == "text" and b["text"].startswith("["):
                b["text"] = "Murray wrote this one as its companion."
        self._json("patch", f"/api/admin/automation-emails/{email['id']}/", {"content": content})
        self.assertEqual(self._json("post", f"/api/admin/automations/{pk}/action/", {"action": "enable"}).status_code, 200)
        self.assertTrue(Automation.objects.get(pk=pk).enabled)
        # On: the step list is frozen, the words aren't.
        self.assertEqual(self._json("patch", f"/api/admin/automations/{pk}/", {"steps": steps[1:]}).status_code, 409)
        self.assertEqual(self._json("patch", f"/api/admin/automation-emails/{email['id']}/", {"subject": {"en": "Next"}}).status_code, 200)
        listed = self.client.get("/api/admin/automations/").json()
        self.assertEqual(listed["automations"][0]["emails"], 1)
        self.assertIn("finished_book", [t["key"] for t in listed["vocabulary"]["triggers"]])
        actions = set(AdminAction.objects.values_list("action", flat=True))
        self.assertTrue({AdminAction.Action.EMAIL_AUTOMATION_SAVE, AdminAction.Action.EMAIL_AUTOMATION_SWITCH} <= actions)

    def test_enable_refuses_a_flow_with_problems(self):
        pk = self._json("post", "/api/admin/automations/", {"name": "x"}).json()["id"]
        res = self._json("post", f"/api/admin/automations/{pk}/action/", {"action": "enable"})
        self.assertEqual(res.status_code, 409)
        self.assertTrue(res.json()["problems"])

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_test_run_sends_every_email_to_me(self, send):
        a, _ = _flow({"type": "signed_up"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], enabled=False)
        _make_profile(email="admin@example.com")
        with mock.patch("emails.admin_automations.UserProfile.objects.filter") as find:
            find.return_value.first.return_value = _make_profile(email="me@example.com")
            res = self._json("post", f"/api/admin/automations/{a.pk}/action/", {"action": "test"})
        self.assertEqual(res.json()["sent"], 1)
        self.assertTrue(EmailMessage.objects.get(to_email="me@example.com").is_test)


class HintTests(TestCase):
    def test_an_email_left_with_a_template_hint_isnt_ready(self):
        a, email = _flow({"type": "signed_up"}, lambda e: [{"id": "e", "type": "email", "email": e.pk}], enabled=False)
        email.content = {"en": {"preheader": "", "blocks": [{"type": "text", "text": "[Your note.]"}]}}
        email.save()
        self.assertEqual(auto.ready_locales(email), [])
        self.assertTrue(any("template hint" in p for p in auto.problems(a)))
