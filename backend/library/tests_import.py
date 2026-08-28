"""Tests for the admin document-upload import (upload_import + the endpoints)."""

from __future__ import annotations

import importlib
import io
import zipfile
from unittest import mock

import fitz  # PyMuPDF
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from library import upload_import as ui
from library.catalog import AUTHORS, BOOKS
from library.ingest import upsert_book
from library.models import Author, Book, Sermon

MIGRATION_0092 = importlib.import_module(
    "library.migrations.0092_way_into_holiest_restated_headings"
)

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
        self.assertEqual(res["warnings"], [])  # chapter checks don't apply to a sermon

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
        # Untitled stays untitled. It used to be stored as "Chapter 2", which the
        # reader — printing the order itself — then rendered "2. Chapter 2". The
        # reader now names an untitled chapter, and `upsert_book` takes the same
        # line, so the two import paths agree on what a nameless chapter is.
        self.assertEqual(book.chapters.get(order=2).title, "")
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

    def test_clean_hex_only_accepts_valid_css_lengths(self):
        self.assertEqual(ui._clean_hex("#123"), "#123")  # 3
        self.assertEqual(ui._clean_hex("#1234"), "#1234")  # 4
        self.assertEqual(ui._clean_hex("#112233"), "#112233")  # 6
        self.assertEqual(ui._clean_hex("#11223344"), "#11223344")  # 8
        self.assertEqual(ui._clean_hex("#12345"), "")  # 5 — invalid CSS hex
        self.assertEqual(ui._clean_hex("#1234567"), "")  # 7 — invalid CSS hex

    def test_http_url_requires_a_real_scheme(self):
        self.assertEqual(ui._http_url("httpfoo"), "")  # startswith("http") is not enough
        self.assertEqual(ui._http_url("httpx://evil"), "")
        self.assertEqual(ui._http_url("https://ok.example/x.jpg"), "https://ok.example/x.jpg")

    def test_create_book_tolerates_non_string_metadata(self):
        # A malformed payload sending a number/None must not crash create_book.
        book = ui.create_book(
            self.author,
            "Coerced",
            [{"title": "One", "html": f"<p>{BODY}</p>"}],
            "en",
            subtitle=1885,  # int, not str
            cover_color=123,
            attribution=None,
        )
        self.assertEqual(book.subtitle, "1885")
        self.assertEqual(book.cover_color, "")
        self.assertEqual(book.attribution, "")


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
        self.assertIsInstance(r.json()["warnings"], list)  # QA audit runs on the preview

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
        # A genuinely supported language with no content yet. This asserted "fr"
        # while the picker came from a hardcoded display map — but French had no
        # Bible, no glossary, no UI locale and no content: it was aspirational
        # text, not a supported target. Arabic is the real case — wired
        # end-to-end (verified Bible, complete glossary, UI locale) and still a
        # draft awaiting its first book, which is exactly what you'd import into.
        self.assertIn("ar", codes)

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

    def test_create_author_long_name_slug_within_limit(self):
        # A very long name, created twice so the second collides, must not
        # overflow SlugField(120) when the -N suffix is appended.
        long_name = "Reverend " + ("Wordsworth " * 40)
        r1 = self.client.post("/api/admin/authors/", {"name": long_name}, format="json")
        r2 = self.client.post("/api/admin/authors/", {"name": long_name}, format="json")
        self.assertEqual((r1.status_code, r2.status_code), (201, 201))
        self.assertLessEqual(len(r1.json()["slug"]), 120)
        self.assertLessEqual(len(r2.json()["slug"]), 120)
        self.assertNotEqual(r1.json()["slug"], r2.json()["slug"])


@override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
class ImportAuthTests(TestCase):
    def test_import_endpoints_require_admin(self):
        client = APIClient()
        self.assertEqual(client.post("/api/admin/import/parse/").status_code, 401)
        self.assertEqual(client.post("/api/admin/import/publish/").status_code, 401)
        self.assertEqual(client.post("/api/admin/authors/").status_code, 401)


