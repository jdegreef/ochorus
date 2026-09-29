"""The author detail payload's `available_languages` — the page's hreflang set.

An author page is prerendered in every locale but noindexed where it has
nothing of the writer's own (frontend `hasOwnContent`), and the sitemap lists
only the rest. The hreflang set has to match, or every indexed author page
points crawlers at noindexed siblings. So a language counts when it has a bio,
a published book or a published sermon — and nothing else.
"""

from __future__ import annotations

from django.test import TestCase

from .contemporize import MODERN_LANGUAGE
from .models import Author, AuthorTranslation, Book, Sermon
from .serializers import AuthorDetailSerializer


class AuthorAvailableLanguagesTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")

    def _langs(self, author=None):
        return AuthorDetailSerializer(author or self.author).data["available_languages"]

    def test_nothing_of_their_own_is_no_language(self):
        self.assertEqual(self._langs(), [])

    def test_the_source_bio_counts_in_its_own_language(self):
        self.author.bio = "A life."
        self.author.save()
        self.assertEqual(self._langs(), ["en"])

    def test_a_translated_bio_counts_but_an_empty_translation_does_not(self):
        AuthorTranslation.objects.create(author=self.author, language="sw", bio_html="<p>Maisha.</p>")
        AuthorTranslation.objects.create(author=self.author, language="es")
        self.assertEqual(self._langs(), ["sw"])

    def test_published_books_and_sermons_count_unpublished_and_modern_do_not(self):
        Book.objects.create(author=self.author, slug="b", language="es", title="B", is_published=True)
        Book.objects.create(author=self.author, slug="b", language="pt", title="B", is_published=False)
        Book.objects.create(
            author=self.author, slug="b", language=MODERN_LANGUAGE, title="B", is_published=True
        )
        Sermon.objects.create(author=self.author, slug="s", language="lg", title="S", is_published=True)
        self.assertEqual(self._langs(), ["es", "lg"])

    def test_a_translation_in_the_source_language_does_not_count(self):
        # Never served: `_localized` reads the source fields for that language.
        AuthorTranslation.objects.create(author=self.author, language="en", bio="Stray.")
        self.assertEqual(self._langs(), [])

    def test_an_imprint_bio_never_counts(self):
        imprint = Author.objects.create(slug="house", name="House", is_imprint=True, bio="Us.")
        self.assertEqual(self._langs(imprint), [])
