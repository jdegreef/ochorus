"""The Language registry: seeding, readiness, going live, and the admin's language screens.

Moved out of the 6,500-line library/tests.py so a domain can be run — and
edited — on its own. Pure move: no test changed.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock, skipUnless

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from . import languages as languages_module
from . import readiness as readiness_module
from .language_seed import SEED_LANGUAGES
from .languages import config as language_config
from .models import (
    Author,
    AuthorTranslation,
    Book,
    Language,
    Plan,
    Topic,
)
from .translation import (
    GLOSSARY_TERMS,
    Ref,
    fetch_chapter,
    missing_glossary_terms,
    verify_glossary,
)

#: A language that does not exist, for the add-a-language screens.
INVENTED = {
    "code": "zz",
    "name": "Testish",
    "native_name": "Testish",
    "bible_code": "irvhin",  # any code the verifier accepts; mocked in these tests
    "bible_label": "Stand-in Version",
    "glossary": {t: f"zz-{t}" for t in GLOSSARY_TERMS},
}


class LanguageDisplayCacheTests(TestCase):
    """The per-process display cache, and how it recovers from another worker.

    `post_save` invalidates the cache in the process that did the write — and
    only there. Under more than one worker (which is every deployment) that made
    "the registry is the source of language names" true for one process and
    false for the rest: a language added from the admin rendered as a bare code
    everywhere else until a deploy restarted them.

    `bulk_create` is the faithful simulation: it writes the row WITHOUT sending
    `post_save`, which is exactly what another process's write looks like from
    in here.
    """

    def setUp(self):
        languages_module.invalidate()

    def test_a_language_another_worker_created_is_found(self):
        languages_module.entry("en")  # warm this process's map, before `fr` exists
        Language.objects.bulk_create(
            [Language(code="fr", name="French", native_name="Français")]
        )
        self.assertEqual(languages_module.entry("fr")["name"], "French")

    def test_a_code_with_no_row_still_falls_back_to_itself(self):
        self.assertEqual(languages_module.entry("qq")["name"], "qq")

    def test_an_unresolvable_code_is_not_requeried_forever(self):
        """The cost of the recovery above, paid once per process per code."""
        languages_module.entry("qq")
        with self.assertNumQueries(0):
            languages_module.entry("qq")
            languages_module.entry("qq")

    def test_two_unresolvable_codes_do_not_erase_each_other(self):
        """They did, when the miss path went through `invalidate`.

        `invalidate` clears every recorded absence, so a response naming two
        codes with no row rebuilt the map once per lookup — each miss forgetting
        the other's negative. A queue listing a handful of retired codes would
        have paid a query per row, which is precisely the N+1 this cache exists
        to prevent.
        """
        languages_module.entry("qq")
        languages_module.entry("xx")
        with self.assertNumQueries(0):
            for _ in range(5):
                languages_module.entry("qq")
                languages_module.entry("xx")

    def test_a_recorded_absence_is_dropped_once_the_row_appears(self):
        """A negative must never outlive the fact it recorded."""
        self.assertEqual(languages_module.entry("fr")["name"], "fr")  # absent, recorded
        Language.objects.bulk_create(
            [Language(code="fr", name="French", native_name="Français")]
        )
        # Nothing has invalidated this process's map — but another miss on a
        # DIFFERENT code refreshes it, and that refresh must retract "fr".
        languages_module.entry("yy")
        self.assertEqual(languages_module.entry("fr")["name"], "French")

    def test_a_known_language_costs_nothing_after_the_first_build(self):
        """The reason this cache exists — callers loop over content rows."""
        languages_module.entry("en")
        with self.assertNumQueries(0):
            for _ in range(20):
                languages_module.entry("en")

    def test_an_edit_in_this_process_still_invalidates(self):
        languages_module.entry("en")
        Language.objects.filter(code="en").update(name="English (edited)")
        # `update()` sends no signal either, so this is the same recovery path.
        languages_module.invalidate()
        self.assertEqual(languages_module.entry("en")["name"], "English (edited)")


class LanguageSeedTableTests(SimpleTestCase):
    """Guards on the repo's seed table; see library/language_seed.py."""

    def test_every_language_is_fully_configured(self):
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code):
                for field in ("name", "native", "bible", "bible_label", "glossary"):
                    self.assertTrue(cfg.get(field), f"{code}: empty {field}")

    def test_glossaries_cover_the_shared_term_set(self):
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code):
                self.assertEqual(
                    set(cfg["glossary"]), set(GLOSSARY_TERMS),
                    f"{code}: glossary terms differ from GLOSSARY_TERMS",
                )

    @skipUnless(
        os.environ.get("CHECK_BIBLE_CODES"), "network check; CHECK_BIBLE_CODES=1 to run"
    )
    def test_bible_codes_resolve_against_take_root(self):
        # Goes through fetch_chapter — the same call scripture_context makes on a
        # real job — so this proves the codes work for the path that uses them,
        # not for a URL the test built itself. Opt-in so CI stays hermetic:
        #   CHECK_BIBLE_CODES=1 uv run python manage.py test \
        #     library.tests.LanguageSeedTableTests
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code, bible=cfg["bible"]):
                data = fetch_chapter(cfg["bible"], Ref("JHN", 1))
                self.assertTrue(
                    data and data.get("verses"),
                    f"{code}: {cfg['bible']} returned no verses",
                )


