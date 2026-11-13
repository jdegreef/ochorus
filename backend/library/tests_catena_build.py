"""build_catena's text handling: the quotation stack that reopens a speech
running across verse blocks, the typography tidy, and the shipped books' verse
blocks, whose double quotation marks must never close a speech they did not
open."""

import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from library.management.commands.build_catena import open_at, tidy

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

    def test_only_typography_is_touched(self):
        self.assertEqual(
            tidy("12. He  said , as - it were ,\nthis .\n\nA second   paragraph ."),
            ["He said, as — it were, this.", "A second paragraph."],
        )


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
