"""In-text Scripture cross-references for the reader.

Two jobs:

* :func:`annotate_references` wraps Bible references appearing in a chapter's
  cleaned HTML in ``<a class="scripture-ref" data-ref="…">`` so the reader can
  make them tappable. A cheap regex finds *candidate* spans (for their position
  in the HTML) and ``pythonbible`` validates each one, so a capitalised word that
  merely looks like a book (``Room 3:16``) is left alone.
* :func:`lookup` resolves a reference to its verse text for the popover, from the
  public-domain **American Standard Version** bundled by ``pythonbible-asv`` —
  no network, so it works offline and needs no external Bible API.

English (ASV) only for now; a target-language edition can layer on later.
"""

from __future__ import annotations

import re
from functools import lru_cache

import pythonbible as bible
from pythonbible.versions import Version

VERSION = Version.AMERICAN_STANDARD
VERSION_LABEL = "American Standard Version"

# A "Book chapter:verse[-verse]" candidate: an optional leading 1/2/3, a
# capitalised word (+ optional trailing period for abbreviations), then the
# chapter:verse. Deliberately loose — pythonbible does the real validation.
_CANDIDATE = re.compile(
    r"\b((?:[1-3]\s+)?[A-Z][A-Za-z]+\.?\s+\d{1,3}\s*[:.]\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)"
)
_TAG_SPLIT = re.compile(r"(<[^>]+>)")
_MAX_VERSES = 25


@lru_cache(maxsize=None)  # ~8k distinct candidates corpus-wide; 4096 thrashed (23% hits)
def _first_reference(text: str):
    """The first valid Bible reference in ``text``, or None."""
    try:
        refs = bible.get_references(text)
    except Exception:
        return None
    return refs[0] if refs else None


def annotate_references(html: str) -> str:
    """Wrap valid Bible references in tappable anchors, in text only.

    Splits on tags so attribute values are never touched, and skips text inside
    an existing ``<a>`` so references already linked aren't double-wrapped.
    """
    if not html or ":" not in html:
        return html
    parts = _TAG_SPLIT.split(html)
    anchor_depth = 0
    for i, part in enumerate(parts):
        if i % 2 == 1:  # a tag
            tag = part[:3].lower()
            if tag.startswith("<a") and not part.lower().startswith("<area"):
                anchor_depth += 1
            elif tag == "</a":
                anchor_depth = max(0, anchor_depth - 1)
            continue
        if anchor_depth or ":" not in part:
            continue
        parts[i] = _wrap_text(part)
    return "".join(parts)


def _wrap_text(text: str) -> str:
    def repl(match: re.Match) -> str:
        candidate = match.group(1)
        if _first_reference(candidate) is None:
            return candidate
        return f'<a class="scripture-ref" data-ref="{candidate}">{candidate}</a>'

    return _CANDIDATE.sub(repl, text)


def cited_references(html: str, limit: int = 8) -> list[str]:
    """Distinct Bible references cited in cleaned HTML, first-appearance order.

    The same candidate regex + pythonbible validation ``annotate_references``
    uses, run over the text between tags. Each hit is rendered in canonical
    form ("Jn 3:16" and "John 3:16" collapse to one chip) and deduped, capped
    at ``limit`` so a citation-dense sermon yields an index, not a wall.
    """
    if not html or ":" not in html:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for i, part in enumerate(_TAG_SPLIT.split(html)):
        if i % 2 == 1 or ":" not in part:
            continue
        for match in _CANDIDATE.finditer(part):
            ref = _first_reference(match.group(1))
            if ref is None:
                continue
            try:
                display = bible.format_scripture_references([ref])
            except Exception:
                display = match.group(1)
            if display in seen:
                continue
            seen.add(display)
            out.append(display)
            if len(out) >= limit:
                return out
    return out


@lru_cache(maxsize=4096)
def reference_verse_ids(text: str) -> frozenset:
    """Every ASV verse id referenced by ``text`` (empty if it isn't a reference).

    Used by search to match a scripture query against a sermon's ``scripture_ref``
    by verse *overlap* — so "John 3:16" finds a sermon on "John 3:14-21", and
    abbreviations ("Jn 3:16") and chapter-only queries ("John 3") resolve too.
    """
    try:
        refs = bible.get_references(text)
    except Exception:
        return frozenset()
    ids: set[int] = set()
    for ref in refs:
        try:
            ids.update(bible.convert_reference_to_verse_ids(ref))
        except Exception:
            continue
    return frozenset(ids)