class LanguageRegistrySeedTests(TestCase):
    """`seed_languages` — identity refreshes, the switch and the bar do not.

    This is the trap backend/CLAUDE.md warns about and that has bitten this
    codebase before: the seed re-runs on EVERY deploy, so any field a workflow
    owns after creation must be create-only. For languages that means `status`
    (an admin launched it), the thresholds (an admin tuned them), `went_live_at`
    and `notes`. If those were in the update set, the first deploy after a launch
    would silently put the language back to draft.
    """

    def test_seed_creates_every_configured_language(self):
        Language.objects.all().delete()
        call_command("seed_languages")
        codes = set(Language.objects.values_list("code", flat=True))
        # English (the source) plus every translation target.
        self.assertEqual(codes, {"en", "es", "sw", "lg", "pt", "ar", "hi", "uk", "fr"})

        en = Language.objects.get(code="en")
        self.assertTrue(en.is_source)
        self.assertEqual(en.bible_code, "")  # nothing to translate scripture into

        ar = Language.objects.get(code="ar")
        self.assertTrue(ar.rtl, "Arabic is right-to-left")
        self.assertFalse(ar.is_source)
        self.assertTrue(ar.bible_code, "a target language needs a Bible")
        # The glossary rides on the row now — it is what a translate_* command
        # reads, so a seeded language must arrive with a complete one.
        self.assertEqual(missing_glossary_terms(ar.glossary), [])

    def test_seed_is_idempotent(self):
        call_command("seed_languages")
        before = Language.objects.count()
        call_command("seed_languages")
        self.assertEqual(Language.objects.count(), before)

    def test_a_deploy_never_walks_back_a_launch_or_a_tuned_bar(self):
        call_command("seed_languages")
        ar = Language.objects.get(code="ar")
        # An admin launches Arabic and tunes its bar down for a beachhead run.
        ar.status = Language.Status.LIVE
        ar.min_books = 1
        ar.min_bios = 0
        ar.notes = "beachhead launch"
        ar.save()

        call_command("seed_languages")  # i.e. the next deploy

        ar.refresh_from_db()
        self.assertEqual(ar.status, Language.Status.LIVE, "the deploy un-launched it")
        self.assertEqual(ar.min_books, 1, "the deploy reset a tuned threshold")
        self.assertEqual(ar.min_bios, 0)
        self.assertEqual(ar.notes, "beachhead launch")

    def test_a_deploy_does_refresh_identity(self):
        # The other half: identity IS the repo's, so a correction ships.
        call_command("seed_languages")
        lg = Language.objects.get(code="lg")
        lg.name = "Wrong Name"
        lg.native_name = "Wrong"
        lg.save()

        call_command("seed_languages")

        lg.refresh_from_db()
        self.assertEqual(lg.name, "Luganda")
        self.assertEqual(lg.native_name, "Luganda")

    def test_a_deploy_repairs_a_repo_language_glossary(self):
        # Identity includes the glossary, so a term corrected in the repo ships
        # — and a row someone hand-edited in the database is put back.
        call_command("seed_languages")
        lg = Language.objects.get(code="lg")
        lg.glossary = {"grace": "wrong"}
        lg.save(update_fields=["glossary"])

        call_command("seed_languages")

        lg.refresh_from_db()
        self.assertEqual(missing_glossary_terms(lg.glossary), [])
        self.assertEqual(lg.glossary["grace"], SEED_LANGUAGES["lg"]["glossary"]["grace"])


class LanguageEntryTests(TestCase):
    """`_language_entry` now reads the registry rather than a hardcoded map."""

    def setUp(self):
        from library import languages

        languages.invalidate()

    def test_names_come_from_the_registry(self):
        from library.languages import entry

        self.assertEqual(entry("sw")["name"], "Swahili")
        self.assertEqual(entry("sw")["native_name"], "Kiswahili")

    def test_arabic_is_no_longer_bare_codes(self):
        # The old LANGUAGE_NAMES map had no Arabic, so an Arabic row rendered as
        # "ar / ar". That was the concrete cost of a fourth source of truth.
        from library.languages import entry

        ar = entry("ar")
        self.assertEqual(ar["name"], "Arabic")
        self.assertNotEqual(ar["native_name"], "ar")
        self.assertTrue(ar["rtl"])

    def test_an_unknown_code_degrades_to_itself(self):
        from library.languages import entry

        self.assertEqual(entry("zz")["name"], "zz")

    def test_editing_a_row_invalidates_the_cache(self):
        from library.languages import entry

        self.assertEqual(entry("lg")["name"], "Luganda")
        lang = Language.objects.get(code="lg")
        lang.name = "Ganda"
        lang.save()
        # The signal in library/languages.py drops the cache, so a rename shows
        # up without a restart.
        self.assertEqual(entry("lg")["name"], "Ganda")

    def test_live_codes_reads_status_from_the_database(self):
        from library.languages import live_codes

        self.assertIn("es", live_codes())
        self.assertNotIn("ar", live_codes())  # draft

        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        self.assertIn("ar", live_codes())


class LanguageListEndpointTests(TestCase):
    """`/api/library/languages/` — intent AND inventory, plus the build's view."""

    def setUp(self):
        self.client = APIClient()
        from library import languages

        languages.invalidate()
        self.author = Author.objects.create(slug="a", name="A")
        for lang in ("en", "es"):
            Book.objects.create(
                author=self.author, slug="b", language=lang, title="T", is_published=True
            )

    def test_reader_list_needs_both_live_status_and_books(self):
        codes = [r["code"] for r in self.client.get("/api/library/languages/").data]
        self.assertEqual(codes, ["en", "es"])

        # Swahili is live in the registry but has no book here yet — the reader's
        # picker must not offer a language with nothing to open.
        self.assertNotIn("sw", codes)

        # And a language with books but NOT live stays out: this is the guard the
        # old books-only rule lacked, which is how pt got advertised while empty.
        Book.objects.create(
            author=self.author, slug="b", language="ar", title="T", is_published=True
        )
        codes = [r["code"] for r in self.client.get("/api/library/languages/").data]
        self.assertNotIn("ar", codes)

    def test_all_returns_every_live_language_for_the_build(self):
        # The build asks for intent, not inventory: a live locale still filling
        # up must be prerendered and advertised.
        codes = [r["code"] for r in self.client.get("/api/library/languages/?all=1").data]
        self.assertEqual(codes, ["en", "es", "sw", "lg", "pt"])
        self.assertNotIn("ar", codes)  # draft

    def test_going_live_changes_what_the_build_is_told(self):
        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        codes = [r["code"] for r in self.client.get("/api/library/languages/?all=1").data]
        self.assertIn("ar", codes)

    def test_entries_carry_the_flags_the_reader_needs(self):
        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        rows = {r["code"]: r for r in self.client.get("/api/library/languages/?all=1").data}
        self.assertTrue(rows["ar"]["rtl"], "the reader needs to know to flip direction")
        self.assertFalse(rows["es"]["rtl"])
        self.assertTrue(rows["en"]["is_source"])


