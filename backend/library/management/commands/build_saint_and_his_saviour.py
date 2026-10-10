"""Build Spurgeon's *The Saint and His Saviour* (1857) from four OCR witnesses.

The book is on neither CCEL nor Gutenberg, so the only clean public-domain
source is the Internet Archive — and there every scan is an OCR text layer.
Four of them, though, are scans of the SAME stereotype plates (Sheldon,
Blakeman & Co., New York, 1857, and the Sheldon & Co. reprint of 1859 from
those plates): page for page and line for line the same setting, scanned from
different copies in different libraries by different OCR runs. Their errors
are largely independent — one reads "Jesns", another "Jesus" — so this command
does not trust any one of them. It reflows each witness, aligns the other
three against a primary word by word, and lets a majority of witnesses
overrule the primary wherever it is outvoted. What survives that vote is then
repaired from the `_FIXES` table below, each entry settled by reading all four
witnesses at that spot.

Two things the vote cannot settle get their own passes. The older runs share
one OCR engine, so they share its blind spots (V read as Y, italic words, a
`"` fused to every capital W); a word the modern run never once produces is
repaired by a letter-confusion table (`_repair_word`), and opening quotes
before a W are taken from the modern run alone. What is left is the
`_FIXES` table, each entry settled against the page images.

The book: the author's Preface, then twelve chapters, each headed by a roman
numeral and an all-caps title over a scripture epigraph (kept as a
blockquote), and each closing with a short address "To the Unconverted
Reader" (kept as an `<h3>`). After the last comes the closing doxology (Rev.
1:5-6). About 150 footnotes — mostly the source of a quotation — sit at the
page foot under the printer's * † ‡ § ‖ ¶, restarting on every page; they are
paired with their marks page by page and set as lettered notes after an `<hr/>`
at the chapter's end (the `<sup>*</sup>` shape `unspoken-sermons` uses).
`_PAGE_NOTES` places the few the scans garble past pairing. Hymn stanzas keep
their lines (`<br/>`). Italics are lost, as in every OCR import.

Fixture-driven: `seed_books` creates it on the next deploy, resolving the
existing `charles-h-spurgeon` author from `authors.json`. Idempotent; no
`catalog.py` entry (a stray `import_archive` could only mangle it).

    DJANGO_DEBUG=true uv run python manage.py build_saint_and_his_saviour
    # offline, from saved <item>_djvu.txt files:
    DJANGO_DEBUG=true uv run python manage.py build_saint_and_his_saviour --source-dir DIR
"""

from __future__ import annotations

import difflib
import html as _html
import re
import statistics
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import (
    _BARE_NUM,
    _NON_LETTER,
    _WS,
    _is_header,
    fetch_text,
)
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "the-saint-and-his-saviour"
TITLE = "The Saint and His Saviour"
SUBTITLE = "The Progress of the Soul in the Knowledge of Jesus"
AUTHOR_SLUG = "charles-h-spurgeon"
PUBLICATION_YEAR = 1857
COVER_COLOR = "#7a3b2e"  # deep madder — house-style cover ground

#: The primary witness (its paragraphing and verse lines are kept) followed by
#: the three that vote with it. All four are the 1857 Sheldon, Blakeman plates.
PRIMARY = "sainthissaviour00spurrich"
WITNESSES = [
    PRIMARY,
    "sainthissaviouro00spur",
    "sainthissaviour00spur",
    "sainthissaviouro0000spur",
]
#: The one witness from a modern OCR engine; its errors differ in kind.
MODERN = "sainthissaviouro0000spur"
VOTERS = WITNESSES[1:]
_MODERN_INDEX = VOTERS.index(MODERN)

DESCRIPTION = (
    "Written over two busy years at the start of his London ministry, the young "
    "Spurgeon's book traces the soul's growing acquaintance with "
    "Christ — from the days when “we esteemed him not,” through "
    "conviction, longing, pardon and the joy of conversion, to love, trial, the "
    "seasons when Jesus seems to hide himself, and the secret of keeping "
    "communion with him. It is meant, as its preface says, for beginners: to "
    "comfort the mourner, confirm the weak, guide the wandering and reassure "
    "the doubting."
)

HOOK = "How does a soul come to know Jesus? The young Spurgeon traces the road, step by step."

ATTRIBUTION = (
    "Public domain — first published 1857. Text from four Internet Archive "
    "scans of the 1857 New York edition (Sheldon, Blakeman & Co.) and its "
    "reprints from the same plates (sainthissaviour00spurrich, "
    "sainthissaviouro00spur, sainthissaviour00spur, sainthissaviouro0000spur), "
    "reconciled word by word."
)

#: The twelve chapters, from the book's Contents. Order IS the reading order.
TITLES = [
    "The Despised Friend",
    "Faithful Wounds",
    "Jesus Desired",
    "Jesus Pardoning",
    "Joy at Conversion",
    "Complete in Christ",
    "Love to Jesus",
    "Love's Logic",
    "Jesus in the Hour of Trouble",
    "Jesus Hiding Himself",
    "The Causes of Apparent Desertion",
    "Communion Preserved",
]

#: Printed after Chapter XII on its own page, in capitals.
DOXOLOGY = (
    "Unto him that loved us, and washed us from our sins in his own blood, and "
    "hath made us kings and priests unto God and our Father; to him be glory "
    "and dominion, for ever and ever. Amen."
)
_DOXOLOGY_START = re.compile(r"^\W*UNTO\s+HIM\s+THAT\s+LOVED\b")

#: Every chapter closes with a short address headed, in capitals, "TO THE
#: UNCONVERTED READER." — the last one adds "WHO IS UNDER CONCERN OF SOUL."
ADDRESS = "To the Unconverted Reader"
ADDRESS_LAST = "To the Unconverted Reader Who Is under Concern of Soul"
_ADDRESS_KEY = "TOTHEUNCONVERTEDREADER"
#: A footnote line whose "*" the scan lost: a bare scripture reference
#: ("2 Cor. vii. 10, 11.").
_CITATION = re.compile(r"^\W{0,2}(?:[1-3]\s)?[A-Z][a-z]{1,5}\.?\s+[ivxlcIVXLC]+[.,]\s*\d[\d,\s\-—.]*$")


_TOKEN = re.compile(
    r"[A-Za-z0-9]+(?:'[A-Za-z]+)*(?:-[A-Za-z0-9]+(?:'[A-Za-z]+)*)*|—|\S"
)
_WORD = re.compile(r"[A-Za-z0-9]")
#: OCR renderings of an opening double quote in these scans: a doubled
#: apostrophe anywhere, an asterisk and a quote at the start of a line
#: ("*'  We esteemed him not"), a low-9 mark.
_QUOTE_GARBLE = re.compile(r"''|^\*['\"]|„")
_TERMINAL = (".", "!", "?", '"', "'", ":")
_NUMERAL_LINE = re.compile(r"^[IVXLCYTUMivxlcymigun|]{1,5}\.?$")
_NO_SPACE_BEFORE = set(",.;:!?)")

#: Footnote reference marks as the scans render them: the printer's * † ‡ § ‖,
#: and the OCR's readings of the dagger family as a lone f, t, i or j (none an
#: English word), "+", "{" or a backslash.
_MARK_TOKENS = {"*", "†", "‡", "§", "‖", "|", "+", "{", "}", "\\", "»", "$", "£", "J", "f", "t", "i", "j"}
#: The footnotes at a page's foot. The first on a page is always "*" (read as
#: "»" once); the rest open on a dagger-family mark.
_NOTE_FIRST = re.compile(r"^(?:\*|»)\s*[A-Za-z0-9\"]")


