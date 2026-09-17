"""The mined-provenance gate, and the checks that keep it honest.

Two jobs, the same two ``tests_verse_consistency`` and ``tests_english_audit``
have, for the same reasons.

1. **The gate.** No translation may claim a verse was mined verbatim from a
   shipped file when the two texts disagree. ``KNOWN_ADAPTED`` pins the backlog;
   the suite fails on anything new, and fails when a pinned entry is FIXED but
   left behind, so the list can only shrink.

2. **Precision.** The failure mode here is not missing an adapted verse, it is
   crying wolf — and this check has an unusually good way to cry wolf, because
   both sides are located by chapter:verse alone. A first cut reported 37
   findings, of which the great majority were different books sharing a number
   (Joel 2:25 against Revelation 2:25). Each rule below pins the defect AND the
   convention it spares, so a later tidy-up cannot quietly re-flood the report.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from library import mined_verification as mv

# `mined` claims the corpus contradicts: the two texts are the same verse, but
# not the same words — a verse adapted while being lifted, which the
# translation-worker skill says is `self_rendered`, not `mined`.
#   (notes file, reference)
# Delete the line when the repair ships — a stale entry fails below.
KNOWN_ADAPTED: set[tuple[str, str]] = {
    # The source reads "kunyenyekeana katika kumcha Kristo"; the translation
    # re-persons the verb to "mkinyenyekeana …". Faithful Swahili, but the
    # wording is the translator's, so the row owes a reviewer a look.
    ("watchman-nee-a-life.sw.json", "Ephesians 5:21"),
}


class MinedProvenanceGateTests(SimpleTestCase):
    """Reads the shipped corpus. No DB, no network."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.findings, cls.census = mv.audit()

    def test_no_unpinned_contradicted_claim(self):
        new = sorted(str(f) for f in self.findings
                     if (f.notes_file, f.reference) not in KNOWN_ADAPTED)
        self.assertEqual(
            new,
            [],
            "A translation claims a verse was mined verbatim from a shipped file, "
            "but the two texts differ. Either match the source's wording exactly, "
            "or mark the row `self_rendered` and drop its source_file — an "
            "adapted verse is the reviewer's job, and counting it as checked "
            "hides work rather than doing it.",
        )

    def test_the_pin_shrinks_only(self):
        """A repaired claim must be un-pinned, or the gate loosens."""
        found = {(f.notes_file, f.reference) for f in self.findings}
        stale = sorted(KNOWN_ADAPTED - found)
        self.assertEqual(
            stale,
            [],
            "These are pinned as adapted but the corpus no longer contradicts "
            "them — delete them from KNOWN_ADAPTED so the gate can only tighten.",
        )

    def test_no_note_cites_a_file_that_does_not_exist(self):
        """A fixture-shaped source_file must resolve; a Bible name is not one."""
        self.assertEqual(self.census.get("cites_a_missing_file", 0), 0)

    def test_the_audit_actually_examined_something(self):
        """Guards the whole suite against silently checking nothing.

        Every rule below narrows what is comparable, and a scanner that narrows
        itself to zero passes every other test in this file while proving
        nothing. 121 rows were checkable on 2026-09-17; the floor is set well
        under that so ordinary corpus churn doesn't trip it, and a collapse to
        near-zero does.
        """
        checked = self.census.get("verified", 0) + self.census.get("contradicted", 0)
        self.assertGreater(checked, 60, f"census: {dict(self.census)}")


