"""Downloadable editions of a book: EPUB (built per request) and print HTML.

Both formats are assembled from the same parts — a cover, a title page, "About
Ochorus", a short biography of the author, "About this work", the chapters, and
a colophon — so an EPUB and a PDF of one edition
can never disagree about what the book contains. The chapters come straight
from the database, so a download always matches what the reader serves,
including fixes that reached production by data migration rather than fixture.

EPUB is built on request by ``BookEpubView``: a book is a few hundred KB of
zipped XHTML and takes milliseconds. The view's ETag is the shared content
version (``http_cache``), checked before anything is built; the zip itself is
deterministic (fixed timestamps and member order), so equal content is equal
bytes.

PDF is NOT built on the API: that needs a browser engine for page layout and
for Arabic/Devanagari shaping, and the API image has none. ``export_book``
renders the print HTML below and prints it with headless Chrome off-server; the
file ships as a static asset at ``/pdfs/<slug>.pdf`` via ``Book.pdf_url``.

Which editions are exportable is decided in ``library/export_policy.py``. A new
language also needs its back matter in ``STRINGS`` below, because that is
Ochorus's own prose and there is no English fallback.
"""

from __future__ import annotations

import html
import io
import json
import logging
import uuid
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import requests
from django.conf import settings
from lxml import etree
from lxml import html as lxml_html

from .covers import twin_path
from .languages import entry as language_entry
from .localization import DEFAULT_LANGUAGE
from .models import Book

log = logging.getLogger(__name__)

#: The back-matter prose, per language. A language without an entry cannot be
#: exported: this is Ochorus's own writing, and there is no English fallback.
STRINGS = {
    "en": {
        "contents": "Contents",
        "about": "About this work",
        "chapter": "Chapter {n}",
        "published": "First published {year}.",
        "public_domain": (
            "The text of this book is in the public domain. This edition was "
            "prepared by Ochorus, a free library of Christian classics."
        ),
        "translation_rights": (
            "The original text of this book is in the public domain. This "
            "translation was prepared by Ochorus, a free library of Christian "
            "classics."
        ),
        # An in-copyright original (see ``is_in_copyright``): its © line comes
        # from the book row; these say who made this edition.
        "edition": "This edition was prepared by Ochorus, a free library of Christian classics.",
        "translation_edition": (
            "This translation was prepared by Ochorus, a free library of Christian classics."
        ),
        "ai_unreviewed": (
            "This is an AI translation that is awaiting review by a native "
            "speaker. It is not the author's original text."
        ),
        "read_online": "Read it online, free, at",
        # The short-biography page after "About Ochorus", before the contents.
        "author_title": "About the Author",
        "full_bio": "Read the full biography at",
        "more": "More free classics at",
        # The "About Ochorus" page before the contents. Trusted markup, written
        # here (drawn from the site's About page, messages/en.json about_*);
        # {site} is the reader's origin as a link.
        "ochorus_title": "About Ochorus",
        "ochorus_html": (
            '<p class="vision">“To make the epic classics of the Christian faith free '
            "to the Church around the world — in their own language, to the glory of "
            'God.”</p>'
            "<p>Ochorus is a Christian ministry based in Victoria, Canada, and Kampala, "
            "Uganda. Since 2021 we have been finding the great Christian books of the "
            "past, editing them carefully for today’s readers, and giving them away — "
            "free to read and free to keep.</p>"
            "<p>We are not only a website. Books printed in Uganda are placed directly "
            "into people’s hands across East Africa — at pastors’ conferences, and in "
            "the churches, schools and prisons we are invited to serve.</p>"
            "<h2>Keep reading at {site}</h2>"
            "<ul>"
            "<li>Hundreds of classics, sermons and biographies — free, with no ads and "
            "no account needed.</li>"
            "<li>Books in many languages, from English and Swahili to Arabic and "
            "Hindi.</li>"
            "<li>Reading plans, highlights and notes that follow you from device to "
            "device.</li>"
            "<li>Listen aloud, or save a book to read offline.</li>"
            "<li>Free downloads like this one. Share them freely.</li>"
            "</ul>"
            '<p class="verse">“Freely ye have received, freely give.” '
            "<span>Matthew 10:8</span></p>"
        ),
    },
}

