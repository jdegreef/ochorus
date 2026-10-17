"""Merge tags (emails/merge_tags.py): values per reader, fallbacks, sentences
that drop out, subjects, previews, checks, translation and batch sends."""

from __future__ import annotations

import json
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from library.models import Author, Book, Plan, PlanDay
from reading.models import PlanProgress, ReadingProgress, WorkKind

from . import merge_tags
from .broadcasts import send_broadcast
from .models import Broadcast, EmailSubscription
from .preflight import run as run_checks
from .rendering import render_broadcast
from .tests import SENDING, _broadcast, _make_profile

V = {"first_name": "Ana", "last_book": "Humility", "plan_name": None, "plan_day": None, "books_finished": None}


class FillTests(SimpleTestCase):
    def test_a_tag_with_a_value(self):
        self.assertEqual(merge_tags.fill_line("Hi {first_name}", V, "en"), "Hi Ana")
        self.assertEqual(merge_tags.fill_line("Hi {name}", V, "en"), "Hi Ana")  # the old spelling

    def test_fallback_then_default_then_drop(self):
        self.assertEqual(merge_tags.fill_line("{plan_name|a plan}", V, "en"), "a plan")
        self.assertEqual(merge_tags.fill_line("Hi {first_name}", {**V, "first_name": None}, "es"), "Hi amigo")
        self.assertIsNone(merge_tags.fill_line("Day {plan_day}", V, "en"))

    def test_a_sentence_with_nothing_to_say_drops_out(self):
        text = "Dear {first_name}, welcome back. You are on day {plan_day} of {plan_name}! {last_book} is waiting."
        self.assertEqual(merge_tags.fill_paragraph(text, V, "en"), "Dear Ana, welcome back. Humility is waiting.")

    def test_sentences_end_in_other_scripts(self):
        text = "Bonjour {first_name}。Jour {plan_day}。Fin."
        self.assertEqual(merge_tags.fill_paragraph(text, V, "en"), "Bonjour Ana。Fin.")

    def test_unknown_braces_are_left_alone(self):
        self.assertEqual(merge_tags.fill_line("A {weird} title", V, "en"), "A {weird} title")
        self.assertEqual(merge_tags.unknown_in("A {weird} title {name}"), {"{weird}"})

    def test_subject_drops_the_tag_and_tidies(self):
        self.assertEqual(merge_tags.fill_subject("{plan_name}: your next day", V, "en"), "your next day")
        self.assertEqual(merge_tags.fill_subject("Keep going, {plan_name}!", V, "en"), "Keep going!")
        self.assertEqual(merge_tags.fill_subject("{first_name}, one to read next", V, "en"), "Ana, one to read next")

    def test_tag_names(self):
        self.assertEqual(merge_tags.tag_names("{plan_day|1} of {plan_name}"), ["plan_day", "plan_name"])


class ValueTests(TestCase):
    def setUp(self):
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        Book.objects.create(author=murray, slug="humility", language="en", title="Humility")
        Book.objects.create(author=murray, slug="humility", language="es", title="Humildad")
        Book.objects.create(author=murray, slug="surrender", language="en", title="Absolute Surrender")
        plan = Plan.objects.create(slug="prayer", language="en", title="Thirty days of prayer")
        Book.objects.create(author=murray, slug="b", language="en", title="B")
        for day in (1, 2, 3):
            PlanDay.objects.create(plan=plan, day=day, book_slug="b", chapter_order=day)
        self.reader = _make_profile()

    def _values(self, profile=None, lang="en"):
        return merge_tags.values_for(profile or self.reader, lang, first_name="Ana", needed=set(merge_tags.TAGS))

    def test_a_reader_with_nothing_yet(self):
        v = self._values()
        self.assertEqual((v["last_book"], v["plan_name"], v["plan_day"], v["books_finished"]), (None, None, None, None))

    def test_a_reader_with_reading(self):
        now = timezone.now()
        ReadingProgress.objects.create(profile=self.reader, kind=WorkKind.BOOK, book_slug="surrender", language="en", finished_at=now)
        ReadingProgress.objects.create(profile=self.reader, kind=WorkKind.BOOK, book_slug="humility", language="es")
        PlanProgress.objects.create(profile=self.reader, plan_slug="prayer", started_at=now, done=[1])
        v = self._values()
        self.assertEqual(v["last_book"], "Humildad")  # the edition they read
        self.assertEqual(v["books_finished"], "1")
        self.assertEqual((v["plan_name"], v["plan_day"]), ("Thirty days of prayer", "2"))
        self.assertEqual(v["language"], "English")

    def test_a_finished_plan_has_no_next_day(self):
        PlanProgress.objects.create(profile=self.reader, plan_slug="prayer", started_at=timezone.now(), done=[1, 2, 3])
        self.assertIsNone(self._values()["plan_day"])

    def test_a_plan_not_in_the_emails_language_says_nothing(self):
        PlanProgress.objects.create(profile=self.reader, plan_slug="prayer", started_at=timezone.now(), done=[])
        self.assertIsNone(self._values(lang="es")["plan_name"])


