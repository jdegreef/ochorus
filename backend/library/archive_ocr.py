"""Sermons from archive.org scans: the djvu OCR text, cleaned and cross-checked.

Some public-domain preachers survive only as scanned books — Samuel Davies'
*Sermons* (1864), Chalmers' *Sermons and Discourses* (1844), Bonar's *Family
Sermons* (1863) — and their only clean-looking transcriptions online are
modernised rewrites (SermonIndex's Davies quotes the NIV). The printed text is
in archive.org's `<id>_djvu.txt`, which is OCR laid out line by line: running
heads and page numbers between pages, words hyphenated across lines, a space
before every `;` and `?`, and 10–15 misread words per thousand.

Two things make that usable:

* ``clean`` turns a slice of the OCR back into paragraphs — drops page furniture,
  rejoins paragraphs split by a page turn, undoes line-end hyphens when the
  joined word is a real one, and closes up the spaced punctuation.
* ``reconcile`` cross-checks scans. archive.org often holds two or three
  independent scans of the same edition, whose misreadings rarely coincide
  ("Christy" in one, "Christ," in the other). Aligning them word by word and
  taking, wherever they disagree, the reading that is a real word removes most
  of the noise mechanically. What survives is repaired the usual way
  (``BODY_CORRECTIONS``), from a reader's report.

The word list is the English library itself (``library_vocabulary``), so "real
word" means "a word some other text on the shelf uses".
"""

from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import requests

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
CONTENT_DIR = Path(__file__).resolve().parent / "fixtures" / "content"

# A word must appear this often elsewhere in the library to count as real.
MIN_REAL = 2


@lru_cache(maxsize=8)
def fetch_djvu(identifier: str) -> str:
    url = f"https://archive.org/download/{identifier}/{identifier}_djvu.txt"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    return resp.text


@lru_cache(maxsize=1)
def library_vocabulary() -> Counter:
    vocab: Counter = Counter()
    for path in CONTENT_DIR.glob("*/*.en.json"):
        for row in json.loads(path.read_text()):
            text = row["fields"].get("body_text") or ""
            vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", text))
    return vocab


def _spans_agree(mine: list[str], theirs: list[str], core, real) -> bool:
    """May `theirs` replace `mine`, a stretch the scans split differently?

    Yes when the letters are the same and only the spacing differs ("ungo
    lliness" / "ungodliness"), or when `mine` holds a non-word and `theirs`,
    no longer by more than a word, holds none ("dnst its" / "dread its").
    """
    if not theirs or not all(real(t) for t in theirs):
        return False
    if "".join(core(m) for m in mine) == "".join(core(t) for t in theirs):
        return True
    return abs(len(mine) - len(theirs)) <= 1 and not all(real(m) for m in mine)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class SliceError(ValueError):
    """A marker that does not occur where `slice_sermon` needs it."""


def _flatten(text: str) -> tuple[str, list[int]]:
    """`text` case-folded with whitespace runs collapsed, and each char's index."""
    chars, where, prev_space = [], [], False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                chars.append(" ")
                where.append(i)
            prev_space = True
        else:
            chars.append(ch.casefold())
            where.append(i)
            prev_space = False
    return "".join(chars), where


def slice_sermon(text: str, start_marker: str, body_starts: str, end_marker: str) -> str:
    """The OCR of one sermon: from its Bible text to the next sermon's heading.

    A book repeats a sermon's title and text in its contents list and running
    heads, so the slice starts at the last occurrence of `start_marker` (the
    words its Bible text begins with) before `body_starts` (the sermon's first
    words, which must follow within a page), and runs to the first `end_marker`
    after that. All three are matched case- and
    whitespace-insensitively; keep `body_starts` short, since each scan
    misreads different letters.
    """
    hay, where = _flatten(text)
    start, body = _norm(start_marker), _norm(body_starts)
    a = hay.find(start)
    while a >= 0:
        anchor = hay.find(body, a, a + _PAGE_CHARS)
        if anchor >= 0:
            break
        a = hay.find(start, a + 1)
    else:
        raise SliceError(f"no {start_marker!r} followed by {body_starts!r}")
    # A contents entry near the start can sit within a page of the body too;
    # the sermon's own Bible text is the last occurrence before its first words.
    a = hay.rfind(start, a, anchor)
    b = hay.find(_norm(end_marker), anchor)
    if b < 0:
        raise SliceError(f"end marker not found after the body: {end_marker!r}")
    # The marker may fall mid-verse ("neither the things that are in the
    # world"); start at the top of its paragraph so the whole text comes too.
    begin = where[a]
    gap = list(re.finditer(r"\n[ \t]*\n", text[max(0, begin - _PAGE_CHARS):begin]))
    if gap:
        begin = max(0, begin - _PAGE_CHARS) + gap[-1].end()
    return text[begin:where[b]]


# How far after the Bible text the sermon's first words may start.
_PAGE_CHARS = 3000


# A running head: a short line in capitals, perhaps with the page number, or a
# bare page number. Body text in capitals is rare and never this short.
_PAGE_NO = re.compile(r"^[\divxlcIVXLC]{1,5}\.?$")
# The bracketed tag a two-column edition sets in its running head: "[SERM."
_SERM_TAG = re.compile(r"^\W{0,3}\w?SERM\W{0,3}$", re.I)


def _letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _is_furniture(line: str, heads: tuple[str, ...] = ()) -> bool:
    t = line.strip()
    if not t:
        return False
    if _PAGE_NO.match(t) or _SERM_TAG.match(t):
        return True
    if heads and _letters(t) in heads:
        return True  # a running head set in the sermon title's own case
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True  # stray marks: "■", ". . .", "*"
    upper = sum(c.isupper() for c in letters) / len(letters)
    return len(t) <= 90 and upper > 0.85 and len(letters) >= 4