# Every other language's back matter, keyed exactly like STRINGS["en"] — kept as
# data so the prose in nine languages doesn't bury this module. The vision line
# is each language's ``about_vision_quote`` from the site's own catalogue.
# ``PilotTests`` holds every key present for every exported language.
STRINGS.update(
    json.loads((Path(__file__).resolve().parent / "export_strings.json").read_text(encoding="utf-8"))
)

#: Fixed zip timestamp, so identical content always zips to identical bytes.
_EPOCH = (1980, 1, 1, 0, 0, 0)
_UUID_NS = uuid.UUID("5d0b6a52-0f1c-4a6e-9f0e-6b1f0c6a7d31")


# --- parts ------------------------------------------------------------------


@dataclass(frozen=True)
class ExportChapter:
    order: int
    title: str
    body: str  # well-formed XHTML fragment


@dataclass(frozen=True)
class Cover:
    data: bytes
    media_type: str
    ext: str


@dataclass(frozen=True)
class Edition:
    book: Book
    author: str
    lang: str
    rtl: bool
    strings: dict
    about: str  # XHTML fragment, may be empty
    chapters: list[ExportChapter]
    cover: Cover | None
    bio: str  # the author's short biography as XHTML paragraphs; "" for none
    url: str  # the book's page on the reader, "" when the site URL is unknown

    @property
    def identifier(self) -> str:
        return f"urn:uuid:{uuid.uuid5(_UUID_NS, f'{self.book.slug}/{self.lang}')}"


def to_xhtml(fragment: str) -> str:
    """Re-serialise a sanitized HTML fragment as well-formed XHTML."""
    if not fragment.strip():
        return ""
    wrapper = lxml_html.fragment_fromstring(fragment, create_parent="div")
    out = [html.escape(wrapper.text or "", quote=False)]
    for child in wrapper:
        out.append(etree.tostring(child, method="xml", encoding="unicode"))
    return "".join(out)


def _site_url() -> str:
    return getattr(settings, "PUBLIC_SITE_URL", "") or ""


def _site_link(site: str) -> str:
    return f'<a dir="ltr" href="{_e(site)}/">{_e(site.split("//")[-1])}</a>'


def book_url(book: Book) -> str:
    site = _site_url()
    if not site:
        return ""
    prefix = "" if book.language == DEFAULT_LANGUAGE else f"/{book.language}"
    return f"{site}{prefix}/books/{book.slug}/"


def export_filename(book: Book, ext: str) -> str:
    """``<slug>.<ext>``, or ``<slug>.<lang>.<ext>`` outside the default language
    — the one naming rule for a downloaded file and for ``static/pdfs/``."""
    lang = "" if book.language == DEFAULT_LANGUAGE else f".{book.language}"
    return f"{book.slug}{lang}.{ext}"


# No webp: EPUB 3.2 core media types don't include it, and older readers can't show it.
_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def load_cover(cover_url: str) -> Cover | None:
    """The cover raster behind ``cover_url``, or None (the EPUB then has none).

    A repo checkout reads it from ``frontend/static``; the API image, which is
    built from ``backend/`` alone, fetches it from the public site. A failure
    is NOT cached — the next download tries again rather than the worker
    serving cover-less books until it restarts.
    """
    ext = Path(cover_url.split("?")[0]).suffix.lower()
    if not cover_url or ext not in _MEDIA:
        return None
    try:
        data = _cover_bytes(cover_url)
    except (OSError, requests.RequestException) as e:
        log.warning("book_export: no cover for %s: %s", cover_url, e)
        return None
    return Cover(data=data, media_type=_MEDIA[ext], ext=ext.replace(".jpeg", ".jpg"))


#: A committed copy of each exportable edition's cover, beside this module.
#: The API image is built from ``backend/`` alone, so it has no
#: ``frontend/static``, and its fetch of the cover from the public site failed
#: in production — every EPUB shipped without one and e-readers drew their own.
#: A file in the image cannot fail that way. ``export_book`` writes it, and
#: ``tests_book_export.CoverTests`` fails when one is missing or stale.
BUNDLED_COVERS = Path(__file__).resolve().parent / "export_covers"


