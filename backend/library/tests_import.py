"""Tests for the admin document-upload import (upload_import + the endpoints)."""

from __future__ import annotations

import io
import zipfile
from unittest import mock

import fitz  # PyMuPDF
from django.test import SimpleTestCase, TestCase, override_settings
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
            publication_year=1885,
            attribution="Public domain — CCEL scan",
        )
        self.assertEqual(book.subtitle, "A Subtitle")
        self.assertEqual(book.cover_color, "#3b5bdb")
        # Import never stores a cover_url — covers are repo-borne /covers/ assets,
        # so an imported book starts coverless (a generated plate stands in) until
        # a designed cover ships in a fixture. This is what lets the CSP forbid
        # off-site images (no blanket `img-src https:`).
        self.assertEqual(book.cover_url, "")
        self.assertEqual(book.publication_year, 1885)
        self.assertEqual(book.attribution, "Public domain — CCEL scan")

    def test_create_book_metadata_is_validated(self):
        # Bad hex and out-of-range year are dropped, not stored.
        book = ui.create_book(
            self.author,
            "Bad Meta",
            [{"title": "One", "html": f"<p>{BODY}</p>"}],
            "en",
            cover_color="red; drop table",
            publication_year=99999,
        )
        self.assertEqual(book.cover_color, "")
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


