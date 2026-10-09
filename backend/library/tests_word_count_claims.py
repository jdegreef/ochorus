"""A sentence that counts the words of a phrase must count them right.

House-written prose likes to say "in N words:" and then quote them. The count
is a checkable fact, and it is easy to get wrong when the phrase is edited or
remembered rather than counted:

    On 2026-10-08 the Portuguese translation of *Elisabeth Elliot (For
    Children)* (job #5563) found chapter 8 calling “Doe the nexte thynge”
    three words. The same miscount had also reached the full biography and
    *Key Teachings of Elisabeth Elliot*. A sweep of the claim form below then
    found six more: Chesterton's “Art is the signature of man” (said to be
    five words), MacDonald's “Obedience is the opener of eyes” (five), Owen's
    “Think greatly of the greatness of God” (six), “Do the next thing” in
    *Anchored 2* (three), “Pray continually” (three) and Deuteronomy 32:35's
    “Their foot shall slide in due time” (five).

So this gate reads every English book, chapter and article that Ochorus wrote
itself, finds "<number> word(s) …: “<phrase>”" inside one sentence, and checks
the number against the phrase. Public-domain authors are out of scope: their
words are the text, and their counts often point at a word inside the quote
(Murray's “two words, ‘yield’ …”), which is theirs to say.

Only claims whose phrase follows the count in the same sentence are checked.
A count with the phrase a sentence later (“her motto was four words long. …
‘Doe the nexte thynge’”) is not, because nothing reliable ties the two.

``NOT_A_MISCOUNT`` holds the hits that are right on a careful reading, each with
its reason. The suite also fails when an entry stops matching, so the list
cannot go stale.

No DB, no network: reads the fixture only.
"""

from __future__ import annotations

import html
import json
import re

from django.test import SimpleTestCase

from library.content_fixtures import iter_work_files

NUMBERS = {
    w: n
    for n, w in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
        ]
    )
}

# "<number> word(s)", up to 60 characters that stay inside the sentence, then
# the quoted phrase.
CLAIM = re.compile(
    r"\b(" + "|".join(NUMBERS) + r")[- ]words?\b"
    r"[^.!?“”\"]{0,60}?\s*[“\"]([^”\"]{1,120})[”\"]",
    re.IGNORECASE,
)

HOUSE_AUTHOR = ["ochorus-originals"]

# (fixture file name, the matched claim's first 40 characters) -> why it is right.
NOT_A_MISCOUNT = {
    (
        "all-of-grace-teens.en.json",
        "four words from Romans: God “justifies t",
    ): "“God justifies the ungodly” is four; “God” stands outside the quote.",
    (
        "amanda-smith-autobiography-teens.en.json",
        "one word: “I WILL.”",
    ): "She put the weight on one word, the stressed WILL.",
    (
        "john-hyde-a-life-teens.en.json",
        "one word “scores of times with long paus",
    ): "The quote is how often he said the word, not the word itself.",
    (
        "tukutendereza.en.json",
        "one word has a New Testament twin: “Awak",
    ): "The quote is the word's twin verse, not the word.",
}


def phrase_word_count(phrase: str) -> int:
    """Words in a quoted phrase, ignoring punctuation (dashes split words)."""
    phrase = re.sub(r"[—–]", " ", phrase)
    phrase = re.sub(r"[^\w\s'’-]", "", phrase)
    return len(phrase.split())


def claims(text: str):
    """Yield ``(claimed, actual, matched_text)`` for each count claim in text."""
    plain = html.unescape(re.sub(r"<[^>]+>", "", text))
    for m in CLAIM.finditer(plain):
        yield NUMBERS[m.group(1).lower()], phrase_word_count(m.group(2)), m.group(0)


def house_written_texts():
    """Yield ``(file name, text)`` for every English house-written field."""
    for path, rows in iter_work_files():
        if not path.name.endswith(".en.json") or not rows:
            continue
        head = rows[0]
        fields = head["fields"]
        house = (
            head["model"] == "library.article"
            or fields.get("author") == HOUSE_AUTHOR
            or fields.get("attribution", "").startswith("© Ochorus")
        )
        if not house:
            continue
        for row in rows:
            for key in ("body_html", "description", "qa", "study_questions"):
                value = row["fields"].get(key)
                if not value:
                    continue
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False).replace('\\"', '"')
                yield path.name, value


class ClaimParsingTests(SimpleTestCase):
    def test_counts_the_quoted_phrase(self):
        found = list(claims("The message was four words long: “Doe the nexte thynge.”"))
        self.assertEqual(found[0][:2], (4, 4))

    def test_catches_a_miscount(self):
        found = list(claims("<p>in five words: “Art is the signature of man.”</p>"))
        self.assertEqual(found[0][:2], (5, 6))

    def test_a_dash_separates_words(self):
        self.assertEqual(phrase_word_count("I the Vine—you the branch."), 6)

    def test_apostrophes_and_hyphens_stay_inside_a_word(self):
        self.assertEqual(phrase_word_count("God’s well-known word"), 3)

    def test_the_phrase_must_be_in_the_same_sentence(self):
        self.assertEqual(list(claims("It was four words long. She said “Go.”")), [])


class WordCountClaimTests(SimpleTestCase):
    def test_house_written_counts_match_their_phrase(self):
        wrong, used = [], set()
        for name, text in house_written_texts():
            for claimed, actual, matched in claims(text):
                if claimed == actual:
                    continue
                key = (name, matched[:40])
                if key in NOT_A_MISCOUNT:
                    used.add(key)
                    continue
                wrong.append(f"{name}: says {claimed}, quotes {actual}: {matched}")
        self.assertEqual(
            sorted(set(wrong)),
            [],
            "A sentence counts the words of a phrase and gets it wrong. Fix the "
            "number (in the English and any edition repeating it, and in the "
            "book's markdown source if it has one), or, if the count is right "
            "on a careful reading, add it to NOT_A_MISCOUNT with the reason.",
        )
        self.assertEqual(
            sorted(set(NOT_A_MISCOUNT) - used),
            [],
            "These NOT_A_MISCOUNT entries no longer match; delete them.",
        )
