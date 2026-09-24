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
        author = Author.objects.create(slug="a-writer", name="A. Writer")
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
        colophon = self._zip(self._get()).read("OEBPS/colophon.xhtml").decode()
        self.assertIn("awaiting review", colophon)

    def test_same_content_same_bytes_and_a_304(self):
        first = self._get()
        self.assertEqual(first.content, self._get().content)
        again = self._get(HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")

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

    def test_print_contents_carries_page_numbers_when_given(self):
        ed = book_export.build_edition(self.book)
        numbered = book_export.render_print_html(ed, pages={"about": 4, "ch1": 5, "ch2": 9})
        self.assertIn('<span class="pg">9</span>', numbered)
        # The first pass reserves the column empty, so the layout can't move.
        self.assertIn('<span class="pg"></span>', book_export.render_print_html(ed))


class PilotTests(TestCase):
    def test_every_pilot_language_has_back_matter(self):
        for _slug, lang in export_policy.EXPORT_PILOT:
            self.assertIn(lang, book_export.STRINGS)