def _siglum(k: int) -> str:
    """The mark a chapter's k-th note wears: a, b, … z, aa, ab, ….

    The print restarts * † ‡ § ‖ ¶ on every page, which a chapter-end list
    cannot do — one chapter has 31 notes. Not digits: a numbered `<sup>` is
    stripped as residue on every deploy (`corrections.strip_footnote_markers`).
    """
    letters = "abcdefghijklmnopqrstuvwxyz"
    return letters[k] if k < 26 else letters[k // 26 - 1] + letters[k % 26]


# --------------------------------------------------------------------------- #
# Reading one witness
# --------------------------------------------------------------------------- #


def _normalize_line(line: str) -> str:
    line = line.replace("“", '"').replace("”", '"')
    line = line.replace("‘", "'").replace("’", "'")
    line = line.replace("—", " — ").replace("--", " — ")
    line = line.replace("¬", "-")  # a soft-hyphen glyph at line end
    line = re.sub(r"^\s*[•·]", "*", line)  # a footnote's leading * read as a bullet
    line = _QUOTE_GARBLE.sub('"', line.strip())
    return _WS.sub(" ", line).strip()


def _letters_key(text: str) -> str:
    return _NON_LETTER.sub("", text).upper()


def _caps_share(text: str) -> float:
    letters = _NON_LETTER.sub("", text)
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


_BOOK_KEY = _letters_key("THE SAINT AND HIS SAVIOUR")


def _is_page_mark(line: str, chapter_key: str) -> bool:
    """A page number or a running header (book title or chapter title)."""
    if _BARE_NUM.match(line) or _is_header(line):
        return True
    letters = _NON_LETTER.sub("", line)
    if _caps_share(line) >= 0.8 and len(letters) >= 8:
        key = _letters_key(line)
        # A header whose page number the scanner lost or misread.
        return _similar(key, _BOOK_KEY) >= 0.75 or _similar(key, chapter_key) >= 0.75
    return False


def _is_junk(line: str) -> bool:
    """Stray scanner marks: no letters, or a letter or two with no prose shape."""
    letters = _NON_LETTER.sub("", line)
    if not letters:
        return True
    return len(letters) <= 2 and not line.endswith((".", ",", ";", ":", "!", "?", '"'))


def _find_heads(lines: list[str]) -> list[int]:
    """Line index of each chapter's ALL-CAPS title, in order.

    A title is a digit-free, mostly-capitals line whose letters match the
    Contents title; running headers repeat the title but carry a page number,
    and the Contents sets the titles in mixed case, so the first match after
    the previous chapter is the head itself.
    """
    heads: list[int] = []
    start = 0
    for title in TITLES:
        key = _letters_key(title)
        for i in range(start, len(lines)):
            line = lines[i]
            if not line or re.search(r"\d", line) or _caps_share(line) < 0.7:
                continue
            if _similar(_letters_key(line), key) >= 0.8:
                heads.append(i)
                start = i + 1
                break
        else:
            raise CommandError(f"chapter head {title!r} not found — the scan changed.")
    return heads


class Para:
    """A run of printed lines: a paragraph (or the continuation of one across a
    page of footnotes), one footnote, or the address heading."""

    def __init__(self, kind: str, cont: bool = False):
        self.kind = kind          # "text" | "note" | "head"
        self.cont = cont          # continues the previous text paragraph
        self.lines: list[str] = []
        self.pages: list[int] = []


class Token:
    __slots__ = ("text", "space", "para", "line", "head", "note", "page")

    def __init__(self, text: str, space: bool):
        self.text = text
        self.space = space   # whitespace preceded it in the source
        self.para = False    # opens a paragraph
        self.line = False    # opens a printed line inside a verse paragraph
        self.head = False    # opens the sub-heading paragraph
        self.note = None     # id of the footnote line it belongs to
        self.page = 0

    def inherit(self, old: Token) -> None:
        self.note, self.page = old.note, old.page


def _tokens(text: str) -> list[tuple[str, bool]]:
    out = []
    for m in _TOKEN.finditer(text):
        space = m.start() == 0 or text[m.start() - 1].isspace()
        out.append((m.group(0), space))
    return out


class Witness:
    """One scan, cut into sections: the Preface, then the twelve chapters."""

    def __init__(self, raw: str, vocab: Counter, modern_vocab: Counter, *, modern: bool = False):
        self.lines = [_normalize_line(x) for x in raw.split("\n")]
        if modern:
            # The modern OCR reads an opening double quote as `“‘`.
            self.lines = [re.sub(r"\"'(?=\s*[A-Za-z])", '"', x) for x in self.lines]
        else:
            # The three older OCR runs read a capital W as `"W` — 77 to 93
            # times a scan, against 19 real quotes before a W that the modern
            # run sees. Drop ONE attached mark: a real quote survives as the
            # first of a doubled `""W` or a spaced `" "W`.
            self.lines = [x.replace('"W', "W") for x in self.lines]
        self.vocab = vocab
        self.modern_vocab = modern_vocab
        heads = _find_heads(self.lines)
        end = len(self.lines)
        for i in range(heads[-1], len(self.lines)):
            if _DOXOLOGY_START.match(self.lines[i]):
                end = i
                break
        else:
            raise CommandError("closing doxology not found — the scan changed.")
        pre = next(
            (i for i in range(heads[0]) if _letters_key(self.lines[i]) == "PREFACE"), None
        )
        if pre is None:
            raise CommandError("preface not found — the scan changed.")
        # The Contents follows the Preface: its heading is the first short
        # capitals line after it ("COKTEKTS" in one scan).
        contents = next(
            (
                i for i in range(pre + 1, heads[0])
                if 0 < len(self.lines[i]) < 20 and _similar(_letters_key(self.lines[i]), "CONTENTS") >= 0.6
            ),
            None,
        )
        if contents is None:
            raise CommandError("contents not found — the scan changed.")
        self.sections: list[tuple[str, list[str]]] = [("PREFACE", self.lines[pre + 1 : contents])]
        for n, h in enumerate(heads):
            stop = heads[n + 1] if n + 1 < len(heads) else end
            block = self.lines[h + 1 : stop]
            # A title set over two lines ("THE CAUSES OF APPARENT" /
            # "DESERTION."): drop the rest of it.
            key = _letters_key(TITLES[n])
            while block and (
                not block[0]
                or (_caps_share(block[0]) >= 0.9 and _letters_key(block[0]) and _letters_key(block[0]) in key)
            ):
                block = block[1:]
            # Drop the next chapter's numeral (a short roman-ish line at the very
            # end — "VIII.", or as mis-scanned "YIII.", "Mig", "TU."), never a
            # short closing line of prose or a note ("* Ps. li. 3.").
            while block and (not block[-1] or _NUMERAL_LINE.match(block[-1])):
                block = block[:-1]
            self.sections.append((_letters_key(TITLES[n]), block))

    def paragraphs(self, n: int) -> tuple[list[Para], float]:
        """Section n as Paras, in reading order (footnotes where they print),
        and the section's measure (median prose line length)."""
        key, block = self.sections[n]
        kind = []
        for ln in block:
            if not ln:
                kind.append("blank")
            elif _is_page_mark(ln, key):
                kind.append("page")
            elif _is_junk(ln):
                kind.append("junk")
            elif _caps_share(ln) >= 0.8 and len(ln) < 40 and _similar(
                _letters_key(ln)[: len(_ADDRESS_KEY)], _ADDRESS_KEY
            ) >= 0.6:
                kind.append("head")
            else:
                kind.append("text")
        # The heading's second line, in capitals ("WHO IS UNDER CONCERN OF SOUL").
        for i in range(1, len(kind)):
            prev = next((j for j in range(i - 1, -1, -1) if kind[j] != "blank"), None)
            if kind[i] == "text" and prev is not None and kind[prev] == "head" and _caps_share(block[i]) >= 0.9:
                kind[i] = "head"
        # Footnotes: the text lines between a page mark (or the address
        # heading, or the section's end) and the nearest line above it that
        # opens on "*". Notes are set in smaller type, wrap, and lose their
        # marks, so everything below that line is note; prose never opens a
        # line on a bare "*". Failing that, a bottom line that is a bare
        # scripture reference is a note whose "*" the scan lost.
        ends = [i for i, k in enumerate(kind) if k in ("page", "head")] + [len(block)]
        for i in ends:
            seen = 0
            j = i - 1
            while j >= 0 and kind[j] not in ("page", "head") and seen < 7:
                if kind[j] == "text":
                    seen += 1
                    if _NOTE_FIRST.match(block[j]):
                        for r in range(j, i):
                            if kind[r] == "text":
                                kind[r] = "note"
                        break
                j -= 1
            else:
                j = i - 1
                while j >= 0 and kind[j] in ("blank", "junk"):
                    j -= 1
                if j >= 0 and kind[j] == "text" and _CITATION.match(block[j]):
                    kind[j] = "note"

        text_lines = [ln for ln, k in zip(block, kind, strict=True) if k == "text"]
        width = statistics.median(len(x) for x in text_lines) if text_lines else 50

        paras: list[Para] = []
        cur: Para | None = None
        last = ""                  # the last prose line, across any notes
        gap_blank = gap_page = False
        page = 0
        prev_kind = ""
        for ln, k in zip(block, kind, strict=True):
            if k in ("blank", "junk"):
                gap_blank = gap_blank or k == "blank"
                continue
            if k == "page":
                if prev_kind != "page":   # a header and its page number: one turn
                    page += 1
                prev_kind = k
                gap_page = True
                continue
            prev_kind = k
            if k in ("note", "head"):
                if k == "note" and paras and paras[-1].kind == "note" and ln[:1].islower():
                    paras[-1].lines.append(ln)   # a note wrapped onto a second line
                    paras[-1].pages.append(page)
                    continue
                if k == "head" and paras and paras[-1].kind == "head" and cur is None:
                    paras[-1].lines.append(ln)
                    paras[-1].pages.append(page)
                    continue
                if cur is not None and cur.lines:
                    paras.append(cur)
                    cur = Para("text", cont=True) if k == "note" else None
                elif k == "head":
                    cur = None
                p = Para(k)
                p.lines, p.pages = [ln], [page]
                paras.append(p)
                if k == "head":
                    last = ""
                    gap_blank = gap_page = False
                else:
                    gap_page = True
                continue
            if last and (gap_blank or gap_page):
                if gap_page:
                    # A page turn: the indent is lost, so a paragraph ends there
                    # only when the last line both closes a sentence and stops
                    # short of the measure.
                    brk = last.rstrip().endswith(_TERMINAL) and len(last) < 0.85 * width
                else:
                    # A blank inside a hymn (the djvu text leaves one where the
                    # print indents a line) is not a paragraph's end: a stanza
                    # line that has not closed its sentence runs on.
                    in_verse = cur is not None and all(len(x) < 0.85 * width for x in cur.lines)
                    brk = not (in_verse and re.search(r"[A-Za-z,;\-]$", last.rstrip()))
                if brk:
                    if cur is not None and cur.lines:
                        paras.append(cur)
                    cur = None
            if cur is None:
                cur = Para("text")
            cur.lines.append(ln)
            cur.pages.append(page)
            last = ln
            gap_blank = gap_page = False
        if cur is not None and cur.lines:
            paras.append(cur)
        return paras, width

    def join_lines(self, lines: list[str]) -> list[tuple[str, bool, int]]:
        """Tokens of a run of lines: (text, space_before, line_index)."""
        out: list[tuple[str, bool, int]] = []
        carry = ""
        for li, raw in enumerate(lines):
            ln = raw
            if carry:
                m = re.match(r"([A-Za-z]+)(.*)", ln)
                if m:
                    ln = self._dehyphen(carry, m.group(1)) + m.group(2)
                else:
                    ln = carry + "- " + ln
                first_is_new_line = False
                carry = ""
            else:
                first_is_new_line = True
            hm = re.search(r"([A-Za-z]+)-$", ln)
            if hm:
                carry = hm.group(1)
                ln = ln[: hm.start()].rstrip()
                if not ln:
                    continue
            toks = _tokens(ln)
            if first_is_new_line and toks and out and self._unbroken(out[-1][0], toks[0][0]):
                # A word broken over the line with its hyphen lost ("recollec" /
                # "tions"): both halves are rare, the whole is common.
                out[-1] = (out[-1][0] + toks[0][0], out[-1][1], out[-1][2])
                toks = toks[1:]
                first_is_new_line = False
            for k, (t, s) in enumerate(toks):
                out.append((t, s or k == 0, li if (first_is_new_line and k == 0) else -1))
        if carry:
            out.append((carry, True, -1))
        return out

    def _dehyphen(self, left: str, right: str) -> str:
        """Rejoin a word broken over a line. Keep the hyphen for a compound:
        one the scans print hyphenated mid-line more often than solid, or —
        when neither form occurs elsewhere — two common words ("snow-wreath")
        rather than the halves of one ("recollec-tions")."""
        v = self.vocab
        hyph, solid = v[f"{left}-{right}".lower()], v[(left + right).lower()]
        if hyph != solid:
            return f"{left}-{right}" if hyph > solid else left + right
        # Whole words by the modern run's count, which (unlike the older runs)
        # never drops a line-end hyphen and so never counts a half as a word.
        m = self.modern_vocab
        if right.lower() in _SUFFIXES:
            return left + right
        if m[left.lower()] >= 3 and m[right.lower()] >= 3 and len(left) > 2 and len(right) > 2:
            return f"{left}-{right}"
        return left + right

    def _unbroken(self, a: str, b: str) -> bool:
        if not (a.isalpha() and b.isalpha() and b[:1].islower()):
            return False
        v = self.vocab
        return v[(a + b).lower()] >= 4 and (v[a.lower()] < 3 or v[b.lower()] < 3)

    def stream(self, n: int) -> list[tuple[str, bool]]:
        out: list[tuple[str, bool]] = []
        for p in self.paragraphs(n)[0]:
            out.extend((t, s) for t, s, _ in self.join_lines(p.lines))
        return out


def _vocab(texts: list[str]) -> Counter:
    words: Counter = Counter()
    for raw in texts:
        broken = False
        for ln in raw.split("\n"):
            ln = _normalize_line(ln)
            if not ln:
                continue
            # Exclude both halves of a word broken over a line: they are the
            # evidence in question, not words.
            if broken:
                ln = re.sub(r"^[A-Za-z]+", "", ln)
            broken = bool(re.search(r"[A-Za-z]-$", ln))
            ln = re.sub(r"[A-Za-z]+-$", "", ln)
            for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", ln):
                words[w.lower()] += 1
    return words


#: A line-break half that is an ending, not a word, however often the scans
#: read it alone ("obey-" / "ing").
_SUFFIXES = {"ing", "ings", "est", "less", "ness", "ed", "ly", "ment", "ful", "mary"}

#: Letter confusions of these scans, tried one at a time on a word no
#: witness agrees on — "Yery" (V read as Y in all three older runs), "ISTow",
#: "tliee", "Eedeemer", "rny".
_CONFUSIONS = [
    ("Y", "V"), ("IST", "N"), ("E", "R"), ("K", "R"), ("k", "r"),
    ("li", "h"), ("tli", "th"), ("rn", "m"), ("ii", "u"), ("ii", "n"), ("ij", "n"),
    ("cl", "d"), ("c", "e"), ("b", "h"), ("u", "n"), ("n", "u"),
]


def _repair_word(word: str, vocab: Counter, modern: Counter) -> str:
    """A token the modern scan never reads, one confusion away from a common
    word it does read, becomes that word.

    The modern engine's errors are of another kind from the older three, so a
    word it never once produces in the whole book — "Yery", "tliee" — is a
    misreading the older runs share, which the vote could not overrule."""
    if not word.isalpha() or len(word) < 3 or modern[word.lower()]:
        return word
    best, best_n = word, 0
    for bad, good in _CONFUSIONS:
        start = 0
        while (i := word.find(bad, start)) >= 0:
            cand = word[:i] + good + word[i + len(bad):]
            n = modern[cand.lower()]
            if n and vocab[cand.lower()] >= 3 and n > best_n:
                best, best_n = cand, n
            start = i + 1
    return best


def _repair_glyph(word: str, nxt: str) -> str | None:
    """A glyph confusion no vocabulary can settle, or None.

    A capital O read as a zero ("0 love, thou bottomless abyss!"), and a
    roman numeral's l read as I ("Ps. Ixxxviii. 15", "Iv. 4")."""
    if word == "0" and nxt[:1].isalpha():
        return "O"
    if re.fullmatch(r"I[xvi]+", word):
        return "l" + word[1:]
    return None


def _rejoin(toks: list[Token], modern: Counter, vocab: Counter) -> list[Token]:
    """Close a word the older runs split with a space where a line-end hyphen
    was lost ("repent ance", "cer tainly"): the modern run reads the whole
    word somewhere in the book and never reads one of the halves — or reads
    neither half, and some scan reads the whole."""
    out: list[Token] = []
    for t in toks:
        if out and t.space and not t.para and t.note == out[-1].note:
            a, b = out[-1].text, t.text
            halves = modern[a.lower()], modern[b.lower()]
            if a.isalpha() and b.isalpha() and b[0].islower() and (
                (modern[(a + b).lower()] and not all(halves))
                or (vocab[(a + b).lower()] >= 2 and not any(halves))
            ):
                out[-1].text = a + b
                continue
        out.append(t)
    return out


# --------------------------------------------------------------------------- #
# Voting
# --------------------------------------------------------------------------- #


def _boundary_map(p: list[str], w: list[str]) -> dict[int, int | None]:
    """Primary token boundary → witness token boundary, where the alignment
    pins one down (inside or at the edge of a matching run)."""
    sm = difflib.SequenceMatcher(None, p, w, autojunk=False)
    bmap: dict[int, int | None] = {}
    for i1, j1, size in sm.get_matching_blocks():
        for t in range(size + 1):
            i, j = i1 + t, j1 + t
            if i in bmap and bmap[i] != j:
                bmap[i] = None
            else:
                bmap[i] = j
    return bmap


def _restore_w_quotes(toks: list[Token], modern: list[str]) -> list[Token]:
    """Put back an opening quote before a W-word that only the modern run
    reads (the older runs' `"W` is erased as a misread capital)."""
    sm = difflib.SequenceMatcher(None, [t.text for t in toks], modern, autojunk=False)
    inserts: set[int] = set()
    for op, i1, _i2, j1, j2 in sm.get_opcodes():
        if op == "insert" and modern[j1:j2] == ['"'] and i1 < len(toks) and toks[i1].text[:1] == "W":
            inserts.add(i1)
    out: list[Token] = []
    for k, t in enumerate(toks):
        if k in inserts:
            q = Token('"', True)
            q.inherit(t)
            q.para, t.para = t.para, False
            q.line, t.line = t.line, False
            out.append(q)
        out.append(t)
    return out


def _w_quote(seq: tuple[str, ...]) -> tuple[str, ...] | None:
    """`seq` with each opening quote before a W-word dropped, or None if it
    has none — what the older runs make of the modern run's reading."""
    out, dropped = [], False
    for k, t in enumerate(seq):
        if t == '"' and k + 1 < len(seq) and seq[k + 1][:1] == "W":
            dropped = True
            continue
        out.append(t)
    return tuple(out) if dropped else None


def _known(seq: tuple[str, ...], vocab: Counter) -> int:
    return sum(1 for t in seq if not _WORD.match(t) or vocab[t.lower()] >= 3)


def _vote(
    primary: list[Token], streams: list[list[tuple[str, bool]]], vocab: Counter
) -> tuple[list[Token], int]:
    """Replace each primary reading that a majority of witnesses outvotes.

    Anchors are token boundaries that at least two other witnesses pin down;
    between consecutive anchors every witness offers its reading, and the
    commonest wins if at least two witnesses hold it and it beats the
    primary's own count (a tie goes to the reading made of real words)."""
    p = [t.text for t in primary]
    others = [[t for t, _ in w] for w in streams]
    spaces = [[s for _, s in w] for w in streams]
    maps = [_boundary_map(p, w) for w in others]
    anchors = [
        b for b in range(len(p) + 1)
        if b in (0, len(p)) or sum(1 for m in maps if m.get(b) is not None) >= 2
    ]
    out: list[Token] = []
    changed = 0
    for a, b in zip(anchors, anchors[1:], strict=False):
        mine = tuple(p[a:b])
        votes = Counter({mine: 1})
        where: dict[tuple[str, ...], tuple[int, int]] = {}
        modern = None
        for wi, (w, m) in enumerate(zip(others, maps, strict=True)):
            ja, jb = m.get(a), m.get(b)
            if ja is None or jb is None or jb < ja:
                continue
            cand = tuple(w[ja:jb])
            if len(cand) > len(mine) + 6:
                continue  # a misalignment, not a reading
            votes[cand] += 1
            where.setdefault(cand, (wi, ja))
            if wi == _MODERN_INDEX:
                modern = cand
        best, n = votes.most_common(1)[0]
        take = None
        outvoted = best != mine and n >= 2 and (
            n > votes[mine] or (n == votes[mine] and _known(best, vocab) > _known(mine, vocab))
        )
        if outvoted:
            take = best
        elif (
            n == 1 and modern and modern != mine
            and _known(modern, vocab) == len(modern) and _known(mine, vocab) < len(mine)
        ):
            # No two witnesses agree. The modern engine's errors are of another
            # kind from the older three, so take its reading when it is made of
            # real words and the primary's is not.
            take = modern
        # The older runs' `"W` was erased as a misread capital (see Witness),
        # so before a W only the modern run can see a real opening quote.
        chosen = take if take is not None else mine
        if modern and modern != chosen and _w_quote(modern) == chosen:
            take = modern
        seg = primary[a:b]
        if take is None or (not take and any(
            t.para or t.head or t.line or (t.text.isalpha() and len(t.text) > 1) for t in seg
        )):
            out.extend(seg)
            continue
        changed += 1
        if not take:
            continue  # the primary's stray marks: no witness reads them
        wi, ja = where[take]
        new = [Token(t, spaces[wi][ja + k]) for k, t in enumerate(take)]
        new[0].space = seg[0].space
        new[0].para = seg[0].para
        for k, tok in enumerate(new):
            tok.inherit(seg[min(k, len(seg) - 1)])
        for k, old in enumerate(seg):
            if old.line:
                new[min(k, len(new) - 1)].line = True
            if old.head:
                new[0].head = True
        out.extend(new)
    return out, changed


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_GLUE = "\x00"
_EDGE = "\x03"


def _render(toks: list[Token], marks: dict[int, str] | None = None) -> str:
    """Tokens → text, with the era's loose spacing normalised.

    `marks` maps a token's index to the placeholder of the footnote it calls
    ("" drops the token); `_esc` turns the placeholder into `<sup>`.
    """
    marks = marks or {}
    out = ""
    open_double = False
    n = len(toks)
    for k, t in enumerate(toks):
        s = t.text
        if k in marks:
            if marks[k]:
                out = out.rstrip(" ") + f"\x01{marks[k]}\x02"
            continue
        prev = toks[k - 1].text if k else None
        nxt = toks[k + 1].text if k + 1 < n else None
        if s == '"':
            if prev is None or prev in ("(", "—"):
                opener = True
            elif k + 1 in marks:
                opener = False  # a footnote mark follows only a closing quote
            elif nxt is None or nxt in _NO_SPACE_BEFORE or nxt == "—":
                opener = False
            elif prev in _NO_SPACE_BEFORE or _WORD.match(prev) or prev in ('"', "'"):
                opener = not open_double
            else:
                opener = True
            open_double = opener
            out = out.replace(_GLUE, "")
            if opener:
                if out and not out.endswith((" ", "\n", "—", "(")):
                    out += " "
                out += s + _GLUE
            else:
                out = out.rstrip(" ") + s
            continue
        glue = out.endswith(_GLUE)
        out = out.replace(_GLUE, "")
        if t.line and out:
            out = out.rstrip(" ") + "\n" + s
        elif not out:
            out = s
        elif s in _NO_SPACE_BEFORE or s == "—":
            out = out.rstrip(" ") + s
        elif glue or out.endswith(("—", "(", "\n")) or (s == "'" and not t.space):
            out += s
        elif out.endswith("'") and len(out) >= 2 and out[-2] in " \n—":
            out += s  # after an opening single quote
        else:
            out += " " + s
    return out.replace(_GLUE, "").strip()


def _esc(text: str) -> str:
    text = _html.escape(text, quote=False)
    text = re.sub(r"\x01(.*?)\x02", r"<sup>\1</sup>", text)
    return text.replace("\n", "<br/>")


def _fix_dropcap(text: str) -> str:
    """The chapter's first word is set in capitals ("THE death in sin")."""
    m = re.match(r'^(["\']?)([A-Z]{2,})\b', text)
    if m:
        text = m.group(1) + m.group(2).capitalize() + text[m.end():]
    return text


def _is_verse(lines: list[str], width: float) -> bool:
    if len(lines) < 2:
        return False
    starts = all(re.match(r'^["\']?\s*[A-Z]', ln) for ln in lines)
    return starts and max(len(ln) for ln in lines) < 0.85 * width


def _split_notes(toks: list[Token]) -> list[list[Token]]:
    """One footnote line → its notes (a line can carry two or three)."""
    notes: list[list[Token]] = []
    for k, t in enumerate(toks):
        lead = k == 0 or (
            t.text in _MARK_TOKENS and k + 1 < len(toks)
            and (toks[k + 1].text[:1].isupper() or toks[k + 1].text[:1].isdigit())
            and k > 0 and toks[k - 1].text in (".", ",", ";")
        )
        if lead:
            notes.append([])
        if not (lead and t.text in _MARK_TOKENS):
            notes[-1].append(t)
    return [n for n in notes if n]


#: Marks that only ever CONTINUE a run already glued to a reference mark: the
#: doubled sigla (** †† §§ read as "ff", "tt") and the scanner's readings of
#: ¶ and ‖.
_MARK_TAIL = _MARK_TOKENS | {"ff", "tt", "T", "^", "%", "|"}


def _mark_runs(body: list[Token]) -> list[list[int]]:
    """Footnote reference marks in the body, each as its run of tokens.

    Not a mark: an omission "* * *" (spaced asterisks), or a roman "i" in a
    reference ("Sol. Song, i. 4")."""
    runs: list[list[int]] = []
    i, n = 0, len(body)
    while i < n:
        t = body[i]
        nxt = body[i + 1] if i + 1 < n else None
        prv = body[i - 1] if i else None
        if t.text not in _MARK_TOKENS:
            i += 1
            continue
        if t.text == "*" and ((nxt and nxt.text == "*" and nxt.space) or (prv and prv.text == "*" and t.space)):
            i += 1
            continue
        if t.text == "i" and nxt and nxt.text in (".", ","):
            i += 1
            continue
        j = i + 1
        while j < n and body[j].text in _MARK_TAIL and not body[j].space:
            j += 1
        runs.append(list(range(i, j)))
        i = j
    return runs


#: Pages whose marks or notes the scans garble past pairing by order: each
#: note is given with the text its mark follows, read across all four scans.
#: Key: (section, page within section); section 0 is the Preface.
_PAGE_NOTES: dict[tuple[int, int], list[tuple[str, str]]] = {
    # Burton on the wounded conscience (Anatomy of Melancholy).
    (2, 6): [
        ("because of thine indignation.'", "Ps. cii. 6, 10; lv. 4."),
        ("all manner of meat.'", "Ps. cvii. 18."),
        ("the grief of heart,'", "Ps. xxxviii. 8."),
        ("as David did, as Job did.", "Job xx. 3, 21, 22, &c."),
    ],
    (2, 7): [
        ("as Wierus writes,", "De Lamiis, lib. iii. c. 7."),
        # The print reads "Deut. xxvii.", which has 26 verses; "the sight of
        # thine eyes which thou shalt see" is Deut. xxviii. 65-67.
        ("and fear of heart.\"", "Deut. xxviii. 65, 66."),
    ],
    (3, 21): [
        ("humility is the way to glory.\"", "Ephr. Udall's Sermons."),
        ("had they already attained it.", "Seneca de Ira, lib. iii. c. 36."),
        ("very beasts for folly.", "Ps. lxxiii. 22."),
    ],
    (5, 38): [
        ("glory in their tribulations also;'", "Rom. v. 1, 3."),
        ("unspeakable and full of glory.'\"", "1 Pet. i. 5, 6, 8."),
    ],
    (9, 17): [
        ("and to spite and mock the devil.\"", "Luther, in his Table-talk."),
        ("we share in the spoil.", "1 Sam. xxx. 24."),
    ],
    (9, 22): [
        ("for then he was obeying to the death\"", "Goodwin's Child of Light, &c."),
    ],
    (11, 7): [
        ("ready to die from their youth up,\"", "Ps. lxxxviii. 15."),
        ("are wiser than he in others.", "1 Kings, iv. 31."),
        ("how to encamp in the wilderness,", "Num. x. 31."),
    ],
    # A quotation that sets a reference after nearly every clause.
    (11, 18): [
        ("and counteth us as his enemies;", "Job xix. 11."),
        ("our secret sins in the light of his countenance;", "Ps. xc. 8."),
        ("and our sin is before us continually;", "Ps. li. 3."),
        ("he maketh our strength to fail;", "Lam. i. 14."),
        ("the iniquities of our youth,", "Job xiii. 26."),
        ("our wounds stink and are corrupt;", "Ps. xxxviii. 3, 5, 7."),
        ("it melteth in the midst of our bowels;", "Ps. xxii. 14."),
        ("our bones are parched like an hearth,", "Ps. cii. 3."),
        ("so heavy is his hand upon us night and day.", "Ps. xxxii. 4."),
        ("we roar like bears, and mourn like doves;", "Isa. lix. 11, 12."),
    ],
    (11, 19): [
        ("he visiteth us every morning,", "Job vii. 18."),
        ("he shutteth out our prayer,", "Lam. iii. 8."),
        ("and is even angry against it,", "Ps. lxxx. 4."),
        ("that he will not hear;", "Isa. lix. 2."),
    ],
    (12, 0): [
        ("that ye have one to another?\"", "Luke xxiv. 17."),
    ],
}


def _fix_note(text: str) -> str:
    """A note's own OCR residue (they are set in small type, and only voted)."""
    # A reference's points read as hyphens: "Ps- cvii- 18-".
    text = re.sub(r"(?<=[A-Za-z0-9])\s*-(?=\s|$)", ".", text)
    return _WS.sub(" ", text).strip()


#: Residual OCR damage the vote cannot reach — every witness agrees on the
#: wrong reading, or no two agree on the right one. Each pair was settled by
#: reading all four scans at that place. Applied in order to the chapter HTML.
_FIXES: list[tuple[str, str]] = [
    # --- Epigraphs: an opening quote no scan reads, a figure misread, and the
    # small-capital book names set in capitals.
    ('<blockquote><p>But they constrained him', '<blockquote><p>"But they constrained him'),
    ('—Ps. xxx. Y.', '—Ps. xxx. 7.'),
    ('—PROV. xxvii. 6.', '—Prov. xxvii. 6.'),
    ('—LUKE xxiv. 29.', '—Luke xxiv. 29.'),
    # --- Words the older scans share a misreading of, often in italic.
    ("nor could we saj,", "nor could we say,"),
    ("Master had been in this milage", "Master had been in this village"),
    ('He says:—"Hove them that love me', 'He says:—"I love them that love me'),
    ("The snowwreath of satisfaction", "The snow-wreath of satisfaction"),
    ("forsake the throne? ~ No;", "forsake the throne? No;"),
    ("mingled with such tears, and \\ v ith those", "mingled with such tears, and with those"),
    ("called to see me long ago / for surely", "called to see me long ago; for surely"),
    ("be con strained to do likewise", "be constrained to do likewise"),
    ("endured our ob stinacy,", "endured our obstinacy,"),
    ("all saved persons have Keen wounded", "all saved persons have been wounded"),
    ("Terror unique tremor", "Terror ubique tremor"),
    ("in scirpo quazritantes", "in scirpo quæritantes"),
    ("come upon me, &amp; c., at death's door.", "come upon me, &amp;c., at death's door."),
    ("undique terror: tears, terrors,", "undique terror: 'tears, terrors,"),
    ("for the grief of heart,';): as David did", "for the grief of heart,' as David did"),
    ("an excellent test may le found", "an excellent test may be found"),
    ("Natural conscience may ~ be distinguished", "Natural conscience may be distinguished"),
    ("with our own capabilities / then indeed", "with our own capabilities; then indeed"),
    ("a strong desire to seek his lace,", "a strong desire to seek his face,"),
    ("who had mary mock repentances", "who had many mock repentances"),
    ("Every tliief loves honesty", "Every thief loves honesty"),
    ("give jour assent to this", "give your assent to this"),
    ("the duty of selfexamination,", "the duty of self-examination,"),
    ("loving dealings byand bye.", "loving dealings by and bye."),
    ("manifestations; and yet-with all this,", "manifestations; and yet—with all this,"),
    ("shine on the back-slider while", "shine on the backslider while"),
    ("attributes of his God-head,", "attributes of his Godhead,"),
    ("\"A certain noble-man had", "\"A certain nobleman had"),
    ("Me, of sinners chief—forgive /\"", "Me, of sinners chief—forgive!\""),
    ("where I might find Him / \"Once,", "where I might find Him!\" Once,"),
    ("or the cata comb,", "or the catacomb,"),
    ("Desire o' erleapeth space;", "Desire o'erleapeth space;"),
    ("I have su. ely heard Ephraim", "I have surely heard Ephraim"),
    ("very beasts for folly 4 Like men", "very beasts for folly. Like men"),
    ("swell its floods. 4rood morality,", "swell its floods. Good morality,"),
    ("HeavVs never deaf,", "Heav'n's never deaf,"),
    ("when all things dery thee", "when all things deny thee"),
    ("obtain peace and ete nal life.", "obtain peace and eternal life."),
    ("\"Let the wicke 1 forsake his way,", "\"Let the wicked forsake his way,"),
    ("whole floods of harm) ny.", "whole floods of harmony."),
    ("It was weddingday with our soul,", "It was wedding-day with our soul,"),
    ("the captivity ofZion,", "the captivity of Zion,"),
    ("<p>' O love, thou bottomless abyss!", "<p>\"O love, thou bottomless abyss!"),
    ("power of novelty in everydaylife,", "power of novelty in every-day life,"),
    ("were the sumtotal of Christian", "were the sum-total of Christian"),
    ("Mr. Readyto-halt;", "Mr. Ready-to-halt;"),
    ("Mr. Feeblemind;", "Mr. Feeble-mind;"),
    ("in the time of con-motion that we", "in the time of conviction that we"),
    ("true religion to le a miserable thing", "true religion to be a miserable thing"),
    ("they are said to 'rejoice greatly and 'with joy", "they are said to 'rejoice greatly,' and 'with joy"),
    # The Greek and the Wycliffe black-letter, which no scan reads.
    ("The original word, appaf3c,) v, seems", "The original word, αρραβων, seems"),
    ("the whole of Tre-nvb / pw / zei'oj.", "the whole of πεπληρωμένοι."),
    ("\"QUtfc v ben filltfr in $ nm.\"", "\"And ȝe ben fillid in Hym.\""),
    ("II. Ye aee fully supplied in Him.", "II. Ye are fully supplied in Him."),
    ("do we feel want of strength f Is he not", "do we feel want of strength? Is he not"),
    ("imputation. ~ No; though", "imputation. No; though"),
    ("He will give us knowledge / He can open", "He will give us knowledge; He can open"),
    ("the fields of knowledge / let us separate", "the fields of knowledge; let us separate"),
    ("\"It is enough—Fm filled to the brim\"", "\"It is enough—I'm filled to the brim\""),
    ("the believer's 'all in all.' 1\"", "the believer's 'all in all.'\""),
    ("\"COMPLETE ra HIM.\"", "\"COMPLETE IN HIM.\""),
    ("shoots of love to hirt and desire", "shoots of love to him and desire"),
    ("our acts unkind. Wo would sooner", "our acts unkind. We would sooner"),
    ("content itself with litties:", "content itself with littles:"),
    ("pain less painful than en joyment.", "pain less painful than enjoyment."),
    ("in the Beloved / and we humbly crave", "in the Beloved; and we humbly crave"),
    ("the more complete will bo our idea", "the more complete will be our idea"),
    ("her fullgrown son.", "her full-grown son."),
    ("than the newborn Christian", "than the new-born Christian"),
    ("are opened. Yinet", "are opened. Vinet"),
    ("name of the Lord shall ~ be saved.", "name of the Lord shall be saved."),
    ("I. THE VALLEY OF BAG A.", "I. THE VALLEY OF BACA."),
    ("the Latin Yulgate,", "the Latin Vulgate,"),
    ("in the bloodbesprinkled way.", "in the blood-besprinkled way."),
    ("we share in the spoii.", "we share in the spoil."),
    ("faithful over all oui failures", "faithful over all our failures"),
    ("The great Eeformer said,", "The great Reformer said,"),
    ("of it are phut out from", "of it are shut out from"),
    ("when not in cognosci f it may have", "when not in cognosci; it may have"),
    ("why hast thou forsaken me (when as great", "why hast thou forsaken me? (when as great"),
    ("about his saints. 'The Lord of hosts", "about his saints. \"The Lord of hosts"),
    ("I have fought the good light;", "I have fought the good fight;"),
    ("and thou h'ndest thy profession", "and thou findest thy profession"),
    ("If the presence of Jesus ~ be not felt", "If the presence of Jesus be not felt"),
    ("make it a well.\" &amp; c.", "make it a well.\" &amp;c."),
    ("make it a well,\" &amp; c.", "make it a well,\" &amp;c."),
    ("will dig a well,\" &amp; c.", "will dig a well,\" &amp;c."),
    ("is peculiarly lusy;", "is peculiarly busy;"),
    ("no meat. \"\" Instead of sweet smell", "no meat.\" \"Instead of sweet smell"),
    ("Lest the green firtree should", "Lest the green fir-tree should"),
    ("Christ's presence is nevermore acceptable", "Christ's presence is never more acceptable"),
    ("favour from us, kindletli his anger", "favour from us, kindleth his anger"),
    ("he maketh our strenth to fail;", "he maketh our strength to fail;"),
    ("Such is the strengh of love", "Such is the strength of love"),
    ("are corrupt; T our veins", "are corrupt; our veins"),
    ("upon us night and day. ^ Then cry", "upon us night and day. Then cry"),
    ("is even angry against it,:): because", "is even angry against it, because"),
    ("encamp in the wilderness, ^: and so", "encamp in the wilderness, and so"),
    ("a melancholy temper ^ that always", "a melancholy temper, that always"),
    ("they are welladapted to thine", "they are well-adapted to thine"),
    ("the storm. The pro mise,", "the storm. The promise,"),
    ("It is not our eve on him", "It is not our eye on him"),
    ("tottering church of Home,", "tottering church of Rome,"),
    ("his portion ot treasure", "his portion of treasure"),
    ("This he did to &gt; ry their affection.", "This he did to try their affection."),
    ("any kind of sinful dissimil ation.", "any kind of sinful dissimulation."),
    ("So lung as we put our lips", "So long as we put our lips"),
    ("the sweet consump tion of cares,", "the sweet consumption of cares,"),
    ("which our Lord allows? ~ No—", "which our Lord allows? No—"),
    ("lies down in a led of coals", "lies down in a bed of coals"),
    ("<br/>Kecline our weary heads upon", "<br/>Recline our weary heads upon"),
    ("\"' Twas you, my sins,", "\"'Twas you, my sins,"),
    # "he" read as "lie", "be" as "he", in all three older scans.
    ("nor will lie think them too fallen", "nor will he think them too fallen"),
    ("\"Let none escape;\" lie will cut up", "\"Let none escape;\" he will cut up"),
    ("so doth lie bestow his favours", "so doth he bestow his favours"),
    ("he can never say that lie is complete;", "he can never say that he is complete;"),
    ("And is lie not false who serves", "And is he not false who serves"),
    ("we shall he obedient to his commands", "we shall be obedient to his commands"),
    ("we shall not he content until", "we shall not be content until"),
    ("wisdom, love, aud power of God", "wisdom, love, and power of God"),
    # Quotation marks the older scans set on the wrong side of a space.
    ("being 'born in sin, and shapen in iniquity, \"these", "being \"born in sin, and shapen in iniquity,\" these"),
    ("as \"God's vicegerent,' 7 styling", "as \"God's vicegerent,\" styling"),
    ("Be of good cheer; for\" He who walked", "Be of good cheer; for \"He who walked"),
    ("stay their hand and say,\" It is enough, \"for daily", "stay their hand and say, \"It is enough,\" for daily"),
    ("for their rites\" could never make the comers thereunto perfect; \"but this", "for their rites \"could never make the comers thereunto perfect;\" but this"),
    ("as Paul did,\" For me to live is Christ. \"A man", "as Paul did, \"For me to live is Christ.\" A man"),
    ("has indeed\" entered into rest. \"To him", "has indeed \"entered into rest.\" To him"),
    ("down in a bed of coals \"The absence", "down in a bed of coals.\" \"The absence"),
    ("to their windows * and when", "to their windows; and when"),
    ("guilt oppress' d?", "guilt oppress'd?"),
    ("eyes are darken' d with", "eyes are darken'd with"),
    # --- The notes.
    ("Rev. Joseph Irons, CamberwelL", "Rev. Joseph Irons, Camberwell."),
    ("Sours Implantation, by T. Hooker.", "Soul's Implantation, by T. Hooker."),
    ("Mai. iii. 16, 17.", "Mal. iii. 16, 17."),
    # A printer's reference that cannot exist (Proverbs has thirty-one
    # chapters): "I thought on my ways, and turned my feet unto thy
    # testimonies" is Ps. cxix. 59. (Deut. xxviii is the same case, set in
    # _PAGE_NOTES.)
    ("Prov. cix. 59.", "Ps. cxix. 59."),
]


def build_chapters(texts: dict[str, str], log=print, *, strict: bool = True) -> list[tuple[str, str]]:
    """The thirteen sections as (title, html). `strict=False` reports what a
    real build refuses — a stale fix, an unplaced note — instead of raising,
    for working on the tables."""

    def fail(msg: str) -> None:
        if strict:
            raise CommandError(msg)
        log(f"  !! {msg}")

    vocab = _vocab(list(texts.values()))
    repairs: Counter = Counter()
    modern_vocab = _vocab([texts[MODERN]])
    readers = {
        k: Witness(v, vocab, modern_vocab, modern=(k == MODERN)) for k, v in texts.items()
    }
    prim = readers[PRIMARY]
    fixes_used: Counter = Counter()
    chapters: list[tuple[str, str]] = []
    for n, title in enumerate(["Preface", *TITLES]):
        paras, width = prim.paragraphs(n)
        toks: list[Token] = []
        note_id = 0
        for p in paras:
            verse = p.kind == "text" and _is_verse(p.lines, width)
            joined = prim.join_lines(p.lines)
            for k, (t, s, li) in enumerate(joined):
                tok = Token(t, s)
                tok.para = k == 0 and not p.cont and p.kind in ("text", "head")
                tok.head = p.kind == "head"
                tok.line = verse and li > 0
                tok.page = p.pages[li] if li >= 0 else (toks[-1].page if toks else 0)
                if p.kind == "note":
                    tok.note = note_id
                toks.append(tok)
            if p.kind == "note":
                note_id += 1
        # Sentinels at both ends, so that a mark one scan reads before the
        # first word (an epigraph's opening quote) or after the last falls
        # inside a voted segment instead of outside every one.
        start, end = Token(_EDGE, True), Token(_EDGE, True)
        start.para = True
        edge = [(_EDGE, True)]
        others = [edge + readers[name].stream(n) + edge for name in VOTERS]
        voted, changed = _vote([start, *toks, end], others, vocab)
        voted = [t for t in voted if t.text != _EDGE]
        if voted and not voted[0].para:
            voted[0].para = True
        voted = _restore_w_quotes(voted, [t for t, _ in others[_MODERN_INDEX]])
        # A page turn the primary misread as a paragraph's end: the voted text
        # runs on mid-sentence into a lowercase word.
        for k in range(1, len(voted)):
            t, prev = voted[k], voted[k - 1]
            if (t.para and not t.head and not prev.head and prev.note is None and t.note is None
                    and (prev.text in (",", ";") or prev.text[-1:].isalpha()) and t.text[:1].islower()):
                t.para = False
        voted = _rejoin(voted, modern_vocab, vocab)
        for k, t in enumerate(voted):
            nxt = voted[k + 1].text if k + 1 < len(voted) else ""
            fixed = _repair_glyph(t.text, nxt) or _repair_word(t.text, vocab, modern_vocab)
            if fixed != t.text:
                repairs[(t.text, fixed)] += 1
                t.text = fixed

        # Footnotes out of the flow, keyed by page.
        notes_by_page: dict[int, list[list[Token]]] = {}
        body: list[Token] = []
        lines_of_note: dict[int, list[Token]] = {}
        for t in voted:
            if t.note is None:
                body.append(t)
            else:
                lines_of_note.setdefault(t.note, []).append(t)
        for nid in sorted(lines_of_note):
            nt = lines_of_note[nid]
            notes_by_page.setdefault(nt[0].page, []).extend(_split_notes(nt))

        # Markers in the body, by page; pair them with that page's notes.
        marks_by_page: dict[int, list[list[int]]] = {}
        for run in _mark_runs(body):
            marks_by_page.setdefault(body[run[0]].page, []).append(run)
        # A mark renders as a placeholder "#k" naming note k; the sigla are
        # dealt out in reading order once every mark is placed.
        mark_of: dict[int, str] = {}
        note_texts: list[str] = []
        anchored: list[tuple[str, int]] = []
        for page in sorted(set(notes_by_page) | set(marks_by_page)):
            ns = notes_by_page.get(page, [])
            ms = marks_by_page.get(page, [])
            if not strict and ns:
                log(f"     notes ch {n} page {page}: " + " | ".join(_render(x) for x in ns))
            if (n, page) in _PAGE_NOTES:
                for run in ms:
                    for i in run:
                        mark_of[i] = ""
                for anchor, note in _PAGE_NOTES[(n, page)]:
                    anchored.append((anchor, len(note_texts)))
                    note_texts.append(note)
                continue
            if not ns:
                continue  # stray marks on a page with no notes: OCR noise, see _FIXES
            if len(ns) != len(ms):
                fail(f"ch {n} page {page}: footnotes unpaired")
                log(f"  ch {n} page {page}: {len(ms)} marks, {len(ns)} notes: "
                    + " | ".join(_render(x) for x in ns)
                    + " || " + " | ".join(_render(body[max(0, r[0] - 6):r[-1] + 1]) for r in ms))
                continue
            for run, nt in zip(ms, ns, strict=True):
                mark_of[run[0]] = f"#{len(note_texts)}"
                for i in run[1:]:
                    mark_of[i] = ""
                note_texts.append(_render(nt))

        # Paragraphs.
        groups: list[tuple[int, list[Token]]] = []
        for i, t in enumerate(body):
            if t.para or not groups:
                groups.append((i, []))
            groups[-1][1].append(t)
        html = ""
        first = True  # the opening word is set in capitals (_fix_dropcap)
        for gi, (start, g) in enumerate(groups):
            local = {i - start: s for i, s in mark_of.items() if start <= i < start + len(g)}
            text = _render(g, local)
            if gi == 0 and n > 0:
                html += f"<blockquote><p>{_esc(text)}</p></blockquote>"
                continue
            if g[0].head:
                html += f"<h3>{ADDRESS_LAST if n == len(TITLES) else ADDRESS}</h3>"
                first = True
                continue
            if first:
                text = _fix_dropcap(text)
                first = False
            html += f"<p>{_esc(text)}</p>"
        if n == len(TITLES):
            html += f"<p>{DOXOLOGY}</p>"
        for old, new in _FIXES:
            if old in html:
                fixes_used[old] += 1
                html = html.replace(old, new)
            for k, note in enumerate(note_texts):
                if old in note:
                    fixes_used[old] += 1
                    note_texts[k] = note.replace(old, new)
        for anchor, k in anchored:
            if html.count(anchor) != 1:
                fail(f"ch {n}: footnote anchor {anchor!r} found {html.count(anchor)}x")
                continue
            html = html.replace(anchor, f"{anchor}<sup>#{k}</sup>")
        order = [int(k) for k in re.findall(r"<sup>#(\d+)</sup>", html)]
        if sorted(order) != list(range(len(note_texts))):
            fail(f"ch {n}: footnote marks and notes disagree")
        for seq, k in enumerate(order):
            html = html.replace(f"<sup>#{k}</sup>", f"<sup>{_siglum(seq)}</sup>", 1)
        if order:
            html += "<hr/>" + "".join(
                f"<p><sup>{_siglum(seq)}</sup> {_esc(_fix_note(note_texts[k]))}</p>"
                for seq, k in enumerate(order)
            )
        log(f"  ch {n:2}: {changed} readings from the other witnesses, {len(order)} notes")
        chapters.append((title, html))
    log("  letter repairs: " + ", ".join(f"{a}>{b}" + (f" x{c}" if c > 1 else "") for (a, b), c in sorted(repairs.items())))
    unused = [old for old, _ in _FIXES if not fixes_used[old]]
    if unused:
        fail(f"{len(unused)} fix(es) no longer match: {unused[:5]}")
    return chapters


def load_texts(source_dir: str | None) -> dict[str, str]:
    texts = {}
    for item in WITNESSES:
        if source_dir:
            texts[item] = (Path(source_dir) / f"{item}.txt").read_text(encoding="utf-8", errors="replace")
        else:
            texts[item] = fetch_text(item)
    return texts


class Command(BaseCommand):
    help = "Build Spurgeon's The Saint and His Saviour (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("--source-dir", help="read <item>.txt djvu files from here")

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not in the DB — seed it first.") from exc

        chapters = build_chapters(load_texts(opts.get("source_dir")), log=self.stdout.write)

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "hook": HOOK,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{PRIMARY}",
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
            settled = settled_chapter_body(SLUG, order, clean_fragment(body))
            curled, changed = convert(settled, outer_guillemets=False)
            if changed:
                assert_punctuation_only(settled, curled, f"{SLUG}.en[{order}]")
            wc = word_count(curled)
            if wc < (300 if order == 1 else 1000):
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=curled)
            self.stdout.write(f"  ch {order:2}: {title[:40]:40} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