class TocLineDetectionTests(TestCase):
    """Contents-page lines are dropped; prose that merely uses dots is not.

    `_TOC_LINE_RE` used to be a bare `\\.{4,}`, so ANY block containing four
    consecutive dots was deleted as page furniture. This author writes with
    ellipses ("..... and blessed is he"), and the importer silently ate a
    1 Corinthians 12 quotation and a whole giftings list out of "Soar Like the
    Eagle". A contents line is dots leading TO A PAGE NUMBER.
    """

    def _chapterize(self, blocks):
        from library.management.commands.import_ochorus import chapterize

        return chapterize(blocks, 12.0)

    def test_contents_lines_are_still_dropped(self):
        from library.management.commands.import_ochorus import _TOC_LINE_RE

        for line in (
            "FLYING HIGH ............................................... 2",
            "Chapter Two ...................................... 13",
            "Appendix .... 137",
        ):
            self.assertTrue(_TOC_LINE_RE.search(line), line)

    def test_prose_with_an_ellipsis_survives(self):
        from library.management.commands.import_ochorus import _TOC_LINE_RE

        for line in (
            "vv 12 - 27 by one Spirit we were baptized into one body ... the body "
            "is not one member but many..... The ear cannot say to the eye",
            "Secular (the rod in my hand): airman or mariner; .... catering",
            ".....and blessed is he who is not offended by me!",
        ):
            self.assertIsNone(_TOC_LINE_RE.search(line), line)

    def test_multi_line_contents_block_is_dropped_whole(self):
        # A PDF can emit its whole contents page as ONE block; the pattern is
        # multiline so any entry line inside it still marks the block as noise.
        from library.management.commands.import_ochorus import _TOC_LINE_RE

        block = "Table of Contents\nChapter One ......... 2\nChapter Two ......... 13"
        self.assertTrue(_TOC_LINE_RE.search(block))

    def test_chapterizer_keeps_prose_containing_dot_runs(self):
        # Bodies must clear the chapterizer's 120-word stub floor.
        filler = " ".join(["the eagle mounts up with wings as it waits upon God"] * 14)
        blocks = [
            ("Contents", 12.0),
            ("Chapter One ................ 2", 12.0),
            ("Chapter Two ............... 9", 12.0),
            ("Chapter Three ............. 17", 12.0),
            ("CHAPTER ONE", 18.0),
            ("Flying High", 18.0),
            (f"He gives power to the faint..... and to them that have no might. {filler}", 12.0),
            ("CHAPTER TWO", 18.0),
            ("Love Gifts", 18.0),
            (f"The ear cannot say to the eye 'I have no need of you'..... but God. {filler}", 12.0),
            ("CHAPTER THREE", 18.0),
            ("Vision", 18.0),
            (f"Where there is no vision the people perish. {filler}", 12.0),
        ]
        sections = self._chapterize(blocks)
        self.assertEqual(len(sections), 3)
        bodies = " ".join(body for _, body in sections)
        # The author's words survived …
        self.assertIn("He gives power to the faint", bodies)
        self.assertIn("The ear cannot say to the eye", bodies)
        # … and the contents lines did not.
        self.assertNotIn("................", bodies)
        self.assertNotIn("Chapter Two ...", bodies)


