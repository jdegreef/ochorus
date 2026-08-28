"""The reverse scripture index — which passages cite a verse, and which get URLs.

The behaviour worth pinning here is not "does it find citations" (search has
done that since citations were indexed) but the RULES that decide what becomes
a public page: the two floors, the English-only scope, and the honesty of the
counts a page publishes about itself.
"""

from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter
from .scripture_graph import (
    CHAPTER_FLOOR,
    VERSE_FLOOR,
    book_from_slug,
    book_slug,
    qualifying_pages,
)


def cite(book, order, ref, *, body=None):
    """A chapter whose prose cites `ref`, indexed the way the deploy indexes it."""
    Chapter.objects.create(
        book=book,
        order=order,
        title=f"Chapter {order}",
        body_html=f"<p>{body or 'A passage that dwells on'} {ref} at some length.</p>",
    )


class PageListTests(TestCase):
    """`qualifying_pages` — the single list the API, the build and the sitemap share."""

    def setUp(self):
        self.author = Author.objects.create(slug="a", name="A Writer")
        self.book = Book.objects.create(
            author=self.author, slug="w", language="en", title="A Work"
        )

    def _index(self):
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def test_a_verse_under_the_floor_gets_no_page(self):
        for i in range(VERSE_FLOOR - 1):
            cite(self.book, i + 1, "Romans 8:28")
        self._index()
        verses = [p for p in qualifying_pages() if p["verse"] == 28]
        self.assertEqual(verses, [])

    def test_a_verse_at_the_floor_gets_one(self):
        for i in range(VERSE_FLOOR):
            cite(self.book, i + 1, "Romans 8:28")
        self._index()
        page = next(p for p in qualifying_pages() if p["verse"] == 28)
        self.assertEqual((page["book"], page["chapter"]), ("romans", 8))
        self.assertEqual(page["citing_count"], VERSE_FLOOR)

    def test_one_chapter_citing_a_verse_many_times_is_still_one_voice(self):
        # The floor counts DISTINCT chapters. Repetition inside a single
        # chapter is one writer returning to a text, and letting it clear the
        # floor alone would publish a page nobody else in the library cites.
        cite(
            self.book,
            1,
            "Romans 8:28",
            body="Romans 8:28. Again Romans 8:28. And once more Romans 8:28. Yet again Romans 8:28. Romans 8:28",
        )
        self._index()
        self.assertEqual([p for p in qualifying_pages() if p["verse"] == 28], [])

    def test_a_chapter_page_needs_fewer_citations_than_a_verse_page(self):
        # The floors differ on purpose: a Bible-chapter page aggregates every
        # verse under it and stays substantial where a verse page would not.
        self.assertLess(CHAPTER_FLOOR, VERSE_FLOOR)
        for i in range(CHAPTER_FLOOR):
            cite(self.book, i + 1, f"Romans 8:{i + 1}")
        self._index()
        pages = qualifying_pages()
        self.assertTrue(any(p["chapter"] == 8 and p["verse"] is None for p in pages))
        self.assertFalse(any(p["verse"] for p in pages))

    def test_non_english_chapters_are_not_counted(self):
        # extract_citations validates against English book names, so a Spanish
        # edition indexes almost nothing — but the English text spliced into
        # one would otherwise vote for an English page from a locale that
        # cannot have one.
        es = Book.objects.create(
            author=self.author, slug="w", language="es", title="Una obra"
        )
        for i in range(VERSE_FLOOR + 2):
            cite(es, i + 1, "Romans 8:28")
        self._index()
        self.assertEqual([p for p in qualifying_pages() if p["verse"] == 28], [])

    def test_unpublished_books_are_not_counted(self):
        hidden = Book.objects.create(
            author=self.author,
            slug="h",
            language="en",
            title="Hidden",
            is_published=False,
        )
        for i in range(VERSE_FLOOR + 2):
            cite(hidden, i + 1, "Romans 8:28")
        self._index()
        self.assertEqual([p for p in qualifying_pages() if p["verse"] == 28], [])


