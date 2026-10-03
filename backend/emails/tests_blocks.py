"""Tests for block-based campaign content: cleaning, per-language library
resolution (no English fallback), rendering, the block pre-send checks, and the
design API (preview, library picker, templates)."""

from __future__ import annotations

import json
from unittest import mock

from django.test import TestCase, override_settings

from library.models import AdminAction, Author, Book, Plan

from . import blocks as blocks_mod
from .models import Broadcast, EmailSubscription, EmailTemplate
from .preflight import run as run_checks
from .rendering import render_broadcast
from .tests import SENDING, _broadcast, _make_profile


def _library():
    murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
    for lang, title in (("en", "Humility"), ("es", "Humildad")):
        Book.objects.create(
            author=murray,
            slug="humility-2",
            language=lang,
            title=title,
            description="The beauty of holiness.",
            cover_url="/covers/art/humility-2.jpg",
        )
    Plan.objects.create(slug="humility-12-days", language="en", title="Humility in 12 Days")


def _content(*blocks):
    return {"blocks": list(blocks)}


BOOK = {"type": "book", "slug": "humility-2", "label": "Start reading"}


class CleanTests(TestCase):
    def test_keeps_known_types_and_fields_only(self):
        cleaned = blocks_mod.clean(
            [
                {"type": "heading", "text": "  Hi  ", "style": "red"},
                {"type": "script", "text": "<script>"},
                "not a block",
                {"type": "book", "slug": "humility-2", "label": 3},
            ]
        )
        self.assertEqual(
            cleaned,
            [
                {"type": "heading", "text": "Hi"},
                {"type": "book", "slug": "humility-2", "label": "3"},
            ],
        )

    def test_legacy_fields_read_as_blocks(self):
        blocks = blocks_mod.blocks_for(
            {"heading": "H", "paragraphs": ["a", "b"], "cta_label": "Go", "cta_path": "books"}
        )
        self.assertEqual([b["type"] for b in blocks], ["heading", "text", "text", "button"])


@SENDING
class RenderTests(TestCase):
    def setUp(self):
        _library()

    def _render(self, locale, *blocks, subject=None):
        profile = _make_profile(locale=locale, name="Ana Reader")
        sub = EmailSubscription.objects.create(profile=profile)
        b = _broadcast(
            subject={locale: subject or "Hello"},
            content={locale: _content(*blocks)},
        )
        return render_broadcast(b, profile, sub)

    def test_book_block_renders_the_readers_edition(self):
        html = self._render("es", BOOK).html
        self.assertIn("Humildad", html)
        self.assertIn("Andrew Murray", html)
        self.assertIn("https://ochorus.test/es/books/humility-2/", html)
        self.assertIn("https://ochorus.test/covers/art/humility-2.jpg", html)
        self.assertNotIn(">Humility<", html)

    def test_no_english_fallback_for_a_missing_edition(self):
        html = self._render("fr", {"type": "heading", "text": "Bonjour"}, BOOK).html
        self.assertIn("Bonjour", html)
        self.assertNotIn("Humility", html)
        self.assertNotIn("books/humility-2", html)

    def test_text_is_escaped_and_name_filled(self):
        html = self._render(
            "en",
            {"type": "text", "text": "Dear {name},\n\n<b>bold</b>"},
            {"type": "quote", "text": "Q", "attribution": "A"},
            {"type": "divider"},
        ).html
        self.assertIn("Dear Ana,", html)
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", html)
        self.assertNotIn("<b>bold</b>", html)

    def test_email_frame_shrinks_to_a_phone(self):
        # A fixed 600px frame made every email scroll sideways on a phone.
        html = self._render("en", {"type": "heading", "text": "H"}).html
        self.assertIn("width:100%; max-width:600px", html)
        self.assertNotRegex(html, r"[^-]width:600px")

    def test_rtl_language_sets_direction(self):
        html = self._render("ar", {"type": "quote", "text": "Q"}).html
        self.assertIn('dir="rtl"', html)
        self.assertIn("border-right:3px", html)


class BlockPreflightTests(TestCase):
    def setUp(self):
        _library()
        _make_profile()

    def _codes(self, broadcast, level):
        return {c["code"] for c in run_checks(broadcast) if c["level"] == level}

    def test_missing_edition_warns_and_unknown_work_errors(self):
        b = _broadcast(
            subject={"en": "Hi", "fr": "Salut"},
            content={
                "en": _content({"type": "book", "slug": "no-such-book"}),
                "fr": _content({"type": "heading", "text": "H"}, BOOK),
            },
        )
        self.assertIn("library:en:0", self._codes(b, "error"))
        self.assertIn("library:fr:1", self._codes(b, "warning"))

    def test_unchosen_library_block_and_empty_email_error(self):
        b = _broadcast(content={"en": _content({"type": "plan", "slug": ""})})
        errors = self._codes(b, "error")
        self.assertIn("library:en:0", errors)
        self.assertIn("body:en", errors)


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class DesignApiTests(TestCase):
    def setUp(self):
        _library()

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    @override_settings(PUBLIC_SITE_URL="https://ochorus.test", API_PUBLIC_URL="https://api.test")
    def test_preview_renders_unsaved_content(self):
        res = self._post(
            "/api/admin/emails/preview/",
            {"locale": "es", "subject": "Hola", "content": _content(BOOK)},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Humildad", res.json()["html"])
        self.assertEqual(res.json()["subject"], "Hola")

    def test_library_search_groups_editions(self):
        rows = self.client.get("/api/admin/emails/library/?type=book&q=humil").json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], "humility-2")
        self.assertEqual(rows[0]["title"], "Humility")
        self.assertEqual(sorted(rows[0]["languages"]), ["en", "es"])
        plans = self.client.get("/api/admin/emails/library/?type=plan").json()["results"]
        self.assertEqual(plans[0]["slug"], "humility-12-days")
        self.assertEqual(self.client.get("/api/admin/emails/library/?type=x").status_code, 400)

    def test_save_content_cleans_blocks(self):
        b = _broadcast()
        res = self.client.patch(
            f"/api/admin/broadcasts/{b.pk}/",
            data=json.dumps({"content": {"en": _content({"type": "evil"}, BOOK)}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.content["en"]["blocks"], [BOOK])

    def test_templates_from_broadcast_list_and_delete(self):
        b = _broadcast(content={"en": _content(BOOK)})
        res = self._post("/api/admin/emails/templates/", {"name": "Book launch", "from_broadcast": b.pk})
        self.assertEqual(res.status_code, 201)
        tid = res.json()["id"]
        listed = self.client.get("/api/admin/emails/templates/").json()["templates"]
        self.assertEqual(listed[0]["content"]["en"]["blocks"], [BOOK])
        self.assertEqual(self._post("/api/admin/emails/templates/", {}).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/admin/emails/templates/{tid}/").status_code, 204)
        self.assertFalse(EmailTemplate.objects.exists())
        actions = set(AdminAction.objects.values_list("action", flat=True))
        self.assertIn(AdminAction.Action.EMAIL_TEMPLATE_SAVE, actions)
        self.assertIn(AdminAction.Action.EMAIL_TEMPLATE_DELETE, actions)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_a_block_broadcast_sends_per_language(self, send):
        _make_profile(email="es@example.com", locale="es")
        b = _broadcast(subject={"es": "Hola"}, content={"es": _content(BOOK)})
        from .broadcasts import send_broadcast

        send_broadcast(Broadcast.objects.get(pk=b.pk))
        self.assertIn("Humildad", send.call_args.kwargs["html"])
