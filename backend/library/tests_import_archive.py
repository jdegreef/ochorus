"""The archive.org importer: licence gate, printing floor, chapter detection.

archive.org is the only source whose catalogue is not wholly public domain and
whose text quality varies by PRINTING rather than by work, so both of those get
gates here. The chapter tests are regression tests for a live defect: the
importer split Sibbes' *Bruised Reed* at its table of contents and produced one
chapter from a twenty-six chapter book, with every existing gate green.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from library.management.commands.import_archive import (
    MIN_PRINTING_YEAR,
    PD_THROUGH_YEAR,
    _roman,
    chapterize,
    drop_contents_run,
    printing_year,
    public_domain_reason,
)


class LicenceGateTests(SimpleTestCase):
    """An archive.org identifier can point at anything, including a book that is
    only lendable — unlike CCEL and Gutenberg, whose catalogues are PD outright."""

    def test_an_explicit_not_in_copyright_status_passes(self):
        ok, why = public_domain_reason({"possible-copyright-status": "NOT_IN_COPYRIGHT"})
        self.assertTrue(ok)
        self.assertIn("NOT_IN_COPYRIGHT", why)

    def test_any_other_explicit_status_is_refused_even_on_an_old_book(self):
        # The trap this closes: a modern edition of an ancient work, passing on
        # its subject's age rather than its own.
        ok, why = public_domain_reason(
            {"possible-copyright-status": "IN_COPYRIGHT", "year": "1651"}
        )
        self.assertFalse(ok)
        self.assertIn("IN_COPYRIGHT", why)

    def test_a_creative_commons_public_domain_licence_passes(self):
        ok, _ = public_domain_reason(
            {"licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/"}
        )
        self.assertTrue(ok)

    def test_age_alone_passes_when_the_item_records_nothing_else(self):
        # Ramabai's 1888 High-Caste Hindu Woman carries neither a status nor a
        # licence — refusing on that would lose genuinely public-domain scans.
        ok, why = public_domain_reason({"year": "1888"})
        self.assertTrue(ok)
        self.assertIn("1888", why)

    def test_a_recent_printing_with_no_status_is_refused(self):
        ok, _ = public_domain_reason({"year": str(PD_THROUGH_YEAR + 1)})
        self.assertFalse(ok)

    def test_an_undated_item_with_no_status_is_refused(self):
        ok, why = public_domain_reason({"title": "Something"})
        self.assertFalse(ok)
        self.assertIn("no printing year", why)

    def test_the_year_is_read_from_whichever_date_field_exists(self):
        self.assertEqual(printing_year({"date": "1878-01-01"}), 1878)
        self.assertEqual(printing_year({"publicdate": "2011-05-02 18:00:00"}), 2011)
        self.assertIsNone(printing_year({}))


class RomanNumeralTests(SimpleTestCase):
    def test_well_formed_numerals_parse(self):
        self.assertEqual(_roman("I"), 1)
        self.assertEqual(_roman("IV"), 4)
        self.assertEqual(_roman("XVII"), 17)
        self.assertEqual(_roman("XXVI"), 26)

    def test_a_mangled_numeral_is_rejected_rather_than_guessed(self):
        # "XVIL" is how this scan renders XVII. Under the plain subtractive rule
        # it parses to 34 — a wrong-but-plausible value that read as a numbering
        # restart and threw away 16 of Sibbes' 26 chapters.
        self.assertIsNone(_roman("XVIL"))
        self.assertIsNone(_roman("IIII"))
        self.assertIsNone(_roman("Q"))


class ContentsRunTests(SimpleTestCase):
    def test_a_leading_contents_list_is_dropped_at_the_restart(self):
        markers = [(10, "I", ""), (13, "II", ""), (16, "III", ""),
                   (900, "I", "The Text opened"), (1100, "II", "Those that Christ")]
        self.assertEqual([m[0] for m in drop_contents_run(markers)], [900, 1100])

    def test_a_book_with_no_contents_list_is_untouched(self):
        markers = [(170, "I", ""), (448, "II", ""), (671, "III", "")]
        self.assertEqual(drop_contents_run(markers), markers)

    def test_only_a_return_to_one_counts_as_a_restart(self):
        # A backwards step that is not to I is an OCR misread, not a new run;
        # cutting there would discard everything before it.
        markers = [(1, "I", ""), (2, "II", ""), (3, "XVIL", ""), (4, "XVIII", "")]
        self.assertEqual(len(drop_contents_run(markers)), 4)

    def test_the_last_restart_wins(self):
        markers = [(1, "I", ""), (2, "II", ""), (50, "I", ""), (60, "II", ""), (500, "I", "")]
        self.assertEqual([m[0] for m in drop_contents_run(markers)], [500])


class ChapterMarkerTests(SimpleTestCase):
    def test_a_bare_marker_takes_its_title_from_the_next_line(self):
        text = "\n".join([
            "CHAPTER I.", "Early Years", "Susanna was born in 1669.", "She was the youngest.",
            "CHAPTER II.", "Marriage", "She married Samuel in 1688.",
        ])
        secs = chapterize(text)
        self.assertEqual([t for t, _ in secs], ["Early Years", "Marriage"])
        self.assertIn("born in 1669", secs[0][1])

    def test_a_marker_with_the_title_on_the_same_line(self):
        # "Chap. IV. — Signs of one truly bruised" — the shape that matched
        # nothing before, so a whole printing style was unimportable.
        text = "\n".join([
            "Chap. I. — The Text opened and divided",
            "The reed is a poor thing.",
            "Chap. II. — Those that Christ hath to do withal",
            "They are bruised first.",
        ])
        secs = chapterize(text)
        self.assertEqual(
            [t for t, _ in secs],
            ["The Text opened and divided", "Those that Christ hath to do withal"],
        )
        self.assertIn("poor thing", secs[0][1])

    def test_the_contents_list_does_not_become_the_chapters(self):
        text = "\n".join(
            ["Chapter I.", "The Text opened", "Chapter II.", "Those that Christ"]
            + ["filler"] * 5
            + ["Chap. I. — The Text opened", "The real body of chapter one.",
               "Chap. II. — Those that Christ", "The real body of chapter two."]
        )
        secs = chapterize(text)
        self.assertEqual(len(secs), 2)
        self.assertIn("real body of chapter one", secs[0][1])


class PrintingFloorTests(SimpleTestCase):
    def test_the_floor_sits_where_type_became_modern(self):
        # Not an arbitrary round number: below it the scans are long-s and
        # ligature type, which OCRs to noise. See the module docstring.
        self.assertEqual(MIN_PRINTING_YEAR, 1800)
