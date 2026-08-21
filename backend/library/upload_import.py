"""Parse an uploaded Word (.docx) or PDF document into structured library content.

Powers the admin "upload a document" import. It turns raw bytes into a *preview*
— detected chapters (a book) or a single body (a sermon) — WITHOUT saving, so an
admin can review before publishing (see ``AdminImportParseView`` /
``AdminImportPublishView``). Reuses the existing ingestion helpers (PyMuPDF block
extraction + the chapterizer + the HTML cleaner) and adds Word support via
mammoth.

Out of scope: OCR of scanned *image* PDFs — those have no extractable text layer
and are detected and reported rather than silently producing an empty import.
"""

from __future__ import annotations

import io
import re
from html import escape

import mammoth
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils.text import slugify

from . import qa
from .covers import ink_safe
from .ingest import (
    clean_fragment,
    clean_title,
    is_front_matter,
    strip_trailing_pagenum,
    word_count,
)
from .management.commands.import_ochorus import chapterize, pdf_blocks
from .models import Author, Book, Chapter, Sermon

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

# A section is (title, body_html); an empty title means "untitled".
Section = tuple[str, str]


class ParseError(Exception):
    """A problem the admin should see (bad file, scanned PDF, empty document)."""


# --- format extraction --------------------------------------------------------


def _docx_html(data: bytes) -> str:
    try:
        return mammoth.convert_to_html(io.BytesIO(data)).value or ""
    except Exception as exc:  # mammoth raises on non-docx / corrupt files
        raise ParseError(f"Couldn't read this Word document: {exc}") from exc


def _split_on_headings(html: str) -> list[Section]:
    """Split cleaned HTML into (title, body) sections at each top-level heading."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    sections: list[Section] = []
    title: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if buf or title:
            sections.append((title or "", "".join(buf)))

    for el in root.find_all(recursive=False):
        if el.name in ("h1", "h2"):
            flush()
            title, buf = el.get_text(" ", strip=True), []
        else:
            buf.append(str(el))
    flush()
    return sections


def _blocks_to_html(blocks: list[tuple[str, float]]) -> str:
    """PDF text blocks as paragraphs."""
    return "".join(f"<p>{escape(text)}</p>" for text, _ in blocks if text.strip())


def _looks_scanned(blocks: list[tuple[str, float]]) -> bool:
    """A PDF with no meaningful text layer is a scan — we can't extract it."""
    return sum(len(t.strip()) for t, _ in blocks) < 40


# --- public API ---------------------------------------------------------------


def _clean_body(html: str) -> tuple[str, int]:
    """The one cleaning contract, shared by preview and publish.

    Strips to the allowlisted-tag fragment, drops an absorbed trailing page
    number, and returns ``(cleaned_html, word_count)`` so callers apply the same
    "< 5 words is empty" floor everywhere.
    """
    body = strip_trailing_pagenum(clean_fragment(html))
    return body, word_count(body)


def _finalize(sections: list[Section]) -> list[dict]:
    """Clean each section, drop empties and front matter; return preview dicts."""
    out: list[dict] = []
    for raw_title, raw_body in sections:
        title = clean_title(raw_title) if raw_title else ""
        # Skip TOC / index / title-page sections the same way the PDF chapterizer
        # does, so a .docx whose front matter is styled as a heading doesn't
        # publish it as a real chapter.
        if title and is_front_matter(title):
            continue
        body, words = _clean_body(raw_body)
        if words < 5:
            continue
        out.append({"title": title, "html": body, "words": words})
    return out


