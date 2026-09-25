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

import json
import re
from functools import lru_cache
from pathlib import Path

from django.test import SimpleTestCase

from library import corrections, english_audit
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


class EnglishAuditRepinTests(SimpleTestCase):
    """The guard on the re-pin, the sibling of `VerseConsistencyRepinTests`.

    The ratchet above is exact equality against the committed file, so ANY
    change — including importing a book — needs `--update-baseline`. That makes
    the re-pin routine, and a routine re-pin is one nobody reads: whatever
    defects the new import carries go straight into the pin, and so does any
    regression in a work that was already there. 59 works on 2026-08-24, 87 on
    2026-09-16, with nothing on the way saying what each import brought in.

    So the two cases are separated. A new work is ordinary and is reported; an
    already-pinned work that GAINED findings needs `--absorb` said out loud.
    """

    OLD = {"a-book": {"hyphen-space": 3, "broken-smallcaps": 1}}

    def test_an_existing_work_gaining_findings_is_a_regression(self):
        self.assertEqual(
            english_audit.baseline_regressions({"a-book": {"hyphen-space": 5}}, self.OLD),
            ["a-book [hyphen-space]: 3 -> 5"],
        )

    def test_an_existing_work_gaining_a_whole_class_is_a_regression(self):
        self.assertEqual(
            english_audit.baseline_regressions({"a-book": {"welded-footnote": 2}}, self.OLD),
            ["a-book [welded-footnote]: 0 -> 2"],
        )

    def test_a_brand_new_work_is_not_a_regression(self):
        """An import is the ordinary way this file grows — see BASELINE_PATH."""
        self.assertEqual(
            english_audit.baseline_regressions({"new-book": {"hyphen-space": 40}}, self.OLD), []
        )

    def test_a_new_work_is_reported_with_what_it_brings_in(self):
        self.assertEqual(
            english_audit.baseline_new_works(
                {"new-book": {"hyphen-space": 40, "broken-smallcaps": 2}}, self.OLD
            ),
            ["new-book: 42 finding(s) across 2 class(es)"],
        )

    def test_repairing_a_work_is_not_a_regression(self):
        self.assertEqual(
            english_audit.baseline_regressions({"a-book": {"hyphen-space": 1}}, self.OLD), []
        )

    def test_the_committed_baseline_is_its_own_fixed_point(self):
        self.assertEqual(english_audit.baseline_regressions(_corpus()), [])


