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


class AdminUnpublishedWorklistTests(TestCase):
    """The enumerated worklist behind the "unpublished" attention counts."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        # A published book (excluded) and two unpublished ones (listed).
        pub = Book.objects.create(author=self.author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=pub, order=1, title="One", body_html="<p>x</p>", word_count=2)
        draft = Book.objects.create(
            author=self.author, slug="secret", language="en", title="Secret", is_published=False
        )
        Chapter.objects.create(book=draft, order=1, title="A", body_html="<p>a b c</p>", word_count=3)
        Book.objects.create(
            author=self.author, slug="abide", language="es", title="Permaneced", is_published=False
        )
        # A published and an unpublished sermon.
        Sermon.objects.create(
            author=self.author, slug="grace", language="en", title="Grace", body_html="<p>x</p>"
        )
        Sermon.objects.create(
            author=self.author, slug="mercy", language="en", title="Mercy",
            body_html="<p>x</p>", is_published=False,
        )

    @override_settings(DEBUG=True)
    def test_lists_only_unpublished_with_counts(self):
        res = self.client.get("/api/admin/unpublished/")
        self.assertEqual(res.status_code, 200)
        books = res.data["books"]
        self.assertEqual({(b["slug"], b["language"]) for b in books}, {("secret", "en"), ("abide", "es")})
        secret = next(b for b in books if b["slug"] == "secret")
        self.assertEqual(secret["author"], "Andrew Murray")
        self.assertEqual(secret["chapters"], 1)
        self.assertEqual(secret["words"], 3)

        sermons = res.data["sermons"]
        self.assertEqual([(s["slug"], s["language"]) for s in sermons], [("mercy", "en")])

    def test_requires_admin(self):
        res = self.client.get("/api/admin/unpublished/")
        self.assertIn(res.status_code, (401, 403))


class AdminAuthorsWithoutBioTests(TestCase):
    """The enumerated worklist behind the "authors without a bio" count."""

    def setUp(self):
        self.client = APIClient()
        # Has a bio → excluded.
        Author.objects.create(slug="am", name="Andrew Murray", bio="Preacher.")
        # An imprint with no bio → excluded (never gets a bio).
        Author.objects.create(slug="oo", name="Ochorus Originals", is_imprint=True)
        # Two bio-less people; "busy" carries more content, so ranks first.
        busy = Author.objects.create(slug="busy", name="Busy Writer")
        Book.objects.create(author=busy, slug="b1", language="en", title="B1")
        # A Spanish edition of the SAME work — must NOT make busy read as 3 books.
        Book.objects.create(author=busy, slug="b1", language="es", title="B1 (es)")
        Book.objects.create(author=busy, slug="b2", language="en", title="B2")
        Sermon.objects.create(author=busy, slug="s1", language="en", title="S1", body_html="<p>x</p>")
        Author.objects.create(slug="quiet", name="Quiet Writer")

    @override_settings(DEBUG=True)
    def test_ranks_bio_less_non_imprints_by_content(self):
        res = self.client.get("/api/admin/authors-without-bio/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([a["slug"] for a in res.data], ["busy", "quiet"])
        busy = res.data[0]
        # Distinct works: b1 (en+es) + b2 = 2, not 3 editions.
        self.assertEqual(busy["books"], 2)
        self.assertEqual(busy["sermons"], 1)

    def test_requires_admin(self):
        res = self.client.get("/api/admin/authors-without-bio/")
        self.assertIn(res.status_code, (401, 403))
