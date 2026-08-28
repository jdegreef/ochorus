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

from functools import lru_cache

from django.test import SimpleTestCase

from library import english_audit
from library.corrections import rejoin_linebreak_hyphens as rejoin
from library.english_audit import Record, audit_records, counts


@lru_cache(maxsize=1)
def _corpus() -> dict[str, dict[str, int]]:
    """One corpus scan shared by every test that needs it.

    Scanning 94 fixture files costs ~5s. Three tests want the same immutable
    artefact, and they live in two different TestCase classes, so `setUpClass`
    would still leave two scans — hence a module-level cache. Measured: 14.0s to
    4.7s for the file.
    """
    return english_audit.counts_by_work(english_audit.audit_fixtures())


def _findings(body_html: str, *, is_pd: bool = True, title: str = "") -> dict[str, int]:
    return counts(audit_records([Record("t ch01", "t", title, body_html, is_pd)]))


class EnglishAuditRatchetTests(SimpleTestCase):
    def test_findings_match_the_baseline_work_for_work(self):
        """No work's defect count may drift from its pin, in either direction.

        Growth is the regression this exists to catch: a new import that drags
        in forty hyphen-space artifacts fails here rather than surfacing
        eighteen months later, in a translation, in five languages.

        Shrinkage has to fail too, or the baseline silently re-permits every
        defect someone has already fixed — the pin would sit above the real
        number and a later regression back up to it would pass.
        """
        self.assertEqual(
            _corpus(),
            english_audit.read_baseline(),
            "The English audit no longer matches its baseline. A work that GREW "
            "has a new defect — fix it. A work that SHRANK has had one fixed — "
            "re-pin with `manage.py audit_english --update-baseline` and say in "
            "the commit message what you fixed.",
        )


