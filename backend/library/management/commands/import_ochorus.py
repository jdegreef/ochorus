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

from library import english_audit
from library.corrections import (
    EXCLUDED_SLUGS,
    apply_body_corrections,
    chapter_title_overrides,
)
from library.ingest import clean_title, is_front_matter, strip_trailing_pagenum
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
    # "Back Ochorus" starts the site footer — without it in the terminator the
    # capture drags in WordPress boilerplate (cleaned up by migrations 0029/0030
    # for rows imported before this fix).
    description = ""
    m = re.search(
        r"Description:\s*(?:Book Overview)?\s*(.+?)(?:Download|Related|Newsletter|Back Ochorus|$)",
        text,
    )
    if m:
        description = _clean_description(m.group(1).strip())[:1500]

    return {
        "slug": slug,
        "title": title,
        "author": author or "Ochorus",
        "cover_url": cover_url,
        "pdf_url": pdf_url,
        "description": description,
        "source_url": url,
    }


def _clean_description(desc: str) -> str:
    """Tidy a scraped description: the flat text run carries the page's
    "Contents" heading (often empty) at the end — drop a bare heading, keep a
    genuine contents list as "Contents: …" — plus stray-punctuation fixes."""
    bare = re.search(r"\s*Contents\s*$", desc)
    if bare:
        desc = desc[: bare.start()].rstrip()
    elif (idx := desc.rfind(" Contents ")) != -1:
        head, tail = desc[:idx].rstrip(), desc[idx + len(" Contents ") :].strip()
        sep = " Contents: " if _ends_sentence(head) else ". Contents: "
        desc = head + sep + tail
    desc = desc.replace("?.", "?").replace(" .", ".")
    if desc and not _ends_sentence(desc):
        desc += "."
    return desc


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
            # Single-letter blocks (decorative drop caps, often extracted out of
            # reading order) are kept as-is; they're reattached per chapter later.
            blocks.append((t, max(s["size"] for s in spans)))
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


def _norm(t: str) -> str:
    return " ".join(t.lower().split())


_DROPCAP_PUNCT = " \"'“”‘’.-"


def _dropcap_letter(t: str) -> str:
    """If a block is a decorative initial — a single capital, possibly wrapped in
    quotes (e.g. '\"A') — return the letter; else "". These are not headings."""
    core = t.strip(_DROPCAP_PUNCT)
    return core if len(core) == 1 and core.isalpha() and core.isupper() else ""


def _is_dropcap(t: str) -> bool:
    return bool(_dropcap_letter(t))


def _repair_dropcaps(paras: list[str], caps: list[str]) -> list[str]:
    """Reattach decorative initials: a paragraph that begins lowercase has lost
    its drop cap, so prepend the next available one ("hat is…" + "W" → "What is…")."""
    if not caps:
        return paras
    ci = 0
    out: list[str] = []
    for p in paras:
        if ci < len(caps) and p[:1].islower():
            p = caps[ci] + p
            ci += 1
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


def _smart_title(s: str) -> str:
    """Title-case an ALL-CAPS heading; leave already-mixed-case text unchanged.

    Also drops a trailing "Introduction" — a section subhead that some layouts
    set inside the same block as the chapter title ("THE BROKEN FENCE
    Introduction"). Guarded so a chapter actually titled "Introduction" keeps it.
    """
    s = s.strip(" .:-")
    if len(s.split()) > 1:
        s = re.sub(r"\s+introduction\s*$", "", s, flags=re.I)
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        return re.sub(r"(^|\s)([A-Za-z])", lambda m: m.group(1) + m.group(2).upper(), s.lower())
    return s


def _titleish(t: str, s: float, thresh: float) -> bool:
    """A short block that reads as a title — set large, ALL-CAPS, or a bio name."""
    return len(t.split()) <= 14 and (s >= thresh or _is_title_block(t))


# Prose-ending punctuation. "?" and "!" are NOT here: a chapter title may end
# in either ("Is Sickness a Chastisement?"), and the word cap already keeps real
# sentences out.
_PROSE_END = re.compile(r"[.,;:]$")
# A parenthesised chapter-and-verse citation — "(Matt. 9:6)", "(John 15:5)".
# It marks the epigraph, never the title, even when the two share wording.
_VERSE_CITATION = re.compile(r"\(\s*[\w.\s]+\d+\s*:\s*\d+")
# A line that is ONLY a scripture reference ("Mark 5 :25—34", "I Corinthians
# 12:4, 9, 11") — these sit under the title in this layout and are not one.
_BARE_REFERENCE = re.compile(r"^[IVX\d]*\s*[A-Z][A-Za-z]*\.?\s+\d+\s*:", re.A)


