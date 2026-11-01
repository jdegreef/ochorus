"""Sermons from archive.org scans: the djvu OCR text, cleaned and cross-checked.

Some public-domain preachers survive only as scanned books — Samuel Davies'
*Sermons* (1864), Chalmers' *Sermons and Discourses* (1844), Bonar's *Family
Sermons* (1863) — and their only clean-looking transcriptions online are
modernised rewrites (SermonIndex's Davies quotes the NIV). The printed text is
in archive.org's `<id>_djvu.txt` (fetched by `import_archive.fetch_text`), which
is OCR laid out line by line: running heads and page numbers between pages,
words hyphenated across lines, a space before every `;` and `?`, and 10–15
misread words per thousand.

``sermon_paragraphs`` is the one entry point. It slices the sermon out of each
scan, ``clean``s each slice back into paragraphs — drops page furniture, rejoins
paragraphs split by a page turn, undoes line-end hyphens when the joined word is
a real one, sets footnotes after the text, closes up the spaced punctuation —
and then ``reconcile``s them. archive.org often holds two or three independent
scans of the same edition, whose misreadings rarely coincide ("Christy" in one,
"Christ," in the other); aligning them word by word and taking, wherever they
disagree, the reading that is a real word removes most of the noise
mechanically. What survives is repaired the usual way (``BODY_CORRECTIONS``),
from a reader's report.

"Real word" means one the English library uses: ``english_audit``'s corpus
oracle, so the importer and the audit agree on what a word is.

The book builders (``import_archive``, ``archive_hocr``, ``archive_book``) have
their own reflow of the same OCR, tuned to whole books; this one is tuned to a
single sermon cut out of a volume and to cross-checking scans.
"""

from __future__ import annotations

import difflib
import re
from functools import lru_cache

from library.english_audit import library_word_counts

# A word must appear this often elsewhere in the library to count as real. At 2,
# misreads that leaked into the corpus twice ("tbe") passed for words.
MIN_REAL = 3
# How far after the Bible text the sermon's first words may start.
_PAGE_CHARS = 3000


class SliceError(ValueError):
    """A marker that does not occur where `slice_sermon` needs it."""


def sermon_paragraphs(
    scans: list[str], text_starts: str, body_starts: str, ends_before: str, title: str = ""
) -> tuple[str, list[str]]:
    """One sermon from one or more scans of its edition: (Bible text, paragraphs).

    `scans[0]` is the primary — pick the cleanest — and the rest only correct
    it; a corrector whose OCR misreads one of the markers is left out rather than
    failing the sermon. The paragraphs before the one opening on `body_starts` are the Bible
    text, joined into one string; the paragraphs from it on are the sermon, its
    footnotes last.
    """
    primary = clean(slice_sermon(scans[0], text_starts, body_starts, ends_before), title)
    others = []
    for scan in scans[1:]:
        try:
            others.append(clean(slice_sermon(scan, text_starts, body_starts, ends_before), title))
        except SliceError:
            continue  # this scan misread a marker; the others still correct the primary
    text = reconcile(primary, others)
    body = _norm(body_starts)
    at = next((i for i, p in enumerate(text) if _norm(p).startswith(body)), None)
    if at is None:
        raise SliceError(f"no paragraph opens with {body_starts!r}")
    return " ".join(text[:at]), text[at:]


# --- slicing ------------------------------------------------------------------


def _norm(text: str) -> str:
    return _flatten(text)[0].strip()


def _fold(ch: str) -> str:
    """One char case-folded to ONE char, so `_flatten`'s index stays aligned.

    `casefold` expands some ("ﬁ" → "fi", "ß" → "ss"); those keep their case.
    """
    folded = ch.casefold()
    return folded if len(folded) == 1 else ch


