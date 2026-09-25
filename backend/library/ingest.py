"""Shared ingestion helpers: HTML cleaning, word counting, and DB upsert.

Both importers (CCEL, Gutenberg) reduce source HTML to the same safe subset and
write Author / Book / Chapter rows through `upsert_book`.
"""

from __future__ import annotations

import re
import unicodedata
from html import escape

from bs4 import BeautifulSoup
from django.db import transaction

from library.catalog import AUTHORS, BOOKS, BookEntry
from library.corrections import (
    _EDGE_BREAKS,
    chapter_title_overrides,
    settled_chapter_body,
)
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
    drop_furniture,
)

# Same again for the word-count pair, which moved to library/text.py to sit
# beside the other derivation from body_html.
from library.text import html_to_text, text_of, word_count  # noqa: F401

# The sanitizer and its allowlists now live in library/sanitize.py — the trust
# boundary is security-critical enough to own a module, and models/commands need
# to import it without dragging in this module's model dependencies. `text_of`
# and `word_count` left for a second reason too: Chapter/Sermon.save() derives
# the count now, and reaching THIS module from models.py would pull the catalog
# and every importer into the graph the serializers reach (see tests_fixture).


# A redundant "Chapter <n>." prefix (word / digit / roman numeral, any
# separator) — the reader already shows the chapter number, so it reads as
# "1. Chapter One. The Morning Hour". Stripped only when a descriptive title
# follows (a bare "Chapter 3" is left alone — there's nothing else to show).
# The separator after the counter is either a `.`/`:`/dash FOLLOWED BY SPACE
# ("Chapter One. The Morning Hour"), or — the Schaff/ANF argument form — a
# period/colon ABUTTING an em/en-dash with no space ("Chapter I.—The salutation").
_CHAPTER_PREFIX = re.compile(
    r"^\s*chapter\s+\S[^.:—–]*?\s*(?:[.:]\s*[—–]|[.:—–]\s+)\s*", re.I
)
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
_PLURAL_POSSESSIVE = re.compile(r"[a-z]s' [a-z]", re.I)
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
# The same numeral as a raw pattern, lowercase, for matching text that has been
# through `normalize_words`. WELL-FORMED and below a thousand, because it is
# used with no "chapter" beside it to disambiguate: a loose `[ivxlcdm]+` also
# spells "civil", "mild", "livid", "mill", "dim" and "did", every one of which
# is a heading a book might really carry, and `m{0,3}` would make it match
# "mix" (MIX is 1009). No chapter is numbered past CMXCIX.
_ROMAN_STRICT = r"(?=[ivxlcd])(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"
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


# Only whitespace opens a new word above, so the first word of each em/en-dash-
# joined clause of an ALL-CAPS heading stays lowercased ("Pennsylvania—going",
# "Pray—prayer"). A dash begins a new clause the way a colon subtitle does, so
# capitalise after it too. Em/en-dash only — a hyphen joins one compound word.
_AFTER_DASH = re.compile(r"([—–]\s*)([a-z])")


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
    return _AFTER_DASH.sub(lambda m: m.group(1) + m.group(2).upper(), " ".join(out))


# A CHAPTER TITLE that is nothing but a counter. The reader already prints the
# chapter number, so "Chapter I" tells a reader nothing and renders "1. Chapter
# I"; Bounds's Purpose in Prayer is thirteen of them, untitled in the source.
#
# Applied in `upsert_book`, NOT in `clean_title`, and that distinction is the
# whole point: `clean_title` also cleans headings and intermediate values that
# other code reads the counter OUT of. Emptying there broke two callers —
# `import_ccel`'s grouped path writes each leaf as `<h3>{clean_title(...)}</h3>`
# and all 276 of Confessions' leaves are bare counters, and
# `import_gutenberg._ROMAN_OR_NUM` matches "Chapter IV" to know it must borrow
# the real title from the next node. A title is only "no title" once it is being
# stored AS a title.
#
# CHAPTER only — not "Section"/"Part", which name a unit the reader does NOT
# number and so still carry information ("Section I" in Union and Communion,
# "Part III" in Religious Affections; nine such titles ship today).
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
    # A plural possessive ("Revival at Evans' Mills") is an apostrophe with a
    # space after it, which `_SQUOTE` reads as a closing quote. When it is the
    # title's ONLY single quote there is nothing for it to close, so keep it.
    if t.count("'") == 1 and _PLURAL_POSSESSIVE.search(t):
        t = t.replace("'", "\x00")
    t = _SQUOTE.sub("", t).replace("\x00", "'")
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
    return _cap_first(t)


