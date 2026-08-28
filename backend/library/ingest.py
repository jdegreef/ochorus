"""Shared ingestion helpers: HTML cleaning, word counting, and DB upsert.

Both importers (CCEL, Gutenberg) reduce source HTML to the same safe subset and
write Author / Book / Chapter rows through `upsert_book`.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from django.db import transaction

from library.catalog import AUTHORS, BOOKS, BookEntry
from library.corrections import apply_body_corrections, chapter_title_overrides
from library.models import Author, Book, Chapter

# Re-exported so `from library.ingest import clean_fragment` keeps working —
# it is the documented entry point (backend/CLAUDE.md) and has many callers.
from library.sanitize import (  # noqa: F401
    _PAGE_MARKER,
    _WS,
    ALLOWED_TAGS,
    DROP_SELECTORS,
    clean_fragment,
    clean_html,
)

# The sanitizer and its allowlists now live in library/sanitize.py — the trust
# boundary is security-critical enough to own a module, and models/commands need
# to import it without dragging in this module's model dependencies.


# A redundant "Chapter <n>." prefix (word / digit / roman numeral, any
# separator) — the reader already shows the chapter number, so it reads as
# "1. Chapter One. The Morning Hour". Stripped only when a descriptive title
# follows (a bare "Chapter 3" is left alone — there's nothing else to show).
_CHAPTER_PREFIX = re.compile(r"^\s*chapter\s+\S[^.:—–]*?\s*[.:—–]\s+", re.I)
# The same redundancy without the word "Chapter": a CCEL TOC often numbers its
# own entries ("1. Men of Prayer Needed"), and the reader prepends the order
# itself, so it renders "1. 1. Men of Prayer Needed". Digits only — a
# roman-numeral prefix is handled below, under a caps guard it needs and this
# does not.
_NUMBER_PREFIX = re.compile(r"^\s*\d{1,3}[.)]\s+(?=\S)")
# …except where the numeral is part of a Bible book's NAME. `_ROMAN_PREFIX`
# keeps "II. Timothy" for this reason, and the arabic rule needs the same guard
# or "1. John" / "2. John" / "3. John" all collapse to "John" — three chapters
# with one title. Only the books that come numbered; matched whole, so "1. John
# the Baptist" (a real numbered title) still loses its numeral. Not a word-count
# test — Murray's "11. Patiently" and "25. Quietly" are one-word titles that
# must still be stripped.
_NUMBERED_BOOKS = frozenset(
    {"samuel", "kings", "chronicles", "corinthians", "thessalonians",
     "timothy", "peter", "john", "maccabees", "esdras"}
)
# Quotation marks are noise in a title. Double quotes (incl. straight ") go
# everywhere; a straight single quote only when it's NOT flanked by letters, so
# apostrophes in contractions/possessives (God's, Paul's) are preserved.
_DQUOTE = re.compile(r"[“”„‟«»″‶\"]")
_SQUOTE = re.compile(r"(?<![A-Za-z])'|'(?![A-Za-z])")
# CCEL headings are often ALL-CAPS with a roman-numeral prefix ("II. THE DIGNITY
# OF CHRIST"); the rest of the library is Title Case. A roman-numeral prefix and
# a set of lowercase-in-title connector words for the caps→title-case pass.
_ROMAN_PREFIX = re.compile(r"^[IVXLCDM]+\.\s+")
# A trailing "(Continued)" / "(Concluded)" marker. CCEL sets the heading itself
# in caps but the marker in title case, which defeated the all-caps test below:
# three of Prayer and Praying Men's sixteen headings kept their roman numeral
# and stayed SHOUTING beside title-cased siblings from the same TOC. Judged on
# the heading proper, they are as ALL-CAPS as the rest.
_TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")
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


# A "title" that is nothing but a chapter counter. The reader already prints the
# chapter number, so "Chapter I" tells a reader nothing and renders as
# "1. Chapter I"; Bounds's Purpose in Prayer is thirteen of them, untitled in
# the source. Emptied rather than kept, so the reader can show the number alone.
#
# CHAPTER only — deliberately not "Section"/"Part", which name a unit the reader
# does NOT number and so still carry information ("Section I" in Union and
# Communion, "Part III" in Religious Affections; nine such titles ship today and
# none is a bare "Chapter N").
_BARE_CHAPTER = re.compile(r"^\s*chapter\s+[ivxlcdm\d]+\.?\s*$", re.I)


def _numbering_prefix(t: str) -> re.Match[str] | None:
    """A redundant numbering prefix on `t`, if removing it leaves a title."""
    m = _CHAPTER_PREFIX.match(t)
    # Nothing descriptive after the counter means there is no prefix to strip —
    # the whole title is the counter, and `_BARE_CHAPTER` empties it at the end.
    if m and t[m.end():].strip():
        return m
    m = _NUMBER_PREFIX.match(t)
    if m and (rest := t[m.end():].strip()) and rest.rstrip(".").lower() not in _NUMBERED_BOOKS:
        return m
    return None


def strip_numbering_prefix(t: str) -> str:
    """Drop a redundant "Chapter N." / "N." numbering prefix from `t`.

    To a fixpoint, so it is idempotent: one pass over a doubly-numbered
    "1. 2. Title" would leave "2. Title" and the next call would shorten it
    again.

    Split out of `clean_title` so a backfill can apply this rule alone; see
    migration 0090 for why the full cleaner is wrong for stored titles.
    """
    while (m := _numbering_prefix(t)) is not None:
        t = t[m.end():].strip()
    return t


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
    t = strip_numbering_prefix(t)
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
    core = _TRAILING_PAREN.sub("", t).strip() or t
    is_allcaps = any(c.isalpha() for c in core) and all(c.isupper() for c in core if c.isalpha())
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
    return "" if _BARE_CHAPTER.match(t) else _cap_first(t)


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
    # Content fields refresh on every (re-)import; the workflow-owned fields are
    # CREATE-ONLY (backend/CLAUDE.md) so a re-import can't silently republish a
    # copyright-pulled book, re-type a reviewed one, or reshuffle sort_order.
    fields = {
        "author": author,
        "title": entry.title,
        "subtitle": entry.subtitle,
        "source_url": entry.source_ref if entry.source_ref.startswith("http") else "",
        "cover_color": entry.cover_color,
    }
    book, _ = Book.objects.update_or_create(
        slug=entry.slug,
        language=language,
        defaults=fields,
        create_defaults={
            **fields,
            "source_type": Book.SourceType.PUBLIC_DOMAIN,
            "is_published": True,
            "sort_order": sort_order,
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
        # An empty title stays empty — a chapter can genuinely have no name (see
        # `_BARE_CHAPTER`). `Chapter.title` is `blank=True` and the reader names
        # it; the synthetic "Chapter {order}" this used to store only stood in
        # the way, and produced no title that ever shipped.
        final_title = clean_title(override) if override else title
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