class ReadinessReportTests(TestCase):
    """`readiness.report` — the computed answer to "can this language go live?"."""

    def setUp(self):
        self.es = Language.objects.get(code="es")
        self.en = Language.objects.get(code="en")
        self.author = Author.objects.create(slug="a", name="A", bio="An English bio.")

    def _report(self, lang, bible=None):
        """A report with the Bible check stubbed out.

        Two reasons, both learned the hard way. The Bible check makes a live call
        to the Take Root API, so leaving it real would (a) make this suite depend
        on a third party being up — a hidden network dependency in a unit test —
        and (b) make results differ by environment: it passes in CI, which has
        network, and reports `unknown` in a sandbox that doesn't. A test that
        changes verdict with its surroundings isn't testing the code.
        """
        stub = bible or readiness_module.Check(
            "bible", "Bible", readiness_module.PASS, "stubbed"
        )
        with mock.patch.object(readiness_module, "_bible_check", return_value=stub):
            return readiness_module.report(lang)

    def test_the_source_language_skips_translation_checks(self):
        # Unstubbed on purpose: this asserts the real skip logic, and for the
        # source language `_bible_check` returns early — before any network call
        # — so it's safe to run for real here.
        r = readiness_module.report(self.en)
        by_key = {c.key: c for c in r.checks}
        for key in ("bible", "glossary", "ui"):
            self.assertEqual(by_key[key].status, "skipped", key)

    def test_a_failing_count_blocks_and_says_what_is_missing(self):
        self.es.min_books = 3
        self.es.save()
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "fail")
        self.assertEqual(books.current, 0)
        self.assertEqual(books.required, 3)
        self.assertIn("needs 3", books.detail)

    def test_zero_disables_a_check_rather_than_failing_it(self):
        self.es.min_books = 0
        self.es.save()
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "skipped")
        self.assertFalse(books.blocking)

    def test_meeting_the_bar_passes(self):
        self.es.min_books = 1
        self.es.min_bios = 0
        self.es.require_all_topics = False
        self.es.save()
        Book.objects.create(
            author=self.author, slug="b", language="es", title="T", is_published=True
        )
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "pass")

    def test_verify_bible_false_skips_the_network_check(self):
        # The bulk scoreboard path must not make a live Bible call per language.
        with mock.patch.object(readiness_module, "_bible_check") as live:
            bible = {
                c.key: c
                for c in readiness_module.report(self.es, verify_bible=False).checks
            }["bible"]
        live.assert_not_called()
        # A configured code reads as unknown here (deferred to the real check);
        # it neither blocks nor scores.
        self.assertEqual(bible.status, readiness_module.UNKNOWN)

    def test_verify_bible_false_still_catches_a_missing_bible(self):
        # The cheap, local failure — no Bible configured at all — is still caught
        # without a network call.
        self.es.bible_code = ""
        self.es.save()
        with mock.patch.object(readiness_module, "_bible_check") as live:
            bible = {
                c.key: c
                for c in readiness_module.report(self.es, verify_bible=False).checks
            }["bible"]
        live.assert_not_called()
        self.assertEqual(bible.status, readiness_module.FAIL)

    def test_unknown_does_not_block_readiness(self):
        # Bible and interface strings can be unanswerable where they're asked —
        # no network, or an API container that can't see the frontend. Treating
        # that as failure would block a launch for an unrelated reason; the
        # interface rule is enforced at build time instead.
        #
        # The unknown is INJECTED rather than induced by the environment: an
        # earlier version of this test just asserted "some check is unknown",
        # which held in a sandbox with no network and failed in CI, where the
        # Bible check really does resolve.
        self.es.min_books = 0
        self.es.min_bios = 0
        self.es.min_plans = 0
        self.es.require_all_topics = False
        self.es.save()
        unreachable = readiness_module.Check(
            "bible", "Bible", readiness_module.UNKNOWN, "Could not reach the Bible API."
        )
        r = self._report(self.es, bible=unreachable)
        self.assertIn("unknown", {c.status for c in r.checks})
        self.assertTrue(r.ready, "an unanswerable check must not block")

    def test_a_genuinely_bad_bible_does_block(self):
        # The counterpart: `unknown` is forgiving, `fail` is not.
        self.es.min_books = 0
        self.es.min_bios = 0
        self.es.min_plans = 0
        self.es.require_all_topics = False
        self.es.save()
        bad = readiness_module.Check(
            "bible", "Bible", readiness_module.FAIL, "Bible code 'nope' returned no verses."
        )
        r = self._report(self.es, bible=bad)
        self.assertFalse(r.ready)
        self.assertEqual([c.key for c in r.blockers], ["bible"])

    def test_untranslated_topics_block_when_required(self):
        Topic.objects.create(slug="t", title="T", description="d", is_published=True)
        self.es.require_all_topics = True
        self.es.save()
        topics = {c.key: c for c in self._report(self.es).checks}["topics"]
        self.assertEqual(topics.status, "fail")
        self.assertIn("hidden in this language", topics.detail)

    def test_bios_count_either_short_or_long_form(self):
        self.es.min_bios = 1
        self.es.save()
        AuthorTranslation.objects.create(author=self.author, language="es", bio_html="<p>x</p>")
        bios = {c.key: c for c in self._report(self.es).checks}["bios"]
        self.assertEqual(bios.status, "pass")

    def test_a_missing_ui_catalogue_fails_and_is_not_forceable(self):
        # A count bar (books, bios) is a judgement `force` can override. A
        # missing UI catalogue is not: a live locale with no compiled catalogue
        # cannot build, so its failure is marked unforceable and go-live refuses
        # it even when forced.
        with mock.patch.object(readiness_module, "_ui_gaps", return_value=(readiness_module.NO_CATALOGUE, 0)):
            ui = readiness_module._ui_check(self.es)
        self.assertEqual(ui.status, "fail")
        self.assertFalse(ui.forceable)

    def test_an_incomplete_ui_catalogue_is_also_unforceable(self):
        with mock.patch.object(readiness_module, "_ui_gaps", return_value=(1, 0)):
            ui = readiness_module._ui_check(self.es)
        self.assertEqual(ui.status, "fail")
        self.assertFalse(ui.forceable)

    def test_hard_blockers_are_only_the_unforceable_failures(self):
        # Zero out the count bars so the UI catalogue is the sole blocker, then
        # confirm it lands in `hard_blockers` (and the endpoint's `unforceable`
        # list) while a normal count failure would not.
        self.es.min_books = 0
        self.es.min_bios = 0
        self.es.min_plans = 0
        self.es.require_all_topics = False
        self.es.save()
        with mock.patch.object(readiness_module, "_ui_gaps", return_value=(readiness_module.NO_CATALOGUE, 0)):
            r = self._report(self.es)
        self.assertFalse(r.ready)
        self.assertEqual([c.key for c in r.hard_blockers], ["ui"])
        self.assertEqual(r.as_dict()["unforceable"], ["ui"])