class EnglishAuditPrecisionTests(SimpleTestCase):
    """One test per check, each pinning the defect AND the convention it spares."""

    def test_smallcaps_only_when_the_pieces_rejoin_into_a_word(self):
        # "L ORD" -> LORD is the extractor splitting small caps.
        self.assertEqual(_findings("<p>the L ORD is my shepherd</p>").get("broken-smallcaps"), 1)
        # "A SHORT" -> ASHORT is not a word; it is just a small-caps opening.
        # This single test took the class from 233 findings to 8.
        self.assertNotIn("broken-smallcaps", _findings("<p>A SHORT preface follows</p>"))

    def test_welded_footnote_needs_the_marker_DOUBLED_with_the_same_number(self):
        """The doubled marker is the whole signal, and it has to stay narrow.

        `<sup>` is ordinary markup here — real footnote references, verse
        numbers, ordinals — so flagging any `<sup>` next to prose would fire on
        every properly-extracted note in the corpus. What is wrong is the
        extractor emitting the in-text marker AND the note's own label at the
        foot of the page, then running the note body into the sentence.
        """
        # The defect: same number twice, note text welded to the prose.
        welded = "<p>Should prove <i>ad infinitum</i>,<sup>1</sup><sup>1</sup>Without end. and eat out</p>"
        self.assertEqual(_findings(welded).get("welded-footnote"), 1)

        # A correctly extracted reference — one marker, note elsewhere.
        self.assertNotIn("welded-footnote", _findings("<p>worketh in Christians,<sup>2</sup> and of the Spirit</p>"))
        # Two ADJACENT references to different notes. Ugly, but two real
        # markers, not a marker and a duplicated label.
        self.assertNotIn("welded-footnote", _findings("<p>as both attest<sup>4</sup><sup>5</sup> in their letters</p>"))
        # An ordinal, which is what <sup> is for outside footnotes.
        self.assertNotIn("welded-footnote", _findings("<p>on the 1<sup>st</sup> of June</p>"))

    def test_welded_footnote_is_found_in_headings_too(self):
        """155 of the corpus instances are inside an <h2>, where the doubled
        digits render in the heading itself."""
        h = "<h2>Fourth Series <sup>3</sup><sup>3</sup>Consisting of seven discourses</h2>"
        self.assertEqual(_findings(h).get("welded-footnote"), 1)

    def test_welded_footnote_is_not_auto_fixable(self):
        """Where the note ENDS is a judgement — only ~39% close on a clean full
        stop — so a machine must never cut it."""
        from library.english_audit import AUTO_FIXABLE, MECHANICAL

        self.assertNotIn("welded-footnote", AUTO_FIXABLE)
        self.assertNotIn("welded-footnote", MECHANICAL)

    def test_lost_paragraphing_is_judged_per_CHAPTER_not_per_paragraph(self):
        """The granularity is the whole finding.

        Four per-paragraph rules were measured against the corpus and each one
        failed: a long block alone (749 blocks of 20+ sentences, mostly the
        period's own prose), a division marker mid-block (922 blocks, and a read
        of nine showed roughly two true — the rest were scripture citations split
        at `Rom. viii. | 32.`), a quotation fused to its commentary (3 findings,
        one of them a `”` inside an editorial bracket), and a mid-block speech
        attribution (8, mostly Wesley citing apostles). None had an oracle to
        appeal to. At chapter scale the question needs none.
        """
        long_para = "word " * 500
        # A chapter set as two enormous blocks has lost its paragraphing.
        self.assertEqual(
            _findings(f"<p>{long_para}</p><p>{long_para}</p>").get("lost-paragraphing"), 1
        )
        # And the shape `life-of-antony` sets 28 of its 45 chapters in: a whole
        # chapter as ONE block. A 600-word floor exempted that entire book.
        self.assertEqual(_findings(f"<p>{'word ' * 450}</p>").get("lost-paragraphing"), 1)

        # A chapter of the SAME length, properly broken up, is not a finding —
        # length alone is not the defect, and a class that said so would report
        # most of the library.
        broken_up = "".join(f"<p>{'word ' * 100}</p>" for _ in range(10))
        self.assertNotIn("lost-paragraphing", _findings(broken_up))

        # A single long paragraph inside an otherwise well-set chapter is left
        # alone. This is the case per-paragraph rules kept getting wrong: the
        # period writes long, and `on-the-priesthood` legitimately averages 256
        # words a paragraph.
        one_giant = f"<p>{long_para}</p>" + "".join(
            f"<p>{'word ' * 100}</p>" for _ in range(10)
        )
        self.assertNotIn("lost-paragraphing", _findings(one_giant))

        # Short works are exempt: a note or a fragment is honestly one block.
        self.assertNotIn("lost-paragraphing", _findings(f"<p>{'word ' * 250}</p>"))

    def test_lost_paragraphing_counts_blocks_and_words_the_way_the_reader_sees_them(self):
        """Both counts are taken from the RAW html, and both have to be.

        `BLOCK`'s `<(p|…)>(.*?)</\1>` swallows a `<blockquote>` and the `<p>`s
        inside it as a single match. Counting blocks that way undercounts any
        chapter carrying a multi-paragraph quotation and inflates its mean —
        34 fixture records are already miscounted like that — which in a class
        whose whole claim is precision is a false-positive vector.
        """
        quoted = "<blockquote>" + "".join(
            f"<p>{'word ' * 100}</p>" for _ in range(6)
        ) + "</blockquote>"
        self.assertNotIn(
            "lost-paragraphing",
            _findings(quoted),
            "the paragraphs inside a blockquote are still paragraphs",
        )

        # Words come from the whole body, not from inside block tags: 204
        # records carry prose no `<p>` encloses, and a chapter that lost its
        # tags altogether would otherwise score zero words and be skipped in
        # silence — the one shape this check least wants to miss.
        self.assertEqual(_findings("word " * 450).get("lost-paragraphing"), 1)

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

    def test_word_fusion_spares_the_agent_noun_washer(self):
        """`washer` is `was`+`her` by the oracle but an ordinary English word;
        it is named in FUSION_EXEMPT, like the Latin above."""
        self.assertNotIn(
            "word-fusion",
            _findings("<p>she was a beautiful washer and ironer</p>"),
        )

    def test_dropcap_only_when_the_remainder_is_a_common_word(self):
        self.assertEqual(_findings("<p>Ithink it is so</p>").get("dropcap-fused"), 1)
        for ordinary in ("Indian", "Inquire", "Ireland", "Increase"):
            self.assertNotIn(
                "dropcap-fused",
                _findings(f"<p>{ordinary} was mentioned</p>"),
                f"{ordinary} is an ordinary word, not a fused drop cap",
            )

    def test_anachronism_only_against_an_author_who_could_not_have_written_it(self):
        modern = "<p>He answered it by e-mail</p>"
        # Andrew Murray died in 1917; e-mail in his mouth means the import
        # invented text — the same shape as the humility-2 ch04 defect, and what
        # caught the real way-into-holiest transcriber note. One trigger, so the
        # count proves the PD gate rather than which triggers happen to survive.
        self.assertEqual(_findings(modern, is_pd=True).get("anachronism"), 1)
        # A living author may write about e-mail.
        self.assertNotIn("anachronism", _findings(modern, is_pd=False))

    def test_anachronism_does_not_fire_on_the_period_word_car(self):
        # `cars?` was removed: in a pre-automobile corpus every "car" is a
        # railroad car, streetcar, balloon car or biblical chariot — 41 false /
        # 0 true across the corpus. See the ANACHRONISM comment for the history.
        for period in (
            "<p>I took the cars to Rochester</p>",          # railroad
            "<p>on the Sixth avenue cars</p>",              # streetcar
            "<p>King Solomon made himself a car of state</p>",  # Song of Songs 3:9
            "<p>the great juggernaut car of India</p>",     # temple chariot
        ):
            self.assertNotIn("anachronism", _findings(period, is_pd=True), period)

    def test_orphan_quote_is_a_close_with_nothing_open(self):
        # A long quotation opens every paragraph and closes only the last, so an
        # odd count mid-run is the convention.
        run = "<p>“first part</p><p>“second part</p><p>“and the end.”</p>"
        self.assertNotIn("orphan-close-quote", _findings(run))
        self.assertEqual(
            _findings("<p>nothing was opened here.”</p>").get("orphan-close-quote"), 1
        )

    def test_orphan_open_quote_is_a_margin_rule_read_as_a_mark(self):
        """`the-bruised-reed`'s shape: opening marks mid-sentence on a lowercase
        word, nothing closing them, far too many to be quotation."""
        peppered = "<p>a king of poor ‘and afflicted persons, he will ‘not show it</p>" * 5
        self.assertEqual(_findings(peppered).get("orphan-open-quote"), 10)

    def test_orphan_open_quote_spares_real_quotation(self):
        for html in (
            # a long quotation opens every paragraph, capitalised, closes once
            "<p>“And he came unto Lehi</p><p>“And he found a jawbone.”</p>",
            # opens mid-sentence on a lowercase word, but closes in the block
            "<p>he told them that ‘the Holy Spirit would come’ upon them</p>",
            "<p>we have “received the Spirit” of adoption</p>",
        ):
            with self.subTest(html=html[:40]):
                self.assertNotIn("orphan-open-quote", _findings(html))

    def test_orphan_open_quote_is_judged_as_a_density(self):
        """One stray in a long work is noise; the same stray in a short one
        at Bruised Reed density is the defect."""
        stray = "<p>a king of poor ‘and afflicted persons</p>"
        filler = "<p>" + "plain prose " * 50 + "</p>"
        self.assertNotIn("orphan-open-quote", _findings(stray + filler * 20))
        self.assertIn("orphan-open-quote", _findings(stray))

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

    def test_stray_parens_needs_the_pair_to_be_EMPTY(self):
        """A cross-reference whose anchor text the sanitizer deleted.

        EMPTINESS is the test, and it is the whole reason the class is exact —
        see `STRAY_PARENS` for the cause, the corpus measurement, and why the
        neighbouring unbalanced-paren idea was rejected. What this pins is the
        line between the two: an empty pair is the defect, a pair carrying
        anything at all is the author's prose.
        """
        # The defect, six of them in one sentence of `holy-in-christ` ch10.
        self.assertEqual(
            _findings("<p>deep Restfulness (), humble Reverence ()</p>").get("stray-parens"), 2
        )
        # Same defect with the space the extractor sometimes leaves behind.
        self.assertEqual(
            _findings("<p>known by us in their power. ( )</p>").get("stray-parens"), 1
        )
        # The convention: a parenthesis with content, however short, is prose.
        for kept in ("(ch. 3)", "(a)", "(Note A.)", "(see Luke iv.)"):
            self.assertNotIn(
                "stray-parens",
                _findings(f"<p>deep Restfulness {kept}, and so on</p>"),
                f"{kept} carries a reference",
            )

    def test_stray_parens_does_not_claim_the_defects_it_cannot_see(self):
        """The three shapes it is blind to, pinned so a clean report is read
        for exactly what it says.

        All three are the same sanitizer damage wearing a shape an emptiness
        test cannot match, and each was found by reading a shipped work rather
        than by a scanner. Widening the pattern to reach any of them is what
        would cost the class the precision it is being added for.
        """
        # 1. A lone unmatched `)` — `ministry-of-intercession` ch13, where
        #    Gutenberg's own transcription dropped the opening paren. Only a
        #    balance check sees this, and balance measures 57 rows.
        self.assertNotIn("stray-parens", _findings("<p>of His spirit to the Father. )</p>"))

        # 2. Quote marks left between the parentheses — `holy-in-christ`
        #    ch12, where Gutenberg had
        #    `(see ‘<a class="pginternal">Sixth Day</a>’)`.
        self.assertNotIn(
            "stray-parens", _findings("<p>His Glory and Majesty (see ‘’). And here</p>")
        )

        # 3. A dropped HEADING — `holy-in-christ` ch33 as it ships, where the
        #    heading was deleted outright and only its rule survived. There is
        #    no punctuation left for ANY text-level check to catch, which is
        #    why the assertion below is about the class and not about this
        #    snippet: see STRAY_PARENS for the two selectors that do this.
        self.assertNotIn(
            "stray-parens", _findings("<hr/> <p>In a little book—Holiness, as</p>")
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
        """The committed English fixture must carry no repairable text.

        `apply_body_corrections` heals the database on every deploy, but the
        fixture is a file — nothing rewrites it, and it is what a fresh build
        loads and what the ratchet measures.

        Checks `apply_body_corrections`, NOT the bare hyphen rule. It used to
        check the rule, which is the same blind spot the command had: a
        DECLARED repair added to `BODY_CORRECTIONS` later leaves the fixture
        stale, the rule says nothing about it, and ten book fixtures sat that
        way undetected. Both body fields, because `body_text` is derived from
        `body_html` and a file that corrects one and not the other disagrees
        with itself.
        """
        import json

        from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
        from library.corrections import apply_body_corrections

        dirty = []
        for path in sorted(BOOKS_DIR.glob("*.en.json")) + sorted(SERMONS_DIR.glob("*.en.json")):
            slug = path.name[: -len(".en.json")]
            for row in json.loads(path.read_text(encoding="utf-8")):
                fields = row.get("fields", {})
                order = fields.get("order")
                if any(
                    apply_body_corrections(slug, order, fields.get(key) or "")
                    != (fields.get(key) or "")
                    for key in ("body_html", "body_text")
                ):
                    dirty.append(path.name)
                    break
        self.assertEqual(
            dirty, [], "run `manage.py normalize_english_fixture --write`"
        )


class TranscriptionFootnoteTests(SimpleTestCase):
    """`strip_transcription_footnotes` — the opt-in sub-case of the weld.

    Wesley's Sermons weld a doubled-marker "[text from the 1872 edition]" stamp
    into 122 sermon-number headings. This removes exactly those, and its whole
    safety is that it fires ONLY on a doubled same-numbered marker whose note is
    that stamp and which ends the heading. It must leave every genuine note
    alone, because those are content a later pass will re-place, not delete.
    """

    def _strip(self, html):
        from library.corrections import strip_transcription_footnotes

        return strip_transcription_footnotes(html)

    def test_removes_the_stamp_and_leaves_the_heading(self):
        for note in (
            "[text from the 1872 edition]",
            "(text of the 1872 edition)",
            "[text of the 1872 ed.]",
            "[text from the 1872 Edition]",
        ):
            html = f"<h2>Sermon 7 <sup>15</sup><sup>15</sup>{note} </h2>"
            with self.subTest(note=note):
                self.assertEqual(self._strip(html), "<h2>Sermon 7</h2>")

    def test_keeps_a_genuine_dateline_note(self):
        """"Preached at ..." is content — this pass must not touch it."""
        html = ("<h2>The Almost Christian <sup>7</sup><sup>7</sup>"
                "Preached at St. Mary\u2019s, Oxford, on July 25, 1741. </h2>")
        self.assertEqual(self._strip(html), html)

    def test_keeps_a_series_description(self):
        html = ("<h2>Fourth Series <sup>3</sup><sup>3</sup>Consisting of seven "
                "discourses which were published by Mr. Wesley only.</h2>")
        self.assertEqual(self._strip(html), html)

    def test_needs_the_marker_doubled_with_the_same_number(self):
        # A single marker is a correctly extracted reference.
        html = "<h2>Sermon 7 <sup>15</sup>[text from the 1872 edition] </h2>"
        self.assertEqual(self._strip(html), html)
        # Two DIFFERENT numbers are two real markers, not a marker + label.
        html2 = "<h2>Sermon 7 <sup>15</sup><sup>16</sup>[text from the 1872 edition] </h2>"
        self.assertEqual(self._strip(html2), html2)

    def test_only_fires_inside_a_heading(self):
        """The `</h2>` lookahead keeps it off body prose, even if some
        paragraph ever carried the same stamp."""
        html = "<p>as noted<sup>4</sup><sup>4</sup>[text from the 1872 edition] the text reads</p>"
        self.assertEqual(self._strip(html), html)

    def test_is_idempotent(self):
        once = self._strip("<h2>Sermon 7 <sup>15</sup><sup>15</sup>[text from the 1872 edition] </h2>")
        self.assertEqual(self._strip(once), once)


class LoneFootnoteMarkerTests(SimpleTestCase):
    """`strip_footnote_markers` — the corpus-wide rule that removes lone
    footnote-reference superscripts (residue the notes are gone from).

    Its whole safety is that it fires only on a LONE marker: an empty
    ``<sup></sup>`` or a bare numbered one, never a marker that abuts another
    ``<sup>`` (a welded footnote, a different and tracked defect), never an
    ordinal (which keeps its letters), and never an inline ``[n]`` bracket
    (which is usually the author's own enumeration and content the page keeps).
    """

    def _strip(self, html):
        from library.corrections import strip_footnote_markers

        return strip_footnote_markers(html)

    def test_removes_an_empty_marker(self):
        self.assertEqual(
            self._strip("<p>towards its centre,<sup></sup> from that</p>"),
            "<p>towards its centre, from that</p>",
        )

    def test_removes_an_empty_marker_before_a_block_close(self):
        self.assertEqual(
            self._strip("<p>availeth much.<sup></sup></p>"),
            "<p>availeth much.</p>",
        )

    def test_removes_a_bare_numbered_marker(self):
        self.assertEqual(
            self._strip("<p>first did meet with grace;<sup>4</sup> for he</p>"),
            "<p>first did meet with grace; for he</p>",
        )

    def test_leaves_a_welded_footnote_untouched(self):
        """Removing only its markers would strand the note text mid-prose, so
        the lookbehind/lookahead exclude both markers of the pair."""
        welded = "<p>the only Son from me.”<sup>1</sup><sup>1</sup>Full Text: Genesis 22:1–12</p>"
        self.assertEqual(self._strip(welded), welded)

    def test_keeps_an_ordinal_superscript(self):
        """An ordinal keeps its letters (`1<sup>st</sup>`); the digit class
        cannot match it, so a genuine ordinal survives."""
        html = "<p>on the 1<sup>st</sup> of June</p>"
        self.assertEqual(self._strip(html), html)

    def test_leaves_inline_bracket_enumeration_alone(self):
        """`[1]`/`[a]` are the reader's (ear-only) concern — the page keeps
        them as the author's numbered points."""
        html = "<p>three things requisite: [1] Wisdom. [2] Authority.</p>"
        self.assertEqual(self._strip(html), html)

    def test_no_op_on_a_stripped_body(self):
        """The pattern is anchored on `<sup>`, which body_text never carries."""
        text = "first did meet with grace; for he found it"
        self.assertEqual(self._strip(text), text)

    def test_is_idempotent(self):
        once = self._strip("<p>grace;<sup>4</sup> and much.<sup></sup></p>")
        self.assertEqual(self._strip(once), once)
        self.assertEqual(once, "<p>grace; and much.</p>")


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
        from library.corrections import BODY_CORRECTIONS, PARAGRAPH_BREAK

        # The FIELD VALUES, not the serialized file: `json.dumps` escapes every
        # `"` as `\"`, so a correction whose text contains a double quote — the
        # straight quotes `things-as-they-are` uses throughout — matched nothing
        # and was reported dead. A false positive on a test whose whole job is
        # to notice a pair that protects nothing.
        corpus = "\n".join(
            value
            for path in list(BOOKS_DIR.glob("*.json")) + list(SERMONS_DIR.glob("*.json"))
            for row in json.loads(path.read_text(encoding="utf-8"))
            for value in (row.get("fields") or {}).values()
            if isinstance(value, str)
        )
        dead = [
            (slug, old)
            for slug, entry in BODY_CORRECTIONS.items()
            # A declared paragraph break has the same two states, spelled with
            # the seam closed up (not yet applied) and split (applied).
            for old, new in (
                *entry.get("replacements", ()),
                *(
                    (f"{tail} {head}", f"{tail}{PARAGRAPH_BREAK}{head}")
                    for tail, head in entry.get("paragraph_breaks", ())
                ),
                # A declared note heading has the same two states, spelled
                # as the anchor it is inserted before (not yet applied — and
                # still present afterwards) and the heading itself (applied).
                # Dead means BOTH are gone: the paragraph this titles was
                # edited or renumbered out from under the entry.
                *entry.get("restored_blocks", ()),
                # A wrapped display line keeps its text, so its head is present
                # either way; dead means the run it names was edited away.
                *((head, f"<{tag}>{head}") for head, tag, *_ in entry.get("wrapped_blocks", ())),
                # A back-matter cut: its first block (not yet applied) and the
                # ending it cuts after (applied). Dead means both are gone.
                *entry.get("back_matter", ()),
            )
            if old not in corpus and new not in corpus
        ]
        self.assertEqual(dead, [], "BODY_CORRECTIONS entries matching nothing in the fixture")

    def test_reformed_pastor_ch04_paragraphing_restored(self):
        """The five paragraphs CCEL ran into the one before them.

        Read off the 1862 scan's first-line indents, not chosen by block length
        — see the `the-reformed-pastor` entry in `corrections.py`. Asserted
        against the SHIPPED fixture because that is what the ratchet measures
        and what a deployed database gets rewritten to. Only the openings and
        the count: that the corrections are a no-op over this file is
        `test_the_fixture_is_clean`'s job, and that the book audits clean is the
        ratchet's — its baseline entry is removed in the same commit.
        """
        import json

        from library.content_fixtures import book_fixture_path

        records = json.loads(
            book_fixture_path("the-reformed-pastor", "en").read_text(encoding="utf-8")
        )
        body = next(
            r["fields"]["body_html"]
            for r in records
            if r["model"] == "library.chapter" and r["fields"]["order"] == 4
        )
        for opening in (
            "<p>Alas! it is the common danger",
            "<p>It is a palpable error of some ministers",
            "<p>Moreover, what skill is necessary to defend",
            "<p>What skill is necessary to deal in private",
            "<p>O brethren! do you not shrink",
        ):
            self.assertIn(opening, body)
        # 24 paragraphs: the scan's 23, plus the one break the stored text
        # carries that the 1862 printing does not.
        self.assertEqual(body.count("<p>"), 24)


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
                # Neither: most are a bare stray to delete, but some stand
                # where a LETTER was lost ("“ruth from truth"), and only a
                # second printing can say which.
                "orphan-open-quote",
                "run-together",
                # Neither. The DETECTION is exact — an empty parenthesis pair
                # is never prose — but the repair is not: only the source can
                # say what the anchor said, and it may be a note letter
                # (`(Note A.)`), a chapter reference (`(ch. 3)`) or a page.
                # `holy-in-christ` ch10 needed the Gutenberg HTML read for the
                # targets AND two archive.org printings compared to settle
                # whether the references were the author's at all.
                "stray-parens",
                "title-case-vs-body",
                # Neither: the scanner can spot that a word LOOKS like two
                # glued together, but only a reader can say where the seam
                # goes — or that there is no seam. Power Through Prayer is the
                # work that first put this class in the corpus, and its one
                # finding is a false positive ("soother", a real word that
                # occurs nowhere else in the library, read as "so" + "other").
                "word-fusion",
                # Neither, and emphatically not mechanical: where a paragraph
                # breaks is a judgement about the prose. The scanner can say a
                # chapter has lost its paragraphing — 4,602 words in two blocks
                # is not a style — but only a reader can put the breaks back.
                "lost-paragraphing",
                # Neither. The DETECTION is exact — a doubled marker carrying
                # the same number, which no correctly extracted footnote has —
                # but the repair is not, because where the note ends is not
                # marked. Only ~39% close on a clean full stop; the rest run
                # "Mr. R. Rowley, of Shrewsbury, upon Acham bridge." or carry a
                # scripture reference mid-note, so a machine cutting at the
                # first period would take half a note or half a sentence.
                "welded-footnote",
            }
        )
        emitted = {label for classes in _corpus().values() for label in classes}
        self.assertEqual(emitted - known, set(), "unclassified finding class(es)")


