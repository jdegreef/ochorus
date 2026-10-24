"""Build J. C. Ryle's *Old Paths* (1877) from an Internet Archive scan.

Neither Gutenberg nor CCEL carries the book, so the source is the OCR of
William Hunt's London printing of 1878, Princeton Theological Seminary's copy
(`oldpathsbeingpla00ryle`) — the one pre-1929 scan on archive.org. It is read
from ABBYY's own XML (`_abbyy.gz`), not the plain-text layer, because the XML
keeps what the book needs and the text throws away:

* **Italics.** Ryle italicises a phrase in nearly every paragraph; ABBYY marks
  them character by character.
* **Type size.** Body text, the small type of quotations and Ryle's end-of-
  chapter extracts, and footnotes are told apart by x-height (a body "a" is
  22–24 px at 350 dpi, small type 18–20). A run of small type under the body
  text, after a gap or opening on a mark (*, †), is a page's footnotes.
* **Small capitals.** Each paper's divisions open in small capitals ("I. The
  FIRST remark … EVERY ONE OF US HAS AN UNDYING SOUL"); a capital no taller
  than the x-height is a small capital and is set lower-case.
* **Layout.** First-line indents give the paragraphs, across page breaks;
  running heads, folios and printer's signatures are dropped.

Each paper opens on a fresh page under its numeral and title (dropped; titles
come from `TITLES`), then its text or texts in italics, set as the epigraph.
Footnotes go after their paper, lettered a, b, c … as in *Practical Religion*
(a bare numbered `<sup>` is stripped corpus-wide), at the place the print's
mark stood — most marks survive OCR, the rest are anchored in the data file.

OCR REPAIRS live in `data/old-paths/ocr_fixes.json`, settled by aligning
ABBYY's reading with an independent Tesseract OCR of the same page images
(where the two disagree, the reading that is an English word in its context
wins), and then by checking every doubtful word against the page image:

* `words` — a word's text by its ABBYY id ("leaf.n"); a word broken over a
  line end is one fix naming both halves;
* `punct` — a stop ABBYY dropped or misread (`add` / `swap`);
* `hyphens` — line-end hyphens that belong to the word ("self-|denial");
  every other line-end hyphen is a break and is closed up;
* `text` — per chapter, literal (find, replace) pairs, each matching once;
* `anchors` — per chapter, the text each footnote mark follows, in order.

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry.

    DJANGO_DEBUG=true uv run python manage.py build_old_paths
    DJANGO_DEBUG=true uv run python manage.py build_old_paths --abbyy <saved _abbyy.gz>
"""

from __future__ import annotations

import gzip
import html as _html
import io
import json
import re
import statistics
from pathlib import Path
from string import ascii_lowercase

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from lxml import etree

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter

SLUG = "old-paths"
TITLE = "Old Paths"
#: The title page's "Being Plain Statements on Some of the Weightier Matters
#: of Christianity", without the participle.
SUBTITLE = "Plain Statements on Some of the Weightier Matters of Christianity"
AUTHOR_SLUG = "j-c-ryle"
COVER_COLOR = "#5b4a3a"
ARCHIVE_ID = "oldpathsbeingpla00ryle"
SOURCE_URL = f"https://archive.org/details/{ARCHIVE_ID}"
ABBYY_URL = f"https://archive.org/download/{ARCHIVE_ID}/{ARCHIVE_ID}_abbyy.gz"
PUBLICATION_YEAR = 1877
FIXES = Path(__file__).resolve().parent / "data" / SLUG / "ocr_fixes.json"

DESCRIPTION = (
    "Nineteen plain papers on the truths Ryle held “necessary to salvation”: "
    "the inspiration of Scripture, the soul, sin, forgiveness, justification, "
    "the cross, the Holy Ghost, conversion, faith and repentance, Christ’s "
    "invitation and intercession, election and perseverance. The doctrinal "
    "companion to Practical Religion and Knots Untied, it presses each truth "
    "home as a question the reader must answer for himself."
)