def parse_upload(data: bytes, filename: str, kind: str) -> dict:
    """Parse an uploaded document into a preview.

    Returns ``{"kind", "chapters": [{title, html, words}], "suggested_title"}``.
    For a sermon there is exactly one entry (the whole body). Raises ``ParseError``
    with an admin-facing message for anything unusable.
    """
    if kind not in ("book", "sermon"):
        raise ParseError("kind must be 'book' or 'sermon'.")
    if not data:
        raise ParseError("The uploaded file was empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ParseError("File is too large (max 25 MB).")

    name = (filename or "").lower()
    is_pdf = name.endswith(".pdf") or data[:5] == b"%PDF-"
    is_docx = name.endswith(".docx")
    if not (is_pdf or is_docx):
        raise ParseError("Unsupported file — upload a .docx or .pdf.")

    # Extract PDF text once here; the scanned check, chapterizer, and sermon body
    # all reuse these blocks rather than re-parsing the file.
    blocks: list[tuple[str, float]] = []
    body_size = 0.0
    if is_pdf:
        try:
            blocks, body_size = pdf_blocks(data)
        except Exception as exc:  # PyMuPDF raises on corrupt / mislabelled PDFs
            raise ParseError(f"Couldn't read this PDF: {exc}") from exc
        if _looks_scanned(blocks):
            raise ParseError(
                "This PDF looks like a scanned image with no text to extract. "
                "OCR isn't supported yet — please upload a text PDF or a Word document."
            )

    if kind == "sermon":
        html = _docx_html(data) if is_docx else _blocks_to_html(blocks)
        chapters = _finalize([("", html)])
    elif is_docx:
        html = _docx_html(data)
        # Split on Word heading styles; if the doc has none, keep it as one
        # chapter so the admin still gets the text to split in review.
        sections = _split_on_headings(html) or [("", html)]
        chapters = _finalize(sections)
    else:  # book, pdf
        # Fall back to the whole document as one chapter when the chapterizer
        # can't find breaks — better a reviewable single chapter than an error.
        sections = chapterize(blocks, body_size) or [("", _blocks_to_html(blocks))]
        chapters = _finalize(sections)

    if not chapters:
        raise ParseError("Couldn't find any readable text in this document.")

    # Suggest a title: first non-empty section title, else the filename stem.
    suggested = next((c["title"] for c in chapters if c["title"]), "")
    if not suggested and filename:
        suggested = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()

    # Content-quality warnings for the reviewer. Chapter-title/split checks only
    # make sense for a multi-chapter book; a sermon is a single body.
    warnings = qa.qa_report(chapters) if kind == "book" else []

    return {
        "kind": kind,
        "chapters": chapters,
        "suggested_title": suggested,
        "warnings": warnings,
    }


# --- publishing ---------------------------------------------------------------


def _unique_slug(base: str, model, language: str) -> str:
    """A slug unique for (slug, language) on the given model."""
    root = slugify(base)[:150] or "untitled"
    slug = root
    n = 2
    while model.objects.filter(slug=slug, language=language).exists():
        slug = f"{root}-{n}"
        n += 1
    return slug


def _clean_hex(value) -> str:
    """A validated CSS hex accent (#rgb / #rgba / #rrggbb / #rrggbbaa), else empty."""
    v = str(value or "").strip()
    return v if re.fullmatch(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", v) else ""


def _plate_hex(value) -> str:
    """A validated accent, floored so white type can sit on it.

    An admin picks this colour in a `<input type="color">` with nothing to tell
    them a pale one leaves the byline under 4.5:1, and an imported row never
    passes through the fixture gate that would catch it. Empty stays empty — the
    drawer supplies the house blue — and a short or alpha form is left alone,
    since `ink_safe` speaks #rrggbb and mapping #abc to the default would
    replace the admin's pick rather than darken it.
    """
    cleaned = _clean_hex(value)
    return ink_safe(cleaned) if re.fullmatch(r"#[0-9a-fA-F]{6}", cleaned) else cleaned


def _clean_year(value) -> int | None:
    """A plausible publication year (1..2100), else None."""
    try:
        y = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return y if 0 < y <= 2100 else None


def _http_url(value) -> str:
    """An http(s) URL, else empty (the model's URLField isn't full_clean()'d here)."""
    v = str(value or "").strip()
    return v if v.startswith(("http://", "https://")) else ""


@transaction.atomic
def create_book(
    author: Author,
    title: str,
    chapters: list[dict],
    language: str = "en",
    source_url: str = "",
    *,
    subtitle: str = "",
    cover_color: str = "",
    cover_url: str = "",
    publication_year=None,
    attribution: str = "",
) -> Book:
    """Create a published Book with chapters from reviewed preview sections.

    The section HTML is re-cleaned here (not trusted from the client round-trip),
    so a tampered payload can only yield valid content or a rejection. Raises
    ``ParseError`` — rolling back the whole write — if no chapter survives.
    """
    slug = _unique_slug(title, Book, language)
    last = Book.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0
    book = Book.objects.create(
        author=author,
        slug=slug,
        language=language,
        title=title.strip()[:300],
        subtitle=str(subtitle or "").strip()[:300],
        source_type=Book.SourceType.PUBLIC_DOMAIN,
        source_url=_http_url(source_url),
        cover_url=_http_url(cover_url),
        cover_color=_plate_hex(cover_color),
        publication_year=_clean_year(publication_year),
        attribution=str(attribution or "").strip(),
        sort_order=last + 1,
        is_published=True,
    )
    order = 0
    for ch in chapters:
        if not isinstance(ch, dict):  # tolerate a malformed publish payload
            continue
        body, words = _clean_body(ch.get("html", ""))
        if words < 5:
            continue
        order += 1
        Chapter.objects.create(
            book=book,
            order=order,
            title=(clean_title(ch.get("title") or "") or f"Chapter {order}")[:300],
            body_html=body,
            word_count=words,
        )
    if order == 0:
        raise ParseError("No chapters had readable text.")
    return book


@transaction.atomic
def create_sermon(
    author: Author,
    title: str,
    body_html: str,
    language: str = "en",
    scripture_ref: str = "",
    source_url: str = "",
) -> Sermon:
    """Create a published Sermon from a reviewed preview body.

    The body is re-cleaned here rather than trusted from the client round-trip;
    if nothing readable survives, raises ``ParseError`` instead of committing a
    blank sermon (the same floor ``create_book`` applies per chapter).
    """
    body, words = _clean_body(body_html)
    if words < 5:
        raise ParseError("The sermon had no readable text.")
    slug = _unique_slug(title, Sermon, language)
    last = Sermon.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0
    return Sermon.objects.create(
        author=author,
        slug=slug,
        language=language,
        title=title.strip()[:300],
        scripture_ref=scripture_ref.strip()[:160],
        body_html=body,
        word_count=words,
        source_url=_http_url(source_url),
        sort_order=last + 1,
        is_published=True,
    )