class RestatedHeadingStripTests(TestCase):
    """`strip_restated_heading` — the rule migration 0092 and the fixture share.

    `import_ccel.extract_body` drops these while the source page is still
    parsed markup; this is the same rule expressed over a body that is already
    STORED, which is not the same text. `clean_html` keeps h2-h4 and unwraps
    everything else, so a source heading that was an <h1> survives as bare text
    in front of the first <p>.
    """

    def _strip(self, html, title):
        from library.ingest import strip_restated_heading

        return strip_restated_heading(html, title)

    def test_a_leading_heading_that_repeats_the_title_goes(self):
        self.assertEqual(
            self._strip("<h2>TO YOU</h2> <p>HE WHO SPOKE and wrote…</p>", "To You"),
            "<p>HE WHO SPOKE and wrote…</p>",
        )

    def test_an_unwrapped_h1_left_as_loose_text_goes_too(self):
        self.assertEqual(
            self._strip("THE MONTH OF JANUARY <p>Jan. 1</p>", "The Month of January"),
            "<p>Jan. 1</p>",
        )

    def test_a_heading_that_says_more_than_the_title_stays(self):
        # Till He Come chapter 2 keeps its subtitle once the restatement above
        # it is gone; nothing else about the chapter may move.
        html = "<h3>A COMMUNION ADDRESS AT MENTONE.</h3> <p>IT is a theme…</p>"
        self.assertEqual(self._strip(html, "Mysterious Visits"), html)

    def test_a_numbering_difference_is_not_a_difference(self):
        self.assertEqual(
            self._strip("<h2>1 Men of Prayer Needed</h2> <p>Prose.</p>",
                        "Men of Prayer Needed"),
            "<p>Prose.</p>",
        )

    def test_a_numeral_that_is_part_of_the_NAME_is_not_numbering(self):
        # "1. John" and "2. John" both reduce to "john" once the numbering is
        # set aside, so without `_NUMBERED_BOOKS` a chapter headed for one
        # epistle restates a chapter titled for another. Same guard
        # `strip_numbering_prefix` carries, which cannot reach this: the
        # normaliser has already removed the "." it keys on.
        html = "<h2>1. John</h2> <p>Prose.</p>"
        self.assertEqual(self._strip(html, "2. John"), html)
        self.assertEqual(self._strip(html, "1. John"), "<p>Prose.</p>")
        # A real numbered title still loses its numeral, as it always did.
        self.assertEqual(
            self._strip("<h2>1 John the Baptist</h2> <p>Prose.</p>", "John the Baptist"),
            "<p>Prose.</p>",
        )

    def test_a_mid_chapter_heading_is_never_reached(self):
        html = "<p>Opening prose.</p> <h2>To You</h2> <p>More prose.</p>"
        self.assertEqual(self._strip(html, "To You"), html)

    def test_it_is_idempotent(self):
        once = self._strip("<h2>CLOSE</h2> <p>Prose.</p>", "Close")
        self.assertEqual(self._strip(once, "Close"), once)

    def test_a_strip_that_would_empty_the_chapter_is_refused(self):
        html = "<h2>Close</h2>"
        self.assertEqual(self._strip(html, "Close"), html)

    def test_a_non_latin_heading_is_compared_in_its_own_script(self):
        # The rule normalised to [a-z0-9] until 0092, which reduces any Arabic
        # or Devanagari string to "" — so every Arabic heading "restated" every
        # Arabic title. Both directions are asserted here.
        html = "<h2>आपके नाम</h2> <p>गद्य।</p>"
        self.assertEqual(self._strip(html, "आपके नाम"), "<p>गद्य।</p>")
        other = "<h2>وليمة العهد</h2> <p>نثر.</p>"
        self.assertEqual(self._strip(other, "الأولويّات"), other)

    def test_a_heading_of_pure_punctuation_restates_nothing(self):
        html = "<h2>———</h2> <p>Prose.</p>"
        self.assertEqual(self._strip(html, "———"), html)

    def test_a_translation_follows_its_english_twin(self):
        # `strip_leading_heading_element` drops the block whatever it says,
        # because the English chapter facing it decided. The Hindi heading here
        # paraphrases its own title, so the title rule alone leaves it.
        from library.ingest import strip_leading_heading_element

        html = '<h2>"परमेश्वर वह है जो उनको धर्मी ठहरानेवाला है"</h2> <p>रोमियों 8:33</p>'
        title = "परमेश्वर वह है जो धर्मी ठहराता है"
        self.assertEqual(self._strip(html, title), html)
        self.assertEqual(strip_leading_heading_element(html), "<p>रोमियों 8:33</p>")

    def test_following_the_english_never_eats_loose_text(self):
        from library.ingest import strip_leading_heading_element

        html = "Opening prose with no markup at all."
        self.assertEqual(strip_leading_heading_element(html), html)

    def test_a_footnote_inside_the_heading_does_not_save_it(self):
        # `extract_body` reads a candidate heading BEFORE clean_html removes the
        # footnote apparatus, so a marker inside the heading joined its text and
        # the restatement test stopped matching. Whitefield's farewell sermon
        # was the one duplicate heading in that book to survive the import.
        from library.management.commands.import_ccel import extract_body

        html = (
            '<div id="theText"><h1>The Good Shepherd: A Farewell Sermon'
            '<span class="NoteRef">5</span></h1>'
            '<p class="Footnote">The last sermon he preached in London.</p>'
            "<p>John 10:27 — My sheep hear my voice.</p></div>"
        )
        self.assertEqual(
            extract_body(html, "The Good Shepherd: A Farewell Sermon"),
            "<p>John 10:27 — My sheep hear my voice.</p>",
        )


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

        book, created = upsert(self._meta(), [("Ch1", "<p>a</p>")], sort_order=3)
        self.assertTrue(created)
        self.assertTrue(book.is_published)
        self.assertEqual(book.source_type, Book.SourceType.PUBLIC_DOMAIN)

        # Simulate what prod does after the first import: a copyright pull and a
        # review/sort decision the seed/import must not overwrite.
        book.is_published = False
        book.source_type = Book.SourceType.AI_REVIEWED
        book.sort_order = 99
        book.save(update_fields=["is_published", "source_type", "sort_order"])

        again, created = upsert(
            self._meta(title="Humility (revised)"), [("Ch1", "<p>b</p>")], sort_order=3
        )
        self.assertFalse(created)
        self.assertEqual(again.pk, book.pk)
        self.assertFalse(again.is_published)  # not republished
        self.assertEqual(again.source_type, Book.SourceType.AI_REVIEWED)  # not re-typed
        self.assertEqual(again.sort_order, 99)  # not reshuffled
        self.assertEqual(again.title, "Humility (revised)")  # content DID refresh
        self.assertEqual(again.chapters.count(), 1)

    def test_reimport_with_no_chapters_preserves_existing_book(self):
        """A chapterize regression (empty result) on an existing book must NOT
        wipe its chapters or touch its publish state — the pre-fix code deleted
        every chapter and left the book published-but-empty (review #26, bug #6).
        """
        from library.management.commands.import_ochorus import upsert

        book, _ = upsert(
            self._meta(), [("Ch1", "<p>a</p>"), ("Ch2", "<p>b</p>")], sort_order=3
        )
        self.assertEqual(book.chapters.count(), 2)
        self.assertTrue(book.is_published)

        again, created = upsert(self._meta(), [], sort_order=3)
        self.assertFalse(created)
        self.assertEqual(again.pk, book.pk)
        self.assertEqual(again.chapters.count(), 2)  # chapters NOT wiped
        self.assertTrue(again.is_published)  # still published, unchanged

    def test_first_import_with_no_chapters_saves_unpublished(self):
        """A brand-new book whose detection yields nothing is created unpublished
        (is_published=bool(chapters)) rather than shipping empty-but-live."""
        from library.management.commands.import_ochorus import upsert

        book, created = upsert(self._meta(slug="empty-one"), [], sort_order=4)
        self.assertTrue(created)
        self.assertFalse(book.is_published)
        self.assertEqual(book.chapters.count(), 0)


