"""The English-source ratchet, and the checks that keep the scanner honest.

Two jobs:

1. **The ratchet.** No finding class may grow past its committed baseline. The
   whole reason this exists is that we kept discovering import defects during
   *translation* — after the defect had already been reproduced faithfully into
   three to six language editions. A count that grows in a PR is one defect
   caught at review instead of eighteen months and five languages later.

2. **Precision regression.** The scanner's failure mode is not missing a defect,
   it is crying wolf: the first version reported 8,917 findings, of which nearly
   all were false, and output nobody trusts gets skimmed. Each check below pins
   the exact test that separates the defect from the convention, so a later
   "simplification" that drops one fails here rather than quietly re-flooding
   the report.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from library import english_audit
from library.english_audit import Record, audit_records, counts


def _findings(body_html: str, *, is_pd: bool = True, title: str = "") -> dict[str, int]:
    return counts(audit_records([Record("t ch01", "t", title, body_html, is_pd)]))


class EnglishAuditRatchetTests(SimpleTestCase):
    def test_no_class_grows_past_its_baseline(self):
        baseline = english_audit.read_baseline()
        current = counts(english_audit.audit_fixtures())
        grew = {
            label: (n, baseline.get(label, 0))
            for label, n in current.items()
            if n > baseline.get(label, 0)
        }
        self.assertEqual(
            grew,
            {},
            "English defect classes grew (class: now vs baseline). Fix them, or "
            "if the growth is legitimate re-pin with `manage.py audit_english "
            "--update-baseline` and say why in the commit message.",
        )

    def test_baseline_is_not_stale(self):
        """A class that has shrunk must be re-pinned, or the ratchet slips back.

        Without this the baseline silently re-permits every defect someone has
        already fixed.
        """
        baseline = english_audit.read_baseline()
        current = counts(english_audit.audit_fixtures())
        shrunk = {
            label: (current.get(label, 0), n)
            for label, n in baseline.items()
            if current.get(label, 0) < n
        }
        self.assertEqual(
            shrunk,
            {},
            "Defect classes have shrunk (class: now vs baseline) — good. "
            "Re-pin with `manage.py audit_english --update-baseline`.",
        )


class EnglishAuditPrecisionTests(SimpleTestCase):
    """One test per check, each pinning the defect AND the convention it spares."""

    def test_smallcaps_only_when_the_pieces_rejoin_into_a_word(self):
        # "L ORD" -> LORD is the extractor splitting small caps.
        self.assertEqual(_findings("<p>the L ORD is my shepherd</p>").get("broken-smallcaps"), 1)
        # "A SHORT" -> ASHORT is not a word; it is just a small-caps opening.
        # This single test took the class from 233 findings to 8.
        self.assertNotIn("broken-smallcaps", _findings("<p>A SHORT preface follows</p>"))

    def test_dropcap_only_when_the_remainder_is_a_common_word(self):
        self.assertEqual(_findings("<p>Ithink it is so</p>").get("dropcap-fused"), 1)
        for ordinary in ("Indian", "Inquire", "Ireland", "Increase"):
            self.assertNotIn(
                "dropcap-fused",
                _findings(f"<p>{ordinary} was mentioned</p>"),
                f"{ordinary} is an ordinary word, not a fused drop cap",
            )

    def test_anachronism_only_against_an_author_who_could_not_have_written_it(self):
        modern = "<p>He drove his car to the meeting</p>"
        # Andrew Murray died in 1917; cars in his mouth mean the import invented
        # text (this is exactly the humility-2 ch04 defect).
        self.assertEqual(_findings(modern, is_pd=True).get("anachronism"), 1)
        # A living author may write about cars.
        self.assertNotIn("anachronism", _findings(modern, is_pd=False))

    def test_orphan_quote_is_a_close_with_nothing_open(self):
        # A long quotation opens every paragraph and closes only the last, so an
        # odd count mid-run is the convention.
        run = "<p>“first part</p><p>“second part</p><p>“and the end.”</p>"
        self.assertNotIn("orphan-close-quote", _findings(run))
        self.assertEqual(
            _findings("<p>nothing was opened here.”</p>").get("orphan-close-quote"), 1
        )

    def test_space_before_punct_is_reported_only_where_it_is_sporadic(self):
        """17th-century typography vs an italics-strip artifact.

        The distribution is sharply bimodal — 777/647/586 in the three 17c texts
        against 1 or 2 in a modern one — so a work full of it is following its
        era's convention and a work with a handful has a defect.
        """
        one = "<p>a sentence ended oddly .</p>"
        sporadic = [Record("w ch01", "w", "", one, True)]
        self.assertEqual(counts(audit_records(sporadic)).get("space-before-punct"), 1)

        wholesale = [
            Record(f"w ch{i:02d}", "w", "", one, True)
            for i in range(english_audit.SPB_CONVENTION_MIN)
        ]
        self.assertNotIn("space-before-punct", counts(audit_records(wholesale)))

    def test_title_case_disagreeing_with_body(self):
        """A hyphenated single-letter suffix cased one way in the title and the
        other in the body — one of the two was retyped.

        The live instance is stepping-stones-2 ch13: the title reads "Type-a
        Specialist" where its own body reads "Type-A Specialist". Deliberately
        narrow — it fires only on a lone letter after the hyphen, so ordinary
        compounds ("Self-denial" against "Self-Denial") are left alone, those
        being a house-style question rather than a transcription slip.
        """
        self.assertEqual(
            _findings("<p>every Type-A Specialist</p>", title="Type-a Specialist").get(
                "title-case-vs-body"
            ),
            1,
        )
        self.assertNotIn(
            "title-case-vs-body",
            _findings("<p>on Self-Denial he wrote</p>", title="Self-denial"),
        )

    def test_clean_prose_produces_nothing(self):
        # The scanner's whole value is that a clean report means something.
        self.assertEqual(
            _findings("<p>He that hath ears to hear, let him hear.</p>", title="Hearing"), {}
        )


class EnglishAuditContractTests(SimpleTestCase):
    def test_only_unambiguous_classes_are_auto_fixable(self):
        """Guards the safety split the english-qa skill relies on.

        Widening this set means a machine starts rewriting the text of a
        public-domain author unattended. `broken-smallcaps` qualifies because
        the repair is forced — the pieces rejoin into exactly one real word.
        Nothing else does: the humility-2 "cars" defect needed a human to read
        the 1895 edition and find "The poor, who have nothing in themselves".
        """
        self.assertEqual(english_audit.AUTO_FIXABLE, frozenset({"broken-smallcaps"}))

    def test_every_class_the_scanner_emits_is_classified(self):
        """A new check must be declared auto-fixable, mechanical, or neither.

        Otherwise it lands in the report with no guidance and gets treated
        however the reader guesses.
        """
        known = (
            english_audit.AUTO_FIXABLE
            | english_audit.MECHANICAL
            | {
                "anachronism",
                "dropcap-fused",
                "misspelling",
                "orphan-close-quote",
                "run-together",
                "title-case-vs-body",
            }
        )
        emitted = set(counts(english_audit.audit_fixtures()))
        self.assertEqual(emitted - known, set(), "unclassified finding class(es)")

    def test_content_path_resolves_without_a_hardcoded_root(self):
        """The predecessor script hardcoded /home/user/... and ran nowhere else."""
        self.assertTrue((english_audit.CONTENT / "authors.json").exists())
