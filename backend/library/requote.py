"""Re-quote tooling: find every Scripture quotation in a translated work, and
check a splice spec before it touches the fixture.

The Amharic library is being re-quoted to the Open Word Bible. In wave 1 the
hand-written notes files missed 12% of the quotations overall and up to 46% in
one book, so every worker inventoried the English and the Amharic block by
block before re-quoting anything — the bulk of each book's cost — and then
wrote its own throwaway validator. This module does both once.

INVENTORY (``inventory``)
    Five detectors, each a row per quotation, all keyed to the same
    ``(chapter, block_index)`` the notes use:

    * ``cited`` — a quotation with a citation right after it: ``«…» (ዮሐንስ 3:16)``.
      The same adjacency rule as ``verse_consistency.PAIR`` (reused, with the
      language's chapter:verse separators — Amharic also writes ``3፥16``).
    * ``quoted`` — a quotation with no citation that matches a verse in its
      VICINITY (cited within two blocks, or quoted in the aligned English
      block), or, when long enough, a verse found anywhere in the language's
      OWB.
    * ``recited`` — an unquoted verbatim run of a vicinity verse: OWB's words,
      or a wording the language's corpus quotes that verse with elsewhere (the
      only "1962 text" the repo holds, and the one a worker has to replace).
    * ``recurring`` — a refrain too short for any of the above («ፈቃድህ ትሁን»),
      named once in the word list with ``detect`` and found wherever it stands.
    * ``english_only`` — the aligned English block quotes or recites a verse
      and nothing in the Amharic block was matched to it: the translator
      paraphrased it, or recited it in wording no detector knows. A human
      decides; the status guess is ``allusion``.

    Each row carries the OWB text of its reference (a range joined, via
    ``fetch_passage_text``), a status guess — ``already_owb`` (verbatim OWB in
    the containment sense ``mined_verification.is_verbatim`` uses, ±1 verse),
    ``needs_requote`` or ``allusion`` — and the flags of any recurring-word
    decision in ``data/requote/<lang>.json``.

    ``notes_diff`` joins the rows to the notes file by REFERENCE inside a
    chapter, never by ``block_index`` alone (indexes drift — the brief records
    +34), and reports the quotations the notes miss, the rows that point at
    the wrong block, and the rows with no quotation behind them.

VALIDATOR (``validate`` / ``apply``)
    A splice spec is a list of ``{chapter, block, old, new, reference}``.
    Edits are simulated in order against the raw ``body_html``; each must find
    ``old`` exactly once in its block, put only OWB words inside the quote
    marks (``«…»``-joined pieces and ``‹›``-converted inner marks allowed, and
    "…"-joined pieces per the translation-worker skill), and leave the chapter's
    tag sequence, the block's quote-mark balance and a sentence-final mark unchanged.
    ``apply`` writes the result in the file's existing layout.

Block indexes. A book or sermon block is what the admin's side-by-side view
counts (``admin_views.quality._blocks``: one block per closing p / li /
blockquote / h1-6 holding text), per chapter. A bio counts top-level elements
(an ``<aside>`` callout is one block) and then its Q&A answers — the
convention the bio notes files record in their headers.
"""

from __future__ import annotations

import html as htmllib
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import cache, lru_cache
from pathlib import Path

from . import verse_consistency as vc

LIBRARY = Path(__file__).resolve().parent
BACKEND = LIBRARY.parent
CONTENT = LIBRARY / "fixtures" / "content"
NOTES = LIBRARY / "fixtures" / "translation_notes"
BIOS = LIBRARY / "migrations" / "data"
LANGUAGE_DATA = LIBRARY / "data" / "requote"

ALREADY_OWB = "already_owb"
NEEDS_REQUOTE = "needs_requote"
ALLUSION = "allusion"

TITLE = -1  # the block index of a chapter's title, which can quote a verse too

Reader = Callable[[Path], "str | None"]


