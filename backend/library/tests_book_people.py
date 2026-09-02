"""People found IN a book (``BookPerson``) — the link from a work to the bios of
people it is about or that walk through it, distinct from its author.

Exercises both directions of the reverse link (book → people, person → appears
in), the language gate (no bio in this language → not shown, no English
fallback), and the idempotent seed's tolerance of a bio that hasn't landed yet.
"""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import body_of

from .models import Author, Book, BookPerson, Chapter


class BookPeopleAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # The imprint that "wrote" the anthology, and two people found inside it.
        self.imprint = Author.objects.create(
            slug="ochorus-originals", name="Ochorus Originals", is_imprint=True
        )
        self.whitefield = Author.objects.create(
            slug="george-whitefield", name="George Whitefield",
            bio="A field preacher of the Great Awakening.",
        )
        self.wesley = Author.objects.create(
            slug="john-wesley", name="John Wesley",
            bio="Founder of Methodism.",
        )
        # A person with NO bio at all — nothing to link to, so never shown.
        self.no_bio = Author.objects.create(slug="anon", name="Anon")

        self.book = Book.objects.create(
            author=self.imprint, slug="men-who-moved-heaven", language="en",
            title="Men Who Moved Heaven",
        )
        Chapter.objects.create(
            book=self.book, order=1, title="One", body_html=body_of(50)
        )
        # Order deliberately reversed from sort_order to prove ordering.
        BookPerson.objects.create(
            book_slug="men-who-moved-heaven", person=self.wesley,
            role="mentioned", sort_order=1,
        )
        BookPerson.objects.create(
            book_slug="men-who-moved-heaven", person=self.whitefield,
            role="subject", sort_order=0,
        )
        BookPerson.objects.create(
            book_slug="men-who-moved-heaven", person=self.no_bio,
            role="featured", sort_order=2,
        )

    def test_book_detail_lists_featured_people_in_order(self):
        res = self.client.get("/api/library/books/men-who-moved-heaven/?language=en")
        self.assertEqual(res.status_code, 200)
        people = res.data["featured_people"]
        # Bio-less person dropped; the rest in sort_order, with their roles.
        self.assertEqual(
            [(p["slug"], p["role"]) for p in people],
            [("george-whitefield", "subject"), ("john-wesley", "mentioned")],
        )

    def test_featured_people_language_gated(self):
        # No Swahili bio for either person → nobody to link to on the sw page,
        # even though the book (were it published in sw) would carry the rows.
        Book.objects.create(
            author=self.imprint, slug="men-who-moved-heaven", language="sw",
            title="Watu Walioinua Mbingu",
        )
        res = self.client.get("/api/library/books/men-who-moved-heaven/?language=sw")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["featured_people"], [])

    def test_author_detail_appears_in(self):
        res = self.client.get("/api/library/authors/george-whitefield/?language=en")
        self.assertEqual(res.status_code, 200)
        appears = res.data["appears_in"]
        self.assertEqual(len(appears), 1)
        self.assertEqual(appears[0]["slug"], "men-who-moved-heaven")
        self.assertEqual(appears[0]["role"], "subject")

    def test_appears_in_language_gated(self):
        # A person with content of their OWN in Swahili (so their page exists
        # there) who is featured in an English-only book: the featured book has
        # no sw row, so it drops out of the sw page (no English fallback).
        person = Author.objects.create(slug="q", name="Q", bio="x")
        own = Book.objects.create(
            author=person, slug="q-own", language="sw", title="Kitabu"
        )
        Chapter.objects.create(book=own, order=1, title="i", body_html=body_of(5))
        BookPerson.objects.create(
            book_slug="men-who-moved-heaven", person=person, role="mentioned"
        )
        res = self.client.get("/api/library/authors/q/?language=sw")
        self.assertEqual(res.status_code, 200)
        # Their own sw book shows; the en-only featured book is gated out.
        self.assertEqual([b["slug"] for b in res.data["books"]], ["q-own"])
        self.assertEqual(res.data["appears_in"], [])

    def test_appears_in_honors_curated_order(self):
        # One person featured in two books; the display order follows the
        # person's BookPerson.sort_order, not the books' own order.
        person = Author.objects.create(slug="p", name="P", bio="x")
        for slug, title in (("book-a", "A"), ("book-b", "B")):
            b = Book.objects.create(
                author=self.imprint, slug=slug, language="en", title=title
            )
            Chapter.objects.create(book=b, order=1, title="i", body_html=body_of(5))
        # book-b first (sort_order 0), book-a second (sort_order 1).
        BookPerson.objects.create(book_slug="book-a", person=person, sort_order=1)
        BookPerson.objects.create(book_slug="book-b", person=person, sort_order=0)
        res = self.client.get("/api/library/authors/p/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["slug"] for b in res.data["appears_in"]], ["book-b", "book-a"])

    def test_appears_in_excludes_self_authored(self):
        # A person is featured in a book they also WROTE — it belongs under
        # `books`, not `appears_in`, so the page doesn't list it twice.
        author = Author.objects.create(slug="jw", name="J. W.", bio="x")
        own = Book.objects.create(
            author=author, slug="my-own-book", language="en", title="My Own Book"
        )
        Chapter.objects.create(book=own, order=1, title="I", body_html=body_of(10))
        BookPerson.objects.create(
            book_slug="my-own-book", person=author, role="subject"
        )
        res = self.client.get("/api/library/authors/jw/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["slug"] for b in res.data["books"]], ["my-own-book"])
        self.assertEqual(res.data["appears_in"], [])


class SeedBookPeopleTests(TestCase):
    CMD = "library.management.commands.seed_book_people.BOOK_PEOPLE"

    def test_seed_is_idempotent_and_tolerates_missing_author(self):
        Author.objects.create(slug="george-whitefield", name="George Whitefield")
        seed = [
            (
                "men-who-moved-heaven",
                [("george-whitefield", "subject"), ("ghost-author", "mentioned")],
            )
        ]
        with mock.patch(self.CMD, seed):
            call_command("seed_book_people", stdout=StringIO())
        # The ghost author is skipped, the real one landed.
        self.assertEqual(BookPerson.objects.count(), 1)
        row = BookPerson.objects.get()
        self.assertEqual(row.person.slug, "george-whitefield")
        self.assertEqual(row.role, "subject")
        # Re-running upserts (no duplicate); an edited role is refreshed in place.
        refreshed = [("men-who-moved-heaven", [("george-whitefield", "featured")])]
        with mock.patch(self.CMD, refreshed):
            call_command("seed_book_people", stdout=StringIO())
        self.assertEqual(BookPerson.objects.count(), 1)
        self.assertEqual(BookPerson.objects.get().role, "featured")