def chapter_title(raw: str) -> str:
    """`clean_title`, plus: a title that is only a counter is no title at all.

    The split from `clean_title` is deliberate — see `_BARE_CHAPTER`. Every
    importer that STORES a chapter title goes through here; the ones that clean
    a heading or an intermediate value call `clean_title` and keep the counter.
    """
    t = clean_title(raw)
    return "" if _BARE_CHAPTER.match(t) else t


# "Transcriber's Note(s)", "Transcribers' Notes", "Transcriber Note",
# "Note by the Transcriber" — and not "Transcriber's Notebook".
_TRANSCRIBERS_NOTE = re.compile(
    r"^(?:transcribers?['’]?s?['’]? notes?|notes? (?:by|from) the transcriber)\b"
)


def is_front_matter(title: str) -> bool:
    """A section that is apparatus, not the work: front matter, indexes, and the
    back of the book (a publisher's catalogue, a transcriber's notes)."""
    t = title.strip().lower().rstrip(".")
    if t.startswith("index"):  # "Index", "Indexes", "Index of Bible Verses Used"
        return True
    if t.endswith(" index"):  # "Subject Index", "Scripture Index"
        return True
    # "title" = a bare title-page section (CCEL lists one for some works); note
    # "the title" (a real exposition section) is a different string and kept.
    if t in {"list of illustrations", "illustrations"}:  # a plate list, no prose
        return True
    # "Book catalogue" is the heading Project Gutenberg's ebook maker puts over the
    # publisher's trailing back-catalogue of priced titles (e.g. #55743's Revell
    # ad list) — never the work, and its imprint is "WORKS BY <name>", which the
    # "PUBLISHED BY" catalogue-cut in import_gutenberg does not catch.
    if t in {"book catalogue", "book catalog"}:
        return True
    # "Transcriber's Note(s)" is the etext's errata apparatus. Under 300 words it
    # would otherwise be MERGED into the chapter before it as an <h3> — how
    # #51931's notes ended How to Bring Men to Christ.
    if _TRANSCRIBERS_NOTE.match(t):
        return True
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


# --- headings that merely restate the chapter's own title --------------------

# The comparison form of a heading or a title: case-folded, stripped of
# everything that is not a letter, a mark or a digit, and NFC-normalised so two
# spellings of the same accented or Indic character compare equal.
#
# Deliberately NOT `[^a-z0-9]` — that was the rule until this comment, and it
# reduces every Arabic and Devanagari string to the empty string, so under it
# ANY Arabic heading "restates" ANY Arabic title. Measured on the committed
# fixture: 67 rows of `waiting-on-god.ar` / `.hi`, `the-key-in-my-hand.ar` and
# one of `all-of-grace.hi` matched that way, none of them a real restatement
# ("وليمة العهد" against the title "الأولويّات"). Nothing acted on it — the rule only ran inside the CCEL
# importer, which imports English — but this module's `strip_restated_heading`
# is meant to run over the whole corpus, so the rule has to be true in every
# script before it can. `\w` is not enough either: it drops Devanagari vowel
# signs (category Mc/Mn), fusing distinct words.
_KEPT_CATEGORIES = ("L", "M", "N")


def normalize_words(text: str) -> str:
    """Case-folded, punctuation-free words — the form two titles compare in."""
    folded = unicodedata.normalize("NFC", text).lower()
    kept = (c if unicodedata.category(c)[0] in _KEPT_CATEGORIES else " " for c in folded)
    return _WS.sub(" ", "".join(kept)).strip()


# A chapter page's own heading numbers itself, and not always the way its TOC
# entry does: Bounds's TOC reads "1. Men of Prayer Needed" while the page's
# <h2> reads "1 Men of Prayer Needed". Both are the same restatement, and
# `clean_title` drops the TOC's number, so the two only compare equal with the
# numbering set aside on each side.
#
# Roman numerals count too: every chapter of Prayer and Praying Men opens
# "<h2>III. ABRAHAM, THE MAN OF PRAYER</h2>", and thirty-five of `way-into-holiest`
# open "<h2>II. THE DIGNITY OF CHRIST</h2>", above prose the reader already sees
# titled. Strict, for the reason `_ROMAN_STRICT` gives.
# A bare leading counter ("3 ", "iv "), or a "chapter 3 " / "chapter iv "
# word-prefix — the ANF/NPNF argument heads ("Chapter I.—The salutation…").
# Setting the latter aside keeps `restates_title` in step with `clean_title`,
# which now strips that same "Chapter N.—" prefix off the title itself; without
# it the body's restated heading no longer matches the stripped title and leaks
# into the chapter. `_NUMBERED_BOOKS` still guards the strip (below).
_LEAD_COUNTER = re.compile(rf"^(?:chapter\s+)?(?:\d{{1,3}}|{_ROMAN_STRICT})\s+")


