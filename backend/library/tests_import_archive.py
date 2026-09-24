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
    _marker_value,
    _roman,
    _to_roman,
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

    def test_the_last_chapter_stops_at_the_end(self):
        # Finney's 1876 Memoirs: nine pages of hymnal advertisements follow.
        text = "\n".join([
            "CHAPTER I.", "Work at Home", "He died in 1875.", "THE    END.",
            "Manuals for Worship.", "SONGS FOR THE SANCTUARY. The most popular.",
        ])
        body = chapterize(text)[0][1]
        self.assertIn("died in 1875", body)
        self.assertNotIn("Sanctuary", body)

    def test_a_header_with_lowercased_letters_is_still_a_header(self):
        # The scanner lowercases a letter or two inside a caps running header.
        text = "\n".join([
            "CHAPTER I.", "Birth", "I was born in", "8 MEMOIRS or CHARLES G. Fli^NEY.",
            "Connecticut. EARLY in the year 1826, 1 went on.",
        ])
        body = chapterize(text)[0][1]
        self.assertNotIn("MEMOIRS", body)
        self.assertIn("born in Connecticut.", body)
        self.assertIn("EARLY in the year 1826", body)

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


class ContentsTitleTests(SimpleTestCase):
    """Whose heading to believe when the contents page and the body disagree."""

    SIBBES = "\n".join([
        "CONTENTS.",
        "Chapter I.",
        "The Text opened and divided. What the Reed is, and",
        "what the bruising . . . * .",
        "",
        "Chapter II.",
        "Grace is mingled with Corruption",
        "",
    ] + ["front matter"] * 4 + [
        "Chap. I. — T/ie Text opened and divided. What the",
        "THE prophet Isaiah being lifted up.",
        "Chap. II. — Gract is minted with Corruptum.",
        "Grace is little at the first.",
    ])

    CLARKE = "\n".join([
        "CONTENTS.",
        "CHAPTER  I.— BIKTH  AND  ANCESTRY  .  .  .1",
        "CHAPTEE  II.— YOUTH  AND  MARRIAGE  .  .  15",
        "",
    ] + ["front matter"] * 4 + [
        "CHAPTER  I.",
        "",
        "BIRTH    AND    ANCESTRY.",
        "",
        "THE armies of the Church Militant.",
        "CHAPTER  II.",
        "",
        "YOUTH    AND    MARRIAGE.",
        "",
        "She married Samuel in 1688.",
    ])

    def test_an_inline_heading_defers_to_the_contents_page(self):
        # The body heading is a wrapped display line, so it is both truncated
        # and set in the type that OCRs worst.
        titles = [t for t, _ in chapterize(self.SIBBES)]
        self.assertEqual(
            titles,
            [
                "The Text opened and divided. What the Reed is, and what the bruising",
                "Grace is mingled with Corruption",
            ],
        )

    def test_a_heading_on_its_own_line_beats_the_contents_page(self):
        # Clarke's contents reads "BIKTH"; her body reads "BIRTH". A rule that
        # preferred the contents, or compared lengths, would ship the typo.
        titles = [t for t, _ in chapterize(self.CLARKE)]
        self.assertEqual(titles, ["Birth and Ancestry", "Youth and Marriage"])

    def test_the_contents_scan_stops_at_the_next_entry_however_it_is_spelled(self):
        # "CHAPTEE" is not a marker this importer matches, so without an
        # explicit stop the wrap-scan swallowed the rest of the contents page
        # into chapter one's title — a 130-character heading.
        titles = [t for t, _ in chapterize(self.CLARKE)]
        self.assertNotIn("YOUTH", titles[0].upper())
        self.assertLess(len(titles[0]), 40)

    def test_a_contents_title_that_wrapped_mid_word_is_rejoined(self):
        text = "\n".join([
            "Chapter I.", "Signs of one truly bruised. Means and measure of bruis'", "ing",
            "",
        ] + ["x"] * 3 + ["Chap. I. — Signs of one truly bruised. Means and", "Body text here."])
        self.assertEqual(chapterize(text)[0][0], "Signs of one truly bruised. Means and measure of bruising")