@lru_cache(maxsize=4096)
def lookup(ref_text: str) -> dict | None:
    """Resolve a reference to ASV verse text for the popover, or None."""
    ref = _first_reference(ref_text)
    if ref is None:
        return None
    verse_ids = bible.convert_reference_to_verse_ids(ref)[:_MAX_VERSES]
    verses = []
    for vid in verse_ids:
        try:
            text = bible.get_verse_text(vid, version=VERSION)
        except Exception:
            continue
        if text:
            verses.append({"number": vid % 1000, "text": text})
    if not verses:
        return None
    return {
        "reference": bible.format_scripture_references([ref]),
        "verses": verses,
        "version": VERSION_LABEL,
    }


@lru_cache(maxsize=512)
def book_of(ref_text: str) -> tuple[str, int] | None:
    """(display name, canonical order) of the Bible book a reference is in.

    Powers the sermons page's book facet: "Malachi 3:6" -> ("Malachi", 39).
    None when the text isn't a parseable English reference (e.g. the localized
    refs on translated sermons — those still match the plain text filter).
    """
    ref = _first_reference(ref_text)
    if ref is None:
        return None
    return (ref.book.title, ref.book.value)


def extract_citations(text: str) -> list[dict]:
    """Every Bible reference cited in plain text, as indexable verse-id spans.

    Returns [{"ref": "John 3:16", "start": 43003016, "end": 43003016,
    "offset": 118, "count": 2}, ...] — one entry per distinct verse span, with
    the character offset of its FIRST occurrence (for snippet centring) and how
    often it recurs. Spans use pythonbible's numeric verse ids (BBBCCCVVV), so
    a (start, end) pair covers a reference even when it crosses a chapter
    boundary; range overlap against a query's ids is exact because ids in the
    numeric gaps between chapters do not correspond to real verses and can
    never be queried.
    """
    found: dict[tuple[int, int], dict] = {}
    for m in _CANDIDATE.finditer(text or ""):
        ref = _first_reference(m.group(1))
        if ref is not None and ref.start_chapter is None:
            # A period after a FULL book name ("Matthew. 1:23") detaches the
            # numbers and pythonbible falls back to the whole book — a span of
            # 28 chapters for a single-verse citation. Retry without the
            # period; if it still parses book-only, skip: citation rows must
            # come from explicit chapter:verse text, never whole books.
            ref = _first_reference(m.group(1).replace(". ", " ", 1))
        if ref is None or ref.start_chapter is None:
            continue
        try:
            ids = bible.convert_reference_to_verse_ids(ref)
        except Exception:
            continue
        if not ids:
            continue
        key = (ids[0], ids[-1])
        entry = found.get(key)
        if entry:
            entry["count"] += 1
        else:
            found[key] = {
                "ref": m.group(1).strip(),
                "start": ids[0],
                "end": ids[-1],
                "offset": m.start(1),
                "count": 1,
            }
    return sorted(found.values(), key=lambda e: e["offset"])


# ── Citation accuracy ──────────────────────────────────────────────────────
# Does the text a book QUOTES actually say what the reference it CITES says?
#
# This is the defect class translators kept finding by hand and no scanner
# caught: `the-way-to-god` alone cites Luke xvii. 10 for Luke 18:10, John xiv. 5
# for 14:6, Exod. xx. 2 for 20:3 and Matt. xxvi. 23 for 26:33. Unlike a spacing
# artifact it survives translation intact — worse, the translation-worker
# convention is to reproduce the printed reference verbatim, so one wrong
# citation becomes six.
#
# Compared against the ASV, which is not the KJV these books quote. So the
# measure is deliberately not "are these the same string".

_WORD = re.compile(r"[a-z]+")

# Function words carry no evidence about WHICH verse this is: every verse has
# them, so counting them drags every score toward the middle and flattens the
# gap the check depends on.
_STOP = frozenset(
    """the and of to in that he for his it with is was be as not but they them
    him her their this these those a an i you ye thou thee thy thine we us our
    my me shall will unto upon into out up down by from at on all any are were
    have hath had do did doth done which who whom what when where then than so
    if or nor yet also there here now O""".lower().split()
)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _STOP)


