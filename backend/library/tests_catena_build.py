"""build_catena's text handling: the quotation stack that reopens a speech
running across verse blocks, the typography tidy, and the shipped books' verse
blocks, whose double quotation marks must never close a speech they did not
open."""

import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from library.management.commands.build_catena import Command, open_at, tidy

BOOKS = Path(settings.BASE_DIR) / "library" / "fixtures" / "content" / "books"
_VERSE_BLOCK = re.compile(r"<blockquote><p>(.*?)</p><p>— ([^<]+)</p></blockquote>", re.S)


class OpenAtTests(SimpleTestCase):
    def test_a_double_inside_a_single_inside_a_double_is_nested(self):
        # Matthew 22:2–14, abridged: the parable's speech runs to 22:14.
        verses = {
            (22, 2): '"What happens in the kingdom of heaven can be compared to this.',
            (22, 4): "So he sent more servants: 'Tell the guests, \"See, come to the wedding.\"'",
            (22, 6): "The rest laid hands on the king's servants.",
            (22, 12): "He said, 'Friend, how did you come in?' The man had nothing to say.",
            (22, 14): 'For the invited are many, but the chosen are few."',
            (22, 15): "Then the Pharisees went out.",
        }
        self.assertEqual(open_at(verses), {(22, 4), (22, 6), (22, 12), (22, 14)})

    def test_a_quotation_inside_a_quotation_closes_only_itself(self):
        # John 10:34–38: "Your own law says ... 'I said, "You are gods"'?
        verses = {
            (10, 34): "Jesus answered them, \"Your own law says, does it not, 'I said, \"You are gods\"'?",
            (10, 36): "how can you tell him, 'You are blaspheming,' because I said, 'I am the Son of God'?",
            (10, 38): 'believe the works."',
            (10, 39): "They tried again to seize him.",
        }
        self.assertEqual(open_at(verses), {(10, 36), (10, 38)})

    def test_a_speech_reopened_at_a_new_paragraph_stays_open(self):
        # John 14–16: OWB reopens a long discourse without closing the last paragraph.
        verses = {
            (14, 1): '"Do not let your hearts be troubled.',
            (14, 2): '"In my Father\'s house there are many rooms.',
            (14, 3): 'I will come back."',
            (14, 4): "Thomas said nothing.",
        }
        self.assertEqual(open_at(verses), {(14, 2), (14, 3)})

    def test_an_apostrophe_is_not_a_quotation(self):
        verses = {(1, 1): "The disciples' boat, and Peter's net.", (1, 2): "Then they rowed."}
        self.assertEqual(open_at(verses), set())


class TidyTests(SimpleTestCase):
    def test_a_byte_order_mark_stands_for_a_space(self):
        self.assertEqual(tidy("cleansed of leprosy\ufeff was he"), ["cleansed of leprosy was he"])
        self.assertEqual(tidy("leprosy\ufeffwas"), ["leprosy was"])

    def test_a_byte_order_mark_inside_a_quotation_mark_goes_with_its_space(self):
        self.assertEqual(tidy("“\ufeffWho? Find them out.\ufeff ”"), ["“Who? Find them out.”"])

    def test_a_byte_order_mark_inside_a_bracket_goes_with_its_space(self):
        self.assertEqual(tidy("(\ufeff 2 Timothy 2:9 ; \ufeff Zechariah 1:5 )"), ["(2 Timothy 2:9; Zechariah 1:5)"])

    def test_a_space_inside_a_curled_mark_is_closed_up(self):
        self.assertEqual(tidy("he said, “ prevented, ” and went"), ["he said, “prevented,” and went"])

    def test_only_typography_is_touched(self):
        self.assertEqual(
            tidy("12. He  said , as - it were ,\nthis .\n\nA second   paragraph ."),
            ["He said, as — it were, this.", "A second paragraph."],
        )