class EnglishAuditPrecisionTests(SimpleTestCase):
    """One test per check, each pinning the defect AND the convention it spares."""

    def test_smallcaps_only_when_the_pieces_rejoin_into_a_word(self):
        # "L ORD" -> LORD is the extractor splitting small caps.
        self.assertEqual(_findings("<p>the L ORD is my shepherd</p>").get("broken-smallcaps"), 1)
        # "A SHORT" -> ASHORT is not a word; it is just a small-caps opening.
        # This single test took the class from 233 findings to 8.
        self.assertNotIn("broken-smallcaps", _findings("<p>A SHORT preface follows</p>"))

    def test_word_fusion_needs_a_function_head_a_common_tail_and_a_rare_whole(self):
        """The three conditions, and the convention each one spares.

        Measured against the corpus: all three together find 17 and every one
        is a real defect. Drop any one of them and the class re-floods, which
        is the failure this module exists to avoid.
        """
        # The defect: a space lost inside a sentence.
        self.assertEqual(_findings("<p>all my children weresafe, and he hoped</p>").get("word-fusion"), 1)
        self.assertEqual(_findings("<p>it would not be amiss tospeak of it</p>").get("word-fusion"), 1)

        # 1. The head must be a function word that cannot begin an English word.
        #    `in`, `be`, `for` and `up` are productive prefixes and are excluded
        #    by their absence — otherwise `inborn`, `befitting`, `forgiver` and
        #    `upbringing` all read as fusions.
        for ordinary in ("inborn", "befitting", "forgiver", "upbringing", "aboard"):
            self.assertNotIn(
                "word-fusion",
                _findings(f"<p>the {ordinary} thing</p>"),
                f"{ordinary} begins with a productive prefix, not a lost space",
            )

        # 2. The tail must be a word the library uses often. Without this the
        #    same heads match ordinary vocabulary.
        for ordinary in ("tornado", "torchlight", "buttery", "shearings", "tonsure"):
            self.assertNotIn(
                "word-fusion",
                _findings(f"<p>the {ordinary} was there</p>"),
                f"{ordinary} splits into a head and a non-word, not two words",
            )

        # 3. The fused form must itself be rare. A real word recurs — `himself`
        #    3,491 times across the library, `today` 445 — so the corpus counts
        #    are what tell a compound from a fusion.
        for real in ("himself", "themselves", "yourself", "today", "whatever", "whenever"):
            self.assertNotIn(
                "word-fusion",
                _findings(f"<p>he said {real} would do</p>"),
                f"{real} is a word the library uses constantly, not a fusion",
            )

    def test_word_fusion_spares_the_latin_it_cannot_judge(self):
        """A foreign quotation is the one thing an English word oracle can't
        read: `solet` and `nomen` are Latin, and both are named rather than
        reasoned about."""
        for latin in ("solet", "nomen"):
            self.assertNotIn("word-fusion", _findings(f"<p>tristis abire {latin} est</p>"))

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

    def test_inline_markup_does_not_manufacture_a_space_before_punctuation(self):
        """Stripping `</em>` to a space invented the defect it was looking for.

        `<em>The True Vine</em>, dedicating` read as "Vine , dedicating" — an
        italics-strip artifact, said the check, about our own italics. That was
        59% of all raw space-before-punct hits and 100% of the biographies',
        where citing works in italics is the house style.
        """
        self.assertNotIn(
            "space-before-punct",
            _findings("<p>he wrote <em>The True Vine</em>, dedicating it to them</p>"),
        )
        # The genuine article — a space in the text itself — still fires.
        self.assertEqual(
            _findings("<p>a sentence ended oddly .</p>").get("space-before-punct"), 1
        )

    def test_block_tags_inside_a_block_still_separate_sentences(self):
        """Only INLINE tags may vanish.

        Dropping every tag instead fused "one.</p><p>Two" into "one.Two" and
        `run-together` went from 11 findings to 30, all of them seams.
        """
        self.assertNotIn(
            "run-together",
            _findings("<blockquote><p>ends here.</p><p>Starts there.</p></blockquote>"),
        )

    def test_misspelling_needs_word_boundaries(self):
        """The trap the corrections table already warned about.

        Matching "Brazilia" as a bare substring fired on every correct
        "Brazilian" — 6 of 23 findings were false, and the BODY_CORRECTIONS
        entry for it carries a comment saying the bare string "also occurs
        inside 'Brazilian' five times, which is correct and must not move".
        """
        self.assertEqual(_findings("<p>the city of Brazilia</p>").get("misspelling"), 1)
        for correct in ("Brazilian", "Brazilians"):
            self.assertNotIn(
                "misspelling",
                _findings(f"<p>a {correct} missionary</p>"),
                f"{correct} is spelled correctly",
            )

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


class BiographyAuditTests(SimpleTestCase):
    """Biographies were the one English content type nothing checked."""

    def _bio(self, body_html: str) -> dict[str, int]:
        return counts(audit_records([Record("x (bio)", "x", "Name", body_html, False)]))

    def test_a_bio_is_audited_for_transcription_damage(self):
        self.assertEqual(self._bio("<p>the L ORD is good</p>").get("broken-smallcaps"), 1)

    def test_a_bio_is_not_judged_for_anachronism(self):
        """We write these, in modern English, about people who died in 1917.

        The anachronism check exists to catch invented text in a
        public-domain author's mouth. A biographer saying a life was later
        dramatised on television is writing normally, not inventing.
        """
        self.assertNotIn("anachronism", self._bio("<p>later shown on television</p>"))

    def test_every_bio_with_prose_is_reachable(self):
        from library.english_audit import _bio_records

        bios = list(_bio_records())
        self.assertGreater(len(bios), 20, "authors.json should yield most authors' bios")
        self.assertTrue(all(r.body_html for r in bios))


