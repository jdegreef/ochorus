"""Linking inline Scripture references to their reverse-index pages.

`annotate_references` has always made a reference a popover anchor; these check
the new second job — giving the anchor a crawlable `href` when, and only when,
its Bible chapter cleared the scripture-graph floor and a page was built. The
floor itself is `pages_for`'s, tested in tests_scripture_graph / tests_book_
scripture; here it is mocked, so these stay fast and DB-free and check exactly
the new wiring: candidate collection, URL shape, and anchor emission.
"""

from unittest import mock

from django.test import SimpleTestCase

from .scripture import annotate_references, reference_candidates


class ReferenceCandidateTests(SimpleTestCase):
    def test_collects_distinct_raw_candidates_in_order(self):
        html = "<p>See John 3:16 and Romans 8:28, then John 3:16 again.</p>"
        self.assertEqual(reference_candidates(html), ["John 3:16", "Romans 8:28"])

    def test_ignores_non_references_and_existing_anchors(self):
        html = '<p>Room 3:16 is not, but <a href="/x">John 3:16</a> is already linked.</p>'
        # Room 3:16 is not a book; the John 3:16 inside an <a> is skipped.
        self.assertEqual(reference_candidates(html), [])

    def test_empty_and_digitless(self):
        self.assertEqual(reference_candidates(""), [])
        self.assertEqual(reference_candidates("<p>no numbers here</p>"), [])


class AnnotateLinkTests(SimpleTestCase):
    def test_adds_href_only_for_mapped_candidates(self):
        html = "<p>John 3:16 and Romans 8:28.</p>"
        links = {"John 3:16": "/scripture/john/3/"}
        out = annotate_references(html, links=links)
        # Mapped -> real link, with the popover attrs kept.
        self.assertIn(
            '<a class="scripture-ref" href="/scripture/john/3/" data-ref="John 3:16">John 3:16</a>',
            out,
        )
        # Unmapped -> popover-only, no href.
        self.assertIn('<a class="scripture-ref" data-ref="Romans 8:28">Romans 8:28</a>', out)
        self.assertNotIn('href="/scripture/romans', out)

    def test_no_links_is_unchanged_behaviour(self):
        html = "<p>John 3:16.</p>"
        self.assertEqual(annotate_references(html), annotate_references(html, links=None))
        self.assertNotIn("href=", annotate_references(html))


class ScriptureLinksTests(SimpleTestCase):
    """`scripture_links` turns `pages_for`'s page dicts into URLs."""

    def _run(self, pages):
        # pages_for is the floor resolver; mock it so these are DB-free.
        from . import scripture_graph

        with mock.patch.object(scripture_graph, "pages_for", return_value=pages):
            return scripture_graph.scripture_links(list(pages.keys()))

    def test_chapter_page_url(self):
        got = self._run({"Romans 8:28": {"book": "romans", "chapter": 8, "verse": None}})
        self.assertEqual(got, {"Romans 8:28": "/scripture/romans/8/"})

    def test_verse_page_url(self):
        got = self._run({"John 3:16": {"book": "john", "chapter": 3, "verse": 16}})
        self.assertEqual(got, {"John 3:16": "/scripture/john/3/16/"})

    def test_unbuilt_page_is_omitted(self):
        got = self._run({"Obadiah 1:1": None})
        self.assertEqual(got, {})


class LinkScriptureWiringTests(SimpleTestCase):
    """`serializers._link_scripture` composes the pieces end to end."""

    def test_body_gets_href_for_a_built_page_only(self):
        from . import scripture_graph
        from .serializers import _link_scripture

        html = "<p>On John 3:16 and also Obadiah 1:1.</p>"
        pages = {
            "John 3:16": {"book": "john", "chapter": 3, "verse": 16},
            "Obadiah 1:1": None,
        }
        with mock.patch.object(scripture_graph, "pages_for", return_value=pages):
            out = _link_scripture(html)
        self.assertIn('href="/scripture/john/3/16/" data-ref="John 3:16"', out)
        self.assertIn('data-ref="Obadiah 1:1"', out)
        self.assertNotIn("scripture/obadiah", out)


class ChapterOnlyCitationTests(SimpleTestCase):
    """Whole-chapter citations ("Romans 8", "John 17"), which the chapter:verse
    pattern never matched. Linked when their page exists; otherwise untouched."""

    def test_collected_as_candidates(self):
        html = "<p>Read Romans 8, then John 17 and 1 John 3; Psalm 23 too.</p>"
        self.assertEqual(
            reference_candidates(html), ["Romans 8", "John 17", "1 John 3", "Psalm 23"]
        )

    def test_linked_when_the_page_exists(self):
        html = "<p>The prayer of John 17 completes the picture.</p>"
        out = annotate_references(html, links={"John 17": "/scripture/john/17/"})
        self.assertIn(
            '<a class="scripture-ref" href="/scripture/john/17/" data-ref="John 17">John 17</a>',
            out,
        )

    def test_left_as_text_without_a_page(self):
        html = "<p>The prayer of John 17 completes the picture.</p>"
        self.assertEqual(annotate_references(html), html)
        self.assertEqual(annotate_references(html, links={}), html)

    def test_verse_citation_wins_over_its_chapter(self):
        # "Romans 8:28" is the verse citation, never "Romans 8" followed by junk.
        html = "<p>Romans 8:28 and Romans 8. 3 are verse citations.</p>"
        self.assertEqual(reference_candidates(html), ["Romans 8:28", "Romans 8. 3"])

    def test_rejects_non_references(self):
        # A chapter the book doesn't have, an abbreviation, a roman numeral,
        # a lower-case word, and a name that is not a book.
        html = "<p>John 25, Rom 8, John xvii, the job 5 days, Peterson 3.</p>"
        self.assertEqual(reference_candidates(html), [])

    def test_single_chapter_book_number_is_a_verse(self):
        # Jude, Philemon, Obadiah… are cited by verse alone: "Jude 24" is 1:24.
        self.assertEqual(reference_candidates("<p>(Jude 24)</p>"), ["Jude 24"])

    def test_not_wrapped_inside_an_existing_link(self):
        html = '<p><a href="/x">Romans 8</a></p>'
        self.assertEqual(reference_candidates(html), [])
        self.assertEqual(annotate_references(html, links={"Romans 8": "/s/"}), html)


class LinkedOnlyTests(SimpleTestCase):
    """`linked_only` — for a surface with no popover (an author bio)."""

    def test_wraps_only_references_with_a_page(self):
        html = "<p>John 3:16 and Romans 8:28.</p>"
        out = annotate_references(
            html, links={"John 3:16": "/scripture/john/3/16/"}, linked_only=True
        )
        self.assertIn('href="/scripture/john/3/16/" data-ref="John 3:16"', out)
        self.assertNotIn('data-ref="Romans 8:28"', out)
        self.assertIn("Romans 8:28.", out)

    def test_bio_html_is_link_only(self):
        from . import scripture_graph
        from .serializers import _link_scripture

        html = "<p>He preached on John 3:16 and Obadiah 1:1.</p>"
        pages = {
            "John 3:16": {"book": "john", "chapter": 3, "verse": 16},
            "Obadiah 1:1": None,
        }
        with mock.patch.object(scripture_graph, "pages_for", return_value=pages):
            out = _link_scripture(html, linked_only=True)
        self.assertIn('href="/scripture/john/3/16/"', out)
        self.assertNotIn('data-ref="Obadiah 1:1"', out)
