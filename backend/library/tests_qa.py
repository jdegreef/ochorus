"""Tests for the import preview content-quality checks (library.qa)."""

from __future__ import annotations

from django.test import TestCase

from library import qa

GOOD = (
    "This is a well-formed paragraph with more than enough words in it to comfortably "
    "look like real prose taken from a genuine printed book and to end cleanly on a stop."
)


def ch(title, html, words=None):
    return {"title": title, "html": html, "words": words if words is not None else len(qa.text_of(html).split())}


class QaReportTests(TestCase):
    def checks(self, chapters):
        return {w["check"] for w in qa.qa_report(chapters)}

    def test_clean_book_has_no_warnings(self):
        chapters = [
            ch("The First Thing", f"<p>{GOOD}</p><p>{GOOD}</p>" * 3),
            ch("The Second Thing", f"<p>{GOOD}</p><p>{GOOD}</p>" * 3),
        ]
        self.assertEqual(qa.qa_report(chapters), [])

    def test_generic_and_empty_titles(self):
        # Both a bare "Chapter 3" and an empty title flag generic_title.
        chapters = [
            ch("Chapter 3", f"<p>{GOOD}</p>" * 3),
            ch("", f"<p>{GOOD}</p>" * 3),
        ]
        gen = [w for w in qa.qa_report(chapters) if w["check"] == "generic_title"]
        self.assertEqual(len(gen), 2)

    def test_mid_sentence_split_only_when_followed(self):
        # First chapter ends mid-sentence and is followed → flagged.
        chapters = [
            ch("One", "<p>and then he went on to say</p>", words=200),
            ch("Two", f"<p>{GOOD}</p>", words=200),
        ]
        self.assertIn("mid_sentence_split", self.checks(chapters))
        # A single/last chapter ending mid-sentence is NOT flagged (nothing follows).
        last = [ch("Only", "<p>ends without a period</p>", words=200)]
        self.assertNotIn("mid_sentence_split", self.checks(last))

    def test_non_latin_sentence_marks_end_a_chapter(self):
        # Hindi danda, Amharic full stop / question mark and the Arabic
        # question mark are sentence ends; a chapter ending in one isn't split.
        for end in ("जाता है।", "प्रार्थना॥", "ጸሎት ነው።", "ምን ይሆናል፧", "ماذا نفعل؟"):
            with self.subTest(end=end):
                chapters = [ch("One", f"<p>{end}</p>", words=200), ch("Two", f"<p>{GOOD}</p>", words=200)]
                self.assertNotIn("mid_sentence_split", self.checks(chapters))
        # A Hindi chapter that really stops mid-sentence is still flagged.
        chapters = [ch("One", "<p>और फिर उसने कहा कि</p>", words=200), ch("Two", f"<p>{GOOD}</p>", words=200)]
        self.assertIn("mid_sentence_split", self.checks(chapters))

    def test_closing_bracket_ends_a_chapter(self):
        # An editorial note / sermon date or a footnote marker closes a chapter.
        for end in ("and be satisfied. [Jan. 20, 1782]", "fill it well.[4]"):
            with self.subTest(end=end):
                chapters = [ch("One", f"<p>{end}</p>", words=200), ch("Two", f"<p>{GOOD}</p>", words=200)]
                self.assertNotIn("mid_sentence_split", self.checks(chapters))
        # A chapter that really stops mid-sentence is still flagged.
        chapters = [ch("One", "<p>and then he said that the</p>", words=200), ch("Two", f"<p>{GOOD}</p>", words=200)]
        self.assertIn("mid_sentence_split", self.checks(chapters))

    def test_tiny_and_giant(self):
        tiny = [ch("Short", "<p>five words go here now</p>", words=5)]
        self.assertIn("tiny_chapter", self.checks(tiny))
        giant = [ch("Long", f"<p>{GOOD}</p>", words=9000)]
        self.assertIn("giant_chapter", self.checks(giant))

    def test_fragmented_paragraphs(self):
        # 20 five-word paragraphs → 100 words over 20 paras (avg 5): clears the
        # shared FRAG thresholds (>=10 paras, >=100 words, avg < 20).
        html = "<p>one two three four five</p>" * 20
        self.assertIn("fragmented_paragraphs", self.checks([ch("Frag", html, words=100)]))

    def test_missing_drop_cap(self):
        chapters = [ch("Lower", f"<p>lowercase opening that should have been a drop cap {GOOD}</p>", words=200)]
        self.assertIn("missing_drop_cap", self.checks(chapters))

    def test_duplicate_title(self):
        chapters = [
            ch("Prayer", f"<p>{GOOD}</p>" * 3),
            ch("Prayer", f"<p>{GOOD}</p>" * 3),
        ]
        self.assertIn("duplicate_title", self.checks(chapters))

    def test_high_severity_sorts_first(self):
        chapters = [
            ch("Chapter 1", "<p>word</p>" * 10, words=10),  # generic(high)+tiny+fragmented
            ch("Real Title", f"<p>{GOOD}</p>" * 3),
        ]
        report = qa.qa_report(chapters)
        self.assertTrue(report)
        self.assertEqual(report[0]["severity"], "high")

    def test_loose_text_flagged_with_count_and_snippet(self):
        html = f"<p>{GOOD}</p>A caption under a lost picture<p>{GOOD}</p>Another stray line."
        [w] = [w for w in qa.qa_report([ch("Pictures", html, words=200)]) if w["check"] == "loose_text"]
        self.assertEqual(w["severity"], "medium")
        self.assertIn("2 pieces of text", w["message"])
        self.assertIn("A caption under a lost picture", w["message"])

    def test_clean_body_has_no_loose_text_warning(self):
        self.assertNotIn("loose_text", self.checks([ch("Clean", f"<p>{GOOD}</p><hr/><p>{GOOD}</p>")]))