class PartSelectionTests(SimpleTestCase):
    """One work out of a collected-works volume.

    Sibbes, Owen, Manton and Charnock are all mainly available that way, and
    the collected editions are the better-produced scans: Grosart's Sibbes
    prints "All should side with Christ" where the standalone 1878 printing
    OCRs it "^// should side with Christ".
    """

    VOLUME = "\n".join([
        "THE COMPLETE WORKS",
        "MEMOIR OF THE AUTHOR",
        "He was born in 1577.",
        "THE BRUISED REED AND SMOKING FLAX.",          # half-title, no chapters below
    ] + ["front matter"] * 40 + [
        "THE BRUISED REED AND SMOKING FLAX.",          # the real start
        "[CHAPTER I. — The Text opened and divided.]",
        "The prophet Isaiah being lifted up.",
        "[CHAPTER II. — Grace is little at first.]",
        "Grace is small in its beginnings.",
        "THE SWORD OF THE WICKED,",
        "[CHAPTER I. — Another work entirely.]",
        "This belongs to the next treatise.",
    ])

    def _titles(self, part="", end=""):
        return [t for t, _ in chapterize(self.VOLUME, part, end)]

    def test_a_part_takes_only_its_own_work(self):
        self.assertEqual(
            self._titles("THE BRUISED REED AND SMOKING FLAX.", "THE SWORD OF THE WICKED,"),
            ["The Text opened and divided", "Grace is little at first"],
        )

    def test_the_start_is_the_title_the_chapters_sit_under(self):
        # Not the half-title forty lines earlier, which would drag the memoir in.
        secs = chapterize(self.VOLUME, "THE BRUISED REED AND SMOKING FLAX.", "THE SWORD OF THE WICKED,")
        self.assertNotIn("born in 1577", secs[0][1])

    def test_without_an_end_the_next_work_ends_it_by_renumbering(self):
        self.assertEqual(len(self._titles("THE BRUISED REED AND SMOKING FLAX.")), 2)

    def test_an_unknown_part_is_an_error_not_a_silent_whole_volume(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._titles("A WORK NOT IN THIS VOLUME")

    def test_an_unknown_end_is_an_error_too(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._titles("THE BRUISED REED AND SMOKING FLAX.", "NO SUCH HEADING")

    def test_the_last_chapter_stops_at_the_part_boundary(self):
        # Without this the final chapter ran to the end of the volume — 93,000
        # words of somebody else's treatise.
        secs = chapterize(self.VOLUME, "THE BRUISED REED AND SMOKING FLAX.", "THE SWORD OF THE WICKED,")
        self.assertNotIn("next treatise", secs[-1][1])


class MangledMarkerTests(SimpleTestCase):
    """Both halves of a chapter marker get mis-scanned, and both are tolerated."""

    def test_the_word_chapter_is_matched_however_it_scanned(self):
        # CHAPTEE (Clarke), CHAPTEB (Grosart) — real, from two different scans.
        for word in ("CHAPTER", "CHAPTEE", "CHAPTEB", "Chap."):
            text = f"{word} II. — A title\nSome body text here.\n"
            self.assertEqual([t for t, _ in chapterize(text)], ["A title"], word)

    def test_a_numeral_scanned_with_y_for_v_still_parses(self):
        # "[CHAPTER YI. — Grace is mingled with Corruption.]" — losing this
        # merged two chapters into one silently.
        self.assertEqual(_roman("YI"), 6)
        self.assertEqual(_roman("Yl"), 6)

    def test_a_numeral_that_is_still_not_roman_is_rejected(self):
        self.assertIsNone(_roman("XVIL"))
        self.assertIsNone(_roman("ZZ"))

    def test_stacked_is_fused_into_one_letter_still_parse(self):
        # Finney's 1876 Memoirs: "Vm." for VIII, "Xn." / "Xin." for XII / XIII.
        self.assertEqual(_roman("Vm"), 8)
        self.assertEqual(_roman("Xn"), 12)
        self.assertEqual(_roman("Xin"), 13)
        # A capital N or M is not a numeral.
        self.assertIsNone(_roman("XN"))

    def test_the_c_of_the_word_read_as_o_still_marks_a_chapter(self):
        text = "OHAPTEE II.\nA title\nSome body text here.\n"
        self.assertEqual([t for t, _ in chapterize(text)], ["A title"])

    def test_a_final_l_is_read_as_i_when_that_continues_the_sequence(self):
        # "CHAPTEE XXL" for XXI (Finney), "CHAPTER XL" for XI (Foote). XXL is
        # no numeral and XL is forty, so either way chapter XXI merged into XX.
        for mangled, before in (("XL", 10), ("XXL", 20), ("XIIL", 12)):
            marks = [f"{_to_roman(n)}." for n in range(1, before + 1)]
            marks += [mangled, f"{_to_roman(before + 2)}."]
            text = "\n".join(f"CHAPTER {m}\nTitle {m}\nBody {m}." for m in marks)
            titles = [t for t, _ in chapterize(text)]
            self.assertEqual(len(titles), before + 2, mangled)
            self.assertEqual(titles[before], f"Title {mangled}", mangled)

    def test_a_genuine_fortieth_chapter_still_reads_forty(self):
        self.assertEqual(_marker_value("XL", "XXXIX"), 40)
        self.assertEqual(_marker_value("XL", "X"), 11)
        self.assertEqual(_marker_value("XXL", "XX"), 21)
        self.assertEqual(_marker_value("XL", None), 40)


class WrappedHeadingTests(SimpleTestCase):
    """A bracketed chapter heading that does not close on its own line."""

    def test_the_rest_of_the_heading_is_not_left_in_the_body(self):
        # Grosart wraps 8 of the Bruised Reed's 27 headings, and their tails
        # read as the chapter's opening words: "the Bruising.] THE prophet
        # Isaiah being lifted up".
        text = "\n".join([
            "[CHAPTER I. — The Text opened and divided. What the Reed is, and what",
            "the Bruising.]",
            "THE prophet Isaiah being lifted up.",
        ])
        (title, body), = chapterize(text)
        self.assertEqual(title, "The Text opened and divided. What the Reed is, and what the Bruising")
        self.assertNotIn("Bruising.]", body)
        self.assertIn("prophet Isaiah", body)

    def test_a_page_break_inside_the_heading_does_not_end_it(self):
        # Chapters I, IX and XXI each wrap across a blank line.
        text = "\n".join([
            "[CHAPTER IX. — Governors should be tender of weak ones, and also private",
            "",
            "Christians.]",
            "So in the censures of the church.",
        ])
        (title, body), = chapterize(text)
        self.assertTrue(title.endswith("private Christians"), title)
        self.assertNotIn("Christians.]", body)

    def test_a_heading_that_closes_on_its_own_line_is_untouched(self):
        text = "[CHAPTER V. — Grace is little at first.]\nGrace is small in its beginnings.\n"
        (title, body), = chapterize(text)
        self.assertEqual(title, "Grace is little at first")
        self.assertIn("small in its beginnings", body)

    def test_the_wrap_stops_at_the_next_marker(self):
        text = "\n".join([
            "[CHAPTER I. — An unclosed heading",
            "[CHAPTER II. — A closed one.]",
            "Body of two.",
        ])
        self.assertEqual([t for t, _ in chapterize(text)][0], "An unclosed heading")


class SalvagedMarkerTests(SimpleTestCase):
    """A bracketed marker whose opening the scanner ate."""

    def test_a_marker_reduced_to_its_numeral_is_still_found(self):
        # Grosart's chapter VIII survives only as "B VIII. — Tenderness
        # required in ministers toward young beginners.]" — the tail of
        # "[CHAPTEB". Losing it merged chapters VII and VIII silently.
        text = "\n".join([
            "[CHAPTER VII. — Christ will not quench small beginnings.]",
            "The first body.",
            "B VIII. — Tenderness required in ministers toward young beginners.]",
            "The second body.",
        ])
        titles = [t for t, _ in chapterize(text)]
        self.assertEqual(len(titles), 2)
        self.assertEqual(titles[1], "Tenderness required in ministers toward young beginners")

    def test_ordinary_prose_ending_in_a_bracket_is_not_a_marker(self):
        text = "\n".join([
            "[CHAPTER I. — A real one.]",
            "He wrote of the bruised reed [see note 4]",
            "and carried on in the same paragraph.",
        ])
        self.assertEqual(len(chapterize(text)), 1)


class RuleQuoteTests(SimpleTestCase):
    """A margin rule the scan read as an opening quote at the start of a line
    (Pickering's 1838 *Bruised Reed*, which sets no quotation marks)."""

    def _body(self, *lines):
        (_, body), = chapterize("\n".join(["Chap. I. — The Text opened", *lines]))
        return body

    def test_a_line_initial_mark_before_a_word_is_dropped(self):
        body = self._body("so that the church is", "‘armed with invincible courage.")
        self.assertIn("is armed with invincible courage", body)

    def test_a_line_initial_mark_before_a_capital_is_dropped_too(self):
        body = self._body("let us go to", "‘Christ presently to bind us up again.")
        self.assertIn("go to Christ presently", body)

    def test_a_line_initial_mark_before_a_digit_is_left_for_the_pairs(self):
        # "‘0 all the world": the 0 is a lost "t", which only a pair can restore.
        self.assertIn("‘0 all", self._body("he will declare", "‘0 all the world what he is."))

    def test_a_word_split_on_the_mark_is_rejoined(self):
        # "con-" / "‘ceits": with the mark gone the hyphen-join closes the word.
        self.assertIn("mean conceits of himself", self._body("He hath mean con-", "‘ceits of himself."))

    def test_a_mark_mid_line_is_left_alone(self):
        # The line start is the whole signal. Mid-line ("He will ‘not show his
        # strength") the reflow cannot tell a rule from a quote, so the mark is
        # left for the audit and a repair pair.
        self.assertIn("He will ‘not show", self._body("He will ‘not show his strength."))

    def test_a_work_that_closes_a_quote_keeps_its_marks(self):
        body = self._body("The prophet saith,", "“comfort ye my people.”")
        self.assertIn("“comfort ye", body)

    def test_the_question_is_asked_of_the_part_not_the_volume(self):
        # The volume's front matter quotes; the work sliced out of it does not.
        text = "\n".join([
            "MEMOIR OF THE AUTHOR",
            "He called it “the sweetest of his books.”",
            "THE BRUISED REED AND SMOKING FLAX.",
            "[CHAPTER I. — The Text opened.]",
            "so that the church is",
            "‘armed with invincible courage.",
            "INDEX.",
        ])
        (_, body), = chapterize(text, "THE BRUISED REED AND SMOKING FLAX.", "INDEX.")
        self.assertIn("is armed with", body)
