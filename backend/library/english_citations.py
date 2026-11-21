"""Do the English editions cite the verses they quote?

`audit_citations` asks this of the public-domain originals, against the ASV,
and is a worklist for a human. This module asks it of EVERY English edition —
the originals, the Modern English editions (`en-modern`), the house-written
Ochorus Originals, the young-reader adaptations and the articles — against
every English Bible we bundle, and it sorts what it finds by who owns the
mistake. That sorting is the point.

Why it exists: translation workers kept finding wrong references in the English
and, correctly, carrying them into every language — "2 Cor 3:14" for a
quotation of 2:14, "Genesis 27:28" for 37:28, "Hebrews 3:18" for 2:18, "Mathew".
A miscitation is the one English defect that survives translation intact (a
careful translator reproduces a printed reference verbatim), so one slip
becomes one per language. Catching it in the English is the only cheap place.

## Who owns a mistake decides what may be done about it

* **pd** — a public-domain original. The author's miscitation IS the text (the
  `english-qa` skill: "do not improve the author"); Murray cites Luke ix. 15
  for Luke 9:18 in the 1898 printing. REPORT ONLY. Settling whether an error is
  the author's or our extractor's needs the printed scan.
* **modern** — an `en-modern` edition. We wrote it; its references are ours.
* **house** — an Ochorus Original, a `-children` / `-teens` adaptation, an
  article. We wrote them too.

Only `modern` and `house` findings can be `fixable`, and only when the evidence
is unambiguous (`Finding.fixable`). Everything else is printed for a human.

## What is checked

1. **miscited** — the quotation barely matches the cited verse(s) and plainly
   matches another reference (a verse or a run of up to four verses).
2. **range** — the quotation starts in the cited verse(s) but runs on past
   them: "(James 1:2)" over the whole of James 1:2-4.
3. **no-such-verse** — the book is real, the verse is not ("Psalm 23:9").
4. **book-spelling** — a reference whose book name is a near-miss of a real
   one ("Mathew 5:3", "Philipians 4:6", "Revelations 3:20"). Scanned over the
   whole text, not only quote+citation pairs.

## Scoring, and why it is conservative

Words are compared as content-token SETS (function words out, a crude stem so
"loveth" meets "loves"), and each verse is scored in every bundled Bible —
the Open Word Bible (modern; nearest to the ESV/BSB wording the modern editions
and house books use) and the ASV (nearest to the KJV the originals quote),
plus the KJV when pythonbible has it installed — keeping the best. An author
quoting the KJV is therefore never punished for not quoting the OWB, and the
reverse.

The cited reference is scored LENIENTLY (containment either way round, and the
best of a single verse or the whole range), a rival STRICTLY (how much of the
quotation it covers). A loose paraphrase scores low against everything and so
stays silent; only a quotation that fits somewhere ELSE far better is reported.
"""

from __future__ import annotations

import contextlib
import html
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pythonbible as bible

from library import bible_store, scripture
from library.content_fixtures import BOOKS_DIR, SERMONS_DIR

ARTICLES_DIR = BOOKS_DIR.parent / "articles"

#: Authors whose books we wrote. Everything they carry is house text.
HOUSE_AUTHORS = frozenset({"ochorus-originals", "james-degreef-and-ochorus"})
#: The bundled Bible itself: its books ARE the verse text, nothing to audit.
SKIP_AUTHORS = frozenset({"open-word-bible"})
#: Young-reader adaptations are house-written (see the project CLAUDE.md).
ADAPTATION_SUFFIXES = ("-children", "-teens")

# ── Thresholds ────────────────────────────────────────────────────────────
#: A quotation needs this many content words to be judged at all.
MIN_TOKENS = 4
#: The cited reference "does not hold the quotation" at or below this.
CITED_MAX = scripture.CITED_MAX
#: A rival must cover this much of the quotation, and beat the cited score by
#: RIVAL_MARGIN. Cross-book is a bigger claim drawn from a bigger pool.
RIVAL_MIN = 0.60
CROSS_BOOK_RIVAL_MIN = 0.70
RIVAL_MARGIN = 0.30
#: Unambiguous: the rival is near-total, the cited near-nothing, and nothing in
#: another passage comes close.
FIX_RIVAL_MIN = 0.80
FIX_CITED_MAX = 0.25
FIX_RUNNER_UP_GAP = 0.20
FIX_MIN_TOKENS = 5
#: Word order: a rival must keep this share of the quotation's adjacent word
#: pairs to be reported at all, and FIX_PHRASE_MIN to be called unambiguous.
RIVAL_PHRASE_MIN = 0.30
FIX_PHRASE_MIN = 0.40
#: A rival may be a run of verses: a quotation of James 1:2-4 is not "James 1:3".
MAX_WINDOW = 4
#: range: the cited verses hold too little of the quotation, and a run of
#: verses CONTAINING them holds this much more of it …
RANGE_COVERAGE_MAX = 0.65
RANGE_EXTENDED_MIN = 0.60
RANGE_GAIN = 0.30
RANGE_PHRASE_GAIN = 0.15
RANGE_MIN_TOKENS = 8
#: … and, to be unambiguous, nearly all of it, in order.
FIX_RANGE_MIN = 0.80
FIX_RANGE_PHRASE_MIN = 0.35