class FlatMarkerTitleTests(TestCase):
    """A "CHAPTER N" marker whose title is set at BODY size, not larger.

    Murray's *Divine Healing* is typographically flat: the marker and the title
    under it are both 12pt and only the running header is bigger, so the
    size/ALL-CAPS title borrow finds nothing. The chapter then keeps a bare
    "Chapter 1" AND the title line is merged into the epigraph that follows it
    ("Pardon and Healing “But that ye may know…").
    """

    def _chapterize(self, blocks):
        from library.management.commands.import_ochorus import chapterize

        return chapterize(blocks, 12.0)

    def _flat(self, text):
        from library.management.commands.import_ochorus import _flat_marker_title

        return _flat_marker_title(text)

    def test_a_body_size_title_is_borrowed_and_leaves_the_body(self):
        filler = "word " * 130
        blocks = [
            ("CHAPTER 1", 12.0),
            ("Pardon and Healing", 12.0),
            (f"“But that ye may know that the Son of man hath power. {filler}", 12.0),
            ("CHAPTER 2", 12.0),
            ("Because of Your Unbelief", 12.0),
            (f"“Then came the disciples to Jesus apart. {filler}", 12.0),
        ]
        from library.ingest import clean_title

        sections = self._chapterize(blocks)
        # chapterize keeps the marker; clean_title (which every importer applies)
        # drops it once a descriptive title is there to show instead.
        self.assertEqual(
            [t for t, _ in sections],
            ["Chapter 1. Pardon and Healing", "Chapter 2. Because of Your Unbelief"],
        )
        self.assertEqual(
            [clean_title(t) for t, _ in sections],
            ["Pardon and Healing", "Because of Your Unbelief"],
        )
        # The title is the title, not the first words of the prose.
        self.assertNotIn("Pardon and Healing", sections[0][1])
        self.assertIn("But that ye may know", sections[0][1])

    def test_titles_that_are_quoted_questions_or_long_are_still_taken(self):
        # Each of these was rejected by the first cut of the guards, shipping a
        # bare "Chapter N" with the title fused into the prose.
        self.assertTrue(self._flat("Your Body Is the Temple of the Holy Ghost"))  # 9 words
        self.assertTrue(self._flat("Is Sickness a Chastisement?"))               # ends "?"
        self.assertTrue(self._flat("“Ye Are the Branches”"))                     # quoted
        self.assertTrue(self._flat("Pardon and Healing"))

    def test_prose_epigraphs_and_bare_references_are_refused(self):
        # A full verse epigraph — too long, and carries a citation.
        self.assertFalse(self._flat(
            "“But that ye may know that the Son of man hath power on earth to "
            "forgive sins, Arise, take up thy bed” (Matt. 9:6)."
        ))
        # A SHORT quoted epigraph is caught by its citation, not its length —
        # this one repeats the chapter title almost word for word.
        self.assertFalse(self._flat("“Ye are the branches” (John 15:5)."))
        # Lines that are nothing but a scripture reference sit under the title.
        self.assertFalse(self._flat("Mark 5 :25—34"))
        self.assertFalse(self._flat("I Corinthians 12:4, 9, 11"))
        # Ordinary prose.
        self.assertFalse(self._flat("In man two natures are combined."))
        self.assertFalse(self._flat(""))


class CcelLeadingHeadingTests(TestCase):
    """CCEL chapters whose heading is set as consecutive one-line paragraphs.

    Most CCEL works mark it as a real <h2>; *Waiting on God* uses three <p>s
    ("First Day." / "WAITING ON GOD:" / the title), which render as stray
    fragments repeating the chapter title.
    """

    def _fold(self, html):
        from library.management.commands.import_ccel import fold_leading_heading

        return fold_leading_heading(html)

    def test_the_heading_run_becomes_one_h2(self):
        out = self._fold(
            "<p>First Day.</p> <p>WAITING ON GOD:</p> <p>The God of Our Salvation.</p>"
            " <p>'My soul waiteth only upon God.'</p> <p>IF salvation comes from God…</p>"
        )
        self.assertTrue(out.startswith("<h2>First Day. WAITING ON GOD: The God of Our Salvation.</h2>"))
        self.assertIn("<p>'My soul waiteth only upon God.'</p>", out)

    def test_it_is_idempotent(self):
        once = self._fold("<p>First Day.</p> <p>WAITING ON GOD:</p> <p>Prose follows here.</p>")
        self.assertEqual(self._fold(once), once)

    def test_an_epigraph_broken_into_verse_lines_is_not_swallowed(self):
        # CCEL sets poetry one line per <p>. Without the quote/dash stop these
        # become part of the heading, losing the opening line of Scripture.
        out = self._fold(
            "<p>Third Day.</p> <p>WAITING ON GOD:</p> <p>The True Place of the Creature.</p>"
            " <p>'These wait all upon Thee;</p> <p>That Thou mayest give them their meat.</p>"
        )
        self.assertIn("<p>'These wait all upon Thee;</p>", out)
        self.assertNotIn("These wait all upon Thee", out.split("</h2>")[0])

    def test_a_dashed_citation_line_stops_the_run(self):
        out = self._fold("<p>First Day.</p> <p>WAITING:</p> <p>—Ps. 62:5</p> <p>Prose here.</p>")
        self.assertEqual(out.split("</h2>")[0], "<h2>First Day. WAITING:")
        self.assertIn("<p>—Ps. 62:5</p>", out)

    def test_short_narrative_prose_is_left_alone(self):
        # Two genuinely short prose paragraphs: no ALL-CAPS or colon line, so
        # nothing here reads as a heading.
        html = "<p>He was gone.</p> <p>She did not know.</p> <p>Then a much longer paragraph.</p>"
        self.assertEqual(self._fold(html), html)

    def test_a_fold_that_would_consume_the_whole_body_is_refused(self):
        html = "<p>First Day.</p> <p>WAITING ON GOD:</p>"
        self.assertEqual(self._fold(html), html)


