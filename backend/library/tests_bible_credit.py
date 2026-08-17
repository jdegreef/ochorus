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
from .language_seed import SEED_LANGUAGES
from .models import Language
from .readiness import FAIL, PASS, SKIPPED, Check, _attribution_check
from .translation import GLOSSARY_TERMS

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

    Both catalogue calls are stubbed. ``_verify_bible`` and ``licence_for`` reach
    api.takeroot.bible, which CI cannot; and stubbing ``licence_for`` explicitly
    is the point rather than a convenience — left live it returns
    ``("", False)`` offline, so every case below would pass through the
    could-not-ask fallback and the derivation these tests exist to check would
    never run.
    """

    def setUp(self):
        self.client = APIClient()
        for target, value in (
            ("_verify_bible", (True, "stubbed")),
            ("licence_for", ("", False)),
        ):
            patcher = mock.patch.object(content, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _catalogue(self, licence: str, known: bool = True):
        """What Take Root says about the submitted Bible code."""
        return mock.patch.object(content, "licence_for", return_value=(licence, known))

    def _create(self, **extra):
        payload = {
            "code": "zu",
            "name": "Zulu",
            "native_name": "isiZulu",
            "bible_code": "zul-x",
            "bible_label": "Some Licensed Zulu Bible",
            "glossary": dict.fromkeys(GLOSSARY_TERMS, "x"),
            **extra,
        }
        return self.client.post("/api/admin/languages/", payload, format="json")

    def test_the_licence_comes_from_the_submitted_code_not_the_form(self):
        """The keystroke that used to defeat the whole gate.

        The Bible box is free text and its placeholder is `irvhin` — the CC BY-SA
        Hindi IRV. Typing a licensed code by hand sends no licence at all, and
        trusting the form would have stored a blank one, skipped the attribution
        check as "public domain", and cleared the language for launch.
        """
        with self._catalogue("CC BY-SA 4.0"):
            self.assertEqual(self._create().status_code, 201)
        self.assertEqual(Language.objects.get(code="zu").bible_licence, "CC BY-SA 4.0")

    def test_the_catalogue_also_overrides_a_licence_that_is_not_owed(self):
        """The other direction, so this is a lookup and not a one-way ratchet."""
        with self._catalogue(""):
            self._create(bible_licence="CC BY 4.0")
        self.assertEqual(Language.objects.get(code="zu").bible_licence, "")

    def test_the_form_is_believed_only_when_the_catalogue_cannot_be_asked(self):
        """"We could not check" must not become "public domain" — but it is also
        the one moment the picker knows something the server cannot re-derive."""
        with self._catalogue("", known=False):
            self._create(bible_licence="CC BY 4.0")
        self.assertEqual(Language.objects.get(code="zu").bible_licence, "CC BY 4.0")

    def test_an_over_long_licence_is_truncated_rather_than_crashing(self):
        with self._catalogue("x" * 500):
            self.assertEqual(self._create().status_code, 201)
        self.assertEqual(len(Language.objects.get(code="zu").bible_licence), 60)

    def test_a_licensed_language_is_told_what_it_owes(self):
        with self._catalogue("CC BY 4.0"):
            res = self._create()
        steps = " ".join(res.data["next_steps"])
        self.assertIn("CC BY 4.0", steps)
        self.assertIn("bibleCredit.ts", steps)

    def test_a_public_domain_language_is_not_nagged(self):
        with self._catalogue(""):
            res = self._create()
        self.assertNotIn("bibleCredit.ts", " ".join(res.data["next_steps"]))

    def test_it_cannot_go_live_until_the_credit_is_written(self):
        with self._catalogue("CC BY 4.0"):
            self._create()
        self.assertEqual(_attribution_check(Language.objects.get(code="zu")).status, FAIL)

        res = self.client.patch(
            "/api/admin/languages/zu/settings/",
            {"bible_attribution": "Scripture from Some Licensed Zulu Bible, CC BY 4.0."},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(_attribution_check(Language.objects.get(code="zu")).status, PASS)

    def test_changing_the_bible_re_derives_the_licence(self):
        """A licence is a fact about the Bible, not about the row. Swapping a
        public-domain text for a licensed one and keeping the old blank licence
        would retire the gate exactly when it starts to matter."""
        with self._catalogue(""):
            self._create()
        with self._catalogue("CC BY-SA 4.0"):
            res = self.client.patch(
                "/api/admin/languages/zu/settings/",
                {"bible_code": "zul-licensed"},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.data)
        row = Language.objects.get(code="zu")
        self.assertEqual(row.bible_licence, "CC BY-SA 4.0")
        self.assertEqual(_attribution_check(row).status, FAIL)

    def test_an_over_long_credit_line_is_a_400_not_a_500(self):
        """The column is 300 chars. Postgres raises DataError on overflow and
        SQLite silently does not, so an unvalidated field is a 500 that local
        tests would never show."""
        with self._catalogue("CC BY 4.0"):
            self._create()
        res = self.client.patch(
            "/api/admin/languages/zu/settings/",
            {"bible_attribution": "x" * 400},
            format="json",
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertIn("300", res.data["detail"])

    def test_the_settings_payload_carries_both_fields(self):
        """The admin card reads them off the language page; absent means the
        credit box never appears and the licence row never warns."""
        with self._catalogue("CC BY 4.0"):
            self._create()
        payload = self.client.get("/api/admin/languages/zu/").data["settings"]
        self.assertEqual(payload["bible_licence"], "CC BY 4.0")
        self.assertEqual(payload["bible_attribution"], "")


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
            self.assertRegex(flat, rf"['\"]?{re.escape(code)}['\"]?\s*:", f"{code} missing")
            self.assertIn(
                re.sub(r"\s+", " ", credit),
                flat,
                f"{code}: bibleCredit.ts does not carry the seeded credit verbatim",
            )

    def test_frontend_credits_carry_a_licence_uri(self):
        """CC BY-SA 4.0 §3(a)(1)(A)(iii) wants the licence linked where that is
        practicable, and in an HTML footer it always is. Asserted on the seed
        rather than the TS because the seed is the copy a human edits first."""
        for code, credit in _seed_attributions().items():
            self.assertIn("https://", credit, f"{code}: credit links no licence")

    def test_the_frontend_may_credit_a_language_the_seed_has_never_heard_of(self):
        """Deliberately NOT an equality check, and the reason is worth keeping.

        An admin-created language is owned by the database, never by
        ``language_seed.py`` — ``AdminLanguageSettingsView`` returns 409 for a
        repo-defined one precisely so those two sets stay disjoint. So the
        create response tells an admin to put their credit in bibleCredit.ts,
        and an equality check here would fail CI for doing exactly that, while
        the only alternative (adding it to the seed) would make the settings
        page refuse the edit that produced it. Equality was that contradiction
        written down.

        What still has to hold is the direction that protects readers: every
        credit the repo declares must be one the site actually renders. Extra
        keys are checked on the frontend side instead — bibleCredit.test.ts
        fails any key that is not a routable locale.
        """
        if not CREDIT_TS.exists():
            self.skipTest("frontend/ not present in this checkout")
        body = CREDIT_TS.read_text(encoding="utf-8").split("BIBLE_CREDIT", 1)[1]
        body = body.split("};", 1)[0]
        # Quoted keys included: a locale like `zh-hans` cannot be a bare
        # identifier, and a guard that quietly stops seeing hyphenated locales
        # is the same bug href.test.ts already caught once.
        keyed = set(re.findall(r"^\t['\"]?([\w-]+)['\"]?\s*:", body, re.M))
        self.assertLessEqual(
            set(_seed_attributions()),
            keyed,
            "bibleCredit.ts is missing a credit the seed declares",
        )