def _flat_marker_title(t: str) -> bool:
    """A body-size line that is really the chapter's descriptive title.

    Some PDFs are typographically flat: the "CHAPTER 1" marker AND the title
    below it are both set at body size, with only the running header set larger
    (Murray's *Divine Healing*). ``_titleish`` can't see such a title — it is
    neither larger than body nor ALL-CAPS — so the chapter keeps a bare
    "Chapter 1" and the title text is left to be merged into the first
    paragraph, gluing "Pardon and Healing" onto the epigraph that follows.

    The line has to be told apart from the two other things that follow a
    marker: the scripture epigraph and the opening of the prose. Length does
    most of the work (an epigraph or a real sentence runs long), so the rest is
    deliberately narrow — reject prose-ending punctuation, a verse citation, and
    a line that is nothing but a scripture reference. A title may legitimately
    be quoted ("Ye Are the Branches") or ask a question, so neither is excluded.
    """
    words = t.split()
    return (
        1 <= len(words) <= 12
        and not _PROSE_END.search(t)
        and not _VERSE_CITATION.search(t)
        and not _BARE_REFERENCE.match(t)
        and any(c.isalpha() for c in t)
    )


def _segment(blocks, is_heading, is_noise, thresh) -> list[tuple[str, str]]:
    """Split blocks into chapters at each heading.

    `is_heading(i, t, s)` marks a chapter title; `is_noise(t, s)` marks a running
    header/footer to drop entirely. A "CHAPTER X" marker borrows the following
    title block (set large or ALL-CAPS) as its descriptive title. Drop caps are
    reattached and split paragraphs rejoined per chapter.
    """
    starts = [i for i, (t, s) in enumerate(blocks) if is_heading(i, t, s)]
    if len(starts) < 2:
        return []
    chapters: list[tuple[str, str]] = []
    for j, idx in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(blocks)
        seg = blocks[idx:end]
        head = seg[0][0]
        rest = [(t, s) for t, s in seg[1:] if not is_noise(t, s)]

        title_parts: list[str] = []
        body_paras: list[str] = []
        if _CHAP_RE.match(head):
            m = _CHAP_RE.match(head)
            number, trailing = _normalize_number(m.group(1), m.group(2))
            k = 0
            if trailing and len(trailing.split()) <= 14:
                # "Chapter 1: Charles Spurgeon — The Prince of Preachers" —
                # the whole trailing text IS the descriptive title (mixed-case
                # included; it used to be silently dropped unless ALL-CAPS).
                title_parts.append(trailing.strip(" .:-"))
            elif trailing:
                # Long trailing = the chapter text starts inline on the marker
                # line. Take a leading ALL-CAPS run (if any) as the title and
                # push the rest into the body.
                cap = re.match(r"([A-Z0-9'’,\- ]{3,}?)(?=[a-z]|$)", trailing)
                if cap and cap.group(1).strip(" '-,"):
                    title_parts.append(cap.group(1).strip(" '-,"))
                    leftover = trailing[cap.end():].strip(" .:-")
                    if len(leftover.split()) > 4:
                        body_paras.append(leftover)
            if not title_parts and not body_paras:  # borrow the following title block(s)
                while k < len(rest) and _titleish(rest[k][0], rest[k][1], thresh):
                    title_parts.append(rest[k][0])
                    k += 1
                # Flat PDF: nothing stood out by size or caps, so the single
                # short unpunctuated line after the marker IS the title.
                if not title_parts and k < len(rest) and _flat_marker_title(rest[k][0]):
                    title_parts.append(rest[k][0])
                    k += 1
            title = f"Chapter {number}"
            if title_parts:
                title += ". " + _smart_title(" ".join(title_parts))
            body_paras += [t for t, s in rest[k:]]
        else:
            # Font heading: the heading block(s) are the title.
            title_parts = [head]
            k = 0
            while k < len(rest) and _titleish(rest[k][0], rest[k][1], thresh) and not _CHAP_RE.match(rest[k][0]):
                title_parts.append(rest[k][0])
                k += 1
            title = _smart_title(" ".join(title_parts))
            body_paras = [t for t, s in rest[k:]]

        if is_front_matter(title):  # contents / title page / index
            continue
        caps = [_dropcap_letter(p) for p in body_paras if _is_dropcap(p)]
        body_paras = [p for p in body_paras if not _is_dropcap(p)]
        body_paras = _repair_dropcaps(_merge_paragraphs(body_paras), caps)
        body_html = "".join(f"<p>{html.escape(p)}</p>" for p in body_paras)
        if len(re.sub(r"<[^>]+>", " ", body_html).split()) < 120:  # stub / TOC entry
            continue
        chapters.append((title[:300], body_html))
    return chapters