ATTRIBUTION = (
    "Public domain — J. C. Ryle, Old Paths (London: William Hunt and Company; "
    "preface dated October 1877). Text from the 1878 printing, Princeton "
    "Theological Seminary Library copy, digitized by the Internet Archive."
)

#: The papers, as headed in the text (the Contents drops their stops).
TITLES = [
    "Preface",
    "Inspiration",
    "Our Souls!",
    "Few Saved!",
    "Our Hope!",
    "Alive or Dead?",
    "Our Sins!",
    "Forgiveness",
    "Justification!",
    "The Cross of Christ",
    "The Holy Ghost",
    "Having the Spirit",
    "Conversion",
    "The Heart",
    "Christ’s Invitation",
    "Faith!",
    "Repentance",
    "Christ’s Power to Save",
    "Election",
    "Perseverance",
]
#: The leaf (scan page) each opens on: the Preface, then pages 1, 40, 64 …
STARTS = [
    11,
    19,
    58,
    82,
    111,
    139,
    168,
    197,
    229,
    257,
    281,
    309,
    340,
    358,
    376,
    394,
    421,
    454,
    476,
    494,
]
#: Leaves of text: the Preface (v–x) and the papers (1–521). The Contents and
#: the colophon fall outside.
LEAVES = [*range(11, 17), *range(19, 540)]
#: Where Ryle's closing "Note referred to at page 487" begins (set in small type).
CLOSING_NOTE_LEAF = 536

#: Small type that closes a paper — Ryle's extracts after "Inspiration" and
#: "Justification" — sits where footnotes would; it is text, not notes.
EXTRACT_LEAVES = {53, 256}
#: Notes whose mark the OCR lost, by leaf and opening words.
UNMARKED_NOTES = {12: "To this statement", 504: '"As Christ being'}
#: A note's second paragraph whose opening quote reads as a mark.
NOT_A_NOTE = {477: "He that go"}

#: x-height (median of a, c, e, m, n …) at or under which a paragraph is small type.
SMALL_TYPE = 20.5
_X_LETTERS = set("aceomnrsuvwxz")
_NS = "{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}"
_SIGNATURE = re.compile(r"^[A-Za-z]{1,2}\s?\d?$|^\W{1,3}$")
_NOTE_MARK_LINE = re.compile(r"^[\*†‡§•\+]")
_NOTE_START = re.compile(r"^(?:[\*†‡§•'\+]|-f-|[tf] ?(?=[\"“]))")
_BR = {"t": "<br/>", "it": False, "id": None}

#: Junk the OCR leaves in words whose letters are right, and the print's
#: furniture (applied to each chapter's text before the literal repairs).
CLEANUP = [
    (r"■\s*", ""),  # specks
    (
        r"(?<=[A-Za-z])(?:3[’'][-–]?|\}[’'][-–]?|\}[-–]|\}|\)\^)(?=[\s,.;:!?\"”’)<])",
        "",
    ),  # a y in two: "day}’"
    (r"\^", ""),
    (r"(?<![\w])[%\\|]+(?=[A-Za-z])", ""),  # "%written", "\who", "|in"
    (r"(?<=[A-Za-z,.;:!?])[|\]](?=[\s])", ""),  # "he] would", "for| me"
    (r"(?<=\s)\](?=[a-z])", ""),  # "]ministers"
    (r"(?<=[a-z])\[(?=\s)", ""),  # "among[ them"
    (r",,", ","),
    (r"\b[35][-'^]?(ou|our)\b", r"y\1"),  # "3'ou", "3our"
    (r"\b(Isa\.|Isaiah|Psalm|Ps\.|Psal\.) Iv\b", r"\1 lv"),
    (r"\bI(x[xvi]+|v)(?=\.)", r"l\1"),  # "Ixiii." is lxiii.
    (r"(?<=[\s>])'(?=p[a-z])", ""),  # an italic p read with an apostrophe
    (r"\b([A-Z]{2,})- ([A-Z]{2,})\b", r"\1\2"),  # "CAN- NOT", in capitals
    (r"(?<=[a-z])/'", ',"'),
    (r"(?<=[\s>])(?:1|7|13|25|2|3)(?=(?:he|him|not|paper|point|page|your)\b)", ""),
    (
        r"(?<=[a-z])\.(?=(?:shall|closing|so|show|stages|art|faith|it|struggle|than|shapen|see|s,)\b)",
        " ",
    ),
    (r"\b1\.5\.\)", "15.)"),
    (r"(?<=\d) j (?=[A-Z])", "; "),
    (r"(?<=[ (])([0-9])G\b", r"\g<1>6"),
    (r"\bJ (esus|udge|ohn|ustification|ust)\b", r"J\1"),
    (r"\bf (ree|ruits)\b", r"f\1"),
    (r"\(cZ\)", "(d)"),
    (
        r"Treatise on</i> J\S{5,30}\.—Johnstone.s Edition of Owens Works\.",
        "Treatise on Justification</i>.—Johnstone's Edition of Owen's Works.",
    ),
]
#: A date with OCR letters for digits ("1G84", "IGSO").
_YEAR = re.compile(r"\b([1I])([0-9GOCSlI])([0-9GOCSlI])([0-9GOCSlI])\b")
_YEAR_DIGITS = {"G": "6", "O": "0", "C": "6", "S": "8", "l": "1", "I": "1"}