def _book_bodies(slug: str) -> dict[int, str]:
    """A shipped English book's chapter bodies, by order."""
    from library.content_fixtures import book_fixture_path

    path = book_fixture_path(slug, "en")
    return {r["fields"]["order"]: r["fields"]["body_html"]
            for r in json.loads(path.read_text(encoding="utf-8"))
            if (r.get("fields") or {}).get("body_html")}


class ShelfRepairTests(SimpleTestCase):
    """Shipped rows repaired in place, because shipped books are never re-imported.

    Most are what the two over-matching selectors had already eaten:
    `[class*=pginternal]` (#1573) and `[class*=note i]` (#1574) are both
    qualified now, so no future import loses this text. `the-bruised-reed` is
    the OCR damage its #1943 re-import shipped — one case per class of defect.

    Every case is asserted twice over: the repaired string is in the shipped
    fixture, AND stripping it back out and re-settling puts it back. The second
    half is the one that matters — asserting the fixture alone passes with the
    correction deleted, while the live rows (repaired by `apply_body_corrections`
    on every deploy) would silently revert.
    """

    #: slug -> [(damaged, repaired)] exactly as a reader would see them.
    REPAIRS = {
        "holy-in-christ": [
            ("made in the note to ‘Sixth Day,’ on .</p>",
             "made in the note to ‘Sixth Day,’ on Holiness as Proprietorship.</p>"),
        ],
        "the-life-of-trust": [
            (" of the Lord Jesus. Even about the of this century",
             " of the Lord Jesus. Even about the commencement of this century"),
            ("large piece of ground in the of Bristol",
             "large piece of ground in the neighborhood of Bristol"),
            ("Again, four from among the -school children",
             "Again, four from among the Sunday-school children"),
            ("if one is enabled to God’s own time",
             "if one is enabled to wait God’s own time"),
        ],
        "things-as-they-are": [
            ("one of the old dames seen in . A capital typical face",
             "one of the old dames seen in chapter vi. A capital typical face"),
            ('stuff on the stone is the "Imp" of . <p>Then a Caste meeting',
             'stuff on the stone is the "Imp" of chapter xx. <p>Then a Caste meeting'),
            ('the "rabbits" mentioned in . She saw us',
             'the "rabbits" mentioned in Chapter I. She saw us'),
        ],
        "selected-sermons-edwards": [
            ("for the press (see Introduction, p. ). The manuscript",
             "for the press (see Introduction, p. xxix). The manuscript"),
        ],
        "the-bruised-reed": [
            # a whole scanned line lost, "repaired" into a verbless sentence
            ("let us not fore the cure be wrought,",
             "let us not take off ourselves too soon, nor pull off the plaster "
             "before the cure be wrought,"),
            # a stray opening mark where a letter was
            ("believe “ruth from truth", "believe truth from truth"),
            # a stray closing mark
            ("without making’ a noise", "without making a noise"),
            # misreads landing on a real word
            ("authority derived rot God", "authority derived from God"),
            ("the Sear of the Lord", "the fear of the Lord"),
            # a scripture reference
            ("Rom. vii. 34, saith", "Rom. vii. 24, saith"),
            # the entry's own earlier modernisation, undone
            ("an affectionate entreaty", "an affectionate intreaty"),
        ],
    }

    #: `holy-in-christ`'s note headings, deleted whole rather than emptied.
    HEADINGS = (
        ("<h3>NOTE.</h3>", 5),
        ("<h3> NOTE A.</h3> <h4>Holiness as Proprietorship.</h4>", 33),
        ("<h3> NOTE B.</h3> <h4>On the Word for Holiness.</h4>", 33),
        ("<h3> NOTE C.</h3> <h4>The Holiness of God.</h4>", 33),
        ("<h3> NOTE D.</h3>", 33),
        ("<h3> NOTE E.</h3>", 33),
        ("<h3> NOTE F.</h3> <h4>Note from Bengel on Rom. i. 4.</h4>", 33),
        ("<h3> NOTE G.</h3> <h4>‘Freed’ and ‘Possessed’—The Twofold Result of "
         "Redemption.</h4>", 33),
    )

    def test_every_repair_is_in_the_shipped_fixture_exactly_once(self):
        for slug, pairs in self.REPAIRS.items():
            joined = "\n".join(_book_bodies(slug).values())
            for damaged, repaired in pairs:
                with self.subTest(slug=slug, repaired=repaired[:40]):
                    self.assertEqual(joined.count(repaired), 1)
                    self.assertNotIn(damaged, joined)

    def test_the_corrections_are_what_repair_them(self):
        """Damage each site again; `apply_body_corrections` must undo it."""
        for slug, pairs in self.REPAIRS.items():
            bodies = _book_bodies(slug)
            for damaged, repaired in pairs:
                order = next(o for o, b in bodies.items() if repaired in b)
                with self.subTest(slug=slug, chapter=order):
                    broken = bodies[order].replace(repaired, damaged, 1)
                    self.assertNotEqual(broken, bodies[order])
                    self.assertEqual(
                        corrections.settled_chapter_body(slug, order, broken),
                        bodies[order],
                    )

    def test_every_note_heading_is_restored_to_its_own_chapter(self):
        """`restore_dropped_blocks` runs over EVERY chapter of the book.

        So an anchor that also matched another chapter would insert a heading
        into the wrong one. Both halves are pinned: the heading is in the
        chapter it belongs to, and in no other.
        """
        bodies = _book_bodies("holy-in-christ")
        for heading, order in self.HEADINGS:
            with self.subTest(heading=heading[:28]):
                carriers = [o for o, b in bodies.items() if heading in b]
                self.assertEqual(carriers, [order])

    def test_a_stripped_note_heading_comes_back(self):
        bodies = _book_bodies("holy-in-christ")
        for heading, order in self.HEADINGS:
            with self.subTest(heading=heading[:28]):
                broken = bodies[order].replace(heading + " ", "", 1)
                self.assertNotEqual(broken, bodies[order])
                self.assertEqual(
                    corrections.settled_chapter_body("holy-in-christ", order, broken),
                    bodies[order],
                )


