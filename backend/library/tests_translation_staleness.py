"""Translation staleness: the per-deploy fingerprint refresh, the coverage
matrix's `stale` languages, and the "still current" re-baseline."""

from __future__ import annotations

import io

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import translation_staleness as ts
from .models import AdminAction, Article, Author, Book, Chapter, Sermon


class TranslationStalenessTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        self.sw = Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        for book, body in ((self.en, "<p>Pride</p>"), (self.sw, "<p>Kiburi</p>")):
            Chapter.objects.create(book=book, order=1, title="One", body_html=body)

    def _edit(self, book, body):
        Chapter.objects.filter(book=book, order=1).update(body_html=body)

    def test_first_refresh_baselines_every_translation(self):
        counts = ts.refresh("book")
        self.en.refresh_from_db()
        self.sw.refresh_from_db()
        self.assertTrue(self.en.content_digest)
        self.assertEqual(self.sw.english_digest, self.en.content_digest)
        self.assertEqual(self.en.english_digest, "", "the English row has no baseline")
        self.assertEqual(counts["rebaselined"], 1)
        self.assertEqual(ts.stale_languages("book"), {})

    def test_an_original_language_edition_is_never_a_stale_translation(self):
        # Pascal's own French beside Trotter's English: the English is the
        # translation, so an English fix must not flag the French as stale.
        fr = Book.objects.create(
            author=self.en.author, slug="humility", language="fr", title="Humilité",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
        )
        Chapter.objects.create(book=fr, order=1, title="Un", body_html="<p>Orgueil</p>")
        ts.refresh("book")
        self._edit(self.en, "<p>Pride, corrected</p>")
        counts = ts.refresh("book")
        fr.refresh_from_db()
        self.assertEqual(fr.english_digest, "")
        self.assertEqual(counts["stale"], 1, "only the sw translation")
        self.assertEqual(ts.stale_languages("book"), {"humility": ["sw"]})

    def test_refresh_is_idempotent(self):
        ts.refresh("book")
        self.assertEqual(ts.refresh("book"), {"updated": 0, "rebaselined": 0, "stale": 0})

    def test_an_english_change_makes_the_translation_stale(self):
        ts.refresh("book")
        self._edit(self.en, "<p>Pride, corrected</p>")
        self.assertEqual(ts.refresh("book")["stale"], 1)
        self.assertEqual(ts.stale_languages("book"), {"humility": ["sw"]})
        # And it stays stale deploy after deploy until something happens to it.
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {"humility": ["sw"]})

    def test_a_new_chapter_in_english_is_a_change(self):
        ts.refresh("book")
        Chapter.objects.create(book=self.en, order=2, title="Two", body_html="<p>More</p>")
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {"humility": ["sw"]})

    def test_retranslating_rebaselines(self):
        """The translation's own text changed (re-translated, or chapters topped
        up) → it was made from the English as it now stands."""
        ts.refresh("book")
        self._edit(self.en, "<p>Pride, corrected</p>")
        ts.refresh("book")
        self._edit(self.sw, "<p>Kiburi, tena</p>")
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {})

    def test_english_and_translation_fixed_in_one_deploy_is_not_stale(self):
        ts.refresh("book")
        self._edit(self.en, "<p>Pride, corrected</p>")
        self._edit(self.sw, "<p>Kiburi, kimesahihishwa</p>")
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {})

    def test_mark_current_clears_it_and_survives_the_next_deploy(self):
        ts.refresh("book")
        self._edit(self.en, "<p>Pride (typo fixed)</p>")
        ts.refresh("book")
        self.assertTrue(ts.mark_current("book", "humility", "sw"))
        self.assertEqual(ts.stale_languages("book"), {})
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {})

    def test_mark_current_refuses_english_and_unknown(self):
        ts.refresh("book")
        self.assertFalse(ts.mark_current("book", "humility", "en"))
        self.assertFalse(ts.mark_current("book", "nope", "sw"))
        self.assertFalse(ts.mark_current("book", "humility", "fr"))

    def test_sermons_and_articles(self):
        author = Author.objects.get(slug="am")
        for lang, body in (("en", "<p>Grace</p>"), ("es", "<p>Gracia</p>")):
            # A translation ships ai_unreviewed; the model's default,
            # public_domain, means an original-language edition.
            kind = Book.SourceType.PUBLIC_DOMAIN if lang == "en" else Book.SourceType.AI_UNREVIEWED
            Sermon.objects.create(
                author=author, slug="grace", language=lang, title="G", body_html=body, source_type=kind
            )
            Article.objects.create(slug="prayer", language=lang, h1="P", body_html=body, source_type=kind)
        call_command("refresh_translation_digests", stdout=io.StringIO())
        Sermon.objects.filter(slug="grace", language="en").update(title="Grace abounding")
        Article.objects.filter(slug="prayer", language="en").update(body_html="<p>More</p>")
        call_command("refresh_translation_digests", stdout=io.StringIO())
        self.assertEqual(ts.stale_languages("sermon"), {"grace": ["es"]})
        self.assertEqual(ts.stale_languages("article"), {"prayer": ["es"]})
        self.assertEqual(ts.stale_languages("book"), {})

    @override_settings(DEBUG=True)
    def test_coverage_lists_stale_and_mark_current_endpoint_clears_it(self):
        client = APIClient()
        ts.refresh("book")
        self._edit(self.en, "<p>Pride, corrected</p>")
        ts.refresh("book")

        books = {b["slug"]: b for b in client.get("/api/admin/coverage/").data["books"]}
        self.assertEqual(books["humility"]["stale"], ["sw"])

        url = "/api/admin/coverage/mark-current/"
        self.assertEqual(client.post(url, {"kind": "book"}, format="json").status_code, 400)
        self.assertEqual(
            client.post(url, {"kind": "book", "slug": "nope", "language": "sw"}, format="json").status_code,
            404,
        )
        res = client.post(url, {"kind": "book", "slug": "humility", "language": "sw"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            AdminAction.objects.filter(
                action=AdminAction.Action.TRANSLATION_MARK_CURRENT, target="book:humility:sw"
            ).exists()
        )
        books = {b["slug"]: b for b in client.get("/api/admin/coverage/").data["books"]}
        self.assertNotIn("stale", books["humility"])


class ReviewedHydeTranslationMigrationTests(TestCase):
    """0168: reviewed John Hyde translations take the corrected files, re-gated."""

    def _run(self):
        import importlib

        from django.apps import apps as global_apps

        mod = importlib.import_module("library.migrations.0168_correct_reviewed_hyde_translations")
        mod.correct_reviewed(global_apps, None)
        return mod

    def setUp(self):
        from .models import AuthorTranslation

        self.AT = AuthorTranslation
        self.hyde = Author.objects.create(slug="john-hyde", name="John Hyde")

    def test_reviewed_row_takes_the_files_and_is_regated(self):
        tr = self.AT.objects.create(
            author=self.hyde, language="es", bio="viejo", bio_html="<p>Sialkot</p>",
            faq=[{"q": "x", "a": "y"}], reviewed=True, source_stale=True,
        )
        mod = self._run()
        tr.refresh_from_db()
        want = mod.corrected_fields("es")
        self.assertEqual(set(want), {"bio", "bio_html", "faq"})
        for name, value in want.items():
            self.assertEqual(getattr(tr, name), value)
        self.assertFalse(tr.reviewed, "AI-written wording must be re-gated for review")
        self.assertFalse(tr.source_stale)

    def test_unreviewed_and_other_authors_are_left_to_the_seed(self):
        other = Author.objects.create(slug="someone-else", name="Someone")
        unreviewed = self.AT.objects.create(author=self.hyde, language="pt", bio="velho")
        elsewhere = self.AT.objects.create(author=other, language="es", bio="otro", reviewed=True)
        self._run()
        unreviewed.refresh_from_db()
        elsewhere.refresh_from_db()
        self.assertEqual(unreviewed.bio, "velho")
        self.assertEqual((elsewhere.bio, elsewhere.reviewed), ("otro", True))

    def test_reviewed_row_already_matching_keeps_its_approval(self):
        import importlib

        mod = importlib.import_module("library.migrations.0168_correct_reviewed_hyde_translations")
        tr = self.AT.objects.create(
            author=self.hyde, language="sw", reviewed=True, **mod.corrected_fields("sw")
        )
        self._run()
        tr.refresh_from_db()
        self.assertTrue(tr.reviewed)


class TypographyIsNotAChangeTests(TestCase):
    """A typography sweep of the English must not flag its translations."""

    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.en = Book.objects.create(author=author, slug="w", language="en", title="W")
        self.sw = Book.objects.create(
            author=author, slug="w", language="sw", title="W",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(
            book=self.en, order=1, title="One",
            body_html='<p>Pray -- really pray -- and say &quot;yes&quot;...</p>',
        )
        Chapter.objects.create(book=self.sw, order=1, title="Moja", body_html="<p>Omba</p>")
        ts.refresh("book")

    def _edit(self, body):
        Chapter.objects.filter(book=self.en, order=1).update(body_html=body)

    def test_typographic_form_folds_only_typography(self):
        f = ts.typographic_form
        self.assertEqual(f("a -- b"), f("a—b"))
        self.assertEqual(f("a – b"), f("a — b"))
        self.assertEqual(f("“so”"), f('"so"'))
        self.assertEqual(f("it’s"), f("it's"))
        self.assertEqual(f("wait…"), f("wait..."))
        self.assertEqual(f("a&nbsp; b"), f("a b"))
        # Words, case and markup still count.
        self.assertNotEqual(f("GOD"), f("God"))
        self.assertNotEqual(f("<p>a</p><p>b</p>"), f("<p>a b</p>"))
        self.assertNotEqual(f("self-righteous"), f("self—righteous"))

    def test_a_typography_sweep_leaves_translations_current(self):
        self._edit("<p>Pray — really pray — and say “yes”…</p>")
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {})

    def test_a_wording_change_still_flags_them(self):
        self._edit("<p>Pray — really pray — and say “no”…</p>")
        ts.refresh("book")
        self.assertEqual(ts.stale_languages("book"), {"w": ["sw"]})


class RefingerprintMigrationTests(TestCase):
    """0178 moves every digest to the typographic rule without changing which
    translations are stale — except those #4936's dashes alone had flagged."""

    @staticmethod
    def _old(parts):
        import hashlib

        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8"))
            h.update(ts._SEP.encode())
        return h.hexdigest()

    def test_state_carries_over_and_4936s_typography_flags_clear(self):
        import importlib

        from django.apps import apps

        mig = importlib.import_module("library.migrations.0178_typographic_translation_digests")
        (kind, pre_slug), pre_digest = next(
            (k, v) for k, v in mig.PRE_4936.items() if k[0] == "book"
        )
        author = Author.objects.create(slug="x", name="X")

        def edition(slug, lang, body):
            b = Book.objects.create(
                author=author, slug=slug, language=lang, title=slug,
                source_type=Book.SourceType.AI_UNREVIEWED if lang != "en" else "",
            )
            Chapter.objects.create(book=b, order=1, title="T", body_html=body)
            return b

        en = edition("cur", "en", "<p>Text -- here</p>")
        current = edition("cur", "sw", "<p>Maandishi</p>")
        stale = edition("cur", "lg", "<p>Ebiwandiikiddwa</p>")
        dash_en = edition(pre_slug, "en", "<p>After the sweep — here</p>")
        dash_flagged = edition(pre_slug, "es", "<p>Texto</p>")

        old_en = self._old(["1", "T", "<p>Text -- here</p>"])
        Book.objects.filter(pk=en.pk).update(content_digest=old_en)
        Book.objects.filter(pk=current.pk).update(english_digest=old_en)
        Book.objects.filter(pk=stale.pk).update(english_digest="0" * 64)
        Book.objects.filter(pk=dash_en.pk).update(
            content_digest=self._old(["1", "T", "<p>After the sweep — here</p>"])
        )
        Book.objects.filter(pk=dash_flagged.pk).update(english_digest=pre_digest)

        mig.refingerprint(apps, None)
        # The deploy's own refresh then finds nothing to change...
        self.assertEqual(ts.refresh("book")["rebaselined"], 0)
        # ...and only the translation that was already behind stays flagged.
        self.assertEqual(ts.stale_languages("book"), {"cur": ["lg"]})