#: Paragraph markers "(a)", "(1)" — the OCR gives some as (/), («), (h) for (b).
_MARKER = re.compile(
    r"^(\[(?:p|quote) \d+\] )(?:<i>)?(?:[({]+(?:<i>)?([^)\s]{1,4}?)|([A-Za-z]))(?:</i>)?\)",
    re.M,
)
#: Body-text marks that are not footnote marks.
_MARK_NOISE = [
    r"\*",
    r'(?<=["”])-f(?= \()',
    r"•\}-",
    r"-f-",
    r"•(?=\s|\w)",
    r"(?<=power\.) f(?= \()",
]


# --- the scan -----------------------------------------------------------------


def fetch_abbyy() -> bytes:
    resp = requests.get(
        ABBYY_URL,
        timeout=300,
        headers={"User-Agent": "OchorusBot/0.1 (+https://ochorus.org)"},
    )
    resp.raise_for_status()
    return resp.content


def parse(abbyy_gz: bytes) -> list[list[dict]]:
    """ABBYY XML → per leaf, paragraphs of lines of words. A word carries its
    text (small capitals set lower-case), italic flag, bbox and id "leaf.n"."""
    pages = []
    for _, pg in etree.iterparse(
        io.BytesIO(gzip.decompress(abbyy_gz)), tag=_NS + "page"
    ):
        leaf, n, pars = len(pages), 0, []
        for par in pg.iter(_NS + "par"):
            heights = [
                int(c.get("b")) - int(c.get("t"))
                for c in par.iter(_NS + "charParams")
                if c.text and c.text in _X_LETTERS
            ]
            xh = statistics.median(heights) if len(heights) >= 3 else None
            lines = []
            for ln in par.iter(_NS + "line"):
                words, cur = [], None
                for fm in ln.iter(_NS + "formatting"):
                    italic = fm.get("italic") == "true"
                    for c in fm.iter(_NS + "charParams"):
                        ch = c.text or " "
                        box = [int(c.get(k)) for k in "ltrb"]
                        if ch == " ":
                            cur = None
                            continue
                        if c.get("wordStart") == "true" or cur is None:
                            cur = {"t": "", "it": 0, "n": 0, "bbox": box[:]}
                            words.append(cur)
                        if (
                            ch.isupper()
                            and ch != "J"
                            and box[3] - box[1] <= (xh or 23) * 1.22
                        ):
                            ch = ch.lower()  # a small capital
                        cur["t"] += ch
                        cur["n"] += 1
                        cur["it"] += italic
                        cur["bbox"][2] = box[2]
                        cur["bbox"][1] = min(cur["bbox"][1], box[1])
                        cur["bbox"][3] = max(cur["bbox"][3], box[3])
                for w in words:
                    w["it"] = w["it"] * 2 > w.pop("n")
                    w["id"] = f"{leaf}.{n}"
                    n += 1
                if words:
                    lines.append(
                        {"bbox": [int(ln.get(k)) for k in "ltrb"], "words": words}
                    )
            if lines:
                pars.append(
                    {
                        "xh": xh,
                        "lines": lines,
                        "bbox": [
                            min(ln["bbox"][0] for ln in lines),
                            lines[0]["bbox"][1],
                            max(ln["bbox"][2] for ln in lines),
                            lines[-1]["bbox"][3],
                        ],
                    }
                )
        pages.append(pars)
        pg.clear()
    return pages