class LineBreakHyphenTests(SimpleTestCase):
    """The one rule-based repair, and the four things it must never do.

    A word broken across a line in the source PDF arrives as "self-" + a line
    break, and the paragraph merge rejoins it with a space. 429 of these were
    stored across 39 works. The repair closes the space and NOTHING else — it
    never removes the hyphen, and that restraint is what makes it safe to run
    unattended on a public-domain author.
    """

    def test_closes_the_space(self):
        self.assertEqual(rejoin("self- righteous"), "self-righteous")
        self.assertEqual(rejoin("Fountain- head"), "Fountain-head")

    def test_never_removes_the_hyphen(self):
        """Dropping it would modernise the author — the one forbidden edit.

        "to-day" is Wesley's spelling and "over-much" is Whitefield's. The
        unhyphenated form is attested elsewhere in those same works, so a rule
        keyed on attestation would have "corrected" both.
        """
        for period_spelling in ("to- day", "over- much", "four- fold", "whole- hearted"):
            got = rejoin(period_spelling)
            self.assertEqual(got, period_spelling.replace("- ", "-"))
            self.assertIn("-", got, "the author's hyphen must survive")

    def test_leaves_a_capitalised_resumption_alone(self):
        """A broken word never resumes with a capital, so these are unprovable.

        They are either a flattened dash — "thus- Moses, the man of God", "I
        ask- What does this mean?" — or a genuine proper-noun compound —
        "non- Israelite", "Golden- Mouthed" — and nothing mechanical separates
        the two. 21 cases; leaving ~7 real compounds unjoined is much cheaper
        than welding a clause boundary shut.
        """
        for unprovable in ("thus- Moses", "I ask- What", "non- Israelite", "Golden- Mouthed"):
            self.assertEqual(rejoin(unprovable), unprovable)

    def test_leaves_suspended_compounds_alone(self):
        """"two- and three-fold" — here the space is correct English."""
        for suspended in ("two- and twenty", "day- to day", "pre- or post-"):
            self.assertEqual(rejoin(suspended), suspended)

    def test_never_joins_across_a_paragraph_boundary(self):
        """A hyphen at the end of a <p> is a verse line, not a broken word.

        the-possibilities-of-faith quotes "Glory begin below-</p><p>Celestial
        fruits" — joining that would run two lines of a poem together.
        """
        verse = "<p>Glory begin below-</p><p>Celestial fruits</p>"
        self.assertEqual(rejoin(verse), verse)

    def test_is_idempotent(self):
        once = rejoin("self- righteous")
        self.assertEqual(rejoin(once), once)

    def test_the_fixture_is_clean(self):
        """The committed English fixture must carry no repairable hyphen.

        `apply_body_corrections` heals the database on every deploy, but the
        fixture is a file — nothing rewrites it, and it is what a fresh build
        loads and what the ratchet measures.
        """
        import json

        from library.content_fixtures import BOOKS_DIR, SERMONS_DIR

        dirty = []
        for path in sorted(BOOKS_DIR.glob("*.en.json")) + sorted(SERMONS_DIR.glob("*.en.json")):
            for row in json.loads(path.read_text(encoding="utf-8")):
                body = row.get("fields", {}).get("body_html") or ""
                if rejoin(body) != body:
                    dirty.append(path.name)
                    break
        self.assertEqual(
            dirty, [], "run `manage.py normalize_english_fixture --write`"
        )


class CorrectionsHygieneTests(SimpleTestCase):
    def test_no_replacement_pair_is_dead(self):
        """Every repair must still refer to text that exists somewhere.

        A pair whose `old` has been applied and whose `new` is nowhere to be
        found is repairing a book that no longer contains either string — a
        typo in the entry, or a work that has since been dropped. It sits in
        the table looking like protection and provides none.

        Checked in both directions because a correction's lifecycle has two
        valid states: not yet applied to the fixture (`old` present) and
        applied (`new` present).
        """
        import json

        from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
        from library.corrections import BODY_CORRECTIONS

        corpus = "\n".join(
            json.dumps(json.loads(p.read_text(encoding="utf-8")), ensure_ascii=False)
            for p in list(BOOKS_DIR.glob("*.json")) + list(SERMONS_DIR.glob("*.json"))
        )
        dead = [
            (slug, old)
            for slug, entry in BODY_CORRECTIONS.items()
            for old, new in entry.get("replacements", ())
            if old not in corpus and new not in corpus
        ]
        self.assertEqual(dead, [], "BODY_CORRECTIONS entries matching nothing in the fixture")


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
        emitted = {label for classes in _corpus().values() for label in classes}
        self.assertEqual(emitted - known, set(), "unclassified finding class(es)")
