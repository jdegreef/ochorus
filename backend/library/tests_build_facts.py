"""library/build_facts.py — production's DB-owned facts, carried to a build DB.

The round trip these pin: export from one DB (production), apply to a DB seeded
from the repo (the web build's throwaway API), and the reader-visible decisions
only production holds — live languages, publish and review state, approved
quotes and bios — come out the same, while content only one side has is left
alone or reported, never invented.
"""

import json
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .build_facts import FORMAT, VERSION, apply_facts, export_facts, validate
from .models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Language,
    Quote,
    Sermon,
)


class BuildFactsRoundTripTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        self.book_en = Book.objects.create(
            author=self.author, slug="with-christ", language="en", title="With Christ"
        )
        self.book_es = Book.objects.create(
            author=self.author, slug="with-christ", language="es", title="Con Cristo",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        self.sermon = Sermon.objects.create(
            author=self.author, slug="a-sermon", language="en", title="A sermon"
        )
        ch = Chapter.objects.create(book=self.book_en, order=1, title="One", body_html="<p>a</p>")
        self.quote = Quote.objects.create(
            slug="andrew-murray-q1", author=self.author, text="A long enough sentence.",
            chapter=ch, paragraph=1, reviewed=False,
        )
        self.bio = AuthorTranslation.objects.create(
            author=self.author, language="es", bio="Texto del repo.", reviewed=False
        )

    def _production_decisions(self):
        """What an admin does in production that no file records."""
        Language.objects.filter(code="ar").update(status=Language.Status.LIVE)
        Language.objects.filter(code="es").update(native_name="Español (editado)")
        Language.objects.create(code="zz", name="Test", native_name="Testish",
                                status=Language.Status.LIVE, sort_order=99)
        Book.objects.filter(pk=self.book_es.pk).update(source_type=Book.SourceType.AI_REVIEWED)
        Sermon.objects.filter(pk=self.sermon.pk).update(is_published=False)
        Quote.objects.filter(pk=self.quote.pk).update(reviewed=True)
        AuthorTranslation.objects.filter(pk=self.bio.pk).update(
            reviewed=True, bio="Texto aprobado.", bio_html="<p>Aprobado.</p>"
        )

    def _reset_to_repo(self):
        """What a fresh DB seeded from the repo looks like instead."""
        Language.objects.filter(code="ar").update(status=Language.Status.DRAFT)
        Language.objects.filter(code="es").update(native_name="Español")
        Language.objects.filter(code="zz").delete()
        Book.objects.filter(pk=self.book_es.pk).update(source_type=Book.SourceType.AI_UNREVIEWED)
        Sermon.objects.filter(pk=self.sermon.pk).update(is_published=True)
        Quote.objects.filter(pk=self.quote.pk).update(reviewed=False)
        AuthorTranslation.objects.filter(pk=self.bio.pk).update(
            reviewed=False, bio="Texto del repo.", bio_html=""
        )

    def test_round_trip_restores_production_decisions(self):
        self._production_decisions()
        facts = json.loads(json.dumps(export_facts()))  # through JSON, as on disk
        self._reset_to_repo()

        report = apply_facts(facts)

        self.assertEqual(Language.objects.get(code="ar").status, Language.Status.LIVE)
        self.assertEqual(Language.objects.get(code="es").native_name, "Español (editado)")
        self.assertEqual(Language.objects.get(code="zz").status, Language.Status.LIVE)
        self.assertIn("zz", report["languages"]["created"])
        self.book_es.refresh_from_db()
        self.assertEqual(self.book_es.source_type, Book.SourceType.AI_REVIEWED)
        self.sermon.refresh_from_db()
        self.assertFalse(self.sermon.is_published)
        self.quote.refresh_from_db()
        self.assertTrue(self.quote.reviewed)
        self.bio.refresh_from_db()
        self.assertTrue(self.bio.reviewed)
        self.assertEqual(self.bio.bio, "Texto aprobado.")
        self.assertEqual(self.bio.bio_html, "<p>Aprobado.</p>")
        self.assertEqual(report["missing"], {})

    def test_reapplying_changes_nothing(self):
        facts = export_facts()
        report = apply_facts(facts)
        for label in ("books", "sermons", "articles", "plans", "topics", "quotes"):
            self.assertEqual(report["changed"][label], 0, label)

    def test_content_only_this_checkout_has_keeps_its_seed_default(self):
        facts = export_facts()
        new = Book.objects.create(
            author=self.author, slug="brand-new", language="en", title="New this commit"
        )
        apply_facts(facts)
        new.refresh_from_db()
        self.assertTrue(new.is_published)

    def test_content_only_production_has_is_reported(self):
        facts = export_facts()
        facts["books"].append(["admin-upload", "en", True, "public_domain"])
        report = apply_facts(facts)
        self.assertEqual(report["missing"]["books"], ["admin-upload:en"])
        self.assertFalse(Book.objects.filter(slug="admin-upload").exists())

    def test_a_language_production_never_had_stays_dark(self):
        facts = export_facts()
        facts["languages"] = [r for r in facts["languages"] if r["code"] != "pt"]
        Language.objects.filter(code="pt").update(status=Language.Status.LIVE)
        report = apply_facts(facts)
        self.assertEqual(Language.objects.get(code="pt").status, Language.Status.DRAFT)
        self.assertIn("pt", report["languages"]["darkened"])


class BuildFactsValidationTests(TestCase):
    def test_rejects_foreign_documents(self):
        for bad in (None, [], {}, {"format": "other", "version": VERSION}):
            with self.assertRaises(ValueError):
                validate(bad)

    def test_rejects_another_version(self):
        with self.assertRaises(ValueError):
            validate({"format": FORMAT, "version": VERSION + 1, "languages": [{"code": "en"}]})

    def test_rejects_a_document_without_english(self):
        # English is the source language; without it the export came from the
        # wrong database, and applying it would darken every page.
        with self.assertRaises(ValueError):
            validate({"format": FORMAT, "version": VERSION, "languages": [{"code": "es"}]})


# The command refuses anything but the build's SQLite file; CI's test DB is
# Postgres, so the tests stand in for the build DB explicitly.
_BUILD_DB = "library.management.commands.apply_build_facts._is_build_db"


@mock.patch(_BUILD_DB, return_value=True)
class BuildFactsCommandTests(TestCase):
    def test_export_then_apply_through_the_commands(self, _db):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            call_command("export_build_facts", "--out", str(path), stderr=_Null())
            self.assertEqual(json.loads(path.read_text())["format"], FORMAT)
            call_command("apply_build_facts", str(path), stdout=_Null())

    def test_apply_fails_when_production_has_too_much_the_repo_lacks(self, _db):
        facts = export_facts()
        facts["books"] = [[f"upload-{i}", "en", True, "public_domain"] for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text(json.dumps(facts))
            with self.assertRaises(CommandError):
                call_command("apply_build_facts", str(path), "--max-missing", "2", stdout=_Null())
            call_command("apply_build_facts", str(path), "--max-missing", "3", stdout=_Null())

    def test_apply_refuses_a_database_that_is_not_the_build_db(self, is_build_db):
        is_build_db.return_value = False
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text(json.dumps(export_facts()))
            with self.assertRaises(CommandError):
                call_command("apply_build_facts", str(path), stdout=_Null())

    def test_apply_rejects_a_bad_file(self, _db):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.json"
            path.write_text('{"format": "nope"}')
            with self.assertRaises(CommandError):
                call_command("apply_build_facts", str(path), stdout=_Null())


class _Null:
    def write(self, *_a, **_k):
        pass

    def flush(self):
        pass
