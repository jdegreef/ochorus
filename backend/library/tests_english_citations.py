"""The English citation audit (`library/english_citations.py`).

Positives are the shapes translation workers kept finding and carrying into
every language; negatives are the ones that would have made the audit "fix" a
correct reference — a parallel passage, a reference list, a BSB/NIV wording
none of our bundled Bibles prints.
"""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase

from library import english_citations as ec


def _rec(tier: str = "house") -> ec.Record:
    return ec.Record(Path("x.en.json"), "x", "en", "x ch01", tier, 1, "", 1)


def _check(quote: str, ref: str, tier: str = "house"):
    return ec.check_pair(_rec(tier), quote, ref)


class MiscitationTests(SimpleTestCase):
    def test_wrong_chapter_digit_is_found_and_rewritable(self):
        # "Genesis 27:28" for the sale of Joseph, 37:28.
        f = _check(
            "Then there passed by Midianites merchantmen; and they drew and lifted up Joseph "
            "out of the pit, and sold Joseph to the Ishmaelites for twenty pieces of silver",
            "Genesis 27:28",
        )
        self.assertEqual((f.kind, f.suggestion), ("miscited", "Genesis 37:28"))
        self.assertTrue(f.fixable)
        self.assertEqual(f.replacement, "Genesis 37:28")

    def test_public_domain_original_is_reported_never_fixable(self):
        # The author's miscitation is the text (english-qa): same evidence, no fix.
        f = _check(
            "Then there passed by Midianites merchantmen; and they drew and lifted up Joseph "
            "out of the pit, and sold Joseph to the Ishmaelites for twenty pieces of silver",
            "Genesis 27:28",
            tier="pd",
        )
        self.assertTrue(f.unambiguous)
        self.assertFalse(f.fixable)

    def test_parallel_passage_is_not_a_miscitation(self):
        # Deut 6:7 and 11:19 say the same thing; the NIV of 6:7 fits 11:19's
        # bundled wording better, and is still correctly cited.
        self.assertIsNone(
            _check(
                "when you sit at home and when you walk along the road, "
                "when you lie down and when you get up",
                "Deuteronomy 6:7",
            )
        )

    def test_a_later_reference_in_the_list_counts(self):
        # Bunyan's "(Jer. 49:11; 15:11)" quotes 15:11.
        self.assertIsNone(
            _check(
                "Verily it shall be well with thy remnant, verily I will cause the enemy "
                "to entreat thee well in the time of evil",
                "Jer. 49:11; 15:11",
            )
        )

    def test_a_coincidence_of_words_is_not_a_rival(self):
        # A Wesley maxim cited to James 4:2 shares a word or two with Acts 26.
        self.assertIsNone(
            _check("God Does Nothing but in Answer to Prayer", "James 4:2")
        )
        self.assertIsNone(
            _check("Eighty and Six Years Have I Served Him", "Revelation 2:10")
        )

    def test_correct_citation_is_silent(self):
        self.assertIsNone(
            _check(
                "For God so loved the world, that he gave his only begotten Son",
                "John 3:16",
            )
        )

    def test_a_numbered_book_later_in_the_list_counts(self):
        # "2 Cor. 4:5" is its own reference, not "1 Cor. 2 Cor. 4:5".
        self.assertIsNone(
            _check(
                "For we preach not ourselves, but Christ Jesus the Lord; "
                "and ourselves your servants for Jesus' sake",
                "1 Cor. 2:3; 2 Cor. 4:5",
            )
        )

    def test_a_verse_no_bundled_bible_prints_is_not_judged(self):
        # Matt 18:11 is KJV-only; the originals quote it correctly.
        self.assertIsNone(
            _check(
                "For the Son of man is come to save that which was lost",
                "Matthew 18:11",
            )
        )