def _compared(text: str) -> str:
    """``text`` as `restates_title` weighs it: normalised, numbering set aside.

    `_NUMBERED_BOOKS` guards the strip, exactly as `_numbering_prefix` and
    `_ROMAN_PREFIX` guard `clean_title`'s. Without it "1. John" and "2. John"
    both reduce to "john" and a chapter headed for one epistle restates a
    chapter titled for another — and "II. Timothy" loses the numeral that is
    part of the name. `normalize_words` has already removed the "." that the
    numbering rule up in this module keys on, so its own guard cannot reach
    this.
    """
    words = normalize_words(text)
    without = _LEAD_COUNTER.sub("", words)
    return words if without in _NUMBERED_BOOKS else without


def restates_title(text: str, title: str) -> bool:
    """Does this heading merely repeat the chapter's own title, numbering aside?"""
    if not title:
        return False
    heading = _compared(text)
    # A heading that normalises to nothing — a rule of dashes, a lone bullet —
    # is not a restatement of anything; without this it would equal a title
    # that also normalises to nothing.
    return bool(heading) and heading == _compared(title)


# The two shapes a leading heading takes in a STORED body. `clean_html` keeps
# h2-h4 and unwraps everything else, so a chapter whose source heading was an
# <h1> or <h5> — Whitefield's sermons, Spurgeon's Cheque Book, Till He Come —
# carries it as bare text in front of the first <p> instead.
_LEADING_HEADING = re.compile(r"\s*<(h[1-6])\b[^>]*>(?P<text>.*?)</\1\s*>", re.S | re.I)
_LEADING_LOOSE = re.compile(r"\s*(?P<text>[^<]+)")
# How many leading blocks a scan may take. `import_ccel.extract_body` imports
# this for its own window, so the two cannot drift apart about the same chapter.
MAX_LEADING_BLOCKS = 2


def _strip_leading(body_html: str, accept, limit: int = 1) -> str:
    """Drop leading heading blocks while ``accept(text)`` says so.

    Shared by both strippers below so the two rules that matter — where a
    leading block starts and ends, and that a strip may never empty the chapter
    — have one definition. A one-line chapter whose only line is its own title
    is still worth more than a blank page.
    """
    rest = body_html
    for _ in range(limit):
        match = _LEADING_HEADING.match(rest) or _LEADING_LOOSE.match(rest)
        if match is None or not accept(text_of(match.group("text"))):
            break
        rest = rest[match.end():].lstrip()
    return rest if text_of(rest) else body_html


def strip_restated_heading(body_html: str, title: str) -> str:
    """Drop a leading heading that only repeats ``title``.

    The reader renders the chapter title above the body, so such a heading
    prints the title twice. ``import_ccel.extract_body`` has dropped these
    since the rule was written, which is why a fresh import has none; this is
    the same rule expressed over a body that is already STORED, and it is what
    migration 0092, `scripts/strip_restated_headings.py` and the committed
    fixture all go through, so they cannot disagree about which rows are
    affected. See that migration for the census and the judgement calls.

    Only a LEADING heading, and only one that restates the title in full — a
    mid-chapter heading is never reached, and a heading that says anything of
    its own stops the scan.
    """
    return _strip_leading(
        body_html, lambda text: restates_title(text, title), MAX_LEADING_BLOCKS
    )


def strip_leading_heading_element(body_html: str) -> str:
    """Drop one leading ``<h1>``-``<h6>``, whatever it says.

    THE CALLER MUST HAVE A REASON — this applies no rule of its own. It exists
    for a TRANSLATED chapter, which migration 0092 judges by its English twin
    rather than by its own title, because that is what a translation is: written
    from the English body, keeping its markup block for block
    (`tests_translation_markup` enforces the ordered tag sequence), so the block
    facing a restated English heading is the same restatement.

    An ELEMENT only, never loose text: a translated body that opens with bare
    text is opening with prose, since the `<h1>`-unwrapping that produces the
    loose shape happened in the CCEL importer, which only ever ran in English.
    """
    match = _LEADING_HEADING.match(body_html)
    if match is None:
        return body_html
    rest = body_html[match.end():].lstrip()
    return rest if text_of(rest) else body_html


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
        body = settled_chapter_body(entry.slug, order, body)
        # A per-book override is normalised the same way import_ochorus does, so
        # the same declared correction yields the same stored title on any source.
        override = title_overrides.get(order)
        # A chapter can genuinely have no name: an empty title stays empty, and
        # a title that is only a counter becomes one (see `_BARE_CHAPTER`).
        # `Chapter.title` is `blank=True` and the reader names it; the synthetic
        # "Chapter {order}" this used to store only stood in the way, and
        # produced no title that ever shipped.
        final_title = chapter_title(override) if override else chapter_title(title)
        Chapter.objects.create(
            book=book,
            order=order,
            title=final_title[:300],
            body_html=body,
        )
    return book


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# A `<div>` holding any of these is a wrapper, not a display line: editions wrap
# a chapter's or study's own heading in one, and those must not be read as content.
_DISPLAY_LINE_WRAPS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote",
                       "div", "table", "ul", "ol"]