def cover_image_url(book) -> str:
    """The raster that shows this edition's cover the way Ochorus draws it.

    A designed cover is its own image — its title is in its pixels. A painting
    or a plate is a wordless GROUND that the site sets the title over in the
    browser, so the image of it WITH its title is the edition's og twin — the
    same rule as ``coverArt.shareImage`` on the frontend.
    """
    url = book.cover_url or ""
    if url.startswith("/covers/art/") or (url.startswith("/covers/") and url.endswith(".svg")):
        return twin_path(book.slug, book.language)[0]
    return url


def bundled_cover_path(book) -> Path | None:
    """Where this edition's committed cover lives, or None if it can have none."""
    ext = Path(cover_image_url(book).split("?")[0]).suffix.lower()
    if ext not in _MEDIA:
        return None
    return BUNDLED_COVERS / f"{book.slug}.{book.language}{ext.replace('.jpeg', '.jpg')}"


def edition_cover(book) -> Cover | None:
    """The cover for an export: the committed copy, else found as ``load_cover`` does."""
    bundled = bundled_cover_path(book)
    if bundled is not None and bundled.is_file():
        return Cover(data=bundled.read_bytes(), media_type=_MEDIA[bundled.suffix], ext=bundled.suffix)
    return load_cover(cover_image_url(book))


def site_cover_file(book) -> Path:
    """The file the site serves for ``cover_image_url`` — in a repo checkout."""
    return Path(settings.BASE_DIR).parent / "frontend" / "static" / cover_image_url(book).lstrip("/")


@lru_cache(maxsize=16)
def _cover_bytes(cover_url: str) -> bytes:
    """Raises on failure, so lru_cache only ever holds a success."""
    if cover_url.startswith("/"):
        local = Path(settings.BASE_DIR).parent / "frontend" / "static" / cover_url.lstrip("/")
        if local.is_file():
            return local.read_bytes()
        if not _site_url():
            raise FileNotFoundError(cover_url)
        cover_url = _site_url() + cover_url
    # (connect, read): a slow site must not hold a sync worker for long.
    res = requests.get(cover_url, timeout=(3, 5))
    res.raise_for_status()
    return res.content


def author_bio(book: Book) -> str:
    """The author's SHORT biography in the edition's language, or "".

    ``Author.bio`` is English; another language reads its ``AuthorTranslation``.
    No English fallback — the same rule as the site, which shows a translated
    edition's author page in that language or not at all — so a language with
    no translated bio simply has no biography page. An imprint (Ochorus
    Originals) is a publisher, not a person, and gets none either.
    """
    author = book.author
    if author.is_imprint:
        return ""
    if book.language == DEFAULT_LANGUAGE:
        return author.bio.strip()
    tr = author.translations.filter(language=book.language).only("bio").first()
    return tr.bio.strip() if tr else ""


def _bio_paragraphs(text: str) -> str:
    return "".join(f"<p>{_e(p.strip())}</p>" for p in text.split("\n\n") if p.strip())


def author_url(book: Book) -> str:
    site = _site_url()
    if not site:
        return ""
    prefix = "" if book.language == DEFAULT_LANGUAGE else f"/{book.language}"
    return f"{site}{prefix}/authors/{book.author.slug}/"


def build_edition(book: Book) -> Edition:
    strings = STRINGS[book.language]
    chapters = [
        ExportChapter(
            order=order,
            title=title or strings["chapter"].format(n=order),
            body=to_xhtml(body),
        )
        for order, title, body in book.chapters.order_by("order").values_list(
            "order", "title", "body_html"
        )
    ]
    # Only the written "About this work" — not ``description``, which is card
    # and search-snippet copy and reads as a blurb when set as a page.
    about = to_xhtml(book.about_html)
    return Edition(
        book=book,
        author=book.author.name,
        lang=book.language,
        rtl=bool(language_entry(book.language).get("rtl")),
        strings=strings,
        about=about,
        chapters=chapters,
        cover=edition_cover(book),
        bio=_bio_paragraphs(author_bio(book)),
        url=book_url(book),
    )


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def is_in_copyright(book: Book) -> bool:
    """A living author's own work, shared with permission — NOT public domain.

    ``source_type`` can't say so (it has no licensed value; these rows carry
    ``public_domain`` like Growing in Wisdom), so the signal is the rights line
    they carry instead: an ``attribution`` that opens with "©". Every other
    attribution in the library is a credit on a public-domain text.
    """
    return (book.attribution or "").lstrip().startswith("©")


