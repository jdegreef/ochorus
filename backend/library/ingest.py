"""Shared ingestion helpers: HTML cleaning, word counting, and DB upsert.

Both importers (CCEL, Gutenberg) reduce source HTML to the same safe subset and
write Author / Book / Chapter rows through `upsert_book`.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag
from django.db import transaction

from library.catalog import AUTHORS, BOOKS, BookEntry
from library.corrections import apply_body_corrections, chapter_title_overrides
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
    # CCEL marks a print page break with <span class="pb">17</span>. Left in,
    # the number lands mid-sentence (or alone at the top of a chapter) in a
    # reflowable reader. Exact selector — "pb" is too short to substring-match.
    "span.pb",
    "[class*=navbar i]", "[class*=toolbar i]",
    # CCEL's whole footnote apparatus: the note text (`class="Footnote"`) plus
    # the superscript markers that point at it (`Note`, `NoteRef`, `mnote`).
    # `i` = case-insensitive — a case-sensitive `[class*=footnote]` missed the
    # capitalised classes entirely and inlined note text into the prose
    # ("desires knowledge 2 Aristotle, Metaphysics, i. 1. ; but"), while the
    # markers left bare digits mid-sentence.
    "[class*=note i]",
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
# A whole-token roman numeral ("II", "IV", "CXIX", "XLV") — used to KEEP such a
# word uppercase through the caps→title-case pass so scripture/section headings
# don't mangle ("II CORINTHIANS" -> "II Corinthians", not "Ii Corinthians").
_ROMAN_WORD = re.compile(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", re.I)
_TITLE_EDGE = "\"“”'‘’.,;:?!()[]"
_TITLE_SMALL = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "into", "nor",
    "of", "on", "or", "the", "to", "up", "with",
}


def _cap_first(s: str) -> str:
    """Uppercase the first alphabetic character ("in Him" -> "In Him", "'once'"
    -> "'Once'"), leaving everything else — apostrophes, quotes — untouched.
    A letter that follows a digit is left alone so ordinals stay lowercase
    ("1st" -> "1st", not "1St")."""
    for i, ch in enumerate(s):
        if ch.isalpha():
            if i > 0 and s[i - 1].isdigit():
                return s
            return s[:i] + ch.upper() + s[i + 1:]
    return s


def _titlecase_caps(s: str) -> str:
    """Title-case an ALL-CAPS heading, keeping connector words lowercase and
    preserving apostrophes ("CHRIST'S" -> "Christ's", not "Christ'S") and
    roman-numeral words ("PSALM CXIX" -> "Psalm CXIX")."""
    words = s.split()
    out: list[str] = []
    for i, w in enumerate(words):
        stripped = w.strip(_TITLE_EDGE)
        if len(stripped) >= 2 and _ROMAN_WORD.fullmatch(stripped):
            out.append(w)  # keep roman numerals uppercase
            continue
        low = w.lower()
        core = low.strip(_TITLE_EDGE)
        if 0 < i < len(words) - 1 and core in _TITLE_SMALL:
            out.append(low)
        else:
            out.append(_cap_first(low))
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
    # Drop blocks left empty — including spacer paragraphs whose only content is
    # a <br> (CCEL uses <p><br/></p> for vertical space; in a reflowable reader
    # that renders as a ragged gap).
    html = re.sub(r"<(p|h2|h3|h4|blockquote|li)>(?:\s|<br\s*/?>)*</\1>", "", html)
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
    # Drop a trailing "Contents" nav link, but never blank the whole title — a
    # bare "Contents" must stay so is_front_matter can recognise and drop it.
    t = re.sub(r"\s*Contents$", "", t).strip() or t
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
    # Trailing dash: the same typographic noise as the trailing full stop above
    # (seen once as "Chapter VI—" in CCEL's Confessions TOC). Only a TRAILING
    # dash — an internal one ("Elijah — The Man of God") is the author's
    # punctuation and must stay.
    t = re.sub(r"\s*[—–-]+$", "", t) or t
    is_allcaps = any(c.isalpha() for c in t) and all(c.isupper() for c in t if c.isalpha())
    # Drop a leading roman-numeral chapter prefix ("II. THE DIGNITY OF CHRIST" ->
    # "THE DIGNITY OF CHRIST"), but ONLY on ALL-CAPS CCEL-style headings. A
    # mixed-case numbered title (Murray's "I. Humility: The Glory of the
    # Creature"), a Bible book ("II. Timothy"), and a person's initials
    # ("D. L. Moody") must keep the leading token — so require both all-caps and a
    # multi-letter (non-initial) word after the numeral.
    if is_allcaps:
        m = _ROMAN_PREFIX.match(t)
        # Strip unless what follows is another initial ("L." in "D. L. MOODY") —
        # an article/word like "A" in "IX. A WARNING" should still be stripped.
        if m and not re.match(r"[A-Za-z]\.", t[m.end():]):
            t = t[m.end():]
    # ALL-CAPS heading -> Title Case. A bare roman numeral ("IV") is left alone
    # rather than mangled to "Iv"; roman-numeral words inside are preserved.
    if is_allcaps and not re.fullmatch(r"[IVXLCDM]+", t):
        t = _titlecase_caps(t)
    return _cap_first(t)


def text_of(html: str) -> str:
    return _WS.sub(" ", re.sub(r"<[^>]+>", " ", html)).strip()


def word_count(html: str) -> int:
    return len(text_of(html).split())


def is_front_matter(title: str) -> bool:
    t = title.strip().lower().rstrip(".")
    if t.startswith("index"):  # "Index", "Indexes", "Index of Bible Verses Used"
        return True
    if t.endswith(" index"):  # "Subject Index", "Scripture Index"
        return True
    # "title" = a bare title-page section (CCEL lists one for some works); note
    # "the title" (a real exposition section) is a different string and kept.
    return t in {"contents", "table of contents", "title", "title page", "prefatory note"}


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
    # bio/years are CREATE-ONLY. authors.json is their source of truth (seed_books
    # uses get_or_create for exactly this reason), while catalog entries carry the
    # short stub written when a book was first added. Overwriting on every import
    # meant importing ANY book silently truncated that author's real bio — it hit
    # amy-carmichael, f-b-meyer, susanna-wesley, george-muller and andrew-murray,
    # and each fix was to paste the long bio back into catalog.py, until most
    # catalog bios were hand-synced duplicates of authors.json. create_defaults
    # keeps the stub for a brand-new author and leaves an existing one alone —
    # same idiom as the book upsert in import_ochorus.
    author, _ = Author.objects.update_or_create(
        slug=a.slug,
        defaults={"name": a.name},
        create_defaults={
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
    title_overrides = chapter_title_overrides(entry.slug)
    order = 0
    for title, body in sections:
        if not body or word_count(body) < 5:
            continue
        order += 1
        body = strip_trailing_pagenum(body)
        body = apply_body_corrections(entry.slug, order, body)
        # A per-book override is normalised the same way import_ochorus does, so
        # the same declared correction yields the same stored title on any source.
        override = title_overrides.get(order)
        final_title = clean_title(override) if override else (title or f"Chapter {order}")
        Chapter.objects.create(
            book=book,
            order=order,
            title=final_title[:300],
            body_html=body,
            word_count=word_count(body),
        )
    return book


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