def _text(par: dict) -> str:
    return " ".join(w["t"] for ln in par["lines"] for w in ln["words"])


def _furniture(par: dict) -> bool:
    """A running head or folio: top of the page, one line."""
    txt = _text(par).lower()
    top = par["bbox"][1]
    return top < 205 or (
        top < 270
        and len(par["lines"]) == 1
        and bool(
            re.fullmatch(r"[\dgoilsvx ]*[.,]?", txt)
            or "old paths" in txt
            or "paths." in txt
            or (
                re.fullmatch(r"[a-z' ]+[.!]\s*\d*", txt)
                and par["lines"][0]["bbox"][0] > 300
            )
        )
    )


def layout(pages: list[list[dict]]) -> list[dict]:
    """Each text leaf's lines, as body (B), small type (S) or footnote (F)."""
    out = []
    for leaf in LEAVES:
        pars = [
            q
            for q in pages[leaf]
            if not _furniture(q) and _text(q) not in ("o", "•", ".", "o o o")
        ]
        if (
            pars
            and len(pars[-1]["lines"]) == 1
            and _SIGNATURE.match(_text(pars[-1]))
            and pars[-1]["bbox"][1] > 1900
        ):
            pars = pars[:-1]  # printer's signature
        kinds = [
            "S" if q["xh"] and q["xh"] <= SMALL_TYPE else "B" if q["xh"] else None
            for q in pars
        ]
        for i, k in enumerate(
            kinds
        ):  # a paragraph too short to measure takes its neighbour's size
            if k is None:
                kinds[i] = (
                    kinds[i - 1]
                    if i and kinds[i - 1]
                    else next((x for x in kinds[i:] if x), "B")
                )
        j = len(kinds)
        while j > 0 and kinds[j - 1] == "S":
            j -= 1
        if (
            0 < j < len(kinds)
        ):  # small type closing the page under body text: its footnotes
            gap = pars[j]["bbox"][1] - pars[j - 1]["bbox"][3]
            if _NOTE_MARK_LINE.match(pars[j]["lines"][0]["words"][0]["t"]) or gap >= 60:
                kinds[j:] = ["F"] * (len(kinds) - j)
        if leaf in EXTRACT_LEAVES:
            kinds = ["S" if k == "F" else k for k in kinds]
        lefts = [
            ln["bbox"][0]
            for q, k in zip(pars, kinds, strict=True)
            if k == "B"
            for ln in q["lines"]
        ]
        if not lefts:  # a page all in small type keeps its own margin
            lefts = [ln["bbox"][0] for q in pars for ln in q["lines"]]
            lefts = [x for x in lefts if x <= min(lefts) + 15] if lefts else []
        margin = statistics.median(lefts) if lefts else None
        rights = [
            ln["bbox"][2]
            for q, k in zip(pars, kinds, strict=True)
            if k == "B"
            for ln in q["lines"]
        ] or [ln["bbox"][2] for q in pars for ln in q["lines"]]
        rmargin = max(rights) if rights else None
        for q, k in zip(pars, kinds, strict=True):
            for i, ln in enumerate(q["lines"]):
                out.append(
                    {
                        "leaf": leaf,
                        "kind": k,
                        "left": ln["bbox"][0],
                        "right": ln["bbox"][2],
                        "margin": margin,
                        "rmargin": rmargin,
                        "par_first": i == 0,
                        "words": ln["words"],
                    }
                )
    return out


def _line_text(ln: dict) -> str:
    return " ".join(w["t"] for w in ln["words"])


