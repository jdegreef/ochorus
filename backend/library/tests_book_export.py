"""Downloadable editions (library/book_export.py): the EPUB endpoint and the
parts both formats share.

What these guard is shape — that a download is a readable EPUB, carries the
rights line and (for a machine translation) the review notice, and is only
served for an edition we have vetted. Whether it LOOKS right on a Kindle is a
human check on a device.
"""

from __future__ import annotations

import io
import zipfile
from unittest import mock

from django.test import TestCase, override_settings
from lxml import etree

from . import book_export, export_policy
from .models import Author, Book, Chapter

PILOT = frozenset({("pilot-book", "en")})


@override_settings(PUBLIC_SITE_URL="https://ochorus.test")
@mock.patch.object(export_policy, "EXPORT_PILOT", PILOT)
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

    def test_an_imprint_has_no_biography_page(self):
        self.book.author.is_imprint = True
        self.book.author.save()
        self.assertNotIn("OEBPS/about-author.xhtml", self._zip(self._get()).namelist())

    def test_print_contents_carries_page_numbers_when_given(self):
        ed = book_export.build_edition(self.book)
        numbered = book_export.render_print_html(ed, pages={"about": 4, "ch1": 5, "ch2": 9})
        self.assertIn('<span class="pg">9</span>', numbered)
        # The first pass reserves the column empty, so the layout can't move.
        self.assertIn('<span class="pg"></span>', book_export.render_print_html(ed))


class PilotTests(TestCase):
    def test_every_pilot_language_has_back_matter(self):
        keys = set(book_export.STRINGS["en"])
        for _slug, lang in export_policy.EXPORT_PILOT:
            self.assertIn(lang, book_export.STRINGS)
            self.assertEqual(set(book_export.STRINGS[lang]), keys, f"{lang} back matter is incomplete")

    def test_every_pilot_edition_has_its_pdf(self):
        # The book page links pdf_url, and the prerender fails on a missing file
        # — but that's the web build; this catches it in CI first.
        import json

        from .content_fixtures import book_fixture_path

        static = book_export.Path(book_export.settings.BASE_DIR).parent / "frontend" / "static"
        for slug, lang in sorted(export_policy.EXPORT_PILOT):
            fields = json.loads(book_fixture_path(slug, lang).read_text(encoding="utf-8"))[0]["fields"]
            pdf = fields.get("pdf_url", "")
            self.assertTrue(pdf, f"{slug} ({lang}) is exportable but has no pdf_url")
            self.assertTrue((static / pdf.lstrip("/")).is_file(), f"{pdf} is missing — run export_book")


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
        for slug, lang in sorted(export_policy.EXPORT_PILOT):
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


def _fixture_cover_url(slug: str, language: str) -> str:
    import json

    from .content_fixtures import book_fixture_path

    rows = json.loads(book_fixture_path(slug, language).read_text(encoding="utf-8"))
    return rows[0]["fields"]["cover_url"]
