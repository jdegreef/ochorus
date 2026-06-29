"""Import books from the ochorus.com catalogue.

Each book on ochorus.com is a landing page (/books/<slug>/) with metadata and a
downloadable PDF. We scrape the metadata, download the PDF, extract its text
with PyMuPDF, split it into chapters on "CHAPTER X" markers, and upsert.

    python manage.py import_ochorus                 # all books
    python manage.py import_ochorus the-inner-chamber  # one or more by slug
    python manage.py import_ochorus --list          # list catalogue slugs
    python manage.py import_ochorus --limit 3       # first N (for testing)
"""

from __future__ import annotations

import html
import re
from collections import Counter
from urllib.parse import urljoin

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from library.models import Author, Book, Chapter

CATALOG_URL = "https://ochorus.com/ochorus-books/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

_BOOK_RE = re.compile(r"/books/([a-z0-9-]+)/?$", re.I)
# Chapter heading at the start of a text block: "CHAPTER FOUR", "CHAPTER 4", etc.
_CHAP_RE = re.compile(
    r"^\s*CHAPTER\s+([0-9]+|[IVXLCDM]+|[A-Z]+(?:[ -][A-Z]+)?)\b[\s.:-]*(.*)$", re.I
)
_PAGENUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
_META_FIELDS = ("Author", "Pages", "Nationality", "Language", "File Size")
_TENS = {"TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"}
_ONES = {"ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE"}
_BIO_YEARS = re.compile(r"\(\s*\d{3,4}\s*[–-]\s*\d{0,4}\s*\)")


def fetch(url: str, binary: bool = False):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=90)
    resp.raise_for_status()
    return resp.content if binary else resp.text