def _rights_key(book: Book) -> str:
    # A translation's words are new, so only its ORIGINAL is public domain —
    # and an in-copyright original isn't public domain at all.
    if is_in_copyright(book):
        return "edition" if book.source_type == Book.SourceType.PUBLIC_DOMAIN else "translation_edition"
    return "public_domain" if book.source_type == Book.SourceType.PUBLIC_DOMAIN else "translation_rights"


def _rights_text(book: Book, strings: dict) -> str:
    """The one-line rights statement (also the EPUB's dc:rights)."""
    if is_in_copyright(book):
        return f"{book.attribution.strip()} {strings[_rights_key(book)]}"
    return strings[_rights_key(book)]


def _rights(ed: Edition) -> str:
    s = ed.strings
    parts = []
    if ed.book.source_type == Book.SourceType.AI_UNREVIEWED:
        parts.append(f'<p class="notice">{_e(s["ai_unreviewed"])}</p>')
    if is_in_copyright(ed.book):
        # The © line IS the rights statement; the edition line follows it.
        # dir="auto": the © line is usually English inside an RTL edition,
        # where bidi would otherwise move its "©" and full stop to the wrong ends.
        parts.append(f'<p dir="auto">{_e(ed.book.attribution.strip())}</p>')
        parts.append(f"<p>{_e(s[_rights_key(ed.book)])}</p>")
    else:
        parts.append(f"<p>{_e(s[_rights_key(ed.book)])}</p>")
        if ed.book.attribution:
            parts.append(f'<p dir="auto">{_e(ed.book.attribution)}</p>')
    return "".join(parts)


def _colophon(ed: Edition) -> str:
    s = ed.strings
    site = _site_url()
    parts = [_rights(ed)]
    if ed.url:
        parts.append(f'<p>{_e(s["read_online"])} <a dir="ltr" href="{_e(ed.url)}">{_e(ed.url)}</a></p>')
    if site:
        parts.append(f'<p>{_e(s["more"])} {_site_link(site)}</p>')
    return "".join(parts)


def _ochorus_page(ed: Edition) -> str:
    link = _site_link(_site_url() or "https://ochorus.com")
    return f'<h1>{_e(ed.strings["ochorus_title"])}</h1>' + ed.strings["ochorus_html"].replace(
        "{site}", link
    )


def _author_page(ed: Edition) -> str:
    """The short biography: name, life dates, the bio, and where to read more."""
    a = ed.book.author
    parts = [f'<h1>{_e(ed.strings["author_title"])}</h1>', f'<p class="name">{_e(ed.author)}</p>']
    if a.birth_year:
        parts.append(f'<p class="dates">{a.birth_year}–{a.death_year or ""}</p>')
    parts.append(ed.bio)
    link = author_url(ed.book)
    if link:
        parts.append(f'<p class="more">{_e(ed.strings["full_bio"])} <a dir="ltr" href="{_e(link)}">{_e(link)}</a></p>')
    return "".join(parts)


def _title_page(ed: Edition) -> str:
    b = ed.book
    parts = [f'<h1 class="book-title">{_e(b.title)}</h1>']
    if b.subtitle:
        parts.append(f'<p class="subtitle">{_e(b.subtitle)}</p>')
    parts.append(f'<p class="author">{_e(ed.author)}</p>')
    if b.publication_year:
        parts.append(f'<p class="year">{_e(ed.strings["published"].format(year=b.publication_year))}</p>')
    parts.append('<p class="imprint">Ochorus</p>')
    return "".join(parts)


# --- EPUB -------------------------------------------------------------------

