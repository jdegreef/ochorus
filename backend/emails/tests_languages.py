"""One email, every language (emails/languages.py): the per-language overview,
asking for every missing language at once, and checking for every draft."""

from __future__ import annotations

import json
from unittest import mock

from django.test import TestCase, override_settings

from library import languages as registry
from library.models import Author, Book, Language

from . import translation_jobs as jobs
from .audience import resolve
from .models import Broadcast, EmailSubscription
from .tests import _broadcast, _make_profile
from .tests_translation import _GitHub

BLOCKS = [
    {"type": "heading", "text": "Hello"},
    {"type": "text", "text": "A new classic is live."},
    {"type": "book", "slug": "humility", "label": ""},
]


def _live(*codes):
    Language.objects.exclude(code__in=codes).update(status=Language.Status.DRAFT)
    for code in codes:
        Language.objects.update_or_create(code=code, defaults={"name": code.upper(), "native_name": {"en": "English"}.get(code, code), "status": Language.Status.LIVE})
    registry.invalidate()


@override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t", GITHUB_TRANSLATION_REPO="x/y")
class LanguagesTests(TestCase):
    def setUp(self):
        _live("en", "es", "fr")
        self.addCleanup(registry.invalidate)  # the registry cache outlives the test's rows
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        Book.objects.create(author=murray, slug="humility", language="en", title="Humility")
        Book.objects.create(author=murray, slug="humility", language="es", title="Humildad")
        self.gh = _NumberedGitHub()
        patcher = mock.patch.multiple(
            "emails.translation_jobs.requests", post=self.gh.post, get=self.gh.get, patch=self.gh.patch
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _campaign(self):
        return _broadcast(subject={"en": "Hello"}, content={"en": {"preheader": "", "blocks": BLOCKS}})

    def _rows(self, b):
        b = Broadcast.objects.get(pk=b.pk)
        res = self.client.get(f"/api/admin/broadcasts/{b.pk}/")
        return {r["code"]: r for r in res.json()["languages"]["rows"]}

    def test_overview_states_readers_and_gaps(self):
        _make_profile(email="fr1@example.com", locale="fr")
        en = _make_profile(email="x@example.com", locale="en")
        EmailSubscription.objects.create(profile=en, email_locale="fr")
        b = self._campaign()
        rows = self._rows(b)
        self.assertEqual(rows["en"]["status"], "source")
        self.assertEqual(rows["es"]["status"], "missing")
        self.assertEqual(rows["fr"]["readers"], 2)
        self.assertEqual(rows["fr"]["gaps"], [{"type": "book", "slug": "humility"}])
        self.assertEqual(rows["es"]["gaps"], [])

    def test_request_all_then_fetch_all(self):
        b = self._campaign()
        res = self.client.post(
            f"/api/admin/broadcasts/{b.pk}/translations/",
            data=json.dumps({"action": "request_all"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], {"es": "requested", "fr": "requested"})
        self.assertEqual(len(self.gh.filed), 2)
        rows = {r["code"]: r["status"] for r in res.json()["languages"]["rows"]}
        self.assertEqual((rows["es"], rows["fr"]), ("requested", "requested"))

        # Spanish comes back; French isn't back yet.
        b.refresh_from_db()
        es_issue = b.translations["es"]["issue"]
        reply = _spanish_for(jobs.job_payload(b, "en", "es"))
        with mock.patch.object(jobs, "_replies", side_effect=lambda n: iter([reply] if n == es_issue else [])):
            res = self.client.post(
                f"/api/admin/broadcasts/{b.pk}/translations/",
                data=json.dumps({"action": "fetch_all"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(sorted(res.json()["outcome"].values()), ["draft", "requested"])

    def test_strict_locale_is_editable(self):
        b = self._campaign()
        self.client.patch(
            f"/api/admin/broadcasts/{b.pk}/", data=json.dumps({"strict_locale": True}), content_type="application/json"
        )
        b.refresh_from_db()
        self.assertTrue(b.strict_locale)

    def test_email_language_takes_a_list(self):
        fr = _make_profile(email="fr@example.com", locale="fr")
        es = _make_profile(email="es@example.com", locale="es")
        _make_profile(email="en@example.com", locale="en")
        self.assertEqual(set(resolve({"email_language": ["fr", "es"]})), {fr, es})


class _NumberedGitHub(_GitHub):
    """Each filed issue gets its own number."""

    def post(self, url, json=None, **kw):
        self.filed.append(json)
        number = 4000 + len(self.filed)
        return mock.Mock(
            status_code=201,
            raise_for_status=lambda: None,
            json=lambda: {"number": number, "html_url": f"https://github.com/x/y/issues/{number}"},
        )


def _spanish_for(payload):
    texts = ["Hola", "Un nuevo clásico está disponible."]
    return {**jobs.check_answer(payload, {"subject": "Hola", "preheader": "", "texts": texts})}



class ReviewFixTests(TestCase):
    def setUp(self):
        _live("en", "es", "fr")
        self.addCleanup(registry.invalidate)

    def test_an_unreviewed_ai_draft_is_never_the_source(self):
        from . import languages

        b = _broadcast(
            subject={"es": "Hola", "en": "Hello"},
            content={"es": {"blocks": [{"type": "text", "text": "Hola a todos"}]}, "en": {"blocks": [{"type": "text", "text": "Hello all"}]}},
        )
        b.translations = {"en": {"state": "draft", "issue": 1, "url": "", "source_locale": "es", "source_digest": "x"}}
        b.save()
        overview = languages.overview(b)
        rows = {r["code"]: r for r in overview["rows"]}
        self.assertEqual(overview["source"], "es")
        self.assertEqual(rows["en"]["status"], "draft")
        self.assertFalse(rows["en"]["sendable"])
        self.assertEqual(rows["es"]["status"], "source")

    @override_settings(GITHUB_TRANSLATION_TOKEN="t", GITHUB_TRANSLATION_REPO="x/y")
    def test_request_all_stops_when_github_is_down(self):
        import requests

        from . import languages

        b = _broadcast(subject={"en": "Hello"}, content={"en": {"blocks": [{"type": "text", "text": "Hello all"}]}})
        with mock.patch("emails.translation_jobs.file_issue", side_effect=requests.ConnectionError) as filed:
            outcome = languages.request_all(b)
        self.assertEqual(filed.call_count, 1)
        self.assertEqual(set(outcome), {"es", "fr"})

    def test_a_malformed_email_language_matches_nobody(self):
        _make_profile(email="a@example.com")
        self.assertEqual(list(resolve({"email_language": 5})), [])

    def test_readers_in_a_language_that_isnt_live_get_a_row(self):
        from . import languages

        de = _make_profile(email="de@example.com", locale="en")
        EmailSubscription.objects.create(profile=de, email_locale="de")
        b = _broadcast(subject={"en": "Hello"}, content={"en": {"blocks": [{"type": "text", "text": "Hello"}]}})
        rows = {r["code"]: r for r in languages.overview(b)["rows"]}
        self.assertEqual(rows["de"]["readers"], 1)
