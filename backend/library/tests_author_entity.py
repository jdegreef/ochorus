"""`Author.same_as` — the entity identifiers behind the author page's Person markup.

WHAT THIS CAN AND CANNOT GUARD. Whether a URL names the RIGHT person is a human
check: nothing here can tell Thomas Watson the Puritan from Thomas Watson the
IBM chairman, and a wrong identifier is worse than none because it tells search
engines the page is about somebody else. So these tests guard everything else —
shape, scope, and the rules that would let a bad value in quietly — and the
identity check stays with the person who wrote the row.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from .author_sync import sync_author
from .models import Author

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "content" / "authors.json"

#: The vocabularies we actually publish. Deliberately a closed list: `sameAs`
#: is only as strong as the authority behind it, and a link to a blog or a
#: bookseller dilutes the claim rather than supporting it.
ALLOWED_HOSTS = ("en.wikipedia.org", "www.wikidata.org")


def fixture_authors() -> list[dict]:
    return [r["fields"] for r in json.loads(FIXTURE.read_text()) if r["model"] == "library.author"]


class FixtureIdentifierTests(SimpleTestCase):
    """Shape and scope of what ships in `authors.json`."""

    def test_every_identifier_is_an_absolute_url_on_an_authority_we_trust(self):
        for a in fixture_authors():
            for url in a.get("same_as", []):
                with self.subTest(author=a["slug"], url=url):
                    self.assertTrue(url.startswith("https://"), "must be absolute https")
                    host = url.split("/")[2]
                    self.assertIn(host, ALLOWED_HOSTS)

    def test_a_wikidata_identifier_is_a_q_number(self):
        # A Wikidata URL that is not an item — a property, a lexeme, a search
        # page — is not an identifier, and would assert something false.
        for a in fixture_authors():
            for url in a.get("same_as", []):
                if "wikidata.org" in url:
                    with self.subTest(author=a["slug"], url=url):
                        self.assertRegex(url, r"^https://www\.wikidata\.org/wiki/Q\d+$")

    def test_no_author_carries_the_same_identifier_twice(self):
        for a in fixture_authors():
            urls = a.get("same_as", [])
            with self.subTest(author=a["slug"]):
                self.assertEqual(len(urls), len(set(urls)))

    def test_two_authors_never_share_an_identifier(self):
        # The failure this catches is a copy-paste between neighbouring rows,
        # which would claim two of our writers are the same human being.
        seen: dict[str, str] = {}
        for a in fixture_authors():
            for url in a.get("same_as", []):
                self.assertNotIn(
                    url, seen, f"{a['slug']} and {seen.get(url)} share {url}"
                )
                seen[url] = a["slug"]

    def test_an_imprint_never_gets_a_person_identifier(self):
        # "Ochorus Originals" is a house byline. Pointing it at a real person
        # would be a false claim about who wrote those books.
        for a in fixture_authors():
            if a.get("is_imprint"):
                with self.subTest(author=a["slug"]):
                    self.assertEqual(a.get("same_as", []), [])

    def test_an_imprint_never_carries_a_bio(self):
        # A byline is not a person, so it presents no biography: no short bio,
        # no long-form bio_html, no editorial Q&A. Keeps the fixture side of the
        # rule the `bio_for`/`faq_for` guards enforce at read time; a bio typed
        # into an imprint row here would render it as an author with a life.
        for a in fixture_authors():
            if a.get("is_imprint"):
                with self.subTest(author=a["slug"]):
                    self.assertEqual((a.get("bio") or "").strip(), "")
                    self.assertEqual((a.get("bio_html") or "").strip(), "")
                    self.assertEqual(a.get("faq", []), [])

    def test_a_wikipedia_identifier_names_an_article_not_a_search(self):
        for a in fixture_authors():
            for url in a.get("same_as", []):
                if "wikipedia.org" in url:
                    with self.subTest(author=a["slug"], url=url):
                        self.assertRegex(url, r"^https://en\.wikipedia\.org/wiki/[^?#]+$")

    def test_the_historical_writers_are_actually_covered(self):
        # A ratchet, not a target. Unlike almost everything else about this
        # library, the entity work is FINISHABLE: it scales with the number of
        # writers, not the number of books, so coverage going backwards is a
        # mistake rather than a backlog.
        with_ids = [a for a in fixture_authors() if a.get("same_as")]
        self.assertGreaterEqual(len(with_ids), 36)

    def test_every_author_is_either_identified_or_deliberately_not(self):
        """No author may sit in the gap between "researched" and "decided".

        The failure this prevents is silent: a writer added later inherits an
        empty list, which is indistinguishable from one we looked into and
        chose to leave blank. Naming the exceptions means adding a writer
        WITHOUT an identifier is a decision someone has to make here.
        """
        # A house byline, two living contributors, and a writer with no
        # article to point at.
        expected_blank = {
            "ochorus-originals",
            "gareth-evans",
            "hannah-buyinza",
            "simeon-nsibambi",
            # East African Revival figures with no verified standalone
            # Wikipedia/Wikidata entity to point at — a wrong identifier is
            # worse than none, so these stay blank until one is confirmed.
            # (Their better-documented peers — joe-church, janani-luwum,
            # yona-kanamuzeyi — carry same_as.)
            "yosiya-kinuka",
            "blasio-kigozi",
            "william-nagenda",
            "lawrence-barham",
            # No Wikipedia article (the "Charles S. Price" there is a ship)
            # and no Wikidata item for the evangelist.
            "charles-s-price",
        }
        blank = {a["slug"] for a in fixture_authors() if not a.get("same_as")}
        self.assertEqual(
            blank,
            expected_blank,
            "an author has no identifiers and is not on the known-blank list — "
            "research them, or add them here with a reason",
        )


class SyncTests(TestCase):
    """`same_as` is fixture-owned, unlike the fill-only author fields."""

    def setUp(self):
        self.author = Author.objects.create(slug="w", name="A Writer")

    def test_an_empty_row_is_filled(self):
        sync_author(self.author, {"same_as": ["https://en.wikipedia.org/wiki/X"]})
        self.author.refresh_from_db()
        self.assertEqual(self.author.same_as, ["https://en.wikipedia.org/wiki/X"])

    def test_a_wrong_identifier_can_be_CORRECTED_by_the_fixture(self):
        # The reason this field is not fill-only. An identifier pointing at the
        # wrong person is exactly what has to be fixable by editing the fixture
        # and deploying, rather than needing a data migration.
        self.author.same_as = ["https://en.wikipedia.org/wiki/Wrong_Person"]
        self.author.save()
        sync_author(self.author, {"same_as": ["https://en.wikipedia.org/wiki/Right_Person"]})
        self.author.refresh_from_db()
        self.assertEqual(self.author.same_as, ["https://en.wikipedia.org/wiki/Right_Person"])

    def test_the_fixture_can_clear_them(self):
        self.author.same_as = ["https://en.wikipedia.org/wiki/X"]
        self.author.save()
        sync_author(self.author, {"same_as": []})
        self.author.refresh_from_db()
        self.assertEqual(self.author.same_as, [])

    def test_a_row_that_omits_the_key_leaves_the_value_alone(self):
        # An older serialization must not read as "clear it".
        self.author.same_as = ["https://en.wikipedia.org/wiki/X"]
        self.author.save()
        changed, _ = sync_author(self.author, {"bio": ""})
        self.author.refresh_from_db()
        self.assertEqual(self.author.same_as, ["https://en.wikipedia.org/wiki/X"])
        self.assertNotIn("same_as", changed)

    def test_an_unchanged_row_writes_nothing(self):
        # The seeds run on every deploy; a no-op has to stay a no-op.
        self.author.same_as = ["https://en.wikipedia.org/wiki/X"]
        self.author.save()
        changed, _ = sync_author(self.author, {"same_as": ["https://en.wikipedia.org/wiki/X"]})
        self.assertEqual(changed, [])


class ApiTests(TestCase):
    """The author page can only mark up what the API sends it."""

    def test_the_detail_endpoint_carries_the_identifiers(self):
        Author.objects.create(
            slug="w",
            name="A Writer",
            same_as=["https://www.wikidata.org/wiki/Q1"],
        )
        res = self.client.get("/api/library/authors/w/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["same_as"], ["https://www.wikidata.org/wiki/Q1"])

    def test_the_book_detail_carries_its_author_identifiers(self):
        """The book page emits Person markup, so it needs them too.

        Only the DETAIL payload: a book CARD emits no Person markup, so putting
        these on AuthorSerializer would ship the same handful of URLs on all 130
        rows of a shelf for nothing to read.
        """
        from .models import Book, Chapter

        writer = Author.objects.create(
            slug="w2", name="A Writer", same_as=["https://www.wikidata.org/wiki/Q2"]
        )
        book = Book.objects.create(
            author=writer, slug="b2", language="en", title="A Work"
        )
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
        res = self.client.get("/api/library/books/b2/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["author_same_as"], ["https://www.wikidata.org/wiki/Q2"])
        # The card nested inside carries none — that is the point.
        self.assertNotIn("same_as", res.data["author"])

    def test_a_book_whose_author_has_none_sends_an_empty_list(self):
        from .models import Book, Chapter

        writer = Author.objects.create(slug="w3", name="Nobody")
        book = Book.objects.create(
            author=writer, slug="b3", language="en", title="Another"
        )
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
        self.assertEqual(
            self.client.get("/api/library/books/b3/").data["author_same_as"], []
        )

    def test_an_author_without_any_sends_an_empty_list_not_null(self):
        # `sameAs: null` in JSON-LD is invalid; the page tests for length, so
        # the shape has to be a list either way.
        Author.objects.create(slug="x", name="Another")
        res = self.client.get("/api/library/authors/x/")
        self.assertEqual(res.data["same_as"], [])

    def test_an_imprint_presents_no_biography_even_if_one_is_stored(self):
        # The durable half of the "a byline is not an author with a bio" rule:
        # whatever a stray admin edit leaves in the row, the reader-facing
        # methods and the detail endpoint withhold the biographical surface.
        imprint = Author.objects.create(
            slug="house",
            name="A House Byline",
            is_imprint=True,
            bio="Should never be shown.",
            bio_html="<p>Nor this.</p>",
            faq=[{"q": "Who?", "a": "Nobody — it is a byline."}],
        )
        self.assertEqual(imprint.bio_for("en"), "")
        self.assertEqual(imprint.bio_html_for("en"), "")
        self.assertEqual(imprint.faq_for("en"), [])
        self.assertFalse(imprint.has_bio_in("en"))

        res = self.client.get("/api/library/authors/house/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["bio"], "")
        self.assertEqual(res.data["bio_html"], "")
        self.assertEqual(res.data["faq"], [])