@lru_cache(maxsize=256)
def _book_verses(book, chapter_hint: int) -> tuple[tuple[int, frozenset[str]], ...]:
    """Every verse of a book as (verse_id, content tokens).

    Keyed with a chapter hint only so callers in different chapters share the
    cache entry; the book is what actually determines the result.
    """
    out = []
    try:
        chapters = bible.get_number_of_chapters(book)
    except Exception:
        return ()
    for ch in range(1, chapters + 1):
        try:
            n = bible.get_number_of_verses(book, ch)
        except Exception:
            continue
        for v in range(1, n + 1):
            vid = bible.get_verse_id(book, ch, v)
            try:
                text = bible.get_verse_text(vid, version=VERSION)
            except Exception:
                continue
            if text:
                out.append((vid, _tokens(text)))
    return tuple(out)


def _overlap(verse: frozenset[str], quote: frozenset[str]) -> float:
    """Containment, whichever way round fits — never symmetric similarity.

    Both asymmetries occur and each breaks one direction:

    * a quotation runs PAST the verse it cites (two verses quoted, the first
      cited), so the quote is the larger set — verse-in-quote holds;
    * a quotation takes only the speech and leaves the narrative frame behind
      ("Though all shall be offended…" against a verse that opens "But Peter
      answered and said unto him"), so the verse is the larger set —
      quote-in-verse holds.

    Symmetric overlap/union halves the score in both, which is what a wrong
    citation looks like. Taking the better direction keeps the two apart.
    """
    if not verse or not quote:
        return 0.0
    hit = len(verse & quote)
    return max(hit / len(verse), hit / len(quote))


# A citation is only reported when the quote barely covers the verse it cites
# AND some other verse in the same book covers far better. The second half is
# what keeps this precise: an author's loose paraphrase also scores low, but it
# does not match a different verse — so it stays silent. Tuned against the
# seven known misprints in `the-way-to-god` and a full-corpus false-positive
# sweep; see tests_english_audit.
CITED_MAX = 0.34
RIVAL_MIN = 0.60
RIVAL_MARGIN = 0.30


def misattributed(quote: str, ref_text: str) -> str | None:
    """The reference this quote actually matches, if the cited one is wrong.

    Returns a formatted reference ("Luke 18:10") when the quoted text plainly
    belongs to a different verse of the same book, else None. Same-book only:
    it is the misprint shape that occurs (a digit or a numeral mis-set), and
    scanning all 66 books per candidate would trade the precision this check
    exists for against recall it does not need.
    """
    # pythonbible reads a range only across an ASCII hyphen: given
    # "Acts 4:31-35" it returns five verses, given the en-dash these books
    # actually typeset it silently returns one. That difference is not cosmetic
    # — it turns every passage citation into a reported misprint, which is most
    # of what the first corpus sweep found in Wesley.
    ref = _first_reference(ref_text.replace("–", "-").replace("—", "-"))
    if ref is None or ref.start_chapter is None:
        return None
    try:
        cited_ids = bible.convert_reference_to_verse_ids(ref)
    except Exception:
        return None
    if not cited_ids:
        return None

    q = _tokens(quote)
    # Too short to judge: "Fear not" carries two content words and appears in
    # scores of verses. Four is low, but the commandments and the confessions
    # are short — "Thou shalt have no other gods before me" is four — and the
    # rival margin below is what actually discriminates, not length.
    if len(q) < 4:
        return None

    # Best-fitting verse WITHIN the citation, not the union of them. A union
    # was the first attempt and it is wrong for a range: "Acts 4:31-35" unions
    # five verses, a quotation of one of them covers a fifth of that, and the
    # check reports a passage citation as a misprint. Wesley alone produced
    # dozens of those. Scoring each verse and keeping the best asks the question
    # that matters — is what they quoted anywhere in what they cited.
    cited_best = 0.0
    seen = False
    for vid in cited_ids:
        try:
            toks = _tokens(bible.get_verse_text(vid, version=VERSION) or "")
        except Exception:
            continue
        if not toks:
            continue
        seen = True
        cited_best = max(cited_best, _overlap(toks, q))
    if not seen or cited_best > CITED_MAX:
        return None

    best_id, best = None, 0.0
    for vid, toks in _book_verses(ref.book, ref.start_chapter):
        if vid in cited_ids:
            continue
        score = _overlap(toks, q)
        if score > best:
            best_id, best = vid, score
    if best_id is None or best < RIVAL_MIN or best - cited_best < RIVAL_MARGIN:
        return None
    return f"{ref.book.title} {best_id // 1000 % 1000}:{best_id % 1000}"
