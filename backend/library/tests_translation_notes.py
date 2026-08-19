"""seed_translation_notes: the review queue's flags are only as good as this."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .management.commands.seed_translation_notes import notes_path
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

    def test_humility_2_es_notes_seed(self):
        # The other half of #942's es couple, pinned for the same reason.
        call_command("seed_translation_notes", verbosity=0)
        rows = TranslationNote.objects.filter(
            kind="book", slug="humility-2", language="es"
        )
        self.assertEqual(rows.count(), 77)
        self.assertEqual(rows.filter(status="self_rendered").count(), 76)
        self.assertEqual(set(rows.values_list("job_issue", flat=True)), {520})
        self.assertEqual(set(rows.values_list("pull_request", flat=True)), {942})
        mined = rows.get(status="mined")
        self.assertEqual(mined.reference, "Matthew 11:29")
        self.assertTrue(mined.source_file, "mined but cites no source")


# --- Coverage: does every translation carry its review notes? ----------------

BACKLOG_PATH = Path(__file__).resolve().parent / "data" / "translation_notes_backlog.json"


def translated_works() -> list[tuple[str, str, str]]:
    """``(kind, slug, language)`` for every shipped translation, sorted.

    A translation is any book or sermon content file whose language is not
    ``en``. ``en-modern`` counts: a contemporized edition comes off the same
    translate-then-review pipeline and its careful pass can reword a quotation,
    so its provenance is worth the same record.
    """
    from library.content_fixtures import BOOKS_DIR, SERMONS_DIR

    works = [
        (kind, slug, language)
        for kind, directory in (("book", BOOKS_DIR), ("sermon", SERMONS_DIR))
        for path in directory.glob("*.json")
        for slug, _, language in [path.name[: -len(".json")].rpartition(".")]
        if slug and language != "en"
    ]
    return sorted(works)


def works_missing_notes() -> set[str]:
    """``<kind>/<slug>.<language>`` for every translation with no notes file."""
    return {
        f"{kind}/{slug}.{language}"
        for kind, slug, language in translated_works()
        if not notes_path(kind, slug, language).exists()
    }


def read_backlog() -> set[str]:
    return set(json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))["uncovered"])


class NotesCoverageTests(SimpleTestCase):
    """Every NEW translation ships its review notes; the backlog only shrinks.

    A translation's scripture provenance — which verses were recovered verbatim
    from our own shipped corpus, and which the translator rendered itself — is
    worked out while the job runs and is unrecoverable afterwards. It cannot be
    backfilled in bulk: nothing in the shipped file records where its wording
    came from. So it is captured at ship time or not at all.

    It was mostly not at all. When this gate was written, **5 of 163** shipped
    book and sermon translations carried a notes file, and every other signal on
    the remaining 158 read done — issues closed, fixtures valid, CI green. One
    batch PR shipped ten jobs and zero notes. ``ShippedNotesTests`` above pins
    individual translations by hand, so a translation with no file at all was
    never examined by anything.

    The backlog is committed as data (``data/translation_notes_backlog.json``)
    rather than as a literal here, because there are 158 of them and because it
    is a work list somebody will want to sort and count. There is deliberately
    no ``--update-backlog`` command: an entry leaves the list when its notes
    ship, one line at a time, and the second test below fails if a stale entry
    is left behind. Fixture-only, no DB.
    """

    def test_every_new_translation_ships_its_notes(self):
        missing = sorted(works_missing_notes() - read_backlog())
        self.assertEqual(
            missing,
            [],
            "These translations ship no review notes:\n  "
            + "\n  ".join(missing)
            + "\n\nWrite fixtures/translation_notes/<kind>/<slug>.<language>.json "
            "listing every scripture reference the translation quotes, each "
            "`mined` (wording taken verbatim from a shipped *.<lang>.json, which "
            "`source_file` must name) or `self_rendered`. The review queue turns "
            "it into the row's 'N verses unverified' chip — without it a reviewer "
            "cannot tell which verses still need checking, and the provenance is "
            "gone once the run ends.",
        )

    def test_backlog_contains_no_covered_or_unknown_entries(self):
        backlog = read_backlog()
        fixed = sorted(backlog - works_missing_notes())
        self.assertEqual(
            fixed,
            [],
            "These entries no longer belong in the backlog — their notes have "
            "shipped, or the translation was renamed or removed. Delete them "
            f"from {BACKLOG_PATH.name} so the list can only shrink: {fixed}",
        )
