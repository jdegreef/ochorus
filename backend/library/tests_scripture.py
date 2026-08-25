"""Scripture: reference detection in prose, the citation index built from it, and
fetching verse text from the Bible API in a target language.

A bad Bible code does not fail — it omits scripture silently — so the checks
here are the ones that notice."""

from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .models import (
    Author,
    Book,
    Chapter,
    Sermon,
)
from .search import search_library
from .translation import (
    Ref,
    fetch_chapter,
)


class ScriptureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_annotate_wraps_valid_references_only(self):
        from library.scripture import annotate_references

        html = "<p>As John 3:16 says, and see Romans 8:28. But Room 3:16 is not.</p>"
        out = annotate_references(html)
        self.assertIn('<a class="scripture-ref" data-ref="John 3:16">John 3:16</a>', out)
        self.assertIn('data-ref="Romans 8:28"', out)
        self.assertNotIn('data-ref="Room 3:16"', out)  # not a real book
        self.assertIn("Room 3:16 is not", out)

    def test_annotate_skips_attributes_and_existing_anchors(self):
        from library.scripture import annotate_references

        # Reference inside an existing <a> must not be double-wrapped.
        html = '<p><a href="/x">John 3:16</a></p>'
        self.assertEqual(annotate_references(html).count("<a"), 1)
        self.assertEqual(annotate_references(""), "")

    def test_lookup_endpoint_returns_asv_text(self):
        res = self.client.get("/api/library/scripture/?ref=John 3:16")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["reference"], "John 3:16")
        self.assertEqual(res.data["verses"][0]["number"], 16)
        self.assertIn("God so loved the world", res.data["verses"][0]["text"])
        self.assertEqual(res.data["version"], "American Standard Version")

    def test_lookup_endpoint_range(self):
        res = self.client.get("/api/library/scripture/?ref=Romans 8:28-29")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["verses"]), 2)

    def test_lookup_endpoint_bad_and_missing(self):
        self.assertEqual(self.client.get("/api/library/scripture/").status_code, 400)
        self.assertEqual(
            self.client.get("/api/library/scripture/?ref=Nope 1:1").status_code, 404
        )

    def test_sermon_body_references_are_annotated(self):
        author = Author.objects.create(slug="cs-scrip", name="Charles Spurgeon")
        Sermon.objects.create(
            author=author,
            slug="faith-and-life",
            language="en",
            title="Faith and Life",
            body_html="<p>Consider Hebrews 11:1 and take heart.</p>",
            sort_order=1,
        )
        res = self.client.get("/api/library/sermons/faith-and-life/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            '<a class="scripture-ref" data-ref="Hebrews 11:1">Hebrews 11:1</a>',
            res.data["body_html"],
        )
        # The reader header needs the author's portrait.
        self.assertIn("author_photo", res.data)