class EdwardsSermonTextTests(SimpleTestCase):
    """Four sermons shipped with no scripture text at all.

    Edwards opens each sermon with the verse he expounds, and this edition marks
    it `<p class="note">` — which `[class*=note i]`, written for CCEL's footnote
    apparatus, matched and decomposed whole. ch2/3/4/8 opened mid-argument
    ("Those Christians to whom the apostle directed this epistle…") with nothing
    saying which apostle or which epistle.

    The book is its own witness that a text belongs there: ch5/6/7 still carry
    theirs, because this edition marks THOSE `<p class="center">` — not a drop
    selector, so they were never touched. This asserts both halves — the four
    restored, the three untouched — and, separately, that the CORRECTION is what
    puts the text back. Asserting only the settled fixture would pass with the
    correction deleted, while the live rows (repaired by `apply_body_corrections`
    on every deploy, since `seed_books` never rewrites an existing body) went
    quietly back to opening mid-argument.
    """

    REPAIRED = {
        2: "1 Cor. i. 29-31.—That no flesh should glory in his presence.",
        3: "Matt. xvi.—And Jesus answered and said unto him, Blessed art thou",
        4: "Ruth i. 16.—And Ruth said, Intreat me not to leave thee",
        8: "2 Cor. i. 14.—As also you have acknowledged us in part",
    }
    # Never damaged, so never repaired: the source set these in a plain <p>.
    UNTOUCHED = {
        5: "John xiv. 2.—In my Father’s house are many mansions.",
        6: "Deuteronomy xxxii. 35.—Their foot shall slide in due time.",
        7: "Ezek. xix. 12.—Her strong rods were broken and withered.",
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = (Path(__file__).resolve().parent / "fixtures" / "content" /
                "books" / "selected-sermons-edwards.en.json")
        cls.bodies = {
            (r["fields"].get("order")): r["fields"]["body_html"]
            for r in json.loads(path.read_text())
            if (r.get("fields") or {}).get("body_html")
        }

    def test_every_sermon_opens_with_its_text(self):
        """The FIRST block, not merely somewhere in the body.

        Block 0 is what the quote anchors in `quote_seed` are counted from, so
        "opens with" has to mean the opening — `assertIn` would pass on a text
        that had drifted down the chapter and taken every anchor with it. This
        also subsumes the old separate check that the repaired chapters no
        longer start on the `<p><br/>` spacer the deleted text left behind.
        """
        for order, opening in {**self.REPAIRED, **self.UNTOUCHED}.items():
            with self.subTest(chapter=order):
                self.assertTrue(
                    self.bodies[order].startswith(f"<p>{opening}"),
                    f"ch{order} does not open with its text: "
                    f"{self.bodies[order][:80]!r}",
                )

    def test_the_correction_is_what_restores_the_text(self):
        """Strip the text back out and the correction must put it back.

        The other tests read the settled fixture, which already contains the
        text — they pass with the correction deleted. Production does not: those
        rows are damaged and `apply_body_corrections` is the only thing that
        repairs them, so this is the test that fails if the entry is dropped or
        mis-keyed.
        """
        for order, opening in self.REPAIRED.items():
            with self.subTest(chapter=order):
                settled = self.bodies[order]
                block_end = settled.index("</p>") + len("</p> ")
                damaged = settled[block_end:]
                self.assertFalse(damaged.startswith(f"<p>{opening}"))
                self.assertEqual(
                    corrections.settled_chapter_body(
                        "selected-sermons-edwards", order, damaged),
                    settled,
                )

    def test_the_correction_is_a_no_op_on_the_settled_fixture(self):
        """The fixture ships settled, so the guard must recognise its own work.

        If it did not, every deploy would insert a second copy of the text —
        which is exactly why this is `restored_blocks` and not a `replacements`
        pair.
        """
        for order, body in self.bodies.items():
            with self.subTest(chapter=order):
                self.assertEqual(
                    corrections.settled_chapter_body(
                        "selected-sermons-edwards", order, body),
                    body,
                )


class RibbandOfBlueTitleLineTests(SimpleTestCase):
    """`a-ribband-of-blue` lost the display line that ends a sentence.

    Gutenberg #23438 runs "…to introduce the wearing of the" straight into a
    centred `<div class="c1">"RIBBAND OF BLUE."</div>`, which the sermon
    importer never collected. The fr and sw editions were translated from the
    damaged English, so all three carry the repair, at the same block index.
    """

    RESTORED = {
        "en": '<p>"RIBBAND OF BLUE."</p>',
        "fr": "<p>« CORDON BLEU ».</p>",
        "sw": '<p>"UZI WA RANGI YA SAMAWI."</p>',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sermons = Path(__file__).resolve().parent / "fixtures" / "content" / "sermons"
        cls.bodies = {
            lang: json.loads(
                (sermons / f"a-ribband-of-blue.{lang}.json").read_text()
            )[0]["fields"]["body_html"]
            for lang in cls.RESTORED
        }

    def test_the_line_follows_the_truncated_sentence_in_every_edition(self):
        for lang, block in self.RESTORED.items():
            with self.subTest(language=lang):
                blocks = re.findall(r"<p>.*?</p>", self.bodies[lang])
                self.assertEqual(blocks.index(block), 10)

    def test_the_correction_is_what_restores_the_line(self):
        """Strip it back out and the correction must put it back.

        Production rows are damaged; `apply_body_corrections` on deploy is what
        repairs them, so this fails if the entry is dropped or mis-keyed.
        """
        for lang, block in self.RESTORED.items():
            with self.subTest(language=lang):
                settled = self.bodies[lang]
                damaged = settled.replace(f"{block} ", "", 1)
                self.assertNotIn(block, damaged)
                self.assertEqual(
                    corrections.settled_sermon_body("a-ribband-of-blue", damaged),
                    settled,
                )
                self.assertEqual(
                    corrections.settled_sermon_body("a-ribband-of-blue", settled),
                    settled,
                )


class RibbandOfBlueDisplayLineTests(SimpleTestCase):
    """The rest of Gutenberg #23438 — see that entry in `corrections.py`.

    Asserted per edition: a translation pair that silently stops matching
    leaves that language's prod rows damaged while the English passes.
    """

    SLUGS = {
        "blessed-prosperity": 10,
        "blessed-adversity": 9,
        "a-full-reward": 1,
        "self-denial-versus-self-assertion": 1,
        "all-sufficiency": 1,
        "under-the-shepherds-care": 1,
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.content_fixtures import SERMONS_DIR

        cls.editions = {
            (slug, path.stem.rsplit(".", 1)[1]): json.loads(path.read_text())[0]["fields"]["body_html"]
            for slug in cls.SLUGS
            for path in sorted(SERMONS_DIR.glob(f"{slug}.*.json"))
        }

    @staticmethod
    def _blocks(slug):
        return [block for _, block in corrections.BODY_CORRECTIONS[slug]["restored_blocks"]]

    def test_every_edition_carries_every_line(self):
        for (slug, lang), body in self.editions.items():
            with self.subTest(slug=slug, language=lang):
                self.assertEqual(sum(b in body for b in self._blocks(slug)), self.SLUGS[slug])

    def test_the_correction_is_what_restores_them(self):
        """Strip them all back out and the correction must put every one back."""
        for (slug, lang), settled in self.editions.items():
            with self.subTest(slug=slug, language=lang):
                damaged = settled
                for block in self._blocks(slug):
                    damaged = damaged.replace(f"{block} ", "", 1)
                self.assertNotIn("<h3>", damaged)
                self.assertEqual(corrections.settled_sermon_body(slug, damaged), settled)
                self.assertEqual(corrections.settled_sermon_body(slug, settled), settled)


class BrainerdDisplayLineTests(SimpleTestCase):
    """Gutenberg #65066's dropped display lines — see that entry in `corrections.py`.

    Asserted per edition, like the #23438 repair above: a Swahili pair that
    silently stops matching would leave the sw rows damaged while the English
    passes. The entry lists the 24 English pairs, then the 24 Swahili ones.
    """

    SLUG = "life-and-diary-of-david-brainerd"
    LINES_PER_CHAPTER = {2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 1, 8: 8, 9: 5, 11: 1, 12: 1}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.content_fixtures import book_fixture_path

        pairs = corrections.BODY_CORRECTIONS[cls.SLUG]["restored_blocks"]
        cls.blocks = {"en": [b for _, b in pairs[:24]], "sw": [b for _, b in pairs[24:]]}
        cls.editions = {
            lang: {
                row["fields"]["order"]: row["fields"]["body_html"]
                for row in json.loads(book_fixture_path(cls.SLUG, lang).read_text())
                if "body_html" in row["fields"]
            }
            for lang in cls.blocks
        }

    def test_every_edition_carries_every_line(self):
        self.assertEqual(sum(self.LINES_PER_CHAPTER.values()), 24)
        for lang, chapters in self.editions.items():
            self.assertEqual(len(self.blocks[lang]), 24)
            for order, body in chapters.items():
                with self.subTest(language=lang, chapter=order):
                    self.assertEqual(
                        sum(b in body for b in self.blocks[lang]),
                        self.LINES_PER_CHAPTER.get(order, 0),
                    )

    def test_the_correction_is_what_restores_them(self):
        """Strip them all back out and the correction must put every one back."""
        for lang, chapters in self.editions.items():
            for order, settled in chapters.items():
                with self.subTest(language=lang, chapter=order):
                    damaged = settled
                    for block in self.blocks[lang]:
                        damaged = damaged.replace(f"{block} ", "", 1)
                    self.assertFalse([b for b in self.blocks[lang] if b in damaged])
                    self.assertEqual(corrections.settled_chapter_body(self.SLUG, order, damaged), settled)
                    self.assertEqual(corrections.settled_chapter_body(self.SLUG, order, settled), settled)


class UnfailingSpringsDisplayLineTests(SimpleTestCase):
    """Gutenberg #57109's Rev. 22:17 display line — see that entry in
    `corrections.py`. Asserted per edition, for the same reason as above."""

    SLUG = "unfailing-springs"
    LANGUAGES = {"ar", "en", "es", "fr", "hi", "lg", "pt", "sw", "uk"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.content_fixtures import SERMONS_DIR

        cls.editions = {
            path.stem.rsplit(".", 1)[1]: json.loads(path.read_text())[0]["fields"]["body_html"]
            for path in sorted(SERMONS_DIR.glob(f"{cls.SLUG}.*.json"))
        }
        cls.blocks = [block for _, block in corrections.BODY_CORRECTIONS[cls.SLUG]["restored_blocks"]]

    def test_every_edition_is_covered(self):
        self.assertEqual(set(self.editions), self.LANGUAGES)
        self.assertEqual(len(self.blocks), len(self.LANGUAGES))

    def test_the_line_sits_under_the_address_heading(self):
        for lang, body in self.editions.items():
            with self.subTest(language=lang):
                [block] = [b for b in self.blocks if b in body]
                self.assertIn(f"</h2>{block} <p>", body)

    def test_the_correction_is_what_restores_it(self):
        """Strip it back out and the correction must put it back."""
        for lang, settled in self.editions.items():
            with self.subTest(language=lang):
                [block] = [b for b in self.blocks if b in settled]
                damaged = settled.replace(f"{block} ", "", 1)
                self.assertNotIn("22:17)", damaged)
                self.assertEqual(corrections.settled_sermon_body(self.SLUG, damaged), settled)
                self.assertEqual(corrections.settled_sermon_body(self.SLUG, settled), settled)


class RealityOfPrayerVerseTests(SimpleTestCase):
    """The two poems `reality-of-prayer` lost at import — see its
    `restored_blocks` in `corrections.py`.

    Asserted per edition, and in the chapter and block position the source
    sets them: a translation pair that silently stops matching leaves that
    language's prod rows damaged while the English passes.
    """

    SLUG = "reality-of-prayer"
    # chapter order -> 0-indexed block the poem occupies, in every edition
    POSITIONS = {5: 15, 16: 21}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from library.content_fixtures import BOOKS_DIR

        cls.editions = {
            path.stem.rsplit(".", 1)[1]: {
                row["fields"]["order"]: row["fields"]["body_html"]
                for row in json.loads(path.read_text())
                if row["model"] == "library.chapter"
            }
            for path in sorted(BOOKS_DIR.glob(f"{cls.SLUG}.*.json"))
        }

    def _blocks(self):
        return [block for _, block in corrections.BODY_CORRECTIONS[self.SLUG]["restored_blocks"]]

    def test_each_edition_carries_both_poems_in_place(self):
        self.assertEqual(set(self.editions), {"en", "es"})
        for lang, chapters in self.editions.items():
            for order, index in self.POSITIONS.items():
                with self.subTest(language=lang, chapter=order):
                    blocks = [
                        m.group(0)
                        for m in re.finditer(r"<(p|blockquote|h\d)>.*?</\1>", chapters[order])
                    ]
                    self.assertIn(blocks[index], self._blocks())
                    self.assertEqual(chapters[order].count("<blockquote>"), 1)

    def test_the_correction_is_what_restores_them(self):
        """Strip them back out and the correction must put each one back."""
        for lang, chapters in self.editions.items():
            for order in self.POSITIONS:
                with self.subTest(language=lang, chapter=order):
                    settled = chapters[order]
                    damaged = settled
                    for block in self._blocks():
                        damaged = damaged.replace(f"{block} ", "", 1)
                    self.assertNotIn("<blockquote>", damaged)
                    self.assertEqual(
                        corrections.settled_chapter_body(self.SLUG, order, damaged), settled)
                    self.assertEqual(
                        corrections.settled_chapter_body(self.SLUG, order, settled), settled)


class DroppedBlockRestorationTests(SimpleTestCase):
    """`restore_dropped_blocks` — the sanitizer's OTHER victim.

    `[class*=pginternal]` was an UNQUALIFIED drop selector, so `_clean`
    decomposed a Gutenberg anchor whole rather than unwrapping it to its text. A
    heading whose only child is that anchor was emptied, and the empty-block
    regex then deleted the heading. `ministry-of-intercession` ch18 lost all six
    of its note headings that way, in the same import that left five bare `()`
    in the chapters pointing at them.

    It carries a keep-predicate now (`sanitize.KEEP_PREDICATES`), so no future
    import loses a heading this way; these rows are the ones already shipped,
    and they are never re-imported.
    """

    HEADINGS = (("<p>Just this day", "<h4>NOTE A, Chap. VI. p. 73</h4>"),)

    def _restore(self, html):
        return corrections.restore_dropped_blocks(html, self.HEADINGS)

    def test_inserts_the_heading_before_its_block(self):
        self.assertEqual(
            self._restore("<p>Just this day I met her.</p>"),
            "<h4>NOTE A, Chap. VI. p. 73</h4> <p>Just this day I met her.</p>",
        )

    def test_is_idempotent(self):
        """The property a `replacements` pair could not have here.

        A pure insertion's `old` is a substring of its `new`, so as a pair this
        would add a second heading on every run — and the deploy applies
        corrections on top of already-corrected rows, forever.
        """
        once = self._restore("<p>Just this day I met her.</p>")
        self.assertEqual(self._restore(once), once)

    def test_disarms_itself_once_the_sanitizer_stops_eating_the_heading(self):
        """The reason the heading is declared with the tag the SOURCE used.

        `[class*=pginternal]` is what deleted these; now that the selector is
        fixed, a re-import brings Gutenberg's own `<h4>` back. The guard then
        recognises it and this correction quietly becomes a no-op. Declared as
        `<h3>` it would not match, and a re-imported English edition would carry
        BOTH headings — failing `tests_translation_markup` against a Hindi
        edition that, being a translation rather than a re-import, gained
        nothing.
        """
        reimported = "<h4>NOTE A, Chap. VI. p. 73</h4> <p>Just this day I met her.</p>"
        self.assertEqual(self._restore(reimported), reimported)

    def test_no_op_when_the_anchor_is_absent(self):
        """Every entry is applied to every chapter of its slug, in every
        language, so five of any six anchors miss on any given body."""
        other = "<p>A different chapter entirely.</p>"
        self.assertEqual(self._restore(other), other)

    def test_no_op_on_a_stripped_body(self):
        """Anchors carry their `<p>`, which `body_text` never holds — that is
        what keeps block tags out of the tagless field."""
        text = "Just this day I met her."
        self.assertEqual(self._restore(text), text)

    def test_inserts_only_the_first_occurrence(self):
        """A heading titles ONE block. If an anchor were ever ambiguous the
        repair must not scatter copies through the chapter."""
        doubled = "<p>Just this day I met her.</p> <p>Just this day I met her.</p>"
        self.assertEqual(self._restore(doubled).count("<h4>"), 1)


class LooseBlockWrapTests(SimpleTestCase):
    """`wrap_loose_blocks` — a display line the sanitizer UNWRAPPED.

    The sibling of `restore_dropped_blocks`: there the block was deleted, here
    only its tags were, so the text shipped as a loose run between blocks.
    """

    def _wrap(self, html, *blocks):
        return corrections.wrap_loose_blocks(html, blocks)

    def test_wraps_the_run_up_to_the_next_block(self):
        self.assertEqual(
            self._wrap("FIRST OF ALL, let us go. <p>We will enter.</p>", ("FIRST OF ALL", "p")),
            "<p>FIRST OF ALL, let us go.</p> <p>We will enter.</p>",
        )

    def test_is_idempotent_and_disarms_on_a_reimport(self):
        """A re-import emits the block itself; the guard sees the head inside
        a block and leaves it, as it does the settled form."""
        once = self._wrap("FIRST OF ALL, let us go. <p>We will.</p>", ("FIRST OF ALL", "p"))
        self.assertEqual(self._wrap(once, ("FIRST OF ALL", "p")), once)

    def test_a_heading_holds_plain_text_and_edge_breaks_go(self):
        """As `display_line` writes them, so the guard recognises a re-import."""
        self.assertEqual(
            self._wrap(
                "<p>should be</p> THIS IS JESUS OF NAZARETH<br/> THE KING OF THE JEWS.<br/> <p>It was</p>",
                ("THIS IS JESUS", "h3"),
            ),
            "<p>should be</p> <h3>THIS IS JESUS OF NAZARETH THE KING OF THE JEWS.</h3> <p>It was</p>",
        )

    def test_two_lines_flattened_into_one_run_are_split_at_the_second_head(self):
        self.assertEqual(
            self._wrap(
                "<p>We give it here.</p> MARY'S SONG My soul beholds<br/> the Lord.<br/> <p>For three</p>",
                ("MARY'S SONG", "h3"),
                ("My soul beholds", "p"),
            ),
            "<p>We give it here.</p> <h3>MARY'S SONG</h3> <p>My soul beholds<br/> the Lord.</p> <p>For three</p>",
        )

    def test_a_tail_leaves_a_caption_loose(self):
        """An illustration's caption is not a display line: it stays as it was."""
        self.assertEqual(
            self._wrap(
                "AFTER SOME months, for baptizing the people. The Jordan. <p>Bethabara</p>",
                ("AFTER SOME months", "p", "for baptizing the people."),
            ),
            "<p>AFTER SOME months, for baptizing the people.</p> The Jordan. <p>Bethabara</p>",
        )

    def test_a_head_inside_a_block_is_left_alone(self):
        body = "<p>He said FIRST OF ALL, let us go.</p>"
        self.assertEqual(self._wrap(body, ("FIRST OF ALL", "p")), body)

    def test_no_op_on_a_tagless_body(self):
        """A head is bare text, so it WOULD match `body_text`; tags must never
        reach that field."""
        text = "FIRST OF ALL, let us go. We will enter."
        self.assertEqual(self._wrap(text, ("FIRST OF ALL", "p")), text)


class HurlbutDisplayLineTests(SimpleTestCase):
    """`hurlbuts-life-of-christ`: 118 display lines shipped as loose text.

    See its `wrapped_blocks` entry in `corrections.py`. Asserted against the
    SHIPPED fixture, and — the part that matters for a future re-import —
    against what the importer emits from the edition's own markup.
    """

    SLUG = "hurlbuts-life-of-christ"

    def _chapters(self):
        import json

        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, "en").read_text(encoding="utf-8"))
        return {
            r["fields"]["title"]: r["fields"]["body_html"]
            for r in rows
            if r["model"] == "library.chapter"
        }

    def _entries(self):
        return corrections.BODY_CORRECTIONS[self.SLUG]["wrapped_blocks"]

    def test_every_line_ships_in_its_block(self):
        corpus = "".join(self._chapters().values())
        for head, tag, *_ in self._entries():
            with self.subTest(head=head):
                self.assertTrue(f"<{tag}>{head}" in corpus, head)

    def test_the_correction_wraps_the_flattened_rows(self):
        """Strip every wrapped line back to loose text; the correction must
        restore the shipped body exactly. (Asserting the fixture alone passes
        with the entry deleted, while the live rows stay flat.)"""
        heads = [head for head, *_ in self._entries()]
        for title, body in self._chapters().items():
            flat = body
            for head in heads:
                flat = re.sub(
                    rf"<(p|h3)>({re.escape(head)}.*?)</\1>", r"\2", flat, count=1, flags=re.S
                )
            if flat == body:
                continue
            with self.subTest(chapter=title):
                self.assertEqual(corrections.settled_chapter_body(self.SLUG, None, flat), body)

    # PG 40460's own markup, cut down to whole blocks: a drop-cap opening paragraph, a centred
    # heading over a poem set as one div, an opening paragraph that runs into
    # an illustration, and a heading set on two lines.
    PAGE = """<html><body>
<h2>A Young Girl's Journey</h2>
<p>We give it here.</p>
<div class="center">MARY'S SONG</div>
<div class="poem">
My soul beholds the greatness of the Lord,<br>
And my spirit hath rejoiced in God my Saviour.<br>
For he hath looked upon his servant in my lowly state;<br>
And from this time people in all ages shall call me blessed.<br>
<br>
For he that is mighty hath done to me great things;<br>
And holy is his name.<br>
And his mercy is from age to age<br>
On those who fear him.<br>
<br>
He hath showed strength with his arm;<br>
He hath scattered the proud in the vain thoughts of their heart.<br>
He hath put down princes from their thrones,<br>
And hath lifted up those of humble state.<br>
<br>
The hungry he hath filled with good things;<br>
And the rich he hath sent empty away.<br>
He hath given help to Israel his servant<br>
That he might remember mercy<br>
As he spoke to our fathers,<br>
Toward Abraham and his children forever.<br>
</div>
<p>For three months Mary stayed with Elizabeth.</p>
<h2>The Carpenter Leaves His Shop</h2>
<div class="chaptertitle">CHAPTER 15</div>
<div class="cap">AFTER SOME months the news was brought to
Nazareth that John the Baptist had come up the
river Jordan and was now preaching at a place
about twelve miles south of the Sea of Galilee. The
place where John was preaching had two names. It
was called "Bethany beyond Jordan," there being
another Bethany quite near Jerusalem; and it was also
called "Bethabara," a word which means "the place
where one can walk across the river"; for there the river
Jordan was so shallow that people waded across it.
John had chosen this place because the sloping shore
beside the river was fitted for the crowds to listen to
his preaching, and the shallow water was near at hand
for baptizing the people.</div>
<div class="figright" style="width: 300px;" role="figure">
<img alt="painting" height="285" src="images/illus-116.jpg" width="300">
<span class="caption">The Jordan. At the supposed place of
Christ's baptism.</span>
</div>
<p>Bethabara or Bethany was about twenty-five miles from Nazareth.</p>
<h2>Jesus on the Cross</h2>
<div class="chaptertitle">CHAPTER 96</div>
<div class="cap">IT WAS the custom of the Romans when they put to
death any man upon the cross, to place on the cross
above his head a writing, telling what the man's
crime was. Pilate commanded that the writing above the
head of Jesus should be</div>
<div class="center">
THIS IS JESUS OF NAZARETH<br>
THE KING OF THE JEWS.<br>
</div>
<p>It was written in the language of three different peoples.</p>
</body></html>"""

    def test_the_importer_emits_the_blocks_the_correction_wraps(self):
        """The guard is a string match, so the importer and the correction must
        agree byte for byte, or a re-import carries a line twice."""
        from library.ingest import soup
        from library.management.commands.import_gutenberg import (
            content_root,
            split_by_heading,
        )

        chapters = self._chapters()
        emitted = 0
        for title, body in split_by_heading(content_root(self.PAGE), "h2"):
            for block in soup(body).body.find_all(["p", "h3"], recursive=False):
                block = str(block)
                if not any(block.startswith(f"<{tag}>{head}") for head, tag, *_ in self._entries()):
                    continue  # prose the importer always kept
                with self.subTest(chapter=title, block=block[:40]):
                    self.assertTrue(block in chapters[title], block)
                    emitted += 1
        self.assertEqual(emitted, 5)


class RetrospectDisplayLineTests(SimpleTestCase):
    """`a-retrospect`: 47 display lines shipped as loose text, in en and es.

    See its `wrapped_blocks` entry in `corrections.py`: the 47 English entries,
    then the 47 Spanish ones (a 48th, ch12's MIDI transcriber's note, is cut
    instead — a `replacements` pair). Asserted per edition against the SHIPPED fixture,
    and the English against what the importer emits from PG 26744's own markup.
    """

    SLUG = "a-retrospect"
    LINES = 47

    def _chapters(self, lang):
        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, lang).read_text(encoding="utf-8"))
        return {
            r["fields"]["title"]: r["fields"]["body_html"]
            for r in rows
            if r["model"] == "library.chapter"
        }

    def _entries(self, lang):
        entries = corrections.BODY_CORRECTIONS[self.SLUG]["wrapped_blocks"]
        self.assertEqual(len(entries), 2 * self.LINES)
        return entries[: self.LINES] if lang == "en" else entries[self.LINES :]

    def test_every_line_ships_in_its_block(self):
        for lang in ("en", "es"):
            corpus = "".join(self._chapters(lang).values())
            for head, tag, *_ in self._entries(lang):
                with self.subTest(language=lang, head=head):
                    self.assertEqual(corpus.count(f"<{tag}>{head}"), 1)

    def test_the_correction_wraps_the_flattened_rows(self):
        """Strip every wrapped line back to loose text; the correction must
        restore the shipped body exactly."""
        for lang in ("en", "es"):
            heads = [head for head, *_ in self._entries(lang)]
            for title, body in self._chapters(lang).items():
                flat = body
                for head in heads:
                    flat = re.sub(
                        rf"<p>({re.escape(head)}.*?)</p>", r"\1", flat, count=1, flags=re.S
                    )
                if flat == body:
                    continue
                with self.subTest(language=lang, chapter=title):
                    self.assertEqual(corrections.settled_chapter_body(self.SLUG, None, flat), body)

    # PG 26744's own markup, whole blocks, prose cut short: a chapter opener set
    # as a drop-cap div, a journal dateline in a right-set div, and two poems
    # each followed by the prose line the edition sets as a div of its own.
    PAGE = """<html><body>
<h2>CHAPTER X</h2>
<h3>FIRST EVANGELISTIC EFFORTS</h3>
<div class="cap">A JOURNEY taken in the spring of 1855 with the
Rev. J. S. Burden of the Church Missionary Society
(now the Bishop of Victoria, Hong-kong) was attended with
some serious dangers.</div>
<p>From thence we went on to T'ung-chau.</p>
<div class="right">
<i>Thursday, April 26th, 1855.</i><br>
</div>
<p>After breakfast we commended ourselves to the care of
our Heavenly <span class="smcap">Father</span>.</p>
<p>That verse—</p>
<div class="poem">
"The perils of the sea, the perils of the land,<br>
Should not dishearten thee: thy <span class="smcap">Lord</span> is nigh at hand.<br>
But should thy courage fail, when tried and sore oppressed,<br>
His promise shall avail, and set thy soul at rest."<br>
</div>
<div class="unindent">seemed particularly appropriate to our circumstances, and
was very comforting to me.</div>
<p>On our way we passed through one small town.</p>
<h2>CHAPTER XV</h2>
<h3>SETTLEMENT IN NINGPO</h3>
<p>How glad one is now, not only to know, with dear Miss Havergal,
that——</p>
<div class="poem">
"They who trust Him wholly<br>
<span style="margin-left: 2em;">Find Him wholly true,"</span><br>
</div>
<div class="unindent">but also that when we fail to trust fully He still remains
unchangingly faithful. He <i>is</i> wholly true whether
we trust or not. "If we believe not, He abideth faithful;
He cannot deny Himself." But oh, how we dishonour
our <span class="smcap">Lord</span> whenever we fail to trust Him, and what peace,
blessing, and triumph we lose in thus sinning against the
Faithful One! May we never again presume in anything
to doubt Him!</div>
<p>The year 1857 was a troublous time.</p>
</body></html>"""

    def test_the_importer_emits_the_blocks_the_correction_wraps(self):
        """The guard is a string match, so the importer and the correction must
        agree byte for byte — here once the fixture's curled quotation marks
        are folded back to the edition's straight ones."""
        from library.ingest import soup
        from library.management.commands.import_gutenberg import (
            content_root,
            split_by_heading,
        )

        straight = str.maketrans("“”‘’", "\"\"''")
        chapters = {t: b.translate(straight) for t, b in self._chapters("en").items()}
        heads = [head.translate(straight) for head, *_ in self._entries("en")]
        emitted = 0
        for title, body in split_by_heading(content_root(self.PAGE), "h2"):
            for block in soup(body).body.find_all("p", recursive=False):
                block = str(block)
                if not any(block.startswith(f"<p>{head}") for head in heads):
                    continue  # prose the importer always kept
                with self.subTest(chapter=title, block=block[:40]):
                    self.assertIn(block, chapters[title])
                    emitted += 1
        self.assertEqual(emitted, 6)


