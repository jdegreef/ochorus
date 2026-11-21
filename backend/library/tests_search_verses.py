"""A verse found by its words: "for god so loved the world" → John 3:16."""

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from . import bible_store
from .models import Author, Sermon
from .scripture import quoted_reference


class QuotedReferenceTests(SimpleTestCase):
    def test_the_words_of_a_verse_name_it(self):
        for words, ref in [
            ("for god so loved the world", "John 3:16"),  # the ASV's (KJV-era) wording
            ("love is patient", "1 Corinthians 13:4"),  # the OWB's
            ("Be still, and know", "Psalms 46:10"),  # punctuation and case don't matter
            ("all things work together for good", "Romans 8:28"),
        ]:
            with self.subTest(words):
                self.assertEqual(quoted_reference(words), ref)

    def test_short_common_or_typed_references_name_nothing(self):
        for words in ["prayer", "the lord", "the love of god", "the holy spirit", "john 3:16", "abide in christ"]:
            with self.subTest(words):
                self.assertIsNone(quoted_reference(words))

    def test_the_phrase_is_plain_words_never_fts_syntax(self):
        self.assertEqual(bible_store.phrase(['"so', "loved)", "the*", "world"])[:1], [43003016])
        self.assertEqual(bible_store.phrase(["", "!!"]), [])


class VerseSearchTests(TestCase):
    def setUp(self):
        spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="Charles H. Spurgeon")
        Sermon.objects.create(
            author=spurgeon, slug="the-love-of-god", language="en", title="The Love of God",
            scripture_ref="John 3:14-21", body_html="<p>Look and live.</p>",
        )

    def test_the_search_names_the_verse_and_leads_with_what_preaches_it(self):
        data = APIClient().get(
            "/api/library/search/", {"q": "for god so loved the world", "language": "en"}
        ).data
        self.assertEqual(data["verse"], "John 3:16")
        self.assertEqual(data["results"][0]["sermon_slug"], "the-love-of-god")

    def test_not_outside_english(self):
        data = APIClient().get(
            "/api/library/search/", {"q": "for god so loved the world", "language": "es"}
        ).data
        self.assertNotIn("verse", data)
