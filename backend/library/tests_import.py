"""Tests for the admin document-upload import (upload_import + the endpoints)."""

from __future__ import annotations

import io
import zipfile

import fitz  # PyMuPDF
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from library import upload_import as ui
from library.catalog import AUTHORS, BOOKS
from library.ingest import upsert_book
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