def assemble(lines: list[dict]) -> list[dict]:
    """Lines → per paper, its blocks (epigraph, p, quote) and its notes."""
    by_leaf: dict[int, list[dict]] = {}
    for ln in lines:
        by_leaf.setdefault(ln["leaf"], []).append(ln)
    papers = []
    for ci, start in enumerate(STARTS):
        end = STARTS[ci + 1] if ci + 1 < len(STARTS) else 10**6
        lns = [
            ln
            for leaf in sorted(by_leaf)
            if start <= leaf < end
            for ln in by_leaf[leaf]
        ]
        paper: dict = {"blocks": [], "notes": []}
        # skip the heading: "PREFACE."; a numeral and title ("OLD PATHS." too on page 1)
        i = 1 if ci == 0 else (3 if start == 19 else 2)
        epigraph = []
        if ci:
            while i < len(lns):
                ln = lns[i]
                ind = ln["left"] - (ln["margin"] or ln["left"])
                italic = sum(w["it"] for w in ln["words"])
                if (
                    italic >= 2
                    or ind > 60
                    or _line_text(ln).startswith("—")
                    or (ln["kind"] == "S" and ind > -15 and lns[i + 1]["kind"] == "S")
                ):
                    epigraph.append(ln)
                    i += 1
                else:
                    break
        if epigraph:
            paper["blocks"].append(
                {
                    "kind": "epigraph",
                    "leaf": start,
                    "lines": [ln["words"] for ln in epigraph],
                }
            )
        prev, prev_kept = None, None
        for ln in lns[i:]:
            ended = (
                prev is None
                or (prev["rmargin"] and prev["right"] < prev["rmargin"] - 60)
                or re.search(r"[.!?:;\"'—)]$", _line_text(prev))
            )
            prev = ln
            ind = ln["left"] - (ln["margin"] or ln["left"])
            txt = _line_text(ln)
            if ln["kind"] == "F":
                first = (ln["par_first"] or (ind > 10 and ended)) and bool(
                    _NOTE_START.match(txt)
                    or txt.startswith(UNMARKED_NOTES.get(ln["leaf"], "\0"))
                )
                if NOT_A_NOTE.get(ln["leaf"], "\0") in txt:
                    first = False
                if first or not paper["notes"]:
                    paper["notes"].append(
                        {"leaf": ln["leaf"], "paras": [[ln["words"]]]}
                    )
                elif ind > 25 and ended:
                    paper["notes"][-1]["paras"].append([ln["words"]])
                else:
                    paper["notes"][-1]["paras"][-1].append(ln["words"])
                continue
            kind = "p" if ln["kind"] == "B" else "quote"
            last = paper["blocks"][-1] if paper["blocks"] else None

            def short(x):
                return x and x["rmargin"] and x["right"] < x["rmargin"] - 120

            if (
                kind == "quote"
                and short(ln)
                and short(prev_kept)
                and prev_kept["kind"] == "S"
                and last
                and last["kind"] == "quote"
                and not re.search(r"[—-]\s*$", _line_text(prev_kept))
            ):
                last["lines"].append([_BR, *ln["words"]])  # a line of verse
                prev_kept = ln
                continue
            if (
                last is None
                or last["kind"] != kind
                or (ind > (22 if kind == "p" else 12) and ended)
            ):
                paper["blocks"].append(
                    {"kind": kind, "leaf": ln["leaf"], "lines": [ln["words"]]}
                )
            else:
                last["lines"].append(ln["words"])
            prev_kept = ln
        papers.append(paper)
    return papers


# --- words to text ------------------------------------------------------------