class EmptyBlockCleaningTests(TestCase):
    """<p><br/></p> spacers and CCEL page-break markers are page furniture."""

    def test_br_only_blocks_and_page_markers_go(self):
        from library.ingest import clean_fragment

        out = clean_fragment(
            '<p><span class="pb">17</span></p><p><br/></p><p>Real prose.</p><p><br /></p>'
        )
        self.assertEqual(out.replace(" ", ""), "<p>Realprose.</p>")

    def test_a_page_number_inside_a_sentence_does_not_join_words(self):
        from library.ingest import clean_fragment

        out = clean_fragment('<p>they that are in the flesh cannot please <span class="pb">34</span> God.</p>')
        self.assertIn("cannot please God.", out)


class UpsertBookAuthorBioTests(TestCase):
    """upsert_book must never overwrite an existing author's bio.

    `authors.json` is the source of truth for bios; `catalog.py`'s AuthorEntry
    carries only the short stub written when a book was first added. When
    upsert_book pushed that stub through `defaults=`, importing ANY book
    truncated the author's real bio — it hit five authors, each "fixed" by
    pasting the long bio back into the catalog.
    """

    def _entry(self):
        return next(b for b in BOOKS if b.author_slug in AUTHORS)

    def test_existing_author_bio_survives_an_import(self):
        entry = self._entry()
        stub = AUTHORS[entry.author_slug].bio
        Author.objects.create(
            slug=entry.author_slug, name="Placeholder",
            bio="A much longer, reviewed biography that must not be clobbered.",
            birth_year=1800, death_year=1880,
        )
        upsert_book(entry, [("Ch 1", "<p>Body text here, long enough.</p>")])
        a = Author.objects.get(slug=entry.author_slug)
        self.assertNotEqual(a.bio, stub)
        self.assertTrue(a.bio.startswith("A much longer, reviewed biography"))
        self.assertEqual(a.birth_year, 1800)  # years are create-only too
        # The name still updates — it's the display label, not reviewed content.
        self.assertEqual(a.name, AUTHORS[entry.author_slug].name)

    def test_new_author_still_gets_the_catalog_bio(self):
        entry = self._entry()
        Author.objects.filter(slug=entry.author_slug).delete()
        upsert_book(entry, [("Ch 1", "<p>Body text here, long enough.</p>")])
        a = Author.objects.get(slug=entry.author_slug)
        self.assertEqual(a.bio, AUTHORS[entry.author_slug].bio)

    def test_reimport_resolves_to_the_existing_author_not_a_fork(self):
        # `catalog.py` said `charles-spurgeon` for five books while the fixture
        # and prod had only `charles-h-spurgeon`, so re-importing any of them
        # created a SECOND Spurgeon holding just the catalog stub — no bio_html,
        # no photo — and re-pointed the book at it. Every catalog author slug
        # must name a row that already exists (tests_fixture pins that against
        # authors.json); this pins the behaviour it protects.
        entry = next(b for b in BOOKS if b.author_slug == "charles-h-spurgeon")
        real = Author.objects.create(
            slug="charles-h-spurgeon", name="Charles H. Spurgeon",
            bio="The full biography.", bio_html="<p>Long form.</p>",
            photo_url="/spurgeon.png",
        )

        upsert_book(entry, [("Ch 1", "<p>Body text here, long enough.</p>")])

        self.assertEqual(Author.objects.filter(slug__contains="spurgeon").count(), 1)
        book = Book.objects.get(slug=entry.slug, language="en")
        self.assertEqual(book.author_id, real.pk)
        real.refresh_from_db()
        self.assertEqual(real.photo_url, "/spurgeon.png")  # portrait not lost


