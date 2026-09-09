"""The admin "needs attention" hub endpoint: read-only aggregation of the
content-health and demand signals the dashboard leads with."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    Author,
    Book,
    Chapter,
    Language,
    SearchQueryLog,
    Sermon,
)


class AdminAttentionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray", bio="Preacher.")
        Author.objects.create(slug="cs", name="Charles Spurgeon")  # no bio
        # An imprint with no bio must NOT count against authors_without_bio.
        Author.objects.create(slug="oo", name="Ochorus Originals", is_imprint=True)

        en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=en, order=1, title="One", body_html="<p>one two</p>", word_count=2)
        # An empty chapter (integrity).
        Chapter.objects.create(book=en, order=2, title="Two", body_html="", word_count=0)
        # An unpublished draft with no chapters — expected, NOT an empty_books defect.
        Book.objects.create(
            author=author, slug="secret", language="en", title="Draft", is_published=False
        )
        # A published, unreviewed AI translation (with a chapter, so not "empty").
        sw = Book.objects.create(
            author=author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(book=sw, order=1, title="Moja", body_html="<p>x</p>", word_count=2)
        # A published book with no chapters — the one empty_books defect.
        Book.objects.create(author=author, slug="stub", language="en", title="Stub")

        # French isn't in the seeded registry (the seed ships ar/en/es/lg/pt/sw;
        # fr/hi/uk were added later via the admin), so create it. It gets a sermon
        # but no book → it should surface in languages_missing_books. The seeded
        # languages have no content at all, so none of them do.
        Language.objects.create(code="fr", name="French", native_name="Français")
        Sermon.objects.create(
            author=author, slug="himself", language="fr", title="Lui-même", body_html="<p>x</p>"
        )

        # Search: two zero-result queries out of three in the window.
        SearchQueryLog.objects.create(query="wendy bello", language="es", result_count=0)
        SearchQueryLog.objects.create(query="josé luis navajo", language="es", result_count=0)
        SearchQueryLog.objects.create(query="prayer", language="en", result_count=12)

    @override_settings(DEBUG=True)
    def test_attention_signals(self):
        res = self.client.get("/api/admin/attention/")
        self.assertEqual(res.status_code, 200)
        d = res.data

        self.assertEqual(d["unreviewed_translations"], 1)
        self.assertEqual(d["unpublished_books"], 1)
        self.assertEqual(d["unpublished_sermons"], 0)
        # Two authors have no bio, but one of them is an imprint and is excluded.
        self.assertEqual(d["authors_without_bio"], 1)
        self.assertEqual(d["empty_chapters"], 1)
        self.assertEqual(d["empty_books"], 1)  # "stub" — published, no chapters

        # Only French has content-but-no-books; every other seeded language has
        # nothing at all and is excluded.
        missing = d["languages_missing_books"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["code"], "fr")
        self.assertEqual(missing[0]["name"], "French")
        self.assertEqual(missing[0]["sermons"], 1)

        self.assertEqual(d["searches"]["total_30d"], 3)
        self.assertEqual(d["searches"]["zero_30d"], 2)
        self.assertAlmostEqual(d["searches"]["zero_rate"], 0.667, places=3)

    def test_requires_admin(self):
        # No DEBUG bypass: an anonymous request is refused, like every admin view.
        res = self.client.get("/api/admin/attention/")
        self.assertIn(res.status_code, (401, 403))
