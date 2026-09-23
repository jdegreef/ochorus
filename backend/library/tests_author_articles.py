"""`articles_for_author` and the author detail payload's `articles` field — the
reverse cross-link from a person to the articles written about them.

The counterpart of `tests_guides`. An article belongs on an author page two
ways, unioned: it names the person in its Read-next `related`, or it is a
reader's guide (slug ends `-guide`) whose PRIMARY book that person wrote. These
tests pin that definition — the primary-book rule, the union and its dedupe, the
publish gate, and the per-language rule, which is where this helper deliberately
differs from `guides_for_book`: articles are per-language rows and translated
ones exist, so a locale gets its own articles or none, never English fallback.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Article, Author, Book
from .serializers import AuthorDetailSerializer, articles_for_author


class ArticlesForAuthorTests(TestCase):
    def setUp(self):
        self.murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        self.other = Author.objects.create(slug="e-m-bounds", name="E. M. Bounds")

    def _book(self, author, slug, title, *, language="en", published=True):
        # Chapterless on purpose: articles_for_author reads only slugs, and
        # AuthorDetailSerializer tolerates a book with no chapters.
        return Book.objects.create(
            author=author, slug=slug, language=language, title=title,
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

    def _slugs(self, author_slug="andrew-murray", language="en"):
        return [a["slug"] for a in articles_for_author(author_slug, language)]

    # --- the two ways in ---------------------------------------------------

    def test_a_guide_to_this_authors_book_surfaces_on_their_page(self):
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article("abide-in-christ-guide", [{"type": "book", "slug": "abide-in-christ"}])
        self.assertEqual(self._slugs(), ["abide-in-christ-guide"])

    def test_an_article_naming_the_author_surfaces_even_without_a_book(self):
        """A topical essay is not a guide, but if its Read-next funnel sends the
        reader to this bio, the bio may send them back."""
        self._article(
            "what-does-it-mean-to-abide-in-christ",
            [{"type": "author", "slug": "andrew-murray"}],
        )
        self.assertEqual(self._slugs(), ["what-does-it-mean-to-abide-in-christ"])

    def test_an_article_matching_both_ways_is_listed_once(self):
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "abide-in-christ-guide",
            [
                {"type": "book", "slug": "abide-in-christ"},
                {"type": "author", "slug": "andrew-murray"},
            ],
        )
        self.assertEqual(self._slugs(), ["abide-in-christ-guide"])

    # --- what must NOT surface --------------------------------------------

    def test_a_guide_to_another_authors_book_does_not_surface(self):
        self._book(self.other, "power-through-prayer", "Power Through Prayer")
        self._article(
            "power-through-prayer-guide",
            [{"type": "book", "slug": "power-through-prayer"}],
        )
        self.assertEqual(self._slugs(), [])

    def test_a_guide_is_attributed_only_to_its_primary_books_author(self):
        """A guide may point on to sibling works by other people; keying on the
        FIRST book keeps it off the secondary author's page — the same rule
        `guides_for_book` uses to keep it off the secondary book."""
        self._book(self.other, "power-through-prayer", "Power Through Prayer")
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "power-through-prayer-guide",
            [
                {"type": "book", "slug": "power-through-prayer"},
                {"type": "book", "slug": "abide-in-christ"},
            ],
        )
        self.assertEqual(self._slugs(), [])
        self.assertEqual(self._slugs("e-m-bounds"), ["power-through-prayer-guide"])

    def test_an_unpublished_article_never_surfaces(self):
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "abide-in-christ-guide",
            [{"type": "book", "slug": "abide-in-christ"}],
            published=False,
        )
        self.assertEqual(self._slugs(), [])

    def test_a_guide_to_an_unpublished_book_does_not_surface(self):
        self._book(self.murray, "abide-in-christ", "Abide in Christ", published=False)
        self._article("abide-in-christ-guide", [{"type": "book", "slug": "abide-in-christ"}])
        self.assertEqual(self._slugs(), [])

    def test_malformed_related_is_skipped_not_raised(self):
        """`related` is a schema-less hand-authored JSON field."""
        self._article("a-string", "not-a-list")
        self._article("wrong-shape", [["book", "abide-in-christ"], None, 7])
        self._article("no-slug-guide", [{"type": "book"}])
        self.assertEqual(self._slugs(), [])

    # --- per-language ------------------------------------------------------

    def test_each_language_gets_its_own_articles_and_no_english_fallback(self):
        """Where `guides_for_book` gates on English, this does not: translated
        article rows exist (fr), so a French page gets French articles and a
        language with none gets an empty list — never the English ones."""
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article("abide-in-christ-guide", [{"type": "book", "slug": "abide-in-christ"}])
        self._article(
            "abide-in-christ-guide",
            [{"type": "book", "slug": "abide-in-christ"}],
            language="fr",
            h1="Demeurez en Christ : guide de lecture",
        )
        self.assertEqual(self._slugs(language="en"), ["abide-in-christ-guide"])
        self.assertEqual(
            [a["h1"] for a in articles_for_author("andrew-murray", "fr")],
            ["Demeurez en Christ : guide de lecture"],
        )
        self.assertEqual(self._slugs(language="lg"), [])

    def test_the_authors_books_count_across_languages(self):
        """Book slugs are shared across translations, so an English guide still
        attaches to an author whose only published edition is localized."""
        self._book(self.murray, "abide-in-christ", "Demeurez en Christ", language="fr")
        self._article("abide-in-christ-guide", [{"type": "book", "slug": "abide-in-christ"}])
        self.assertEqual(self._slugs(), ["abide-in-christ-guide"])

    # --- the payload -------------------------------------------------------

    def test_the_detail_payload_is_card_shaped(self):
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "abide-in-christ-guide",
            [{"type": "book", "slug": "abide-in-christ"}],
            h1="Abide in Christ: A Reader’s Guide",
        )
        articles = AuthorDetailSerializer(self.murray).data["articles"]
        self.assertEqual(len(articles), 1)
        self.assertEqual(set(articles[0]), {"slug", "h1", "description"})
        self.assertEqual(articles[0]["h1"], "Abide in Christ: A Reader’s Guide")

    def test_the_person_card_does_not_carry_articles(self):
        from .serializers import AuthorListSerializer

        self.assertNotIn("articles", AuthorListSerializer(self.murray).data)