class ReimportCreateOnlyTests(TestCase):
    """A re-import refreshes content but must NOT walk back workflow-owned state
    (review #26): a copyright pull (is_published=False), a review decision
    (source_type), and the assigned sort_order all survive a later re-import."""

    def _meta(self, **over):
        base = {
            "author": "Andrew Murray",
            "title": "Humility",
            "description": "d",
            "source_url": "http://example.test/humility",
            "cover_url": "",
            "pdf_url": "",
            "slug": "humility",
        }
        base.update(over)
        return base

    def test_reimport_keeps_pulled_publish_state_and_source_type(self):
        from library.management.commands.import_ochorus import upsert

        book = upsert(self._meta(), [("Ch1", "<p>a</p>")], sort_order=3)
        self.assertTrue(book.is_published)
        self.assertEqual(book.source_type, Book.SourceType.PUBLIC_DOMAIN)

        # Simulate what prod does after the first import: a copyright pull and a
        # review/sort decision the seed/import must not overwrite.
        book.is_published = False
        book.source_type = Book.SourceType.AI_REVIEWED
        book.sort_order = 99
        book.save(update_fields=["is_published", "source_type", "sort_order"])

        again = upsert(
            self._meta(title="Humility (revised)"), [("Ch1", "<p>b</p>")], sort_order=3
        )
        self.assertEqual(again.pk, book.pk)
        self.assertFalse(again.is_published)  # not republished
        self.assertEqual(again.source_type, Book.SourceType.AI_REVIEWED)  # not re-typed
        self.assertEqual(again.sort_order, 99)  # not reshuffled
        self.assertEqual(again.title, "Humility (revised)")  # content DID refresh
        self.assertEqual(again.chapters.count(), 1)