EPUB_CSS = """
body { font-family: serif; line-height: 1.5; margin: 0 5%; }
h1 { font-size: 1.5em; text-align: center; margin: 2em 0 1.5em; line-height: 1.25; }
h2 { font-size: 1.2em; margin: 1.5em 0 0.75em; }
p { margin: 0; text-indent: 1.5em; text-align: justify; }
h1 + p, h2 + p, h3 + p, blockquote + p, .noindent { text-indent: 0; }
blockquote { margin: 1em 1.5em; font-style: italic; }
blockquote p { text-indent: 0; }
.titlepage { text-align: center; }
.titlepage p { text-indent: 0; text-align: center; }
.book-title { font-size: 2em; margin-top: 30%; }
.subtitle { font-style: italic; font-size: 1.1em; }
.author { font-size: 1.2em; margin-top: 2em; }
.year { margin-top: 1em; font-size: 0.9em; }
.imprint { margin-top: 30%; letter-spacing: 0.15em; text-transform: uppercase; font-size: 0.8em; }
.back p { text-indent: 0; text-align: left; margin-bottom: 1em; }
.notice { font-weight: bold; }
.ochorus p { text-indent: 0; text-align: left; margin-bottom: 0.8em; }
.ochorus .vision, .ochorus .verse { font-style: italic; text-align: center; }
.ochorus .verse span { display: block; font-style: normal; font-size: 0.85em; }
.ochorus li { margin-bottom: 0.3em; }
.author-page p { text-indent: 0; text-align: left; margin-bottom: 0.8em; }
.author-page .name { text-align: center; font-size: 1.15em; margin-bottom: 0.2em; }
.author-page .dates { text-align: center; font-size: 0.9em; margin-bottom: 1.5em; }
.author-page .more { font-size: 0.9em; margin-top: 1.5em; }
.cover { margin: 0; padding: 0; text-align: center; }
.cover img { max-width: 100%; max-height: 100%; }
nav ol { list-style: none; padding: 0; }
nav li { margin: 0.4em 0; }
""".strip()


def _xhtml(ed: Edition, title: str, body: str, *, body_class: str = "", nav: bool = False) -> str:
    dir_attr = ' dir="rtl"' if ed.rtl else ""
    epub_ns = ' xmlns:epub="http://www.idpf.org/2007/ops"' if nav else ""
    cls = f' class="{body_class}"' if body_class else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml"{epub_ns} xml:lang="{ed.lang}" lang="{ed.lang}"{dir_attr}>\n'
        f'<head><meta charset="utf-8"/><title>{_e(title)}</title>'
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        f"<body{cls}>{body}</body>\n</html>\n"
    )


def render_epub(ed: Edition) -> bytes:
    b, s = ed.book, ed.strings
    # (id, href, title-for-toc or None, xhtml)
    docs: list[tuple[str, str, str | None, str]] = []
    if ed.cover:
        docs.append((
            "cover", "cover.xhtml", None,
            _xhtml(ed, b.title, f'<div class="cover"><img src="cover{ed.cover.ext}" alt="{_e(b.title)}"/></div>', body_class="cover"),
        ))
    docs.append(("titlepage", "title.xhtml", None, _xhtml(ed, b.title, _title_page(ed), body_class="titlepage")))
    docs.append(("ochorus", "about-ochorus.xhtml", None, _xhtml(ed, s["ochorus_title"], _ochorus_page(ed), body_class="ochorus")))
    if ed.bio:
        docs.append(("author", "about-author.xhtml", None, _xhtml(ed, s["author_title"], _author_page(ed), body_class="author-page")))
    if ed.about:
        docs.append(("about", "about.xhtml", s["about"], _xhtml(ed, s["about"], f"<h1>{_e(s['about'])}</h1>{ed.about}")))
    for ch in ed.chapters:
        docs.append((
            f"ch{ch.order:03d}", f"chapter-{ch.order:03d}.xhtml", ch.title,
            _xhtml(ed, ch.title, f"<h1>{_e(ch.title)}</h1>{ch.body}"),
        ))
    docs.append(("colophon", "colophon.xhtml", None, _xhtml(ed, "Ochorus", _colophon(ed), body_class="back")))

    toc_items = [(href, title) for _, href, title, _ in docs if title]
    nav = _xhtml(
        ed, s["contents"],
        f'<nav epub:type="toc" id="toc"><h1>{_e(s["contents"])}</h1><ol>'
        + "".join(f'<li><a href="{href}">{_e(t)}</a></li>' for href, t in toc_items)
        + "</ol></nav>",
        nav=True,
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f'<head><meta name="dtb:uid" content="{ed.identifier}"/></head>'
        f"<docTitle><text>{_e(b.title)}</text></docTitle><navMap>"
        + "".join(
            f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{_e(t)}</text></navLabel>'
            f'<content src="{href}"/></navPoint>'
            for i, (href, t) in enumerate(toc_items, 1)
        )
        + "</navMap></ncx>\n"
    )

    modified = b.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    if ed.cover:
        manifest.append(
            f'<item id="cover-image" href="cover{ed.cover.ext}" media-type="{ed.cover.media_type}" properties="cover-image"/>'
        )
    manifest += [f'<item id="{i}" href="{h}" media-type="application/xhtml+xml"/>' for i, h, _, _ in docs]
    spine = "".join(f'<itemref idref="{i}"/>' for i, _, _, _ in docs)
    direction = ' page-progression-direction="rtl"' if ed.rtl else ""
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" '
        f'xml:lang="{ed.lang}">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="bookid">{ed.identifier}</dc:identifier>'
        f"<dc:title>{_e(b.title)}</dc:title>"
        f"<dc:creator>{_e(ed.author)}</dc:creator>"
        f"<dc:language>{ed.lang}</dc:language>"
        "<dc:publisher>Ochorus</dc:publisher>"
        f"<dc:rights>{_e(_rights_text(b, s))}</dc:rights>"
        + (f"<dc:description>{_e(b.description)}</dc:description>" if b.description else "")
        + (f"<dc:source>{_e(ed.url)}</dc:source>" if ed.url else "")
        + f'<meta property="dcterms:modified">{modified}</meta>'
        + ('<meta name="cover" content="cover-image"/>' if ed.cover else "")
        + "</metadata>"
        f"<manifest>{''.join(manifest)}</manifest>"
        f'<spine toc="ncx"{direction}>{spine}</spine>'
        "</package>\n"
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        def put(name: str, data, compress=True):
            info = zipfile.ZipInfo(name, date_time=_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)

        # The mimetype entry must come first and be stored uncompressed.
        put("mimetype", "application/epub+zip", compress=False)
        put("META-INF/container.xml", container)
        put("OEBPS/content.opf", opf)
        put("OEBPS/nav.xhtml", nav)
        put("OEBPS/toc.ncx", ncx)
        put("OEBPS/style.css", EPUB_CSS)
        if ed.cover:
            put(f"OEBPS/cover{ed.cover.ext}", ed.cover.data, compress=False)
        for _, href, _, doc in docs:
            put(f"OEBPS/{href}", doc)
    return buf.getvalue()