class CitationIndexTests(TestCase):
    def _book(self, slug="cite-book", language="en"):
        author = Author.objects.create(slug=f"a-{slug}", name="A")
        return Book.objects.create(author=author, slug=slug, language=language, title=slug)

    def test_extract_citations_spans_and_dedupe(self):
        from .scripture import extract_citations

        cites = extract_citations(
            "See John 3:16 and again John 3:16; also 1 Cor 13:4-7. Room 5:1 is not a book."
        )
        by_ref = {c["ref"]: c for c in cites}
        self.assertEqual(set(by_ref), {"John 3:16", "1 Cor 13:4-7"})
        self.assertEqual(by_ref["John 3:16"]["count"], 2)
        j = by_ref["John 3:16"]
        self.assertEqual(j["start"], j["end"])  # single verse
        c = by_ref["1 Cor 13:4-7"]
        self.assertEqual(c["end"] - c["start"], 3)  # four-verse span

    def test_index_command_incremental_and_reindex_on_save(self):

        book = self._book()
        ch = Chapter.objects.create(
            book=book, order=1, title="T", body_html="<p>As John 3:16 says.</p>"
        )
        call_command("index_citations")
        self.assertEqual(ch.citations.count(), 1)
        stamped = Chapter.objects.get(pk=ch.pk).citations_indexed_at
        self.assertIsNotNone(stamped)

        # Second run touches nothing (stamp set).
        call_command("index_citations")
        self.assertEqual(
            Chapter.objects.get(pk=ch.pk).citations_indexed_at, stamped
        )

        # A body edit clears the stamp; next run re-indexes.
        ch.refresh_from_db()
        ch.body_html = "<p>Now Romans 8:28 instead.</p>"
        ch.save()
        self.assertIsNone(Chapter.objects.get(pk=ch.pk).citations_indexed_at)
        call_command("index_citations")
        refs = list(ch.citations.values_list("ref_text", flat=True))
        self.assertEqual(refs, ["Romans 8:28"])

    def test_search_finds_citing_chapters_by_overlap(self):

        book = self._book()
        Chapter.objects.create(
            book=book, order=1, title="Exact",
            body_html="<p>For God so loved the world (John 3:16).</p>",
        )
        Chapter.objects.create(
            book=book, order=2, title="Range",
            body_html="<p>The whole discourse (John 3:1-21) rewards study.</p>",
        )
        Chapter.objects.create(
            book=book, order=3, title="Other",
            body_html="<p>Psalm 23:1 comforts.</p>",
        )
        # Unpublished + wrong-language rows must not leak into results.
        hidden = self._book(slug="hidden-book")
        hidden.is_published = False
        hidden.save()
        Chapter.objects.create(
            book=hidden, order=1, title="H", body_html="<p>John 3:16 too.</p>"
        )
        lg = self._book(slug="cite-book-lg", language="lg")
        Chapter.objects.create(
            book=lg, order=1, title="L", body_html="<p>John 3:16 in lg body.</p>"
        )
        call_command("index_citations")


        results = search_library("John 3:16", "en")
        chapter_hits = [
            (r["book_slug"], r["chapter_order"])
            for r in results
            if r["type"] == "chapter"
        ]
        self.assertIn(("cite-book", 1), chapter_hits)
        self.assertIn(("cite-book", 2), chapter_hits)  # range overlap
        self.assertNotIn(("cite-book", 3), chapter_hits)
        self.assertNotIn(("hidden-book", 1), chapter_hits)
        self.assertNotIn(("cite-book-lg", 1), chapter_hits)
        # exact citation ranks before the wide range, snippet is marker-wrapped
        exact = next(r for r in results if r.get("chapter_order") == 1)
        self.assertIn("⟦John 3:16⟧", exact["snippet"])
        self.assertLess(
            chapter_hits.index(("cite-book", 1)), chapter_hits.index(("cite-book", 2))
        )

    def test_multi_reference_query_uses_exact_intersection(self):
        """"John 3:16 and Romans 8:28" must not match everything in between."""

        book = self._book(slug="span-book")
        Chapter.objects.create(
            book=book, order=1, title="True1",
            body_html="<p>See John 3:16 for the promise.</p>",
        )
        Chapter.objects.create(
            book=book, order=2, title="True2",
            body_html="<p>And Romans 8:28 for the assurance.</p>",
        )
        # Falls inside min..max of the two references but overlaps neither.
        Chapter.objects.create(
            book=book, order=3, title="Between",
            body_html="<p>Acts 2:38 stands between them.</p>",
        )
        call_command("index_citations")


        hits = [
            (r["book_slug"], r["chapter_order"])
            for r in search_library("John 3:16 and Romans 8:28", "en")
            if r["type"] == "chapter"
        ]
        self.assertIn(("span-book", 1), hits)
        self.assertIn(("span-book", 2), hits)
        self.assertNotIn(("span-book", 3), hits)

    def test_full_book_name_with_period_is_not_whole_book(self):
        """"Matthew. 1:23" must index one verse, not 28 chapters."""
        from .scripture import extract_citations

        cites = extract_citations("the words in Matthew. 1:23, well known.")
        self.assertEqual(len(cites), 1)
        self.assertEqual(cites[0]["start"], cites[0]["end"])  # single verse
        self.assertEqual(cites[0]["start"], 40001023)

    def test_bare_book_name_skips_citation_lead(self):
        """"Matthew" is a text query, not a whole-book citation sweep."""

        book = self._book(slug="matt-citer")
        Chapter.objects.create(
            book=book, order=1, title="C",
            body_html="<p>Matthew 5:3 opens the sermon.</p>",
        )
        call_command("index_citations")

        from .search import _base_querysets, _scripture_chapter_hits

        eligible = _base_querysets("en")["chapter"]
        self.assertEqual(_scripture_chapter_hits("Matthew", eligible), [])
        self.assertEqual(len(_scripture_chapter_hits("Matthew 5:3", eligible)), 1)