class Typesetter:
    """Turns a block's lines of words into text, applying the word repairs."""

    def __init__(self, fixes: dict):
        self.words = fixes["words"]
        self.punct = fixes["punct"]
        self.hyphens = set(fixes["hyphens"])

    def word(self, w: dict, nxt: dict | None) -> tuple[str, bool]:
        """A word's text after its repair; True when the repair spans the line end."""
        text, merged = self._repaired(w, nxt)
        p = self.punct.get(w["id"]) if w["id"] else None
        if p and "add" in p:
            m = re.search(r"['\"’”)\]^*•}/]*$", text)
            if not re.search(r"[.,;:!?]$", text[: m.start()]):
                text = text[: m.start()] + p["add"] + text[m.start() :]
        elif p and "swap" in p:
            text = re.sub(r"[.,](?=[^.,]*$)", p["swap"], text, count=1)
        return text, merged

    def _repaired(self, w: dict, nxt: dict | None) -> tuple[str, bool]:
        fix = self.words.get(w["id"]) if w["id"] else None
        if fix is None:
            return w["t"], False
        merged = isinstance(fix, list)
        new = fix[0] if merged else fix
        a = w["t"][:-1] + nxt["t"] if merged else w["t"]
        lead = re.match(r"^[^A-Za-z]*", a).group(0).replace("^", "")
        tail = re.search(r"[^A-Za-z]*$", a).group(0).replace("^", "")
        core = a[len(lead) : len(a) - len(tail)] if tail else a[len(lead) :]
        rest = core[len(new) :] if core.lower().startswith(new.lower()) else ""
        if tail.startswith("'") and new.endswith("y") and re.search(r"[j}\]3]'", a):
            tail = tail[1:]  # "Holj'" is "Holy": the apostrophe is the y's tail
        if rest[:1] in tuple(".,;:!?"):
            tail = rest[0] + tail  # "sin.l" is "sin." and a speck of the next page
        return lead + new + tail, merged

    def tokens(self, lines: list[list[dict]]) -> list[list]:
        """[text, italic] per word, line-end hyphens closed up or kept."""
        toks: list[list] = []
        skip_next = False
        for li, ws in enumerate(lines):
            for wi, w in enumerate(ws):
                if wi == 0 and skip_next:
                    skip_next = False
                    continue
                nxt = (
                    lines[li + 1][0]
                    if wi == len(ws) - 1 and li + 1 < len(lines) and lines[li + 1]
                    else None
                )
                text, merged = self.word(w, nxt)
                if merged:
                    toks.append([text, w["it"], w["id"]])
                    skip_next = True
                    continue
                if (
                    wi == 0
                    and toks
                    and toks[-1][0].endswith("-")
                    and re.match(r"[a-z]", text)
                ):
                    head = toks[-1][0][:-1]
                    toks[-1][0] = (
                        head + ("-" if toks[-1][2] in self.hyphens else "") + text
                    )
                    continue
                toks.append([text, w["it"], w["id"]])
        return toks


def set_text(toks: list[list]) -> str:
    """Tokens → one paragraph's text: quote marks to their words, italics as
    <i>, the print's spaced stops closed up."""
    # A lone quote mark belongs to a neighbour: a closing one to the word
    # before while a quotation is open, else an opening one to the word after.
    joined: list[list] = []
    carry, open_q = "", False
    for t, it, _ in toks:
        t = t.replace("^", "") if re.fullmatch(r"[\^'\"]+", t) else t
        if t == "":
            continue
        prv = joined[-1] if joined else None
        if re.fullmatch(r"[\"']+", t):
            if '"' in t and open_q and prv:
                prv[0] += t
                open_q = False
                continue
            if "'" in t and '"' not in t and prv and re.search(r"[.,;:!?]$", prv[0]):
                prv[0] += t
                continue
            carry += t
            if '"' in t:
                open_q = True
            continue
        t = carry + t
        carry = ""
        if t.endswith('"') and not open_q and t.count('"') % 2 == 1 and len(t) > 1:
            t = t[:-1]
            carry = '"'
            open_q = True  # it opens the next word's quotation
        else:
            open_q ^= t.count('"') % 2 == 1
        joined.append([t, it])
    if carry and joined:
        joined[-1][0] += carry

    def italic(tok):
        return tok[1] and re.search(r"[A-Za-z]", tok[0])

    out = []
    for i, tok in enumerate(joined):
        t = tok[0]
        if italic(tok):
            lead, core, tail = re.match(
                r"^([(\"'‘“]*)(.*?)([,.;:!?\)\]\"'”’—]*)$", t
            ).groups()
            s = (
                " "
                + _html.escape(lead, quote=False)
                + ("" if i and italic(joined[i - 1]) else "<i>")
            )
            s += _html.escape(core, quote=False)
            if i + 1 < len(joined) and italic(joined[i + 1]):
                s += _html.escape(tail, quote=False)
            else:
                s += "</i>" + _html.escape(tail, quote=False)
            out.append(s)
        elif t == "<br/>":
            out.append("<br/>")
        else:
            out.append(" " + _html.escape(t, quote=False))
    s = "".join(out).strip()
    s = re.sub(r"\s+([!?;:,.)])", r"\1", s)
    return re.sub(r"\s*—\s*", "—", s)


