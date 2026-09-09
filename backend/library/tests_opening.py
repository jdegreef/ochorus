"""`opening_excerpt` — the first taste of a book's prose.

Every rule here exists because the naive version was wrong on a real book, and
each test names the one that broke it. The corpus is 68 heterogeneous
public-domain imports; "the first paragraph of chapter 1" is wrong on more than
a third of them.

The gate is deliberately allowed to say NO. Three books get no excerpt today,
and a page with no excerpt reads fine — a page opening on an editorial synopsis
of a treatise does not.
"""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from .models import Author, Book, Chapter
from .opening import (
    MAX_DEPTH,
    MAX_WORDS,
    opening_candidate_orders,
    opening_excerpt,
)


def ch(title: str, *paragraphs: str):
    return (0, title, "".join(f"<p>{p}</p>" for p in paragraphs))


LONG = (
    "In this my relation of the merciful working of God upon my soul, it will "
    "not be amiss, if, in the first place, I do, in a few words, give you a "
    "hint of my pedigree, and manner of bringing up, that thereby the goodness "
    "and bounty of God towards me may be the more advanced and magnified."
)


class SelectionTests(SimpleTestCase):
    def test_front_matter_is_skipped(self):
        text, title = opening_excerpt(
            [ch("Preface", "Short note."), ch("Chapter I", LONG)]
        )
        self.assertEqual(title, "Chapter I")
        self.assertTrue(text.startswith("In this my relation"))

    def test_apparatus_is_matched_anywhere_in_the_title(self):
        """The corpus has "Extract from the Preface", "A Short Account of the
        Author…" and "Personal Profile" — none start with the marker word."""
        for heading in (
            "Extract from the Preface",
            "A Short Account of the Author and the Great Success",
            "Personal Profile",
            "Advertisement by the Reporter",
            "Prefactory Note",  # yes, the corpus misspells it
        ):
            with self.subTest(heading=heading):
                _text, title = opening_excerpt(
                    [ch(heading, LONG), ch("Chapter I", LONG)]
                )
                self.assertEqual(title, "Chapter I")

    def test_it_does_not_wander_deep_into_the_book(self):
        """Grace Abounding fell through five front sections and offered its
        CONCLUSION as a first taste. An excerpt from chapter six is not an
        opening, so past the limit the answer is nothing."""
        # The magnitude is part of the contract, not just the behaviour: a
        # limit of 99 would pass the check below while still handing back a
        # passage from the middle of the book.
        self.assertLessEqual(
            MAX_DEPTH, 5, "deeper than the front of the book is not an opening"
        )
        junk = ch("Part", "§ heading only")
        text, _ = opening_excerpt([junk] * (MAX_DEPTH + 1) + [ch("Real", LONG)])
        self.assertEqual(text, "")

    def test_a_book_with_no_clean_opening_gets_nothing(self):
        self.assertEqual(opening_excerpt([]), ("", ""))


class ProseGateTests(SimpleTestCase):
    def _rejected(self, *paragraphs):
        text, _ = opening_excerpt([ch("One", *paragraphs)])
        return text == ""

    def test_an_editorial_synopsis_is_rejected(self):
        """On the Incarnation: "§1. Introductory.—The subject of this treatise:
        the humiliation and incarnation of the Word." Not Athanasius."""
        self.assertTrue(
            self._rejected(
                "§1. Introductory.—The subject of this treatise: the "
                "humiliation and incarnation of the Word. Presupposes the "
                "doctrine of Creation, and that by the Word."
            )
        )

    def test_a_chapter_argument_is_rejected(self):
        """Owen: topic phrases strung on em-dashes, never a sentence."""
        self.assertTrue(
            self._rejected(
                "The foundation of the whole ensuing discourse laid in Rom. "
                "viii. 13 — The words of the apostle opened — The certain "
                "connection between true mortification and salvation — "
                "Mortification the work of believers — The Spirit the "
                "principal efficient cause of it."
            )
        )

    def test_an_absorbed_running_head_is_rejected(self):
        self.assertTrue(
            self._rejected(
                "RELIGIOUS AFFECTIONS. PART 1. CONCERNING THE NATURE OF THE "
                "AFFECTIONS AND THEIR IMPORTANCE IN RELIGION. And this is the "
                "text that follows it, running on for a while afterwards."
            )
        )

    def test_an_opening_that_is_mostly_quoted_scripture_is_rejected(self):
        """Catherine Booth's "Repentance" opens on two verses and nothing
        else — it tastes of the Bible, not of the book."""
        self.assertTrue(
            self._rejected(
                "\u201cRepent, for the kingdom of heaven is at hand, and here "
                "is a long quotation filling the paragraph entirely with the "
                "words of scripture rather than any of the author writing in "
                "his own voice at all.\u201d "
                "\u201cFrom that time Jesus began to preach, and to say.\u201d"
            )
        )

    def test_one_long_sentence_is_accepted(self):
        """The rule was two sentences and it rejected Bunyan and Edwards, whose
        openings run ninety words before the first full stop. A long period is
        a feature of the prose this shelf is made of."""
        text, _ = opening_excerpt([ch("One", LONG)])
        self.assertTrue(text.startswith("In this my relation"))