def _merge_heading_runs(blocks: list[tuple[str, float]], thresh: float) -> list[tuple[str, float]]:
    """Rejoin a title that wraps across blocks ("Chapter 1: Charles Spurgeon —
    The Prince of" + "Preachers Who Prayed"). Adjacent heading-size blocks of the
    same size merge while the first doesn't end a sentence and the result stays
    title-length."""
    out: list[tuple[str, float]] = []
    for t, s in blocks:
        if (
            out
            and s >= thresh
            and out[-1][1] >= thresh
            and round(s) == round(out[-1][1])
            and not _ends_sentence(out[-1][0])
            and len(f"{out[-1][0]} {t}".split()) <= 18
        ):
            out[-1] = (f"{out[-1][0]} {t}", max(out[-1][1], s))
        else:
            out.append((t, s))
    return out


# Standalone section headings that bound a chapter just like a CHAPTER marker
# when set at heading size (Introduction, Conclusion, Scripture Appendix, …).
#
# Sermon/address collections need this too: a book can number its main body with
# CHAPTER markers and then title its closing pieces "SECOND ADDRESS", "Sermon
# III", "Addresses on Holiness…". The marker pass wins whenever it finds >=3
# chapters, so without these the end matter silently merges into the last
# chapter (Catherine Booth's Godliness: 4 addresses fused into one 7.8k-word
# chapter). The ordinal list is closed (not `\w+`) and the pattern is anchored,
# so the size-12 subtitle "AN ADDRESS DELIVERED IN EXETER HALL" sitting under a
# title is NOT a boundary — a `\w+` prefix would swallow it. Numbered sermons
# carry their number as a suffix ("Sermon III"), so no prefix arm is needed there.
_SECTION_RE = re.compile(
    r"^(?:introduction|conclusion|preface|prologue|epilogue|foreword|afterword"
    r"|(?:\w+\s+){0,2}appendix"
    r"|(?:(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+)?"
    r"address(?:es)?\b"
    r"|(?:sermon|lecture|discourse)s?\b)", re.I,
)
# A table-of-contents line: text followed by a dot leader.
# A contents-page line: dot leaders that lead TO A PAGE NUMBER
# ("FLYING HIGH ....... 13"). Requiring the number matters — prose uses runs
# of dots as an ellipsis (".....and blessed is he who is not offended by me"),
# and a bare-dots pattern deleted those paragraphs outright.
_TOC_LINE_RE = re.compile(r"\.{4,}\s*\d+\s*$", re.M)

_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
_WORD_NUMS = {w.lower(): n for n, w in enumerate(
    ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
     "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
     "sixteen", "seventeen", "eighteen", "nineteen", "twenty"])}


def _chapter_int(label: str) -> int | None:
    """Parse a CHAPTER label ("7", "VII", "Seven") to an int; None if we can't."""
    label = label.strip().lower()
    if label.isdigit():
        return int(label)
    if label in _WORD_NUMS:
        return _WORD_NUMS[label]
    if label and all(c in _ROMAN for c in label):
        total = 0
        for a, b in zip(label, label[1:] + " ", strict=True):
            v = _ROMAN[a]
            total += -v if _ROMAN.get(b, 0) > v else v
        return total
    return None


