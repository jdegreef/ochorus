"""`sibling_editions` and the detail payload's `editions` field — the cross-link
between the full text of a work and its young-reader retellings.

The relationship is the slug convention alone (`<base>` ⇄ `<base>-teens` ⇄
`<base>-children`); nothing in the model joins the rows. These tests pin the
convention, the full → teens → children order, the per-request `is_published`
gate, the same-language rule, and — the one that would bite — that a work whose
real title merely ends in `-children` is not mistaken for a retelling.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Author, Book, Chapter
from .serializers import BookDetailSerializer, sibling_editions


class SiblingEditionsTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="hudson-taylor", name="Hudson Taylor")

    def _book(self, slug, title, *, language="en", published=True):
        book = Book.objects.create(
            author=self.author, slug=slug, language=language, title=title,
            is_published=published,
        )
        # A chapter so the card annotations (chapter_count/word_count) are real.
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>Hi.</p>")
        return book

    def test_full_text_links_to_its_retellings_in_reading_age_order(self):
        full = self._book("a-retrospect", "A Retrospect")
        self._book("a-retrospect-children", "A Retrospect (For Children)")
        self._book("a-retrospect-teens", "A Retrospect (For Teens)")
        slugs = [b.slug for b in sibling_editions(full)]
        self.assertEqual(slugs, ["a-retrospect-teens", "a-retrospect-children"])

    def test_a_retelling_links_back_to_the_full_text_and_its_siblings(self):
        self._book("a-retrospect", "A Retrospect")
        children = self._book("a-retrospect-children", "A Retrospect (For Children)")
        self._book("a-retrospect-teens", "A Retrospect (For Teens)")
        slugs = [b.slug for b in sibling_editions(children)]
        self.assertEqual(slugs, ["a-retrospect", "a-retrospect-teens"])

    def test_unpublished_editions_are_omitted(self):
        full = self._book("the-life-of-trust", "The Life of Trust")
        self._book(
            "the-life-of-trust-children",
            "The Life of Trust (For Children)",
            published=False,
        )
        self.assertEqual(sibling_editions(full), [])

    def test_editions_do_not_cross_a_language_boundary(self):
        """No-English-fallback: a French full text links only French retellings."""
        fr = self._book("a-retrospect", "Un rétrospectif", language="fr")
        self._book(
            "a-retrospect-children",
            "A Retrospect (For Children)",
            language="en",
        )
        self.assertEqual(sibling_editions(fr), [])

    def test_a_real_title_ending_in_children_is_not_a_retelling(self):
        """`divine-songs-for-children` is Watts's own title, not an edition of a
        `divine-songs-for` work — so it must surface no phantom sibling."""
        watts = self._book("divine-songs-for-children", "Divine Songs for Children")
        self.assertEqual(sibling_editions(watts), [])

    def test_a_work_with_no_retelling_gets_an_empty_list(self):
        book = self._book("mortification-of-sin", "The Mortification of Sin")
        self.assertEqual(BookDetailSerializer(book).data["editions"], [])

    def test_the_detail_payload_carries_card_shaped_editions(self):
        full = self._book("a-retrospect", "A Retrospect")
        self._book("a-retrospect-children", "A Retrospect (For Children)")
        data = BookDetailSerializer(full).data["editions"]
        self.assertEqual(len(data), 1)
        card = data[0]
        self.assertEqual(card["slug"], "a-retrospect-children")
        self.assertEqual(card["title"], "A Retrospect (For Children)")
        # Card-shaped: enough for a BookCard to render without another fetch.
        for key in ("cover_url", "author", "chapter_count"):
            self.assertIn(key, card)

    def test_the_shelf_card_does_not_carry_editions(self):
        from .serializers import BookListSerializer

        book = self._book("a-retrospect", "A Retrospect")
        self.assertNotIn("editions", BookListSerializer(book).data)

    def test_a_sibling_edition_is_not_also_listed_under_related(self):
        """The retelling shares its parent's author, so "more like this" would
        otherwise surface the same work already shown as an edition — once is
        enough."""
        full = self._book("a-retrospect", "A Retrospect")
        self._book("a-retrospect-children", "A Retrospect (For Children)")
        # An unrelated same-author book SHOULD still be a related suggestion.
        self._book("union-and-communion", "Union and Communion")
        data = BookDetailSerializer(full).data
        edition_slugs = {e["slug"] for e in data["editions"]}
        related_slugs = {r["slug"] for r in data["related"]}
        self.assertIn("a-retrospect-children", edition_slugs)
        self.assertNotIn("a-retrospect-children", related_slugs)
        self.assertIn("union-and-communion", related_slugs)
