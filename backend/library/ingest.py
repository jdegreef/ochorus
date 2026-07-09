"""Shared ingestion helpers: HTML cleaning, word counting, and DB upsert.

Both importers (CCEL, Gutenberg) reduce source HTML to the same safe subset and
write Author / Book / Chapter rows through `upsert_book`.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag
from django.db import transaction

from library.catalog import AUTHORS, BOOKS, BookEntry
from library.corrections import apply_body_corrections
from library.models import Author, Book, Chapter

# Tags we keep in chapter bodies; everything else is unwrapped (kept text) or
# decomposed (dropped entirely, below).
ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "blockquote",
    "em", "strong", "i", "b", "br", "hr",
    "ul", "ol", "li", "sup",
}
# Elements removed wholesale (chrome, page furniture, footnote machinery).
DROP_SELECTORS = [
    "script", "style", "nav", "header", "footer", "form", "button",
    "[class*=pagenum]", "[class*=pageno]", "[class*=page-num]",
    "[class*=navbar]", "[class*=toolbar]", "[class*=footnote]",
    "[class*=pg-boilerplate]", "[class*=pginternal]",
    "[id*=navbar]", "[id*=toc]",
]
_PAGE_MARKER = re.compile(r"\[p\s*[ivxlcdm0-9]+\s*\]", re.I)
_WS = re.compile(r"\s+")

# A redundant "Chapter <n>." prefix (word / digit / roman numeral, any
# separator) — the reader already shows the chapter number, so it reads as
# "1. Chapter One. The Morning Hour". Stripped only when a descriptive title
# follows (a bare "Chapter 3" is left alone — there's nothing else to show).
_CHAPTER_PREFIX = re.compile(r"^\s*chapter\s+\S[^.:—–]*?\s*[.:—–]\s+", re.I)
# Quotation marks are noise in a title. Double quotes (incl. straight ") go
# everywhere; a straight single quote only when it's NOT flanked by letters, so
# apostrophes in contractions/possessives (God's, Paul's) are preserved.
_DQUOTE = re.compile(r"[“”„‟«»″‶\"]")
_SQUOTE = re.compile(r"(?<![A-Za-z])'|'(?![A-Za-z])")
# CCEL headings are often ALL-CAPS with a roman-numeral prefix ("II. THE DIGNITY
# OF CHRIST"); the rest of the library is Title Case. A roman-numeral prefix and
# a set of lowercase-in-title connector words for the caps→title-case pass.
_ROMAN_PREFIX = re.compile(r"^[IVXLCDM]+\.\s+")
_TITLE_SMALL = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "into", "nor",
    "of", "on", "or", "the", "to", "up", "with",
}


def _titlecase_caps(s: str) -> str:
    """Title-case an ALL-CAPS heading, keeping connector words lowercase and
    preserving apostrophes ("CHRIST'S" -> "Christ's", not "Christ'S")."""
    words = s.split()
    out: list[str] = []
    for i, w in enumerate(words):
        low = w.lower()
        core = low.strip("\"“”'‘’.,;:?!()[]")
        if 0 < i < len(words) - 1 and core in _TITLE_SMALL:
            out.append(low)
            continue
        for j, ch in enumerate(low):  # capitalise the first alphabetic character
            if ch.isalpha():
                low = low[:j] + ch.upper() + low[j + 1:]
                break
        out.append(low)
    return " ".join(out)


def clean_html(node: Tag) -> str:
    """Reduce a parsed content node to safe, attribute-free HTML."""
    for sel in DROP_SELECTORS:
        for el in node.select(sel):
            el.decompose()
    for tag in node.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
        else:
            tag.attrs = {}
    html = node.decode_contents() if isinstance(node, Tag) else str(node)
    html = _PAGE_MARKER.sub("", html)
    html = _WS.sub(" ", html)
    html = re.sub(r"<(p|h2|h3|h4|blockquote|li)>\s*</\1>", "", html)
    return html.strip()


def clean_fragment(html: str) -> str:
    """Clean a raw HTML fragment string (re-parses it; non-mutating to caller)."""
    wrapper = BeautifulSoup(f"<div>{html}</div>", "lxml").div
    return clean_html(wrapper)


def clean_title(raw: str) -> str:
    """Normalise a chapter heading for display.

    Drops page markers and a trailing 'Contents' link, strips a redundant
    "Chapter N." prefix, removes quotation marks (keeping apostrophes), and
    capitalises the first letter. Idempotent — safe to apply more than once.
    """
    t = _PAGE_MARKER.sub("", raw or "")
    t = _WS.sub(" ", t).strip()
    t = re.sub(r"\s*Contents$", "", t).strip()
    # Drop the "Chapter N." prefix when a descriptive title remains.
    m = _CHAPTER_PREFIX.match(t)
    if m and t[m.end():].strip():
        t = t[m.end():]
    # Remove quotation marks; tidy stray wrapping punctuation and spacing.
    t = _DQUOTE.sub("", t)
    t = _SQUOTE.sub("", t)
    t = re.sub(r"^[\s`~]+|[\s`~]+$", "", t)
    t = _WS.sub(" ", t).strip()
    # A single trailing full stop is typographic noise in a title ("Adoration.",
    # "Love That Passeth Knowledge ."); ellipses are left alone.
    t = re.sub(r"(?<!\.)\s*\.$", "", t)
    # Drop a leading roman-numeral chapter prefix ("VI. Perfect through
    # sufferings" -> "Perfect through sufferings"), but never a person's initials
    # ("D. L. Moody") — require a multi-letter word, not another initial, to follow.
    m = _ROMAN_PREFIX.match(t)
    if m and re.match(r"[A-Za-z]{2,}", t[m.end():]):
        t = t[m.end():]
    # ALL-CAPS CCEL heading -> Title Case. Gated on every letter being uppercase,
    # so mixed-case and already-clean titles are never touched; a bare roman
    # numeral ("IV") is left alone rather than mangled to "Iv".
    letters = [ch for ch in t if ch.isalpha()]
    if letters and all(ch.isupper() for ch in letters) and not re.fullmatch(r"[IVXLCDM]+", t):
        t = _titlecase_caps(t)
    # Capitalise the first alphabetic character ("in Him" -> "In Him").
    for i, ch in enumerate(t):
        if ch.isalpha():
            t = t[:i] + ch.upper() + t[i + 1:]
            break
    return t


def text_of(html: str) -> str:
    return _WS.sub(" ", re.sub(r"<[^>]+>", " ", html)).strip()


def word_count(html: str) -> int:
    return len(text_of(html).split())


def is_front_matter(title: str) -> bool:
    t = title.strip().lower().rstrip(".")
    if t.startswith("index"):  # "Index", "Indexes", "Index of Bible Verses Used"
        return True
    return t in {"contents", "table of contents", "title page", "prefatory note"}


# A bare 1–3 digit number stuck to the very end of a chapter, directly after
# terminal punctuation ("Amen.  4", "evermore!”10") — the next section's number
# or a page number absorbed at the chapter boundary. It appears either inside
# the last paragraph ("…Amen. 4</p>") or as loose text after it ("…Amen.</p>4").
# Requiring the punctuation first means verse references ("Psalm 145:7") and
# years (4 digits) are never touched.
_TRAILING_NUM_IN = re.compile(r"([.!?…”\"'])\s*\d{1,3}\s*(</p>\s*)$")
_TRAILING_NUM_OUT = re.compile(r"([.!?…”\"']\s*</p>)\s*\d{1,3}\s*$")


def strip_trailing_pagenum(body_html: str) -> str:
    """Drop an absorbed page/section number from the end of a chapter body."""
    body_html = body_html.rstrip()
    body_html = _TRAILING_NUM_IN.sub(r"\1\2", body_html)
    return _TRAILING_NUM_OUT.sub(r"\1", body_html)


@transaction.atomic
def upsert_book(entry: BookEntry, sections: list[tuple[str, str]], language: str = "en") -> Book:
    """Create/replace a Book and its chapters from (title, body_html) sections."""
    a = AUTHORS[entry.author_slug]
    author, _ = Author.objects.update_or_create(
        slug=a.slug,
        defaults={
            "name": a.name,
            "bio": a.bio,
            "birth_year": a.birth_year,
            "death_year": a.death_year,
        },
    )
    sort_order = next(i for i, b in enumerate(BOOKS) if b.slug == entry.slug)
    book, _ = Book.objects.update_or_create(
        slug=entry.slug,
        language=language,
        defaults={
            "author": author,
            "title": entry.title,
            "subtitle": entry.subtitle,
            "source_type": Book.SourceType.PUBLIC_DOMAIN,
            "source_url": entry.source_ref if entry.source_ref.startswith("http") else "",
            "cover_color": entry.cover_color,
            "sort_order": sort_order,
            "is_published": True,
        },
    )
    book.chapters.all().delete()
    order = 0
    for title, body in sections:
        if not body or word_count(body) < 5:
            continue
        order += 1
        body = strip_trailing_pagenum(body)
        body = apply_body_corrections(entry.slug, order, body)
        Chapter.objects.create(
            book=book,
            order=order,
            title=(title or f"Chapter {order}")[:300],
            body_html=body,
            word_count=word_count(body),
        )
    return book


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
