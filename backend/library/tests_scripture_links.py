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