class ChapterScriptureRowTests(TestCase):
    """The chapter page's scripture index — and that it never links to a 404."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        self.book = Book.objects.create(
            author=author, slug="w", language="en", title="A Work"
        )
        # Enough citing chapters that Romans 8:28 clears the VERSE floor, which
        # also clears the (lower) chapter floor for Romans 8.
        for i in range(VERSE_FLOOR + 1):
            cite(self.book, i + 1, "Romans 8:28")
        # Cited once — under both floors, so it has no page to link to.
        # Obadiah is a one-chapter book, so the canonical display form drops
        # the chapter: "Obadiah 1:3" is rendered "Obadiah 3".
        cite(self.book, 90, "Obadiah 1:3")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def _row(self, order=1, slug="w"):
        res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/")
        self.assertEqual(res.status_code, 200)
        return res.data["scripture_refs"]

    def test_a_chapter_lists_the_passages_it_treats(self):
        self.assertEqual([r["ref"] for r in self._row()], ["Romans 8:28"])

    def test_a_reference_with_a_page_carries_where_to_find_it(self):
        row = self._row()
        self.assertEqual(
            row[0]["page"], {"book": "romans", "chapter": 8, "verse": 28}
        )

    def test_a_reference_under_the_floor_carries_no_page(self):
        # The chip still shows — the passage IS treated here — but it links
        # nowhere, because the page list deliberately never built one.
        row = self._row(order=90)
        self.assertEqual([r["ref"] for r in row], ["Obadiah 3"])
        self.assertIsNone(row[0]["page"])

    def test_every_page_the_row_offers_really_serves(self):
        """The guard that matters: a chip must never be a dead link.

        This is the same failure that killed the prerender build once already,
        one level along — there the chapter page linked a verse the floor had
        withheld, here it would be a chip doing it.
        """
        for order in (1, 90):
            for entry in self._row(order=order):
                page = entry["page"]
                if page is None:
                    continue
                path = f"/api/library/scripture/{page['book']}/{page['chapter']}/"
                if page["verse"]:
                    path += f"{page['verse']}/"
                with self.subTest(ref=entry["ref"]):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_pages_for_agrees_with_the_published_page_list(self):
        """`pages_for` and `qualifying_pages` share `bucket` — prove it holds.

        Two implementations of "does this page exist" would drift, and the drift
        is silent: chips would point at pages the sitemap never advertised and
        the build never rendered.
        """
        from .scripture_graph import pages_for

        published = {
            (p["book"], p["chapter"], p["verse"]) for p in qualifying_pages()
        }
        for ref, page in pages_for(["Romans 8:28", "Obadiah 1:3", "Romans 8:1"]).items():
            with self.subTest(ref=ref):
                if page is None:
                    continue
                self.assertIn(
                    (page["book"], page["chapter"], page["verse"]), published
                )

    def test_it_resolves_one_query_however_many_references(self):
        # Asking per reference is ten thousand queries across a build of 1,264
        # chapter pages, which is why this is written as one range filter.
        from .scripture_graph import pages_for

        with self.assertNumQueries(1):
            pages_for(["Romans 8:28", "John 3:16", "Psalm 23:1", "Obadiah 1:3"])

    def test_a_translated_chapter_has_no_row(self):
        # Citations parse against English book names, and the pages they would
        # point at are English. A Spanish chapter with a stray English string
        # must not present two references as its scripture index.
        es = Book.objects.create(
            author=self.book.author, slug="w", language="es", title="Una obra"
        )
        cite(es, 1, "Romans 8:28")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        res = self.client.get("/api/library/books/w/chapters/1/?language=es")
        self.assertEqual(res.data["scripture_refs"], [])

    def test_a_chapter_citing_nothing_has_an_empty_row(self):
        Chapter.objects.create(
            book=self.book, order=70, title="Quiet", body_html="<p>No references.</p>"
        )
        self.assertEqual(self._row(order=70), [])


class BookSlugTests(TestCase):
    def test_slugs_are_readable_and_round_trip(self):
        # The URL is the name people search, not the USFM code.
        import pythonbible as bible

        self.assertEqual(book_slug(bible.Book.ROMANS), "romans")
        self.assertEqual(book_slug(bible.Book.CORINTHIANS_1), "1-corinthians")
        for b in bible.Book:
            self.assertEqual(book_from_slug(book_slug(b)), b)

    def test_an_unknown_slug_resolves_to_nothing(self):
        self.assertIsNone(book_from_slug("st-hubbins"))


class GraphViewTests(TestCase):
    """The page itself: what it serves, what it refuses, and what it claims."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        self.book = Book.objects.create(
            author=author, slug="w", language="en", title="A Work"
        )
        for i in range(VERSE_FLOOR + 1):
            cite(self.book, i + 1, "Romans 8:28")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def test_a_verse_page_serves_its_text_and_its_passages(self):
        res = self.client.get("/api/library/scripture/romans/8/28/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["reference"], "Romans 8:28")
        self.assertIn("work together for good", res.data["text"])
        self.assertEqual(len(res.data["passages"]), VERSE_FLOOR + 1)
        self.assertEqual(res.data["passages"][0]["author_name"], "A Writer")

    def test_the_excerpt_is_centred_on_the_citation(self):
        res = self.client.get("/api/library/scripture/romans/8/28/")
        self.assertIn("Romans 8:28", res.data["passages"][0]["excerpt"])

    def test_a_chapter_page_lists_the_verses_the_library_treats(self):
        res = self.client.get("/api/library/scripture/romans/8/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([v["number"] for v in res.data["verses"]], [28])

    def test_citing_count_is_the_true_total_not_the_page_size(self):
        # It was len(passages), which is capped — so a passage 113 chapters
        # treated reported 40, understating its own evidence and contradicting
        # the count the page list published for the same reference.
        from .scripture_graph import MAX_PASSAGES

        for i in range(MAX_PASSAGES + 5):
            cite(self.book, 100 + i, "Romans 8:28")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        res = self.client.get("/api/library/scripture/romans/8/28/")
        self.assertEqual(res.data["passages_shown"], MAX_PASSAGES)
        self.assertGreater(res.data["citing_count"], MAX_PASSAGES)

    def test_a_whole_chapter_citation_does_not_vote_for_each_verse(self):
        # "Romans 8" says nothing about which verse a writer stopped at, so it
        # is evidence for the chapter page and for no verse under it. Letting it
        # count per-verse would have every verse of a much-cited chapter look
        # individually treated.
        for i in range(4):
            cite(self.book, 200 + i, "Romans 8:1-39")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        res = self.client.get("/api/library/scripture/romans/8/")
        by_number = {v["number"]: v["citing_count"] for v in res.data["verses"]}
        # Verse 28 keeps only the chapters that cite it SPECIFICALLY.
        self.assertEqual(by_number.get(28), VERSE_FLOOR + 1)
        self.assertNotIn(1, by_number)
        # The chapter page itself still counts them — that is what they cite.
        self.assertEqual(res.data["citing_count"], VERSE_FLOOR + 5)

    def test_a_verse_under_the_floor_is_marked_as_having_no_page(self):
        # The chapter page links its verses, and a link to a verse the floor
        # withheld is a 404 — which is exactly how the prerender build died on
        # /scripture/genesis/1/27/. The server owns the floor, so the server
        # says what is linkable.
        cite(self.book, 300, "Romans 8:1")  # one citing chapter, far under
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        res = self.client.get("/api/library/scripture/romans/8/")
        by_number = {v["number"]: v for v in res.data["verses"]}
        self.assertFalse(by_number[1]["has_page"])
        self.assertTrue(by_number[28]["has_page"])

    def test_every_linkable_verse_really_serves(self):
        # The guard that matters: whatever the chapter page offers as a link
        # must resolve, or the build breaks on it.
        res = self.client.get("/api/library/scripture/romans/8/")
        for v in res.data["verses"]:
            if v["has_page"]:
                with self.subTest(verse=v["number"]):
                    self.assertEqual(
                        self.client.get(
                            f"/api/library/scripture/romans/8/{v['number']}/"
                        ).status_code,
                        200,
                    )

    def test_the_verse_list_is_ordered_by_how_many_treat_it(self):
        res = self.client.get("/api/library/scripture/romans/8/")
        counts = [v["citing_count"] for v in res.data["verses"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_a_reference_under_the_floor_is_refused(self):
        # Not an empty page: a hand-typed URL must not reach the thin page the
        # page list deliberately withheld.
        self.assertEqual(
            self.client.get("/api/library/scripture/romans/8/29/").status_code, 404
        )

    def test_an_unreal_reference_is_refused(self):
        for path in ("romans/99/", "romans/8/99/", "st-hubbins/1/"):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(f"/api/library/scripture/{path}").status_code, 404
                )

    def test_the_page_list_endpoint_matches_the_pages_that_serve(self):
        listed = self.client.get("/api/library/scripture/pages/").data
        self.assertTrue(listed)
        for page in listed:
            path = f"/api/library/scripture/{page['book']}/{page['chapter']}/"
            if page["verse"]:
                path += f"{page['verse']}/"
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