TAG = re.compile(r"<[^>]+>")

# ── Parsing ───────────────────────────────────────────────────────────────
# The book: "2 Cor.", "2Corinthians", "II Kings", "Song of Solomon", "Psa.".
_BOOK = (
    r"(?:(?:[1-3]|I{1,3})\s*|(?:First|Second|Third)\s+)?"
    r"[A-Z][a-z]{1,14}\.?(?:\s+of\s+[A-Z][a-z]+)?"
)
# The chapter, Arabic or a real Roman numeral (see scripture._ROMAN); then the
# verses — ranges ("6:2 -3", "2:28–3:1") and comma lists ("7:13,14").
_CHAPTER = rf"(?:\d{{1,3}}|{scripture._ROMAN})"
_VERSES = (
    r"[:.]\s?\d{1,3}"
    r"(?:\s?[-–—]\s?\d{1,3}(?:\s?[:.]\s?\d{1,3})?)?"
    r"(?:\s?,\s?\d{1,3}(?:\s?[-–—]\s?\d{1,3})?)*"
)
_REF = rf"(?P<ref>(?P<book>{_BOOK})\s?(?P<chapter>{_CHAPTER})(?P<verses>{_VERSES})?)"
# More references after a semicolon: "(Jer. 49:11; 15:11)". Without them the
# quotation is scored against the first reference only — and Bunyan, quoting
# 15:11, read as a miscitation.
_MORE = rf"(?P<more>(?:\s?;\s?(?:{_BOOK}\s?)?{_CHAPTER}{_VERSES})*)"
_VERSION = r"(?:\s+(?:ESV|KJV|NKJV|NIV|NASB|NLT|ASV|RSV|NRSV|BSB|OWB|CSB|HCSB|AV|RV))?"

# A quotation in double curly, straight, or fenced single curly marks (the
# fencing is verse_consistency.PAIR's: ’ is also the apostrophe).
_QUOTE = (
    r"(?:“(?P<q1>[^“”]{12,700}?)”"
    r"|\"(?P<q2>[^\"]{12,700}?)\""
    r"|(?<!\w)‘(?P<q3>[^‘“”]{12,600}?)’(?!\w))"
)
# Quotation, then its reference: in parentheses (a whole-chapter reference only
# there, "(Acts 4)"), or after a dash. Nothing but punctuation between — the
# verse_consistency adjacency rule, which is what keeps a quotation from being
# paired with the next sentence's reference.
PAIR = re.compile(
    _QUOTE
    + r"[\s,.;:!?’'—–-]{0,6}"
    + rf"(?P<open>\(|[—–])\s?{_REF}{_MORE}{_VERSION}(?P<close>\s?\)|(?![\w:]))"
)
# Reference first: "Joel 2:28–29 — “Your sons…”", "Rom. 12:11, “Be ye…”".
# Never a full stop between, which would read "…” (John 3:16). “Next…" backwards.
LEAD = re.compile(rf"(?<![\w(]){_REF}{_MORE}{_VERSION}\s?[—–,:-]\s?" + _QUOTE)
# Any reference-shaped run, for the book-spelling scan.
ANY_REF = re.compile(
    rf"(?<![\w-])(?P<book>{_BOOK})\s(?P<chapter>\d{{1,3}}):(?P<verse>\d{{1,3}})"
)


def _quote_of(m: re.Match) -> str:
    return next(
        g for g in (m.group("q1"), m.group("q2"), m.group("q3")) if g is not None
    )


def _plain(body_html: str) -> str:
    # Tags become spaces: a reference set in the next paragraph,
    # “…”</p><p>(Matthew 23:12), is still this quotation's reference.
    return re.sub(r"[ \t\r\n]+", " ", html.unescape(TAG.sub(" ", body_html or "")))


