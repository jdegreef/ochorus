"""Downloadable editions (library/book_export.py): the EPUB endpoint and the
parts both formats share.

What these guard is shape — that a download is a readable EPUB, carries the
rights line and (for a machine translation) the review notice, and is only
served for an edition we have vetted. Whether it LOOKS right on a Kindle is a
human check on a device.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings
from lxml import etree

from . import book_export, export_policy
from .models import Author, Book, Chapter

PILOT = frozenset({("pilot-book", "en")})


@override_settings(PUBLIC_SITE_URL="https://ochorus.test")
@mock.patch.object(export_policy, "EXPORT_EDITIONS", PILOT)
@mock.patch.object(book_export, "load_cover", lambda url: None)
class EpubTests(TestCase):
    def setUp(self):
        author = Author.objects.create(
            slug="a-writer", name="A. Writer", birth_year=1847, death_year=1929,
            bio="A. Writer was a pastor.\n\nHe wrote books.",
        )
        self.book = Book.objects.create(
            author=author, slug="pilot-book", language="en", title="Pilot & Book",
            publication_year=1890, about_html="<p>Why it matters.</p>",
        )
        Chapter.objects.create(
            book=self.book, order=1, title="First",
            body_html="<p>One&nbsp;line<br>and <i>another</i>.</p><blockquote><p>Q</p></blockquote>",
        )
        Chapter.objects.create(book=self.book, order=2, title="", body_html="<p>Two.</p>")

    def _get(self, slug="pilot-book", **headers):
        return self.client.get(f"/api/library/books/{slug}/download.epub", **headers)

    def _zip(self, response) -> zipfile.ZipFile:
        return zipfile.ZipFile(io.BytesIO(response.content))

    def test_serves_a_well_formed_epub(self):
        res = self._get()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/epub+zip")
        self.assertIn('filename="pilot-book.epub"', res["Content-Disposition"])
        z = self._zip(res)
        first = z.infolist()[0]
        # The spec: mimetype first, stored, exact bytes.
        self.assertEqual(first.filename, "mimetype")
        self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
        self.assertEqual(z.read("mimetype"), b"application/epub+zip")
        for name in z.namelist():
            if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
                etree.fromstring(z.read(name))  # raises if not well-formed

    def test_chapters_contents_and_back_matter(self):
        z = self._zip(self._get())
        names = z.namelist()
        self.assertIn("OEBPS/chapter-001.xhtml", names)
        self.assertIn("OEBPS/about.xhtml", names)
        ch1 = z.read("OEBPS/chapter-001.xhtml").decode()
        self.assertIn("<br/>", ch1)
        self.assertIn("<i>another</i>", ch1)
        # A blank chapter title gets a numbered one, in the nav too.
        self.assertIn("Chapter 2", z.read("OEBPS/nav.xhtml").decode())
        colophon = z.read("OEBPS/colophon.xhtml").decode()
        self.assertIn("public domain", colophon)
        self.assertIn("https://ochorus.test/books/pilot-book/", colophon)
        self.assertNotIn("AI translation", colophon)
        self.assertIn("Pilot &amp; Book", z.read("OEBPS/content.opf").decode())
        ochorus = z.read("OEBPS/about-ochorus.xhtml").decode()
        self.assertIn("About Ochorus", ochorus)
        self.assertIn('href="https://ochorus.test/"', ochorus)

    def test_an_unreviewed_translation_says_so(self):
        self.book.source_type = Book.SourceType.AI_UNREVIEWED
        self.book.save()
        z = self._zip(self._get())
        colophon = z.read("OEBPS/colophon.xhtml").decode()
        self.assertIn("awaiting review", colophon)
        # Its words are new: only the original is public domain.
        self.assertIn("original text of this book is in the public domain", colophon)
        self.assertNotIn("The text of this book is in the public domain", colophon)
        self.assertIn("This translation was prepared", z.read("OEBPS/content.opf").decode())

    def test_an_in_copyright_book_never_claims_public_domain(self):
        # A living author's book shared with permission carries its © line as
        # the rights statement — never the public-domain one (Gareth Evans).
        self.book.attribution = "© A. Writer. Shared free on Ochorus with the author's permission."
        self.book.save()
        z = self._zip(self._get())
        colophon = z.read("OEBPS/colophon.xhtml").decode()
        opf = z.read("OEBPS/content.opf").decode()
        self.assertNotIn("public domain", colophon)
        self.assertNotIn("public domain", opf)
        self.assertIn("© A. Writer.", colophon)
        self.assertIn("This edition was prepared by Ochorus", colophon)
        self.assertIn("<dc:rights>© A. Writer.", opf)
        # And its translation: new words, still not public domain.
        self.book.source_type = Book.SourceType.AI_UNREVIEWED
        self.book.save()
        colophon = self._zip(self._get()).read("OEBPS/colophon.xhtml").decode()
        self.assertNotIn("public domain", colophon)
        self.assertIn("This translation was prepared by Ochorus", colophon)

    def test_same_content_same_bytes_and_a_304(self):
        first = self._get()
        self.assertEqual(first.content, self._get().content)
        again = self._get(HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")

    def test_a_new_release_changes_the_tag(self):
        tag = self._get()["ETag"]
        with override_settings(RELEASE_COMMIT="abc123"):
            again = self._get(HTTP_IF_NONE_MATCH=tag)
        self.assertEqual(again.status_code, 200)
        self.assertNotEqual(again["ETag"], tag)

    def test_not_in_the_pilot_is_404(self):
        Book.objects.create(author=self.book.author, slug="other", language="en", title="O")
        self.assertEqual(self._get("other").status_code, 404)

    def test_unpublished_is_404(self):
        self.book.is_published = False
        self.book.save()
        self.assertEqual(self._get().status_code, 404)

    def test_other_language_is_404(self):
        res = self.client.get("/api/library/books/pilot-book/download.epub?language=es")
        self.assertEqual(res.status_code, 404)

    def test_detail_payload_flags_it(self):
        from .serializers import BookDetailSerializer

        self.assertEqual(
            BookDetailSerializer(self.book).data["epub_url"],
            "/api/library/books/pilot-book/download.epub?language=en",
        )
        other = Book.objects.create(author=self.book.author, slug="other", language="en", title="O")
        self.assertEqual(BookDetailSerializer(other).data["epub_url"], "")

    def test_print_html_carries_every_chapter(self):
        html = book_export.render_print_html(book_export.build_edition(self.book))
        self.assertIn('id="ch1"', html)
        self.assertIn('id="ch2"', html)
        self.assertIn("Why it matters.", html)
        # "About Ochorus" sits between the title page and the contents.
        self.assertLess(html.index('class="ochorus"'), html.index('class="contents"'))

    def test_a_short_biography_follows_about_ochorus(self):
        z = self._zip(self._get())
        bio = z.read("OEBPS/about-author.xhtml").decode()
        self.assertIn("About the Author", bio)
        self.assertIn("1847–1929", bio)
        self.assertIn("<p>A. Writer was a pastor.</p><p>He wrote books.</p>", bio)
        self.assertIn('href="https://ochorus.test/authors/a-writer/"', bio)
        opf = z.read("OEBPS/content.opf").decode()
        # Reading order: About Ochorus, then the author, then the work itself.
        self.assertLess(opf.index('idref="ochorus"'), opf.index('idref="author"'))
        self.assertLess(opf.index('idref="author"'), opf.index('idref="about"'))
        html = book_export.render_print_html(book_export.build_edition(self.book))
        self.assertLess(html.index('class="ochorus"'), html.index('class="author-page"'))
        self.assertLess(html.index('class="author-page"'), html.index('class="contents"'))

    def test_a_translation_reads_the_translated_bio_and_never_falls_back(self):
        from .models import AuthorTranslation

        es = Book.objects.create(author=self.book.author, slug="pilot-book", language="es", title="Libro")
        self.assertEqual(book_export.author_bio(es), "")  # no English fallback
        AuthorTranslation.objects.create(author=self.book.author, language="es", bio="Fue pastor.")
        self.assertEqual(book_export.author_bio(es), "Fue pastor.")

    def test_a_written_export_bio_wins_over_the_short_one(self):
        text = "He was born.\n\nHe preached.\n\nHe died."
        with tempfile.TemporaryDirectory() as d, mock.patch.object(book_export, "EXPORT_BIOS_DIR", Path(d)):
            (Path(d) / "a-writer.en.txt").write_text(text + "\n", encoding="utf-8")
            self.assertEqual(book_export.author_bio(self.book), text)
            # Per language: an English file never speaks for Spanish.
            es = Book.objects.create(author=self.book.author, slug="pilot-book", language="es", title="Libro")
            self.assertEqual(book_export.author_bio(es), "")

    def test_an_imprint_has_no_biography_page(self):
        self.book.author.is_imprint = True
        self.book.author.save()
        self.assertNotIn("OEBPS/about-author.xhtml", self._zip(self._get()).namelist())

    def test_an_author_page_that_spills_onto_a_second_page_fails_the_pdf(self):
        from .management.commands import export_book

        ed = book_export.build_edition(self.book)
        html = book_export.render_print_html(ed)
        self.assertLess(html.index('id="author-top"'), html.index('id="author-end"'))
        export_book._check_author_page(ed, "x.pdf", {"author-top": 4, "author-end": 4, "ch1": 6})
        export_book._check_author_page(ed, "x.pdf", {"ch1": 5})  # no bio page
        with self.assertRaises(export_book.AuthorPageOverflow):
            export_book._check_author_page(ed, "x.pdf", {"author-top": 4, "author-end": 5})

    def test_print_contents_carries_page_numbers_when_given(self):
        ed = book_export.build_edition(self.book)
        numbered = book_export.render_print_html(ed, pages={"about": 4, "ch1": 5, "ch2": 9})
        self.assertIn('<span class="pg">9</span>', numbered)
        # The first pass reserves the column empty, so the layout can't move.
        self.assertIn('<span class="pg"></span>', book_export.render_print_html(ed))


class PrintFontTests(TestCase):
    def test_the_print_page_embeds_static_fonts_that_exist(self):
        # A variable web font makes Chrome draw every glyph as a Type 3
        # picture — twice the PDF. The page must use the bundled static files.
        import re

        css = book_export._print_fonts_css()
        files = re.findall(r"url\(fonts/([^)]+)\)", css)
        self.assertTrue(files)
        for name in files:
            self.assertTrue((book_export.PRINT_FONTS / name).is_file(), f"{name} is missing")


class PilotTests(TestCase):
    def test_every_pilot_language_has_back_matter(self):
        keys = set(book_export.STRINGS["en"])
        for _slug, lang in export_policy.EXPORT_EDITIONS:
            self.assertIn(lang, book_export.STRINGS)
            self.assertEqual(set(book_export.STRINGS[lang]), keys, f"{lang} back matter is incomplete")

    def test_every_stored_pdf_edition_links_its_bucket_file(self):
        # book-pdfs.yml uploads each to PDF_STORAGE_URL under export_filename;
        # ?download= makes Supabase send it as an attachment, since a
        # cross-origin <a download> is ignored.
        for slug, lang in sorted(export_policy.STORED_PDF_EDITIONS):
            name = book_export.export_filename(mock.Mock(slug=slug, language=lang), "pdf")
            self.assertEqual(
                _fixture_fields(slug, lang).get("pdf_url"),
                f"{export_policy.PDF_STORAGE_URL}{name}?download={name}",
                f"{slug} ({lang})",
            )

    def test_english_classics_are_public_domain_texts(self):
        # Their back matter says "in the public domain", so each must be a
        # published, public-domain English row that Ochorus didn't write.
        from .content_fixtures import authors_by_slug, book_editions
        from .corrections import COPYRIGHT_BLOCKED_SLUGS
        from .serializers import _edition_base_slug

        editions = {(slug, lang): fields for _path, slug, lang, fields in book_editions()}
        imprints = {slug for slug, a in authors_by_slug().items() if a.get("is_imprint")}
        for slug in sorted(export_policy.ENGLISH_CLASSICS):
            fields = editions.get((slug, "en"))
            self.assertIsNotNone(fields, f"{slug} has no English fixture")
            self.assertTrue(fields["is_published"], f"{slug} is not published")
            self.assertEqual(fields["source_type"], Book.SourceType.PUBLIC_DOMAIN, slug)
            self.assertFalse(
                book_export.is_in_copyright(mock.Mock(attribution=fields.get("attribution", ""))),
                f"{slug} is in copyright",
            )
            self.assertNotIn(slug, COPYRIGHT_BLOCKED_SLUGS)
            self.assertNotIn(fields["author"][0], imprints, f"{slug} is by an Ochorus imprint")
            self.assertNotIn(fields.get("series"), (["key-teachings"], ["portraits-of-courage"]), slug)
            # A retelling is a suffixed slug whose full work exists; a real
            # title like divine-songs-for-children has no such sibling.
            base = _edition_base_slug(slug)
            self.assertFalse(base != slug and (base, "en") in editions, f"{slug} is an Ochorus retelling")

    def test_held_works_stay_out(self):
        self.assertFalse(export_policy.HELD_ESV & export_policy.ENGLISH_CLASSICS)

    def test_every_exportable_edition_has_a_one_page_export_bio(self):
        # The About the Author page: three or four paragraphs on one A5 page.
        # The ceiling is loose — export_book fails a PDF whose bio runs past its
        # page — but it stops a bio_html pasted in by mistake.
        # An imprint (Ochorus Originals) is a publisher, not a person: its
        # editions have no About the Author page (author_bio), so no bio file.
        from .content_fixtures import authors_by_slug

        imprints = {slug for slug, a in authors_by_slug().items() if a.get("is_imprint")}
        authors = {
            (_fixture_fields(slug, lang)["author"][0], lang)
            for slug, lang in export_policy.EXPORT_EDITIONS
        }
        wanted = {f"{author}.{lang}.txt" for author, lang in authors if author not in imprints}
        for name in sorted(wanted):
            path = book_export.EXPORT_BIOS_DIR / name
            self.assertTrue(path.is_file(), f"no export bio at {path.name}")
            text = path.read_text(encoding="utf-8").strip()
            self.assertIn(book_export._bio_paragraphs(text).count("<p>"), (3, 4), f"{name}: three or four paragraphs")
            self.assertLessEqual(len(text), 1900, f"{name} is too long for one page")
        # And no file for an author or language with nothing to download: a typo
        # in a name would otherwise sit there unread while the short bio prints.
        stray = {p.name for p in book_export.EXPORT_BIOS_DIR.glob("*.txt")} - wanted
        self.assertFalse(stray, f"export bios no edition uses: {sorted(stray)}")

    def test_export_bios_were_checked_against_the_current_long_bio(self):
        # Each export bio is a short retelling of the author's long bio in its
        # own language (authors.json bio_html; author_bios_<lang>/<slug>.html).
        # When that moves (a corrected date, a new fact) the short copy may be
        # wrong: re-read it against the new long bio, then update its digest
        # in export_bios/sources.json — the designed_covers.py pattern.
        import hashlib
        import json

        from .content_fixtures import AUTHORS_FILE

        english = {
            r["fields"]["slug"]: r["fields"].get("bio_html", "")
            for r in json.loads(AUTHORS_FILE.read_text(encoding="utf-8"))
        }
        translated = book_export.Path(book_export.settings.BASE_DIR) / "library" / "migrations" / "data"
        pinned = json.loads((book_export.EXPORT_BIOS_DIR / "sources.json").read_text(encoding="utf-8"))
        files = sorted(p.name for p in book_export.EXPORT_BIOS_DIR.glob("*.txt"))
        self.assertEqual(sorted(pinned), files, "sources.json must list every export bio")
        for name in files:
            slug, lang, _ = name.split(".")
            source = (
                english[slug] if lang == "en"
                else (translated / f"author_bios_{lang}" / f"{slug}.html").read_text(encoding="utf-8")
            )
            digest = hashlib.sha256(source.encode()).hexdigest()[:16]
            self.assertEqual(pinned[name], digest, f"{name}: its author's long bio changed — re-check it")


class CoverTests(TestCase):
    def setUp(self):
        book_export._cover_bytes.cache_clear()

    @override_settings(PUBLIC_SITE_URL="https://ochorus.test")
    def test_a_failed_fetch_is_not_cached(self):
        import requests

        ok = mock.Mock(content=b"jpeg", raise_for_status=lambda: None)
        with mock.patch.object(book_export.Path, "is_file", return_value=False), mock.patch.object(
            book_export.requests, "get", side_effect=[requests.ConnectionError("down"), ok]
        ) as get:
            self.assertIsNone(book_export.load_cover("/covers/x.jpg"))
            cover = book_export.load_cover("/covers/x.jpg")
        self.assertEqual(cover.data, b"jpeg")
        self.assertEqual(get.call_args.args[0], "https://ochorus.test/covers/x.jpg")

    def test_webp_and_blank_have_no_cover(self):
        self.assertIsNone(book_export.load_cover(""))
        self.assertIsNone(book_export.load_cover("/covers/x.webp"))

    def test_a_wordless_ground_exports_its_twin(self):
        # A painting or plate has no title in its pixels; the site draws one
        # over it. The image of the cover as the site shows it is the twin.
        def edition(url, lang="es"):
            return mock.Mock(slug="x", language=lang, cover_url=url)

        self.assertEqual(book_export.cover_image_url(edition("/covers/art/x.jpg")), "/covers/es/x.png")
        self.assertEqual(book_export.cover_image_url(edition("/covers/x.svg", "en")), "/covers/x.png")
        self.assertEqual(book_export.cover_image_url(edition("/covers/x.jpg", "en")), "/covers/x.jpg")

    def test_a_bundled_cover_needs_no_network(self):
        slug, lang = next(iter(export_policy.EXPORT_PILOT))
        book = mock.Mock(slug=slug, language=lang, cover_url=_fixture_cover_url(slug, lang))
        with mock.patch.object(book_export, "load_cover", side_effect=AssertionError("fetched")):
            cover = book_export.edition_cover(book)
        self.assertIsNotNone(cover)

    def test_every_pilot_edition_bundles_the_cover_the_site_shows(self):
        # The API image has no frontend/static, and fetching the cover from the
        # site failed in production — so each exportable edition carries a
        # committed copy, and it must be the file the site serves today.
        for slug, lang in sorted(export_policy.EXPORT_EDITIONS):
            book = mock.Mock(slug=slug, language=lang, cover_url=_fixture_cover_url(slug, lang))
            bundled = book_export.bundled_cover_path(book)
            self.assertIsNotNone(bundled, f"{slug} ({lang}) has no raster cover to bundle")
            fix = f"run: manage.py export_book {slug} --language {lang}"
            self.assertTrue(bundled.is_file(), f"{bundled.name} is missing — {fix}")
            self.assertEqual(
                bundled.read_bytes(),
                book_export.site_cover_file(book).read_bytes(),
                f"{bundled.name} is stale — {fix}",
            )


def _fixture_fields(slug: str, language: str) -> dict:
    import json

    from .content_fixtures import book_fixture_path

    rows = json.loads(book_fixture_path(slug, language).read_text(encoding="utf-8"))
    return next(r["fields"] for r in rows if r["model"] == "library.book")


def _fixture_cover_url(slug: str, language: str) -> str:
    return _fixture_fields(slug, language)["cover_url"]