class AdminLanguageReadinessEndpointTests(TestCase):
    """The admin readiness report and the editable bar."""

    def setUp(self):
        self.client = APIClient()

    def _patch_perm(self):
        """Admin permission AND a stubbed Bible check.

        The readiness endpoint calls the live Take Root API. Stubbing it here
        keeps these tests hermetic — otherwise the suite fails whenever that
        third party is unreachable, which has nothing to do with this endpoint.
        """
        from unittest.mock import patch

        perm = patch("accounts.permissions.RequireCapability.has_permission", return_value=True)
        bible = mock.patch.object(
            readiness_module,
            "_bible_check",
            return_value=readiness_module.Check(
                "bible", "Bible", readiness_module.PASS, "stubbed"
            ),
        )

        class _Both:
            def __enter__(self):
                perm.start()
                bible.start()
                return self

            def __exit__(self, *exc):
                bible.stop()
                perm.stop()
                return False

        return _Both()

    def test_report_lists_checks_and_current_thresholds(self):
        with self._patch_perm():
            res = self.client.get("/api/admin/languages/ar/readiness/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("checks", res.data)
        self.assertIn("min_books", res.data["thresholds"])
        self.assertEqual(res.data["status"], "draft")

    def test_unknown_language_is_404(self):
        with self._patch_perm():
            self.assertEqual(
                self.client.get("/api/admin/languages/zz/readiness/").status_code, 404
            )
            self.assertEqual(
                self.client.patch(
                    "/api/admin/languages/zz/thresholds/", {"min_books": 1}, format="json"
                ).status_code,
                404,
            )

    def test_editing_the_bar_changes_the_verdict(self):
        with self._patch_perm():
            before = self.client.get("/api/admin/languages/ar/readiness/").data
            self.assertIn("books", before["blocking"])

            # Every countable bar, not just the ones that happen to block today:
            # the point is that lowering the bar clears blockers, and pinning
            # that to the current defaults makes the test fail whenever a
            # default changes for unrelated reasons (min_plans just did).
            res = self.client.patch(
                "/api/admin/languages/ar/thresholds/",
                {
                    "min_books": 0,
                    "min_bios": 0,
                    "min_plans": 0,
                    "min_sermons": 0,
                    "require_all_topics": False,
                },
                format="json",
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data["thresholds"]["min_books"], 0)

            after = self.client.get("/api/admin/languages/ar/readiness/").data
        self.assertEqual(after["blocking"], [], "lowering the bar should clear blockers")

    def test_threshold_validation(self):
        cases = [
            ({"min_books": -1}, 400),
            ({"min_books": "lots"}, 400),
            ({}, 400),  # nothing to update
            ({"min_books": 2}, 200),
        ]
        with self._patch_perm():
            for body, expected in cases:
                res = self.client.patch(
                    "/api/admin/languages/es/thresholds/", body, format="json"
                )
                self.assertEqual(res.status_code, expected, body)

    def test_status_cannot_be_changed_through_the_thresholds_endpoint(self):
        # Launching is the go-live action's job — it re-runs the checks. A
        # thresholds PATCH must never be a back door to going live.
        with self._patch_perm():
            res = self.client.patch(
                "/api/admin/languages/ar/thresholds/",
                {"status": "live", "min_books": 1},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("status", res.data["updated"])
        self.assertEqual(Language.objects.get(code="ar").status, "draft")

    def test_readiness_requires_admin(self):
        # Anonymous gets 401 (no credentials); a signed-in non-admin would get
        # 403. Either way the endpoint is closed — these are admin surfaces that
        # expose content counts and can change a launch bar.
        self.assertIn(
            self.client.get("/api/admin/languages/es/readiness/").status_code, (401, 403)
        )
        self.assertIn(
            self.client.patch(
                "/api/admin/languages/es/thresholds/", {"min_books": 1}, format="json"
            ).status_code,
            (401, 403),
        )


class GoLiveTests(TestCase):
    """Taking a language live: re-check, record, trigger the rebuild.

    The two halves are asserted separately throughout. "Recorded as live" and
    "readers can see it" are different facts — the reader is a prerendered static
    site — and a launch whose deploy failed is a real state that must stay
    visible rather than collapsing into one success flag.
    """

    def setUp(self):
        self.client = APIClient()
        self.ar = Language.objects.get(code="ar")

    def _perm_and_ready(self, ready=True):
        """Admin permission, a stubbed Bible check, and a chosen readiness verdict."""
        from unittest.mock import patch

        perm = patch("accounts.permissions.RequireCapability.has_permission", return_value=True)
        checks = [] if ready else [
            readiness_module.Check("books", "Books", readiness_module.FAIL, "0 books — needs 5.")
        ]
        # Patched on the readiness module itself, which is what golive imports —
        # `from . import readiness` then `readiness.report(...)`, so the lookup
        # happens at call time and this stub is what golive sees.
        rep = mock.patch.object(
            readiness_module, "report", return_value=readiness_module.Report("ar", checks)
        )

        class _Ctx:
            def __enter__(self):
                perm.start()
                rep.start()
                return self

            def __exit__(self, *exc):
                rep.stop()
                perm.stop()
                return False

        return _Ctx()

    def test_not_ready_is_refused_with_its_blockers(self):
        with self._perm_and_ready(ready=False):
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertFalse(res.data["launched"])
        self.assertEqual(res.data["reason"], "not_ready")
        self.assertEqual(res.data["readiness"]["blocking"], ["books"])
        # And crucially it did NOT launch.
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "draft")

    def test_force_launches_past_failing_checks_and_says_so(self):
        with self._perm_and_ready(ready=False):
            res = self.client.post(
                "/api/admin/languages/ar/go-live/", {"force": True}, format="json"
            )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["launched"])
        self.assertTrue(res.data["forced"], "an override must be recorded as one")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")

    def test_force_cannot_launch_a_locale_with_no_ui_catalogue(self):
        # The incident this guards: a language flipped live with no compiled UI
        # locale fails every `fetch-live-locales.mjs` run and freezes ALL
        # deploys. `force` overrides judgement bars, never this — a forced launch
        # here would take the site down, not put the language up.
        from unittest.mock import patch

        ui_fail = readiness_module.Check(
            "ui", "Interface strings", readiness_module.FAIL, "No ar catalogue.",
            0, 120, forceable=False,
        )
        rep = readiness_module.Report("ar", [ui_fail])
        with patch("accounts.permissions.RequireCapability.has_permission", return_value=True):
            with mock.patch.object(readiness_module, "report", return_value=rep):
                res = self.client.post(
                    "/api/admin/languages/ar/go-live/", {"force": True}, format="json"
                )
        self.assertEqual(res.status_code, 409)
        self.assertFalse(res.data["launched"])
        self.assertEqual(res.data["reason"], "unbuildable")
        self.assertEqual(res.data["blocking"], ["ui"])
        self.assertEqual(res.data["readiness"]["unforceable"], ["ui"])
        # It did NOT launch — the row stays draft.
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "draft")

    def test_a_ready_language_launches_and_is_stamped(self):
        with self._perm_and_ready(ready=True):
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")
        self.assertIsNotNone(self.ar.went_live_at)
        self.assertFalse(res.data["forced"])

    def test_relaunching_keeps_the_original_went_live_at(self):
        # Re-running the action (e.g. to retrigger a deploy) must not rewrite when
        # the language became public.
        with self._perm_and_ready(ready=True):
            self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
            self.ar.refresh_from_db()
            first = self.ar.went_live_at
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.went_live_at, first)
        self.assertTrue(res.data["already_live"])

    def test_an_unconfigured_deploy_hook_is_reported_not_hidden(self):
        with self.settings(RENDER_WEB_DEPLOY_HOOK=""):
            with self._perm_and_ready(ready=True):
                res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertTrue(res.data["launched"])
        self.assertEqual(res.data["deploy"]["status"], "not_configured")
        self.assertIn("won't see it", res.data["deploy"]["detail"])

    def test_a_failing_deploy_hook_does_not_undo_the_launch(self):
        # The status flip already happened; losing it because the hook 500'd would
        # be worse than a launch that needs a manual deploy.
        with self.settings(RENDER_WEB_DEPLOY_HOOK="https://hook.example/deploy"):
            with self._perm_and_ready(ready=True):
                with mock.patch(
                    "library.golive.requests.post",
                    side_effect=__import__("requests").RequestException("boom"),
                ):
                    res = self.client.post(
                        "/api/admin/languages/ar/go-live/", {}, format="json"
                    )
        self.assertTrue(res.data["launched"])
        self.assertEqual(res.data["deploy"]["status"], "failed")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")

    def test_the_deploy_hook_is_fired_when_configured(self):
        with self.settings(RENDER_WEB_DEPLOY_HOOK="https://hook.example/deploy"):
            with self._perm_and_ready(ready=True):
                with mock.patch("library.golive.requests.post") as post:
                    post.return_value = mock.Mock(ok=True, status_code=200)
                    res = self.client.post(
                        "/api/admin/languages/ar/go-live/", {}, format="json"
                    )
                    post.assert_called_once_with("https://hook.example/deploy", timeout=20)
        self.assertEqual(res.data["deploy"]["status"], "triggered")

    def test_english_cannot_be_launched(self):
        from unittest.mock import patch

        with patch("accounts.permissions.RequireCapability.has_permission", return_value=True):
            res = self.client.post("/api/admin/languages/en/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_go_live_requires_admin(self):
        self.assertIn(
            self.client.post("/api/admin/languages/ar/go-live/", {}, format="json").status_code,
            (401, 403),
        )


class DeployCheckTests(TestCase):
    """"Did it ship?" — the question `status` cannot answer."""

    def setUp(self):
        self.client = APIClient()

    def _perm(self):
        from unittest.mock import patch

        return patch("accounts.permissions.RequireCapability.has_permission", return_value=True)

    def test_unknown_without_a_site_url_rather_than_a_guess(self):
        with self.settings(PUBLIC_SITE_URL=""):
            with self._perm():
                res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "unknown")

    def test_deployed_when_the_locale_is_in_the_live_sitemap(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.return_value = mock.Mock(
                        ok=True, text="<url><loc>https://ochorus.test/ar/books/</loc></url>"
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "deployed")

    def test_pending_when_the_build_has_not_caught_up(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.return_value = mock.Mock(
                        ok=True, text="<url><loc>https://ochorus.test/es/books/</loc></url>"
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "pending")

    # --- The split sitemap ---------------------------------------------------
    # sitemap.xml is a <sitemapindex> over per-type children, and chapters are no
    # longer advertised, so the index names no locale at all. The check fetches
    # the PAGES child and looks for this locale's static-page URLs (/<code>/) —
    # every advertised locale has those unconditionally, so the URL confirms the
    # build included the locale. Read for the flat shape only, this would report
    # "pending" forever, on the dashboard whose whole point is not to say the
    # deploy landed when it hasn't (and not to say it hasn't when it has).

    def _index(self, *children):
        locs = "".join(f"<sitemap><loc>https://ochorus.test/{c}</loc></sitemap>" for c in children)
        return mock.Mock(ok=True, text=f"<sitemapindex>{locs}</sitemapindex>")

    def _pages(self, *paths):
        locs = "".join(f"<url><loc>https://ochorus.test/{p}</loc></url>" for p in paths)
        return mock.Mock(ok=True, text=f"<urlset>{locs}</urlset>")

    def _route(self, index, pages):
        # verify_deployed fetches /sitemap.xml first, then /sitemap-pages.xml.
        def side_effect(url, *args, **kwargs):
            return pages if url.endswith("/sitemap-pages.xml") else index

        return side_effect

    def test_deployed_when_the_pages_child_lists_this_locale(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.side_effect = self._route(
                        self._index("sitemap-pages.xml", "sitemap-books.xml"),
                        self._pages("ar/", "ar/books", "es/", "es/books"),
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "deployed")

    def test_deployed_for_a_live_locale_that_has_no_books_yet(self):
        # The whole reason the signal is the PAGES child, not the books child: a
        # locale can be live (advertised, static pages built) with zero books —
        # a forced go-live, or a sermons-only locale. Its pages child carries
        # `/ar/` but no `/ar/books/…`, and it must still read as deployed. If this
        # ever fails, the check has been re-narrowed to require a book URL and the
        # false-negative is back.
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.side_effect = self._route(
                        self._index("sitemap-pages.xml"),
                        self._pages("ar/", "ar/about", "ar/sermons"),
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "deployed")

    def test_pending_when_the_pages_child_lacks_this_locale(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.side_effect = self._route(
                        self._index("sitemap-pages.xml"),
                        self._pages("es/", "es/about"),
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "pending")

    def test_another_locales_pages_are_not_mistaken_for_this_one(self):
        # A bare substring of the code would let "ar" match inside a future
        # "ar-EG". Pinning it to a whole path segment ("/ar/") is what keeps a
        # regional child from being read as its base language.
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.side_effect = self._route(
                        self._index("sitemap-pages.xml"),
                        self._pages("ar-EG/", "ar-EG/about"),
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "pending")

    def test_unknown_when_the_pages_child_cannot_be_fetched(self):
        # The index is fine but its pages child is unreachable — that is a
        # "don't know", not a "not deployed": reporting failure here would cry
        # wolf on a transient hiccup.
        import requests as _requests

        def side_effect(url, *args, **kwargs):
            if url.endswith("/sitemap-pages.xml"):
                raise _requests.RequestException("boom")
            return self._index("sitemap-pages.xml")

        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get", side_effect=side_effect):
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "unknown")


class AdminDashboardLanguageListTests(TestCase):
    """Every registry language is listed, whether or not it has content.

    The chicken-and-egg this fixes: the Translate buttons live on the
    per-language page, and the dashboard is how you reach it. Listing only
    languages that already had content meant a language with nothing in it was
    unreachable — so there was no way to queue the work that would give it
    content. Arabic sat fully wired and invisible.
    """

    def setUp(self):
        self.client = APIClient()

    def _rows(self):
        from unittest.mock import patch

        with patch("accounts.permissions.RequireCapability.has_permission", return_value=True):
            return {r["code"]: r for r in self.client.get("/api/admin/stats/").data["languages"]}

    def test_a_language_with_no_content_is_still_listed(self):
        rows = self._rows()
        self.assertIn("ar", rows, "a registry language must be reachable before it has content")
        self.assertEqual(rows["ar"]["books"], 0)
        self.assertEqual(rows["ar"]["sermons"], 0)
        # And it carries its real name, not a bare code — the registry supplies it.
        self.assertEqual(rows["ar"]["name"], "Arabic")

    def test_every_registry_language_appears(self):
        rows = self._rows()
        for code in Language.objects.values_list("code", flat=True):
            self.assertIn(code, rows, code)

    def test_a_content_language_with_no_registry_row_still_appears(self):
        # e.g. the "en-modern" pseudo-language: content exists under a code the
        # registry doesn't model, and hiding it would lose it from the inventory.
        author = Author.objects.create(slug="a", name="A")
        Book.objects.create(
            author=author, slug="b", language="en-modern", title="T", is_published=True
        )
        self.assertIn("en-modern", self._rows())


class InventedLanguageFixtureTests(SimpleTestCase):
    def test_the_fixture_language_is_not_a_real_one(self):
        """If this ever fails, the admin-created tests are silently asserting
        against a repo-defined language and will start returning 409."""
        from library.language_seed import SEED_LANGUAGES

        self.assertNotIn(INVENTED["code"], SEED_LANGUAGES)


class AdminAddLanguageTests(TestCase):
    """"Add a language" — the endpoint that starts a new language.

    The point of these tests is the thing that made the feature worth building:
    a language created here must be *translatable*, not merely listed. So the
    row is checked through `language_config` — the same accessor a translate_*
    command reads — rather than only by field.
    """

    def setUp(self):
        self.client = APIClient()

    def _admin(self, verses=True, reachable=True):
        """Admin permission plus a stubbed Bible API.

        Both are stubbed because the endpoint deliberately makes a live call: a
        wrong Bible code silently drops scripture from every translation, so it
        is checked at creation rather than discovered during a paid job.
        """
        from unittest.mock import patch

        perm = patch("accounts.permissions.RequireCapability.has_permission", return_value=True)
        fetch = patch(
            # The seam is the module that CALLS it, so this names languages.py —
            # where the create view lives now that the language-registry
            # endpoints have their own module.
            "library.admin_views.languages.fetch_chapter",
            return_value={"verses": [{"number": 1, "text": "…"}]} if verses else None,
        )
        api = patch.object(readiness_module, "api_reachable", return_value=reachable)

        class _All:
            def __enter__(self):
                for p in (perm, fetch, api):
                    p.start()
                return self

            def __exit__(self, *exc):
                for p in (api, fetch, perm):
                    p.stop()
                return False

        return _All()

    def _post(self, payload=None, **kw):
        with self._admin(**kw):
            return self.client.post("/api/admin/languages/", payload or INVENTED, format="json")

    def test_creating_a_language_makes_it_translatable(self):
        from library import languages as languages_module

        res = self._post()
        self.assertEqual(res.status_code, 201, res.data)
        languages_module.invalidate()

        lang = Language.objects.get(code="zz")
        self.assertEqual(lang.status, Language.Status.DRAFT, "creating is not launching")
        self.assertFalse(lang.is_source)

        # The real test: the translator can read its config off the new row.
        cfg = language_config("zz")
        self.assertEqual(cfg["bible"], INVENTED["bible_code"])
        self.assertEqual(set(cfg["glossary"]), set(GLOSSARY_TERMS))
        verify_glossary("zz")  # must not raise

    def test_a_new_language_is_immediately_reachable_in_the_admin(self):
        from unittest.mock import patch

        from library import languages as languages_module

        self._post()
        languages_module.invalidate()
        with patch("accounts.permissions.RequireCapability.has_permission", return_value=True):
            rows = {r["code"] for r in self.client.get("/api/admin/stats/").data["languages"]}
        self.assertIn("zz", rows)

    def test_a_new_language_is_not_advertised_to_readers(self):
        # Created as draft, so the build's live-locale list must not pick it up.
        self._post()
        res = self.client.get("/api/library/languages/")
        self.assertNotIn("zz", [r["code"] for r in res.data])

    def test_duplicate_code_is_rejected(self):
        self.assertEqual(self._post(dict(INVENTED, code="pt")).status_code, 409)

    def test_a_malformed_code_is_rejected(self):
        for bad in ("", "H", "english", "hi_IN", "../etc"):
            with self.subTest(code=bad):
                self.assertEqual(self._post(dict(INVENTED, code=bad)).status_code, 400)

    def test_the_code_is_normalised(self):
        self.assertEqual(self._post(dict(INVENTED, code=" ZZ ")).status_code, 201)
        self.assertTrue(Language.objects.filter(code="zz").exists())

    def test_a_partial_glossary_is_rejected(self):
        payload = dict(INVENTED, glossary={"grace": "अनुग्रह"})
        res = self._post(payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("justification", res.data["detail"])
        self.assertFalse(Language.objects.filter(code="hi").exists())

    def test_an_unknown_glossary_term_is_rejected(self):
        payload = dict(INVENTED, glossary=dict(INVENTED["glossary"], predestination="x"))
        res = self._post(payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("predestination", res.data["detail"])

    def test_names_are_required(self):
        self.assertEqual(self._post(dict(INVENTED, native_name="  ")).status_code, 400)
        self.assertEqual(self._post(dict(INVENTED, name="")).status_code, 400)

    def test_a_bible_code_is_required(self):
        self.assertEqual(self._post(dict(INVENTED, bible_code="")).status_code, 400)

    def test_a_bible_code_that_does_not_resolve_is_rejected(self):
        res = self._post(verses=False)
        self.assertEqual(res.status_code, 400)
        self.assertIn("no verses", res.data["detail"])
        self.assertFalse(Language.objects.filter(code="hi").exists())

    def test_an_unreachable_bible_api_does_not_block_creation(self):
        # "We couldn't ask" is not "the code is wrong" — the readiness check asks
        # again later, and refusing here would make our egress a gate on adding
        # a language.
        res = self._post(verses=False, reachable=False)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertFalse(res.data["bible_verified"])
        self.assertIn("Could not reach", res.data["bible_note"])

    def test_the_response_says_what_still_has_to_happen(self):
        res = self._post()
        joined = " ".join(res.data["next_steps"])
        self.assertIn("messages/zz.json", joined, "the UI catalogue gap must be stated")
        self.assertIn("Go live", joined)


class AdminLanguageSettingsTests(TestCase):
    """Editing a language's identity — and refusing to pretend for repo rows."""

    def setUp(self):
        self.client = APIClient()
        self.helper = AdminAddLanguageTests()
        self.helper.client = self.client

    def _patch(self, code, payload, **kw):
        with self.helper._admin(**kw):
            return self.client.patch(
                f"/api/admin/languages/{code}/settings/", payload, format="json"
            )

    def _create_invented(self):
        with self.helper._admin():
            return self.client.post("/api/admin/languages/", INVENTED, format="json")

    def test_an_admin_created_language_can_be_edited(self):
        self._create_invented()
        res = self._patch("zz", {"bible_label": "IRV (2019)", "rtl": False})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(Language.objects.get(code="zz").bible_label, "IRV (2019)")

    def test_a_repo_defined_language_is_refused_rather_than_silently_reverted(self):
        res = self._patch("pt", {"name": "Portugues"})
        self.assertEqual(res.status_code, 409)
        self.assertIn("language_seed.py", res.data["detail"])
        self.assertEqual(Language.objects.get(code="pt").name, "Portuguese")

    def test_a_partial_glossary_cannot_be_saved_later_either(self):
        self._create_invented()
        res = self._patch("zz", {"glossary": {"grace": "अनुग्रह"}})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            set(Language.objects.get(code="zz").glossary), set(GLOSSARY_TERMS)
        )

    def test_a_bible_code_change_is_verified_too(self):
        self._create_invented()
        res = self._patch("zz", {"bible_code": "nope"}, verses=False)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Language.objects.get(code="zz").bible_code, INVENTED["bible_code"])

    def test_unknown_language_is_404(self):
        self.assertEqual(self._patch("zz", {"name": "X"}).status_code, 404)

    def test_the_deploy_leaves_an_admin_created_language_alone(self):
        # The other half of the create-only rule: the seed re-asserts identity
        # for languages IT defines. A language the admin invented isn't in the
        # seed table, so nothing about it may be rewritten by a deploy.
        self._create_invented()
        self._patch("zz", {"name": "Hindi (India)"})
        call_command("seed_languages")
        self.assertEqual(Language.objects.get(code="zz").name, "Hindi (India)")


class UiCatalogueCheckTests(TestCase):
    """Where the interface-strings check gets its answer.

    This check used to be permanently `unknown` in production — the catalogues
    live in frontend/messages/ and the API image is built from backend/ alone —
    so the deployed admin could never say whether a language's interface was
    done. The frontend now generates a summary into backend/ (missing and
    pending keys per locale), and that summary is the check's one source.
    """

    def setUp(self):
        self.lang = Language.objects.get(code="ar")

    def _check_with(self, summary: dict):
        path = Path(tempfile.mkdtemp()) / "ui_catalogues.json"
        path.write_text(json.dumps(summary), "utf-8")
        with mock.patch("library.readiness.CATALOGUE_SUMMARY", path):
            return readiness_module._ui_check(self.lang)

    def test_the_committed_summary_answers(self):
        # Arabic has every key, so this is the case that used to report "unknown"
        # in production and now reports the truth — including its placeholders.
        check = readiness_module._ui_check(self.lang)
        self.assertEqual(check.status, readiness_module.PASS, check.detail)

    def test_an_incomplete_catalogue_fails_with_a_count(self):
        summary = {"locales": {"ar": {"missing": [f"k{i}" for i in range(12)], "pending": []}}}
        check = self._check_with(summary)
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertFalse(check.forceable)
        self.assertIn("12 string(s)", check.detail)

    def test_pending_placeholders_pass_but_are_not_called_translated(self):
        # Every key present, some still the English source: the build accepts it
        # (declared debt), so it doesn't block — but "All translated." would be a
        # lie, which is the whole reason the summary carries pending keys.
        summary = {"locales": {"ar": {"missing": [], "pending": ["a", "b", "c"]}}}
        check = self._check_with(summary)
        self.assertEqual(check.status, readiness_module.PASS)
        self.assertIn("3 still English placeholder(s)", check.detail)
        self.assertNotIn("All translated", check.detail)

    def test_a_fully_translated_catalogue_says_so(self):
        check = self._check_with({"locales": {"ar": {"missing": [], "pending": []}}})
        self.assertEqual((check.status, check.detail), (readiness_module.PASS, "All translated."))

    def test_a_language_absent_from_the_summary_is_absent_not_unknown(self):
        # A language nobody has started an interface for has zero strings — that
        # is a fact, and it should block a launch rather than shrug.
        check = self._check_with({"locales": {"es": {"missing": [], "pending": []}}})
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual(check.detail, "No ar catalogue.")

    def test_no_summary_is_unknown(self):
        with mock.patch("library.readiness.CATALOGUE_SUMMARY", Path("/nonexistent/x.json")):
            check = readiness_module._ui_check(self.lang)
        self.assertEqual(check.status, readiness_module.UNKNOWN)

    def test_a_malformed_row_is_unknown_not_a_count(self):
        check = self._check_with({"locales": {"ar": {"missing": "", "pending": []}}})
        self.assertEqual(check.status, readiness_module.UNKNOWN)

    def test_the_committed_summary_is_shaped_the_way_the_reader_expects(self):
        # Guards the courier itself: the file is generated by an npm script in
        # the other half of the repo, so nothing in Python fails if its shape
        # changes — this does.
        data = json.loads(readiness_module.CATALOGUE_SUMMARY.read_text("utf-8"))
        self.assertEqual(data["base_locale"], "en")
        for code in ("en", "ar", "es", "sw", "lg", "pt"):
            self.assertIn(code, data["locales"], code)
            for field in ("missing", "pending"):
                self.assertIsInstance(data["locales"][code][field], list, (code, field))
        self.assertEqual(data["locales"]["en"]["pending"], [], "English can't be pending")


class PlanThresholdTests(TestCase):
    """The reading-plan bar — the one threshold whose default was wrong.

    `min_plans` shipped at 0 because of a claim that no non-English language had
    a published plan. It came from a database with `seed_plans` unrun; every live
    language has them. These pin both halves of the correction: what a new
    language inherits, and what the check does with it.
    """

    def _report(self, lang):
        # Bible stubbed for the same reason as ReadinessReportTests — a real call
        # makes the verdict depend on whether the sandbox has network.
        with mock.patch.object(
            readiness_module,
            "_bible_check",
            return_value=readiness_module.Check(
                "bible", "Bible", readiness_module.PASS, "stubbed"
            ),
        ):
            return {c.key: c for c in readiness_module.report(lang).checks}

    def test_a_new_language_must_have_a_translated_plan(self):
        # The model default, which is what a language created from the admin gets.
        fresh = Language.objects.create(code="hi", name="Hindi", native_name="हिन्दी")
        self.assertEqual(fresh.min_plans, 1)

    def test_the_migration_left_launched_languages_alone(self):
        # A live language's bar is a record of what it cleared, not a decision
        # still open, so the correction deliberately skipped those rows.
        for code in ("es", "sw", "lg", "pt"):
            self.assertEqual(Language.objects.get(code=code).min_plans, 0, code)

    def test_the_migration_raised_the_unlaunched_one(self):
        self.assertEqual(Language.objects.get(code="ar").min_plans, 1)

    def test_no_plan_fails_the_check(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        check = self._report(lang)["plans"]
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual((check.current, check.required), (0, 1))

    def test_a_published_plan_clears_it(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        Plan.objects.create(
            slug="p", language="es", title="Un plan", is_published=True
        )
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.PASS)

    def test_an_unpublished_plan_does_not_count(self):
        # Readiness asks what a reader can reach, not what exists in a table.
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        Plan.objects.create(slug="p", language="es", title="Un plan", is_published=False)
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.FAIL)

    def test_zero_still_disables_the_check(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 0
        lang.save(update_fields=["min_plans"])
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.SKIPPED)