class LooseTextTests(TestCase):
    """`loose_text`: text sitting outside any block, reported as runs."""

    def test_well_formed_bodies_are_clean(self):
        for html in (
            "",
            f"<p>{GOOD}</p>",
            "<h2>Head</h2>\n<p>One <em>two</em>.</p>\n<hr/>\n<blockquote><p>Q</p></blockquote>",
            "<ul><li>a</li><li>b</li></ul>\n \n<ol><li>c</li></ol>",
            "<p>x</p>\xa0<p>y</p>",  # a non-breaking space between blocks is not text
            "<p>x</p><br/><p>y</p>",  # a stray break carries no text
            "<p>x</p><!-- a note --><p>y</p>",
            "﻿<p>x</p>​<p>y</p>",  # a BOM / zero-width space is not visible text
        ):
            with self.subTest(html=html):
                self.assertEqual(qa.loose_text(html), [])

    def test_bare_text_between_blocks(self):
        html = "<p>Before.</p>\n  A caption,   spread\nover lines  \n<p>After.</p>Tail."
        self.assertEqual(qa.loose_text(html), ["A caption, spread over lines", "Tail."])

    def test_text_at_the_start(self):
        self.assertEqual(qa.loose_text("Opening words<p>Then a paragraph.</p>"), ["Opening words"])

    def test_top_level_inline_tags_are_loose_too(self):
        # A caption set in italics at top level (things-as-they-are's shape) is
        # invisible to a bare-text-node scan, but sits outside any paragraph.
        self.assertEqual(
            qa.loose_text("<p>a</p><i>St. Paul, Asia and Europe.</i><p>b</p>"),
            ["St. Paul, Asia and Europe."],
        )
        self.assertEqual(qa.loose_text("<strong>Bold start</strong><p>b</p>"), ["Bold start"])

    def test_a_poem_joined_by_breaks_is_one_run(self):
        # The Pursuit of God shape: a loose <i>line<br/></i> run between blocks.
        html = (
            "<p>Before.</p><i>There is no holy service<br/></i><i>But hath its secret bliss:<br/></i>"
            "Yet, of all blessèd ministries,<br/>Is one so dear<p>After.</p>"
        )
        self.assertEqual(
            qa.loose_text(html),
            ["There is no holy service But hath its secret bliss: Yet, of all blessèd ministries, Is one so dear"],
        )

    def test_text_inside_a_block_is_not_loose(self):
        # Bare text inside a blockquote or list item is inside a block…
        self.assertEqual(qa.loose_text("<blockquote>Quoted <i>words</i></blockquote><ul><li>item</li></ul>"), [])
        # …and inline markup inside a paragraph never is.
        self.assertEqual(qa.loose_text("<p>One</p><p><em>Two</em> three</p>"), [])

    def test_text_after_hr_and_comment(self):
        self.assertEqual(qa.loose_text("<p>a</p><hr/>After the rule"), ["After the rule"])
        self.assertEqual(qa.loose_text("<p>a</p><!-- x -->After a comment"), ["After a comment"])

    def test_chapter_flag(self):
        self.assertIn("loose-text", qa.chapter_flags("T", 200, GOOD, f"<p>{GOOD}</p>Loose", False))
        self.assertNotIn("loose-text", qa.chapter_flags("T", 200, GOOD, f"<p>{GOOD}</p>", False))

    def test_snippet_is_capped(self):
        snip = qa.loose_snippet([("word " * 40).strip()])
        self.assertTrue(snip.endswith("…"))
        self.assertLessEqual(len(snip), qa.LOOSE_SNIPPET + 1)
        self.assertEqual(qa.loose_snippet(["short"]), "short")