def _flatten(text: str) -> tuple[str, tuple[int, ...]]:
    """`text` case-folded with whitespace runs collapsed, and each char's index."""
    chars, where = [], []
    for m in re.finditer(r"\s+|\S", text):
        chars.append(" " if m[0].isspace() else _fold(m[0]))
        where.append(m.start())
    return "".join(chars), tuple(where)


# Cached apart from `_norm`'s short strings, which would otherwise evict the
# volumes: a batch slices several sermons from the same 2 MB scan.
_flatten_volume = lru_cache(maxsize=4)(_flatten)


def slice_sermon(text: str, text_starts: str, body_starts: str, ends_before: str) -> str:
    """The OCR of one sermon: from its Bible text to the next sermon's heading.

    A book repeats a sermon's title and text in its contents list and running
    heads, so the slice starts at the last occurrence of `text_starts` (the
    words its Bible text begins with) before `body_starts` (the sermon's first
    words, which must follow within a page), and runs to the first
    `ends_before` after that. All three are matched case- and
    whitespace-insensitively; keep `body_starts` short, since each scan
    misreads different letters.
    """
    hay, where = _flatten_volume(text)
    start, body = _norm(text_starts), _norm(body_starts)
    a = hay.find(start)
    while a >= 0:
        anchor = hay.find(body, a, a + _PAGE_CHARS)
        if anchor >= 0:
            break
        a = hay.find(start, a + 1)
    else:
        raise SliceError(f"no {text_starts!r} followed by {body_starts!r}")
    # A contents entry near the start can sit within a page of the body too;
    # the sermon's own Bible text is the last occurrence before its first words.
    a = hay.rfind(start, a, anchor)
    b = hay.find(_norm(ends_before), anchor)
    if b < 0:
        raise SliceError(f"end marker not found after the body: {ends_before!r}")
    # The marker may fall mid-verse ("neither the things that are in the
    # world"); start at the top of its paragraph so the whole text comes too.
    begin = where[a]
    lo = max(0, begin - _PAGE_CHARS)
    gap = list(re.finditer(r"\n[ \t]*\n", text[lo:begin]))
    if gap:
        begin = lo + gap[-1].end()
    return text[begin:where[b]]


# --- cleaning -----------------------------------------------------------------

# A running head: a short line in capitals, perhaps with the page number, or a
# bare page number (a roman folio has no stop; "II." on its own line is a
# sermon's division and stays). Body text in capitals is rare and never this short.
_PAGE_NO = re.compile(r"^(?:\d{1,4}|[ivxlc]{1,6}|[IVXLC]{1,6})$")
# The bracketed tag a two-column edition sets in its running head: "[SERM."
_SERM_TAG = re.compile(r"^\W{0,3}\w?SERM\W{0,3}$", re.I)
# A footnote at the foot of a page: "* This is the most literal translation…".
# It runs to the next blank line, and is set after the sermon (as Unspoken
# Sermons sets MacDonald's), its mark left where the text refers to it.
_FOOTNOTE = re.compile(r"^\s*[*†‡§]\s+[A-Za-z\"“]")  # not an asterism "* * *"
_TERMINAL = (".", "!", "?", ":", '"', "”", "’", "'", ")")


def _letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _is_furniture(line: str, head: str = "") -> bool:
    t = line.strip()
    if not t:
        return False
    if _PAGE_NO.match(t) or _SERM_TAG.match(t):
        return True
    if head and _letters(t) == head:
        return True  # a running head set in the sermon title's own case
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True  # stray marks: "■", ". . .", "*"
    upper = sum(c.isupper() for c in letters) / len(letters)
    return len(t) <= 90 and upper > 0.85 and len(letters) >= 4