class FetchVerseTextTests(SimpleTestCase):
    """`fetch_verse_text` — the guard that keeps a shelf's verse authentic.

    A topic quotes one verse verbatim, so the wording must come from that
    language's Bible. Every failure path must return "" so the caller ships no
    verse rather than a paraphrase (translate_topic warns and moves on).
    """

    def _chapter(self, verses):
        return {"reference": "Jeremías 33", "verses": verses}

    def test_returns_the_requested_verse(self):
        from library import translation as m

        with mock.patch.object(
            m,
            "fetch_chapter",
            return_value=self._chapter(
                [
                    {"number": 2, "text": "Asi dice Jehová..."},
                    {"number": 3, "text": "Clama a mí, y te responderé."},
                ]
            ),
        ):
            self.assertEqual(
                m.fetch_verse_text("rv1858", "Jeremiah 33:3"),
                "Clama a mí, y te responderé.",
            )

    def test_blank_when_the_verse_is_not_in_the_chapter(self):
        from library import translation as m

        with mock.patch.object(
            m, "fetch_chapter", return_value=self._chapter([{"number": 1, "text": "x"}])
        ):
            self.assertEqual(m.fetch_verse_text("rv1858", "Jeremiah 33:3"), "")

    def test_blank_on_an_unparseable_or_missing_reference(self):
        from library import translation as m

        with mock.patch.object(m, "fetch_chapter", return_value=None) as fetch:
            self.assertEqual(m.fetch_verse_text("rv1858", "not a reference"), "")
            fetch.assert_not_called()  # nothing to fetch
            self.assertEqual(m.fetch_verse_text("rv1858", ""), "")

    def test_blank_when_the_api_fails(self):
        from library import translation as m

        with mock.patch.object(m, "fetch_chapter", return_value=None):
            self.assertEqual(m.fetch_verse_text("rv1858", "Jeremiah 33:3"), "")


class ScriptureFetchTests(TestCase):
    """fetch_chapter must never cache a TRANSIENT failure as a permanent miss —
    that is how one dropped request silently strips scripture from every later
    chapter citing the same passage (review #28). Only a definitive answer (the
    verses, or a 404) is cached; a persistent transient failure raises."""

    def setUp(self):
        from library import translation

        translation._verse_cache.clear()
        self.addCleanup(translation._verse_cache.clear)

    def _resp(self, status=200, payload=None):
        r = mock.Mock()
        r.status_code = status
        r.ok = 200 <= status < 300
        r.json.return_value = {} if payload is None else payload
        return r

    def test_404_is_a_definitive_miss_and_is_cached(self):
        with mock.patch(
            "library.translation.requests.get", return_value=self._resp(404)
        ) as get:
            self.assertIsNone(fetch_chapter("rv1858", Ref("JHN", 3)))
            self.assertIsNone(fetch_chapter("rv1858", Ref("JHN", 3)))  # served from cache
        self.assertEqual(get.call_count, 1)

    def test_success_returns_and_caches(self):
        payload = {"reference": "John 3", "verses": [{"number": 16, "text": "For God…"}]}
        with mock.patch(
            "library.translation.requests.get", return_value=self._resp(200, payload)
        ) as get:
            self.assertEqual(fetch_chapter("rv1858", Ref("JHN", 3)), payload)
            fetch_chapter("rv1858", Ref("JHN", 3))
        self.assertEqual(get.call_count, 1)

    def test_transient_failure_retries_then_raises_and_is_not_cached(self):
        import requests

        from library.translation import _FETCH_ATTEMPTS, ScriptureUnavailable

        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get",
            side_effect=requests.RequestException("timeout"),
        ) as get:
            with self.assertRaises(ScriptureUnavailable):
                fetch_chapter("rv1858", Ref("ROM", 8))
        self.assertEqual(get.call_count, _FETCH_ATTEMPTS)

        # NOT cached: once the API recovers, the same passage fetches cleanly.
        good = self._resp(200, {"verses": [{"number": 1, "text": "x"}]})
        with mock.patch("library.translation.requests.get", return_value=good):
            self.assertTrue(fetch_chapter("rv1858", Ref("ROM", 8)).get("verses"))

    def test_transient_then_success_is_retried(self):
        import requests

        good = self._resp(200, {"verses": [{"number": 1, "text": "x"}]})
        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get",
            side_effect=[requests.RequestException("blip"), good],
        ) as get:
            self.assertTrue(fetch_chapter("rv1858", Ref("PSA", 23)).get("verses"))
        self.assertEqual(get.call_count, 2)

    def test_5xx_is_treated_as_transient(self):
        from library.translation import _FETCH_ATTEMPTS, ScriptureUnavailable

        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get", return_value=self._resp(503)
        ) as get:
            with self.assertRaises(ScriptureUnavailable):
                fetch_chapter("rv1858", Ref("ISA", 55))
        self.assertEqual(get.call_count, _FETCH_ATTEMPTS)