class SermonReimportCreateOnlyTests(TestCase):
    """A sermon re-import must not resurrect one that was unpublished in prod
    (a copyright pull). is_published is CREATE-ONLY, matching seed_sermons and
    the book importer (review #26, bug #2)."""

    def test_reimport_does_not_republish_a_pulled_sermon(self):
        from library.management.commands import import_sermons
        from library.sermon_catalog import SERMONS

        entry = SERMONS[0]  # a real ccel entry so SERMONS.index(entry) resolves
        body = "<p>" + " ".join(["word"] * 400) + "</p>"  # clears the 300-word floor
        cmd = import_sermons.Command()

        with mock.patch.object(import_sermons.time, "sleep"), \
             mock.patch.object(import_sermons, "fetch", return_value="<html></html>"), \
             mock.patch.object(import_sermons, "extract", return_value=(body, "Ps 1:1", None)):
            cmd._import_one(entry)
            sermon = Sermon.objects.get(slug=entry.slug, language="en")
            self.assertTrue(sermon.is_published)

            # Prod pulls it for a copyright complaint, directly in the DB.
            sermon.is_published = False
            sermon.save(update_fields=["is_published"])

            cmd._import_one(entry)  # a routine re-import

        sermon.refresh_from_db()
        self.assertFalse(sermon.is_published)  # NOT resurrected