class RangeTests(SimpleTestCase):
    def test_quotation_running_past_the_cited_verse(self):
        f = _check(
            "My brethren, count it all joy when ye fall into divers temptations; knowing this, "
            "that the trying of your faith worketh patience. But let patience have her perfect "
            "work, that ye may be perfect and entire, wanting nothing.",
            "James 1:2",
        )
        self.assertEqual((f.kind, f.suggestion), ("range", "James 1:2-4"))
        self.assertEqual(f.replacement, "James 1:2-4")

    def test_added_verses_must_carry_the_word_order(self):
        # Acts 10:43 in the BSB: 10:42-47 only gathers a few of its words.
        self.assertIsNone(
            _check(
                "All the prophets testify about Him that everyone who believes in Him "
                "receives forgiveness of sins through His name",
                "Acts 10:43",
            )
        )


class ParsingTests(SimpleTestCase):
    def test_unspaced_and_dotted_references_parse(self):
        self.assertEqual(
            ec.parse_ref("John14:27").verse_ids, ec.parse_ref("John 14:27").verse_ids
        )
        self.assertEqual(
            ec.parse_ref("Psalm. 20:7 -8").verse_ids,
            ec.parse_ref("Psalm 20:7-8").verse_ids,
        )
        self.assertEqual(
            ec.parse_ref("Acts ix. 5").verse_ids, ec.parse_ref("Acts 9:5").verse_ids
        )

    def test_no_such_verse_is_false_not_none(self):
        self.assertIs(ec.parse_ref("Psalm 23:9"), False)
        self.assertIsNone(ec.parse_ref("Chapter 3:2"))

    def test_a_dash_reference_belongs_to_the_quotation_before_it(self):
        text = (
            "“For God so loved the world, that he gave his only begotten Son” — John 3:16, "
            "“Being justified by faith, we have peace with God” — Romans 5:1."
        )
        self.assertEqual([r for _, r in ec.pairs_in(text)], ["John 3:16", "Romans 5:1"])

    def test_pairs_read_both_layouts(self):
        text = (
            "“Peace I leave with you, my peace I give unto you”</p><p>(John 14:27). "
            "Joel 2:28 — “I will pour out my spirit upon all flesh” and so on."
        )
        self.assertEqual(
            [r for _, r in ec.pairs_in(ec._plain(text))],
            ["Joel 2:28", "John 14:27"],
        )

    def test_whole_chapter_reference_only_in_parentheses(self):
        self.assertEqual(
            [
                r
                for _, r in ec.pairs_in(
                    "“the promise of the Father, which ye heard” (Acts 4)"
                )
            ],
            ["Acts 4"],
        )
        self.assertEqual(
            ec.pairs_in("“the promise of the Father, which ye heard” — Acts 4 says"), []
        )


class BookSpellingTests(SimpleTestCase):
    def test_near_misses(self):
        self.assertEqual(ec.misspelled_book("Mathew"), "Matthew")
        self.assertEqual(ec.misspelled_book("Revelations"), "Revelation")
        self.assertEqual(ec.misspelled_book("Hebrew"), "Hebrews")
        # The I of Isaiah is not a Roman "1".
        self.assertEqual(ec.misspelled_book("Isiah"), "Isaiah")
        self.assertEqual(ec.misspelled_book("1 Corinthans"), "Corinthians")

    def test_old_abbreviations_and_real_names_are_not_misspellings(self):
        for name in (
            "Psal.",
            "Psal",
            "Matth.",
            "Matt.",
            "Thessalonians",
            "Chapter",
            "Mark",
        ):
            self.assertIsNone(ec.misspelled_book(name), name)


class OwnEditionsTests(SimpleTestCase):
    """The ratchet: no unambiguous miscitation in an edition WE wrote.

    A Modern English edition, an Ochorus Original, a young-reader adaptation
    or an article with one fails here, before a translator copies it into
    every language. Public-domain originals are not held to this: their
    miscitations are the author's (see the english-qa skill)."""

    def test_no_fixable_finding_in_our_own_editions(self):
        fixable = []
        for rec in ec.records():
            if rec.tier == "pd":
                continue
            _, found = ec.audit_record(rec)
            fixable += [
                f"{f.record.where}: {f.printed} → {f.replacement}"
                for f in found
                if f.fixable
            ]
        self.assertEqual(
            fixable,
            [],
            "run `manage.py audit_english_citations --fixable` and correct these",
        )