class VersificationTests(SimpleTestCase):
    """An excerpt keyed in the Hebrew numbering lands on the English verse."""

    def convert(self, schemes, english=True):
        command = Command()
        command.meta = {"versification": schemes, "voices": [{"id": "a", "work": "w"}, {"id": "b", "work": "x"}]}
        command.owb = {
            "english_versification": {"PSA.46.1": [], "PSA.46.2": ["PSA.46.1"], "PSA.46.3": ["PSA.46.2"]}
        } if english else {}
        return command.versification("PSA")

    def test_hebrew_numbering_reads_through_the_map(self):
        to_english = self.convert({"w": "hebrew"})
        self.assertEqual(to_english("w", "PSA.46.2", "PSA.46.3"), ((46, 1), (46, 2)))
        self.assertEqual(to_english("w", "PSA.46.1", "PSA.46.1"), ((46, 1), (46, 1)))  # a title
        self.assertEqual(to_english("w", "PSA.23.4", "PSA.23.4"), ((23, 4), (23, 4)))  # numbered alike

    def test_a_chapter_can_override_the_work(self):
        to_english = self.convert(
            {"w": {"scheme": "hebrew", "chapters": {"46": "english", "44": "english+2", "72": "skip"}}}
        )
        self.assertEqual(to_english("w", "PSA.46.2", "PSA.46.2"), ((46, 2), (46, 2)))
        self.assertEqual(to_english("w", "PSA.44.3", "PSA.44.4"), ((44, 1), (44, 2)))
        self.assertEqual(to_english("w", "PSA.72.3", "PSA.72.3"), (None, None))

    def test_a_work_with_no_scheme_is_english(self):
        self.assertEqual(self.convert({})("x", "PSA.46.2", "PSA.46.2"), ((46, 2), (46, 2)))

    def test_a_shift_needs_no_map(self):
        to_english = self.convert({"w": "english+1"}, english=False)
        self.assertEqual(to_english("w", "PSA.29.2", "PSA.29.2"), ((29, 1), (29, 1)))

    def test_a_bad_entry_fails_clearly(self):
        for schemes in ({"nobody": "hebrew"}, {"w": "greek"}, {"w": "hebrew+1"}, {"w": {"chapters": {}}},
                        {"w": {"scheme": "hebrew", "chapters": {"3": "latin"}}}):
            with self.subTest(schemes=schemes), self.assertRaises(CommandError):
                self.convert(schemes)
        with self.assertRaises(CommandError):
            self.convert({"w": "hebrew"}, english=False)


def excerpt(id_, author, start, words=200, text=None, scanned=False):
    return {
        "id": id_, "author": author, "work": author, "_start": start, "_end": start, "_words": words,
        "text": text or (" ".join(["grace"] * (words - 1)) + " ends."),
        "source_url": "https://archive.org/x" if scanned else "https://ccel.org/x",
    }


def command(excerpts, vocabulary=()):
    c = Command()
    c.meta = {"voices": []}
    c.voices = {"aug": ("Augustine", "T", 0), "cal": ("Calvin", "T", 1), "hen": ("Henry", "T", 2)}
    c.lead, c.rejected = set(), set()
    c.excerpts = {e["id"]: e for e in excerpts}
    c.__dict__["vocabulary"] = set(vocabulary)
    return c