def chapterize(blocks: list[tuple[str, float]], body_size: float) -> list[tuple[str, str]]:
    """Detect chapters.

    Prefer reliable "CHAPTER X" markers; fall back to font-size headings for PDFs
    that title chapters by size alone. A heading-like block that *repeats* across
    the book is a running header/footer (e.g. "Chapter 3" or "Introduction" on
    every page) — those are banned from being headings and dropped from the text,
    so they pollute neither path.
    """
    thresh = body_size * 1.18
    blocks = _merge_heading_runs(blocks, thresh)

    def short(t: str) -> bool:
        return len(t.split()) <= 14 and not _is_dropcap(t)

    freq = Counter(
        _norm(t)
        for t, s in blocks
        if short(t) and (s >= thresh or _CHAP_RE.match(t))
    )
    banned = {k for k, v in freq.items() if v > 2}

    def is_noise(t: str, s: float) -> bool:
        return _norm(t) in banned or bool(_TOC_LINE_RE.search(t))

    # Decide which CHAPTER markers are real chapter starts. When the book sets
    # its markers at heading size, a body-size match is usually an echo — a TOC
    # line or an appendix cross-reference ("Chapter 3 — Rees Howells"). But some
    # books drop a real marker to body size ("Chapter 6" amid size-15 siblings),
    # so a body-size marker that CONTINUES the number sequence is kept, while
    # one that restarts it (appendix "Chapter 1" after "Chapter 10") is not.
    markers_are_large = any(
        s >= thresh and short(t) and _CHAP_RE.match(t) and _norm(t) not in banned
        for t, s in blocks
    )
    marker_idx: set[int] = set()
    prev_num: int | None = None
    for i, (t, s) in enumerate(blocks):
        if not short(t) or _norm(t) in banned or _TOC_LINE_RE.search(t):
            continue
        m = _CHAP_RE.match(t)
        if not m:
            continue
        n = _chapter_int(m.group(1))
        # A body-size "chapter …" whose label isn't a number is prose, not a
        # marker ("The first chapter deals with the doctrines…" split a real
        # sentence in The Key in My Hand). Heading-size markers stay trusted.
        if n is None and s < thresh:
            continue
        if s >= thresh or not markers_are_large or (
            n is not None and prev_num is not None and n == prev_num + 1
        ):
            marker_idx.add(i)
            prev_num = n if n is not None else prev_num

    def is_marker(i: int, t: str, s: float) -> bool:
        if i in marker_idx:
            return True
        # Heading-size section breaks (Introduction / Conclusion / Appendix)
        # bound chapters alongside the numbered markers.
        return (
            s >= thresh
            and short(t)
            and _norm(t) not in banned
            and not _TOC_LINE_RE.search(t)
            and bool(_SECTION_RE.match(t))
        )

    by_marker = _segment(blocks, is_marker, is_noise, thresh)
    if len(by_marker) >= 3:
        return by_marker

    def is_font(i: int, t: str, s: float) -> bool:
        if not short(t) or _norm(t) in banned or _TOC_LINE_RE.search(t):
            return False
        if s >= thresh:
            return True
        # Body-size "chapter …" lines only count when the label is a real
        # number — prose like "chapter deals with…" must not split a chapter.
        m = _CHAP_RE.match(t)
        return bool(m) and _chapter_int(m.group(1)) is not None

    return _segment(blocks, is_font, is_noise, thresh)


@transaction.atomic
def upsert(meta: dict, chapters: list[tuple[str, str]], sort_order: int) -> Book:
    author, _ = Author.objects.get_or_create(
        slug=slugify(meta["author"])[:120] or "ochorus",
        defaults={"name": meta["author"]},
    )
    # Content fields — safe to refresh on every (re-)import.
    fields = {
        "author": author,
        "title": meta["title"],
        "description": meta["description"],
        "source_url": meta["source_url"],
        "cover_url": meta["cover_url"],
        "pdf_url": meta["pdf_url"],
    }
    # Workflow-owned once the book exists, so CREATE-ONLY (backend/CLAUDE.md): a
    # copyright pull sets is_published=False in prod, and review owns source_type
    # — a re-import must not walk either back and silently republish a pulled or
    # re-type a reviewed book. sort_order is likewise assigned once.
    create_only = {
        "source_type": Book.SourceType.PUBLIC_DOMAIN,
        "is_published": bool(chapters),
        "sort_order": sort_order,
    }
    book, _ = Book.objects.update_or_create(
        slug=meta["slug"],
        language="en",
        defaults=fields,
        create_defaults={**fields, **create_only},
    )
    book.chapters.all().delete()
    overrides = chapter_title_overrides(meta["slug"])
    for order, (title, body) in enumerate(chapters, start=1):
        final = clean_title(overrides.get(order, title))
        body = strip_trailing_pagenum(body)
        body = apply_body_corrections(meta["slug"], order, body)
        Chapter.objects.create(
            book=book, order=order, title=final[:300], body_html=body,
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
        if opts["list"]:
            slugs = catalog_slugs()
            for s in slugs:
                self.stdout.write(s)
            self.stdout.write(f"\n{len(slugs)} books.")
            return
        # Explicit slugs are imported directly by their book-page URL, so a book
        # can be (re)imported even when the catalogue listing omits it.
        if opts["slugs"]:
            slugs = list(opts["slugs"])
        else:
            slugs = [s for s in catalog_slugs() if s not in EXCLUDED_SLUGS]
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
        english_audit.report(self, english_audit.audit_book(book), book.slug)
