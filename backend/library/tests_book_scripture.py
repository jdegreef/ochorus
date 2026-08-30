"""`treated_passages` — the passages a book keeps returning to.

The book page's answer to "what scripture is this actually about", derived from
the text rather than declared. Two things make it worth guarding beyond the
usual:

1. It ranks. A ranking that is subtly wrong still looks right — eight plausible
   references in some order — so the tests assert the RULE (distinct chapters,
   not citation count) rather than a snapshot of today's corpus.

2. It links into a page set built by a different function. `qualifying_pages`
   decides what exists; this decides what to point at. If the two ever disagree
   the result is a 404 for the reader and a dead internal link for the crawler,
   which is exactly the failure `pages_for` was extracted to prevent.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Author, Book, Chapter, ChapterCitation
from .scripture_graph import (
    BOOK_PASSAGE_FLOOR,
    BOOK_PASSAGES,
    CHAPTER_FLOOR,
    VERSE_FLOOR,
    treated_passages,
)

ROM_8 = 45008000  # BBBCCCVVV base for Romans 8
ROM_8_28 = 45008028


class RankingTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="a", name="A")
        self.book = Book.objects.create(
            author=self.author, slug="b", language="en", title="B"
        )

    def _chapter(self, order: int) -> Chapter:
        return Chapter.objects.create(
            book=self.book, order=order, title=f"Ch {order}", body_html="<p>x</p>"
        )

    def _cite(self, chapter: Chapter, start: int, end: int | None = None, count=1):
        ChapterCitation.objects.create(
            chapter=chapter, ref_text="r", start_verse_id=start,
            end_verse_id=end or start, count=count,
        )

    def test_a_passage_one_chapter_treats_is_below_the_floor(self):
        """A mention is not a theme, and the section must not be full of them."""
        self._cite(self._chapter(1), ROM_8_28)
        self.assertEqual(treated_passages(self.book.pk), [])

    def test_the_floor_is_distinct_chapters_not_citations(self):
        """One chapter quoting a verse nine times is one chapter making one
        argument. Counting the nine is how a single insistent passage would
        outrank a theme the book actually returns to."""
        ch = self._chapter(1)
        self._cite(ch, ROM_8_28, count=9)
        self.assertEqual(treated_passages(self.book.pk), [])

        self._cite(self._chapter(2), ROM_8_28)
        got = treated_passages(self.book.pk)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["chapters"], BOOK_PASSAGE_FLOOR)

    def test_more_chapters_outrank_more_citations(self):
        one = self._chapter(1)
        for v in range(1, 9):
            self._cite(one, 45007000 + v, count=20)   # Romans 7, one chapter
        self._cite(self._chapter(2), 45007001)
        for order in range(3, 7):
            self._cite(self._chapter(order), ROM_8_28)  # Romans 8, four chapters

        got = treated_passages(self.book.pk)
        self.assertEqual(got[0]["reference"].split(":")[0], "Romans 8")
        self.assertGreater(got[0]["chapters"], got[1]["chapters"])

    def test_the_list_is_capped(self):
        for i in range(BOOK_PASSAGES + 4):
            base = 45001000 + i * 1000
            for order in (i * 2 + 1, i * 2 + 2):
                self._cite(self._chapter(order), base + 1)
        self.assertEqual(len(treated_passages(self.book.pk)), BOOK_PASSAGES)

    def test_a_book_that_cites_nothing_gets_an_empty_list(self):
        """True of 14 English books today — the patristic works quote scripture
        constantly but the translations carry no chapter-and-verse for the
        citation index to find. The section must simply not render."""
        self._chapter(1)
        self.assertEqual(treated_passages(self.book.pk), [])


class GrainAndLinkTests(TestCase):
    """The label must never promise a grain the link does not deliver."""

    def setUp(self):
        self.author = Author.objects.create(slug="a", name="A")

    def _work(self, slug: str, cites: list[tuple[int, int]]):
        book = Book.objects.create(
            author=self.author, slug=slug, language="en", title=slug
        )
        for order, vid in cites:
            ch, _ = Chapter.objects.get_or_create(
                book=book, order=order,
                defaults={"title": f"c{order}", "body_html": "<p>x</p>"},
            )
            ChapterCitation.objects.get_or_create(
                chapter=ch, start_verse_id=vid, end_verse_id=vid,
                defaults={"ref_text": "r", "count": 1},
            )
        return book

    def test_a_label_and_its_link_always_agree(self):
        """`pages_for` may resolve a verse-grain candidate down to its Bible
        chapter. A chip reading "Luke 14:11" that lands on Luke 14 has
        misdescribed itself, so the label is taken from the resolved page."""
        book = self._work("w", [(1, ROM_8_28), (2, ROM_8_28)])
        for entry in treated_passages(book.pk):
            page = entry["page"]
            if page is None:
                continue
            with self.subTest(reference=entry["reference"]):
                has_verse_in_label = ":" in entry["reference"]
                self.assertEqual(has_verse_in_label, page["verse"] is not None)

    def test_a_verse_grain_candidate_resolving_to_a_chapter_page_is_relabelled(self):
        """The Luke 14:11 case, and the reason the relabel step exists.

        Within this book every chapter that touches Romans 8 touches 8:28, so
        the book-level rule says verse grain. Across the corpus that verse sits
        under VERSE_FLOOR while the chapter clears CHAPTER_FLOOR, so the only
        page is Romans 8. Without the relabel the chip reads "Romans 8:28" and
        lands on Romans 8.
        """
        book = self._work("w", [(1, ROM_8_28), (2, ROM_8_28)])
        # Enough other chapters on OTHER verses of Romans 8 to build the
        # chapter page, but not enough on 8:28 to build the verse page.
        for i in range(CHAPTER_FLOOR):
            self._work(f"other{i}", [(1, ROM_8 + 1)])

        got = treated_passages(book.pk)
        self.assertEqual(len(got), 1)
        self.assertIsNotNone(got[0]["page"], "the chapter page should exist")
        self.assertIsNone(got[0]["page"]["verse"])
        self.assertEqual(got[0]["reference"], "Romans 8")

    def test_a_passage_under_the_corpus_floor_is_listed_without_a_page(self):
        """The floors are about the corpus, and one book is not a corpus. It is
        still true about the book, so it is listed — unlinked, never pointing at
        a page that was never built."""
        book = self._work("w", [(1, ROM_8_28), (2, ROM_8_28)])
        got = treated_passages(book.pk)
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["page"])

    def test_it_links_once_enough_independent_chapters_cite_the_verse(self):
        """Same verse, now cited by enough OTHER books to clear VERSE_FLOOR."""
        book = self._work("w", [(1, ROM_8_28), (2, ROM_8_28)])
        for i in range(VERSE_FLOOR):
            self._work(f"other{i}", [(1, ROM_8_28)])
        got = treated_passages(book.pk)
        self.assertIsNotNone(got[0]["page"])
        self.assertEqual(got[0]["page"]["verse"], 28)
        self.assertEqual(got[0]["reference"], "Romans 8:28")


class PayloadTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="a", name="A")

    def _book(self, language="en"):
        return Book.objects.create(
            author=self.author, slug="b", language=language, title="B"
        )

    def test_a_translated_edition_gets_nothing(self):
        """The citation index is built from English bodies, so a translated row
        has none of its own — and answering from the English book's would put
        English chapter counts on a Swahili page and link into a graph with no
        Swahili pages to land on."""
        from .serializers import BookDetailSerializer

        book = self._book(language="sw")
        ch = Chapter.objects.create(
            book=book, order=1, title="c", body_html="<p>x</p>"
        )
        ChapterCitation.objects.create(
            chapter=ch, ref_text="r", start_verse_id=ROM_8_28, end_verse_id=ROM_8_28
        )
        self.assertEqual(BookDetailSerializer(book).data["scripture"], [])

    def test_the_shelf_card_does_not_carry_it(self):
        """Two queries per row, 130 rows, for markup a card does not have."""
        from .serializers import BookListSerializer

        self.assertNotIn("scripture", BookListSerializer(self._book()).data)
