"""`Book.about_html` — the page's own prose about the work.

WHY IT IS GUARDED AT ALL. The chapters are not what distinguishes a book page
here: CCEL, Gutenberg and a dozen reprints carry the same public-domain text
verbatim. This field is the part that is Ochorus's own, which makes a stub or a
truncation expensive in a way a missing chapter title is not — a page that
looks written but says nothing is worse than one that says nothing.

WHAT THIS CANNOT GUARD: whether the prose is TRUE. That a work was published in
1663, or that Baxter catechised eight hundred families, is a human check
against a source, and no test can make it. These guard shape — that what ships
is clean, styleable, substantial, and reaches the page it was written for.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from .models import Author, Book
from .sanitize import clean_fragment

BOOKS = Path(__file__).resolve().parent / "fixtures" / "content" / "books"

#: The page styles this prose with plain body type and nothing else, so the
#: content is held to paragraphs. A heading or a list shipped here would render
#: unstyled — the book page has no `.bio`-style :global block behind it.
ALLOWED_TAGS = {"p"}

#: Item 5 of the book-page review asked for 200-300 words. The floor is what a
#: gate can usefully assert: below it the section is a stub, and a stub under a
#: heading that promises an essay is the failure mode worth catching.
MIN_WORDS = 150


def shipped() -> list[tuple[str, str, str]]:
    """``(slug, language, about_html)`` for every edition that carries one."""
    out = []
    for path in BOOKS.glob("*.json"):
        slug, language, _ = path.name.rsplit(".", 2)
        row = next(
            r for r in json.loads(path.read_text()) if r["model"] == "library.book"
        )
        html = row["fields"].get("about_html", "")
        if html:
            out.append((slug, language, html))
    return out


class ShippedProseTests(SimpleTestCase):
    def test_there_is_some(self):
        """Guards the guard: an empty corpus would pass everything below."""
        self.assertGreaterEqual(len(shipped()), 10)

    def test_every_piece_is_already_sanitizer_clean(self):
        """What is in the repo is what ships — the seed does not rewrite it.

        So the committed bytes must already be what `clean_fragment` would
        produce, rather than merely surviving it.
        """
        for slug, language, html in shipped():
            with self.subTest(slug=slug, language=language):
                self.assertEqual(clean_fragment(html), html)

    def test_every_piece_uses_only_tags_the_page_styles(self):
        for slug, language, html in shipped():
            with self.subTest(slug=slug, language=language):
                self.assertEqual(set(re.findall(r"<(\w+)", html)), ALLOWED_TAGS)

    def test_every_paragraph_is_closed(self):
        for slug, language, html in shipped():
            with self.subTest(slug=slug, language=language):
                self.assertEqual(html.count("<p>"), html.count("</p>"))

    def test_no_piece_is_a_stub(self):
        for slug, language, html in shipped():
            words = len(re.sub(r"<[^>]+>", " ", html).split())
            with self.subTest(slug=slug, language=language, words=words):
                self.assertGreaterEqual(words, MIN_WORDS)

    def test_no_piece_merely_restates_the_description(self):
        """The two fields have different jobs — one is the SERP snippet, one is
        the page. A copy-paste between them wastes the second."""
        for path in BOOKS.glob("*.json"):
            row = next(
                r for r in json.loads(path.read_text()) if r["model"] == "library.book"
            )
            f = row["fields"]
            about = re.sub(r"<[^>]+>", " ", f.get("about_html", "")).strip()
            desc = (f.get("description") or "").strip()
            if about and desc:
                with self.subTest(file=path.name):
                    self.assertNotIn(desc, about)


class PayloadTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="john-owen", name="John Owen")

    def _book(self, **kw):
        return Book.objects.create(
            author=self.author, slug="mortification-of-sin", language="en",
            title="The Mortification of Sin in Believers", **kw
        )

    def test_the_detail_payload_carries_it(self):
        from .serializers import BookDetailSerializer

        book = self._book(about_html="<p>Be killing sin.</p>")
        self.assertEqual(
            BookDetailSerializer(book).data["about_html"], "<p>Be killing sin.</p>"
        )

    def test_a_book_without_one_sends_an_empty_string(self):
        from .serializers import BookDetailSerializer

        self.assertEqual(BookDetailSerializer(self._book()).data["about_html"], "")

    def test_the_shelf_card_does_not_carry_it(self):
        """300 words on every one of 130 rows, for a card that cannot show it."""
        from .serializers import BookListSerializer

        book = self._book(about_html="<p>Be killing sin.</p>")
        self.assertNotIn("about_html", BookListSerializer(book).data)


class QaPayloadTests(TestCase):
    """`Book.qa` — editorial Questions & Answers, the same contract the sermon
    and author Q&A use, exposed under the unified serializer key `qa` with
    `{question, answer}` items. Detail carries it; the shelf card does not."""

    def setUp(self):
        self.author = Author.objects.create(slug="john-owen", name="John Owen")

    def _book(self, **kw):
        return Book.objects.create(
            author=self.author, slug="mortification-of-sin", language="en",
            title="The Mortification of Sin in Believers", **kw
        )

    def test_the_detail_payload_carries_it(self):
        from .serializers import BookDetailSerializer

        qa = [{"question": "What is it about?", "answer": "Killing sin."}]
        book = self._book(qa=qa)
        self.assertEqual(BookDetailSerializer(book).data["qa"], qa)

    def test_a_book_without_one_sends_an_empty_list(self):
        from .serializers import BookDetailSerializer

        self.assertEqual(BookDetailSerializer(self._book()).data["qa"], [])

    def test_the_shelf_card_does_not_carry_it(self):
        from .serializers import BookListSerializer

        book = self._book(qa=[{"question": "Q?", "answer": "A."}])
        self.assertNotIn("qa", BookListSerializer(book).data)


class SeedTests(TestCase):
    def test_the_seed_carries_it_through_and_keeps_it_current(self):
        """Fixture-owned editorial prose, like `description`: an edit to the
        committed file must reach an existing row, not only a new one."""
        from library.management.commands.seed_books import BOOK_FIELDS, UPDATE_FIELDS

        self.assertIn("about_html", BOOK_FIELDS)
        self.assertIn("about_html", UPDATE_FIELDS)

    def test_the_seed_keeps_qa_current(self):
        """`qa` is fixture-owned like `about_html` — an expanded set in the
        committed file must reach an existing row on the next deploy, so it is
        an update field, not create-only."""
        from library.management.commands.seed_books import BOOK_FIELDS, UPDATE_FIELDS

        self.assertIn("qa", BOOK_FIELDS)
        self.assertIn("qa", UPDATE_FIELDS)
