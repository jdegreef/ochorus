"""The painting credits the home hero shows are the curated manifest's own.

``scripts/export_art_credits.py`` writes ``library/data/art_credits.json``
(and the frontend's served copy, which ``artCredits.test.ts`` holds to this
one). If an artwork entry changes and the export is not re-run, the hero
would label a painting with a stale artist or title — this fails first.
"""

import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parent.parent


def _export():
    spec = importlib.util.spec_from_file_location(
        "export_art_credits", BACKEND / "scripts" / "export_art_credits.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArtCreditExportTests(SimpleTestCase):
    def test_committed_credits_match_the_manifest(self):
        export = _export()
        committed = (BACKEND / "library" / "data" / "art_credits.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            committed,
            export.render(),
            "art_credits.json is stale: run `cd backend && python scripts/export_art_credits.py`",
        )

    def test_every_credit_carries_artist_title_and_year_keys(self):
        for slug, row in _export().art_credits().items():
            self.assertEqual(set(row), {"artist", "title", "year", "credit"}, slug)
            self.assertTrue(row["artist"] and row["title"], slug)