class GutenbergDisplayLineTests(SimpleTestCase):
    """`extract_gutenberg_section` keeps PG 23438's centred display lines.

    See `import_sermons._display_line`. The markup below is the edition's own,
    cut down.
    """

    # Display lines the edition set in "Blessed Adversity", as the importer
    # must emit them — and as `BODY_CORRECTIONS` restores them.
    ADVERSITY_LINES = (
        "<h3>INTRODUCTORY.</h3>",
        "<h3>GOD'S TESTIMONY AND CHALLENGE.</h3>",
        '<p><em>"The LORD gave, and the LORD hath taken away; blessed be the '
        'Name of the LORD</em>."--Job i.21.</p>',
        "<h3>THE UNSEEN HEDGE.</h3>",
    )

    PAGE = """<html><body>
<div class="c1">
<h3> <a id="badverse">Blessed Adversity.</a></h3>
</div>
<div class="c1"><small><strong>INTRODUCTORY.</strong></small></div>
<p>The history of Job is full of instruction.</p>
<div class="pg_body_wrapper"><br></div>
<div class="c1"><small>GOD'S TESTIMONY AND CHALLENGE.</small></div>
<div class="c1"><em>"The L<small>ORD</small> gave, and the L<small>ORD</small> hath taken away; blessed be the Name of the L<small>ORD</small></em>."--Job i.21.</div>
<p>In the 8th verse of the 1st chapter.</p>
<div class="c1"><small>THE UNSEEN HEDGE</small>.</div>
<p>The reply of Satan is noteworthy.</p>
<div class="c1"><small>"RIBBAND OF BLUE."</small></div>
<p>GOD would have all His people wear a badge.</p>
<div class="pg_body_wrapper"><a class="pagenum" title="88" id="page_88"></a></div>
<div class="c1">
<h3> <a id="shepherd">Under the Shepherd's Care.</a></h3>
</div>
<div class="c1"><strong><small>A NEW YEAR'S ADDRESS.</small></strong></div>
<div class="pg_body_wrapper"><br></div>
<div class="c1"><em>"For ye were as sheep going astray; but are now returned unto the Shepherd and Bishop of your souls."</em>--1 Peter ii. 25.</div>
<p>"Ye were as sheep going astray." This is evidently addressed to believers.</p>
<div class="c1">
<h3> <a id="denial">Self-Denial versus Self-Assertion.</a></h3>
</div>
</body></html>"""

    def _extract(self, section):
        from library.management.commands.import_sermons import extract_gutenberg_section

        return extract_gutenberg_section(self.PAGE, section)

    def test_display_lines_are_kept_in_reading_order(self):
        intro, testimony, job, hedge = self.ADVERSITY_LINES
        self.assertEqual(
            self._extract("Blessed Adversity"),
            f"{intro}<p>The history of Job is full of instruction.</p>"
            f"{testimony}{job}<p>In the 8th verse of the 1st chapter.</p>"
            # The stop sits outside the small caps in the source; kept.
            f"{hedge}<p>The reply of Satan is noteworthy.</p>"
            # Capitals, but opening with a quotation mark: it ends a sentence.
            '<p>"RIBBAND OF BLUE."</p>'
            "<p>GOD would have all His people wear a badge.</p>",
        )

    def test_a_source_heading_still_ends_the_epigraph_search(self):
        """PG 57109 opens on an <h1>, then an <h2> byline, then John 4:10 as a
        plain `<p>` — which every stored edition of `unfailing-springs` keeps.
        Only a display-line subtitle may be skipped to reach the epigraph."""
        from library.management.commands.import_sermons import extract_gutenberg_section

        page = """<html><body>
<h1>Unfailing Springs</h1>
<h2>J. Hudson Taylor</h2>
<p><i>"JESUS answered and said unto her, If thou knewest the gift of GOD.</i></p>
<h2>Unfailing Springs</h2>
<p>THE best evidence of Christianity is a Christ-like life.</p>
</body></html>"""
        self.assertTrue(extract_gutenberg_section(page, "Unfailing Springs").startswith(
            '<h2>J. Hudson Taylor</h2><p><i>"JESUS answered'
        ))

    def test_a_subtitle_does_not_hide_the_epigraph(self):
        body = self._extract("Under the Shepherd's Care.")
        self.assertTrue(body.startswith(
            "<h3>A NEW YEAR'S ADDRESS.</h3>"
            '<blockquote><em>"For ye were as sheep going astray;'
        ))
        # The study's own <h3> and the next study's wrapper div are not content.
        self.assertNotIn("Self-Denial", body)
        self.assertEqual(body.count("<blockquote>"), 1)

    def test_furniture_divs_are_dropped_not_kept_as_lines(self):
        """A display line loses the div's class, so the sanitizer's drop-by-class
        policy has to be asked about the div first — or a page number or a
        stranded footnote ships as a paragraph."""
        from library.management.commands.import_sermons import extract_gutenberg_section

        page = (
            "<html><body><h3>Sermon</h3><p>Body.</p>"
            '<div class="footnote">[1] A note text.</div>'
            '<div class="pagenum">[12]</div>'
            "<h3>Next</h3></body></html>"
        )
        self.assertEqual(extract_gutenberg_section(page, "Sermon"), "<p>Body.</p>")

    def test_a_line_break_separates_heading_words(self):
        from library.management.commands.import_sermons import extract_gutenberg_section

        page = (
            "<html><body><h3>Sermon</h3><p>Body.</p>"
            "<div>THE NEGATIVE<br>CONDITIONS</div>"
            "<h3>Next</h3></body></html>"
        )
        self.assertIn("<h3>THE NEGATIVE CONDITIONS</h3>", extract_gutenberg_section(page, "Sermon"))


