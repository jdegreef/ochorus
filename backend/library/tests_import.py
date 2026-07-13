"""Tests for the admin document-upload import (upload_import + the endpoints)."""

from __future__ import annotations

import io
import zipfile

import fitz  # PyMuPDF
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from library import upload_import as ui
from library.models import Author, Book, Sermon

# --- fixtures: build real PDF / DOCX bytes in-memory ------------------------


def make_pdf(pages: list[tuple[str, str]]) -> bytes:
    """pages = [(heading, body)]; heading is large text, body is small text."""
    doc = fitz.open()
    for heading, body in pages:
        page = doc.new_page()
        page.insert_text((72, 90), heading, fontsize=22)
        for i, line in enumerate(body.split("\n")):
            page.insert_text((72, 140 + i * 16), line, fontsize=11)
    return doc.tobytes()


_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>"""

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def make_docx(paragraphs: list[tuple[str | None, str]]) -> bytes:
    """paragraphs = [(style|None, text)]; style 'Heading1' → a chapter heading."""
    body = []
    for style, text in paragraphs:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body.append(f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(body)}</w:body></w:document>'
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/document.xml", document)
    return out.getvalue()


BODY = "This is body text with plenty of words to comfortably clear the minimum count."


class ParseTests(TestCase):
    def test_split_on_headings(self):
        html = "<p>intro</p><h1>One</h1><p>a</p><h2>Two</h2><p>b</p>"
        secs = ui._split_on_headings(html)
        titles = [t for t, _ in secs]
        self.assertIn("One", titles)
        self.assertIn("Two", titles)

    def test_pdf_book_chapterizes_or_falls_back(self):
        data = make_pdf([("Chapter One", BODY + "\n" + BODY), ("Chapter Two", BODY)])
        res = ui.parse_upload(data, "book.pdf", "book")
        self.assertEqual(res["kind"], "book")
        self.assertGreaterEqual(len(res["chapters"]), 1)
        self.assertTrue(all(c["words"] >= 5 for c in res["chapters"]))

    def test_pdf_sermon_is_single_body(self):
        data = make_pdf([("Sermon", BODY)])
        res = ui.parse_upload(data, "s.pdf", "sermon")
        self.assertEqual(len(res["chapters"]), 1)

    def test_docx_book_splits_on_word_headings(self):
        data = make_docx(
            [("Heading1", "Chapter One"), (None, BODY), ("Heading1", "Chapter Two"), (None, BODY)]
        )
        res = ui.parse_upload(data, "book.docx", "book")
        self.assertEqual(len(res["chapters"]), 2)
        self.assertEqual(res["chapters"][0]["title"], "Chapter One")

    def test_docx_sermon(self):
        data = make_docx([(None, BODY)])
        res = ui.parse_upload(data, "s.docx", "sermon")
        self.assertEqual(len(res["chapters"]), 1)
        self.assertIn("body text", res["chapters"][0]["html"])

    def test_scanned_pdf_rejected(self):
        blank = fitz.open()
        blank.new_page()
        with self.assertRaises(ui.ParseError):
            ui.parse_upload(blank.tobytes(), "scan.pdf", "book")

    def test_unsupported_file_rejected(self):
        with self.assertRaises(ui.ParseError):
            ui.parse_upload(b"hello", "notes.txt", "book")

    def test_corrupt_pdf_raises_parse_error(self):
        # A file named .pdf whose bytes aren't a valid PDF must surface as a
        # ParseError (→ 400), not an uncaught PyMuPDF error (→ 500).
        with self.assertRaises(ui.ParseError):
            ui.parse_upload(b"%PDF-not-really-a-pdf", "broken.pdf", "book")

    def test_docx_front_matter_heading_dropped(self):
        # A "Contents" heading is front matter and must not become a chapter,
        # matching the PDF chapterizer's behaviour.
        data = make_docx(
            [("Heading1", "Contents"), (None, BODY), ("Heading1", "Chapter One"), (None, BODY)]
        )
        res = ui.parse_upload(data, "book.docx", "book")
        titles = [c["title"] for c in res["chapters"]]
        self.assertNotIn("Contents", titles)
        self.assertIn("Chapter One", titles)


class CreateTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="a-writer", name="A Writer")

    def test_create_book(self):
        chapters = [{"title": "One", "html": f"<p>{BODY}</p>"}, {"title": "", "html": f"<p>{BODY}</p>"}]
        book = ui.create_book(self.author, "My Book", chapters, "en")
        self.assertEqual(book.chapters.count(), 2)
        self.assertEqual(book.chapters.get(order=2).title, "Chapter 2")  # untitled → numbered
        self.assertTrue(book.chapters.first().body_text)  # derived on save

    def test_slug_uniqueness(self):
        b1 = ui.create_book(self.author, "Same Name", [{"title": "x", "html": f"<p>{BODY}</p>"}], "en")
        b2 = ui.create_book(self.author, "Same Name", [{"title": "x", "html": f"<p>{BODY}</p>"}], "en")
        self.assertNotEqual(b1.slug, b2.slug)

    def test_create_sermon(self):
        s = ui.create_sermon(self.author, "A Sermon", f"<p>{BODY}</p>", "en", scripture_ref="John 3:16")
        self.assertEqual(s.scripture_ref, "John 3:16")
        self.assertGreater(s.word_count, 5)

    def test_create_book_empty_rolls_back(self):
        # No chapter clears the word floor → ParseError, and the Book row is
        # rolled back (no orphan) rather than left behind for the view to delete.
        with self.assertRaises(ui.ParseError):
            ui.create_book(self.author, "Empty", [{"title": "x", "html": "<p>hi</p>"}], "en")
        self.assertFalse(Book.objects.filter(title="Empty").exists())

    def test_create_book_tolerates_non_dict_chapters(self):
        chapters = ["junk", None, {"title": "Real", "html": f"<p>{BODY}</p>"}]
        book = ui.create_book(self.author, "Mixed", chapters, "en")
        self.assertEqual(book.chapters.count(), 1)

    def test_create_book_truncates_long_titles(self):
        long = "T" * 400
        book = ui.create_book(self.author, long, [{"title": long, "html": f"<p>{BODY}</p>"}], "en")
        self.assertLessEqual(len(book.title), 300)
        self.assertLessEqual(len(book.chapters.first().title), 300)

    def test_create_sermon_blank_body_rejected(self):
        # Tag-only markup cleans to nothing → ParseError, no blank sermon saved.
        with self.assertRaises(ui.ParseError):
            ui.create_sermon(self.author, "Blank", "<script>x</script>", "en")
        self.assertFalse(Sermon.objects.filter(title="Blank").exists())

    def test_create_book_with_metadata(self):
        book = ui.create_book(
            self.author,
            "Rich",
            [{"title": "One", "html": f"<p>{BODY}</p>"}],
            "en",
            subtitle="A Subtitle",
            cover_color="#3b5bdb",
            cover_url="https://example.org/c.jpg",
            publication_year=1885,
            attribution="Public domain — CCEL scan",
        )
        self.assertEqual(book.subtitle, "A Subtitle")
        self.assertEqual(book.cover_color, "#3b5bdb")
        self.assertEqual(book.cover_url, "https://example.org/c.jpg")
        self.assertEqual(book.publication_year, 1885)
        self.assertEqual(book.attribution, "Public domain — CCEL scan")

    def test_create_book_metadata_is_validated(self):
        # Bad hex, non-http cover url, and out-of-range year are dropped, not stored.
        book = ui.create_book(
            self.author,
            "Bad Meta",
            [{"title": "One", "html": f"<p>{BODY}</p>"}],
            "en",
            cover_color="red; drop table",
            cover_url="javascript:alert(1)",
            publication_year=99999,
        )
        self.assertEqual(book.cover_color, "")
        self.assertEqual(book.cover_url, "")
        self.assertIsNone(book.publication_year)


@override_settings(DEBUG=True)  # bypasses the admin email gate (see permissions)
class EndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="e-writer", name="E Writer")

    def test_parse_then_publish_book(self):
        pdf = make_pdf([("Chapter One", BODY + "\n" + BODY)])
        upload = io.BytesIO(pdf)
        upload.name = "book.pdf"
        r = self.client.post("/api/admin/import/parse/", {"file": upload, "kind": "book"}, format="multipart")
        self.assertEqual(r.status_code, 200)
        chapters = r.json()["chapters"]
        self.assertGreaterEqual(len(chapters), 1)

        r2 = self.client.post(
            "/api/admin/import/publish/",
            {"kind": "book", "author_slug": "e-writer", "title": "Published Book", "chapters": chapters},
            format="json",
        )
        self.assertEqual(r2.status_code, 201)
        self.assertTrue(Book.objects.filter(slug=r2.json()["slug"]).exists())
        self.assertEqual(r2.json()["path"], f"/books/{r2.json()['slug']}")

    def test_publish_sermon(self):
        r = self.client.post(
            "/api/admin/import/publish/",
            {"kind": "sermon", "author_slug": "e-writer", "title": "Pub Sermon", "body_html": f"<p>{BODY}</p>"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Sermon.objects.filter(slug=r.json()["slug"]).exists())

    def test_parse_requires_file(self):
        r = self.client.post("/api/admin/import/parse/", {"kind": "book"}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_publish_unknown_author(self):
        r = self.client.post(
            "/api/admin/import/publish/",
            {"kind": "sermon", "author_slug": "nobody", "title": "X", "body_html": f"<p>{BODY}</p>"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_corrupt_pdf_upload_is_400_not_500(self):
        upload = io.BytesIO(b"%PDF-broken")
        upload.name = "broken.pdf"
        r = self.client.post(
            "/api/admin/import/parse/", {"file": upload, "kind": "book"}, format="multipart"
        )
        self.assertEqual(r.status_code, 400)

    def test_publish_book_all_empty_is_400(self):
        r = self.client.post(
            "/api/admin/import/publish/",
            {
                "kind": "book",
                "author_slug": "e-writer",
                "title": "No Text",
                "chapters": [{"title": "x", "html": "<p>hi</p>"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Book.objects.filter(title="No Text").exists())

    def test_import_languages_lists_more_than_content_languages(self):
        # No books exist, yet the picker must still offer languages to import into.
        r = self.client.get("/api/admin/import/languages/")
        self.assertEqual(r.status_code, 200)
        codes = {row["code"] for row in r.json()}
        self.assertIn("en", codes)
        self.assertIn("fr", codes)  # a supported language with no content yet

    def test_publish_book_persists_metadata(self):
        r = self.client.post(
            "/api/admin/import/publish/",
            {
                "kind": "book",
                "author_slug": "e-writer",
                "title": "Meta Book",
                "subtitle": "The Sub",
                "cover_color": "#112233",
                "publication_year": 1900,
                "attribution": "PD",
                "chapters": [{"title": "One", "html": f"<p>{BODY}</p>"}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        book = Book.objects.get(slug=r.json()["slug"])
        self.assertEqual(book.subtitle, "The Sub")
        self.assertEqual(book.cover_color, "#112233")
        self.assertEqual(book.publication_year, 1900)
        self.assertEqual(book.attribution, "PD")


@override_settings(DEBUG=True)  # bypasses the admin email gate (see permissions)
class AuthorCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_author(self):
        r = self.client.post("/api/admin/authors/", {"name": "John Owen"}, format="json")
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["slug"], "john-owen")
        self.assertEqual(body["book_count"], 0)
        self.assertTrue(Author.objects.filter(slug="john-owen").exists())

    def test_create_author_dedupes_slug(self):
        Author.objects.create(slug="john-owen", name="John Owen")
        r = self.client.post("/api/admin/authors/", {"name": "John Owen"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["slug"], "john-owen-2")

    def test_create_author_requires_name(self):
        r = self.client.post("/api/admin/authors/", {"name": "   "}, format="json")
        self.assertEqual(r.status_code, 400)


@override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
class ImportAuthTests(TestCase):
    def test_import_endpoints_require_admin(self):
        client = APIClient()
        self.assertEqual(client.post("/api/admin/import/parse/").status_code, 401)
        self.assertEqual(client.post("/api/admin/import/publish/").status_code, 401)
        self.assertEqual(client.post("/api/admin/authors/").status_code, 401)