# A footnote at the foot of a page: "* This is the most literal translation…".
# It runs to the next blank line, and is set after the sermon (as Unspoken
# Sermons sets MacDonald's), its mark left where the text refers to it.
_FOOTNOTE = re.compile(r"^\s*[*†‡§]\s")

_TERMINAL = ("." , "!", "?", ":", "\"", "”", "’", "'", ")")


def clean(ocr: str, title: str = "") -> list[str]:
    """OCR lines → paragraphs of plain text.

    Blank lines separate paragraphs, but a page turn also leaves one, so a block
    that stops without terminal punctuation and is followed by one starting in
    lower case is the same paragraph. Footnotes come out of the running text and
    follow it, in order. `title` names the sermon, whose running head some
    editions set in its own mixed case.
    """
    vocab = library_vocabulary()
    heads = (_letters(title),) if title else ()
    blocks: list[list[str]] = [[]]
    notes: list[list[str]] = []
    in_note = False
    for line in ocr.splitlines():
        if not line.strip():
            in_note = False
            if blocks[-1]:
                blocks.append([])
            continue
        if _FOOTNOTE.match(line):
            notes.append([line.strip()])
            in_note = True
            continue
        if in_note:
            notes[-1].append(line.strip())
            continue
        if _is_furniture(line, heads):
            continue
        blocks[-1].append(line.strip())
    paras: list[str] = []
    for block in (b for b in blocks if b):
        text = ""
        for line in block:
            text = _join(text, line, vocab)
        continues = paras and (
            paras[-1].endswith("-")
            or (not paras[-1].rstrip().endswith(_TERMINAL) and text[:1].islower())
        )
        if continues:
            paras[-1] = _join(paras[-1], text, vocab)
        else:
            paras.append(text)
    for note in notes:
        text = ""
        for line in note:
            text = _join(text, line, vocab)
        paras.append(text)
    return [_tidy(p) for p in paras]


def _join(left: str, right: str, vocab: Counter) -> str:
    if not left:
        return right
    m = re.search(r"([A-Za-z]+)-$", left)
    if m:
        first = re.match(r"[A-Za-z]+", right)
        if first:
            head, tail = m.group(1).lower(), first.group(0).lower()
            whole_real = vocab[head + tail] >= MIN_REAL
            parts_real = vocab[head] >= MIN_REAL and vocab[tail] >= MIN_REAL
            if whole_real or not parts_real:
                return left[:-1] + right  # "pre-" + "vailed" → "prevailed"
        return left + right  # a real compound broken at its hyphen: "sin-killers"
    return left + " " + right


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("''", '"')  # a closing double mark read as two singles
    text = re.sub(r" +([,.;:?!])", r"\1", text)  # "mortal ;" → "mortal;"
    return _space_quotes(text)


def _space_quotes(text: str) -> str:
    """Seat each straight double mark against its quotation.

    The OCR spaces them at random ('"beatitude "in addition'). In a paragraph
    with an even count they alternate open/close, so an opener loses the space
    after it and a closer the space before it. An odd count means a quotation
    running on from or into another paragraph, so those are left alone.
    """
    if text.count('"') % 2:
        return text
    out, opening = [], True
    for part in re.split(r'(\s*"\s*)', text):
        if '"' not in part:
            out.append(part)
            continue
        if opening:
            lead = " " if out and out[-1] and not out[-1].endswith(("(", "—", "-")) else ""
            out.append(lead + '"')
        else:
            out.append('" ')
        opening = not opening
    joined = re.sub(r" {2,}", " ", "".join(out))
    return re.sub(r'" (?=[,.;:?!—)\'’]|$)', '"', joined).strip()


# --- cross-checking scans -----------------------------------------------------

_TOKEN = re.compile(r"\S+")


def reconcile(primary: list[str], others: list[list[str]]) -> list[str]:
    """Correct `primary`'s misread words from independent scans of the same page.

    Each paragraph's words are aligned against the whole text of every other
    scan. Where the scans disagree on a single word, the primary's reading
    stands unless it is not a real word and another scan's is; then the other
    scan's token is taken whole, punctuation and all ("Christy" → "Christ,").
    Words are aligned on their letters, so a misread comma alone never moves
    the alignment. Paragraph breaks are the primary's.
    """
    vocab = library_vocabulary()

    def core(tok: str) -> str:
        return re.sub(r"[^A-Za-z']", "", tok).strip("'").lower()

    def real(tok: str) -> bool:
        c = core(tok)
        return bool(c) and all(vocab[p] >= MIN_REAL for p in c.split("'") if p)

    other_tokens = [_TOKEN.findall(" ".join(o)) for o in others]
    out: list[str] = []
    for para in primary:
        toks = _TOKEN.findall(para)
        for alt in other_tokens:
            sm = difflib.SequenceMatcher(None, [core(t) for t in toks], [core(t) for t in alt], autojunk=False)
            fixes = []  # (i1, i2, replacement tokens), applied right to left
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op != "replace":
                    continue
                mine, theirs = toks[i1:i2], alt[j1:j2]
                if i2 - i1 == j2 - j1:
                    for k, (m, t) in enumerate(zip(mine, theirs, strict=True)):
                        if not real(m) and real(t):
                            toks[i1 + k] = t
                elif _spans_agree(mine, theirs, core, real):
                    fixes.append((i1, i2, theirs))
            for i1, i2, theirs in reversed(fixes):
                toks[i1:i2] = theirs
        out.append(" ".join(toks))
    return out

