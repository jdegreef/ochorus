"""The on-disk Bible store answers exactly what the bundles in memory did.

``scripture.owb_verse``, ``translation.fetch_chapter("owb-…")`` and
``scripture._asv_text`` read ``bible_store``'s SQLite file instead of dicts
(to keep ~45 MB out of the API worker). These pin that the move changed no
answer: every verse id either OWB bundle carries, every chapter, and the ASV
against pythonbible itself.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from library import bible_store, scripture, translation


class OwbStoreMatchesTheBundleTests(SimpleTestCase):
    def test_every_verse_id_answers_as_the_bundle_does(self):
        for language in ("en", "am"):
            verses, joined = scripture._owb(language)
            for vid in sorted(set(verses) | set(joined)):
                for probe in (vid - 1, vid, vid + 1):
                    first = joined.get(probe, probe)
                    text = verses.get(first)
                    expected = (first, text) if text else None
                    self.assertEqual(scripture.owb_verse(probe, language), expected, (language, probe))

    def test_every_chapter_comes_back_as_it_did(self):
        for language in ("en", "am"):
            verses, _joined = scripture._owb(language)
            for chapter in sorted({vid // 1000 for vid in verses}):
                base = chapter * 1000
                expected = [(vid, t) for vid, t in sorted(verses.items()) if base < vid < base + 1000]
                self.assertEqual(scripture.owb_chapter_verses(base, language), expected, (language, chapter))
            ref = translation.Ref("PSA", 23)
            self.assertEqual(
                [v["number"] for v in translation.fetch_chapter(f"owb-{language}", ref)["verses"]],
                [1, 2, 3, 4, 5, 6],
            )

    def test_a_joined_verse_answers_with_the_verse_that_holds_it(self):
        # 1 Kings 18:34 is printed under 18:33, in both languages.
        for language in ("en", "am"):
            self.assertEqual(scripture.owb_verse(11018034, language), scripture.owb_verse(11018033, language))
            self.assertEqual(scripture.owb_verse(11018034, language)[0], 11018033)

    def test_an_unbundled_language_still_raises_as_reading_its_file_did(self):
        with self.assertRaises(FileNotFoundError):
            scripture.owb_verse(43003016, "zz")


class AsvStoreMatchesPythonbibleTests(SimpleTestCase):
    def test_every_asv_verse_is_pythonbibles_text(self):
        import pythonbible as bible
        from pythonbible.formatter import get_bible

        ids = sorted(get_bible(scripture.VERSION, "plain_text_readers").verse_start_indices)
        self.assertGreater(len(ids), 31000)
        for vid in ids:
            self.assertEqual(scripture._asv_text(vid), bible.get_verse_text(vid, version=scripture.VERSION), vid)
        self.assertEqual(scripture._asv_text(43003099), "")  # no such verse
        # The Romans doxology OWB lacks still falls back to the ASV.
        self.assertEqual(scripture.reader_verse(45016025)[1], scripture.ASV_LABEL)


class StoreFileTests(SimpleTestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bundles = self.tmp / "bible"
        self.bundles.mkdir()
        shutil.copy(bible_store.BIBLE_DIR / "owb-en-b.json.gz", self.bundles)
        patcher = mock.patch.object(bible_store, "BIBLE_DIR", self.bundles)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_changed_bundle_is_a_new_file_and_the_old_one_goes(self):
        first = bible_store.ensure_built(self.tmp / "store")
        self.assertTrue(first.is_file())
        self.assertEqual(bible_store.ensure_built(self.tmp / "store"), first)  # built once
        shutil.copy(scripture.owb_path("am"), self.bundles)  # scripture's own folder, unpatched
        second = bible_store.ensure_built(self.tmp / "store")
        self.assertNotEqual(second, first)
        self.assertFalse(first.exists())
        self.assertEqual(sorted(p.name for p in (self.tmp / "store").iterdir()), [second.name])
