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


class ShelfRepairTests(SimpleTestCase):
    """The rest of what the two over-matching selectors had already eaten.

    `[class*=pginternal]` (#1573) and `[class*=note i]` (#1574) are both
    qualified now, so no future import loses this text — these are the rows
    already on the shelf, which are never re-imported.

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

    @staticmethod
    def _bodies(slug):
        from library.content_fixtures import book_fixture_path

        path = book_fixture_path(slug, "en")
        return {r["fields"]["order"]: r["fields"]["body_html"]
                for r in json.loads(path.read_text(encoding="utf-8"))
                if (r.get("fields") or {}).get("body_html")}

    def test_every_repair_is_in_the_shipped_fixture_exactly_once(self):
        for slug, pairs in self.REPAIRS.items():
            joined = "\n".join(self._bodies(slug).values())
            for damaged, repaired in pairs:
                with self.subTest(slug=slug, repaired=repaired[:40]):
                    self.assertEqual(joined.count(repaired), 1)
                    self.assertNotIn(damaged, joined)

    def test_the_corrections_are_what_repair_them(self):
        """Damage each site again; `apply_body_corrections` must undo it."""
        for slug, pairs in self.REPAIRS.items():
            bodies = self._bodies(slug)
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
        bodies = self._bodies("holy-in-christ")
        for heading, order in self.HEADINGS:
            with self.subTest(heading=heading[:28]):
                carriers = [o for o, b in bodies.items() if heading in b]
                self.assertEqual(carriers, [order])

    def test_a_stripped_note_heading_comes_back(self):
        bodies = self._bodies("holy-in-christ")
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


class StrayOpenerTests(SimpleTestCase):
    """`strip_stray_openers` — opt-in, for an edition that sets no quotes at all.

    Its safety is its premise. On a work that prints no quotation marks, an
    opening mark can only be a scanned margin rule; anywhere else it would
    delete real quotations. So the function must refuse any body that shows a
    quotation of its own, and must not touch a mark inside a word, which is a
    soft hyphen the work's own pairs rejoin.
    """

    def _strip(self, html):
        return corrections.strip_stray_openers(html)

    def test_removes_an_opener_standing_before_a_word(self):
        self.assertEqual(
            self._strip("<p>a king of poor ‘and afflicted persons</p>"),
            "<p>a king of poor and afflicted persons</p>",
        )
        self.assertEqual(
            self._strip("<p>in holy duties, as meditation “and prayer</p>"),
            "<p>in holy duties, as meditation and prayer</p>",
        )

    def test_removes_one_opening_a_paragraph(self):
        self.assertEqual(self._strip("<p>‘There is a conformity</p>"),
                         "<p>There is a conformity</p>")

    def test_leaves_a_mark_inside_a_word(self):
        """"his‘own" is a soft hyphen misread, and stripping it would weld
        "hisown"; the work's replacement pairs are the channel for those."""
        self.assertEqual(self._strip("<p>neglected his‘own members</p>"),
                         "<p>neglected his‘own members</p>")

    def test_leaves_apostrophes_and_closers(self):
        html = "<p>like Jonas’ gourd, and God’s mercy</p>"
        self.assertEqual(self._strip(html), html)

    def test_refuses_a_body_that_sets_quotation_marks(self):
        """A translation shares the English slug's entry, and may quote."""
        html = "<p>Disse ele: “Não quebrará a cana trilhada.”</p>"
        self.assertEqual(self._strip(html), html)

    def test_is_idempotent(self):
        once = self._strip("<p>poor ‘and “afflicted</p>")
        self.assertEqual(self._strip(once), once)


class BruisedReedRepairTests(SimpleTestCase):
    """The damage #1943's re-import shipped, repaired on the stored text.

    Every case is asserted both ways, as in `ShelfRepairTests`: the repair is in
    the shipped fixture, AND putting the damage back and re-settling undoes it —
    the half that proves the live rows are repaired too, since
    `apply_body_corrections` carries these to prod with no migration.
    """

    SLUG = "the-bruised-reed"

    #: (as #1943 shipped it, as it should read) — one per class of defect.
    REPAIRS = (
        # a whole scanned line lost, "repaired" into a verbless sentence
        ("let us not fore the cure be wrought,",
         "let us not take off ourselves too soon, nor pull off the plaster "
         "before the cure be wrought,"),
        # a stray opening mark where a letter was
        ("believe “ruth from truth", "believe truth from truth"),
        # a stray opening mark, and nothing else
        ("a king of poor ‘and afflicted", "a king of poor and afflicted"),
        # a stray closing mark
        ("without making’ a noise", "without making a noise"),
        # a misread landing on a real word
        ("authority derived rot God", "authority derived from God"),
        ("the Sear of the Lord", "the fear of the Lord"),
        # a scripture reference
        ("Rom. vii. 34, saith", "Rom. vii. 24, saith"),
        # the entry's own earlier modernisation, undone
        ("an affectionate entreaty", "an affectionate intreaty"),
    )

    def _bodies(self):
        return ShelfRepairTests._bodies(self.SLUG)

    def test_every_repair_is_in_the_shipped_fixture_exactly_once(self):
        joined = "\n".join(self._bodies().values())
        for damaged, repaired in self.REPAIRS:
            with self.subTest(repaired=repaired[:40]):
                self.assertEqual(joined.count(repaired), 1)
                self.assertNotIn(damaged, joined)

    def test_the_corrections_are_what_repair_them(self):
        bodies = self._bodies()
        for damaged, repaired in self.REPAIRS:
            order = next(o for o, b in bodies.items() if repaired in b)
            with self.subTest(chapter=order, repaired=repaired[:40]):
                broken = bodies[order].replace(repaired, damaged, 1)
                self.assertNotEqual(broken, bodies[order])
                self.assertEqual(
                    corrections.settled_chapter_body(self.SLUG, order, broken),
                    bodies[order],
                )

    def test_a_reimport_of_the_raw_scan_reads_the_same(self):
        """The raw-scan pair for the lost line now writes the whole sentence,
        so a re-import and the repaired live row agree."""
        raw = "<p>Therefore let us not fore the cure be erowiglt but keep</p>"
        settled = corrections.settled_chapter_body(self.SLUG, 4, raw)
        self.assertIn("nor pull off the plaster before the cure be wrought, but", settled)

    def test_no_opening_quote_mark_survives(self):
        """This edition sets no quotation marks, so every one was scan damage."""
        for order, body in self._bodies().items():
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