class BackMatterTests(SimpleTestCase):
    """`strip_back_matter` — the publisher's and transcriber's pages after the end.

    Gutenberg texts fold the back of the printed book into the last chapter's
    section: a colophon and a priced catalogue, a transcriber's errata note. It
    shipped, and a translator renders what is there, so it reached the
    translations too.
    """

    SEAMS = (("prevailing prayer.</p>", "<p><i>Printed in the United States of America</i></p>"),)
    ENDING = "<p>by earnest, definite, prevailing prayer.</p>"
    TAIL = "<p><i>Printed in the United States of America</i></p><p><i>R. A. TORREY</i></p>"

    def _strip(self, html):
        return corrections.strip_back_matter(html, self.SEAMS)

    def test_cuts_everything_after_the_ending(self):
        self.assertEqual(self._strip(self.ENDING + self.TAIL), self.ENDING)

    def test_tolerates_the_block_separator(self):
        self.assertEqual(self._strip(f"{self.ENDING} \n{self.TAIL}"), self.ENDING)

    def test_is_idempotent(self):
        once = self._strip(self.ENDING + self.TAIL)
        self.assertEqual(self._strip(once), once)

    def test_the_ending_alone_is_not_a_seam(self):
        """Every entry runs against every chapter of its slug: an ending phrase
        that recurs mid-book must not truncate it."""
        body = self.ENDING + "<p>The next paragraph.</p>"
        self.assertEqual(self._strip(body), body)

    def test_the_first_block_alone_is_not_a_seam(self):
        """Nor may a colophon quoted somewhere else cut the book there."""
        body = "<p>Earlier.</p>" + self.TAIL
        self.assertEqual(self._strip(body), body)

    def test_no_op_on_a_stripped_body(self):
        text = "by earnest, definite, prevailing prayer. Printed in the United States of America"
        self.assertEqual(self._strip(text), text)


