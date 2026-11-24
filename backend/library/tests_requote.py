"""The re-quote tooling: the quotation inventory and the splice validator.

Each detector is pinned with the case that shaped it, and the validator with
each check a wave-1 worker's throwaway script carried (substring unique,
replacement inside OWB, tag sequence and quote-mark balance unchanged), plus the
allowances the four founder rules make (pieces joined with "…", OWB's own
speech marks set as ‹ ›). One integration test runs the inventory on a
shipped, already re-quoted sermon, so a detector that starts crying wolf on
real text fails here rather than in a worker's session.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from library import requote as rq
from library.admin_views.quality import _blocks as admin_blocks
from library.content_fixtures import render_rows
from library.translation import USFM_ORDER

JOHN_3_16 = rq.parse_reference("John 3:16")


def owb(ref: str) -> str:
    return rq.owb_text(rq.parse_reference(ref), "am")


def work_of(*bodies: str, kind: str = "book", language: str = "am") -> rq.Work:
    """A synthetic book: one chapter per body, ordered from 1."""
    containers, blocks = {}, []
    for order, body in enumerate(bodies, start=1):
        key = f"body:{order}"
        containers[key] = body
        blocks += rq._blocks_of(body, key, order)
    return rq.Work(kind, "test", language, containers, blocks)


class ReferenceTests(SimpleTestCase):
    def test_notes_references(self):
        self.assertEqual(rq.parse_reference("Psalm 46:1-3").label, "Psalm 46:1-3")
        self.assertEqual(rq.parse_reference("Psalms 103:13").label, "Psalm 103:13")
        self.assertEqual(rq.parse_reference("1 John 5:14").usfm, "1JN")
        self.assertEqual(rq.parse_reference("Matthew 15:28a").label, "Matthew 15:28")
        self.assertEqual(rq.parse_reference("PSA 23:1").usfm, "PSA")
        self.assertEqual(rq.parse_reference("Phil 2:13").usfm, "PHP")
        self.assertIsNone(rq.parse_reference("Wisdom 3:1"))

    def test_amharic_citations(self):
        spans = rq.local_citations("(ዮሐንስ 3:36፤ 1ኛ ዮሐንስ 5:12)", "am")
        self.assertEqual([s.label for s in spans], ["John 3:36", "1 John 5:12"])
        # A verse list reads as the span it covers (school-of-prayer ch32).
        self.assertEqual(
            rq.local_citations("1ኛ ተሰሎንቄ 5:16፣ 17፣ 18", "am")[0].label,
            "1 Thessalonians 5:16-18",
        )
        # The Ethiopic separator and an abbreviation with its dot.
        self.assertEqual(
            rq.local_citations("(ዮሐ. 4፥35-38)", "am")[0].label, "John 4:35-38"
        )
        self.assertEqual(rq.local_citations("1 ቆሮንቶስ 13:4", "am")[0].usfm, "1CO")
        # Numbers with no book named are not a reference.
        self.assertEqual(rq.local_citations("(13:4)", "am"), [])

    def test_language_data_is_well_formed(self):
        for path in sorted(rq.LANGUAGE_DATA.glob("*.json")):
            with self.subTest(language=path.stem):
                data = rq.language_data(path.stem)
                self.assertEqual(data["language"], path.stem)
                self.assertTrue(set(data["book_names"].values()) <= set(USFM_ORDER))
                self.assertEqual(len(set(data["book_names"].values())), 66)
                for d in data["decisions"]:
                    for ref in d["references"]:
                        self.assertIsNotNone(rq.parse_reference(ref), (d["id"], ref))
                    self.assertTrue(d["decision"])

    def test_swahili_citations_as_the_library_writes_them(self):
        spans = rq.local_citations("(Yohana 3:36; 1 Yohana 5:12)", "sw")
        self.assertEqual([s.label for s in spans], ["John 3:36", "1 John 5:12"])
        self.assertEqual(
            rq.local_citations("(1 Wathesalonike 5:16-18)", "sw")[0].label,
            "1 Thessalonians 5:16-18",
        )
        self.assertEqual(
            rq.local_citations("(Matendo ya Mitume 2:38)", "sw")[0].usfm, "ACT"
        )
        self.assertEqual(rq.local_citations("(Ebr 11:6)", "sw")[0].usfm, "HEB")
        self.assertEqual(
            rq.local_citations("(Kumbukumbu la Torati 6:5)", "sw")[0].usfm, "DEU"
        )


class BlockTests(SimpleTestCase):
    def test_blocks_are_the_admin_views_blocks(self):
        body = (
            "<h2>ርዕስ</h2><p>አንድ <i>ሁለት</i></p><blockquote><p>ሦስት</p></blockquote>"
            "<p> </p><ul><li>አራት</li></ul><p>አምስት</p>"
        )
        mine = [rq.render(body[s:e]) for s, e in rq.block_spans(body)]
        self.assertEqual(mine, admin_blocks(body))

    def test_a_bio_aside_is_one_block(self):
        body = '<p>a</p><aside class="prayer"><p>b</p><p><cite>c</cite></p></aside><p>d</p>'
        self.assertEqual(len(rq.block_spans(body)), 4)
        self.assertEqual(len(rq.block_spans(body, top_level=True)), 3)


class InventoryTests(SimpleTestCase):
    def test_cited_quotation_status(self):
        good = f"<p>ሲል ይናገራል፦ «{owb('John 3:16')}» (ዮሐንስ 3:16)።</p>"
        old = (
            "<p>ሲል ይናገራል፦ «እግዚአብሔር አንድያ ልጁን እስኪሰጥ ድረስ ዓለሙን እንዲሁ ወዶአልና» (ዮሐንስ 3:16)።</p>"
        )
        rows = rq.inventory(work_of(good + old), None)
        self.assertEqual(
            [(r.kind, r.reference, r.status) for r in rows],
            [
                ("cited", "John 3:16", rq.ALREADY_OWB),
                ("cited", "John 3:16", rq.NEEDS_REQUOTE),
            ],
        )
        self.assertEqual(rows[0].owb, owb("John 3:16"))

    def test_epigraph_dash_citation(self):
        body = f"<p>«{owb('Psalm 23:1')}»—መዝሙር 23:1።</p>"
        (row,) = rq.inventory(work_of(body), None)
        self.assertEqual(
            (row.kind, row.reference, row.status),
            ("cited", "Psalm 23:1", rq.ALREADY_OWB),
        )

    def test_uncited_quotation_is_matched_to_a_nearby_citation(self):
        body = (
            f"<p>«{owb('John 14:6')}» (ዮሐንስ 14:6)</p>"
            "<p>ስለዚህ «መንገዱ፣ እውነቱና ሕይወቱ እኔ ነኝ» ብሎ ተናገረ።</p>"
        )
        rows = rq.inventory(work_of(body), None)
        quoted = [r for r in rows if r.block_index == 1]
        self.assertEqual(
            [(r.kind, r.reference, r.status) for r in quoted],
            [("quoted", "John 14:6", rq.ALREADY_OWB)],
        )

    def test_unquoted_recitation(self):
        # Phil 2:13's "to will and to do": recited, no marks — a quotation
        # under the founder rule, so the inventory must surface it.
        verse = owb("John 3:16").rstrip("።")
        body = f"<p>(ዮሐንስ 3:16)</p><p>ወንጌሉ ይህ ነው፤ {verse}፤ ይህንም እናምናለን።</p>"
        rows = [r for r in rq.inventory(work_of(body), None) if r.block_index == 1]
        self.assertEqual(
            [(r.kind, r.status) for r in rows], [("recited", rq.ALREADY_OWB)]
        )

    def test_joined_pieces_are_already_owb(self):
        # «በእኔ ብትኖሩ … ለምኑ» — pieces shorter than mined_verification's
        # 8-character floor, joined as the four rules allow.
        span = rq.parse_reference("John 15:7")
        self.assertTrue(rq.is_owb("በእኔ ብትኖሩ … የምትፈልጉትን ሁሉ ለምኑ፤ ይደረግላችሁማል።", span, "am"))
        self.assertFalse(rq.is_owb("በእኔ ብትኖሩ … የምትፈልጉትን ሁሉ ለምኑ፤ ይሆንላችሁማል።", span, "am"))

    def test_english_only_quotation(self):
        english = work_of(
            "<p>He said, “For God so loved the world, that he gave his only begotten Son.”</p>",
            language="en",
        )
        rows = rq.inventory(
            work_of("<p>ጌታ ዓለምን እጅግ ስለ ወደደ ልጁን እንደ ሰጠ ተናገረ።</p>"), english
        )
        self.assertEqual(
            [(r.kind, r.reference, r.status) for r in rows],
            [("english_only", "John 3:16", rq.ALLUSION)],
        )

    def test_detect_decision_finds_a_short_refrain(self):
        # «ፈቃድህ ትሁን» is two words: no detector calls it Scripture alone, so
        # the word list names it and every occurrence becomes a row.
        rows = rq.inventory(work_of("<p>ልባችን ሁልጊዜ «ፈቃድህ ትሁን» ይላል።</p>"), None)
        self.assertEqual(
            [(r.kind, r.reference, r.status, r.flags) for r in rows],
            [("recurring", "Matthew 26:42", rq.NEEDS_REQUOTE, ["thy-will-be-done"])],
        )

    def test_recurring_decision_is_flagged(self):
        english = work_of("<p>The Comforter will come.</p>", language="en")
        body = f"<p>«{owb('John 14:16')}» (ዮሐንስ 14:16)</p>"
        (row,) = [r for r in rq.inventory(work_of(body), english) if r.kind == "cited"]
        self.assertIn("comforter", row.flags)


class NotesDiffTests(SimpleTestCase):
    def setUp(self):
        q = owb("John 3:16")
        self.work = work_of(
            f"<p>መግቢያ።</p><p>«{q}» (ዮሐንስ 3:16)</p><p>«{owb('Psalm 23:1')}» (መዝሙር 23:1)</p>"
        )
        self.rows = rq.inventory(self.work, None)

    def test_missing_wrong_block_and_unlocated(self):
        notes = [
            {
                "reference": "John 3:16",
                "status": "mined",
                "block_index": 0,
                "chapter_order": 1,
            },
            {
                "reference": "Romans 8:28",
                "status": "self_rendered",
                "block_index": 0,
                "chapter_order": 1,
            },
        ]
        diff = rq.notes_diff(self.rows, notes, self.work)
        self.assertEqual([m["reference"] for m in diff["missing"]], ["Psalm 23:1"])
        self.assertEqual(
            [
                (w["reference"], w["notes_block"], w["found_block"])
                for w in diff["wrong_block"]
            ],
            [("John 3:16", 0, 1)],
        )
        self.assertEqual(
            [u["reference"] for u in diff["unlocated_notes"]], ["Romans 8:28"]
        )

    def test_work_level_index_and_sibling_reference(self):
        # No chapter_order: the admin view's work-level index. And a note
        # carrying the reference of the verse that QUOTES this one (Heb 1:5
        # for Ps 2:7) still answers it when the words are that verse's.
        notes = [
            {"reference": "John 3:16", "status": "mined", "block_index": 1},
            {"reference": "Psalms 23:1", "status": "mined", "block_index": 2},
        ]
        diff = rq.notes_diff(self.rows, notes, self.work)
        self.assertEqual(
            (diff["missing"], diff["wrong_block"], diff["unlocated_notes"]),
            ([], [], []),
        )


class OffsetTests(SimpleTestCase):
    def test_a_chapter_shifted_by_one_is_named_once(self):
        wrong = [
            {"chapter": 3, "found_chapter": 3, "notes_block": b + 1, "found_block": b}
            for b in (2, 6, 9)
        ] + [{"chapter": 4, "found_chapter": 4, "notes_block": 1, "found_block": 7}]
        self.assertEqual(rq._offsets(wrong), {"3": -1})


class ValidatorTests(SimpleTestCase):
    def setUp(self):
        self.verse = owb("John 3:16")
        self.body = "<p>እንዲህ ተብሏል፦ «እግዚአብሔር ዓለሙን <i>እንዲሁ</i> ወዶአልና።» (ዮሐንስ 3:16)</p><p>ሁለተኛ።</p>"
        self.work = work_of(self.body)

    def edit(self, **kw):
        e = {
            "chapter": 1,
            "block": 0,
            "reference": "John 3:16",
            "old": "እግዚአብሔር ዓለሙን <i>እንዲሁ</i> ወዶአልና።",
            "new": f"{self.verse.split('፣')[0]} <i>፣</i>",
        }
        e.update(kw)
        return e

    def problems(self, *edits):
        problems, _ = rq.validate(self.work, list(edits))
        return [p.check for p in problems]

    def test_a_good_splice_passes_and_lands(self):
        new = f"{self.verse[:-1]}<i></i>።"
        problems, state = rq.validate(self.work, [self.edit(new=new)])
        self.assertEqual(problems, [])
        self.assertIn(self.verse[:-1], state["body:1"])

    def test_old_must_be_unique_in_its_block(self):
        self.assertEqual(self.problems(self.edit(old="ን", new="ን")), ["unique"])
        self.assertEqual(self.problems(self.edit(old="የለም")), ["unique"])

    def test_new_must_be_owb(self):
        self.assertIn("owb", self.problems(self.edit(new="እግዚአብሔር ዓለሙን ወደደ<i></i>።")))

    def test_tags_balance_and_final_mark(self):
        self.assertIn("tags", self.problems(self.edit(new=f"{self.verse}")))
        self.assertIn(
            "balance",
            self.problems(
                self.edit(old="«", new="", reference="John 3:16", self_rendered=True)
            ),
        )
        self.assertIn(
            "final",
            self.problems(
                self.edit(new=f"{self.verse.split('፣')[0]}<i></i>", self_rendered=True)
            ),
        )

    def test_joined_pieces_and_inner_marks_are_allowed(self):
        acts = owb("Acts 1:8")  # carries its own closing » mid-quote
        body = "<p>«መንፈስ ቅዱስ ኃይል ይሰጣችኋል» (ሐዋርያት ሥራ 1:8)</p>"
        work = work_of(body)
        a, b = acts.split("፤")[0], "እስከ ምድር ዳርቻም ድረስ ስለ እኔ ትመሰክራላችሁ።‹›"
        problems, _ = rq.validate(
            work,
            [
                {
                    "chapter": 1,
                    "block": 0,
                    "reference": "Acts 1:8",
                    "old": "መንፈስ ቅዱስ ኃይል ይሰጣችኋል",
                    "new": f"{a} … {b}",
                }
            ],
        )
        self.assertEqual(problems, [])

    def test_sentences_out_of_owb_order(self):
        # Murray sets John 16:26 before 16:23 inside one pair of marks; each
        # sentence is OWB's own, so the splice is accepted.
        v26, v24 = owb("John 16:26"), owb("John 16:24")
        work = work_of("<p>«ቃል» (ዮሐንስ 16:24)</p>")
        problems, _ = rq.validate(
            work,
            [
                {
                    "chapter": 1,
                    "block": 0,
                    "old": "ቃል",
                    "new": f"{v26} {v24}",
                    "reference": "John 16:25",
                }
            ],
        )
        self.assertEqual(problems, [])
        self.assertEqual(
            self.problems(
                self.edit(new=f"{owb('John 16:26')}<i></i>።", reference="John 3:16")
            ),
            ["owb"],
        )

    def test_edits_are_simulated_in_order(self):
        first = self.edit(new=f"{self.verse[:-1]}<i></i>።")
        # The second edit targets text the first one wrote.
        second = {
            "chapter": 1,
            "block": 0,
            "old": f"{self.verse[:-1]}<i></i>።",
            "new": f"{self.verse[:-1]}<i></i>።",
            "reference": "John 3:16",
        }
        self.assertEqual(self.problems(first, second), [])
        self.assertEqual(self.problems(second), ["unique"])

    def test_apply_writes_the_fixture_layout(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        rows = [
            {
                "model": "library.book",
                "fields": {"slug": "test", "language": "am", "title": "t"},
            },
            {
                "model": "library.chapter",
                "fields": {
                    "book": ["test", "am"],
                    "order": 1,
                    "title": "",
                    "body_html": self.body,
                    "word_count": 1,
                },
            },
        ]
        path = tmp / "test.am.json"
        path.write_text(render_rows(rows), encoding="utf-8")
        work = rq.load_work(
            "book",
            "test",
            "am",
            lambda p: path.read_text(encoding="utf-8") if p.name == path.name else None,
        )
        work.paths["fixture"] = path
        problems, state = rq.validate(
            work, [self.edit(new=f"{self.verse[:-1]}<i></i>።")]
        )
        self.assertEqual(problems, [])
        rq.apply(work, state)
        text = path.read_text(encoding="utf-8")
        written = json.loads(text)
        self.assertEqual(text, render_rows(written))
        self.assertIn(self.verse[:-1], written[1]["fields"]["body_html"])
        from library.text import word_count

        self.assertEqual(
            written[1]["fields"]["word_count"],
            word_count(written[1]["fields"]["body_html"]),
        )


class SwahiliValidatorTests(SimpleTestCase):
    """Swahili quotes with “…”: the validator reads the Scripture inside
    those marks and keeps them balanced, as it does «…» for Amharic."""

    def setUp(self):
        self.verse = rq.owb_text(rq.parse_reference("1 Thessalonians 5:17"), "sw")
        self.work = work_of(
            "<p>Paulo anasema, “ombeni bila kukoma” (1 Wathesalonike 5:17).</p>",
            language="sw",
        )

    def check(self, new, **kw):
        e = {
            "chapter": 1,
            "block": 0,
            "reference": "1 Thessalonians 5:17",
            "old": "“ombeni bila kukoma”",
            "new": new,
            **kw,
        }
        problems, _ = rq.validate(self.work, [e])
        return [p.check for p in problems]

    def test_owb_inside_the_marks_passes(self):
        self.assertEqual(self.check(f"“{self.verse[:-1]}”"), [])

    def test_union_wording_inside_the_marks_is_not_owb(self):
        self.assertIn("owb", self.check("“ombeni bila kukoma daima”"))

    def test_a_dropped_mark_is_unbalanced(self):
        self.assertIn("balance", self.check(f"“{self.verse[:-1]}", self_rendered=True))


class SwahiliInventoryTests(SimpleTestCase):
    """The detectors on Swahili text, and the two ways Latin-script Swahili
    differs from Ethiopic: OWB's capitals are wording, and three letters are
    not a piece."""

    def test_union_quotations_need_requoting_and_owb_does_not(self):
        work = work_of(
            "<p>Yesu alisema, “Mapenzi yako yatimizwe” (Mathayo 26:42).</p>"
            "<p>Paulo, “ombeni bila kukoma” (1 Wathesalonike 5:17).</p>"
            "<p>“Mapenzi Yako na yatendeke duniani kama yanavyotendeka mbinguni”"
            " (Mathayo 6:10).</p>",
            language="sw",
        )
        rows = {r.reference: r for r in rq.inventory(work, None)}
        self.assertEqual(rows["Matthew 26:42"].status, rq.NEEDS_REQUOTE)
        self.assertIn("thy-will-be-done", rows["Matthew 26:42"].flags)
        self.assertEqual(rows["1 Thessalonians 5:17"].status, rq.NEEDS_REQUOTE)
        self.assertIn("pray-without-ceasing", rows["1 Thessalonians 5:17"].flags)
        self.assertEqual(rows["Matthew 6:10"].status, rq.ALREADY_OWB)

    def test_owbs_capitals_are_part_of_the_wording(self):
        span = rq.parse_reference("Matthew 6:10")
        self.assertTrue(rq.is_owb("Mapenzi Yako na yatendeke duniani", span, "sw"))
        self.assertFalse(rq.is_owb("Mapenzi yako na yatendeke duniani", span, "sw"))

    def test_a_short_latin_piece_proves_nothing(self):
        span = rq.parse_reference("Matthew 6:10")
        self.assertFalse(rq.is_owb("Mapenzi Yako… kama", span, "sw"))
        self.assertTrue(rq.is_owb("Mapenzi Yako na yatendeke… mbinguni", span, "sw"))


class ShippedWorkTests(SimpleTestCase):
    """A wave-1 work, already re-quoted: the inventory should call nearly
    every quotation OWB and find the notes complete."""

    def test_the_dying_thief(self):
        result = rq.run_inventory("sermon", "the-dying-thief", "am")
        s = result["summary"]
        self.assertGreaterEqual(s["quotations"], 18)
        self.assertGreaterEqual(s["already_owb"] / s["quotations"], 0.7, result["rows"])
        # The one quotation the notes lack is Moody's unquoted "to them which
        # are in Christ Jesus" (Rom 8:1), which the wave-1 worker judged an
        # allusion. Surfacing it for a human is the job; anything more is noise.
        missing = [(m["reference"], m["kind"]) for m in result["notes_diff"]["missing"]]
        self.assertLessEqual(set(missing), {("Romans 8:1", "recited")}, missing)
