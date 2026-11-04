"""*A Cloud of Praying Witnesses*: what ships stays in step with the manuscript.

``build_praying_witnesses`` writes each volume's ``volume-NN.appendices.md``
from its manuscript and data file, and serializes the book to its fixture. A
manuscript or data edit without a rebuild would leave the committed appendices,
and the chapters ``seed_books`` ships, out of date — so this rebuilds every
volume in memory and compares both.
"""

import json

from django.test import SimpleTestCase

from library.content_fixtures import book_fixture_path
from library.management.commands.build_praying_witnesses import (
    SERIES_DIR,
    VOLUMES,
    chapter_rows,
)


class VolumesInStepTests(SimpleTestCase):
    def test_committed_appendices_and_fixture_match_the_manuscript(self):
        for volume, meta in VOLUMES.items():
            with self.subTest(volume=volume):
                rows, generated = chapter_rows(volume)
                committed = (SERIES_DIR / f"volume-{volume:02d}.appendices.md").read_text()
                self.assertEqual(
                    committed,
                    generated,
                    f"volume {volume}'s appendices are stale: run build_praying_witnesses {volume}",
                )
                fixture = json.loads(book_fixture_path(meta["slug"], "en").read_text())
                shipped = [
                    (r["fields"]["title"], r["fields"]["body_html"])
                    for r in sorted(fixture[1:], key=lambda r: r["fields"]["order"])
                ]
                self.assertEqual(
                    shipped,
                    rows,
                    f"{meta['slug']}.en.json is stale: run build_praying_witnesses {volume} "
                    "and serialize the book",
                )
