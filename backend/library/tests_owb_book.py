"""`build_owb_book`'s reading of an Open Word Bible checkout.

A tiny fake checkout stands in for the real one: only the files `Source` reads,
holding just enough sentences to show each rule. The rules are the ones the
Psalms and Genesis need that the Gospel of John did not: chapters by their
ENGLISH number, psalm titles, and verse set line by line.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from library.management.commands.build_owb_book import Source


def record(rid: str, refs: list[str], text: str) -> dict:
    return {
        "id": rid,
        "refs": refs,
        "renderings": {"en": {"B": text}},
        "source": {"tokens": [f"w-{rid}"]},
    }


class FakeCheckout:
    """A git repository shaped like OWB's, with the given books' sentences."""

    def __init__(self, books: dict[str, dict[str, list[dict]]], english: dict):
        self.dir = tempfile.TemporaryDirectory()
        root = self.root = Path(self.dir.name)
        (root / "data" / "hbo").mkdir(parents=True)
        (root / "data" / "headings").mkdir()
        (root / "data" / "books.json").write_text(
            json.dumps({"books": {code: {"en": name} for code, name in
                                  (("GEN", "Genesis"), ("PSA", "Psalms"))}})
        )
        (root / "data" / "versification.json").write_text(json.dumps({"english": english}))
        for code, chapters in books.items():
            (root / "content" / code).mkdir(parents=True)
            for chapter, records in chapters.items():
                (root / "content" / code / f"{code}.{chapter}.json").write_text(
                    json.dumps({"records": records})
                )
                # Every word runs on from the one before: one paragraph a chapter.
                verses = {
                    r["refs"][0]: [{"id": r["source"]["tokens"][0], "text": "x",
                                    "lemma": "x", "after": " "}]
                    for r in records
                }
                (root / "data" / "hbo" / f"{code}.{chapter}.json").write_text(
                    json.dumps({"verses": verses})
                )
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
             "commit", "-q", "--allow-empty", "-m", "fake"],
            check=True,
        )

    def close(self):
        self.dir.cleanup()


class EnglishChapterTests(SimpleTestCase):
    def test_a_verse_numbered_into_the_next_chapter_in_hebrew_stays_in_its_english_one(self):
        """Hebrew Genesis 32:1 is English 31:55, so it ends chapter 31."""
        fake = FakeCheckout(
            {"GEN": {
                "31": [record("GEN.31.54.s1", ["GEN.31.54"], "Jacob offered a sacrifice.")],
                "32": [
                    record("GEN.32.1.s1", ["GEN.32.1"], "Early in the morning Laban left."),
                    record("GEN.32.2.s1", ["GEN.32.2"], "Jacob went on his way."),
                ],
            }},
            {"GEN.32.1": ["GEN.31.55"], "GEN.32.2": ["GEN.32.1"]},
        )
        self.addCleanup(fake.close)
        chapters = Source(fake.root, "GEN").chapters()
        self.assertEqual(
            {c: [r["id"] for r in rs] for c, rs in chapters.items()},
            {31: ["GEN.31.54.s1", "GEN.32.1.s1"], 32: ["GEN.32.2.s1"]},
        )

    def test_its_heading_moves_on_with_the_passage_it_opens(self):
        """The heading OWB sets over Hebrew 32:1 opens the next English chapter."""
        fake = FakeCheckout(
            {"GEN": {"32": [
                record("GEN.32.1.s1", ["GEN.32.1"], "Early in the morning Laban left."),
                record("GEN.32.2.s1", ["GEN.32.2"], "Jacob went on his way."),
            ]}},
            {"GEN.32.1": ["GEN.31.55"], "GEN.32.2": ["GEN.32.1"]},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "headings" / "GEN.json").write_text(
            json.dumps({"headings": {"GEN.32.1.s1": {"en": "Angels meet Jacob"}}})
        )
        source = Source(fake.root, "GEN")
        chapters = source.chapters()
        self.assertEqual(source.chapter_html(31, chapters[31]), "<p>Early in the morning Laban left.</p>")
        self.assertTrue(source.chapter_html(32, chapters[32]).startswith("<h3>Angels meet Jacob</h3>"))


class PsalmTests(SimpleTestCase):
    def setUp(self):
        fake = FakeCheckout(
            {"PSA": {"3": [
                record("PSA.3.1.s1", ["PSA.3.1"], "A psalm of David,"),
                record("PSA.3.2.s1", ["PSA.3.2"], "when he fled from Absalom."),
                record("PSA.3.3.s1", ["PSA.3.3"],
                       "{{divine_name:LORD|Yahweh}}, how many! \\q Many rise against me."),
                record("PSA.3.4.s1", ["PSA.3.4"], "Many say \\q there is no help."),
            ]}},
            {"PSA.3.1": [], "PSA.3.2": [], "PSA.3.3": ["PSA.3.1"], "PSA.3.4": ["PSA.3.2"]},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "headings" / "PSA.json").write_text(
            json.dumps({"headings": {"PSA.3.1.s1": {"en": "A shield around me"}}})
        )
        self.source = Source(fake.root, "PSA")

    def html(self) -> str:
        chapter, records = next(iter(self.source.chapters().items()))
        self.assertEqual(chapter, 3, "a title stays in its own psalm")
        return self.source.chapter_html(chapter, records)

    def test_the_title_follows_the_heading_and_opens_the_psalm_in_italics(self):
        self.assertTrue(self.html().startswith(
            "<h3>A shield around me</h3>"
            "<p><em>A psalm of David, when he fled from Absalom.</em></p>"
        ))

    def test_each_line_and_each_verse_starts_a_line_of_its_own(self):
        self.assertTrue(self.html().endswith(
            "<p>LORD, how many!<br>Many rise against me.<br>"
            "Many say<br>there is no help.</p>"
        ))

    def test_prose_runs_its_lines_together(self):
        """The Gospel of John's rule, untouched: a book not in POETRY."""
        self.source.poetry = False
        self.assertIn("<p>LORD, how many! Many rise against me. Many say there is no help.</p>",
                      self.html())


class FusedTitleTests(SimpleTestCase):
    """Where the Hebrew counts a short title as part of verse 1 (Psalm 23)."""

    def build(self, first: str) -> str:
        fake = FakeCheckout(
            {"PSA": {"23": [record("PSA.23.1.s1", ["PSA.23.1"], first)]}}, {}
        )
        self.addCleanup(fake.close)
        source = Source(fake.root, "PSA")
        return source.chapter_html(23, source.chapters()[23])

    def test_the_title_sentences_are_peeled_into_italics(self):
        self.assertEqual(
            self.build("A psalm of David. \\q The LORD is my shepherd."),
            "<p><em>A psalm of David.</em></p><p>The LORD is my shepherd.</p>",
        )
        self.assertEqual(
            self.build("For the music director. Of David. I have taken refuge."),
            "<p><em>For the music director. Of David.</em></p><p>I have taken refuge.</p>",
        )

    def test_a_psalm_that_opens_in_praise_keeps_its_first_words(self):
        self.assertEqual(
            self.build("Praise the LORD! \\q Praise God in his holy place."),
            "<p>Praise the LORD!<br>Praise God in his holy place.</p>",
        )
