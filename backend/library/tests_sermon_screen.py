"""`library.sermon_screen`: the checks `screen_sermons` runs before an import.

Each case is the trap a sermon batch actually fell into.
"""

import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from library import sermon_screen

PRINTED = (
    "<p>Come unto me, all ye that labour and are heavy laden, and I will give you rest. "
    "He that believeth on him hath everlasting life, and thou shalt be saved.</p>"
)
MODERNISED = (
    "<p>Come to Me, all you that labor and are heavy laden, and I will give you rest. "
    "He that believes in Him has everlasting life, and you shall be saved.</p>"
)


class SermonScreenTests(SimpleTestCase):
    def test_the_modernised_rewrite_reads_thin_on_archaisms(self):
        printed, modern = (
            sermon_screen.archaism_density(sermon_screen.plain(t)) for t in (PRINTED, MODERNISED)
        )
        self.assertGreater(printed[0], sermon_screen.MODERN_ARCHAISMS)
        self.assertGreater(printed[1], sermon_screen.MODERN_ETH)
        self.assertLess(modern[1], sermon_screen.MODERN_ETH)

    def test_a_page_split_is_a_lower_case_paragraph_after_an_unfinished_one(self):
        self.assertEqual(sermon_screen.page_splits("<p>It is not al- </p><p>ways so.</p>"), 0)
        self.assertEqual(sermon_screen.page_splits("<p>sorely put </p><p>to it and</p>"), 1)
        self.assertEqual(sermon_screen.page_splits("<p>Amen.</p><p>And then</p>"), 0)

    def test_overlap_finds_a_sermon_already_inside_a_book(self):
        text = " ".join(f"word{i} alpha beta gamma" for i in range(60))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "books").mkdir()
            (root / "sermons").mkdir()
            rows = [{"model": "library.chapter", "fields": {"body_text": text}}]
            (root / "books" / "holiness.en.json").write_text(json.dumps(rows))
            index = sermon_screen.LibraryIndex(root)
            self.assertEqual(index.overlap(text, own_slug="let-any-man-come"), ("holiness", 100))
            self.assertEqual(index.overlap("nothing like it at all here " * 20), ("", 0))

    def test_flags_name_each_failure(self):
        class Empty:
            def overlap(self, text, own_slug=""):
                return "", 0

        body = MODERNISED + "<p>[Owing to the great length of this sermon it is abridged.]</p>"
        flags = sermon_screen.screen("rest", body, Empty(), slug_taken=True).flags
        self.assertIn("modernised?", flags)
        self.assertIn("slug taken", flags)
        self.assertIn("ends on furniture", flags)
        self.assertIn("short", flags)
        self.assertEqual(sermon_screen.screen("ok", PRINTED * 400, Empty()).flags, [])

    def test_an_imported_sermons_own_rows_are_not_a_collision(self):
        taken = {"books": {"holiness"}, "articles": set(), "sermons": {"rest"}}
        self.assertFalse(sermon_screen.collides("rest", taken, imported=True))
        self.assertTrue(sermon_screen.collides("rest", taken, imported=False))
        self.assertTrue(sermon_screen.collides("holiness", taken, imported=True))