class DamagedTests(SimpleTestCase):
    """The damage filter turns away what a scan broke, and nothing an edition
    prints on purpose."""

    SOUND_TYPED = [
        "Behold, I Paul say unto you, that if ye be circumcised, Christ shall profit you nothing.",
        "God the Word, as it is written in 1 Reg. and elsewhere, speaks so.",
        "He said, “‘I am the door,’ saith the Lord.” And so it was.",
        "“For your sakes he became poor.” (2 Corinthians 8:9)",
        "For I God the Word was made flesh, and in 1 Reg. it is so.",
        "The old order is abolished, (Psalm 110:4)",
        "He answered, “Go in peace.﻿”",
    ]
    SOUND_SCANNED = [
        "It is so that that which he had had in verses 5 and 6 is the word of the LORD JEHOVAH.",
    ]
    DAMAGED_TYPED = [
        "Thou, 0 Lord, art a shield for me.",
        "‘‘ Happy,” says he, is the man.",
        "And so the argument runs on, and on,",
    ]
    DAMAGED_SCANNED = [
        "O sinner 1 Take heed of this warning.",
        "He preached upon the Mount I The word is good.",
        "This is the the end of the matter.",
        "ON THE PSALMS. And then he spoke.",
    ]

    def check(self, texts, scanned, damaged):
        words = {w.lower() for t in texts for w in re.findall(r"[A-Za-z]+", t)}
        c = command([], vocabulary=words)
        for t in texts:
            with self.subTest(text=t):
                self.assertEqual(c.damaged(excerpt("e", "aug", (1, 1), text=t, scanned=scanned)), damaged)

    def test_sound_text_passes(self):
        self.check(self.SOUND_TYPED, False, False)
        self.check(self.SOUND_SCANNED, True, False)

    def test_damage_is_caught(self):
        self.check(self.DAMAGED_TYPED, False, True)
        self.check(self.DAMAGED_SCANNED, True, True)


class RefillTests(SimpleTestCase):
    """--refill mends only the passages that lost an excerpt."""

    PASSAGES = [("A", [(1, 1), (1, 2)]), ("B", [(1, 3), (1, 4)])]

    def setUp(self):
        self.c = command([
            excerpt("aug.1", "aug", (1, 1)), excerpt("cal.2", "cal", (1, 2)),
            excerpt("hen.1", "hen", (1, 1)), excerpt("hen.2", "hen", (1, 2)), excerpt("cal.1b", "cal", (1, 1)),
            excerpt("aug.3", "aug", (1, 3)), excerpt("cal.4", "cal", (1, 4)), excerpt("hen.3", "hen", (1, 3)),
        ])

    def test_an_untouched_passage_is_identical(self):
        self.c.rejected = {"cal.2"}
        chosen, touched = self.c.refill(self.PASSAGES, [["aug.1", "cal.2"], ["cal.4", "aug.3"]])
        self.assertEqual(touched, [0])
        self.assertEqual(chosen[1], ["cal.4", "aug.3"])

    def test_kept_picks_stand_first_and_the_budget_holds(self):
        self.c.rejected = {"cal.2"}
        chosen, _ = self.c.refill(self.PASSAGES, [["aug.1", "cal.2"], ["aug.3"]])
        self.assertEqual(chosen[0][0], "aug.1")
        self.assertNotIn("cal.2", chosen[0])
        words = sum(self.c.excerpts[i]["_words"] for i in chosen[0])
        self.assertLessEqual(words, 500 * 1.15)  # BUDGET_MIN for a two-verse passage
        self.assertGreater(len(chosen[0]), 1)

    def test_nothing_lost_nothing_changed(self):
        pinned = [["aug.1", "cal.2"], ["aug.3"]]
        chosen, touched = self.c.refill(self.PASSAGES, pinned)
        self.assertEqual((chosen, touched), (pinned, []))

    def test_an_id_this_logia_file_lacks_fails(self):
        with self.assertRaises(CommandError):
            self.c.refill(self.PASSAGES, [["aug.1", "gone.9"], ["aug.3"]])


class ShippedVerseBlockTests(SimpleTestCase):
    def test_no_verse_block_closes_a_speech_it_did_not_open(self):
        files = sorted(BOOKS.glob("catena-on-*.en.json"))
        self.assertTrue(files)
        bad = []
        for path in files:
            for row in json.loads(path.read_text("utf-8"))[1:]:
                for text, cite in _VERSE_BLOCK.findall(row["fields"]["body_html"]):
                    depth = 0
                    for mark in re.findall("[“”]", text):
                        depth += 1 if mark == "“" else -1
                        if depth < 0:
                            bad.append(f"{path.name}: {cite}")
                            break
        self.assertEqual(bad, [])