def clean(ocr: str, title: str = "") -> list[str]:
    """OCR lines → paragraphs of plain text.

    Blank lines separate paragraphs, but a page turn also leaves one, so a block
    that stops without terminal punctuation and is followed by one starting in
    lower case is the same paragraph. Footnotes come out of the running text and
    follow it, in order. `title` names the sermon, whose running head some
    editions set in its own mixed case.
    """
    head = _letters(title)
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
        if _is_furniture(line, head):
            continue
        blocks[-1].append(line.strip())
    paras: list[str] = []
    for block in (b for b in blocks if b):
        text = _join_lines(block)
        continues = paras and (
            paras[-1].endswith("-")
            or (not paras[-1].rstrip().endswith(_TERMINAL) and text[:1].islower())
        )
        if continues:
            paras[-1] = _join(paras[-1], text)
        else:
            paras.append(text)
    paras += [_join_lines(note) for note in notes]
    return [_tidy(p) for p in paras]


def _join_lines(lines: list[str]) -> str:
    text = ""
    for line in lines:
        text = _join(text, line)
    return text


def _join(left: str, right: str) -> str:
    if not left:
        return right
    m = re.search(r"([A-Za-z]+)-$", left)
    if m:
        first = re.match(r"[A-Za-z]+", right)
        if first:
            vocab = library_word_counts()
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


def _core(tok: str) -> str:
    """A token's letters, lower-cased: what two scans are compared on."""
    return re.sub(r"[^A-Za-z']", "", tok).strip("'").lower()


def _real(tok: str) -> bool:
    c = _core(tok)
    vocab = library_word_counts()
    return bool(c) and all(vocab[p] >= MIN_REAL for p in c.split("'") if p)


def _spans_agree(mine: list[str], theirs: list[str]) -> bool:
    """May `theirs` replace `mine`, a stretch the scans split differently?

    Only when `mine` holds a non-word and `theirs` holds none — so a clean
    "himself" is never split into another scan's "him self" — and either the
    letters are the same and only the spacing differs ("ungo lliness" /
    "ungodliness"), or the stretches differ in length by a word at most ("dnst
    its" / "dread its").
    """
    if not theirs or all(_real(m) for m in mine) or not all(_real(t) for t in theirs):
        return False
    same_letters = "".join(map(_core, mine)) == "".join(map(_core, theirs))
    return same_letters or abs(len(mine) - len(theirs)) <= 1


def reconcile(primary: list[str], others: list[list[str]]) -> list[str]:
    """Correct `primary`'s misread words from independent scans of the same text.

    The whole sermon is aligned at once against each other scan, so a
    paragraph's first and last words are cross-checked like the rest. Where the
    scans disagree on a word, the primary's reading stands unless it is not a
    real word and the other scan's is; then the other scan's token is taken
    whole, punctuation and all ("Christy" → "Christ,"). Words are aligned on
    their letters, so a misread comma alone never moves the alignment. A
    stretch the scans split differently is replaced only inside one paragraph;
    paragraph breaks are the primary's.
    """
    toks = [_TOKEN.findall(p) for p in primary]
    # (paragraph, position) of every primary token, in reading order
    index = [(n, k) for n, para in enumerate(toks) for k in range(len(para))]
    for other in others:
        alt = _TOKEN.findall(" ".join(other))
        flat = [toks[n][k] for n, k in index]
        sm = difflib.SequenceMatcher(None, [_core(t) for t in flat], [_core(t) for t in alt], autojunk=False)
        spans = []  # (paragraph, first, last + 1, replacement), applied right to left
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "replace":
                continue
            mine, theirs = flat[i1:i2], alt[j1:j2]
            if i2 - i1 == j2 - j1:
                for (n, k), m, t in zip(index[i1:i2], mine, theirs, strict=True):
                    if not _real(m) and _real(t):
                        toks[n][k] = t
            elif index[i1][0] == index[i2 - 1][0] and _spans_agree(mine, theirs):
                n = index[i1][0]
                spans.append((n, index[i1][1], index[i2 - 1][1] + 1, theirs))
        for n, k1, k2, theirs in reversed(spans):
            toks[n][k1:k2] = theirs
        index = [(n, k) for n, para in enumerate(toks) for k in range(len(para))]
    return [" ".join(t) for t in toks]