def read_file(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def git_reader(rev: str) -> Reader:
    """Read the repo as it stood at ``rev`` — how recall is measured against a
    work's state before its wave-1 re-quote."""

    def read(path: Path) -> str | None:
        rel = path.resolve().relative_to(BACKEND.parent)
        out = subprocess.run(
            ["git", "show", f"{rev}:{rel.as_posix()}"], cwd=BACKEND, capture_output=True
        )
        return out.stdout.decode("utf-8") if out.returncode == 0 else None

    return read


# ── Language data ───────────────────────────────────────────────────────────
@cache
def language_data(language: str) -> dict:
    path = LANGUAGE_DATA / f"{language}.json"
    if not path.exists():
        raise ValueError(
            f"No re-quote language data for {language!r}: add {path.relative_to(BACKEND)}."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@cache
def _fold_table(language: str) -> dict[int, int]:
    """Syllable rows that spell one sound, folded for the FUZZY match only."""
    table: dict[int, int] = {}
    for src, dst in language_data(language).get("fold", []):
        for k in range(8):
            table[ord(src) + k] = ord(dst) + k
    return table


_WORD = re.compile(r"\w+")


def _en_word(w: str) -> str:
    """One English word as the comparison sees it: the ASV prints the name the
    KJV books quote as LORD, and British books spell "honour", "Saviour"."""
    if w == "jehovah":
        return "lord"
    if len(w) >= 6 and w.endswith("our"):
        return w[:-3] + "or"
    return w


def en_norm(text: str) -> str:
    return _WORD.sub(lambda m: _en_word(m.group(0).lower()), text)


def words(text: str, language: str) -> list[tuple[str, int, int]]:
    """(folded word, start, end) for every word, combining marks dropped."""
    fold = _fold_table(language) if language != "en" else {}
    out = []
    for m in _WORD.finditer(text):
        w = "".join(
            c
            for c in m.group(0).casefold()
            if not unicodedata.category(c).startswith("M")
        )
        w = _en_word(w) if language == "en" else w.translate(fold)
        out.append((w, m.start(), m.end()))
    return out


@lru_cache(maxsize=65536)
def _grams(text: str, language: str, n: int = 3) -> frozenset[str]:
    """Character n-grams over the folded words — robust to the prefixes and
    suffixes an agglutinative language hangs on a quoted word."""
    s = " ".join(w for w, _, _ in words(text, language))
    return frozenset(s[i : i + n] for i in range(len(s) - n + 1))


@lru_cache(maxsize=65536)
def _word_trigrams(text: str, language: str) -> frozenset[tuple[str, str, str]]:
    cw = [w for w, _, _ in words(text, language)]
    return frozenset(tuple(cw[i : i + 3]) for i in range(len(cw) - 2))


def similarity(quote: str, candidate: str, language: str) -> float:
    """Share of the quote's character trigrams the candidate holds — or of the
    candidate's the quote holds, so a quotation running two verses together
    still recognises each of them."""
    q, c = _grams(quote, language), _grams(candidate, language)
    if not q or not c:
        return 0.0
    shared = len(q & c)
    # The candidate's share counts only for a quotation of comparable length:
    # a long testimony that happens to say "the Holy Spirit" holds all of a
    # short verse's trigrams and is still not a quotation of it.
    fits = len(c) >= 12 and len(q) <= 2.5 * len(c)
    return max(shared / len(q), shared / len(c) if fits else 0.0)


# ── References ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, order=True)
class Span:
    book: int  # 1-based canonical index
    chapter: int
    first: int
    last: int

    @property
    def usfm(self) -> str:
        return _usfm_order()[self.book - 1]

    @property
    def label(self) -> str:
        name = _english_name(self.usfm)
        tail = f"-{self.last}" if self.last > self.first else ""
        return f"{name} {self.chapter}:{self.first}{tail}"

    def ids(self, slack: int = 0) -> range:
        base = self.book * 1_000_000 + self.chapter * 1000
        return range(base + max(1, self.first - slack), base + self.last + slack + 1)

    def overlaps(self, other: Span, slack: int = 1) -> bool:
        return (
            self.book == other.book
            and self.chapter == other.chapter
            and self.first - slack <= other.last
            and other.first - slack <= self.last
        )


def _usfm_order() -> tuple[str, ...]:
    from .translation import USFM_ORDER

    return USFM_ORDER


@cache
def _english_name(usfm: str) -> str:
    from .translation import BOOK_USFM

    special = {"PSA": "Psalm", "SNG": "Song of Solomon"}
    if usfm in special:
        return special[usfm]
    name = next(k for k, v in BOOK_USFM.items() if v == usfm)
    return " ".join(p if p[0].isdigit() else p.capitalize() for p in name.split())


_ABBREV = {
    "ps": "PSA",
    "pss": "PSA",
    "matt": "MAT",
    "mt": "MAT",
    "phil": "PHP",
    "song": "SNG",
    "gen": "GEN",
    "ex": "EXO",
    "exod": "EXO",
    "deut": "DEU",
    "isa": "ISA",
    "jer": "JER",
    "rom": "ROM",
    "heb": "HEB",
    "rev": "REV",
    "eph": "EPH",
    "col": "COL",
    "gal": "GAL",
    "prov": "PRO",
    "eccl": "ECC",
    "ezek": "EZK",
    "dan": "DAN",
    "jas": "JAS",
    "lk": "LUK",
    "jn": "JHN",
    "mk": "MRK",
}
_ENGLISH_REF = re.compile(
    r"^\s*(?P<book>(?:[1-3]\s*)?[A-Za-z][A-Za-z. ]*?)\.?\s+(?P<ch>\d{1,3})\s*[:.]\s*(?P<v1>\d{1,3})[ab]?"
    r"(?:\s*[-–]\s*(?P<v2>\d{1,3})[ab]?)?"
)


def parse_reference(ref: str) -> Span | None:
    """An English (or USFM-coded) notes reference: ``"Psalm 46:1-3"``, ``"PSA 23:1"``."""
    from .translation import BOOK_USFM

    m = _ENGLISH_REF.match(ref or "")
    if not m:
        return None
    raw = re.sub(r"\s+", " ", m.group("book").strip(". ")).lower()
    order = _usfm_order()
    usfm = (
        BOOK_USFM.get(raw)
        or _ABBREV.get(raw)
        or (raw.upper() if raw.upper() in order else None)
    )
    if usfm is None:
        return None
    first = int(m.group("v1"))
    last = max(first, int(m.group("v2") or first))
    return Span(order.index(usfm) + 1, int(m.group("ch")), first, last)


def span_from_id(verse_id: int, last_id: int | None = None) -> Span:
    last_id = last_id or verse_id
    return Span(
        verse_id // 1_000_000, verse_id // 1000 % 1000, verse_id % 1000, last_id % 1000
    )


@lru_cache(maxsize=65536)
def owb_text(span: Span, language: str, slack: int = 0) -> str:
    """The bundled OWB wording of a span (``slack`` verses either side)."""
    from . import scripture

    texts: list[str] = []
    for vid in span.ids(slack):
        found = scripture.owb_verse(vid, language)
        if found and found[1] not in texts:
            texts.append(found[1])
    return " ".join(texts)


@cache
def _citation_regex(language: str) -> re.Pattern:
    data = language_data(language)
    suffix = re.escape(data.get("ordinal_suffix", ""))
    bases = sorted(
        {re.sub(r"^[1-3]\S*\s+", "", k) for k in data["book_names"]},
        key=len,
        reverse=True,
    )
    sep = re.escape(data.get("cv_separators", ":"))
    return re.compile(
        rf"(?:(?P<num>[1-3])\s*{suffix}?\s*)?(?P<book>{'|'.join(map(re.escape, bases))})\.?\s*"
        rf"|(?P<cv>(?P<ch>\d{{1,3}})\s*[{sep}]\s*(?P<v1>\d{{1,3}})(?:\s*[-–]\s*(?P<v2>\d{{1,3}})(?!\s*[{sep}]))?"
        rf"(?P<more>(?:\s*[,፣]\s*\d{{1,3}}(?!\d|\s*[{sep}]))*))"
    )


def local_citations(text: str, language: str) -> list[Span]:
    """Every chapter:verse reference in a citation as the library writes it:
    ``ዮሐንስ 3:36፤ 1ኛ ዮሐንስ 5:12`` gives two spans. A number with no book
    named before it in the same citation is skipped."""
    data = language_data(language)
    names = data["book_names"]
    suffix = data.get("ordinal_suffix", "")
    order = _usfm_order()
    out: list[Span] = []
    book: str | None = None
    for m in _citation_regex(language).finditer(text):
        if m.group("book"):
            key = (
                f"{m.group('num')}{suffix} {m.group('book')}"
                if m.group("num")
                else m.group("book")
            )
            book = names.get(key) or names.get(m.group("book"))
        elif m.group("cv") and book:
            first = int(m.group("v1"))
            last = max(first, int(m.group("v2") or first))
            # "5:16፣ 17፣ 18" — a verse list, read as the span it covers.
            for extra in map(int, re.findall(r"\d+", m.group("more") or "")):
                if extra == last + 1:
                    last = extra
            out.append(Span(order.index(book) + 1, int(m.group("ch")), first, last))
    return out


@cache
def _pair_regex(language: str) -> re.Pattern:
    """``verse_consistency.PAIR`` with the language's chapter:verse separators."""
    sep = language_data(language).get("cv_separators", ":")
    pattern = vc.PAIR.pattern
    if sep != ":":
        pattern = pattern.replace(
            r"(?P<chapter>\d+)\s*:\s*", rf"(?P<chapter>\d+)\s*[{re.escape(sep)}]\s*"
        )
    return re.compile(pattern, vc.PAIR.flags)


_DASH_CITE = re.compile(r"[»”]\s*(?:<[^>]+>\s*)?[—–-]\s*(?P<cite>[^<«»\n]{2,60})")


def cited_quotations(text: str, language: str):
    """(start, end, quotation, spans) for each quotation with its citation.

    Two forms: ``verse_consistency.PAIR``'s «…» (Ref c:v), and the epigraph's
    «…»—Ref c:v, which a book's chapter openings use and PAIR does not read.
    """
    seen: list[int] = []
    for m in _pair_regex(language).finditer(text):
        spans = local_citations(_paren(m.group(0)), language)
        if spans:
            seen.append(m.start())
            yield m.start(), m.end(), vc.clean(vc.quoted(m)), spans
    for m in _QUOTE.finditer(text):
        if m.start() in seen:
            continue
        d = _DASH_CITE.match(text, m.end() - 1)
        if not d:
            continue
        cite = re.split(r"[።.;፤]\s", d.group("cite") + " ")[0]
        spans = local_citations(cite, language)
        if spans and _citation_regex(language).match(cite.strip()):
            yield m.start(), d.end(), vc.clean(m.group(1)), spans


# ── Blocks ──────────────────────────────────────────────────────────────────
_BLOCK_END = re.compile(r"</(?:p|li|blockquote|h[1-6])>", re.I)
_CONTAINER = re.compile(r"<(aside|blockquote)\b.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def render(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(_TAG.sub("", fragment))).strip()


def block_spans(body: str, top_level: bool = False) -> list[tuple[int, int]]:
    """Raw ``(start, end)`` of each block holding text, in document order.

    The same blocks ``admin_views.quality._blocks`` shows a reviewer. With
    ``top_level`` an ``<aside>`` callout or a ``<blockquote>`` (a pull-quote
    and its attribution) is one block: the bio notes count top-level
    elements, then the Q&A answers ("blocks 0-18, then the FAQ from 19").
    """
    cuts = [m.end() for m in _BLOCK_END.finditer(body)] + [len(body)]
    if top_level:
        boxes = [(m.start(), m.end()) for m in _CONTAINER.finditer(body)]
        cuts = [c for c in cuts if not any(a < c < b for a, b in boxes)]
        cuts = sorted(set(cuts) | {b for _, b in boxes})
    spans, start = [], 0
    for end in cuts:
        if render(body[start:end]):
            spans.append((start, end))
        start = end
    return spans


@dataclass
class Block:
    chapter: int | None  # book chapter order; None for a sermon or bio
    index: int  # per chapter for a book, per work otherwise; TITLE for a title
    container: str  # key into Work.containers
    start: int
    end: int
    text: str  # rendered


@dataclass
class Work:
    kind: str
    slug: str
    language: str
    containers: dict[str, str]
    blocks: list[Block]
    paths: dict[str, Path] = field(default_factory=dict)

    def chapter_blocks(self, chapter: int | None) -> list[Block]:
        return [b for b in self.blocks if b.chapter == chapter and b.index != TITLE]

    def block(self, chapter: int | None, index: int) -> Block:
        for b in self.blocks:
            if b.chapter == chapter and b.index == index:
                return b
        raise KeyError(f"no block {index} in chapter {chapter}")

    def raw(self, b: Block) -> str:
        return self.containers[b.container][b.start : b.end]

    @property
    def chapters(self) -> list[int | None]:
        return list(dict.fromkeys(b.chapter for b in self.blocks))


def _blocks_of(
    body: str, container: str, chapter: int | None, first: int = 0, top_level=False
) -> list[Block]:
    return [
        Block(chapter, first + i, container, s, e, render(body[s:e]))
        for i, (s, e) in enumerate(block_spans(body, top_level))
    ]


def load_work(kind: str, slug: str, language: str, read: Reader = read_file) -> Work:
    """A work's blocks in one language, from the shipped files (or from ``read``)."""
    if kind == "bio":
        return _load_bio(slug, language, read)
    sub = {"book": "books", "sermon": "sermons"}[kind]
    path = CONTENT / sub / f"{slug}.{language}.json"
    raw = read(path)
    if raw is None:
        raise FileNotFoundError(path)
    rows = json.loads(raw)
    containers: dict[str, str] = {}
    blocks: list[Block] = []
    for i, row in enumerate(rows):
        f = row["fields"]
        if row["model"] == "library.chapter":
            order = f["order"]
            if f.get("title"):
                containers[f"title:{i}"] = f["title"]
                blocks.append(
                    Block(
                        order,
                        TITLE,
                        f"title:{i}",
                        0,
                        len(f["title"]),
                        render(f["title"]),
                    )
                )
            containers[f"body:{i}"] = f.get("body_html") or ""
            blocks += _blocks_of(containers[f"body:{i}"], f"body:{i}", order)
        elif row["model"] == "library.sermon":
            containers[f"body:{i}"] = f.get("body_html") or ""
            blocks += _blocks_of(containers[f"body:{i}"], f"body:{i}", None)
    return Work(kind, slug, language, containers, blocks, {"fixture": path})


def _load_bio(slug: str, language: str, read: Reader) -> Work:
    containers: dict[str, str] = {}
    paths: dict[str, Path] = {}
    if language == "en":
        rows = json.loads(read(CONTENT / "authors.json") or "[]")
        author = next(
            (r["fields"] for r in rows if r["fields"].get("slug") == slug), None
        )
        if author is None:
            raise FileNotFoundError(f"author {slug}")
        body, faq = author.get("bio_html") or "", author.get("faq") or []
    else:
        root = BIOS / f"author_bios_{language}"
        paths = {"html": root / f"{slug}.html", "faq": root / f"{slug}.faq.json"}
        body = read(paths["html"])
        if body is None:
            raise FileNotFoundError(paths["html"])
        faq = json.loads(read(paths["faq"]) or "[]")
    containers["html"] = body
    blocks = _blocks_of(body, "html", None, top_level=True)
    for k, item in enumerate(faq):
        key = f"faq:{k}"
        containers[key] = str(item.get("a") or "")
        blocks.append(
            Block(
                None, len(blocks), key, 0, len(containers[key]), render(containers[key])
            )
        )
    return Work("bio", slug, language, containers, blocks, paths)


# ── Bible indexes ───────────────────────────────────────────────────────────
#: A shingle in more verses than this is a stock phrase, not evidence.
COMMON = 25


class ShingleIndex:
    """Word n-gram → verse ids, for "which verse is this?" lookups."""

    def __init__(self, verses: dict[int, list[str]], language: str, n: int):
        self.n, self.language = n, language
        posting: dict[tuple, set[int]] = defaultdict(set)
        for vid, texts in verses.items():
            for text in texts:
                ws = [w for w, _, _ in words(text, language)]
                for i in range(len(ws) - n + 1):
                    posting[tuple(ws[i : i + n])].add(vid)
        self.posting = {k: v for k, v in posting.items() if len(v) <= COMMON}

    def hits(self, tokens: list[str]) -> list[tuple[int, set[int]]]:
        """(token position, verse ids) for each shingle of ``tokens`` found."""
        n = self.n
        return [
            (i, found)
            for i in range(len(tokens) - n + 1)
            if (found := self.posting.get(tuple(tokens[i : i + n])))
        ]


@cache
def owb_index(language: str, n: int = 3) -> ShingleIndex:
    from . import bible_store

    rows = bible_store.between(f"owb-{language}", 0, 10**9)
    return ShingleIndex({vid: [text] for vid, text in rows}, language, n)


@cache
def english_index(n: int = 4) -> ShingleIndex:
    """The ASV, which is near enough the KJV the English classics quote."""
    from . import bible_store

    return ShingleIndex(
        {vid: [t] for vid, t in bible_store.between(bible_store.ASV, 0, 10**9)}, "en", n
    )


@cache
def corpus_index(language: str, n: int = 3) -> ShingleIndex:
    return ShingleIndex(dict(corpus_renderings(language)), language, n)


@cache
def corpus_renderings(language: str) -> dict[int, tuple[str, ...]]:
    """Every wording the language's corpus quotes a verse with, cited.

    The repo holds no copy of the old Bible (the 1962 Amharic is © UBS), but
    the works not yet re-quoted cite it thousands of times, so its wording is
    recoverable verse by verse — and it is exactly the wording a recitation
    without quote marks still carries.
    """
    texts: list[str] = []
    for sub in ("books", "sermons"):
        for path in sorted((CONTENT / sub).glob(f"*.{language}.json")):
            for row in json.loads(path.read_text(encoding="utf-8")):
                if body := row["fields"].get("body_html"):
                    texts.append(body)
    root = BIOS / f"author_bios_{language}"
    texts += [p.read_text(encoding="utf-8") for p in sorted(root.glob("*.html"))]
    found: dict[int, set[str]] = defaultdict(set)
    for text in texts:
        for _, _, quote, spans in cited_quotations(text, language):
            if len(quote.split()) < 2:
                continue
            for vid in spans[-1].ids():
                found[vid].add(quote)
    return {k: tuple(sorted(v)) for k, v in found.items()}


def _paren(match_text: str) -> str:
    return match_text[match_text.rfind("(") :]


# ── Inventory ───────────────────────────────────────────────────────────────
@dataclass
class Row:
    chapter: int | None
    block_index: int
    reference: str
    kind: str  # cited | quoted | recited | recurring | english_only
    status: str
    text: str  # the translated quotation (or the whole block, for english_only)
    owb: str
    english_block: int | None = None
    english: str = ""
    flags: list[str] = field(default_factory=list)
    span: Span | None = None

    def as_json(self) -> dict:
        d = asdict(self)
        d.pop("span")
        return d


_QUOTE = re.compile(r"[«“„]([^«»“”]{2,600}?)[»”]", re.S)
_EN_QUOTE = re.compile(
    r"[“\"]([^“”\"]{12,600}?)[”\"]|(?<!\w)‘([^‘’]{12,600}?)’(?!\w)", re.S
)

#: A recitation must run this many words verbatim (the shingle is 3), and a
#: quotation matched against the WHOLE Bible must be this long.
MIN_RECITATION = 4
MIN_GLOBAL_QUOTE = 6
MIN_GLOBAL_CHARS = 12
#: A three-word run counts when it is this long and its verse is cited close by.
MIN_SHORT_RECITATION_CHARS = 12
SHORT_QUOTE = 3
SHORT_QUOTE_MATCH = 0.75
#: Trigram share for a quotation to count as a candidate verse: in the
#: vicinity, and for a verse the English block is known to quote.
NEAR_MATCH = 0.55
ENGLISH_HINT_MATCH = 0.35
#: Share of an English quotation's content words a verse must hold, and the
#: consecutive 4-word shingles an unquoted English recitation must run.
EN_QUOTE_COVER = 0.6
EN_RECITE_NEAR = 2
EN_RECITE = 5


_MIN_PIECE = 3  # normalised characters: an Ethiopic syllable is one, «በእኔ ብትኖሩ» is 7
_MIN_JOINED = 8


_norm = lru_cache(maxsize=65536)(vc.normalise)


@lru_cache(maxsize=65536)
def _norm_cased(text: str) -> str:
    """``vc.normalise`` without the casefold."""
    return "".join(
        c
        for c in text
        if not unicodedata.category(c).startswith("P") and not c.isspace()
    )


def _norm_for(language: str):
    """The comparison key for a language's VERBATIM checks. Case-sensitive
    where OWB's capitals are part of the wording (``case_sensitive`` in the
    language data: Swahili OWB capitalises God's pronouns, Yako against the
    Union's yako). The fuzzy same-verse match stays casefolded."""
    return _norm_cased if language_data(language).get("case_sensitive") else _norm


def _min_piece(language: str) -> int:
    """The shortest joined piece that proves anything (``min_piece``): three
    Ethiopic syllables are a word, three Latin letters are not."""
    return int(language_data(language).get("min_piece", _MIN_PIECE))


def verbatim(quote: str, source: str, language: str) -> bool:
    """``mined_verification.is_verbatim`` with a per-piece floor that suits a
    syllabic script: its 8-character floor rejects the «በእኔ ብትኖሩ … ለምኑ»
    joins the four rules allow. The pieces still have to be in OWB's order
    and together long enough to mean something."""
    norm = _norm_for(language)
    t, s = norm(quote), norm(source)
    if not t or not s:
        return False
    if t in s or s in t:
        return True
    pieces = [norm(p) for p in _ELLIPSIS.split(quote)]
    pieces = [p for p in pieces if p]
    if (
        len(pieces) < 2
        or not s
        or any(len(p) < _min_piece(language) for p in pieces)
        or sum(map(len, pieces)) < _MIN_JOINED
    ):
        return False
    at = 0
    for piece in pieces:
        at = s.find(piece, at)
        if at < 0:
            return False
        at += len(piece)
    return True


#: How far either side of its reference a quotation may reach and still be
#: called OWB: authors run on into the next verse and cite only the first.
STATUS_SLACK = 3
_SENTENCES = re.compile(r"(?<=[።?!፧])\s+")


def is_owb(text: str, span: Span, language: str, slack: int = STATUS_SLACK) -> bool:
    """Is every piece of this quotation verbatim OWB near its reference?

    Pieces are what a quoter may join: "…"-elided parts, and whole sentences
    — Murray sets John 16:26 before 16:23 inside one pair of marks, and each
    sentence is still OWB's own. The validator applies the same test.
    """
    source = owb_text(span, language, slack=slack)
    if not source:
        return False
    if verbatim(text, source, language):
        return True
    norm, floor = _norm_for(language), _min_piece(language)
    pieces = [
        p for part in _SENTENCES.split(text) for p in _ELLIPSIS.split(part) if norm(p)
    ]
    target = norm(source)
    return len(pieces) > 1 and all(
        len(norm(p)) >= floor and norm(p) in target for p in pieces
    )


def _status(text: str, span: Span, language: str) -> str:
    return ALREADY_OWB if is_owb(text, span, language) else NEEDS_REQUOTE


#: The analysed work's own cited wordings, set for the length of one
#: ``inventory`` call: read from the version being analysed (a pre-re-quote
#: revision, say), not from the shipped corpus ``corpus_renderings`` reads.
_own_renderings: dict[int, tuple[str, ...]] = {}


def _candidates_text(vid: int, language: str) -> list[str]:
    from . import scripture

    out = list(
        dict.fromkeys(
            corpus_renderings(language).get(vid, ()) + _own_renderings.get(vid, ())
        )
    )
    found = scripture.owb_verse(vid, language)
    if found:
        out.insert(0, found[1])
    return out


def _best_verse(quote: str, vids, language: str) -> tuple[float, int | None]:
    """The candidate verse a quotation is closest to. A verse the quotation is
    VERBATIM OWB of wins outright: «የአይሁድ ንጉሥ ኢየሱስ» is OWB Matthew 27:37
    and a near miss of John 19:19, and only the first is already done."""
    from . import scripture

    best, at = 0.0, None
    for vid in sorted(vids):
        owb = scripture.owb_verse(vid, language)
        if owb and verbatim(quote, owb[1], language):
            return 2.0, vid
        for cand in _candidates_text(vid, language):
            s = similarity(quote, cand, language)
            if s > best:
                best, at = s, vid
    return best, at


def _english_detect(text: str, nearby: set[int]) -> list[tuple[int, int, str, str]]:
    """(first id, last id, kind, English text) the English block quotes or recites.

    A quotation is a verse when most of its content words are that verse's
    (the ASV stands in for the KJV the books quote, so wording is compared
    loosely); an unquoted run must hold several consecutive 4-word shingles of
    one verse — longer when the verse is not cited nearby, since a stock
    narrative phrase ("loved him as his own soul") recurs by accident.
    """
    from . import scripture

    idx = english_index()
    found: list[tuple[int, int, str, str]] = []
    quoted_spans = []
    for m in _EN_QUOTE.finditer(text):
        q = (m.group(1) or m.group(2)).strip()
        quoted_spans.append((m.start(), m.end()))
        qtok = scripture._tokens(en_norm(q))
        toks = [w for w, _, _ in words(q, "en")]
        if len(qtok) < 2 or len(toks) < 4:
            continue
        candidates = set(nearby)
        shingles: dict[int, int] = defaultdict(int)
        for _, vids in idx.hits(toks):
            candidates |= vids
            for v in vids:
                shingles[v] += 1
        scored = []
        for vid in candidates:
            vt = scripture._tokens(en_norm(scripture._asv_text(vid)))
            if vt:
                # Ties (a short quotation every psalm shares) go to the verse
                # with the most of its exact phrasing, then to the one cited near.
                shared = len(qtok & vt)
                # A quotation running two verses together holds each verse
                # whole: measure against the verse too, when enough is shared.
                cover = max(
                    shared / len(qtok), shared / len(vt) if shared >= 3 else 0.0
                )
                scored.append((cover, shingles[vid], vid in nearby, -len(vt), vid))
        if not scored:
            continue
        cover, *_, top = max(scored)
        if cover >= EN_QUOTE_COVER:
            run = [
                x[-1]
                for x in scored
                if x[0] >= EN_QUOTE_COVER
                and abs(x[-1] - top) <= 2
                and x[-1] // 1000 == top // 1000
            ]
            found.append((min(run), max(run), "quote", q))
    toks = words(text, "en")
    plain = [w for w, _, _ in toks]
    runs: dict[int, list[int]] = defaultdict(list)
    for i, vids in idx.hits(plain):
        if any(a <= toks[i][1] < b for a, b in quoted_spans):
            continue
        for vid in vids:
            runs[vid].append(i)
    for vid, pos in runs.items():
        best = cur = 1
        for a, b in zip(pos, pos[1:], strict=False):
            cur = cur + 1 if b == a + 1 else 1
            best = max(best, cur)
        if best >= (EN_RECITE_NEAR if vid in nearby else EN_RECITE):
            found.append((vid, vid, "recite", ""))
    return found


def _english_citations(text: str) -> set[int]:
    from . import scripture

    ids: set[int] = set()
    for c in scripture.extract_citations(text):
        if c["end"] - c["start"] < 50:
            ids.update(range(c["start"], c["end"] + 1))
    return ids


def _align(a_sets: list[set[int]], e_sets: list[set[int]]) -> list[int | None]:
    """Map each translated block to an English block of the same chapter.

    Identity when the counts agree (the usual case). Otherwise anchor on
    blocks that share a verse, monotone, and interpolate between anchors.
    """
    na, ne = len(a_sets), len(e_sets)
    if ne == 0:
        return [None] * na
    if na == ne:
        return list(range(na))
    anchors = [(-1, -1)]
    for i, verses in enumerate(a_sets):
        if not verses:
            continue
        guess = round(i * ne / max(1, na))
        last_j = anchors[-1][1]
        options = [
            j
            for j in range(max(last_j + 1, guess - 8), min(ne, guess + 9))
            if verses & e_sets[j]
        ]
        if options:
            anchors.append((i, min(options, key=lambda j: abs(j - guess))))
    anchors.append((na, ne))
    out: list[int | None] = []
    k = 0
    for i in range(na):
        while anchors[k + 1][0] < i:
            k += 1
        (i0, j0), (i1, j1) = anchors[k], anchors[k + 1]
        if i == i1:
            out.append(j1)
            continue
        j = j0 + (i - i0) * (j1 - j0) / max(1, i1 - i0)
        out.append(min(ne - 1, max(0, round(j))))
    return out


def _recurring_rows(
    b: Block, chapter, j, e_text: str, rows: list[Row], language: str
) -> list[Row]:
    """Rows for a ``detect`` decision's old wording wherever it stands.

    A two-word refrain («ፈቃድህ ትሁን», "Thy will be done") is too short for
    any detector to call Scripture on its own, and wave 1 found it again and
    again by hand. The word list names it once; this finds every one.
    """
    out = []
    for d in language_data(language).get("decisions", []):
        if not d.get("detect"):
            continue
        span = parse_reference(d["references"][0])
        for old in d.get("old", []):
            if old not in b.text:
                continue
            if any(
                r.chapter == chapter and r.block_index == b.index and old in r.text
                for r in rows
            ):
                continue
            out.append(
                Row(
                    chapter,
                    b.index,
                    span.label,
                    "recurring",
                    NEEDS_REQUOTE,
                    old,
                    owb_text(span, language),
                    j,
                    e_text,
                    [d["id"]],
                    span,
                )
            )
    return out


def _decision_flags(
    row: Row, english_text: str, block_text: str, language: str
) -> list[str]:
    flags = []
    for d in language_data(language).get("decisions", []):
        refs = [s for r in d.get("references", []) if (s := parse_reference(r))]
        if (
            row.span
            and any(row.span.overlaps(s, slack=0) for s in refs)
            or any(
                re.search(rf"\b{re.escape(k)}\b", english_text, re.I)
                for k in d.get("english", [])
            )
            or any(o in block_text for o in d.get("old", []))
        ):
            flags.append(d["id"])
    return flags


def inventory(work: Work, english: Work | None) -> list[Row]:
    """Every Scripture quotation in ``work``, aligned to ``english``."""
    language = work.language
    own: dict[int, set[str]] = defaultdict(set)
    for b in work.blocks:
        for _, _, quote, spans in cited_quotations(b.text, language):
            for vid in spans[-1].ids():
                own[vid].add(quote)
    _own_renderings.clear()
    _own_renderings.update({k: tuple(sorted(v)) for k, v in own.items()})
    try:
        rows: list[Row] = []
        for chapter in work.chapters:
            rows += _inventory_chapter(work, english, chapter, language)
        return rows
    finally:
        _own_renderings.clear()


def _block_detect(
    text: str,
    language: str,
    near: set[int],
    hinted: set[int],
    chapter: set[int] = frozenset(),
) -> list[tuple]:
    """(first id, last id, kind, matched text) found in one translated block.

    ``near``: verses cited within two blocks; ``hinted``: verses the aligned
    English quotes; ``chapter``: every verse the chapter cites (an epigraph's
    verse is recited twenty paragraphs later)."""
    out: list[tuple] = []
    taken: list[tuple[int, int]] = []
    for start, end, quote, spans in cited_quotations(text, language):
        # A citation list: the reference whose words the quotation carries.
        span = max(
            spans,
            key=lambda s: max(
                (
                    similarity(quote, t, language)
                    for v in s.ids()
                    for t in _candidates_text(v, language)
                ),
                default=0,
            ),
        )
        out.append((min(span.ids()), max(span.ids()), "cited", quote))
        taken.append((start, end))
    for m in _QUOTE.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        quote = vc.clean(m.group(1))
        n = len(quote.split())
        if n < 2:
            continue
        score, vid = _best_verse(quote, near | hinted, language)
        hint_score, hint_vid = _best_verse(quote, hinted, language)
        gvid = _global_verbatim(quote, language) if score < 2 else None
        if n <= SHORT_QUOTE and score < 2:
            # A two- or three-word quotation is usually a term the author
            # sets off; it is Scripture only when it is nearly the verse's own.
            score = score if score >= SHORT_QUOTE_MATCH else 0.0
            hint_score = hint_score if hint_score >= SHORT_QUOTE_MATCH else 0.0
        if score >= 2 and vid:
            out.append((vid, vid, "quoted", quote))
        elif gvid:
            out.append((gvid, gvid, "quoted", quote))
        elif score >= NEAR_MATCH and vid:
            out.append((vid, vid, "quoted", quote))
        elif hint_score >= ENGLISH_HINT_MATCH and hint_vid:
            out.append((hint_vid, hint_vid, "quoted", quote))
        elif (far := _best_verse(quote, chapter - near, language))[0] >= (
            SHORT_QUOTE_MATCH if n <= SHORT_QUOTE else NEAR_MATCH
        ) and far[1]:
            out.append((far[1], far[1], "quoted", quote))
        elif n >= MIN_GLOBAL_QUOTE - 2:
            gvid = _global_owb(quote, language)
            if gvid:
                out.append((gvid, gvid, "quoted", quote))
        taken.append((m.start(), m.end()))
    # Unquoted recitations of a vicinity verse.
    toks = words(text, language)
    free = [(w, s, e) for w, s, e in toks if not any(a <= s < b for a, b in taken)]
    found: list[tuple[int, int, int, int]] = []  # (-length, preference, vid, start)
    free_words = [w for w, _, _ in free]
    free_grams = [tuple(free_words[i : i + 3]) for i in range(len(free_words) - 2)]
    for vid in sorted(near | hinted | chapter):
        close = vid in near or vid in hinted
        for rank, cand in enumerate(_candidates_text(vid, language)):
            grams = _word_trigrams(cand, language)
            if grams.isdisjoint(free_grams):
                continue
            i = 0
            while i < len(free) - 2:
                if free_grams[i] not in grams:
                    i += 1
                    continue
                j = i + 3
                while j < len(free) and free_grams[j - 2] in grams:
                    j += 1
                # Three words count only in OWB's own wording, close to a
                # citation: a book's recurring term («በመንፈስ ቅዱስ መጠመቅ») is
                # three words of some old rendering everywhere it appears.
                long_enough = j - i >= MIN_RECITATION or (
                    close
                    and rank == 0
                    and len(vc.normalise(" ".join(w for w, _, _ in free[i:j])))
                    >= MIN_SHORT_RECITATION_CHARS
                )
                if long_enough:
                    # Prefer OWB's own text (rank 0) and a verse cited close by.
                    found.append((-(j - i), (rank > 0) * 2 + (not close), vid, i))
                i = j
    # One row per stretch of text: a run that matches a range rendering
    # matches every verse of the range, and only one of them is the verse.
    claimed: list[tuple[int, int]] = []
    for neg, _, vid, i in sorted(found):
        j = i - neg
        if any(a < j and i < b for a, b in claimed):
            continue
        claimed.append((i, j))
        s, e = free[i][1], free[j - 1][2]
        out.append((vid, vid, "recited", text[s:e]))
    return out


def _global_verbatim(quote: str, language: str) -> int | None:
    """A verse anywhere in OWB the quotation is verbatim of, when it is long
    enough for that to mean something (Murray's «ሁሉን ለእግዚአብሔር ክብር
    አድርጉ» is 1 Cor 10:31, cited nowhere near it)."""
    from . import scripture

    if len(vc.normalise(quote)) < MIN_GLOBAL_CHARS:
        return None
    idx = owb_index(language)
    toks = [w for w, _, _ in words(quote, language)]
    votes: dict[int, int] = defaultdict(int)
    for _, vids in idx.hits(toks):
        for v in vids:
            votes[v] += 1
    for vid, _ in sorted(votes.items(), key=lambda kv: -kv[1])[:10]:
        found = scripture.owb_verse(vid, language)
        if found and verbatim(quote, found[1], language):
            return vid
    return None


def _global_owb(quote: str, language: str) -> int | None:
    """The verse anywhere a long uncited quotation renders — by OWB's words,
    or by a wording the corpus cites the verse with (the old Bible's)."""
    toks = [w for w, _, _ in words(quote, language)]
    votes: dict[int, int] = defaultdict(int)
    for idx in (owb_index(language), corpus_index(language)):
        for _, vids in idx.hits(toks):
            for v in vids:
                votes[v] += 1
    best, at = 0.0, None
    for vid, count in sorted(votes.items(), key=lambda kv: -kv[1])[:8]:
        if count < 2:
            break
        score = max(
            (similarity(quote, t, language) for t in _candidates_text(vid, language)),
            default=0.0,
        )
        if score > best:
            best, at = score, vid
    return at if best >= NEAR_MATCH else None


def _inventory_chapter(
    work: Work, english: Work | None, chapter, language
) -> list[Row]:
    blocks = work.chapter_blocks(chapter)
    titles = [b for b in work.blocks if b.chapter == chapter and b.index == TITLE]
    e_blocks = english.chapter_blocks(chapter) if english else []
    cites = [
        {v for s in local_citations(b.text, language) for v in s.ids()} for b in blocks
    ]
    e_cites = [_english_citations(b.text) for b in e_blocks]
    e_found = []
    for j, b in enumerate(e_blocks):
        near = set().union(*e_cites[max(0, j - 1) : j + 2]) if e_cites else set()
        e_found.append(_english_detect(b.text, near))
    e_sets = [
        c | {v for f, last, _, _ in found for v in range(f, last + 1)}
        for c, found in zip(e_cites, e_found, strict=True)
    ]
    align = _align(cites, e_sets)

    rows: list[Row] = []
    for i, b in enumerate(blocks + titles):
        is_title = b.index == TITLE
        j = None if is_title else align[i]
        near: set[int] = set()
        if not is_title:
            for k in range(max(0, i - 2), min(len(blocks), i + 3)):
                near |= cites[k]
        else:
            near = set().union(*cites[:3]) if cites else set()
        near = {v + d for v in near for d in (-1, 0, 1)}
        whole = {v + d for c in cites for v in c for d in (-1, 0, 1)}
        hinted: set[int] = set()
        if j is not None:
            for k in range(max(0, j - 1), min(len(e_blocks), j + 2)):
                hinted |= {
                    v for f, last, _, _ in e_found[k] for v in range(f, last + 1)
                }
        e_text = e_blocks[j].text if j is not None and j < len(e_blocks) else ""
        for first, last, kind, text in _block_detect(
            b.text, language, near, hinted, whole
        ):
            span = span_from_id(first, last)
            row = Row(
                chapter,
                b.index,
                span.label,
                kind,
                _status(text, span, language),
                text,
                owb_text(span, language),
                j,
                _english_excerpt(e_text, j, e_found, first, last),
                span=span,
            )
            row.flags = _decision_flags(row, e_text, b.text, language)
            rows.append(row)
        rows += _recurring_rows(b, chapter, j, e_text, rows, language)
    # English quotations nothing in the translation answered.
    for j, found in enumerate(e_found):
        for first, last, _kind, etext in found:
            span = span_from_id(first, last)
            mapped = [
                i for i, a in enumerate(align) if a is not None and abs(a - j) <= 1
            ]
            if any(
                r.span and r.span.overlaps(span) and r.block_index in mapped
                for r in rows
            ):
                continue
            at = min((i for i, a in enumerate(align) if a == j), default=None)
            if at is None and mapped:
                at = min(mapped, key=lambda i: abs(align[i] - j))
            if at is None:
                continue
            b = blocks[at]
            row = Row(
                chapter,
                b.index,
                span.label,
                "english_only",
                ALLUSION,
                b.text,
                owb_text(span, language),
                j,
                etext or e_blocks[j].text,
                span=span,
            )
            row.flags = _decision_flags(row, e_blocks[j].text, b.text, language)
            rows.append(row)
    rows.sort(key=lambda r: (r.block_index, r.kind == "english_only"))
    return rows


def _english_excerpt(e_text: str, j, e_found, first: int, last: int) -> str:
    if j is None or j >= len(e_found):
        return ""
    for f, end, _kind, etext in e_found[j]:
        if etext and f <= last and first <= end:
            return etext
    return e_text


# ── Notes diff ──────────────────────────────────────────────────────────────
def notes_path(kind: str, slug: str, language: str) -> Path:
    return NOTES / kind / f"{slug}.{language}.json"


def load_notes(
    kind: str, slug: str, language: str, read: Reader = read_file
) -> list[dict]:
    raw = read(notes_path(kind, slug, language))
    return json.loads(raw)["references"] if raw else []


def _note_location(note: dict, work: Work) -> tuple[int | None, int | None]:
    """(chapter, per-chapter block) a note points at, reading a book note
    with no ``chapter_order`` as the admin view does: a work-level index."""
    i = note.get("block_index")
    if work.kind != "book":
        return None, i
    if "chapter_order" in note:
        return note["chapter_order"], i
    if i is None:
        return None, None
    for chapter in work.chapters:
        n = len(work.chapter_blocks(chapter))
        if i < n:
            return chapter, i
        i -= n
    return None, None


def notes_diff(rows: list[Row], notes: list[dict], work: Work) -> dict:
    """Join inventory rows to notes rows by reference within a chapter.

    One notes row covers every quotation of its reference in its block, so
    rows are grouped by (chapter, block, reference) first. A quotation group
    with no notes row is ``missing``; a notes row whose reference is quoted in
    the chapter but not in its block is ``wrong_block`` (with where it is);
    a notes row with nothing found behind it is ``unlocated`` — usually an
    allusion or a bare citation, listed so a worker can glance at it.
    """
    groups: dict[tuple, list[Row]] = defaultdict(list)
    for r in rows:
        groups[(r.chapter, r.block_index, r.span)].append(r)
    # A book note with no chapter_order is ambiguous: the admin view reads its
    # index work-wide, but most such files count per chapter and simply never
    # said which chapter (religious-affections: 26 chapters, indexes to 111).
    # So it may sit in any chapter, and either reading counts as its block.
    parsed = []
    for n in notes:
        if work.kind == "book" and "chapter_order" not in n:
            chapter, block, alt = None, n.get("block_index"), _note_location(n, work)
        else:
            (chapter, block), alt = _note_location(n, work), None
        parsed.append((n, chapter, block, alt, parse_reference(n.get("reference", ""))))
    used_groups: set = set()
    matched_notes: set[int] = set()

    def same_chapter(nch, gch):
        return work.kind != "book" or nch is None or nch == gch

    @cache
    def quotes(key, span: Span) -> bool:
        """Does this quotation group answer a note on ``span``? By reference,
        or — a note can carry a sibling reference (Heb 5:6 quoting Ps 110:4,
        Joshua 1:5 noted as Heb 13:5) — by the words themselves."""
        if key[2] and key[2].overlaps(span):
            return True
        source = owb_text(span, work.language, slack=1)
        return any(
            r.kind != "english_only"
            and source
            and verbatim(r.text, source, work.language)
            for r in groups[key]
        )

    def at(key, nch, nblock, alt) -> bool:
        return (key[1] == nblock and same_chapter(nch, key[0])) or (
            alt is not None and key[:2] == alt
        )

    # Exact block first, then nearest block in the chapter.
    for exact in (True, False):
        for k, (n, nch, nblock, alt, span) in enumerate(parsed):
            if k in matched_notes or span is None:
                continue
            options = [
                key
                for key in groups
                if key not in used_groups
                and same_chapter(nch, key[0])
                and (not exact or at(key, nch, nblock, alt))
                and quotes(key, span)
            ]
            if not options:
                continue
            key = min(
                options,
                key=lambda g: abs(g[1] - (nblock if nblock is not None else g[1])),
            )
            used_groups.add(key)
            matched_notes.add(k)
            if not exact:
                n["_found_block"] = key[1]
                n["_found_chapter"] = key[0]
    # A second note on an already-matched group (a range split in two rows).
    for k, (_n, nch, nblock, alt, span) in enumerate(parsed):
        if (
            k not in matched_notes
            and span
            and any(at(key, nch, nblock, alt) and quotes(key, span) for key in groups)
        ):
            matched_notes.add(k)

    missing = []
    for key, rs in sorted(groups.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1])):
        if key in used_groups:
            continue
        missing.append(
            {
                "chapter": key[0],
                "block_index": key[1],
                "reference": rs[0].reference,
                "kind": ",".join(sorted({r.kind for r in rs})),
                "status": rs[0].status,
                "count": len(rs),
                "flags": sorted({f for r in rs for f in r.flags}),
                "text": rs[0].text[:300],
            }
        )
    wrong = [
        {
            "reference": n["reference"],
            "chapter": nch,
            "notes_block": nblock,
            "found_chapter": n.pop("_found_chapter"),
            "found_block": n.pop("_found_block"),
        }
        for (n, nch, nblock, _alt, _span) in parsed
        if "_found_block" in n
    ]
    unlocated = [
        {
            "reference": n.get("reference"),
            "chapter": nch,
            "block_index": nblock,
            "status": n.get("status"),
        }
        for k, (n, nch, nblock, _alt, _span) in enumerate(parsed)
        if k not in matched_notes
    ]
    quotations = [m for m in missing if m["kind"] != "english_only"]
    return {
        "notes_rows": len(notes),
        "missing": quotations,
        "english_only_unnoted": [m for m in missing if m["kind"] == "english_only"],
        "wrong_block": wrong,
        "chapter_offsets": _offsets(wrong),
        "unlocated_notes": unlocated,
    }


def _offsets(wrong: list[dict]) -> dict[str, int]:
    """A chapter whose notes all sit N blocks off (a title or heading counted,
    or not): the brief's "indexes drift" case, named once instead of row by
    row. Reported where one shift explains at least three rows and half the
    chapter's misplaced ones."""
    by_chapter: dict = defaultdict(list)
    for w in wrong:
        if w["chapter"] == w["found_chapter"] and w["notes_block"] is not None:
            by_chapter[w["chapter"]].append(w["found_block"] - w["notes_block"])
    out = {}
    for chapter, shifts in by_chapter.items():
        shift = max(set(shifts), key=shifts.count)
        if shifts.count(shift) >= 3 and shifts.count(shift) * 2 >= len(shifts):
            out[str(chapter)] = shift
    return out


def summary(rows: list[Row], diff: dict | None = None) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[f"{r.kind}:{r.status}"] += 1
    quotations = [r for r in rows if r.kind != "english_only"]
    out = {
        "quotations": len(quotations),
        "already_owb": sum(r.status == ALREADY_OWB for r in quotations),
        "needs_requote": sum(r.status == NEEDS_REQUOTE for r in quotations),
        "english_only": len(rows) - len(quotations),
        "by_kind": dict(sorted(counts.items())),
    }
    if diff is not None:
        out.update(
            notes_rows=diff["notes_rows"],
            missing_from_notes=len(diff["missing"]),
            english_only_unnoted=len(diff["english_only_unnoted"]),
            wrong_block=len(diff["wrong_block"]),
            unlocated_notes=len(diff["unlocated_notes"]),
        )
    return out


def run_inventory(
    kind: str, slug: str, language: str, read: Reader = read_file
) -> dict:
    work = load_work(kind, slug, language, read)
    try:
        english = load_work(kind, slug, "en", read)
    except FileNotFoundError:
        english = None
    rows = inventory(work, english)
    diff = notes_diff(rows, load_notes(kind, slug, language, read), work)
    return {
        "kind": kind,
        "slug": slug,
        "language": language,
        "summary": summary(rows, diff),
        "rows": [r.as_json() for r in rows],
        "notes_diff": diff,
    }


# ── Validator ───────────────────────────────────────────────────────────────
_ELLIPSIS = re.compile(r"\s*(?:…|\.{3})\s*")
#: Verses either side of an edit's reference the OWB check reads: the
#: brief's residual scan ("contained in OWB verses v-1..v+1").
VALIDATE_SLACK = 1


@dataclass
class Problem:
    edit: int
    check: str
    message: str


def _quote_marks(language: str) -> list[tuple[str, str]]:
    """The language's quotation marks (``quote_marks`` in its data): «» unless
    it says otherwise — Swahili quotes with “”."""
    return [tuple(p) for p in language_data(language).get("quote_marks", [["«", "»"]])]


def _quoted_pieces(new_text: str, language: str) -> list[str]:
    """The words a splice claims are Scripture: each quotation in the
    language's marks (pieces joined by "…" split apart), or — with no quote
    marks — the whole replacement less any trailing citation (a recitation)."""
    text = re.sub(r"\s*\([^()]*\d[^()]*\)\s*$", "", new_text)
    inner = [
        q
        for o, c in _quote_marks(language)
        for q in re.findall(rf"{re.escape(o)}(.*?){re.escape(c)}", text, re.S)
    ]
    pieces = inner if inner else [text]
    return [p for piece in pieces for p in _ELLIPSIS.split(piece) if vc.normalise(p)]


def _tags(text: str) -> list[str]:
    return _TAG.findall(text)


def _balance(text: str, language: str) -> int:
    return sum(text.count(o) - text.count(c) for o, c in _quote_marks(language))


def _final(text: str, marks: list[str]) -> bool:
    t = render(text).rstrip(" »›”\"'’)")
    return bool(t) and t[-1] in marks


def validate(work: Work, edits: list[dict]) -> tuple[list[Problem], dict[str, str]]:
    """Check a splice spec by simulating it in order. Returns the problems
    and the containers as they would be after every edit that passed."""
    language = work.language
    marks = language_data(language).get("sentence_final", ["."])
    state = dict(work.containers)
    problems: list[Problem] = []
    for k, e in enumerate(edits):
        where = f"ch{e.get('chapter')} b{e.get('block')}"
        block_key = TITLE if e.get("block") == "title" else e.get("block")
        try:
            b = work.block(e.get("chapter"), block_key)
        except KeyError as exc:
            problems.append(Problem(k, "block", f"{where}: {exc}"))
            continue
        old, new = e.get("old", ""), e.get("new", "")
        body = state[b.container]
        # Re-split the edited text: a splice that passed cannot change the tag
        # sequence, so block i is still block i, only shifted.
        start, end = _shifted(work, state, b)
        raw = body[start:end]
        hits = raw.count(old) if old else 0
        expected = int(e.get("occurrences", 1))
        if hits != expected:
            problems.append(
                Problem(
                    k,
                    "unique",
                    f"{where}: old text found {hits}× in the block (expected {expected})",
                )
            )
            continue
        if old and body.count(old) > hits and not e.get("occurrences"):
            problems.append(
                Problem(
                    k,
                    "unique",
                    f"{where}: old text also occurs elsewhere in this chapter — pass occurrences or narrow it",
                )
            )
        new_raw = raw.replace(old, new)
        if _tags(new_raw) != _tags(raw):
            problems.append(
                Problem(k, "tags", f"{where}: the ordered tag sequence changes")
            )
        if _balance(new_raw, language) != _balance(raw, language):
            problems.append(
                Problem(
                    k,
                    "balance",
                    f"{where}: quote-mark balance {_balance(raw, language)} → {_balance(new_raw, language)}",
                )
            )
        if render(new).count("‹") != render(new).count("›"):
            problems.append(
                Problem(k, "balance", f"{where}: unpaired ‹ › in the replacement")
            )
        if _final(old, marks) and not _final(new, marks):
            problems.append(
                Problem(
                    k,
                    "final",
                    f"{where}: the old text ends a sentence ({render(old)[-1]}) and the new one does not",
                )
            )
        if not e.get("self_rendered"):
            span = parse_reference(e.get("reference", ""))
            if span is None:
                problems.append(
                    Problem(
                        k,
                        "owb",
                        f"{where}: no parseable `reference` (or mark the edit self_rendered)",
                    )
                )
            else:
                slack = int(e.get("slack", VALIDATE_SLACK))
                if not owb_text(span, language, slack=slack):
                    problems.append(
                        Problem(k, "owb", f"{where}: OWB has no text for {span.label}")
                    )
                for piece in _quoted_pieces(render(new), language):
                    if not is_owb(piece, span, language, slack=slack):
                        problems.append(
                            Problem(
                                k,
                                "owb",
                                f"{where}: not OWB {span.label}±{slack}: {piece[:80]!r}",
                            )
                        )
        if any(p.edit == k for p in problems):
            continue
        state[b.container] = body[:start] + new_raw + body[end:]
    return problems, state


def _shifted(work: Work, state: dict[str, str], b: Block) -> tuple[int, int]:
    """Where block ``b`` sits in the container's CURRENT text."""
    if b.index == TITLE or b.container.startswith("faq:"):
        return 0, len(state[b.container])
    spans = block_spans(state[b.container], top_level=work.kind == "bio")
    return spans[b.index]


def apply(work: Work, state: dict[str, str]) -> list[Path]:
    """Write the validated containers back, in each file's existing layout."""
    from .content_fixtures import render_rows
    from .text import word_count

    changed = [k for k in state if state[k] != work.containers[k]]
    if not changed:
        return []
    if work.kind == "bio":
        written = []
        if "html" in changed:
            work.paths["html"].write_text(state["html"], encoding="utf-8")
            written.append(work.paths["html"])
        if any(k.startswith("faq:") for k in changed):
            path = work.paths["faq"]
            original = path.read_text(encoding="utf-8")
            items = json.loads(original)
            for k in changed:
                if k.startswith("faq:"):
                    items[int(k[4:])]["a"] = state[k]
            path.write_text(_dump_like(items, original), encoding="utf-8")
            written.append(path)
        return written
    path = work.paths["fixture"]
    rows = json.loads(path.read_text(encoding="utf-8"))
    for key in changed:
        what, i = key.split(":")
        fields = rows[int(i)]["fields"]
        if what == "title":
            fields["title"] = state[key]
        else:
            fields["body_html"] = state[key]
            fields["word_count"] = word_count(state[key])
    path.write_text(render_rows(rows), encoding="utf-8")
    return [path]


def _dump_like(data, original: str) -> str:
    for indent in (2, 1, None):
        if json.dumps(
            json.loads(original), ensure_ascii=False, indent=indent
        ) == original.rstrip("\n"):
            tail = "\n" if original.endswith("\n") else ""
            return json.dumps(data, ensure_ascii=False, indent=indent) + tail
    raise ValueError("can't tell this file's JSON layout; edit it by hand")