class GutenbergRestoredBlocksMatchImporterTests(SimpleTestCase):
    """Every English `restored_blocks` line for #23438 is what the importer emits.

    The guard in `restore_dropped_blocks` is a string match on the block, so a
    re-import must produce the correction's block byte for byte — or the body
    carries both. EDITION is every display line of the six studies, verbatim
    from PG 23438, with the prose paragraphs between them stubbed out.
    """

    EDITION = """<html><body>
<div class="c1">
<h3> <a id="BProsp">Blessed Prosperity</a></h3>
</div>
<div class="c1">Meditations On The First Psalm.</div>
<div class="c1"><strong><small>INTRODUCTORY.</small></strong></div>
<p>Paragraph 1.</p>
<div class="c1"><small>THE NEGATIVE CONDITIONS OF BLESSING</small></div>
<div class="c1"><em>"Blessed is the man that walketh not in the counsel of the ungodly."</em></div>
<p>Paragraph 2.</p>
<div class="c1"><em>Standeth not in the way of sinners.</em></div>
<p>Paragraph 3.</p>
<div class="c1"><em>"Nor sitteth in the seat of the scornful."</em></div>
<p>Paragraph 4.</p>
<div class="c1"><small>THE POSITIVE CONDITIONS OF BLESSING.</small></div>
<p>Paragraph 5.</p>
<div class="c1"><small>THE OUTCOME IN BLESSING.</small></div>
<p>Paragraph 6.</p>
<div class="c1"><small>THE CONTRAST.</small></div>
<div class="c1"><em>"The ungodly are not so."</em></div>
<p>Paragraph 7.</p>
<div class="c1">
<h3> <a id="badverse">Blessed Adversity.</a></h3>
</div>
<div class="c1"><small><strong>INTRODUCTORY.</strong></small></div>
<p>Paragraph 1.</p>
<div class="c1"><small>GOD'S TESTIMONY AND CHALLENGE.</small></div>
<div class="c1"><em>"The L<small>ORD</small> gave, and the L<small>ORD</small> hath taken away; blessed be the Name of the L<small>ORD</small></em>."--Job i.21.</div>
<p>Paragraph 2.</p>
<div class="c1"><small>THE UNSEEN HEDGE</small>.</div>
<p>Paragraph 3.</p>
<div class="c1"><small>THE TESTING OF JOB</small></div>
<p>Paragraph 4.</p>
<div class="c1"><small>SATAN'S MALIGNITY.</small></div>
<p>Paragraph 5.</p>
<div class="c1"><small>GRACE SUFFICIENT.</small></div>
<p>Paragraph 6.</p>
<div class="c1"><small>DEEPER TRIALS.</small></div>
<p>Paragraph 7.</p>
<div class="c1"><small>THE LOVING-KINDNESS OF THE LORD.</small></div>
<p>Paragraph 8.</p>
<div class="c1">
<h3> <a id="Coming">Coming to the King.</a></h3>
</div>
<div class="c1"><em>"And King Solomon gave unto the Queen of Sheba all her desire, whatsoever she asked, beside that which Solomon gave her of his royal bounty."</em>--1 Kings x. 13.</div>
<p>Paragraph 1.</p>
<div class="c1">
<h3> <a id="Full">A Full Reward.</a></h3>
</div>
<div class="c1"><em>"It hath fully been shewed me, all that thou hast done ... and how thou hast left they father and thy mother, and the land of thy nativity, and art come unto a people which thou knewest not heretofore. The L<small>ORD</small> recompense thy work, and a full reward be given thee of the L<small>ORD</small> G<small>OD</small> of Israel, under whose wings thou art come to trust" (Ruth ii. 11, 12).</em></div>
<p>Paragraph 1.</p>
<div class="c1">
<h3> <a id="shepherd">Under the Shepherd's Care.</a></h3>
</div>
<div class="c1"><strong><small>A NEW YEAR'S ADDRESS.</small></strong></div>
<div class="c1"><em>"For ye were as sheep going astray; but are now returned unto the Shepherd and Bishop of your souls."</em>--1 Peter ii. 25.</div>
<p>Paragraph 1.</p>
<div class="c1">
<h3> <a id="denial">Self-Denial versus Self-Assertion.</a></h3>
</div>
<div class="c1"><em>"If any man will come after Me, let him deny himself, and take up his cross daily, and follow Me.</em>--L<small>UKE</small> ix. 23.</div>
<p>Paragraph 1.</p>
<div class="c1">
<h3> <a id="Sufficiency">All Sufficiency</a></h3>
</div>
<div class="c1"><em>"The L<small>ORD</small> G<small>OD</small> is a Sun and Shield:<br>
the L<small>ORD</small> will give grace and glory:<br>
"No good thing will He withhold from them<br>
that walk uprightly."<br></em>--P<small>SALM LXXXIV</small>. 11.</div>
<p>Paragraph 1.</p>
</body></html>"""

    SLUGS = (
        "blessed-prosperity",
        "blessed-adversity",
        "a-full-reward",
        "self-denial-versus-self-assertion",
        "all-sufficiency",
        "under-the-shepherds-care",
    )

    def test_every_restored_english_block_is_emitted(self):
        import json

        from library.content_fixtures import SERMONS_DIR
        from library.corrections import BODY_CORRECTIONS
        from library.management.commands.import_sermons import extract_gutenberg_section
        from library.sermon_catalog import SERMONS

        sections = {e.slug: e.section for e in SERMONS}
        for slug in self.SLUGS:
            english = json.loads((SERMONS_DIR / f"{slug}.en.json").read_text())[0]["fields"]["body_html"]
            blocks = [
                block for _, block in BODY_CORRECTIONS[slug]["restored_blocks"] if block in english
            ]
            self.assertTrue(blocks)
            extracted = extract_gutenberg_section(self.EDITION, sections[slug])
            for block in blocks:
                with self.subTest(slug=slug, block=block):
                    self.assertIn(block, extracted)


