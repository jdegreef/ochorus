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