class CcelPartSelectorTests(TestCase):
    """`BookEntry.part` — one work out of a Schaff volume.

    The Schaff sets publish a whole volume under one work path (verified by
    probe: `chrysostom/priesthood`, `cyprian/treatises` and
    `athanasius/life_antony` all 404), so a work is addressed by its
    section-stem prefix in the volume TOC. These tests drive `toc_parts`
    against a stubbed TOC rather than the network.
    """

    VOLUME = """
      <a href="vol.i.html">Title Page</a>
      <a href="vol.iv.html">On the Priesthood</a>
      <a href="vol.iv.i.html">Introduction</a>
      <a href="vol.iv.ii.html">Book I</a>
      <a href="vol.iv.iii.html">Book II</a>
      <a href="vol.vii.html">Another Work</a>
      <a href="vol.vii.ii.html">Another Work</a>
      <a href="vol.vii.ii.i.html">Section 1</a>
      <a href="vol.vii.ii.ii.html">Section 2</a>
    """

    def _parts(self, part=""):
        from library.management.commands import import_ccel

        with mock.patch.object(import_ccel, "fetch", return_value=self.VOLUME):
            return import_ccel.toc_parts("schaff/vol", part)

    def test_no_part_still_groups_the_whole_volume_by_its_first_segment(self):
        titles = [t for t, _ in self._parts()]
        self.assertEqual(titles, ["Title Page", "On the Priesthood", "Another Work"])

    def test_a_part_narrows_to_that_work_and_groups_one_level_down(self):
        # The part's own divider page is a parent, so it is not itself a chapter.
        self.assertEqual(
            [t for t, _ in self._parts("iv")], ["Introduction", "Book I", "Book II"]
        )

    def test_a_two_segment_part_reaches_the_level_below_it(self):
        # "vii.ii" skips the volume-level sibling "vii" entirely.
        self.assertEqual([t for t, _ in self._parts("vii.ii")], ["Section 1", "Section 2"])

    def test_a_part_that_matches_nothing_is_an_error_not_an_empty_book(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._parts("zz")


class CcelSummaryTitleTests(TestCase):
    """NPNF/ANF section "titles" that are really a precis of the argument."""

    def _t(self, title):
        from library.management.commands.import_ccel import summary_title

        return summary_title(title)

    def test_the_lead_clause_before_a_dash_is_the_title(self):
        self.assertEqual(
            self._t("Introductory.--The subject of this treatise: the humiliation of the Word"),
            "Introductory",
        )

    def test_the_first_sentence_is_the_title_when_there_is_no_dash(self):
        self.assertEqual(
            self._t("The true doctrine. Creation out of nothing, of God's lavish bounty of being."),
            "The true doctrine",
        )

    def test_a_single_long_sentence_falls_back_to_a_clause_break(self):
        out = self._t(
            "For God has not only made us out of nothing; but He gave us freely, by the Grace "
            "of the Word, a life in correspondence with God"
        )
        self.assertEqual(out, "For God has not only made us out of nothing")

    def test_a_title_with_no_break_at_all_is_cut_at_a_word_boundary(self):
        out = self._t("Man " * 40)
        self.assertLessEqual(len(out), 72)
        self.assertFalse(out.endswith("Ma"))

    def test_a_real_short_title_is_untouched(self):
        self.assertEqual(self._t("Birth and beginnings of Antony"), "Birth and beginnings of Antony")
    def test_an_abbreviations_full_stop_does_not_end_the_lead_clause(self):
        # Without the guard this cut to "The life of St" — and Schaff's section
        # summaries are full of St./Cf./cap. abbreviations.
        self.assertEqual(
            self._t("The life of St. Antony. He was by descent an Egyptian."),
            "The life of St. Antony",
        )
        self.assertEqual(
            self._t("Cf. the earlier argument. This is the second reason."),
            "Cf. the earlier argument",
        )


class BareChapterTitleTests(TestCase):
    """A chapter whose "title" is only a counter is stored as untitled."""

    def _titles(self, sections):
        # A real catalog entry, because `upsert_book` reads `BOOKS` for
        # `sort_order` — but it must be one with NO `chapter_titles` correction,
        # since `upsert_book` applies those and they would replace the titles
        # under test. This was pinned to `purpose-in-prayer` until that book
        # gained editorial titles for its unnamed chapters, at which point all
        # three tests here failed with the corrections' titles rather than their
        # own. Picking the entry by that property instead of by name keeps the
        # next corrections entry from re-arming the same trap.
        from library.catalog import BOOKS
        from library.corrections import chapter_title_overrides
        from library.ingest import upsert_book

        entry = next(b for b in BOOKS if not chapter_title_overrides(b.slug))
        book = upsert_book(entry, sections)
        return [c.title for c in book.chapters.order_by("order")]

    def test_a_counter_only_title_is_stored_empty(self):
        titles = self._titles([("Chapter I", "<p>" + "word " * 200 + "</p>"),
                               ("Chapter II", "<p>" + "word " * 200 + "</p>")])
        self.assertEqual(titles, ["", ""])

    def test_a_real_title_is_untouched(self):
        titles = self._titles([("The Letter Killeth", "<p>" + "word " * 200 + "</p>")])
        self.assertEqual(titles, ["The Letter Killeth"])

    def test_section_and_part_counters_are_kept(self):
        # They name a unit the reader does NOT number, so unlike "Chapter N"
        # they still carry information — nine such titles ship today.
        titles = self._titles([("Section I", "<p>" + "word " * 200 + "</p>"),
                               ("Part III", "<p>" + "word " * 200 + "</p>")])
        self.assertEqual(titles, ["Section I", "Part III"])


class CcelVolumeFurnitureTests(TestCase):
    """Leading page furniture on a Schaff section page, and contents pages."""

    def _body(self, html, title="", book_title="", volume=False):
        from library.management.commands.import_ccel import extract_body

        return extract_body(html, title, book_title, volume)

    def test_running_head_rule_and_restated_title_are_dropped(self):
        # Book I of On the Priesthood opens exactly like this.
        out = self._body(
            "<div id='theText'><p>treatise on the priesthood.</p><p>————————————</p>"
            "<p>Book I.</p><p>1. I had many genuine and true friends.</p></div>",
            "Book I",
            "On the Priesthood",
            volume=True,
        )
        self.assertNotIn("treatise on the priesthood", out)
        self.assertNotIn("————", out)
        self.assertIn("I had many genuine and true friends", out)

    def test_the_running_head_matches_in_either_direction(self):
        # CCEL prints both a tail of the title and the whole of it.
        out = self._body(
            "<div id='theText'><p>Life of Antony.</p><p>The life and conversation of Antony.</p></div>",
            "Preface",
            "The Life of Antony",
            volume=True,
        )
        self.assertNotIn("<p>Life of Antony.</p>", out)
        self.assertIn("The life and conversation", out)

    def test_nothing_is_stripped_without_a_work_title(self):
        # The gate that keeps this off the books imported from per-work paths:
        # run unconditionally it deleted a real chapter of The Imitation of
        # Christ whose whole body restates its title.
        html = "<div id='theText'><p>Book I.</p><p>1. I had many friends.</p></div>"
        self.assertIn("Book I.", self._body(html, "Book I"))

    def test_a_real_opening_sentence_survives(self):
        out = self._body(
            "<div id='theText'><p>The events recorded in this celebrated treatise on the "
            "Priesthood must be read with care by every reader of it.</p></div>",
            "Introduction",
            "On the Priesthood",
            volume=True,
        )
        self.assertIn("The events recorded", out)

    def test_a_heading_that_restates_the_title_with_its_number_is_dropped(self):
        # Bounds's TOC entry is "1. Men of Prayer Needed" (which clean_title
        # reduces to the title alone), while the page's own <h2> numbers itself
        # differently: "1 Men of Prayer Needed". Same restatement, so it goes —
        # otherwise every chapter opens by repeating its own heading.
        out = self._body(
            "<div id='theText'><h2>1 Men of Prayer Needed</h2>"
            "<p>Study universal holiness of life.</p></div>",
            "Men of Prayer Needed",
        )
        self.assertNotIn("Men of Prayer Needed", out)
        self.assertIn("Study universal holiness", out)

    def test_a_heading_that_is_not_the_title_survives_its_leading_number(self):
        # The leading number must not make any heading disposable — only one
        # that restates the chapter's own title.
        out = self._body(
            "<div id='theText'><h2>1 The Voice of Christ</h2>"
            "<p>Hear, my son, my words.</p></div>",
            "Men of Prayer Needed",
        )
        self.assertIn("The Voice of Christ", out)

    def test_a_bare_counter_heading_is_dropped(self):
        # An untitled chapter heads its page with just the numeral. Purpose in
        # Prayer's pages open "<h2>I</h2>" above the first line, and with no
        # title to compare against, nothing else would remove it.
        out = self._body(
            "<div id='theText'><h2>I</h2><p>My Creed leads me to think…</p></div>", ""
        )
        self.assertNotIn("<h2>", out)
        self.assertIn("My Creed leads me", out)

    def test_a_heading_that_merely_starts_with_a_numeral_survives(self):
        out = self._body(
            "<div id='theText'><h2>I Believe</h2><p>Body text here.</p></div>", ""
        )
        self.assertIn("I Believe", out)

    def test_a_heading_carrying_the_books_own_title_is_dropped(self):
        # Prayer and Praying Men's Introduction opens with the work's name above
        # the section's, so the chapter began by shouting the book's title.
        out = self._body(
            "<div id='theText'><h1>PRAYER AND PRAYING MEN</h1>"
            "<h2>INTRODUCTION</h2><p>Rev. Edward McKendrie Bounds was…</p></div>",
            "Introduction",
            "Prayer and Praying Men",
        )
        self.assertNotIn("PRAYER AND PRAYING MEN", out)
        self.assertNotIn("INTRODUCTION", out)
        self.assertIn("Rev. Edward McKendrie Bounds", out)

    def test_a_roman_numbered_heading_restating_the_title_is_dropped(self):
        out = self._body(
            "<div id='theText'><h2>III. ABRAHAM, THE MAN OF PRAYER</h2>"
            "<p>Oh for determined men and women…</p></div>",
            "Abraham, the Man of Prayer",
        )
        self.assertNotIn("ABRAHAM", out)
        self.assertIn("Oh for determined men", out)

    def test_a_roman_looking_word_is_not_read_as_a_numeral(self):
        # "civil", "mild", "livid" are all spelled out of [ivxlcdm]; a loose
        # class would let this heading match the title it merely precedes.
        out = self._body(
            "<div id='theText'><h2>Civil War</h2><p>Prose follows.</p></div>", "War"
        )
        self.assertIn("Civil War", out)

    def test_a_non_latin_heading_is_never_matched_on_an_empty_form(self):
        # `_norm` keeps only ASCII [a-z0-9], so every Russian/Hindi/Arabic
        # heading and title reduces to "" — which once made any two of them
        # compare equal. CCEL is English so it never showed here, but the same
        # predicate decides what a data migration deletes from stored rows.
        out = self._body(
            "<div id='theText'><h2>\u0413\u0415\u0424\u0421\u0418\u041c\u0410\u041d\u0418\u042f</h2>"
            "<p>\u041f\u0440\u043e\u0437\u0430.</p></div>",
            "\u0427\u0430\u0448\u0430 \u0421\u0442\u0440\u0430\u0434\u0430\u043d\u0438\u0439",
        )
        self.assertIn("\u0413\u0415\u0424\u0421\u0418\u041c\u0410\u041d\u0418\u042f", out)

    def test_a_contents_page_is_recognised_by_its_body(self):
        from library.management.commands.import_ccel import is_contents_body

        # The Life of Antony's contents page is titled "Prologue", so only the
        # body gives it away.
        self.assertTrue(is_contents_body("<p>Life of Antony.</p><p>Table of Contents.</p>"))
        self.assertFalse(is_contents_body("<p>1. Antony was by descent an Egyptian.</p>"))


class RestatedHeadingMigrationTests(TestCase):
    """Migration 0092's rewrite — the stored half of the duplicate-heading rule."""

    def test_a_restatement_in_a_heading_element_goes(self):
        self.assertEqual(
            MIGRATION_0092.rewrite(
                "<h2>II. THE DIGNITY OF CHRIST</h2>  <p>Who being the brightness.</p>",
                "The Dignity of Christ",
            ),
            "<p>Who being the brightness.</p>",
        )

    def test_a_restatement_left_loose_before_the_first_tag_goes(self):
        # Twenty-two chapters carry it in this shape, which lands in body_text
        # and so in the search index too. It is residue from an older import:
        # CCEL prints that title in a navbar table outside #theText, so a fresh
        # import never sees it and the importer needs no change for it.
        self.assertEqual(
            MIGRATION_0092.rewrite(
                'IX. A WARNING AGAINST UNBELIEF   <h4>"Take heed, brethren."</h4>',
                "A Warning Against Unbelief",
            ),
            '<h4>"Take heed, brethren."</h4>',
        )

    def test_the_preface_goes_too(self):
        # Every chapter of this book restates its own title; leaving one row
        # duplicated to be tidy about numbering style is a worse book.
        self.assertEqual(
            MIGRATION_0092.rewrite(
                "<h2>PREFACE.</h2> <p>This Epistle bears no name.</p>", "Preface"
            ),
            "<p>This Epistle bears no name.</p>",
        )

    def test_a_heading_that_is_not_the_title_is_left_alone(self):
        self.assertIsNone(
            MIGRATION_0092.rewrite(
                "<h2>II. THE DIGNITY OF CHRIST</h2> <p>Prose.</p>", "Sinai and Sion"
            )
        )

    def test_a_non_latin_heading_is_left_alone(self):
        # `_norm` keeps ASCII only, so both sides once reduced to "" and matched.
        self.assertIsNone(
            MIGRATION_0092.rewrite(
                "<h2>\u0413\u0415\u0424\u0421\u0418\u041c\u0410\u041d\u0418\u042f</h2><p>\u041f\u0440\u043e\u0437\u0430.</p>",
                "\u0427\u0430\u0448\u0430 \u0421\u0442\u0440\u0430\u0434\u0430\u043d\u0438\u0439",
            )
        )

    def test_a_chapter_that_is_only_its_own_title_keeps_it(self):
        self.assertIsNone(
            MIGRATION_0092.rewrite("<h2>XXX. SINAI AND SION</h2>", "Sinai and Sion")
        )

    def test_the_rewrite_is_idempotent(self):
        once = MIGRATION_0092.rewrite(
            "<h2>XXX. SINAI AND SION</h2> <p>Ye are come unto Mount Sion.</p>",
            "Sinai and Sion",
        )
        self.assertIsNone(MIGRATION_0092.rewrite(once, "Sinai and Sion"))