@dataclass(frozen=True)
class Ref:
    """A parsed reference: what was printed, and the verse ids it names."""

    printed: str
    book: bible.Book
    verse_ids: tuple[int, ...]
    chapter_only: bool


def _normalise_ref(text: str) -> str:
    text = re.sub(r"\s*[-–—]\s*", "-", text)
    return re.sub(r"\s*,\s*", ",", text)


@cache
def _book_of_name(name: str) -> bible.Book | None:
    name = name.strip()
    try:
        refs = bible.get_references(f"{name} 1:1")
    except Exception:
        return None
    return refs[0].book if refs else None


def parse_ref(printed: str) -> Ref | None | bool:
    """The reference, or None when the book is not a book, or False when the
    book is real and the verse is not ("Psalm 23:9")."""
    if ";" in printed:
        head, *rest = (p.strip() for p in printed.split(";"))
        first = parse_ref(head)
        if not first:
            return first
        ids = list(first.verse_ids)
        name = re.fullmatch(_REF, head).group("book")
        for part in rest:
            more = parse_ref(part if not part[:1].isdigit() else f"{name} {part}")
            if more:
                ids.extend(more.verse_ids)
        return Ref(printed, first.book, tuple(dict.fromkeys(ids)), False)
    m = re.fullmatch(_REF, printed.strip())
    if not m:
        return None
    book = _book_of_name(m.group("book"))
    if book is None:
        return None
    # pythonbible wants "Book 3:16": not "John14:27", not "Psalm. 20:7".
    canonical = (
        f"{m.group('book').rstrip('.')} {m.group('chapter')}{m.group('verses') or ''}"
    )
    try:
        refs = bible.get_references(_normalise_ref(canonical))
    except Exception:
        refs = []
    if not refs:
        return False
    ids: list[int] = []
    for r in refs:
        try:
            ids.extend(bible.convert_reference_to_verse_ids(r))
        except Exception:
            return False
    # pythonbible keeps only the first of "7:13,14"; read the rest itself.
    first = refs[0]
    if m.group("verses") and "," in m.group("verses"):
        for part in m.group("verses").split(",")[1:]:
            lo, _, hi = part.strip().partition("-")
            hi = hi or lo
            if lo.isdigit() and hi.isdigit():
                for v in range(int(lo), int(hi) + 1):
                    with contextlib.suppress(Exception):
                        ids.append(bible.get_verse_id(first.book, first.end_chapter, v))
    if not ids:
        return False
    return Ref(printed, book, tuple(dict.fromkeys(ids)), m.group("verses") is None)


# ── Bibles ───────────────────────────────────────────────────────────────
_STOP = scripture._STOP | frozenset(
    [
        "your",
        "yours",
        "you",
        "has",
        "does",
        "its",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "let",
        "said",
        "says",
        "say",
        "saith",
        "one",
        "into",
        "very",
        "how",
        "why",
        "whom",
        "whose",
        "because",
        "about",
        "over",
        "such",
        "been",
        "being",
        "am",
    ]
)
_WORD = re.compile(r"[a-z]+")


#: (suffix, shortest word it is stripped from). Crude, and the same on both
#: sides of every comparison, which is all it needs to be: it lets "loveth",
#: "loves" and "loved" meet, and "trials" meet "trial".
_SUFFIXES = (
    ("eth", 7),
    ("est", 8),
    ("ies", 6),
    ("ing", 7),
    ("ed", 6),
    ("es", 6),
    ("s", 5),
)


