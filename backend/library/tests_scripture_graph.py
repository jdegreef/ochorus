"""The reverse scripture index — which passages cite a verse, and which get URLs.

The behaviour worth pinning here is not "does it find citations" (search has
done that since citations were indexed) but the RULES that decide what becomes
a public page: the two floors, the English-only scope, and the honesty of the
counts a page publishes about itself.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Author, Book, Chapter
from .scripture_graph import (
    CHAPTER_FLOOR,
    VERSE_FLOOR,
    book_from_slug,
    book_slug,
    current_pages,
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

    def test_a_page_is_dated_by_the_newest_book_it_quotes(self):
        # `updated_at` is the sitemap's <lastmod>: the newest edit among the
        # books whose chapters make up the page.
        other = Book.objects.create(author=self.author, slug="v", language="en", title="Another")
        for i in range(VERSE_FLOOR - 1):
            cite(self.book, i + 1, "Romans 8:28")
        cite(other, 1, "Romans 8:28")
        self._index()
        Book.objects.filter(pk=other.pk).update(updated_at=self.book.updated_at.replace(year=2099))
        page = next(p for p in qualifying_pages() if p["verse"] == 28)
        self.assertEqual(page["updated_at"].year, 2099)

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


class ChapterNeighbourTests(TestCase):
    """A chapter page names its neighbours among the chapter pages that exist."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        book = Book.objects.create(author=author, slug="w", language="en", title="A Work")
        # Three chapter pages in Bible order (Genesis 1, Romans 8, Revelation 21)
        # with Romans 9 cited once — under the floor, so it is no neighbour.
        order = 0
        for ref in ("Genesis 1:1", "Romans 8:28", "Revelation 21:4"):
            for _ in range(CHAPTER_FLOOR):
                order += 1
                cite(book, order, ref)
        cite(book, order + 1, "Romans 9:1")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def _nav(self, path):
        data = self.client.get(f"/api/library/scripture/{path}").data
        return data["prev"], data["next"]

    def test_neighbours_are_the_adjacent_qualifying_chapters(self):
        prev, nxt = self._nav("romans/8/")
        self.assertEqual(prev, {"book": "genesis", "book_title": "Genesis", "chapter": 1})
        self.assertEqual(nxt["book"], "revelation")
        self.assertEqual(nxt["chapter"], 21)

    def test_the_ends_have_no_neighbour(self):
        self.assertIsNone(self._nav("genesis/1/")[0])
        self.assertIsNone(self._nav("revelation/21/")[1])

    def test_a_verse_page_carries_no_chapter_nav(self):
        for i in range(VERSE_FLOOR):
            cite(Book.objects.get(slug="w"), 100 + i, "Romans 8:28")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        data = self.client.get("/api/library/scripture/romans/8/28/").data
        self.assertNotIn("prev", data)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class CurrentPagesCacheTests(TestCase):
    """The page list is computed once per content revision, and again after one."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        author = Author.objects.create(slug="a", name="A Writer")
        self.book = Book.objects.create(author=author, slug="w", language="en", title="A Work")
        for i in range(CHAPTER_FLOOR):
            cite(self.book, i + 1, "Romans 8:28")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def test_reused_within_a_revision_and_recomputed_after_a_bump(self):
        from unittest import mock

        from . import scripture_graph
        from .models import ContentRevision

        with mock.patch.object(
            scripture_graph, "qualifying_pages", wraps=scripture_graph.qualifying_pages
        ) as computed:
            first = current_pages()
            self.assertEqual(current_pages(), first)
            self.assertEqual(computed.call_count, 1)
            ContentRevision.bump()
            current_pages()
            self.assertEqual(computed.call_count, 2)


class BookViewTests(TestCase):
    """The /scripture/<book>/ page: one Bible book across the library."""

    def setUp(self):
        self.client = APIClient()
        murray = Author.objects.create(slug="murray", name="Andrew Murray")
        bunyan = Author.objects.create(slug="bunyan", name="John Bunyan")
        self.big = Book.objects.create(author=murray, slug="big", language="en", title="Big")
        small = Book.objects.create(author=bunyan, slug="small", language="en", title="Small")
        for i in range(VERSE_FLOOR + 1):
            cite(self.big, i + 1, "Romans 8:28")
        # One chapter citing two Romans chapters: one passage, not two.
        cite(small, 1, "Romans 5:8", body="Compare Romans 8:28 with")
        for i in range(CHAPTER_FLOOR):
            cite(small, i + 2, "Romans 5:8")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def get(self, slug):
        return self.client.get(f"/api/library/scripture/{slug}/")

    def test_a_book_with_chapter_pages_is_served(self):
        res = self.get("romans")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["book"]["title"], "Romans")
        self.assertEqual([c["chapter"] for c in res.data["chapters"]], [5, 8])

    def test_citing_count_counts_each_passage_once(self):
        # 6 chapters in Big + 4 in Small = 10, though Small's first chapter
        # cites both Romans 5 and Romans 8.
        res = self.get("romans")
        self.assertEqual(res.data["citing_count"], VERSE_FLOOR + 1 + CHAPTER_FLOOR + 1)
        self.assertEqual(res.data["books_count"], 2)

    def test_top_books_are_ranked_by_citing_chapters(self):
        top = self.get("romans").data["top_books"]
        self.assertEqual([b["slug"] for b in top], ["big", "small"])
        self.assertEqual(top[0]["author_name"], "Andrew Murray")
        self.assertEqual(top[0]["citing_count"], VERSE_FLOOR + 1)

    def test_one_excerpt_per_top_work_at_its_narrowest_citation(self):
        passages = self.get("romans").data["passages"]
        # In top-book order, one each — not every citing chapter.
        self.assertEqual([p["book_slug"] for p in passages], ["big", "small"])
        self.assertEqual(passages[0]["ref"], "Romans 8:28")
        # Small's first chapter cites Romans 5:8 and 8:28; both are one verse,
        # so either is its narrowest — the excerpt quotes the work's own words.
        self.assertIn(passages[1]["ref"], {"Romans 5:8", "Romans 8:28"})
        for p in passages:
            self.assertTrue(p["excerpt"].strip())
            self.assertEqual(p["chapter_title"], f"Chapter {p['chapter_order']}")

    def test_the_book_carries_its_house_overview(self):
        self.assertIn("Paul", self.get("romans").data["intro"])

    def test_verses_carry_their_text_and_only_pages_that_exist(self):
        verses = self.get("romans").data["verses"]
        self.assertEqual([(v["chapter"], v["verse"]) for v in verses], [(8, 28)])
        self.assertIn("work together for good", verses[0]["text"])

    def test_a_book_without_chapter_pages_404s(self):
        self.assertEqual(self.get("nahum").status_code, 404)
        self.assertEqual(self.get("not-a-book").status_code, 404)

    def test_pages_route_is_not_read_as_a_book(self):
        res = self.client.get("/api/library/scripture/pages/")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.data, list)

    def test_prev_and_next_walk_books_with_pages(self):
        author = Author.objects.get(slug="murray")
        other = Book.objects.create(author=author, slug="o", language="en", title="O")
        for i in range(CHAPTER_FLOOR):
            cite(other, i + 1, "John 3:16")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)
        res = self.get("romans")
        self.assertEqual(res.data["prev"], {"book": "john", "book_title": "John"})
        self.assertIsNone(res.data["next"])


class BookViewEditionAndSpanTests(TestCase):
    """What the book page counts as one work, and what it refuses to count."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="b", name="B")
        full = Book.objects.create(author=author, slug="retro", language="en", title="Retro")
        teens = Book.objects.create(
            author=author, slug="retro-teens", language="en", title="Retro (For Teens)"
        )
        for i in range(CHAPTER_FLOOR):
            cite(full, i + 1, "Romans 5:8")
        cite(teens, 1, "Romans 5:8")
        from django.core.management import call_command

        call_command("index_citations", "--all", verbosity=0)

    def test_young_reader_editions_fold_into_their_work(self):
        res = self.client.get("/api/library/scripture/romans/")
        self.assertEqual(res.data["books_count"], 1)
        self.assertEqual(
            [(b["slug"], b["citing_count"]) for b in res.data["top_books"]],
            [("retro", CHAPTER_FLOOR + 1)],
        )

    def test_a_runaway_span_does_not_count_for_books_it_merely_crosses(self):
        from .models import ChapterCitation

        stray = Chapter.objects.filter(book__slug="retro").first()
        # Acts 1:1 → Revelation 22:21: crosses Romans, but bucket() clamps it.
        ChapterCitation.objects.create(
            chapter=Chapter.objects.create(
                book=stray.book, order=99, title="Stray", body_html="<p>x</p>"
            ),
            ref_text="Acts 1:1-Revelation 22:21",
            start_verse_id=44001001,
            end_verse_id=66022021,
        )
        res = self.client.get("/api/library/scripture/romans/")
        self.assertEqual(res.data["citing_count"], CHAPTER_FLOOR + 1)


class BibleBookIntroTests(TestCase):
    """The house overviews: one for every book that can have a page, sized
    to read as a paragraph, and keyed by the slugs the pages use."""

    def test_every_book_with_asv_text_has_an_overview_of_a_paragraph(self):
        import pythonbible as bible

        from .bible_book_intros import table
        from .scripture_graph import book_slug, verse_text

        books = {book_slug(b) for b in bible.Book if verse_text(b.value * 1_000_000 + 1001)}
        intros = table()["en"]
        self.assertEqual(set(intros), books)
        bad = {s: len(t.split()) for s, t in intros.items() if not 40 <= len(t.split()) <= 110}
        self.assertEqual(bad, {}, "an overview should be one paragraph, 40-110 words")
