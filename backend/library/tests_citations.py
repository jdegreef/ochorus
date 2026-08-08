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

from library.scripture import annotate_references, cited_references, misattributed


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
    thresholds here it flags 247 of the corpus's ~4,400 quote-citation pairs,
    and a meaningful minority of those are this.

    That count was 101 until the rival search was widened across books. The
    extra 146 are not noise: a ten-case sample was checked by hand and all ten
    were real, six of them citing a verse that shares no content word at all
    with the quotation. No previously-reported finding was lost — 21 changed
    their answer to a better one, and none disappeared.
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


class CrossBookTests(SimpleTestCase):
    """The cited reference names the wrong BOOK, not just the wrong number.

    Every case here is confirmed, found by a translator working through
    `talks-to-the-farmer` into Swahili. They matter because the first version of
    this check searched for a rival only inside the cited book, so a cross-book
    misprint was structurally invisible — and worse, the rival search still
    returned the best in-book near-miss, answering confidently and wrongly on
    three of the five. Silence would have been better than that; the right
    answer is better still.
    """

    def test_wrong_book_with_no_in_book_rival(self):
        # Nothing in Jeremiah is close, so the old same-book search returned None.
        self.assertEqual(
            misattributed(
                "a sharp threshing instrument having teeth", "Jeremiah 51:20"
            ),
            "Isaiah 41:15",
        )

    def test_wrong_book_beats_a_confident_in_book_rival(self):
        # The case a fail-only widening cannot reach: Job 41:10 ("Who then is he
        # that can stand before me?") clears RIVAL_MIN inside the cited book, so
        # the search never widened and the answer was "Job 41:10".
        self.assertEqual(
            misattributed("Who can stand before his cold?", "Job 37:22"),
            "Psalms 147:17",
        )

    def test_tie_is_broken_by_word_order_not_canon_order(self):
        # Deuteronomy 32:1 ("Give ear, ye heavens … let the earth hear") holds
        # every content word of this quote, so it ties Isaiah 1:2 at 1.00 on a
        # token set and wins on canon order alone. Only word ORDER separates them.
        self.assertEqual(
            misattributed(
                "Hear, O heavens, and give ear, O earth", "Jeremiah 7:28"
            ),
            "Isaiah 1:2",
        )

    def test_degenerate_short_verse_cannot_win_across_books(self):
        # `_overlap` takes containment whichever way round fits, so Mark 9:40
        # ("he that is not against us is for us") reduces to {against} and scores
        # 1.00 against anything containing that word. Harmless in one book, a
        # certainty across 31,000 verses — this is the pinned ASV/KJV case, whose
        # answer must stay in Acts.
        self.assertEqual(
            misattributed(
                "It is hard for thee to kick against the pricks.", "Acts ix. 5"
            ),
            "Acts 26:14",
        )

    def test_correct_citation_stays_silent_across_the_canon(self):
        # The widened search must not manufacture a rival for a sound citation.
        for quote, ref in (
            ("For God so loved the world, that he gave his only begotten Son", "John 3:16"),
            ("The Lord is my shepherd; I shall not want", "Psalm 23:1"),
            ("In the beginning God created the heavens and the earth", "Genesis 1:1"),
            ("Be still, and know that I am God", "Psalm 46:10"),
        ):
            with self.subTest(ref=ref):
                self.assertIsNone(misattributed(quote, ref))


class RomanNumeralCandidateTests(SimpleTestCase):
    """Chapters set in roman numerals are references too.

    Victorian devotional prose writes "Luke ii. 10", and 690 such citations sit
    across 23 of our English works — most of which use no other form. Reading
    only Arabic digits left those readers with no tappable reference at all and
    hid the same citations from `audit_citations`. pythonbible parses them; only
    our own pre-filter regex did not.
    """

    def test_roman_chapter_is_annotated(self):
        out = annotate_references("<p>If we turn to Luke ii. 10, we find it.</p>")
        self.assertIn('data-ref="Luke ii. 10"', out)

    def test_roman_and_arabic_together(self):
        self.assertEqual(
            cited_references(
                "<p>Colossians iii. 11 and Isaiah 49:24 and Job xxxiii. 24.</p>"
            ),
            ["Colossians 3:11", "Isaiah 49:24", "Job 33:24"],
        )

    def test_prose_that_merely_looks_roman_is_left_alone(self):
        # The regex is loose and pythonbible is the gate, but every junk
        # candidate is a permanent entry in an unbounded cache — so the roman
        # group is a real numeral, not `[ivxlc]+`, which also matches "civil".
        for text in (
            "<p>See Section iv. 2 of the report.</p>",
            "<p>His conduct was civil. 5 men agreed.</p>",
            "<p>Chapter ii. 3 explains it.</p>",
        ):
            with self.subTest(text=text):
                self.assertNotIn("scripture-ref", annotate_references(text))
