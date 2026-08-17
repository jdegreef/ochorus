"""A licensed Bible must be credited, and credited in the place readers look.

Three facts have to agree, and each one on its own is worthless:

* ``language_seed.py`` declares that a language's Bible is licensed,
* ``Language.bible_attribution`` carries the credit line the licence asks for,
* the reader's footer actually renders it (``frontend/src/lib/bibleCredit.ts``).

The middle one is the only one a Python test can see directly, so the third is
checked by reading the frontend module as text. That is the same trick, in
reverse, that ``readiness.py`` already uses for the UI catalogues: the API image
is built from ``backend/`` alone, so the file is absent in production and the
check skips there — but CI runs both halves out of one checkout, which is where
a mismatch would be introduced and therefore where it needs to fail.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import readiness
from .admin_views import content
from .translation import GLOSSARY_TERMS
from .language_seed import SEED_LANGUAGES
from .models import Language
from .readiness import FAIL, PASS, SKIPPED, Check, _attribution_check

CREDIT_TS = (
    Path(settings.BASE_DIR).resolve().parent / "frontend" / "src" / "lib" / "bibleCredit.ts"
)


def _seed_attributions() -> dict[str, str]:
    return {
        code: cfg["bible_attribution"]
        for code, cfg in SEED_LANGUAGES.items()
        if cfg.get("bible_attribution")
    }


class SeedDeclarationTests(TestCase):
    def test_a_licensed_bible_declares_a_credit_line(self):
        """`bible_licence` without `bible_attribution` is the gap this exists to close."""
        missing = [
            code
            for code, cfg in SEED_LANGUAGES.items()
            if cfg.get("bible_licence") and not cfg.get("bible_attribution", "").strip()
        ]
        self.assertEqual(missing, [], "licensed Bible with no credit line configured")

    def test_a_credit_line_declares_the_licence_it_discharges(self):
        """And the reverse: a credit nobody can trace to a licence is decoration."""
        orphans = [
            code
            for code, cfg in SEED_LANGUAGES.items()
            if cfg.get("bible_attribution") and not cfg.get("bible_licence")
        ]
        self.assertEqual(orphans, [])

    def test_hindi_is_the_licensed_one(self):
        """Pinned deliberately. Not because Hindi is special, but because a second
        licensed Bible arriving unnoticed is exactly the change that should make
        someone stop and read this file."""
        self.assertEqual(sorted(_seed_attributions()), ["hi"])
        hi = SEED_LANGUAGES["hi"]
        self.assertEqual(hi["bible_licence"], "CC BY-SA 4.0")
        self.assertIn("Bridge Connectivity Solutions", hi["bible_attribution"])


class SeedToRegistryTests(TestCase):
    def test_seed_writes_the_credit_onto_the_row(self):
        call_command("seed_languages")
        hi = Language.objects.get(code="hi")
        self.assertEqual(hi.bible_licence, "CC BY-SA 4.0")
        self.assertEqual(hi.bible_attribution, SEED_LANGUAGES["hi"]["bible_attribution"])

    def test_public_domain_languages_stay_blank(self):
        call_command("seed_languages")
        for code in ("en", "es", "sw", "lg", "pt", "ar", "uk"):
            row = Language.objects.get(code=code)
            self.assertEqual(row.bible_licence, "", code)
            self.assertEqual(row.bible_attribution, "", code)

    def test_the_credit_is_re_asserted_after_a_hand_edit(self):
        """Identity, not workflow state — so a deploy repairs it rather than
        preserving whatever someone typed over it in the admin."""
        call_command("seed_languages")
        Language.objects.filter(code="hi").update(bible_attribution="oops")
        call_command("seed_languages")
        self.assertEqual(
            Language.objects.get(code="hi").bible_attribution,
            SEED_LANGUAGES["hi"]["bible_attribution"],
        )


class ReadinessTests(TestCase):
    """Called directly rather than through ``report()``: the Bible check beside
    it is the one check that touches the network, and this one must be testable
    from a machine that cannot reach api.takeroot.bible. ``test_report_includes``
    below covers the wiring, which is the only thing the indirection would add.
    """

    def _check(self, code: str):
        return _attribution_check(Language.objects.get(code=code))

    def setUp(self):
        call_command("seed_languages")

    def test_hindi_passes_once_the_credit_is_configured(self):
        self.assertEqual(self._check("hi").status, PASS)

    def test_hindi_cannot_go_live_with_the_credit_removed(self):
        Language.objects.filter(code="hi").update(bible_attribution="   ")
        check = self._check("hi")
        self.assertEqual(check.status, FAIL)
        self.assertTrue(check.blocking)
        self.assertIn("CC BY-SA 4.0", check.detail)

    def test_public_domain_and_source_languages_skip(self):
        for code in ("es", "ar", "en"):
            self.assertEqual(self._check(code).status, SKIPPED, code)

    def test_report_includes_the_check(self):
        """A check that is never run blocks nothing. Patching the Bible check
        keeps this offline — see the class docstring."""
        lang = Language.objects.get(code="hi")
        with mock.patch.object(
            readiness, "_bible_check", return_value=Check("bible", "Bible", PASS, "stub")
        ):
            keys = [c.key for c in readiness.report(lang).checks]
        self.assertIn("attribution", keys)


@override_settings(DEBUG=True)
class AdminCreatedLanguageTests(TestCase):
    """The gate has to hold for a language nobody wrote into the repo.

    This is where the original gap actually lived: the Add-a-language picker
    already knew which Bibles are licensed — it prints "· attribution" beside
    them — and then threw that away on submit. A language created from the admin
    with a CC-BY Bible would have sailed through readiness with nothing crediting
    it, because the only thing that knew was a comment in a Python file about a
    DIFFERENT language.

    `_verify_bible` is patched throughout: it calls api.takeroot.bible, which is
    not reachable from CI, and none of this is about whether the code resolves.
    """

    def setUp(self):
        self.client = APIClient()
        self.patch = mock.patch.object(
            content, "_verify_bible", return_value=(True, "stubbed")
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def _create(self, **extra):
        payload = {
            "code": "zu",
            "name": "Zulu",
            "native_name": "isiZulu",
            "bible_code": "zul-x",
            "bible_label": "Some Licensed Zulu Bible",
            "glossary": {t: "x" for t in GLOSSARY_TERMS},
            **extra,
        }
        return self.client.post("/api/admin/languages/", payload, format="json")

    def test_create_records_the_licence(self):
        res = self._create(bible_licence="CC BY 4.0")
        self.assertEqual(res.status_code, 201, res.data)
        row = Language.objects.get(code="zu")
        self.assertEqual(row.bible_licence, "CC BY 4.0")
        self.assertEqual(row.bible_attribution, "")

    def test_a_licensed_language_is_told_what_it_owes(self):
        res = self._create(bible_licence="CC BY 4.0")
        steps = " ".join(res.data["next_steps"])
        self.assertIn("CC BY 4.0", steps)
        self.assertIn("bibleCredit.ts", steps)

    def test_a_public_domain_language_is_not_nagged(self):
        res = self._create()
        self.assertNotIn("bibleCredit.ts", " ".join(res.data["next_steps"]))

    def test_it_cannot_go_live_until_the_credit_is_written(self):
        self._create(bible_licence="CC BY 4.0")
        lang = Language.objects.get(code="zu")
        self.assertEqual(_attribution_check(lang).status, FAIL)

        res = self.client.patch(
            "/api/admin/languages/zu/settings/",
            {"bible_attribution": "Scripture from Some Licensed Zulu Bible, CC BY 4.0."},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(_attribution_check(Language.objects.get(code="zu")).status, PASS)

    def test_the_settings_payload_carries_both_fields(self):
        """The admin card reads them off the language page; absent means the
        credit box never appears and the licence row never warns."""
        self._create(bible_licence="CC BY 4.0")
        settings_payload = self.client.get("/api/admin/languages/zu/").data["settings"]
        self.assertEqual(settings_payload["bible_licence"], "CC BY 4.0")
        self.assertEqual(settings_payload["bible_attribution"], "")


class FooterRendersItTests(TestCase):
    """The credit exists to be SEEN. A row in Postgres discharges nothing."""

    def test_frontend_carries_every_seeded_credit_verbatim(self):
        if not CREDIT_TS.exists():  # backend-only image; see the module docstring
            self.skipTest("frontend/ not present in this checkout")
        source = CREDIT_TS.read_text(encoding="utf-8")
        # The TS splits long lines across string concatenations, so compare on
        # collapsed whitespace with the quote-and-plus joinery removed rather
        # than requiring the literal to be one unbroken line.
        flat = re.sub(r"['\"]\s*\+\s*['\"]", "", source)
        flat = re.sub(r"\s+", " ", flat)
        for code, credit in _seed_attributions().items():
            self.assertIn(f"{code}:", flat, f"{code} missing from bibleCredit.ts")
            self.assertIn(
                re.sub(r"\s+", " ", credit),
                flat,
                f"{code}: bibleCredit.ts does not carry the seeded credit verbatim",
            )

    def test_frontend_credits_nothing_the_seed_does_not_declare(self):
        """The direction that catches a stale credit left behind after a Bible
        changes — the site would keep crediting a text it no longer quotes."""
        if not CREDIT_TS.exists():
            self.skipTest("frontend/ not present in this checkout")
        source = CREDIT_TS.read_text(encoding="utf-8")
        body = source.split("BIBLE_CREDIT", 1)[1].split("};", 1)[0]
        keyed = set(re.findall(r"^\t(\w+):", body, re.M))
        self.assertEqual(keyed, set(_seed_attributions()))