# --- print HTML (→ PDF) ------------------------------------------------------

PRINT_CSS = """
@page { size: A5; margin: 18mm 16mm 20mm; }
@page { @bottom-center { content: counter(page); font: 9pt "EB Garamond", Georgia, serif; color: #666; } }
@page :first { margin: 0; @bottom-center { content: none; } }
@page front { @bottom-center { content: none; } }
html { font-family: "EB Garamond", Georgia, serif; font-size: 11.5pt; line-height: 1.45; color: #111; }
body { margin: 0; }
.cover { page: front; break-after: page; height: 210mm; width: 148mm; margin: 0; overflow: hidden; }
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.titlepage { page: front; break-after: page; text-align: center; padding-top: 45mm; }
.titlepage p { text-indent: 0; text-align: center; }
.book-title { font-size: 26pt; font-weight: 600; line-height: 1.15; margin: 0 0 6mm; }
.subtitle { font-style: italic; font-size: 13pt; margin: 0; }
.author { font-size: 14pt; margin: 14mm 0 0; }
.year { font-size: 10pt; margin: 4mm 0 0; color: #555; }
.imprint { margin-top: 55mm; letter-spacing: 0.2em; text-transform: uppercase; font-size: 8.5pt; color: #555; }
.ochorus { page: front; break-after: page; font-size: 10.5pt; }
.ochorus h1 { font-size: 17pt; font-weight: 600; text-align: center; margin: 8mm 0 6mm; }
.ochorus h2 { font-size: 11.5pt; margin: 5mm 0 2mm; }
.ochorus p { text-indent: 0; text-align: left; margin: 0 0 2.5mm; }
.ochorus .vision { font-style: italic; text-align: center; font-size: 11.5pt; margin: 0 4mm 5mm; }
.ochorus ul { margin: 0 0 4mm; padding-inline-start: 5mm; }
.ochorus li { margin: 0 0 1.2mm; }
.ochorus a { color: inherit; }
.ochorus .verse { font-style: italic; text-align: center; margin-top: 6mm; }
.ochorus .verse span { display: block; font-style: normal; font-size: 9pt; color: #555; margin-top: 1mm; }
.author-page { page: front; break-after: page; font-size: 10.5pt; }
.author-page h1 { font-size: 17pt; font-weight: 600; text-align: center; margin: 8mm 0 6mm; }
.author-page p { text-indent: 0; text-align: left; margin: 0 0 2.5mm; }
.author-page .name { text-align: center; font-size: 13pt; margin: 0 0 1mm; }
.author-page .dates { text-align: center; font-size: 10pt; color: #555; margin: 0 0 6mm; }
.author-page .more { font-size: 9.5pt; margin-top: 6mm; }
.author-page a { color: inherit; }
.contents { page: front; break-after: page; }
.contents ol { list-style: none; padding: 0; margin: 0; }
.contents li { margin: 0 0 2.2mm; }
.contents a { color: inherit; text-decoration: none; display: flex; align-items: baseline; gap: 2mm; }
.contents .leader { flex: 1; border-bottom: 0.5pt dotted #999; transform: translateY(-1mm); }
.contents .pg { font-variant-numeric: tabular-nums; min-width: 7mm; text-align: end; }
section.part { break-before: page; }
h1.part-title { font-size: 17pt; font-weight: 600; text-align: center; margin: 22mm 0 10mm; line-height: 1.2; }
h2 { font-size: 13pt; margin: 6mm 0 3mm; break-after: avoid; }
p { margin: 0; text-indent: 1.4em; text-align: justify; hyphens: auto; orphans: 2; widows: 2; }
h1 + p, h2 + p, h3 + p, blockquote + p { text-indent: 0; }
blockquote { margin: 3mm 6mm; font-style: italic; }
blockquote p { text-indent: 0; }
.back { padding-top: 60mm; }
.back p { text-indent: 0; text-align: left; margin-bottom: 3mm; font-size: 10pt; }
.back a { color: inherit; }
.notice { font-weight: 600; }
""".strip()

