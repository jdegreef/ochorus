"""seed_translation_notes: the review queue's flags are only as good as this."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from .models import TranslationNote


def _write(root: Path, kind: str, name: str, payload: dict) -> None:
    d = root / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(payload), encoding="utf-8")


BASE = {
    "kind": "sermon",
    "slug": "possibilities",
    "language": "sw",
    "job_issue": 423,
    "pull_request": 897,
    "references": [
        {
            "reference": "Mark 9:23",
            "status": "mined",
            "source_file": "jesus-himself-2.sw.json",
            "block_index": 0,
        },
        {"reference": "Acts 26:18", "status": "self_rendered"},
    ],
}


class SeedTranslationNotesTests(TestCase):
    def _seed(self, payloads, name="possibilities.sw.json"):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind, payload in payloads:
                _write(root, kind, name, payload)
            call_command("seed_translation_notes", path=str(root), verbosity=0)

    def test_creates_rows_with_provenance(self):
        self._seed([("sermon", BASE)])
        self.assertEqual(TranslationNote.objects.count(), 2)
        mined = TranslationNote.objects.get(status="mined")
        self.assertEqual(mined.reference, "Mark 9:23")
        self.assertEqual(mined.source_file, "jesus-himself-2.sw.json")
        self.assertEqual(mined.block_index, 0)
        self.assertEqual(mined.job_issue, 423)
        self.assertEqual(mined.pull_request, 897)

    def test_rerun_is_idempotent(self):
        self._seed([("sermon", BASE)])
        self._seed([("sermon", BASE)])
        self.assertEqual(TranslationNote.objects.count(), 2)

    def test_replace_not_merge_so_a_corrected_note_disappears(self):
        """A reference removed from the file must leave the database."""
        self._seed([("sermon", BASE)])
        trimmed = {**BASE, "references": BASE["references"][:1]}
        self._seed([("sermon", trimmed)])
        self.assertEqual(TranslationNote.objects.count(), 1)
        self.assertFalse(TranslationNote.objects.filter(reference="Acts 26:18").exists())

    def test_other_translations_are_untouched(self):
        self._seed([("sermon", BASE)])
        other = {**BASE, "language": "pt", "references": [
            {"reference": "Mark 9:23", "status": "self_rendered"}
        ]}
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "sermon", "possibilities.pt.json", other)
            call_command("seed_translation_notes", path=str(root), verbosity=0)
        self.assertEqual(TranslationNote.objects.filter(language="sw").count(), 2)
        self.assertEqual(TranslationNote.objects.filter(language="pt").count(), 1)

    def test_malformed_file_is_skipped_not_fatal(self):
        """Review metadata must never take a release down with it."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sermon").mkdir(parents=True)
            (root / "sermon" / "broken.sw.json").write_text("{not json", encoding="utf-8")
            _write(root, "sermon", "possibilities.sw.json", BASE)
            call_command("seed_translation_notes", path=str(root), verbosity=0)
        self.assertEqual(TranslationNote.objects.count(), 2)

    def test_bad_status_is_rejected(self):
        bad = {**BASE, "references": [{"reference": "Mark 9:23", "status": "guessed"}]}
        self._seed([("sermon", bad)])
        self.assertEqual(TranslationNote.objects.count(), 0)

    def test_missing_directory_is_a_noop(self):
        call_command("seed_translation_notes", path="/nonexistent/notes", verbosity=0)
        self.assertEqual(TranslationNote.objects.count(), 0)


class ShippedNotesTests(TestCase):
    """The in-repo notes must load, and match the translation they describe."""

    def test_repo_notes_seed_and_are_well_formed(self):
        call_command("seed_translation_notes", verbosity=0)
        rows = TranslationNote.objects.filter(
            kind="sermon", slug="the-possibilities-of-faith", language="sw"
        )
        self.assertEqual(rows.count(), 40)
        self.assertEqual(rows.filter(status="mined").count(), 16)
        self.assertEqual(rows.filter(status="self_rendered").count(), 24)
        # Every mined verse cites where its wording came from — that citation is
        # the whole reason a reviewer can skip it.
        for r in rows.filter(status="mined"):
            self.assertTrue(r.source_file, f"{r.reference} is mined but cites no source")

    def test_purity_of_heart_es_notes_seed(self):
        # A malformed file is skipped, not fatal — so without this pin the book's
        # 38-site review queue could silently seed zero rows.
        call_command("seed_translation_notes", verbosity=0)
        rows = TranslationNote.objects.filter(
            kind="book", slug="purity-of-heart", language="es"
        )
        self.assertEqual(rows.count(), 38)
        self.assertEqual(rows.filter(status="self_rendered").count(), 38)
        self.assertEqual(set(rows.values_list("job_issue", flat=True)), {516})
        self.assertEqual(set(rows.values_list("pull_request", flat=True)), {942})
