"""Does a quotation match the verse it cites?

Every positive case below is a REAL misprint found by a translator working
through the English, not an invented example — six of them in `the-way-to-god`
alone, which is what made this worth building. The class matters more than its
size: a spacing artifact dies in translation, but a wrong reference is
reproduced faithfully into every language, because that is what a careful
translator does with a printed citation.

The negatives are the ones that decide whether the check is usable. A
quotation that runs past the verse it cites, and a quotation that takes only
the speech and drops the narrative frame, are both normal and must stay
silent — they were what broke the first two scoring attempts.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from library.scripture import misattributed


class CitationAccuracyTests(SimpleTestCase):
    """Positives: the citation is wrong and the right one is nameable."""

    def test_wrong_chapter_digit(self):
        # "xvii" for "xviii" — Luke 17:10 is the unprofitable servants.
        self.assertEqual(
            misattributed(
                "Two men went up into the temple to pray; the one a Pharisee, "
                "and the other a publican.",
                "Luke xvii. 10",
            ),
            "Luke 18:10",
        )

    def test_off_by_one_verse(self):
        # John 14:5 is Thomas asking the way; 14:6 is the answer quoted.
        self.assertEqual(
            misattributed(
                "I am the way, and the truth, and the life: no man cometh unto "
                "the Father, but by me.",
                "John xiv. 5",
            ),
            "John 14:6",
        )

    def test_short_verse_still_resolves(self):
        # Four content words. The rival margin does the work, not the length —
        # a six-token floor silently dropped this one and the confession below.
        self.assertEqual(
            misattributed("Thou shalt have no other gods before me.", "Exod. xx. 2"),
            "Exodus 20:3",
        )

    def test_quote_is_speech_without_its_frame(self):
        # The verse opens "And Simon Peter answered and said"; the book quotes
        # only what he said. Verse-in-quote containment scores this 0.55 and
        # misses it — quote-in-verse scores 1.0.
        self.assertEqual(
            misattributed("Thou art the Christ, the Son of the living God.", "Matthew xvi. 1"),
            "Matthew 16:16",
        )

    def test_wrong_chapter_entirely(self):
        self.assertEqual(
            misattributed(
                "The heart is deceitful above all things, and desperately "
                "wicked: who can know it?",
                "Jer. xxii. 9",
            ),
            "Jeremiah 17:9",
        )


class CitationSilenceTests(SimpleTestCase):
    """Negatives. These are the cases that make the check safe to act on."""

    def test_correct_citation_is_silent(self):
        for quote, ref in [
            ("I am the way, and the truth, and the life: no man cometh unto the "
             "Father, but by me.", "John 14:6"),
            ("Two men went up into the temple to pray; the one a Pharisee, and "
             "the other a publican.", "Luke 18:10"),
            ("For God so loved the world, that he gave his only begotten Son.",
             "John 3:16"),
            ("Thou shalt have no other gods before me.", "Exodus 20:3"),
            ("Thou art the Christ, the Son of the living God.", "Matthew 16:16"),
        ]:
            with self.subTest(ref=ref):
                self.assertIsNone(misattributed(quote, ref))

    def test_quotation_running_past_the_cited_verse_is_silent(self):
        # Two verses quoted, the first cited. Common and correct. Symmetric
        # similarity halves here and reads as a mismatch.
        self.assertIsNone(
            misattributed(
                "In the beginning was the Word, and the Word was with God, and "
                "the Word was God. The same was in the beginning with God.",
                "John 1:1",
            )
        )

    def test_too_short_to_judge(self):
        # "Fear not" is in scores of verses; naming one would be a guess.
        self.assertIsNone(misattributed("Fear not.", "Isaiah 41:10"))

    def test_unparseable_reference_is_silent(self):
        self.assertIsNone(misattributed("Whatever this is.", "Room 3:16"))
        self.assertIsNone(misattributed("Whatever this is.", "not a reference"))


class KnownLimitationTests(SimpleTestCase):
    """The failure modes a caller has to know about, pinned so they are not
    mistaken for bugs later.

    The verse text is the **ASV** (public domain, bundled, offline). These books
    quote the **KJV**. Where the two rest on different manuscripts, a clause the
    KJV prints at the cited verse is simply absent from the ASV there, and the
    check reports a mismatch that is not one. Acts 9:5 is the standing example:
    "it is hard for thee to kick against the pricks" is KJV Acts 9:5 and ASV
    only at 26:14.

    This is why the sweep is a triage list and not a ratchet gate: at the
    thresholds here it flags 101 of the corpus's ~4,400 quote-citation pairs,
    and a meaningful minority of those are this.
    """

    def test_kjv_only_clause_is_a_known_false_positive(self):
        # Documented, not desired. If a KJV text is ever bundled this should
        # start returning None and the assertion should flip.
        self.assertEqual(
            misattributed(
                "It is hard for thee to kick against the pricks.", "Acts ix. 5"
            ),
            "Acts 26:14",
        )