_FONT_LINK = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=EB+Garamond:ital,wght@0,400;0,600;1,400&amp;display=swap"/>'
)


def render_print_html(
    ed: Edition, cover_src: str | None = None, pages: dict[str, int] | None = None
) -> str:
    """The whole book as one print-ready HTML page (A5), for headless Chrome.

    ``cover_src`` is where the page loads the cover from; the caller writes
    the cover next to the HTML and passes its file name.

    ``pages`` maps a contents anchor ("about", "ch3") to its page number.
    Chrome can't resolve ``target-counter()`` in print, so the caller prints
    twice: once without it (the numbers column is still reserved, so nothing
    moves), reads where each anchor landed, then again with it.
    """
    b, s = ed.book, ed.strings
    parts = []
    if ed.cover and cover_src:
        parts.append(f'<div class="cover"><img src="{_e(cover_src)}" alt=""/></div>')
    parts.append(f'<div class="titlepage">{_title_page(ed)}</div>')
    parts.append(f'<div class="ochorus">{_ochorus_page(ed)}</div>')
    if ed.bio:
        parts.append(f'<div class="author-page">{_author_page(ed)}</div>')
    toc = []
    if ed.about:
        toc.append(("about", s["about"]))
    toc += [(f"ch{c.order}", c.title) for c in ed.chapters]
    parts.append(
        f'<nav class="contents"><h1 class="part-title">{_e(s["contents"])}</h1><ol>'
        + "".join(
            f'<li><a href="#{i}"><span>{_e(t)}</span><span class="leader"></span>'
            f'<span class="pg">{(pages or {}).get(i, "")}</span></a></li>'
            for i, t in toc
        )
        + "</ol></nav>"
    )
    if ed.about:
        parts.append(f'<section class="part" id="about"><h1 class="part-title">{_e(s["about"])}</h1>{ed.about}</section>')
    for c in ed.chapters:
        parts.append(f'<section class="part" id="ch{c.order}"><h1 class="part-title">{_e(c.title)}</h1>{c.body}</section>')
    parts.append(f'<section class="part back">{_colophon(ed)}</section>')
    dir_attr = ' dir="rtl"' if ed.rtl else ""
    return (
        f'<!doctype html><html lang="{ed.lang}"{dir_attr}><head><meta charset="utf-8"/>'
        f"<title>{_e(b.title)} — {_e(ed.author)}</title>{_FONT_LINK}"
        f"<style>{PRINT_CSS}</style></head><body>{''.join(parts)}</body></html>"
    )