class ShippedBackMatterTests(SimpleTestCase):
    """Every declared `back_matter` seam, against every edition of its work.

    Driven by the declarations, so a new entry is covered without a new test.
    """

    def test_each_edition_ships_cut_and_the_correction_is_what_cuts_it(self):
        """The settled fixture must end on a declared ending — a translation that
        carried the back matter with no seam of its own fails here — and putting
        the back matter back must be cut again: the fixture alone passes with
        the entry deleted, while production rows still carry the tail."""
        from library.content_fixtures import BOOKS_DIR

        declared = {
            slug: entry["back_matter"]
            for slug, entry in corrections.BODY_CORRECTIONS.items()
            if entry.get("back_matter")
        }
        self.assertTrue(declared)
        for slug, seams in declared.items():
            for path in sorted(BOOKS_DIR.glob(f"{slug}.*.json")):
                last = max(
                    (row["fields"] for row in json.loads(path.read_text(encoding="utf-8"))
                     if row["model"] == "library.chapter"),
                    key=lambda f: f["order"],
                )
                settled = last["body_html"]
                with self.subTest(fixture=path.name):
                    seam = next(((e, f) for e, f in seams if settled.endswith(e)), None)
                    self.assertIsNotNone(seam, f"ch{last['order']} does not end on a declared ending")
                    damaged = f"{settled}{seam[1]}<p>The next advertised title.</p>"
                    for body in (damaged, settled):
                        self.assertEqual(
                            corrections.settled_chapter_body(slug, last["order"], body), settled
                        )