class CcelAbortOnFetchFailureTests(TestCase):
    """A transient section-fetch failure mid-crawl must abort the whole book, not
    ship a partial one — a dropped section renumbers every later chapter, breaking
    plan days, saved positions and prerendered URLs (bug #3)."""

    def test_fetch_failure_leaves_the_existing_book_untouched(self):
        import requests

        from library.catalog import BookEntry
        from library.management.commands import import_ccel
        from library.models import Chapter

        author = Author.objects.create(slug="a-author", name="A Author")
        book = Book.objects.create(
            slug="testbook", language="en", author=author, title="T", is_published=True
        )
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>one</p>")
        Chapter.objects.create(book=book, order=2, title="Two", body_html="<p>two</p>")

        entry = BookEntry(
            slug="testbook", title="T", author_slug="a-author", source="ccel", source_ref="x/y"
        )
        cmd = import_ccel.Command()

        with (
            mock.patch.object(
                import_ccel,
                "toc_parts",
                return_value=[("Ch1", [("u1", "Ch1")]), ("Ch2", [("u2", "Ch2")])],
            ),
            mock.patch.object(import_ccel.time, "sleep"),
            mock.patch.object(import_ccel, "fetch", side_effect=requests.RequestException("boom")),
        ):
            cmd._import_one(entry)

        book.refresh_from_db()
        self.assertTrue(book.is_published)  # not unpublished
        self.assertEqual(book.chapters.count(), 2)  # chapters NOT wiped or renumbered


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

    def test_clean_title_strips_an_anf_chapter_argument_prefix(self):
        # ANF heads each chapter "Chapter I.—<argument>", abutting the em-dash
        # with no space; the reader prints the number itself, so the prefix must
        # go or it renders "1. Chapter I.—…". A real "Chapter Summary" (no
        # counter) is left alone.
        from library.ingest import clean_title

        self.assertEqual(clean_title("Chapter I.—The salutation"), "The salutation")
        self.assertEqual(clean_title("Chapter XLIII.—Moses of old"), "Moses of old")
        self.assertEqual(clean_title("Chapter Summary"), "Chapter Summary")

    def test_an_anf_argument_heading_is_dropped_against_its_full_title(self):
        # The body repeats its "Chapter I.—<argument>" heading. The importer
        # passes the FULL argument title (before summary_titles shortens the
        # STORED title), and _compared sets aside the heading's "chapter i" the
        # way clean_title strips it from the title — so the two match and the
        # heading goes. Without either half the argument leaks before the prose.
        out = self._body(
            "<div id='theText'><h2>Chapter I.—The salutation. Praise of the Corinthians.</h2>"
            "<p>The Church of God which sojourns at Rome.</p></div>",
            "The salutation. Praise of the Corinthians.",
        )
        self.assertNotIn("Chapter I", out)
        self.assertNotIn("salutation", out)
        self.assertIn("The Church of God which sojourns at Rome", out)

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

    def test_a_contents_page_is_recognised_by_its_body(self):
        from library.management.commands.import_ccel import is_contents_body

        # The Life of Antony's contents page is titled "Prologue", so only the
        # body gives it away.
        self.assertTrue(is_contents_body("<p>Life of Antony.</p><p>Table of Contents.</p>"))
        self.assertFalse(is_contents_body("<p>1. Antony was by descent an Egyptian.</p>"))