def _markers(text: str) -> str:
    """Paragraph markers in sequence: "(a)" … or "(1)" …, the OCR's garbles mended."""
    prev = None

    def fix(m):
        nonlocal prev
        raw = (m.group(2) or m.group(3).lower()).replace("<i>", "").replace("</i>", "")
        nxt_letter = (
            chr(ord(prev) + 1) if prev and len(prev) == 1 and prev.isalpha() else None
        )
        if raw in ("h", "6") and nxt_letter == "b":
            val = "b"
        elif raw == ".5":
            val = "5"
        elif raw.isdigit():
            val = raw
        elif raw == "b" and prev and prev.isdigit():
            val = str(int(prev) + 1)  # a 6 read as b
        elif raw in ("/", "/i", "J", "?", "(?"):
            val = nxt_letter or {"/": "f", "/i": "h"}.get(raw, "a")
        elif raw in ("«", "o"):
            val = "a"
        elif raw == "Ji":
            val = "h"
        else:
            val = raw
        prev = val
        return f"{m.group(1)}({val})"

    return _MARKER.sub(fix, text)


def _year(m: re.Match) -> str:
    s = m.group(0)
    if s.isdigit() or not re.search(r"\d", s[1:]):
        return s
    return "".join(_YEAR_DIGITS.get(c, c) for c in s)


def repair(order: int, text: str, fixes: dict) -> str:
    text = _markers(text)
    for pat, rep in CLEANUP:
        text = re.sub(pat, rep, text, flags=re.M)
        if pat == r"\b1\.5\.\)":
            text = _YEAR.sub(_year, text)
    for find, replace in fixes["text"].get(str(order), []):
        if text.count(find) != 1:
            raise CommandError(
                f"ch {order}: repair {find!r} matches {text.count(find)} times, not once"
            )
        text = text.replace(find, replace)
    return text


# --- text to HTML -------------------------------------------------------------


def curl(text: str) -> str:
    """Straight quotes to curly, paragraph by paragraph (tags left alone):
    double quotes alternate when a paragraph has an even number, else an
    opening one follows a space or dash."""

    def para(p):
        parts = re.split(r"(<[^>]+>)", p)
        n = sum(x.count('"') for x in parts if not x.startswith("<"))
        is_open, prev, out = False, " ", []
        for x in parts:
            if x.startswith("<"):
                out.append(x)
                continue
            y = []
            for i, c in enumerate(x):
                if c == '"':
                    is_open = (not is_open) if n % 2 == 0 else prev in " (—[\n"
                    y.append("“" if is_open else "”")
                elif c == "'":
                    nxt = x[i + 1] if i + 1 < len(x) else " "
                    y.append("‘" if prev in " (—[“\n" and nxt.isalpha() else "’")
                else:
                    y.append(c)
                prev = c
            out.append("".join(y))
        p = "".join(out)
        p = re.sub(r"”(?=[A-Za-z(])", "” ", p)
        p = re.sub(r"(?<=[A-Za-z,;:!?])“", " “", p)
        p = re.sub(r"“\s+", "“", p)
        p = re.sub(r"\s+”", "”", p)
        return re.sub(r"‘\s+", "‘", p)

    return "\n\n".join(para(p) for p in text.split("\n\n"))