# A div INSIDE verse is one line of a poem, not a line of its own; the
# importer's poem handling (or the sanitizer's unwrap) owns it. Gutenberg's
# hand-made editions say poem/poetry/stanza, ebookmaker's say lg-container /
# linegroup, the TEI ones tei-lg. A poem set as ONE div, its lines split by
# <br>, is a display line like any other (PG 57109's "LORD JESUS, make
# Thyself to me" in `unfailing-springs`).
_VERSE_CLASS = re.compile(r"poem|poetry|stanza|linegroup|lg-container|tei-lg")
# An illustration and its caption. The image doesn't survive the sanitizer, and
# a caption alone ("A saddled camel") is not the author's text.
_FIGURE_CLASS = re.compile(r"^(?:fig|caption)")
# Opening quotation marks. A line in capitals that opens with one finishes a
# sentence (`"RIBBAND OF BLUE."`); it is not a heading.
QUOTES = ("“", '"', "‘", "'")


def display_line(div, *, verse_lines: bool = False) -> str:
    """A Gutenberg centred display line (`<div class="c1">`) as a body block.

    Gutenberg editions set in-text section headings, displayed verses,
    epigraphs, datelines and signatures as a bare `<div>` — and some set whole
    paragraphs that way (a drop-cap opening, `<div class="cap">`). The
    sanitizer unwraps a div, so without this the line reaches the body as
    loose text between paragraphs — a heading becomes an unmarked run — or,
    where a collector walks only known block tags, vanishes. PG 23438 (*A
    Ribband of Blue*) lost them all; `corrections.py` ("The rest of Gutenberg
    #23438") has the damage.

    A line wholly in capitals is an `<h3>`, text verbatim (the source's own
    small caps and stops) — unless it opens with a quotation mark. Anything else
    is a `<p>`, markup kept. `BODY_CORRECTIONS`' `restored_blocks` insert exactly
    these blocks into rows imported before this existed, so a re-import leaves
    those corrections nothing to do.

    Returns "" for anything that is not a display line, and the caller keeps
    whatever it did before: a wrapper, Gutenberg's own `pg_body_wrapper`
    furniture (page numbers, spacers, PG 57109's "9,000 in print"), anything
    the sanitizer would drop, one line of a poem, a figure or caption, a bare
    chapter counter ("CHAPTER 1" under the chapter's own heading — the reader
    numbers chapters), an empty line.
    Shared by `import_gutenberg` and `import_sermons`.

    `verse_lines=True` keeps a line of a poem as its own `<p>`: the sermon
    collector has no poem handling, so declining it there loses the poem.
    """
    classes = " ".join(div.get("class") or [])
    if (
        "pg_body_wrapper" in classes
        or any(_FIGURE_CLASS.match(c) for c in classes.split())
        or div.find(_DISPLAY_LINE_WRAPS) is not None
        or (not verse_lines and div.find_parent(class_=_VERSE_CLASS) is not None)
    ):
        return ""
    # The block built below carries no class, so the sanitizer would no longer
    # recognise furniture it drops by class (`[class*=pagenum]`, a footnote):
    # ask it about the div itself while the div still has one.
    if not clean_fragment(str(div)).strip():
        return ""
    # Read a copy with the page numbers gone: PG 65066 sets one inside a line
    # ("<span class="pageno">9</span><b>LIFE</b>" reads "9LIFE").
    line = soup(str(div)).find("div")
    drop_furniture(line)
    # A <br> separates words: "THE NEGATIVE<br>CONDITIONS" is two of them.
    text = html_to_text(line.decode_contents())
    if not text or _BARE_CHAPTER.match(text):
        return ""
    if text.isupper() and not text.startswith(QUOTES):
        return f"<h3>{escape(text, quote=False)}</h3>"
    return f"<p>{_EDGE_BREAKS.sub('', line.decode_contents())}</p>"
