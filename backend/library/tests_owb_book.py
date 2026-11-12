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

from django.core.management.base import CommandError
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
        names = {"GEN": "Genesis", "PSA": "Psalms"} | {code: code.title() for code in books}
        (root / "data" / "books.json").write_text(
            json.dumps({"books": {code: {"en": name} for code, name in names.items()}})
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

    def test_a_mixed_book_sets_only_its_verse_line_by_line(self):
        """Job's prose frame runs on; the speeches, which carry `\\q`, do not."""
        fake = FakeCheckout(
            {"JOB": {"3": [
                record("JOB.3.1.s1", ["JOB.3.1"], "After this Job spoke."),
                record("JOB.3.2.s1", ["JOB.3.2"], "He cursed the day."),
            ]}},
            {},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "books.json").write_text(json.dumps({"books": {"JOB": {"en": "Job"}}}))
        prose = Source(fake.root, "JOB")
        self.assertEqual(
            prose.chapter_html(3, prose.chapters()[3]),
            "<p>After this Job spoke. He cursed the day.</p>",
        )
        verse = FakeCheckout(
            {"JOB": {"3": [
                record("JOB.3.3.s1", ["JOB.3.3"], "Let the day perish, \\q and the night."),
                record("JOB.3.4.s1", ["JOB.3.4"], "Let it be darkness."),
            ]}},
            {},
        )
        self.addCleanup(verse.close)
        (verse.root / "data" / "books.json").write_text(json.dumps({"books": {"JOB": {"en": "Job"}}}))
        poem = Source(verse.root, "JOB")
        self.assertEqual(
            poem.chapter_html(3, poem.chapters()[3]),
            "<p>Let the day perish,<br>and the night.<br>Let it be darkness.</p>",
        )


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


class NewTestamentTests(SimpleTestCase):
    def test_revelation_12_18_opens_english_chapter_13(self):
        """OWB's hand-kept New Testament table: SBLGNT 12:18 is English 13:1."""
        fake = FakeCheckout(
            {"REV": {"12": [
                record("REV.12.17.s1", ["REV.12.17"], "The dragon was furious."),
                record("REV.12.18.s1", ["REV.12.18"], "It stood on the sand of the sea."),
            ]}},
            {},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "books.json").write_text(
            json.dumps({"books": {"REV": {"en": "Revelation"}}})
        )
        chapters = Source(fake.root, "REV").chapters()
        self.assertEqual(
            {c: [r["id"] for r in rs] for c, rs in chapters.items()},
            {12: ["REV.12.17.s1"], 13: ["REV.12.18.s1"]},
        )

    def test_marks_later_endings_are_set_apart_from_inside_16_8(self):
        fake = FakeCheckout(
            {"MRK": {"16": [
                record("MRK.16.8.s1", ["MRK.16.8"], "They were afraid."),
                record("MRK.16.8.s2", ["MRK.16.8"], "[They gave Peter a short report.]"),
                record("MRK.16.9.s1", ["MRK.16.9"], "[He appeared first to Mary.]"),
            ]}},
            {},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "books.json").write_text(
            json.dumps({"books": {"MRK": {"en": "Mark"}}})
        )
        source = Source(fake.root, "MRK")
        html = source.chapter_html(16, source.chapters()[16])
        self.assertTrue(html.startswith("<p>They were afraid.</p><p><em>The earliest manuscripts of Mark end at 16:8."))
        self.assertTrue(html.endswith("</blockquote>"))
        self.assertIn("<blockquote><p>[They gave Peter a short report.]", html)


class HeadingIntoNextChapterTests(SimpleTestCase):
    def test_a_verse_numbered_into_the_next_chapter_takes_its_heading(self):
        """SBLGNT Revelation 12:18 is English 13:1: chapter 13's heading moves up to it."""
        fake = FakeCheckout(
            {"REV": {"12": [record("REV.12.18.s1", ["REV.12.18"], "It stood on the sand.")],
                     "13": [record("REV.13.1.s1", ["REV.13.1"], "A beast rose from the sea.")]}},
            {},
        )
        self.addCleanup(fake.close)
        (fake.root / "data" / "books.json").write_text(json.dumps({"books": {"REV": {"en": "Revelation"}}}))
        (fake.root / "data" / "headings" / "REV.json").write_text(
            json.dumps({"headings": {"REV.13.1.s1": {"en": "The beast from the sea"}}})
        )
        source = Source(fake.root, "REV")
        self.assertTrue(
            source.chapter_html(13, source.chapters()[13]).startswith(
                "<h3>The beast from the sea</h3><p>It stood on the sand."
            )
        )


class VerseInProseTests(SimpleTestCase):
    """Outside the VERSE books, only what OWB breaks into lines is verse."""

    def build(self, code: str, records: list[dict]) -> str:
        fake = FakeCheckout({code: {"3": records}}, {})
        self.addCleanup(fake.close)
        source = Source(fake.root, code)
        return source.chapter_html(3, source.chapters()[3])

    def test_narrative_runs_on_and_the_song_after_it_is_set_in_lines(self):
        self.assertEqual(
            self.build("JOB", [
                record("JOB.3.1.s1", ["JOB.3.1"], "After this Job spoke."),
                record("JOB.3.2.s1", ["JOB.3.2"], "He said:"),
                record("JOB.3.3.s1", ["JOB.3.3"], "Let the day perish, \\q and the night."),
                record("JOB.3.4.s1", ["JOB.3.4"], "Let it be darkness."),
            ]),
            # The two prose verses run on; the line of verse starts a line,
            # and so does the verse after it.
            "<p>After this Job spoke. He said:<br>Let the day perish,<br>and the night.<br>Let it be darkness.</p>",
        )

    def test_prose_with_no_line_breaks_runs_on(self):
        self.assertEqual(
            self.build("JHN", [
                record("JHN.3.1.s1", ["JHN.3.1"], "There was a man."),
                record("JHN.3.2.s1", ["JHN.3.2"], "He came at night."),
            ]),
            "<p>There was a man. He came at night.</p>",
        )

    def test_a_verse_book_sets_every_verse_on_its_own_line(self):
        self.assertEqual(
            self.build("PRO", [
                record("PRO.3.1.s1", ["PRO.3.1"], "Do not forget my teaching."),
                record("PRO.3.2.s1", ["PRO.3.2"], "It will add years."),
            ]),
            "<p>Do not forget my teaching.<br>It will add years.</p>",
        )


class EmbedTests(SimpleTestCase):
    def test_a_placeholder_quotes_a_sentence_of_another_book(self):
        """From a chapter OWB splits into passage files (MAT.12.38-50.json)."""
        fake = FakeCheckout({"GEN": {"1": [record("GEN.1.1.s1", ["GEN.1.1"], "In the beginning.")]}}, {})
        self.addCleanup(fake.close)
        (fake.root / "content" / "MAT").mkdir()
        (fake.root / "content" / "MAT" / "MAT.12.38-50.json").write_text(json.dumps({"records": [
            record("MAT.12.42.s1", ["MAT.12.42"], "Someone greater than Solomon is here."),
        ]}))
        source = Source(fake.root, "GEN")
        self.assertEqual(
            source.embed("<p>{{OWB:MAT.12.42.s1}}</p>"),
            "<p>Someone greater than Solomon is here.</p>",
        )
        with self.assertRaises(CommandError):
            source.embed("{{OWB:MAT.12.43.s1}}")


class SummaryTests(SimpleTestCase):
    """OWB's chapter summaries, keyed by the source chapter, land in English ones."""

    def source(self, books, english, summaries) -> Source:
        fake = FakeCheckout(books, english)
        self.addCleanup(fake.close)
        (fake.root / "data" / "summaries").mkdir()
        for code, by_chapter in summaries.items():
            (fake.root / "data" / "summaries" / f"{code}.json").write_text(
                json.dumps({"summaries": {n: {"en": s} for n, s in by_chapter.items()}})
            )
        code = next(iter(books))
        return Source(fake.root, code)

    def test_each_chapter_takes_its_own_curled(self):
        source = self.source(
            {"PSA": {
                "1": [record("PSA.1.1.s1", ["PSA.1.1"], "How blessed.")],
                "2": [record("PSA.2.1.s1", ["PSA.2.1"], "Why do the nations rage?")],
            }},
            {},
            {"PSA": {"1": "The one who delights in God's instruction.", "2": "The \"nations\" plot."}},
        )
        self.assertEqual(
            source.chapter_summaries(),
            {1: "The one who delights in God’s instruction.", 2: "The “nations” plot."},
        )

    def test_a_chapter_hebrew_numbers_otherwise_joins_the_english_one_holding_it(self):
        """Hebrew Joel 3 is English 2:28-32; Hebrew 4 is English 3."""
        source = self.source(
            {"JOL": {
                "2": [record("JOL.2.1.s1", ["JOL.2.1", "JOL.2.2", "JOL.2.3"], "Blow the trumpet.")],
                "3": [record("JOL.3.1.s1", ["JOL.3.1", "JOL.3.2"], "I will pour out my Spirit.")],
                "4": [record("JOL.4.1.s1", ["JOL.4.1"], "In those days.")],
            }},
            {"JOL.3.1": ["JOL.2.28"], "JOL.3.2": ["JOL.2.29"], "JOL.4.1": ["JOL.3.1"]},
            {"JOL": {"2": "The day is coming.", "3": "The Spirit poured out.", "4": "The nations judged."}},
        )
        self.assertEqual(
            source.chapter_summaries(),
            {2: "The day is coming. The Spirit poured out.", 3: "The nations judged."},
        )

    def test_a_split_chapter_gives_its_summary_to_the_english_chapter_it_fills(self):
        """Hebrew Malachi 3:19-24 is all of English 4; 3:1-18 stays English 3."""
        source = self.source(
            {"MAL": {"3": [
                record("MAL.3.1.s1", ["MAL.3.1", "MAL.3.2"], "I am sending my messenger."),
                record("MAL.3.19.s1", ["MAL.3.19"], "The day is coming."),
            ]}},
            {"MAL.3.19": ["MAL.4.1"]},
            {"MAL": {"3": "A messenger, and the day."}},
        )
        self.assertEqual(
            source.chapter_summaries(), {3: "A messenger, and the day.", 4: "A messenger, and the day."}
        )

    def test_a_one_verse_shift_moves_no_summary_and_a_book_without_any_has_none(self):
        source = self.source(
            {"GEN": {
                "31": [record("GEN.31.54.s1", ["GEN.31.54"], "Jacob offered a sacrifice.")],
                "32": [
                    record("GEN.32.1.s1", ["GEN.32.1"], "Laban left."),
                    record("GEN.32.2.s1", ["GEN.32.2"], "Jacob went on."),
                    record("GEN.32.3.s1", ["GEN.32.3"], "He sent messengers."),
                ],
            }},
            {"GEN.32.1": ["GEN.31.55"], "GEN.32.2": ["GEN.32.1"], "GEN.32.3": ["GEN.32.2"]},
            {"GEN": {"31": "Jacob and Laban part.", "32": "Jacob prepares to meet Esau."}},
        )
        self.assertEqual(
            source.chapter_summaries(),
            {31: "Jacob and Laban part.", 32: "Jacob prepares to meet Esau."},
        )
        bare = self.source({"GEN": {"1": [record("GEN.1.1.s1", ["GEN.1.1"], "In the beginning.")]}}, {}, {})
        self.assertEqual(bare.chapter_summaries(), {})