def to_html(order: int, text: str, anchors: list[str]) -> str:
    paras = text.split("\n\n")
    notes = [p for p in paras if p.startswith("[note ")]
    body = "\n\n".join(p for p in paras if not p.startswith("[note "))
    for pat in _MARK_NOISE:
        body = re.sub(pat, "", body)
    body = curl(re.sub(r" +", " ", body))
    if len(anchors) != len(notes):
        raise CommandError(
            f"ch {order}: {len(anchors)} note anchors for {len(notes)} notes"
        )
    pos = 0
    for k, anchor in enumerate(anchors):
        i = body.find(anchor, pos)
        if i < 0:
            raise CommandError(f"ch {order}: note anchor {anchor!r} not found")
        pos = i + len(anchor)
        body = body[:pos] + f"<sup>{ascii_lowercase[k]}</sup>" + body[pos:]
    out = []
    for p in body.split("\n\n"):
        m = re.match(r"\[(\w+) (\d+)\] ?(.*)$", p, re.S)
        kind, leaf, txt = m.group(1), int(m.group(2)), m.group(3).strip()
        if not txt:
            continue
        if order == len(STARTS) and leaf >= CLOSING_NOTE_LEAF:
            # Ryle's closing note: small type, but his own prose
            if re.match(r"(?i)note referred to", txt):
                out.append("<h3>Note</h3>")
                continue
            kind = "p"
        if kind == "epigraph":  # one or more texts: “<i>words</i>.”—Reference.
            for seg in re.split(r"(?<=[\d.])\s+(?=[“”\"‘’'^]*<i>)", txt):
                words, _, ref = seg.rpartition("—")
                words = re.sub(r"^[’'‘“”\"^.\s]+|[’'‘“”\"^\s]+$", "", words)
                words = re.sub(r"[\s“”]+(?=[.,;:!?]?$)", "", words)
                out.append(f"<p>“{words}”—{ref.strip()}</p>")
        elif kind == "quote":
            out.append(f"<blockquote><p>{txt}</p></blockquote>")
        else:
            out.append(f"<p>{txt}</p>")
    for k, note in enumerate(notes):
        txt = re.sub(r"^\[note \d+\] ", "", note)
        txt = re.sub(r"^(?:[\*†‡§•'\+]|-f-|[tf](?= ?[\"“]))\s*", "", txt.strip())
        first, *rest = [curl(x.strip()) for x in txt.split(" ¶ ")]
        out.append(f"<p><sup>{ascii_lowercase[k]}</sup> {first}</p>")
        out.extend(f"<p>{x}</p>" for x in rest)
    return "\n".join(out)


def build(abbyy_gz: bytes, fixes: dict) -> list[tuple[str, str]]:
    """The scan and its repairs → (title, body_html) per chapter."""
    papers = assemble(layout(parse(abbyy_gz)))
    setter = Typesetter(fixes)
    chapters = []
    for order, (title, paper) in enumerate(zip(TITLES, papers, strict=True), start=1):
        parts = [
            f"[{b['kind']} {b['leaf']}] " + set_text(setter.tokens(b["lines"]))
            for b in paper["blocks"]
        ]
        parts += [
            f"[note {n['leaf']}] "
            + " ¶ ".join(set_text(setter.tokens(p)) for p in n["paras"])
            for n in paper["notes"]
        ]
        text = repair(order, "\n\n".join(parts), fixes)
        chapters.append(
            (title, to_html(order, text, fixes["anchors"].get(str(order), [])))
        )
    return chapters


class Command(BaseCommand):
    help = "Build J. C. Ryle's Old Paths from its Internet Archive scan (dev DB)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--abbyy",
            help="Read the scan's _abbyy.gz from this file instead of archive.org.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — seed the library first."
            ) from None
        abbyy = Path(opts["abbyy"]).read_bytes() if opts.get("abbyy") else fetch_abbyy()
        chapters = build(abbyy, json.loads(FIXES.read_text(encoding="utf-8")))
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
            "publication_year": PUBLICATION_YEAR,
        }
        book, was_created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(SLUG),
            },
        )
        book.chapters.all().delete()
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 500:
                raise CommandError(
                    f"ch {order} ({title!r}): only {wc} words — aborted."
                )
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:40]:40} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters")
        )