@SENDING
class RenderTests(TestCase):
    def setUp(self):
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        Book.objects.create(author=murray, slug="humility", language="en", title="Humility")

    def test_render_drops_and_fills(self):
        reader = _make_profile(name="Ana Reader")
        sub = EmailSubscription.objects.create(profile=reader)
        ReadingProgress.objects.create(profile=reader, kind=WorkKind.BOOK, book_slug="humility", language="en")
        b = _broadcast(
            subject={"en": "{first_name}, back to {last_book}"},
            content={
                "en": {
                    "blocks": [
                        {"type": "heading", "text": "Day {plan_day}"},
                        {"type": "text", "text": "Dear {first_name}. You are on day {plan_day}. {last_book} waits."},
                        {"type": "button", "label": "Open {last_book}", "path": "books"},
                    ]
                }
            },
        )
        rendered = render_broadcast(b, reader, sub)
        self.assertEqual(rendered.subject, "Ana, back to Humility")
        self.assertNotIn("Day ", rendered.html)
        self.assertIn("Dear Ana. Humility waits.", rendered.html)
        self.assertIn("Open Humility", rendered.html)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_a_batch_send_looks_up_facts_once(self, send):
        readers = [_make_profile(email=f"r{i}@example.com", name=f"R{i}") for i in range(4)]
        for r in readers[:2]:
            ReadingProgress.objects.create(profile=r, kind=WorkKind.BOOK, book_slug="humility", language="en")
        b = _broadcast(subject={"en": "Hi"}, content={"en": {"blocks": [{"type": "text", "text": "Hi. {last_book} waits."}]}})
        with mock.patch.object(merge_tags, "_facts", wraps=merge_tags._facts) as facts:
            send_broadcast(Broadcast.objects.get(pk=b.pk))
        self.assertEqual(facts.call_count, 1)
        html = {c.kwargs["to"]: c.kwargs["html"] for c in send.call_args_list}
        self.assertIn("Humility waits", html["r0@example.com"])
        self.assertNotIn("waits", html["r3@example.com"])


class CheckTests(TestCase):
    def test_unknown_tags_and_vanishing_subject_tags_warn(self):
        b = _broadcast(
            subject={"en": "Back to {last_book}"},
            content={"en": {"blocks": [{"type": "text", "text": "Hi {firstname}"}]}},
        )
        levels = {c["code"]: c["level"] for c in run_checks(b)}
        self.assertEqual(levels["tags:en"], "warning")
        self.assertEqual(levels["subject-tags:en"], "warning")

    def test_a_fallback_quiets_the_subject_warning(self):
        b = _broadcast(subject={"en": "Back to {last_book|a classic}"}, content={"en": {"blocks": [{"type": "text", "text": "Hi"}]}})
        self.assertNotIn("subject-tags:en", {c["code"] for c in run_checks(b)})


class TranslationTests(SimpleTestCase):
    def test_a_translation_must_keep_its_tags(self):
        from .translation_jobs import TranslationJobError, check_answer

        payload = {"broadcast": 1, "target": "es", "source_digest": "x", "subject": "Hi {first_name}", "preheader": "", "texts": ["Day {plan_day|1}"]}
        ok = check_answer(payload, {"subject": "Hola {first_name}", "texts": ["Día {plan_day|uno}"]})
        self.assertEqual(ok["texts"], ["Día {plan_day|uno}"])
        with self.assertRaises(TranslationJobError):
            check_answer(payload, {"subject": "Hola {nombre}", "texts": ["Día {plan_day}"]})
        with self.assertRaises(TranslationJobError):
            check_answer(payload, {"subject": "Hola {first_name}", "texts": ["Día"]})


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class ApiTests(TestCase):
    def test_tags_and_preview_modes(self):
        tags = self.client.get("/api/admin/emails/merge-tags/").json()["tags"]
        self.assertIn("plan_day", [t["key"] for t in tags])

        def preview(reader):
            return self.client.post(
                "/api/admin/emails/preview/",
                data=json.dumps(
                    {"locale": "en", "subject": "{first_name}", "content": {"blocks": [{"type": "text", "text": "Hi. Day {plan_day}."}]}, "as": reader}
                ),
                content_type="application/json",
            ).json()

        sample = preview("sample")
        self.assertEqual(sample["subject"], "Sarah")
        self.assertIn("Day 12.", sample["html"])
        new = preview("new")
        self.assertEqual(new["subject"], "friend")
        self.assertNotIn("Day", new["html"])