class LengthBucketTests(TestCase):
    """`length_bucket` feeds the audit's chapter-length chart. Its flagged bars
    must hold exactly the chapters `chapter_flags` flags, or the chart and the
    Tiny / Giant checks beside it would disagree about the same chapters."""

    def test_edges_are_increasing_and_carry_both_thresholds(self):
        edges = qa.LENGTH_EDGES
        self.assertEqual(list(edges), sorted(set(edges)))
        self.assertIn(qa.TINY_MAX, edges)
        self.assertIn(qa.GIANT_MIN, edges)

    def test_boundaries(self):
        tiny_edge = qa.LENGTH_EDGES.index(qa.TINY_MAX)
        giant_edge = qa.LENGTH_EDGES.index(qa.GIANT_MIN)
        self.assertEqual(qa.length_bucket(1), 0)
        self.assertEqual(qa.length_bucket(qa.TINY_MAX - 1), tiny_edge)
        self.assertEqual(qa.length_bucket(qa.TINY_MAX), tiny_edge + 1)
        # Exactly GIANT_MIN is not giant: it closes the bar below the line.
        self.assertEqual(qa.length_bucket(qa.GIANT_MIN), giant_edge)
        self.assertEqual(qa.length_bucket(qa.GIANT_MIN + 1), giant_edge + 1)
        self.assertEqual(qa.length_bucket(10**6), len(qa.LENGTH_EDGES))

    def test_flagged_buckets_match_chapter_flags(self):
        # Located by edge, not by position, so moving a threshold can't break it.
        tiny_edge = qa.LENGTH_EDGES.index(qa.TINY_MAX)
        giant_edge = qa.LENGTH_EDGES.index(qa.GIANT_MIN)
        probes = {1, 10**6}
        for e in qa.LENGTH_EDGES:
            probes |= {e - 1, e, e + 1}
        for wc in sorted(probes):
            flags = qa.chapter_flags("Title", wc, "Body.", "<p>Body.</p>", False)
            b = qa.length_bucket(wc)
            self.assertEqual(b <= tiny_edge, "tiny" in flags, wc)
            self.assertEqual(b > giant_edge, "giant" in flags, wc)