class ExtractionTests(SimpleTestCase):
    def test_footnote_markers_are_dropped_content_and_all(self):
        """Stripping tags alone welds the digits to the prose: Pilgrim's
        Progress flattens to "a den,33Bedford jail"."""
        text, _ = opening_excerpt(
            [ch("One", "As I walked through the wilderness of this world, I "
                       "lighted on a certain place where was a den,"
                       "<sup>3</sup><sup>3</sup> and laid me down in that "
                       "place to sleep; and as I slept, I dreamed a dream, "
                       "and behold I saw a man clothed with rags.")]
        )
        self.assertNotIn("33", text)
        self.assertIn("where was a den,", text)

    def test_html_entities_are_decoded(self):
        text, _ = opening_excerpt(
            [ch("One", "THE words necessary, impossible, &amp;c. are "
                       "abundantly used in controversies about Free-Will and "
                       "Moral Agency; and therefore the sense in which they "
                       "are used should be well understood by every one who "
                       "would form a clear judgement upon the matter at all.")]
        )
        self.assertIn("&c.", text)
        self.assertNotIn("&amp;", text)

    def test_a_leading_epigraph_is_skipped(self):
        """Many chapters open under a verse. The excerpt should reach the
        author's own sentences — including the older attribution styles the
        corpus uses ("…at the appearing of Jesus Christ."—1 Peter, i. 7)."""
        text, _ = opening_excerpt(
            [ch("One",
                '"That the trial of your faith, being much more precious than '
                'of gold that perisheth, might be found unto praise."'
                "—1 Peter, i. 7.",
                LONG)]
        )
        self.assertTrue(text.startswith("In this my relation"))

    def test_it_never_ends_on_a_dangling_abbreviation(self):
        """The sentence search stops at an abbreviation's full stop and leaves
        its next word hanging: "…1 Peter, i. 7. Mr." """
        body = ("Word " * 60) + "end. Mr. George Müller founded the orphan houses."
        text, _ = opening_excerpt([ch("One", body)])
        self.assertFalse(text.rstrip().endswith("Mr."))

    def test_the_excerpt_is_capped(self):
        text, _ = opening_excerpt([ch("One", "alpha beta gamma delta. " * 60)])
        self.assertLessEqual(len(text.split()), MAX_WORDS)


class CandidateOrderTests(SimpleTestCase):
    """``opening_candidate_orders`` names the chapters whose BODIES the detail
    serializer must fetch — the egress fix depends on it naming no more than the
    orders ``opening_excerpt`` would actually inspect."""

    def test_front_matter_is_skipped_by_title(self):
        self.assertEqual(
            opening_candidate_orders([(1, "Preface"), (2, "Chapter I")]), [2]
        )

    def test_it_stops_at_max_depth_non_apparatus_chapters(self):
        meta = [(n, f"Chapter {n}") for n in range(1, 10)]
        self.assertEqual(opening_candidate_orders(meta), list(range(1, MAX_DEPTH + 1)))

    def test_apparatus_does_not_spend_depth(self):
        """Leading apparatus is skipped without counting — the real chapters
        past it are still reachable, so their orders (not the apparatus') are the
        candidates."""
        meta = [(1, "Preface"), (2, "Contents"), (3, "Translator's Note")]
        meta += [(4, "Chapter I"), (5, "Chapter II"), (6, "Chapter III")]
        self.assertEqual(
            opening_candidate_orders(meta), list(range(4, 4 + MAX_DEPTH))
        )

    def test_it_matches_what_the_excerpt_loop_inspects(self):
        """The equivalence the serializer relies on: a real chapter sitting past
        MAX_DEPTH non-apparatus chapters is NOT a candidate, exactly as
        opening_excerpt never reaches it (test_it_does_not_wander_deep...)."""
        meta = [(n, "Part") for n in range(1, MAX_DEPTH + 2)] + [(99, "Real")]
        got = opening_candidate_orders(meta)
        self.assertNotIn(99, got)
        self.assertEqual(got, list(range(1, MAX_DEPTH + 1)))

    def test_all_apparatus_or_empty_yields_nothing(self):
        self.assertEqual(opening_candidate_orders([]), [])
        self.assertEqual(
            opening_candidate_orders([(1, "Preface"), (2, "Foreword")]), []
        )


class PayloadTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="a", name="A")
        self.book = Book.objects.create(
            author=self.author, slug="b", language="en", title="B"
        )

    def test_the_detail_payload_carries_text_and_chapter(self):
        from .serializers import BookDetailSerializer

        Chapter.objects.create(
            book=self.book, order=1, title="Chapter I", body_html=f"<p>{LONG}</p>"
        )
        got = BookDetailSerializer(self.book).data["opening"]
        self.assertEqual(got["chapter"], "Chapter I")
        self.assertTrue(got["text"].startswith("In this my relation"))

    def test_a_book_with_no_clean_opening_sends_null(self):
        """Null, not an empty string — the page tests truthiness, and an empty
        blockquote with a caption naming a chapter is worse than no quote."""
        from .serializers import BookDetailSerializer

        Chapter.objects.create(
            book=self.book, order=1, title="Preface", body_html="<p>Short.</p>"
        )
        self.assertIsNone(BookDetailSerializer(self.book).data["opening"])

    def test_the_shelf_card_does_not_carry_it(self):
        """The one field here that reads chapter BODIES — on a shelf it would
        drag 130 books' HTML through the join."""
        from .serializers import BookListSerializer

        self.assertNotIn("opening", BookListSerializer(self.book).data)