class MinedPrecisionTests(SimpleTestCase):
    """One test per rule, each pinning the defect AND the convention it spares."""

    # --- rule 2: same-verse confirmation -------------------------------------

    def test_two_books_sharing_a_verse_number_are_not_the_same_verse(self):
        """The false positive that forced a proportional threshold.

        A note reading "1 Coríntios 2:14" against a body quoting 2 Corinthians
        2:14 and a source holding 1 John 2:14 — three books, one number. They
        share "Deus" and nothing else, so a one-shared-word rule reported it.
        """
        self.assertFalse(
            mv.same_verse(
                "graças a Deus, que sempre nos faz triunfar em Cristo e por meio "
                "de nós manifesta em todo lugar o cheiro do seu conhecimento",
                "venceu o maligno, sendo forte porque a palavra de Deus permanece nele",
            )
        )

    def test_one_clause_worded_two_ways_is_the_same_verse(self):
        """The convention the rule above must not eat.

        The Ephesians 5:21 pin: same clause, the verb re-personed. If this read
        as two different verses the gate would exempt exactly what it exists to
        find.
        """
        self.assertTrue(
            mv.same_verse(
                "mkinyenyekeana katika kumcha Kristo",
                "kunyenyekeana katika kumcha Kristo",
            )
        )

    # --- rule 3: verbatim means containment ----------------------------------

    def test_a_partial_quotation_is_still_verbatim(self):
        """Quoting half a verse where the source has all of it IS mining."""
        self.assertTrue(
            mv.is_verbatim(
                "Mimi ndimi mzabibu",
                "Mimi ndimi mzabibu, ninyi ni matawi",
            )
        )

    def test_punctuation_and_case_are_not_a_wording_difference(self):
        """A verse opening a sentence is capitalised in the body, not in the source."""
        self.assertTrue(
            mv.is_verbatim(
                "Usiogope, kwa maana mimi ni pamoja nawe.",
                "usiogope kwa maana mimi ni pamoja nawe",
            )
        )

    def test_a_re_personed_verb_is_not_verbatim(self):
        """The #426 class, reduced to its smallest form."""
        self.assertFalse(
            mv.is_verbatim(
                "mkinyenyekeana katika kumcha Kristo",
                "kunyenyekeana katika kumcha Kristo",
            )
        )

    def test_an_empty_side_is_never_verbatim(self):
        self.assertFalse(mv.is_verbatim("", "kunyenyekeana katika kumcha Kristo"))
        self.assertFalse(mv.is_verbatim("mkinyenyekeana", ""))

    # --- source_file classification ------------------------------------------

    def test_a_bible_edition_is_not_a_filename(self):
        """6,005 of 6,559 mined rows cite one of these; none is a defect."""
        for name in (
            "Van Dyck (arb-vd) Bible text",
            "Louis Segond (1910)",
            "Open Luganda Contemporary Bible (lug_bib)",
            "Reina-Valera (rv1858) Bible via Take Root API",
        ):
            self.assertFalse(mv.looks_like_a_filename(name), name)
            self.assertFalse(mv.names_a_shipped_fixture(name), name)

    def test_a_fixture_name_is_recognised_as_one(self):
        self.assertTrue(mv.looks_like_a_filename("godliness.sw.json"))
        self.assertTrue(mv.looks_like_a_filename("waiting-on-god.pt.json"))

    def test_a_missing_fixture_is_shaped_like_one_but_does_not_resolve(self):
        """The two halves are separate on purpose — see names_a_shipped_fixture."""
        self.assertTrue(mv.looks_like_a_filename("no-such-book.sw.json"))
        self.assertFalse(mv.names_a_shipped_fixture("no-such-book.sw.json"))

    # --- reference parsing ---------------------------------------------------

    def test_a_split_verse_suffix_is_not_a_number(self):
        """`15:28a` marks which half was quoted; the numbers are still 15:28."""
        self.assertEqual(mv.reference_numbers("Matthew 15:28a"), (15, 28))
        self.assertEqual(mv.reference_numbers("Romans 13:13b-14"), (13, 13))

    def test_a_reference_with_no_chapter_verse_yields_nothing(self):
        self.assertIsNone(mv.reference_numbers("Psalms"))
        self.assertIsNone(mv.reference_numbers(""))

    def test_a_localized_book_name_still_parses(self):
        """Notes should carry English names, but some carry localized ones."""
        self.assertEqual(mv.reference_numbers("1 Coríntios 2:14"), (2, 14))