def _stem(w: str) -> str:
    for suffix, shortest in _SUFFIXES:
        if w.endswith(suffix) and len(w) >= shortest:
            return w[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return w


def tokens(text: str) -> frozenset[str]:
    return frozenset(
        _stem(w)
        for w in _WORD.findall(text.lower().replace("’", "'"))
        if len(w) > 2 and w not in _STOP
    )


@cache
def bible_texts() -> dict[str, dict[int, str]]:
    """Version label -> verse id -> text, for every bundled English Bible."""
    out: dict[str, dict[int, str]] = {}
    verses, joined = scripture._owb("en")
    owb = dict(verses)
    # A joined verse (1 Kings 18:34 printed under 18:33) answers with the text
    # it is printed in, so citing either id finds the words.
    for vid, first in joined.items():
        if first in owb:
            owb[vid] = owb[first]
    out["OWB"] = owb
    out["ASV"] = dict(bible_store.between(bible_store.ASV, 0, 10**9))
    try:  # Only when the pythonbible KJV package is installed (it usually isn't).
        from pythonbible.versions import Version

        bible.get_verse_text(43003016, version=Version.KING_JAMES)
        out["KJV"] = {
            vid: bible.get_verse_text(vid, version=Version.KING_JAMES) or ""
            for vid in out["ASV"]
        }
    except Exception:
        pass
    return out


@cache
def _version_tokens() -> dict[str, dict[int, frozenset[str]]]:
    """Version label -> verse id -> content tokens."""
    return {
        name: {vid: tokens(t) for vid, t in texts.items()}
        for name, texts in bible_texts().items()
    }


@cache
def verse_tokens() -> dict[int, frozenset[str]]:
    """Verse id -> the content tokens of that verse in ANY bundled Bible.

    A union, not a best-of: a modern edition quoting the ESV shares "count …
    joy" with the ASV and "brothers … trials" with the OWB, and scoring each
    Bible alone halves a correct citation's score (James 1:2-4 read 0.44)."""
    out: dict[int, frozenset[str]] = {}
    for verses in _version_tokens().values():
        for vid, toks in verses.items():
            out[vid] = out.get(vid, frozenset()) | toks
    return out


@cache
def _index() -> dict[str, tuple[int, ...]]:
    """Token -> the verse ids holding it."""
    inv: dict[str, list[int]] = defaultdict(list)
    for vid, toks in verse_tokens().items():
        for t in toks:
            inv[t].append(vid)
    return {t: tuple(v) for t, v in inv.items()}


@cache
def _chapter_ids(book_chapter: int) -> tuple[int, ...]:
    """Every verse id of the chapter whose ids are ``book_chapter * 1000 + v``."""
    have = verse_tokens()
    return tuple(
        i
        for i in range(book_chapter * 1000 + 1, book_chapter * 1000 + 200)
        if i in have
    )


def _union(ids) -> frozenset[str]:
    have = verse_tokens()
    return frozenset().union(*(have.get(i, frozenset()) for i in ids))


def _coverage(q: frozenset[str], ids) -> float:
    """How much of the quotation the union of these verses holds."""
    return len(q & _union(ids)) / len(q)


def _lenient(q: frozenset[str], ids) -> float:
    """The cited reference's score: the best single verse either way round, or
    the whole range's coverage — the most charitable reading there is."""
    best = _coverage(q, ids)
    # One Bible at a time here: a union verse is twice the size of either
    # Bible's, so "the verse is all in the quotation" would never hold.
    for verses in _version_tokens().values():
        for i in ids:
            v = verses.get(i)
            if v and len(v) >= MIN_TOKENS:
                best = max(best, scripture._overlap(v, q))
    return best


def phrase_fit(quote: str, ids) -> float:
    """How much of the quotation's word ORDER the verses keep, best Bible.

    Token sets are order-blind, and a run of four verses can gather five
    scattered words that happen to be in a short quotation — "Eighty and Six
    Years Have I Served Him" against Luke 2:36-37. Adjacent word pairs are what
    a real quotation shares with its verse and a coincidence does not."""
    best = 0.0
    for texts in bible_texts().values():
        joined = " ".join(texts.get(i, "") for i in sorted(ids))
        best = max(best, scripture._phrase_fit(joined, quote))
    return best


def format_ids(ids) -> str:
    ids = sorted(ids)
    first, last = ids[0], ids[-1]
    book = bible.Book(first // 1_000_000)
    c1, v1, c2, v2 = (
        first // 1000 % 1000,
        first % 1000,
        last // 1000 % 1000,
        last % 1000,
    )
    if first == last:
        tail = f"{c1}:{v1}"
    elif c1 == c2:
        tail = f"{c1}:{v1}-{v2}"
    else:
        tail = f"{c1}:{v1}-{c2}:{v2}"
    return f"{book.title} {tail}"


def _windows(q: frozenset[str], seeds) -> list[tuple[float, tuple[int, ...]]]:
    """Score each seed verse, and every run of up to MAX_WINDOW verses through
    it in which each verse adds words the quotation has."""
    out: dict[tuple[int, ...], float] = {}
    for seed in seeds:
        chapter = _chapter_ids(seed // 1000)
        if seed not in chapter:
            continue
        at = chapter.index(seed)
        for lo in range(max(0, at - MAX_WINDOW + 1), at + 1):
            for hi in range(at, min(len(chapter), lo + MAX_WINDOW)):
                win = chapter[lo : hi + 1]
                if win in out:
                    continue
                score = _coverage(q, win)
                # Every verse must earn its place: dropping either end may not
                # leave the score unchanged.
                if len(win) > 1 and (
                    _coverage(q, win[1:]) >= score - 1e-9
                    or _coverage(q, win[:-1]) >= score - 1e-9
                ):
                    continue
                out[win] = score
    return sorted(((s, w) for w, s in out.items()), reverse=True)


def rivals(q: frozenset[str], top: int = 40) -> list[tuple[float, tuple[int, ...]]]:
    """The references (a verse, or a run of verses) that best hold the
    quotation, best first, seeded from the verses sharing most of its words."""
    hits: Counter[int] = Counter()
    inv = _index()
    for t in q:
        for vid in inv.get(t, ()):
            hits[vid] += 1
    return _windows(q, [vid for vid, n in hits.most_common(top) if n >= 2])


def _same_passage(a: tuple[int, ...], b: tuple[int, ...], slack: int = 5) -> bool:
    return (
        a[0] // 1000 == b[0] // 1000 and a[0] - slack <= b[-1] and b[0] - slack <= a[-1]
    )


def _parallel(cited_ids, rival_ids) -> bool:
    """Do the cited verses SAY what the rival says? Deut 6:7 and 11:19, the
    Synoptic doublets, Psalm 14 and 53: a quotation of one fits the other, and
    a citation of either is right. Without this a house book quoting the NIV of
    Deut 6:7 was reported as 11:19, whose wording happened to match better."""
    c, r = _union(cited_ids), _union(rival_ids)
    return bool(c and r) and scripture._overlap(c, r) >= 0.5


# ── Corpus ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Record:
    path: Path
    work: str
    language: str
    where: str  # "slug ch03" / "slug (sermon)" / "slug (article)"
    tier: str  # "pd" | "modern" | "house"
    index: int  # the row's position in the fixture file
    body_html: str = field(repr=False)
    order: int | None = None  # a chapter's order, to find its original


def _tier(path: Path, language: str, author: str | None, work: str) -> str:
    if language == "en-modern":
        return "modern"
    if (
        path.parent.name == "articles"
        or author in HOUSE_AUTHORS
        or work.endswith(ADAPTATION_SUFFIXES)
    ):
        return "house"
    return "pd"


def records(slugs=None) -> Iterator[Record]:
    """Every English and Modern English body in the committed fixture."""
    wanted = set(slugs or ())
    paths = []
    for d in (BOOKS_DIR, SERMONS_DIR, ARTICLES_DIR):
        paths += sorted(d.glob("*.en.json")) + sorted(d.glob("*.en-modern.json"))
    for path in paths:
        work, language = path.name[: -len(".json")].rsplit(".", 1)
        if wanted and work not in wanted:
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        head = next(
            (
                r["fields"]
                for r in rows
                if r["model"] in ("library.book", "library.sermon", "library.article")
            ),
            {},
        )
        author = (head.get("author") or [None])[0]
        if author in SKIP_AUTHORS:
            continue
        tier = _tier(path, language, author, work)
        for i, row in enumerate(rows):
            f = row["fields"]
            if not f.get("body_html"):
                continue
            if row["model"] == "library.chapter":
                where = f"{work} ch{f['order']:02d}"
            else:
                where = f"{work} ({row['model'].split('.')[1]})"
            yield Record(
                path, work, language, where, tier, i, f["body_html"], f.get("order")
            )


# ── Findings ─────────────────────────────────────────────────────────────
@dataclass
class Finding:
    record: Record
    kind: str  # miscited | range | no-such-verse | book-spelling
    printed: str  # the reference exactly as printed
    suggestion: str  # what it reads like (a reference, or a book name)
    quote: str = ""
    cited: float = 0.0
    rival: float = 0.0
    runner_up: float = 0.0
    replacement: str = ""  # the printed reference rewritten, when one is safe
    unambiguous: bool = False
    #: A Modern English edition printing the reference its original prints:
    #: the author's citation, carried over as `contemporize-book` requires.
    carried: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def fixable(self) -> bool:
        return (
            self.unambiguous
            and not self.carried
            and self.record.tier in ("modern", "house")
        )

    def as_dict(self) -> dict:
        return {
            "where": self.record.where,
            "file": str(self.record.path.relative_to(BOOKS_DIR.parent)),
            "tier": self.record.tier,
            "kind": self.kind,
            "printed": self.printed,
            "suggestion": self.suggestion,
            "replacement": self.replacement,
            "quote": self.quote,
            "cited": round(self.cited, 2),
            "rival": round(self.rival, 2),
            "runner_up": round(self.runner_up, 2),
            "unambiguous": self.unambiguous,
            "carried": self.carried,
            "fixable": self.fixable,
        }


def _rewrite(printed: str, target: tuple[int, ...], book: bible.Book) -> str:
    """The printed reference with its numbers (and, across books, its book)
    replaced — keeping the author's book spelling and dash where it can."""
    m = re.fullmatch(_REF, printed.strip())
    new = format_ids(target)
    tail = new.rsplit(" ", 1)[1]
    if m is None:
        return ""  # a list of references ("49:11; 15:11"): a human rewrites it
    if m.group("chapter") and not m.group("chapter").isdigit():
        return ""  # a Roman chapter: leave the house style to a human
    dash = next((d for d in "–—" if d in printed), "-")
    tail = tail.replace("-", dash)
    target_book = bible.Book(target[0] // 1_000_000)
    name = m.group("book") if target_book == book else target_book.title
    sep = (
        ""
        if target_book == book and not printed[len(m.group("book")) :].startswith(" ")
        else " "
    )
    return f"{name}{sep}{tail}"


def check_pair(rec: Record, quote: str, printed: str) -> Finding | None:
    """One quotation and the reference printed with it: a Finding, or None."""
    quote = " ".join(quote.split())
    q = tokens(quote)
    if len(q) < MIN_TOKENS:
        return None
    ref = parse_ref(printed)
    if ref is None:
        return None
    book = (
        ref.book
        if ref
        else _book_of_name(
            re.fullmatch(_REF, printed.split(";")[0].strip()).group("book")
        )
    )
    cited_ids = () if ref is False else ref.verse_ids
    cited = _lenient(q, cited_ids) if cited_ids else 0.0

    # A quotation that runs on past its verse scores low against it, so the
    # range question comes first: James 1:2 over 1:2-4 is short, not wrong.
    if (
        ref
        and not ref.chapter_only
        and len(q) >= RANGE_MIN_TOKENS
        and (f := _short_range(rec, quote, q, printed, ref, cited_ids))
    ):
        return f
    if cited <= CITED_MAX:
        return _miscited(rec, quote, q, printed, ref, book, cited_ids, cited)
    return None


def _miscited(rec, quote, q, printed, ref, book, cited_ids, cited) -> Finding | None:
    """The cited verses hardly hold the quotation: does another reference?"""
    cited_set = set(cited_ids)
    found = [(s, w) for s, w in rivals(q) if not cited_set & set(w)]
    best, win = found[0] if found else (0.0, ())
    same_book = bool(win) and win[0] // 1_000_000 == book.value
    if (
        not win
        or best < (RIVAL_MIN if same_book else CROSS_BOOK_RIVAL_MIN)
        or best - cited < RIVAL_MARGIN
        # Across ~31,000 verses a four-word quotation finds a coincidence.
        or (not same_book and len(q) < FIX_MIN_TOKENS)
        or (cited_ids and _parallel(cited_ids, win))
        or phrase_fit(quote, win) < RIVAL_PHRASE_MIN
    ):
        # No verse anywhere holds it. A real verse: a paraphrase, not ours to
        # judge. A verse that does not exist is still worth a look.
        return (
            Finding(rec, "no-such-verse", printed, "", quote) if ref is False else None
        )
    runner = next((s for s, w in found[1:] if not _same_passage(w, win)), 0.0)
    fit = phrase_fit(quote, win)
    f = Finding(
        rec,
        "no-such-verse" if ref is False else "miscited",
        printed,
        format_ids(win),
        quote,
        cited,
        best,
        runner,
    )
    f.notes.append(f"word order {fit:.2f}")
    f.unambiguous = (
        best >= FIX_RIVAL_MIN
        and cited <= FIX_CITED_MAX
        and best - runner >= FIX_RUNNER_UP_GAP
        and len(q) >= FIX_MIN_TOKENS
        and fit >= FIX_PHRASE_MIN
        # "(Acts 4)" over Acts 1:4 is reported, but a whole-chapter reference
        # may be a deliberate pointer at the passage: a human decides.
        and not (ref and ref.chapter_only)
    )
    if f.unambiguous:
        f.replacement = _rewrite(printed, win, book)
        f.unambiguous = bool(f.replacement)
    return f


def _short_range(rec, quote, q, printed, ref, cited_ids) -> Finding | None:
    """The cited verses hold the start of the quotation; does it run on past
    them into verses the reference leaves out? "(James 1:2)" over 1:2-4."""
    have = _coverage(q, cited_ids)
    if have > RANGE_COVERAGE_MAX:
        return None
    ids = sorted(cited_ids)
    chapter = _chapter_ids(ids[0] // 1000)
    if (
        ids[0] // 1000 != ids[-1] // 1000
        or ids[0] not in chapter
        or ids[-1] not in chapter
    ):
        return None
    lo, hi = chapter.index(ids[0]), chapter.index(ids[-1])
    options = []
    # Up to two verses back, four on; every verse added must add words, so the
    # SHORTEST run that reaches the best score is the one reported.
    for back in range(3):
        for fwd in range(5):
            if back == fwd == 0 or lo - back < 0 or hi + fwd >= len(chapter):
                continue
            win = chapter[lo - back : hi + fwd + 1]
            score = _coverage(q, win)
            if score >= RANGE_EXTENDED_MIN and score - have >= RANGE_GAIN:
                options.append((-round(score, 6), back + fwd, win))
    if not options:
        return None
    neg, _, win = min(options)
    # Shortest run within a whisker of the best: a fourth verse adding one stray
    # word is not part of the quotation.
    win = min((o for o in options if -o[0] >= -neg - 0.05), key=lambda o: o[1])[2]
    # The cited verses must hold words of their own, or the quotation is not
    # running on from them but sitting beside them — a miscitation, not a
    # short range.
    if len(q & _union(cited_ids) - _union(set(win) - set(cited_ids))) < 2:
        return None
    score = _coverage(q, win)
    fit = phrase_fit(quote, win)
    # The added verses must carry the quotation's word ORDER on, not just a
    # few of its words: "All the prophets testify about Him…" is Acts 10:43
    # in the BSB, and 10:42-47 only gathers "testify", "believe" and "name".
    if fit - phrase_fit(quote, cited_ids) < RANGE_PHRASE_GAIN:
        return None
    f = Finding(rec, "range", printed, format_ids(win), quote, have, score)
    f.notes.append(f"word order {fit:.2f}")
    # A comma list or a cross-chapter citation: leave the rewrite to a human.
    f.unambiguous = (
        score >= FIX_RANGE_MIN and fit >= FIX_RANGE_PHRASE_MIN and "," not in printed
    )
    if f.unambiguous:
        f.replacement = _rewrite(printed, win, ref.book)
        f.unambiguous = bool(f.replacement)
    return f


# Book names worth suggesting. pythonbible's own titles, plus the names
# people actually write.
_EXTRA_NAMES = (
    "Psalm",
    "Revelation",
    "Song of Songs",
    "Song of Solomon",
    "Ecclesiastes",
)
# Real words that sit before a chapter:verse and are no book.
_NOT_BOOKS = frozenset(
    [
        "Chapter",
        "Verse",
        "Verses",
        "Page",
        "Section",
        "Hymn",
        "Article",
        "Lesson",
        "Part",
        "Book",
        "Day",
        "Question",
        "Answer",
        "Note",
        "Notes",
        "Matins",
        "Lines",
        "Line",
        "Psalter",
        "Number",
        "Song",
        "Sermon",
        "Letter",
        "Canto",
        "Ode",
        "Act",
        "Scene",
        "Volume",
        "Vol",
        "Mark",
        "Job",
        "Acts",
        "Luke",
        "John",
        "James",
        "Jude",
        "Ruth",
        "Amos",
        "Joel",
    ]
)


@cache
def _book_names() -> tuple[str, ...]:
    names = {b.title for b in bible.Book} | set(_EXTRA_NAMES)
    # "1 Corinthians" -> also "Corinthians", so "1 Corinthans" finds it.
    names |= {n.split(" ", 1)[1] for n in list(names) if n[:1].isdigit()}
    return tuple(sorted(names))


def _distance(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@cache
def misspelled_book(name: str) -> str | None:
    """The real book name a printed one is a near-miss of, if exactly one."""
    bare = re.sub(r"^(?:[1-3]|I{1,3})\s*", "", name.rstrip(".")).strip()
    if bare in _NOT_BOOKS or _book_of_name(name) is not None or len(bare) < 4:
        return None
    # A PREFIX of a real name is an abbreviation, and the old ones are the
    # author's house style, not a slip: "Psal." (Flavel, Edwards), "Matth.".
    # So is a real name that pythonbible only refuses for want of its number.
    # Short of only its final "s" is a slip, though: "Hebrew 9:5".
    if any(
        n.lower().startswith(bare.lower()) and n.lower() != bare.lower() + "s"
        for n in _book_names()
    ):
        return None
    limit = 1 if len(bare) <= 6 else 2
    close = sorted(
        (_distance(bare, n), n)
        for n in _book_names()
        if abs(len(n) - len(bare)) <= limit
    )
    close = [(d, n) for d, n in close if d <= limit]
    if not close or (len(close) > 1 and close[1][0] == close[0][0]):
        return None
    return close[0][1]


@cache
def _original_refs(work: str) -> dict[int, frozenset[tuple[int, ...]]]:
    """Every reference the English original's chapters print, as verse ids.

    Verse ids, not text: the original prints "Acts ix. 5" where the modern
    edition prints "Acts 9:5", and "Matt. 5.11" for "Matt. 5:11"."""
    path = BOOKS_DIR / f"{work}.en.json"
    if not path.exists():
        return {}
    out: dict[int, frozenset[tuple[int, ...]]] = {}
    for r in json.loads(path.read_text(encoding="utf-8")):
        if r["model"] != "library.chapter":
            continue
        text = _plain(r["fields"].get("body_html", ""))
        found = set()
        for m in re.finditer(rf"(?<![\w-]){_REF}{_MORE}", text):
            ref = parse_ref((m.group("ref") + m.group("more")).strip())
            if ref:
                found.add(ref.verse_ids)
        out[r["fields"]["order"]] = frozenset(found)
    return out


def _carried(rec: Record, printed: str) -> bool:
    """Does a Modern English chapter's original print this same reference?

    Then the miscitation is the AUTHOR'S — Bunyan's "(Matt. 5.11)" over a
    quotation running into 5:12 — and the modern edition, which keeps the
    author's Scripture as he quoted it, is right to carry it. Correcting it there
    alone would make the two editions disagree about what Bunyan wrote."""
    if rec.tier != "modern" or rec.order is None:
        return False
    ref = parse_ref(printed)
    return bool(ref) and ref.verse_ids in _original_refs(rec.work).get(
        rec.order, frozenset()
    )


def pairs_in(text: str) -> list[tuple[str, str]]:
    """(quotation, reference as printed) for every pair in plain text.

    Reference-first entries are read first and their spans withheld from PAIR,
    or the same quotation is scored twice — once against its own reference and
    once against the next entry's (see `audit_citations`)."""
    out: list[tuple[str, str]] = []
    claimed: list[tuple[int, int]] = []
    for m in LEAD.finditer(text):
        if m.group("verses") is None:
            continue
        out.append((_quote_of(m), (m.group("ref") + m.group("more")).strip()))
        claimed.append(m.span())
    for m in PAIR.finditer(text):
        if any(m.start() < ce and cs < m.end() for cs, ce in claimed):
            continue
        # A whole-chapter reference only when fully parenthesised: "(Acts 4)".
        if m.group("verses") is None and not (
            m.group("open") == "(" and ")" in m.group("close")
        ):
            continue
        out.append((_quote_of(m), (m.group("ref") + m.group("more")).strip()))
    return out


def audit_record(rec: Record) -> tuple[int, list[Finding]]:
    """(pairs read, findings) for one body."""
    text = _plain(rec.body_html)
    pairs = pairs_in(text)
    out = [f for quote, printed in pairs if (f := check_pair(rec, quote, printed))]
    for f in out:
        f.carried = _carried(rec, f.printed)

    # Book spelling is read over every reference, quoted or not; once per
    # spelling per body is enough to find it.
    seen: set[str] = set()
    for m in ANY_REF.finditer(text):
        name = m.group("book")
        right = misspelled_book(name)
        if not right or name in seen:
            continue
        seen.add(name)
        prefix = re.match(r"^(?:[1-3]|I{1,3})\s*", name)
        fixed = (prefix.group(0) if prefix and not right[:1].isdigit() else "") + right
        # "Judy 18:84" is a near-miss of Jude, which has one chapter: the
        # suggestion must make the printed reference a real verse to be sure.
        sure = bool(parse_ref(f"{fixed} {m.group('chapter')}:{m.group('verse')}"))
        f = Finding(
            rec,
            "book-spelling",
            name,
            fixed,
            replacement=fixed if sure else "",
            unambiguous=sure,
        )
        f.notes.append(f"e.g. “{m.group(0)}”")
        out.append(f)
    return len(pairs), out


def audit(slugs=None) -> tuple[int, list[Finding]]:
    """(pairs read, findings) across the English corpus."""
    findings: list[Finding] = []
    n = 0
    for rec in records(slugs):
        read, found = audit_record(rec)
        n += read
        findings.extend(found)
    return n, findings
