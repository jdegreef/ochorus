"""`articles_for_author` and the author detail payload's `articles` field — the
reverse cross-link from a person to the articles that name them.

The counterpart of `tests_guides`. ONE rule: an article belongs on a person's
page when it names them in its Read-next `related`. These tests pin that rule
and, just as importantly, its two edges — the breadth (authorship is NOT
required, so an article lands on the page of everyone it names) and the cost (a
guide that names no author is invisible here). Plus the publish gate, the
malformed-JSON guard, and the per-language rule it shares with
`guides_for_book`: articles are per-language rows and translated ones exist, so
a locale gets its own articles or none, never English fallback.

An earlier draft carried a second rule keying on the guided book's author. It
was measured against the whole corpus, selected a strict subset of this one, and
was deleted; see `articles_for_author`.
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
        # Chapterless on purpose: articles_for_author never reads books at all,
        # and AuthorDetailSerializer tolerates a book with no chapters.
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

    # --- the rule ----------------------------------------------------------

    def test_a_guide_surfaces_through_the_author_it_names(self):
        """Every `-guide` in the corpus names its book's author in `related`
        (73 of 73, measured 2026-09-23), which is why no separate primary-book
        rule is needed. The `write-article` skill states it as an invariant."""
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "abide-in-christ-guide",
            [
                {"type": "book", "slug": "abide-in-christ"},
                {"type": "author", "slug": "andrew-murray"},
            ],
        )
        self.assertEqual(self._slugs(), ["abide-in-christ-guide"])

    def test_an_essay_surfaces_with_no_book_involved(self):
        """A topical essay is not a guide, but if its Read-next funnel sends the
        reader to this bio, the bio may send them back."""
        self._article(
            "what-does-it-mean-to-abide-in-christ",
            [{"type": "author", "slug": "andrew-murray"}],
        )
        self.assertEqual(self._slugs(), ["what-does-it-mean-to-abide-in-christ"])

    def test_an_article_lands_on_the_page_of_everyone_it_names(self):
        """The breadth is deliberate, not an oversight — pinned so it is a known
        trade. A person an article DISCUSSES gets it even though they wrote
        nothing: in the real corpus the guide to Augustine's *Confessions* names
        Monica, and her bio-only page is among the sparsest on the site."""
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article(
            "abide-in-christ-guide",
            [
                {"type": "book", "slug": "abide-in-christ"},
                {"type": "author", "slug": "andrew-murray"},
                {"type": "author", "slug": "e-m-bounds"},
            ],
        )
        self.assertEqual(self._slugs(), ["abide-in-christ-guide"])
        self.assertEqual(self._slugs("e-m-bounds"), ["abide-in-christ-guide"])

    # --- what does NOT surface ---------------------------------------------

    def test_a_guide_that_names_no_author_is_invisible(self):
        """The cost of the one rule, pinned so a regression in article authoring
        shows up here rather than as a silently missing section."""
        self._book(self.murray, "abide-in-christ", "Abide in Christ")
        self._article("abide-in-christ-guide", [{"type": "book", "slug": "abide-in-christ"}])
        self.assertEqual(self._slugs(), [])

    def test_an_article_naming_a_different_person_does_not_surface(self):
        self._article(
            "power-through-prayer-guide",
            [
                {"type": "book", "slug": "power-through-prayer"},
                {"type": "author", "slug": "e-m-bounds"},
            ],
        )
        self.assertEqual(self._slugs(), [])
        self.assertEqual(self._slugs("e-m-bounds"), ["power-through-prayer-guide"])

    def test_a_book_reference_alone_never_matches(self):
        """`related` entries are typed; a book slug that happens to equal an
        author slug must not be mistaken for a person."""
        self._article("odd", [{"type": "book", "slug": "andrew-murray"}])
        self.assertEqual(self._slugs(), [])

    def test_an_unpublished_article_never_surfaces(self):
        self._article(
            "abide-in-christ-guide",
            [{"type": "author", "slug": "andrew-murray"}],
            published=False,
        )
        self.assertEqual(self._slugs(), [])

    def test_malformed_related_is_skipped_not_raised(self):
        """`related` is a schema-less hand-authored JSON field."""
        self._article("a-string", "not-a-list")
        self._article("wrong-shape", [["author", "andrew-murray"], None, 7])
        self._article("no-slug", [{"type": "author"}])
        self.assertEqual(self._slugs(), [])

    # --- per-language ------------------------------------------------------

    def test_each_language_gets_its_own_articles_and_no_english_fallback(self):
        """Translated
        article rows exist (the fixture carries fr, lg, es, pt, sw), so a French
        page gets French articles and a language with none gets an empty list —
        never the English ones."""
        for lang, h1 in (("en", "Abide in Christ: A Reader's Guide"),
                         ("fr", "Demeurez en Christ : guide de lecture")):
            self._article(
                "abide-in-christ-guide",
                [{"type": "author", "slug": "andrew-murray"}],
                language=lang,
                h1=h1,
            )
        self.assertEqual(
            [a["h1"] for a in articles_for_author("andrew-murray", "en")],
            ["Abide in Christ: A Reader's Guide"],
        )
        self.assertEqual(
            [a["h1"] for a in articles_for_author("andrew-murray", "fr")],
            ["Demeurez en Christ : guide de lecture"],
        )
        self.assertEqual(self._slugs(language="lg"), [])

    # --- the payload -------------------------------------------------------

    def test_the_detail_payload_is_card_shaped(self):
        self._article(
            "abide-in-christ-guide",
            [{"type": "author", "slug": "andrew-murray"}],
            h1="Abide in Christ: A Reader's Guide",
        )
        articles = AuthorDetailSerializer(self.murray).data["articles"]
        self.assertEqual(len(articles), 1)
        self.assertEqual(set(articles[0]), {"slug", "h1", "description"})
        self.assertEqual(articles[0]["h1"], "Abide in Christ: A Reader's Guide")

    def test_the_person_card_does_not_carry_articles(self):
        from .serializers import AuthorListSerializer

        self.assertNotIn("articles", AuthorListSerializer(self.murray).data)