class BruisedReedRepairTests(SimpleTestCase):
    """What only `the-bruised-reed` needs pinning; its string repairs are in
    `ShelfRepairTests.REPAIRS` with the rest of the shelf's."""

    SLUG = "the-bruised-reed"

    def test_a_reimport_of_the_raw_scan_reads_the_same(self):
        """The raw-scan pair for the lost line now writes the whole sentence,
        so a re-import and the repaired live row agree."""
        raw = "<p>Therefore let us not fore the cure be erowiglt but keep</p>"
        settled = corrections.settled_chapter_body(self.SLUG, 4, raw)
        self.assertIn("nor pull off the plaster before the cure be wrought, but", settled)

    def test_no_opening_quote_mark_survives(self):
        """This edition sets no quotation marks, so every one was scan damage."""
        for order, body in _book_bodies(self.SLUG).items():
            with self.subTest(chapter=order):
                self.assertNotIn("‘", body)
                self.assertNotIn("“", body)

    def test_every_chapter_carries_its_whole_title(self):
        """Grosart's scan merged the last two chapters, so the title list
        stopped at 27 and ch28 shipped cut off mid-phrase."""
        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, "en").read_text(encoding="utf-8"))
        titles = {r["fields"]["order"]: r["fields"]["title"]
                  for r in rows if r["model"] == "library.chapter"}
        self.assertEqual(titles, corrections.chapter_title_overrides(self.SLUG))
        self.assertEqual(len(titles), 28)


class IntercessionDisplayLineTests(SimpleTestCase):
    """`ministry-of-intercession`: the opening poem's signature, in all six
    editions. See its `wrapped_blocks` entry in `corrections.py`."""

    SLUG = "ministry-of-intercession"
    HEADS = {
        "en": "F. R. Havergal.",
        "es": "F. R. Havergal.",
        "fr": "F. R. Havergal.",
        "hi": "एफ़. आर. हैवरगल।",
        "pt": "F. R. Havergal.",
        "sw": "F. R. Havergal.",
    }

    def _opening(self, lang):
        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, lang).read_text(encoding="utf-8"))
        return next(
            r["fields"]["body_html"]
            for r in rows
            if r["model"] == "library.chapter" and r["fields"]["order"] == 1
        )

    def test_every_edition_ships_the_line_in_its_block(self):
        for lang, head in self.HEADS.items():
            with self.subTest(language=lang):
                self.assertIn(f"<p>{head}</p>", self._opening(lang))

    def test_the_correction_wraps_the_flattened_rows(self):
        for lang, head in self.HEADS.items():
            body = self._opening(lang)
            with self.subTest(language=lang):
                flat = body.replace(f"<p>{head}</p>", head, 1)
                self.assertNotEqual(flat, body)
                self.assertEqual(corrections.settled_chapter_body(self.SLUG, 1, flat), body)

    # PG 29296's own markup: the opening section, its poem cut to the last
    # stanza, and the signature under it.
    PAGE = """<html><body>
<h2 class="chap top4"><a id="Page_ix"></a><span class="ns">[p</span><span class="pgmark">ix</span><span class="ns">] </span>
<a id="THE_MINISTRY_OF_INTERCESSION"></a>THE MINISTRY OF INTERCESSION<br><small class="toclink"><a href="#toc" class="pginternal">Contents</a></small></h2>
<hr class="chap">
<div class="poem"><div class="stanza">
<div>Transmuted into wealth unpriced,</div>
<div class="indent">By Him who giveth thus</div>
<div>The glory all to Jesus Christ,</div>
<div class="indent">The gladness all to us!</div>
</div></div>
<div class="rt"><span class="smc">F. R. Havergal</span>.</div>
<p class="pgbrk lt"><i>September 1877.</i></p>
</body></html>"""

    def test_the_importer_emits_the_block_the_correction_wraps(self):
        """The guard is a string match: the importer's block, byte for byte,
        and followed by the same dateline."""
        from library.management.commands.import_gutenberg import (
            content_root,
            split_by_heading,
        )

        [(_, body)] = split_by_heading(content_root(self.PAGE), "h2")
        block = "<p>F. R. Havergal.</p> <p><i>September 1877.</i></p>"
        self.assertIn(block, body)
        self.assertIn(block, self._opening("en"))