def catalog_slugs() -> list[str]:
    soup = BeautifulSoup(fetch(CATALOG_URL), "lxml")
    out, seen = [], set()
    for a in soup.select("a[href]"):
        m = _BOOK_RE.search(a.get("href", ""))
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def parse_book_page(slug: str) -> dict:
    url = f"https://ochorus.com/books/{slug}/"
    soup = BeautifulSoup(fetch(url), "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else slug.replace("-", " ").title()

    og = soup.find("meta", property="og:image")
    cover_url = og.get("content", "") if og else ""

    pdf_url = ""
    for a in soup.select("a[href]"):
        if a.get("href", "").lower().endswith(".pdf"):
            pdf_url = urljoin(url, a["href"])
            break

    # Metadata + description are rendered as a flat text run on the page.
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    author = _field(text, "Author")
    description = ""
    m = re.search(r"Description:\s*(?:Book Overview)?\s*(.+?)(?:Download|Related|Newsletter|$)", text)
    if m:
        description = m.group(1).strip()[:1500]

    return {
        "slug": slug,
        "title": title,
        "author": author or "Ochorus",
        "cover_url": cover_url,
        "pdf_url": pdf_url,
        "description": description,
        "source_url": url,
    }


def _field(text: str, name: str) -> str:
    others = "|".join(f for f in _META_FIELDS if f != name)
    m = re.search(rf"{name}:\s*(.+?)\s*(?:{others}|More Details|Download|Description|$)", text)
    return m.group(1).strip() if m else ""


# --- PDF → chapters -----------------------------------------------------------

def pdf_blocks(pdf_bytes: bytes) -> tuple[list[tuple[str, float]], float]:
    """Return ([(paragraph_text, max_font_size), …], body_font_size).

    One entry per PyMuPDF text block (≈ a paragraph), tagged with its largest
    font size so headings (set larger than body text) can be detected.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    sizes: Counter[int] = Counter()
    blocks: list[tuple[str, float]] = []
    dropcap = ""  # a decorative initial extracted as its own one-letter block
    for page in doc:
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:  # skip images
                continue
            spans = [s for line in b.get("lines", []) for s in line.get("spans", [])]
            if not spans:
                continue
            t = " ".join(" ".join(s["text"] for s in spans).split())
            if not t or _PAGENUM_RE.match(t):
                continue
            for s in spans:
                sizes[round(s["size"])] += max(1, len(s["text"].strip()))
            size = max(s["size"] for s in spans)
            # A lone uppercase letter is a drop cap; glue it to the next block
            # (e.g. "I" + "n regard…" → "In regard…").
            if len(t) == 1 and t.isalpha() and t.isupper():
                dropcap = t
                continue
            if dropcap:
                t = dropcap + t
                dropcap = ""
            blocks.append((t, size))
    doc.close()
    body = float(sizes.most_common(1)[0][0]) if sizes else 12.0
    return blocks, body


def _normalize_number(num: str, trailing: str) -> tuple[str, str]:
    """Fold a spelled-out compound number ("THIRTY", "SIX") into one ("Thirty-Six")."""
    label = num
    if num.upper() in _TENS:
        m = re.match(r"\s*([A-Za-z]+)\b", trailing)
        if m and m.group(1).upper() in _ONES:
            label = f"{num}-{m.group(1)}"
            trailing = trailing[m.end():]
    return label.title(), trailing.strip(" .:-")


def _ends_sentence(s: str) -> bool:
    """True if a block ends a sentence (so the next block is a new paragraph)."""
    s = s.rstrip()
    while s and s[-1] in "\"”’')]":  # ignore trailing quotes/brackets
        s = s[:-1]
    return (not s) or s[-1] in ".!?"


def _merge_paragraphs(paras: list[str]) -> list[str]:
    """Rejoin paragraphs that the PDF split across line/page breaks.

    PyMuPDF emits one block per visual chunk, so a single source paragraph
    often arrives as several blocks ("…struggle with" + "doubt, let me make it
    clearer."). When a block doesn't end a sentence, the next block continues it.
    """
    out: list[str] = []
    for p in paras:
        if out and not _ends_sentence(out[-1]):
            out[-1] = f"{out[-1]} {p}".strip()
        else:
            out.append(p)
    return out


def _is_title_block(p: str) -> bool:
    """A short heading-like block (a chapter title or a biography name)."""
    words = p.split()
    if not words or len(words) > 9:
        return False
    letters = [c for c in p if c.isalpha()]
    mostly_caps = letters and sum(c.isupper() for c in letters) / len(letters) > 0.7
    return bool(mostly_caps or _BIO_YEARS.search(p))


def _chapter_marker_title(block_texts: list[str]) -> tuple[str, list[str]]:
    """Title + remaining body paragraphs for a 'CHAPTER X' segment."""
    m = _CHAP_RE.match(block_texts[0])
    number, trailing = _normalize_number(m.group(1), m.group(2))
    title_parts: list[str] = []
    body_paras: list[str] = []
    cap = re.match(r"([A-Z0-9'’,\- ]{3,}?)(?=[a-z]|$)", trailing)
    if cap and cap.group(1).strip(" '-,"):
        title_parts.append(cap.group(1).strip(" '-,"))
        leftover = trailing[cap.end():].strip(" .:-")
        if len(leftover.split()) > 4:
            body_paras.append(leftover)
    rest = block_texts[1:]
    k = 0
    while not body_paras and k < len(rest) and _is_title_block(rest[k]):
        title_parts.append(rest[k])
        k += 1
    body_paras.extend(rest[k:])
    title = f"Chapter {number}"
    if title_parts:
        title += ". " + " ".join(title_parts).title()
    return title, body_paras


def _segment(blocks: list[tuple[str, float]], is_head) -> list[tuple[str, str]]:
    """Split blocks into chapters wherever `is_head(text, size)` is true."""
    starts = [i for i, (t, s) in enumerate(blocks) if is_head(t, s)]
    if len(starts) < 2:
        return []
    chapters: list[tuple[str, str]] = []
    for j, idx in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(blocks)
        seg = [t for t, _ in blocks[idx:end]]
        if _CHAP_RE.match(seg[0]):
            title, body_paras = _chapter_marker_title(seg)
        else:
            # Font heading: the heading block(s) are the title.
            title_parts = [seg[0]]
            k = 1
            while k < len(seg) and _is_title_block(seg[k]) and not _CHAP_RE.match(seg[k]):
                title_parts.append(seg[k])
                k += 1
            title = " ".join(title_parts).strip()
            body_paras = seg[k:]
        body_paras = _merge_paragraphs(body_paras)
        body_html = "".join(f"<p>{html.escape(p)}</p>" for p in body_paras)
        if len(re.sub(r"<[^>]+>", " ", body_html).split()) < 120:  # stub / TOC entry
            continue
        chapters.append((title[:300], body_html))
    return chapters


def chapterize(blocks: list[tuple[str, float]], body_size: float) -> list[tuple[str, str]]:
    """Prefer reliable 'CHAPTER X' markers; fall back to font-size headings for
    PDFs that don't use them (or that yield too few chapters that way)."""
    by_marker = _segment(blocks, lambda t, s: bool(_CHAP_RE.match(t)))
    if len(by_marker) >= 3:
        return by_marker

    # Font fallback. Big text that repeats across the book is a running
    # header/footer (e.g. "Introduction" on every page), not a chapter title —
    # ban anything that appears as a heading more than twice.
    thresh = body_size * 1.18
    head_freq = Counter(
        " ".join(t.lower().split()) for t, s in blocks if s >= thresh and len(t.split()) <= 14
    )
    banned = {k for k, v in head_freq.items() if v > 2}

    def is_font_head(t: str, s: float) -> bool:
        if _CHAP_RE.match(t):
            return True
        return (
            s >= thresh
            and len(t.split()) <= 14
            and " ".join(t.lower().split()) not in banned
        )

    by_font = _segment(blocks, is_font_head)
    return by_font if len(by_font) > len(by_marker) else by_marker


@transaction.atomic
def upsert(meta: dict, chapters: list[tuple[str, str]], sort_order: int) -> Book:
    author, _ = Author.objects.get_or_create(
        slug=slugify(meta["author"])[:120] or "ochorus",
        defaults={"name": meta["author"]},
    )
    book, _ = Book.objects.update_or_create(
        slug=meta["slug"],
        language="en",
        defaults={
            "author": author,
            "title": meta["title"],
            "description": meta["description"],
            "source_type": Book.SourceType.PUBLIC_DOMAIN,
            "source_url": meta["source_url"],
            "cover_url": meta["cover_url"],
            "pdf_url": meta["pdf_url"],
            "sort_order": sort_order,
            "is_published": bool(chapters),
        },
    )
    book.chapters.all().delete()
    for order, (title, body) in enumerate(chapters, start=1):
        Chapter.objects.create(
            book=book, order=order, title=title[:300], body_html=body,
            word_count=len(re.sub(r"<[^>]+>", " ", body).split()),
        )
    return book


class Command(BaseCommand):
    help = "Import books from the ochorus.com catalogue (PDF → chapters)."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all).")
        parser.add_argument("--list", action="store_true", help="List catalogue slugs and exit.")
        parser.add_argument("--limit", type=int, default=0, help="Only the first N books.")

    def handle(self, *args, **opts):
        slugs = catalog_slugs()
        if opts["list"]:
            for s in slugs:
                self.stdout.write(s)
            self.stdout.write(f"\n{len(slugs)} books.")
            return
        if opts["slugs"]:
            slugs = [s for s in slugs if s in set(opts["slugs"])]
        if opts["limit"]:
            slugs = slugs[: opts["limit"]]

        for i, slug in enumerate(slugs):
            self._import_one(slug, i)

    def _import_one(self, slug: str, sort_order: int):
        try:
            meta = parse_book_page(slug)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"✗ {slug}: page fetch failed: {exc}"))
            return
        self.stdout.write(f"→ {meta['title']} — {meta['author']}")
        if not meta["pdf_url"]:
            self.stderr.write(self.style.WARNING("  no PDF link; skipping"))
            return
        try:
            blocks, body_size = pdf_blocks(fetch(meta["pdf_url"], binary=True))
        except (requests.RequestException, RuntimeError) as exc:
            self.stderr.write(self.style.ERROR(f"  PDF failed: {exc}"))
            return
        chapters = chapterize(blocks, body_size)
        book = upsert(meta, chapters, sort_order)
        if chapters:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
        else:
            self.stderr.write(self.style.WARNING("  ⚠ no chapters detected (saved unpublished)"))
