"""`guides_for_book` and the book detail payload's `guides` field — the reverse
cross-link from a book to the reader's guide that explains it.

A guide is an article whose slug ends `-guide` (the repo convention) and whose
Read-next `related` leads with this book. These tests pin that definition: a
topical article that merely funnels to the book is not a guide, a multi-book
guide is attributed only to its primary (first) book, the unpublished and
non-English gates hold, and the payload is card-shaped.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Article, Author, Book
from .serializers import BookDetailSerializer, guides_for_book


class GuidesForBookTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="augustine", name="Augustine")

    def _book(self, slug, title, *, language="en", published=True):
        # No chapter needed: guides_for_book queries only Article, and
        # BookDetailSerializer tolerates a chapterless book (opening→None,
        # chapters→[], the dropped card annotations).
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=title,
            is_published=published,
        )

    def _article(self, slug, related, *, published=True, h1=None, language="en"):
        return Article.objects.create(
            slug=slug,
            language=language,
            h1=h1 or slug.replace("-", " ").title(),
            description=f"About {slug}.",
            body_html="<p>Body.</p>",
            related=related,
            is_published=published,
        )

    def test_a_guide_surfaces_on_the_book_it_leads_with(self):
        self._book("confessions", "Confessions")
        self._article(
            "augustines-confessions-guide",
            [{"type": "book", "slug": "confessions"}, {"type": "author", "slug": "augustine"}],
        )
        self.assertEqual(
            [g["slug"] for g in guides_for_book("confessions", "en")],
            ["augustines-confessions-guide"],
        )

    def test_a_topical_article_that_funnels_to_the_book_is_not_a_guide(self):
        """Only the `-guide` convention counts — a 'what is grace' article that
        leads its Read-next with this book must not be mistaken for its guide."""
        self._book("all-of-grace", "All of Grace")
        self._article("what-is-grace", [{"type": "book", "slug": "all-of-grace"}])
        self.assertEqual(guides_for_book("all-of-grace", "en"), [])

    def test_a_multi_book_guide_is_attributed_only_to_its_primary_book(self):
        """A guide may point on to sibling works; keying on the FIRST book means
        the secondary work does not claim another book's guide."""
        self._book("confessions", "Confessions")
        self._book("grace-abounding", "Grace Abounding")
        self._article(
            "augustines-confessions-guide",
            [
                {"type": "book", "slug": "confessions"},
                {"type": "book", "slug": "grace-abounding"},
            ],
        )
        self.assertEqual(
            [g["slug"] for g in guides_for_book("confessions", "en")],
            ["augustines-confessions-guide"],
        )
        self.assertEqual(guides_for_book("grace-abounding", "en"), [])

    def test_multiple_guides_for_one_book_come_in_sort_order(self):
        """A book with more than one guide returns them in (sort_order, h1) — the
        order the book page's `{#each}` renders. No book has two today, but the
        frontend relies on the ordering, so pin it."""
        self._book("confessions", "Confessions")
        a = Article.objects.create(
            slug="augustines-confessions-guide", language="en", h1="A guide",
            description="d", body_html="<p>.</p>",
            related=[{"type": "book", "slug": "confessions"}],
            is_published=True, sort_order=2,
        )
        b = Article.objects.create(
            slug="confessions-second-guide", language="en", h1="B guide",
            description="d", body_html="<p>.</p>",
            related=[{"type": "book", "slug": "confessions"}],
            is_published=True, sort_order=1,
        )
        self.assertEqual(
            [g["slug"] for g in guides_for_book("confessions", "en")],
            [b.slug, a.slug],  # sort_order 1 before 2
        )

    def test_an_unpublished_guide_is_omitted(self):
        self._book("confessions", "Confessions")
        self._article(
            "augustines-confessions-guide",
            [{"type": "book", "slug": "confessions"}],
            published=False,
        )
        self.assertEqual(guides_for_book("confessions", "en"), [])

    def test_a_book_with_no_guide_gets_an_empty_list(self):
        self._book("the-inner-chamber", "The Inner Chamber")
        self.assertEqual(guides_for_book("the-inner-chamber", "en"), [])

    def test_a_malformed_related_entry_does_not_raise(self):
        self._book("confessions", "Confessions")
        self._article("augustines-confessions-guide", ["not-a-dict", {"type": "book"}])
        # No first book resolves, so nothing surfaces — and no exception.
        self.assertEqual(guides_for_book("confessions", "en"), [])

    def test_the_detail_payload_carries_guide_slug_h1_and_description(self):
        book = self._book("confessions", "Confessions")
        self._article(
            "augustines-confessions-guide",
            [{"type": "book", "slug": "confessions"}],
            h1="Augustine’s Confessions: A Reader’s Guide",
        )
        guides = BookDetailSerializer(book).data["guides"]
        self.assertEqual(len(guides), 1)
        self.assertEqual(
            set(guides[0]), {"slug", "h1", "description"}
        )
        self.assertEqual(guides[0]["h1"], "Augustine’s Confessions: A Reader’s Guide")

    def test_a_non_english_book_never_carries_guides(self):
        """Articles are English-only; a localized edition shows no guide section
        (and the payload does not leak the English guide onto it)."""
        book = self._book("confessions", "Confesiones", language="es")
        # The English guide exists, but the Spanish book must not claim it.
        self._book("confessions", "Confessions", language="en")
        self._article(
            "augustines-confessions-guide",
            [{"type": "book", "slug": "confessions"}],
        )
        self.assertEqual(BookDetailSerializer(book).data["guides"], [])

    def test_the_shelf_card_does_not_carry_guides(self):
        from .serializers import BookListSerializer

        book = self._book("confessions", "Confessions")
        self.assertNotIn("guides", BookListSerializer(book).data)
