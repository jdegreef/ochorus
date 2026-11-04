"""*A Cloud of Praying Witnesses*: the generated appendices stay in step.

``build_praying_witnesses`` writes each volume's ``volume-NN.appendices.md``
from its manuscript and data file, and the file is committed so it can be read
like the chapters. A manuscript or data edit without a rebuild would leave the
committed appendices — and the book built from them — out of date, so this
regenerates every volume's and compares.
"""

from django.test import SimpleTestCase

from library.management.commands.build_praying_witnesses import (
    SERIES_DIR,
    VOLUMES,
    check_shape,
    volume_text,
)


class AppendicesInStepTests(SimpleTestCase):
    def test_committed_appendices_match_the_manuscript(self):
        for volume in VOLUMES:
            with self.subTest(volume=volume):
                sections, generated = volume_text(volume)
                check_shape(sections)
                committed = (SERIES_DIR / f"volume-{volume:02d}.appendices.md").read_text()
                self.assertEqual(
                    committed,
                    generated,
                    f"volume {volume}'s appendices are stale: run build_praying_witnesses {volume}",
                )