class ThingsAsTheyAreDisplayLineTests(SimpleTestCase):
    """`things-as-they-are`: 78 display lines shipped as loose text, in en and sw.

    See its `wrapped_blocks` entry in `corrections.py`: the English entries,
    the Swahili ones, then the ornamental break shared by both. Asserted per
    edition against the SHIPPED fixture, and the English against what the
    importer emits from PG 29426's own markup.
    """

    SLUG = "things-as-they-are"
    LINES = 68  # per edition, besides the breaks
    BREAK = "<b>. . . . . . .</b>"
    BREAKS = {3: 1, 8: 3, 25: 1, 27: 3, 28: 1, 30: 1}

    def _chapters(self, lang):
        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, lang).read_text(encoding="utf-8"))
        return {
            r["fields"]["order"]: (r["fields"]["title"], r["fields"]["body_html"])
            for r in rows
            if r["model"] == "library.chapter"
        }

    def _entries(self, lang):
        entries = corrections.BODY_CORRECTIONS[self.SLUG]["wrapped_blocks"]
        self.assertEqual(len(entries), 2 * self.LINES + 3)
        return entries[: self.LINES] if lang == "en" else entries[self.LINES : 2 * self.LINES]

    def test_every_line_ships_in_its_block(self):
        for lang in ("en", "sw"):
            chapters = self._chapters(lang)
            corpus = "".join(body for _, body in chapters.values())
            for head, tag, *_ in self._entries(lang):
                with self.subTest(language=lang, head=head):
                    self.assertEqual(corpus.count(f"<{tag}>{head}"), 1)
            for order, (_, body) in chapters.items():
                with self.subTest(language=lang, chapter=order):
                    self.assertEqual(body.count(self.BREAK), self.BREAKS.get(order, 0))
                    self.assertEqual(
                        body.count(f"<p>{self.BREAK}</p>"), self.BREAKS.get(order, 0)
                    )

    def test_the_correction_wraps_the_flattened_rows(self):
        """Strip every wrapped line back to loose text — with the `<br/>` the
        rows carried in front of a "From" line or the imprint — and the
        correction must restore the shipped body exactly."""
        for lang in ("en", "sw"):
            heads = [head for head, *_ in self._entries(lang)]
            for order, (_, body) in self._chapters(lang).items():
                flat = body.replace(f"<p>{self.BREAK}</p>", self.BREAK)
                for head in heads:
                    lead = "<br/>" if head.startswith(("<i>", "LONDON")) else ""
                    flat = re.sub(
                        rf"<(p|h3)>({re.escape(head)}.*?)</\1>",
                        lambda m, lead=lead: lead + m.group(2),
                        flat,
                        count=1,
                        flags=re.S,
                    )
                if flat == body:
                    continue
                with self.subTest(language=lang, chapter=order):
                    self.assertEqual(corrections.settled_chapter_body(self.SLUG, order, flat), body)

    # PG 29426's own markup, whole display lines, prose cut short: the Note's
    # drop-cap opener, its signature and the first "From" line behind its own
    # <br>; a poem broken by the ornament and run into a caption; an opener
    # after an epigraph's attribution; the imprint behind four breaks.
    PAGE = """<html><body>
<h2>Note</h2>
<div class="cap">WITHIN a few weeks of the publication of <i>Things as They Are</i>,
letters were received from missionaries working in different parts
of India, confirming its truth. But some in England doubt it.
And so it was proposed that if a fourth edition were called for, a few confirmatory
notes, written by experienced South Indian missionaries, other
than those of the district described, would be helpful. Several such notes
are appended. The Indian view of one of the chief facts set forth in the
book is expressed in the note written by one who, better than any missionary,
and surely better even than any onlooker at home, has the right
to be heard in this matter—<i>and the right to be believed</i>.</div>
<p>And now at His feet, who can use the least, we lay this book again; for
"to the Mighty One," as the Tamil proverb says, "even the blade of
grass is a weapon." May it be used for His Name's sake, to win more
prayer for India—and all dark lands—the prayer that prevails.</p>
<div class="sig">
<span class="smcap">Amy Wilson-Carmichael</span>,<br>
</div>
<div class="unindent">
<span style="margin-left: 2em;">Dohnavur, Tinnevelly District,</span><br>
<span style="margin-left: 6em;">S. India.</span><br>
</div>
<h3><br>Confirmatory Notes</h3>
<div class="center"><br><i>From</i> Rev. <span class="smcap">D. Downie</span>, D.D., American Baptist Mission,
Nizam's Dominions, S. India.</div>
<p>I have felt for many years that we missionaries were far too prone.</p>
<h2>CHAPTER I</h2>
<h3>About the Book</h3>
<p>But in touching the Dust we touch the outworkings.</p>
<div class="poem">
"God! fight we not within a cursèd world,<br>
<span style="margin-left: 0.5em;">Whose very air teems thick with leaguèd fiends—</span><br>
<span style="margin-left: 0.5em;">Each word we speak has infinite effects—</span><br>
<span style="margin-left: 0.5em;">Each soul we pass must go to heaven or hell—</span><br>
<span style="margin-left: 0.5em;">And this our one chance through eternity</span><br>
<span style="margin-left: 0.5em;">To drop and die, like dead leaves in the brake!</span><br>
</div>
<div class="center"><b>.        .        .        .        .        .        .</b></div>
<div class="poem">
<span style="margin-left: 0.5em;">Be earnest, earnest, earnest; mad if thou wilt:</span><br>
<span style="margin-left: 0.5em;">Do what thou dost as if the stake were heaven,</span><br>
<span style="margin-left: 0.5em;">And that thy last deed ere the judgment day."</span><br>
<br><br></div>
<div class="figcenter" style="width: 550px;" role="figure" aria-labelledby="ebm_caption3">
<img alt="This is our bullock-bandy. The water was up to the top of the bank when we crossed last. The palms are cocoanuts." height="324" src="images/illus-024.jpg" title="" width="550" id="img_images_illus-024.jpg">
<span class="caption" id="ebm_caption3">This is our bullock-bandy. The water was up to the top of the bank when we crossed last. The palms are cocoanuts.</span>
<h2>CHAPTER X</h2>
<h3>The Creed Chasm</h3>
<div class="blockquot"><p>"I have had to deal in the same afternoon's work, on the one
hand with men of keen powers of intellect, whose subtle
reasoning made one look to the foundations of one's own faith;
and on the other hand with ignorant crowds, whose conception
of sin was that of a cubit measure, and to whom the terms
'faith' and 'love' were as absolutely unknown as though they
had been born and bred in some undeveloped race of Anthropoids."</p>
<div class="sig">
<i>Rev. T. Walker, India.</i><br>
</div><br><br></div>
<div class="cap">IN writing about the Classes and the Masses of South
India, one great difference which does not exist at
home should be explained. In England a prince
and a peasant may be divided by outward things—social
position, style of life, and the duty of life—but in all
inward things they may be one—one in faith, one in
purpose, one in hope. The difference which divides them
is only accidental, external; and the peasant, perhaps
being in advance of the prince in these verities of
existence, may be regarded by the prince as nobler than
himself: there is no spiritual chasm between them. It
is the same in the realm of scholarship. All true
Christians, however learned or however unlearned, hold
one and the same faith. But in India it is not so.
The scholar would smile at the faith of the simple
villagers, he would even teach them to believe that which
he did not believe himself, holding that it was more<span class="pagenum"><a id="Page_92">[92]</a></span>
suitable for them, and he would marvel at your ignorance
if you confounded his creed with theirs; and yet in
name both he and they are Hindus.</div>
<h2>APPENDIX</h2>
<h3>Some Indian Saints</h3>
<p>They have no desire to hide things.</p>
<div class="center"><br><br><br><br>
<small>LONDON: MORGAN AND SCOTT</small><br>
</div>
<hr style="width: 65%;">
</body></html>"""

    def test_the_importer_emits_the_blocks_the_correction_wraps(self):
        """The guard is a string match, so the importer and the correction must
        agree byte for byte, or a re-import carries a line twice."""
        from library.ingest import soup
        from library.management.commands.import_gutenberg import (
            content_root,
            split_by_heading,
        )

        chapters = dict(self._chapters("en").values())
        heads = [head for head, *_ in self._entries("en")] + [self.BREAK]
        emitted = 0
        for title, body in split_by_heading(content_root(self.PAGE), "h2"):
            for block in soup(body).body.find_all(["p", "h3"], recursive=False):
                block = str(block)
                if not any(block.startswith((f"<p>{h}", f"<h3>{h}")) for h in heads):
                    continue  # prose the importer always kept
                with self.subTest(chapter=title, block=block[:40]):
                    self.assertIn(block, chapters[title])
                    emitted += 1
        self.assertEqual(emitted, 8)


class ThingsAsTheyArePrefaceSignatureTests(SimpleTestCase):
    """`things-as-they-are` ch2: the preface's "EUGENE STOCK." signature.

    The rows carried it as `<p>— Eugene Stock</p>`, a restyling from PR #172's
    preface rebuild, which also dropped the `<hr>` before the Glossary; see the
    pair after the book's `wrapped_blocks` in `corrections.py`. Asserted per
    edition against the SHIPPED fixture, and the blocks against what the
    importer emits from PG 29426's own markup.
    """

    SLUG = "things-as-they-are"
    OLD = "<p>— Eugene Stock</p>"
    BLOCK = "<h3>EUGENE STOCK.</h3>"
    NEW = f"{BLOCK}<hr/>"

    def _preface(self, lang):
        from library.content_fixtures import book_fixture_path

        rows = json.loads(book_fixture_path(self.SLUG, lang).read_text(encoding="utf-8"))
        (body,) = (
            r["fields"]["body_html"]
            for r in rows
            if r["model"] == "library.chapter" and r["fields"]["order"] == 2
        )
        return body

    def test_the_signature_ships_as_the_importer_block(self):
        for lang in ("en", "sw"):
            body = self._preface(lang)
            with self.subTest(language=lang):
                self.assertNotIn(self.OLD, body)
                self.assertEqual(body.count(self.BLOCK), 1)
                self.assertIn(f"</p>{self.NEW}<h3>", body)

    def test_the_correction_restores_the_restyled_rows(self):
        """Put the old `<p>` back; the correction must give the shipped body
        exactly. (Asserting the fixture alone passes with the pair deleted,
        while the live rows keep the restyled line.)"""
        for lang in ("en", "sw"):
            body = self._preface(lang)
            with self.subTest(language=lang):
                old = body.replace(self.NEW, self.OLD)
                self.assertNotEqual(old, body)
                self.assertEqual(corrections.settled_chapter_body(self.SLUG, 2, old), body)

    # PG 29426's own markup, prose cut short: enough of the preface to make it
    # a chapter, its signature, and the Contents and Glossary behind it.
    PAGE = """<html><body>
<h2>Preface</h2>
<div class="cap">THE writer of these thrilling chapters is a Keswick
missionary, well known to many friends as the
adopted daughter of Mr. Robert Wilson, the much-respected
chairman of the Keswick Convention. She
worked for a time with the Rev. Barclay Buxton in
Japan; and for the last few years she has been with the
Rev. T. Walker (also a C.M.S. Missionary) in Tinnevelly,
and is on the staff of the Church of England Zenana
Society.</div>
<p>I do not think the realities of Hindu life have ever
been portrayed with greater vividness than in this book;
and I know that the authoress's accuracy can be fully
relied upon. The picture is drawn without prejudice,
with all sympathy, with full recognition of what is
good, and yet with an unswerving determination to
tell the truth and let the facts be known,—that is, so
far as she dares to tell them. What she says is the
truth, and nothing but the truth; but it is not the
whole truth—<i>that</i> she could not tell. If she wrote it,
it could not be printed. If it were printed, it could not
be read. But if we read between the lines, we do just
catch glimpses of what she calls "the Actual."</p>
<p>It is evident that the authoress deeply felt the responsibility
of writing such a book; and I too feel the<span class="pagenum"><a id="Page_x">[x]</a></span>
responsibility of recommending it. I do so with the
prayer of my heart that God will use it to move many.
It is not a book to be read with a lazy kind of sentimental
"interest." It is a book to send the reader to
his knees—still more to <i>her</i> knees.</p>
<p>But the larger part of this book is a revelation—so
far as is possible—of the "Actual" of Hinduism and
Caste. God grant that its terrible facts and its burning
words may sink into the hearts of its readers! Perhaps,
when they have read it, they will at last agree that
we have used no sensational and exaggerated language
when we have said that the Church is only playing at
missions! Service, and self-denial, and prayer, must be
on a different scale indeed if we are ever—I do not say
to convert the world—but even to evangelise it.</p>
<div class="sig">
EUGENE STOCK.<br></div>
<hr style="width: 65%;"><p><span class="pagenum"><a id="Page_xiii">[xiii]</a></span></p>
<h2>Contents</h2>
<div class="center">
<table style="border-spacing: 0px;padding: 0px;border-width: 0px;" data-summary="Contents">
<tbody><tr><td colspan="2" style="text-align: left;"><small>CHAPTER</small></td><td style="text-align: right;"><small>PAGE</small></td></tr>
<tr><td style="text-align: right;">I. </td><td style="text-align: left;"><span class="smcap">About the Book</span></td><td style="text-align: right;"><a href="#Page_1" class="pginternal">1</a></td></tr>
</tbody></table></div>
<hr style="width: 65%;"><p><span class="pagenum"><a id="Page_xv">[xv]</a></span></p>
<h2>Glossary</h2>
<div class="center">
<table style="border-spacing: 0px;padding: 4px;border-width: 0px;" data-summary="Glossary">
<tbody><tr><td style="vertical-align: top;text-align: left;"><span class="smcap">Agni</span></td><td style="text-align: left;">God of Fire.</td></tr>
</tbody></table></div>
</body></html>"""

    def test_the_importer_emits_the_blocks_the_correction_writes(self):
        """The pair's new side must be the importer's blocks byte for byte, and
        end the preface's prose, or a re-import and the rows disagree."""
        from library.management.commands.import_gutenberg import extract_chapters

        pair = (self.OLD, self.NEW)
        self.assertIn(pair, corrections.BODY_CORRECTIONS[self.SLUG]["replacements"])
        (title, body), *_ = extract_chapters(self.PAGE)
        self.assertEqual(title, "Preface")
        self.assertEqual(body.count(self.BLOCK), 1)
        self.assertIn(f"even to evangelise it.</p> {self.BLOCK} <hr/><h3>Glossary</h3>", body)
        self.assertNotIn(self.OLD, body)
