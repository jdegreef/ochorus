"""The hand-written search snippets in ``data/book_meta/<language>.json``.

The file is keyed by slug, not joined to a row, so nothing in the schema stops
it pointing at a book that was renamed or withdrawn, or growing a snippet past
what a result shows. These are the gates that do.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from library.meta_descriptions import MAX_LENGTH, meta_description, table
from library.models import Author, Book

BOOKS = Path(__file__).parent / "fixtures" / "content" / "books"


def _published(slug: str, language: str) -> bool:
    path = BOOKS / f"{slug}.{language}.json"
    if not path.exists():
        return False
    row = json.loads(path.read_text(encoding="utf-8"))[0]
    return row["model"] == "library.book" and bool(row["fields"].get("is_published"))


class MetaDescriptionFileTests(SimpleTestCase):
    def setUp(self):
        self.table = table()

    def test_every_snippet_names_a_published_edition(self):
        stray = [
            f"{lang}/{slug}"
            for lang, rows in self.table.items()
            for slug in rows
            if not _published(slug, lang)
        ]
        self.assertEqual(stray, [], "snippets for a book that is renamed, withdrawn or missing")

    def test_every_snippet_fits_the_budget(self):
        wrong = [
            f"{lang}/{slug} ({len(text)})"
            for lang, rows in self.table.items()
            for slug, text in rows.items()
            if not (40 <= len(text) <= MAX_LENGTH) or text != text.strip()
        ]
        self.assertEqual(wrong, [])

    def test_every_published_english_book_has_one(self):
        # English is the source language and fully covered; a new English book
        # ships with its snippet, like it ships with its description.
        english = self.table.get("en", {})
        missing = sorted(
            p.name.removesuffix(".en.json")
            for p in BOOKS.glob("*.en.json")
            if _published(p.name.removesuffix(".en.json"), "en")
            and p.name.removesuffix(".en.json") not in english
        )
        self.assertEqual(missing, [], "published English books with no snippet")


class MetaDescriptionApiTests(TestCase):
    def test_the_book_detail_carries_the_snippet_or_nothing(self):
        slug, text = next(iter(table()["en"].items()))
        author = Author.objects.create(slug="a", name="A Writer")
        Book.objects.create(author=author, slug=slug, language="en", title="T", is_published=True)
        Book.objects.create(author=author, slug="unwritten", language="en", title="U", is_published=True)
        self.assertEqual(meta_description(slug, "en"), text)
        res = self.client.get(f"/api/library/books/{slug}/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["meta_description"], text)
        res = self.client.get("/api/library/books/unwritten/?language=en")
        self.assertEqual(res.data["meta_description"], "")
