"""Build R. A. Torrey's *What the Bible Teaches* (1898).

Torrey's systematic theology, "a thorough and comprehensive study of what the
Bible has to say concerning the great doctrines of which it treats": six books
(God, Jesus Christ, the Holy Spirit, Man, Angels, the Devil) in fifty-three
chapters, each laid out the way he taught it in the classroom at the Chicago
Bible Institute — the Scripture statements first, then the PROPOSITION they
yield, then his comment. Public domain — copyright 1898 by Fleming H. Revell.

SOURCE. No transcription exists, so this is the OCR of four Internet Archive
scans of the Revell plates. All four set every printed line identically, which
is what makes the repair below possible:

* **Page furniture out.** Running heads ("410 What the Bible Teaches",
  "Prayer 409"), bare page numbers and a few library stamps.
* **A word-by-word vote.** `BASE_ID` is the witness whose text is kept: it
  keeps line-end hyphens and has the cleanest layout. Each chapter of every
  other scan is aligned with it (difflib, on a punctuation-blind key). Two of
  the scans were read by one newer OCR engine and share its misreadings, so a
  base word gives way only when the other old-engine copy and a new-engine
  scan agree on another reading — or when both new-engine scans do and theirs
  is a far commoner word in the book (see `Vote`).
* **OCR repairs from `data/what-the-bible-teaches/ocr_fixes.json`**: literal
  `(find, replace)` pairs per chapter, from a proofread of what the vote left.
  They are written against the stored (settled) text, so they are applied after
  `settled_chapter_body` and the body is settled again. Held as data beside the
  command because they are editorial (see the book-import skill).

MARKUP follows the printed layout: a roman-numbered section head is `<h3>`;
the Scripture proofs Torrey sets in small type (a reference, a dash, the
verse) are `<blockquote>`; the PROPOSITION, Question, Answer and Note labels
are `<strong>`. The Preface opens the book; the Contents and the Index are left
out. Each Book's own title page ("Book II. What the Bible Teaches About Jesus
Christ") is kept as an `<h2>` above that Book's first chapter.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/what-the-bible-teaches.en.json`, resolving the
existing `r-a-torrey` author. No `catalog.py` entry. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_what_the_bible_teaches
"""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.archive_book import apply_fixes, load_fixes, similar
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import fetch_text
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "what-the-bible-teaches"
AUTHOR_SLUG = "r-a-torrey"
TITLE = "What the Bible Teaches"
SUBTITLE = (
    "A Thorough and Comprehensive Study of What the Bible Has to Say "
    "Concerning the Great Doctrines of Which It Treats"
)
PUBLICATION_YEAR = 1898
COVER_COLOR = "#3d4f6b"
#: The witness whose text is kept; the others vote on its words.
BASE_ID = "whatbibleteaches00torr"
OTHER_IDS = (
    "whatthebibletea00torruoft",  # the other old-engine copy (OLD_ID)
    "whatbibleteaches0000rato_m3m7",
    "whatbibleteaches0000reub",
)
ATTRIBUTION = (
    "Public domain — first published 1898 by Fleming H. Revell Company, New "
    "York, Chicago and Toronto. Text from the Internet Archive scans of four "
    "copies of the Revell edition, compared word by word."
)
DESCRIPTION = (
    "Torrey's systematic theology, built the way he taught it at the Chicago "
    "Bible Institute: gather everything the Bible says on a subject, then state "
    "exactly what it teaches. In six books — on God, Jesus Christ, the Holy "
    "Spirit, man, angels and the devil — each chapter sets out the Scriptures "
    "first and draws from them its propositions, from the attributes of God and "
    "the deity of Christ to justification, the new birth, prayer and the coming "
    "again of the Lord."
)

#: Editorial Q&A, answered from Torrey's own Preface and the book's layout.
QA = [
    {
        "question": "What is What the Bible Teaches?",
        "answer": (
            "R. A. Torrey's systematic study of Bible doctrine, first published in 1898. "
            "In six books and fifty-three chapters it takes up what the Bible teaches about "
            "God, about Jesus Christ, about the Holy Spirit, about man, about angels and about "
            "the Devil — gathering the Scriptures on each subject and stating, as exactly as he "
            "can, what they say."
        ),
    },
    {
        "question": "How is each chapter laid out?",
        "answer": (
            "The Scripture comes first and the doctrine second. Torrey sets out the passages "
            "on a point, then sums up their contents in a numbered proposition, then adds such "
            "comment as seems necessary. As he puts it in the Preface, the scripture from which "
            "a proposition is deduced is always given before the proposition."
        ),
    },
    {
        "question": "What does Torrey mean by calling the method inductive?",
        "answer": (
            "That the conclusions are drawn out of the Bible rather than brought to it. The "
            "material the Bible contains is brought together and carefully scrutinized, and only "
            "then is what is seen in it stated — exactness first, then clearness, with beauty "
            "and impressiveness always yielding to precision."
        ),
    },
    {
        "question": "Which translation of the Bible does the book quote?",
        "answer": (
            "The Authorized (King James) Version wherever possible, and the Revised Version "
            "where Torrey judged it manifestly more exact; such quotations are marked R.V. No "
            "Hebrew or Greek appears on the page, but the work rests on a careful study of the "
            "original text."
        ),
    },
    {
        "question": "Who did Torrey write it for?",
        "answer": (
            "Its plainest use, he says, is as a classbook in Bible theology, and its contents "
            "were tested in classes drawn from as many as thirty-six denominations. He also "
            "commends it for family devotions, for private study of the Bible, and for groups "
            "of believers with no church near them who want a definite outline to study the "
            "Bible together."
        ),
    },
    {
        "question": "How does Torrey suggest the book be studied?",
        "answer": (
            "Slowly, Bible in hand. Ponder the Scriptures given first, then put your own "
            "understanding of them into your own words before reading Torrey's proposition. "
            "Often, he says, the reader will improve on his statement; if not, the reader will "
            "understand it better for having done a little thinking first."
        ),
    },
    {
        "question": "What did the study do for Torrey's own faith?",
        "answer": (
            "It deepened it. Finding out precisely what the Bible teaches, he believed, is one "
            "of the surest ways to judge whether it is of divine origin, for it shows whether one "
            "deep philosophy runs through books written by so many different human authors. His "
            "conviction that there was one Author behind the many writers, and that the Author "
            "was God, grew as he studied."
        ),
    },
]

#: Each Book's heading, printed on its own page before its first chapter.
BOOKS = [
    "What the Bible Teaches About God",
    "What the Bible Teaches About Jesus Christ",
    "What the Bible Teaches About the Holy Spirit",
    "What the Bible Teaches About Man",
    "What the Bible Teaches About Angels",
    "What the Bible Teaches About the Devil, or Satan",
]

#: The Contents, in order, with the Book each chapter belongs to.
CHAPTERS: list[tuple[int, str]] = [
    (1, "God as Spirit"),
    (1, "The Unity of God"),
    (1, "The Eternity of God"),
    (1, "The Omnipresence of God"),
    (1, "The Personality of God"),
    (1, "The Omnipotence of God"),
    (1, "The Omniscience of God"),
    (1, "The Holiness of God"),
    (1, "The Love of God"),
    (1, "The Righteousness or Justice of God"),
    (1, "The Mercy or Loving-Kindness of God"),
    (1, "The Faithfulness of God"),
    (2, "The Deity of Jesus Christ"),
    (2, "The Subordination of the Son to the Father"),
    (2, "The Human Nature of Jesus Christ"),
    (2, "The Character of Jesus Christ"),
    (2, "The Death of Jesus Christ"),
    (2, "The Resurrection of Jesus Christ"),
    (2, "The Ascension or Exaltation of Jesus Christ"),
    (2, "The Coming Again of Jesus Christ"),
    (3, "The Personality of the Holy Spirit"),
    (3, "The Deity of the Holy Spirit"),
    (3, "The Distinction of the Holy Spirit from the Father and from His Son, Jesus Christ"),
    (3, "The Subordination of the Holy Spirit to the Father and the Son"),
    (3, "The Names of the Holy Spirit"),
    (3, "The Work of the Holy Spirit"),
    (3, "The Baptism and Filling with the Holy Spirit"),
    (3, "The Work of the Holy Spirit in Prophets and Apostles"),
    (3, "The Work of the Holy Spirit in Jesus Christ"),
    (4, "Man's Original Condition"),
    (4, "The Fall"),
    (4, "The Present Standing Before God and Condition of Men Outside of the "
        "Redemption That Is in Christ Jesus"),
    (4, "The Future Destiny of Those Who Reject the Redemption That Is in Christ Jesus"),
    (4, "Justification"),
    (4, "The New Birth"),
    (4, "Adoption"),
    (4, "Sanctification"),
    (4, "Repentance"),
    (4, "Faith"),
    (4, "Love to God"),
    (4, "Love to Christ"),
    (4, "Love to Man"),
    (4, "Prayer"),
    (4, "Thanksgiving"),
    (4, "Worship"),
    (4, "The Believer's Assurance"),
    (4, "The Future Destiny of Believers"),
    (5, "Angels: Their Nature, Position, Number and Abode"),
    (5, "The Work of Angels"),
    (6, "The Devil: His Existence, Nature, Position and Character"),
    (6, "Ezekiel XXVIII"),
    (6, "The Abode and Work of Satan"),
    (6, "Our Duty Towards Satan and His Destiny"),
]

_WS = re.compile(r"\s+")
#: A bare chapter marker on its own line. The scans misread the numeral every
#: way ("CHAPTER VIL", "CHAPTERVIL", "CHAPTER f£", "CHAPTER II¥."), so the
#: numeral is not read at all: the markers are taken in document order.
_MARKER = re.compile(r"^\s*CHAPTER\s*\S{0,6}(?:\s\S{1,2})?\s*$")
_BOOK_MARKER = re.compile(r"^\s*BOOK\s+\S{1,4}\s*$")
_BARE_NUM = re.compile(r"^[\s\d.,*•'‘’\-]*$")
#: A page number the old engine read as a letter ("i", "I") on a line alone.
_LONE_MARK = re.compile(r"^\s*[iIl1|]\s*$")
_STAMPS = ("LIBRARY", "UNIVERSITY", "TORONTO")
_PREFACE = re.compile(r"^\s*PREFACE\.?\s*\d*\s*$")
_CONTENTS = re.compile(r"^\s*TABLE\s+OF\s+CONTENTS")
_INDEX = re.compile(r"^\s*INDEX\.?\s*$")
_SECTION_HEAD = re.compile(r"^[IVXLU]{1,6}[.,]\s")
_NUMBERED_START = re.compile(r"^\W*[\dIl]{1,3}[\d ]{0,3}\s+\D")
_NUMBERED_END = re.compile(r"\D\s+\d[\d ]{0,3}\W*$")
_PROSE_END = re.compile(r"[.?!,;:\"'”)]\s*$")


def _core(text: str) -> str:
    return _WS.sub(" ", re.sub(r"[^A-Za-z ]", " ", text)).strip().lower()


def _is_caps(line: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", line)
    return len(letters) >= 3 and sum(c.isupper() for c in letters) >= 0.85 * len(letters)


_BOOK_HEAD = "what the bible teaches"


class _Line:
    """What _is_furniture needs to know about a line, whatever the title."""

    def __init__(self, line: str):
        self.s = line.strip()
        self.core = _core(self.s)
        # A running head carries its page number at one end ("410 What the
        # Bible Teaches", "Prayer 409", "Prayer 41 1").
        self.numbered = bool(_NUMBERED_START.match(self.s) or _NUMBERED_END.search(self.s))
        # An unnumbered line is a running head only if it reads like one: no
        # closing stop (prose ends "…true faith." on a line of its own).
        self.prose_end = bool(_PROSE_END.search(self.s))

    def verdict(self) -> bool | None:
        """True/False when the title does not matter; None when it does."""
        s = self.s
        if not s:
            return False  # a blank line is layout: it may end a paragraph
        if _BARE_NUM.match(s) or _LONE_MARK.match(s):
            return True
        if _SECTION_HEAD.match(s):
            return False  # a section head, though it may restate the title
        if any(st.lower() in self.core for st in _STAMPS) and _is_caps(s):
            return True
        if len(self.core.split()) > 14:
            return False
        return None

    def heads(self, head: str) -> bool:
        """A running head of `head` (the book's title or a chapter's): OCR
        sometimes loses the page number, so a short line that IS the title
        counts too, but not one much longer than it ("The Ascension … is
        definitely" is prose)."""
        r = similar(self.core, head)
        if self.numbered and r >= 0.6:
            return True
        if r >= 0.85 and not self.prose_end and len(self.core) <= len(head) + 4:
            return True
        # A running head may be the title's opening words only.
        return self.numbered and len(self.core) >= 6 and head.startswith(self.core)


def _is_furniture(line: str, title: str) -> bool:
    """A running head, page number or stamp — not text."""
    ln = _Line(line)
    verdict = ln.verdict()
    if verdict is not None:
        return verdict
    return ln.heads(_BOOK_HEAD) or ln.heads(_core(title))


def _book_heading_at(line: str) -> bool:
    """A Book's title page: "BOOK II." or its heading in capitals."""
    if _BOOK_MARKER.match(line):
        return True
    core = _core(line)
    return core.startswith("what") and _is_caps(line) and any(
        similar(core, _core(b)[:len(core)]) >= 0.85 for b in BOOKS
    )


def split_witness(text: str) -> tuple[list[str], list[list[str]]]:
    """(Preface lines, [lines of each chapter]) from one scan's text."""
    lines = text.replace("\r", "").split("\n")
    pre = next((i for i, ln in enumerate(lines) if _PREFACE.match(ln)), None)
    if pre is None:
        raise CommandError("no Preface / Contents found")
    toc = next((i for i in range(pre + 1, len(lines)) if _CONTENTS.match(lines[i])), None)
    if toc is None:
        raise CommandError("no Preface / Contents found")
    marks = [i for i, ln in enumerate(lines) if i > toc and _MARKER.match(ln)]
    if len(marks) != len(CHAPTERS):
        raise CommandError(f"found {len(marks)} chapter markers, expected {len(CHAPTERS)}")
    end = next((i for i in range(marks[-1], len(lines))
                if _INDEX.match(lines[i])), len(lines))
    chapters = []
    for n, start in enumerate(marks):
        stop = marks[n + 1] if n + 1 < len(marks) else end
        if n + 1 < len(CHAPTERS) and CHAPTERS[n + 1][0] != CHAPTERS[n][0]:
            # The next Book's title page closes this chapter.
            cut = next((i for i in range(start + 1, stop) if _book_heading_at(lines[i])), None)
            if cut is None:
                raise CommandError(f"ch {n + 1}: no Book heading before the next Book")
            stop = cut
        body = lines[start + 1:stop]
        k = 0
        while k < len(body) and (not body[k].strip() or _is_caps(body[k])):
            k += 1
        title = CHAPTERS[n][1]
        chapters.append([ln for ln in body[k:] if not _is_furniture(ln, title)])
    # The Preface: up to the Contents, without its signature block's furniture.
    preface = [ln for ln in lines[pre + 1:toc] if not _is_furniture(ln, "Preface")]
    return preface, chapters


# --- The vote --------------------------------------------------------------

#: Quote marks and dashes as each OCR engine read them, set to one form so
#: the witnesses compare: straight quotes and a closed-up em dash.
_QUOTE_RUNS = [
    (re.compile(r"[“”„‟«»]"), '"'),
    (re.compile(r"[‘’`´]"), "'"),
    # The old engine reads a double quote as two singles, or with a stray mark.
    (re.compile(r"[<*]\s?'|'\s?[*<]|'\s?'"), '"'),
]
_DASH = re.compile(r"\s*(?:—|--|―|–(?=\s))\s*")
#: A verse reference the OCR spaced ("4: 24", "1 :27").
_REF_SPACE = re.compile(r"(\d)\s*:\s+(?=\d)|(\d)\s+:(?=\d)")
_TOKEN = re.compile(r"—|[^\s—]+")
#: The older engine reads a 1 in a verse reference as i, l or I ("Col. i:15",
#: "ii:25", "Ps. 66:i8"); the two scans it read agree on it, so the vote
#: cannot. In a chapter:verse pair those letters can only be ones.
_REF_ONES = re.compile(r"(?<![A-Za-z])([0-9ilI]{1,3}):([0-9ilI]{1,3})(?![A-Za-z])")
#: A numbered proof "(i)" at the head of its line is "(1)", for the same reason.
#: It also turns the few real lettered (i)/(l) proofs into figures; deciding
#: those from the run of letters here re-aligns the vote and costs more than it
#: saves, so the handful are set back in ocr_fixes.json.
_PROOF_ONE = re.compile(r"^(\s*)\(([ilI]|i[il1]|1[il])\)")
_ONE = str.maketrans({"i": "1", "l": "1", "I": "1"})
_MALACHI = re.compile(r"\bMai\.(?=\s*\d)")


def _normalize(line: str) -> str:
    for rx, rep in _QUOTE_RUNS:
        line = rx.sub(rep, line)
    line = _DASH.sub("—", line)
    line = _REF_SPACE.sub(lambda m: (m.group(1) or m.group(2)) + ":", line)

    def ones(m: re.Match) -> str:
        left, right = m.group(1), m.group(2)
        if not re.search(r"\d", left + right):
            return m.group(0)
        return f"{left.translate(_ONE)}:{right.translate(_ONE)}"

    line = _REF_ONES.sub(ones, line)
    line = _PROOF_ONE.sub(lambda m: m.group(1) + "(" + m.group(2).translate(_ONE) + ")", line)
    # Malachi: "Mal." read as "Mai." by both old-engine copies.
    return _MALACHI.sub("Mal.", line)


def _key(token: str) -> str:
    """What the vote compares: the word's letters and digits, case kept."""
    return "—" if token == "—" else re.sub(r"[\W_]", "", token)


def _split_core(token: str) -> tuple[str, str, str]:
    m = re.match(r"^(\W*)(.*?)(\W*)$", token)
    return m.group(1), m.group(2), m.group(3)


def tokenize(lines: list[str]) -> list[tuple[int, str]]:
    """(line number, token) for a run of lines. A word broken at the line end
    ("system-" / "atic") is one token, its hyphen kept for `_settle_hyphen`."""
    out: list[tuple[int, str]] = []
    for n, raw in enumerate(lines):
        toks = _TOKEN.findall(_normalize(raw))
        if (out and toks and out[-1][1].endswith("-")
                and len(out[-1][1]) > 1 and out[-1][1][-2].isalpha() and toks[0][:1].islower()):
            out[-1] = (out[-1][0], out[-1][1] + "­" + toks[0])
            toks = toks[1:]
        out.extend((n, t) for t in toks)
    return out


def _positions(seq: list[str]) -> dict[tuple[str, ...], list[int]]:
    """Every five-word run in `seq` → where it occurs."""
    idx: dict[tuple[str, ...], list[int]] = {}
    for i in range(len(seq) - 4):
        idx.setdefault(tuple(seq[i:i + 5]), []).append(i)
    return idx


def _starts(base_chapters: list[list[str]], in_base: dict, stream: list[str]) -> list[int | None]:
    """Where each base chapter begins in another witness's token stream.

    Chapter openings repeat ("I. The fact that God is …"), so a first match
    runs ahead. Instead every five-word run in a chapter's opening that occurs
    once in the whole base AND once in the witness implies a start; the median
    of those is taken. `in_base` is `_positions` of the whole base."""
    in_other = _positions(stream)
    starts: list[int | None] = []
    for keys in base_chapters:
        implied = sorted(
            in_other[g][0] - off
            for off in range(max(min(len(keys), 400) - 4, 0))
            if len(in_base.get(g := tuple(keys[off:off + 5]), ())) == 1
            and len(in_other.get(g, ())) == 1
        )
        starts.append(max(implied[len(implied) // 2], 0) if len(implied) >= 3 else None)
    return starts


#: Which OCR engine read each witness. The two newer scans were read by one
#: engine and share its misreadings — small capitals ("Lorp" for LORD,
#: "Curist"), italics ("¢he", "Jrom") — so they are one family, not two votes.
#: The base and the other Toronto copy were read by an older engine.
OLD_ID = "whatthebibletea00torruoft"
NEW_IDS = frozenset({"whatbibleteaches0000rato_m3m7", "whatbibleteaches0000reub"})
ENGINE = {OLD_ID: "old", **dict.fromkeys(NEW_IDS, "new")}


def _ci(key: str) -> str:
    return key.lower()


def _cross_engine(support: set[str]) -> bool:
    return {ENGINE[w] for w in support} == {"old", "new"}


def _group(readings: dict[str, str], keyfn) -> dict[str, set[str]]:
    """Witnesses grouped by what they read (as `keyfn` normalizes it)."""
    by: dict[str, set[str]] = {}
    for w, text in readings.items():
        by.setdefault(keyfn(text), set()).add(w)
    return by


def _is_junk(tokens: list[str]) -> bool:
    """A run the vote may delete outright: stray marks, no real word in it."""
    return not any(re.search(r"[A-Za-z]{3}", t) for t in tokens)


class Vote:
    """The other witnesses' readings of one base chapter.

    A reading replaces the base's when the other old-engine copy and a
    new-engine scan agree on it (two copies, two engines); or when only the
    new engine reads it but it is a far commoner word in the book than the
    base's reading (the base misread a word the new engine got right).
    Readings differing only in case never replace the base: case is where
    the engines differ most (small capitals), and the base's is kept."""

    def __init__(self, base: list[str], lines: list[int]):
        self.base = base
        self.lines = lines
        self.keys = [_key(t) for t in base]
        #: base index → {witness: token}
        self.single: list[dict[str, str]] = [{} for _ in base]
        #: (i1, i2) → {witness: replacement text}
        self.spans: dict[tuple[int, int], dict[str, str]] = {}

    def add(self, witness: str, other: list[str]) -> None:
        okeys = [_key(t) for t in other]
        sm = SequenceMatcher(None, self.keys, okeys, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
                for i, j in zip(range(i1, i2), range(j1, j2), strict=True):
                    self.single[i][witness] = other[j]
            elif i2 - i1 <= 3 and j2 - j1 <= 3:
                self.spans.setdefault((i1, i2), {})[witness] = " ".join(other[j1:j2])

    def _wins(self, support: set[str], new: str, old: str, freq: Counter) -> bool:
        if _cross_engine(support):
            return True
        if support == NEW_IDS:
            return freq[_ci(new)] >= 4 * max(freq[_ci(old)], 1)
        return False

    def result(self, review: list[str], freq: Counter) -> list[str]:
        out = list(self.base)
        taken: set[int] = set()
        for (i1, i2), readings in sorted(self.spans.items()):
            mine = _ci("".join(self.keys[i1:i2]))
            by = _group(readings, lambda text: _ci("".join(_key(t) for t in text.split())))
            for joined, support in by.items():
                # An insertion (i1 == i2) lands on the word at i1, so it
                # reserves that word; a replacement reserves only its own.
                span = set(range(i1, max(i2, i1 + 1)))
                if joined == mine or taken & span:
                    continue
                if not self._wins(support, joined, mine, freq):
                    continue
                if i2 > i1 and not joined and (
                    not _is_junk(self.base[i1:i2])
                    or any(self.lines[i] != self.lines[i - 1] for i in range(i1, i2) if i)
                ):
                    review.append(f"kept (others lack it): {' '.join(self.base[i1:i2])!r}")
                    continue
                text = next(readings[w] for w in sorted(support))
                words = text.split()
                if i1 == i2:
                    if i1 < len(out):
                        out[i1] = text + " " + out[i1]
                elif len(words) == i2 - i1:
                    out[i1:i2] = words
                elif len({self.lines[i] for i in range(i1, i2)}) == 1:
                    out[i1] = text
                    for i in range(i1 + 1, i2):
                        out[i] = ""
                else:
                    # Would move words across a line, and so perhaps across a
                    # paragraph break.
                    review.append(f"span across lines: {' '.join(self.base[i1:i2])!r} / {text!r}")
                    continue
                taken.update(span)
        for i, readings in enumerate(self.single):
            if i in taken or not readings:
                continue
            key = _ci(self.keys[i])
            for word, support in _group(readings, lambda tok: _ci(_key(tok))).items():
                if not word or not key:
                    continue
                if word == key or not self._wins(support, word, key, freq):
                    if word != key and len(support) >= 2:
                        review.append(f"kept: {self.base[i]!r} / {readings[min(support)]!r}")
                    continue
                donor = readings[OLD_ID] if OLD_ID in support else readings[min(support)]
                lead, _, trail = _split_core(out[i])
                _, core, _ = _split_core(donor)
                out[i] = lead + core + trail
                break
            # Trailing stops ("Father," / "Father.") by the same rule.
            mine = _trail(out[i])
            for stop, support in _group(readings, _trail).items():
                if stop != mine and _cross_engine(support):
                    lead, core, trail = _split_core(out[i])
                    rest = re.sub(r"[.,;:!?]", "", trail)
                    out[i] = lead + core + stop + rest
                    break
        return out


def _trail(token: str) -> str:
    """A token's closing stop — the punctuation the vote decides."""
    return "".join(c for c in _split_core(token)[2] if c in ".,;:!?")


def _body_stream(text: str) -> list[str]:
    """A witness's tokens from its first chapter to the Index, page numbers out."""
    lines = text.replace("\r", "").split("\n")
    toc = next(i for i, ln in enumerate(lines) if _CONTENTS.match(ln))
    first = next(i for i, ln in enumerate(lines) if i > toc and _MARKER.match(ln))
    end = next((i for i in range(len(lines) - 1, first, -1) if _INDEX.match(lines[i])), len(lines))
    titles = [_core(title) for _, title in CHAPTERS]
    keep = [ln for ln in lines[first:end]
            if not _BARE_NUM.match(ln.strip()) and not _is_any_head(ln, titles)]
    return [t for _, t in tokenize(keep)]


def _is_any_head(line: str, titles: list[str]) -> bool:
    """A running head of any chapter (the other scans are not split by
    chapter, so their heads are tested against every title; `titles` are
    already `_core`d)."""
    s = line.strip()
    if len(s.split()) > 12 or not re.search(r"\d", s) or ":" in s:
        return False
    ln = _Line(s)
    verdict = ln.verdict()
    if verdict is not None:
        return verdict
    return ln.heads(_BOOK_HEAD) or any(ln.heads(t) for t in titles)


def _preface_stream(text: str) -> list[str]:
    lines = text.replace("\r", "").split("\n")
    pre = next(i for i, ln in enumerate(lines) if _PREFACE.match(ln))
    toc = next(i for i in range(pre + 1, len(lines)) if _CONTENTS.match(lines[i]))
    return [t for _, t in tokenize([ln for ln in lines[pre + 1:toc]
                                    if not _BARE_NUM.match(ln.strip())])]


def voted_sections(base_text: str, others: list[tuple[str, str]], review: list[str]) -> list[list[str]]:
    """[Preface, chapter 1, …] as lines of voted text, in the base's layout."""
    preface, chapters = split_witness(base_text)
    sections = [preface, *chapters]
    toks = [tokenize(s) for s in sections]
    base_keys = [[_key(t) for _, t in tk] for tk in toks]
    votes = [Vote([t for _, t in tk], [n for n, _ in tk]) for tk in toks]
    freq: Counter = Counter(_ci(k) for keys in base_keys for k in keys)
    in_base = _positions([k for keys in base_keys[1:] for k in keys])
    for witness, text in others:
        votes[0].add(witness, _preface_stream(text))
        stream = _body_stream(text)
        freq.update(_ci(_key(t)) for t in stream)
        skeys = [_key(t) for t in stream]
        starts = _starts(base_keys[1:], in_base, skeys)
        for c, s in enumerate(starts):
            if s is None:
                review.append(f"ch {c + 1}: not found in a witness")
                continue
            e = next((x for x in starts[c + 1:] if x is not None), len(stream))
            # A few words either side: the alignment absorbs them.
            votes[c + 1].add(witness, stream[max(s - 10, 0):e + 10])
    out = []
    for n, (tk, vote) in enumerate(zip(toks, votes, strict=True)):
        mine: list[str] = []
        voted = vote.result(mine, freq)
        review.extend(f"§{n}: {r}" for r in mine)
        lines: list[list[str]] = [[] for _ in sections[n]]
        for (ln, _), word in zip(tk, voted, strict=True):
            if word:
                lines[ln].append(word)
        out.append([" ".join(w) for w in lines])
    return out


# --- Markup ----------------------------------------------------------------

def _to_roman(n: int) -> str:
    out = ""
    for value, digits in ((40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += digits
            n -= value
    return out


_ROMANS = [_to_roman(n) for n in range(1, 50)]
#: A section numeral as the scans read it: "I," "L" "U." "[>" "lY." "IIL" …
_HEAD_NUM = re.compile(
    r"^;?((?:[IVXLlYUfHTF]{1,5}|Vra|1[1lI]|m|n)[.,*;]\*?|L|h|\[>|I\s?\*|I\s,|II)\s+(?=[A-Z\"'(])"
)
_BOOKS_ABBR = r"(?:[1-3I]{1,3}\s)?[A-Z][a-z]{1,7}\.?"
_VERSE = r"[0-9ilIgS]{1,3}:\s?[0-9ilIgS]{1,3}"
#: A Scripture proof, set in small type: "(3) Matt. 20:28—"…", "Compare Heb.
#: 9:22—"…", or a numbered section that opens on its proof ("I. Jno. 14:28—").
_PROOF = re.compile(
    rf"^(?:[({{]?[\w/\"<?>]{{1,3}}\)\s*|[IVXL]{{1,6}}\.\s+)?(?:\(?(?:Compare|Comp\.|Cf\.|See)\s+)?"
    rf"{_BOOKS_ABBR}\s?{_VERSE}[^—]{{0,60}}—\s?\""
)
_ORDINAL = (r"(?:[A-Z]+(?:\s?-\s?[A-Z]+)?|GENERAL|SUMMARY)")
_PROPOSITION = re.compile(
    rf"^((?:{_ORDINAL}\s+)?P\s?R\s?O\s?P\s?O\s?S\s?I\s?T\s?I\s?O\s?N)\s*['’]?\s*[:;.,]\s*-?\s*"
)
_LABEL = re.compile(
    r"^((?:Preliminary\s+)?Note(?:\s+[\dilI]{1,2})?|Question|Answer|Summary)"
    r"\s*(?:[.:]\s*—|[.:;])\s*", re.I
)
#: The print numbers books with an old-style figure ("1 Cor.", like "2 Cor.")
#: that the scans read as a capital I.
BOOK_NUMERAL = re.compile(
    r"(?<![\w.])(I{1,3}) (?=(?:Cor|Jno|John|Pet|Thess|Tim|Sam|Kings|Kg|Chron)\.?,? ?\d)"
)
#: 1890s typesetting spaces a stop off its word ("robes ?", "him ;"); the
#: corpus sets them closed up.
SPACED_STOP = re.compile(r"(?<=[\w.\"'”’)\]]) +([;:!?])")
_TERMINAL = ('.', '?', '!', '"', ')', ':', ';', "'")


def _starts_block(line: str) -> bool:
    s = line.strip()
    return bool(_PROPOSITION.match(_spaced_caps(s)) or _LABEL.match(s) or _PROOF.match(s)
                or re.match(r"^[({][\w/\"<?>]{1,3}\)\s", s))


def _spaced_caps(s: str) -> str:
    """Close up a capitals word the OCR split ("SE COND", "FO UR TH")."""
    m = re.match(r"^([A-Z][A-Z\s-]{2,40}?)\s+(P\s?R\s?O\s?P)", s)
    if not m:
        return s
    return re.sub(r"(?<=[A-Z])\s(?=[A-Z])", "", m.group(1)) + " " + s[m.start(2):]


def blocks(lines: list[str]) -> list[str]:
    """Voted lines → paragraphs. A blank line ends a paragraph only when the
    text reads complete (otherwise it is a page break); a label, proof or
    numbered item always starts one, and a section head is always a block of
    its own (the OCR often reads its closing stop as a comma)."""
    out: list[str] = []
    buf: list[str] = []
    in_head = False
    for line in lines:
        s = line.strip()
        if not s:
            if buf and (in_head or buf[-1].rstrip().endswith(_TERMINAL)):
                out.append(" ".join(buf))
                buf = []
                in_head = False
            continue
        head = _is_head_line(s)
        if in_head and buf and _head_wraps(buf[-1], s):
            # The head runs on to a second printed line ("… in Prophets" /
            # "and Apostles.").
            buf.append(s)
            continue
        if buf and (head or in_head or (_starts_block(s) and buf[-1].rstrip().endswith(_TERMINAL))):
            out.append(" ".join(buf))
            buf = []
            in_head = False
        if head and not buf:
            in_head = True
        buf.append(s)
    if buf:
        out.append(" ".join(buf))
    return [_WS.sub(" ", b).strip() for b in out]


def _head_wraps(first: str, line: str) -> bool:
    """A head's first line that stops short, and a short line that ends it."""
    return (not first.rstrip().endswith((".", "?", "!", ":", "*"))
            and len(line.split()) <= 8 and line.rstrip().endswith((".", "?"))
            and not _starts_block(line) and not _is_head_line(line))


def _head_rest(text: str) -> str | None:
    """The words after a section numeral, or None if `text` doesn't open on one."""
    if not _HEAD_NUM.match(text) or _PROOF.match(text):
        return None
    return _HEAD_NUM.sub("", text)


def _is_head_line(line: str) -> bool:
    """The first line of a section head: a numeral, then a capital, short."""
    rest = _head_rest(line)
    return rest is not None and len(rest.split()) <= 12 and not re.search(r"[a-z]\.\s+[A-Z]", rest)


def _is_head(block: str) -> bool:
    rest = _head_rest(block)
    return rest is not None and len(rest.split()) <= 24


#: Section numerals as the scans misread them.
_NUMERAL_OCR = {
    "L": "I", "f": "I", "h": "I", "[>": "I", "1": "I", "I*": "I", "l": "I",
    "IL": "II", "U": "II", "11": "II", "IT": "II", "Il": "II", "lI": "II",
    "Ill": "III", "IIL": "III", "lll": "III", "HI": "III", "Hi": "III",
    "lY": "IV", "IY": "IV", "Y": "V", "YI": "VI", "VL": "VI", "VIL": "VII",
    "VIIL": "VIII", "Vra": "VIII", "XL": "XI", "m": "III", "n": "II", "IF": "IV",
    "TV": "IV", "YU": "VII", "H": "II",
}


def _bare_numeral(got: str) -> str:
    return re.sub(r"[.,*;\s]", "", got)


def _numeral(got: str, prev: int) -> int:
    """The section's number: as read where it is a numeral (OCR variants
    mapped), else the next in sequence."""
    clean = _bare_numeral(got)
    clean = _NUMERAL_OCR.get(clean, clean)
    value = _ROMANS.index(clean) + 1 if clean in _ROMANS else None
    if value is not None and prev < value <= prev + 3:
        return value
    return prev + 1


_SUBHEAD = re.compile(r"^(?:[({]\d{1,2}\)|\d{1,2}\.)\s+[A-Z]")


def _is_subhead(block: str) -> bool:
    """A numbered sub-head ("(2) What Does Holy Mean ?"), not a proof."""
    if not _SUBHEAD.match(block) or _PROOF.match(block) or "—" in block:
        return False
    words = block.split()[1:]
    if len(words) > 14 or not block.rstrip().endswith((".", "?")):
        return False
    long_words = [w for w in words if len(w) > 3]
    return bool(long_words) and sum(w[0].isupper() for w in long_words) >= 0.6 * len(long_words)


def _settle_hyphen(token: str, hyphenated: set[str]) -> str:
    """A word broken at a line end: keep the hyphen only where the book also
    prints the word hyphenated mid-line ("first-born"), or for self-."""
    head, tail = token.split("­", 1)
    whole = head + tail
    word = re.sub(r"[^\w-]|_", "", whole.lower()).strip("-")
    if word in hyphenated or re.match(r"^\W*self-$", head.lower()):
        return whole
    return head[:-1] + tail


def render(lines: list[str], hyphenated: set[str], review: list[str]) -> str:
    """One section's voted lines → HTML."""
    text_lines = [" ".join(_settle_hyphen(t, hyphenated) if "­" in t else t
                           for t in ln.split(" ")) for ln in lines]
    html: list[str] = []
    quote: list[str] = []
    n_head = 0

    def close_quote() -> None:
        if quote:
            html.append("<blockquote>" + "".join(f"<p>{q}</p>" for q in quote) + "</blockquote>")
            quote.clear()

    prev = ""
    letter = ""
    for b in blocks(text_lines):
        b, letter = _reletter(b, letter, review)
        b = _close_quotes(b, review)
        b = SPACED_STOP.sub(r"\1", b)
        if _is_head(b):
            close_quote()
            got = _HEAD_NUM.match(b).group(1)
            n = _numeral(got, n_head)
            if _ROMANS[n - 1] != _bare_numeral(got):
                review.append(f"head {_ROMANS[n - 1]}: read {got!r} in {b[:50]!r}")
            n_head = n
            title = _HEAD_NUM.sub("", b).strip().rstrip(".,*").strip()
            html.append(f"<h3>{_ROMANS[n - 1]}. {_esc(title)}</h3>")
            letter = ""  # a new section starts its own (a), (b), …
        elif _is_subhead(b):
            close_quote()
            num, _, rest = b.partition(" ")
            num = f"({num.strip('({)')})" if num.endswith(")") else num
            html.append(f"<h4>{num} {_esc(rest.rstrip('.').strip())}</h4>")
            letter = ""
        elif _PROOF.match(b) or (b.startswith('"') and prev.endswith(":")):
            m = re.match(r"^([IVXL]{1,6})\.\s+", b)
            if m and _PROOF.match(b) and m.group(1) in _ROMANS:
                # A numbered section that opens on its proof (Book II ch. 2).
                n_head = _ROMANS.index(m.group(1)) + 1
            quote.append(_esc(b))
        else:
            close_quote()
            p = _spaced_caps(b)
            m = _PROPOSITION.match(p)
            if m:
                label = " ".join(w.capitalize() for w in re.sub(r"\s", "", m.group(1))
                                 .replace("PROPOSITION", " PROPOSITION").split())
                label = re.sub(r"-(\w)", lambda x: "-" + x.group(1).lower(), label)
                html.append(f"<p><strong>{label}:</strong> {_esc(p[m.end():])}</p>")
            elif (m := _LABEL.match(b)):
                word = " ".join(w.capitalize() for w in m.group(1).split())
                word = re.sub(r"(?<=Note )[ilI]\b", "1", word)
                sep = ".—" if "—" in m.group(0) or word.endswith("Note") else ":"
                html.append(f"<p><strong>{word}{sep}</strong> {_esc(b[m.end():])}</p>")
            else:
                html.append(f"<p>{_esc(b)}</p>")
        prev = b
    close_quote()
    return "".join(html)


_LETTERED = re.compile(r"^[({]?([\w/\"<?>]{1,3})\)\s+(?=\S)")
_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _reletter(block: str, prev: str, review: list[str]) -> tuple[str, str]:
    """Lettered proofs run (a), (b), (c)… . A letter that reads cleanly is
    kept; one the scans could not read ("(/)", "(<?)", "(\")", "(//)")
    takes the next letter after the one before it."""
    m = _LETTERED.match(block)
    if not m or m.group(1).isdigit():
        return block, prev
    got = m.group(1)
    if got == "li":
        got = "h"
    if len(got) == 1 and got in _LETTERS:
        want = got
    else:
        want = _LETTERS[_LETTERS.index(prev) + 1] if prev and prev != "z" else "a"
        review.append(f"letter ({want}): read {m.group(0).strip()!r} in {block[:40]!r}")
    return f"({want}) " + block[m.end():], want


def _close_quotes(block: str, review: list[str]) -> str:
    """Close up the space the scans leave inside a quotation (`" God is
    holy "`), pairing the paragraph's double quotes in order. A paragraph with
    an odd number is left as it is, for the proofread."""
    marks = [m.start() for m in re.finditer('"', block)]
    if len(marks) % 2:
        review.append(f"odd quotes: {block[:60]!r}")
        return block
    out, last = [], 0
    for n, at in enumerate(marks):
        if n % 2 == 0:
            out.append(block[last:at] + '"')
            last = at + 1
            while last < len(block) and block[last] == " ":
                last += 1
        else:
            out.append(block[last:at].rstrip(" ") + '"')
            last = at + 1
    out.append(block[last:])
    return "".join(out)


def _esc(text: str) -> str:
    return escape(text, quote=False)


def hyphenated_words(texts: list[str]) -> set[str]:
    """Words the scans print hyphenated mid-line ("to-day", "loving-kindness")
    at least as often as closed up ("firstborn" is mostly closed)."""
    hyph: Counter = Counter()
    closed: Counter = Counter()
    for text in texts:
        for line in text.split("\n"):
            for tok in line.split()[:-1]:
                m = re.fullmatch(r"\W*([A-Za-z]+(?:-[A-Za-z]+)*)\W*", tok)
                if m:
                    word = m.group(1).lower()
                    (hyph if "-" in word else closed)[word] += 1
    return {w for w, n in hyph.items() if n >= closed[w.replace("-", "")]}


def build_sections(base_text: str, others: list[tuple[str, str]],
                   review: list[str]) -> list[str]:
    """[Preface, chapter 1, …] as HTML, before corrections."""
    voted = voted_sections(base_text, others, review)
    hyph = hyphenated_words([base_text, *(t for _, t in others)])
    return [render(lines, hyph, review) for lines in voted]


def arabic_book_numerals(html: str) -> str:
    """"I Cor." → "1 Cor." (see BOOK_NUMERAL). Run after the OCR fixes, which
    are written against the text as the scans read it."""
    return BOOK_NUMERAL.sub(lambda m: f"{len(m.group(1))} ", html)


class Command(BaseCommand):
    help = "Build R. A. Torrey's What the Bible Teaches (1898) from four archive.org scans."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cache", help="Directory to keep the fetched scans in (dev re-runs)."
        )
        parser.add_argument(
            "--review", help="Write the vote's open questions to this file."
        )

    def _text(self, item: str, cache: str | None) -> str:
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
            path = Path(cache) / f"{item}.txt"
            if path.exists():
                return path.read_text(encoding="utf-8")
            text = fetch_text(item)
            path.write_text(text, encoding="utf-8")
            return text
        return fetch_text(item)

    def handle(self, *args, **opts):
        # Fetching and aligning the scans takes minutes; only the writes need
        # the transaction.
        cache = opts.get("cache")
        base = self._text(BASE_ID, cache)
        others = [(w, self._text(w, cache)) for w in OTHER_IDS]
        review: list[str] = []
        sections = build_sections(base, others, review)
        if opts.get("review"):
            Path(opts["review"]).write_text("\n".join(review) + "\n", encoding="utf-8")
        with transaction.atomic():
            self._write(sections, len(review))

    def _write(self, sections: list[str], open_questions: int) -> None:
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{BASE_ID}",
            "qa": QA,
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

        fixes = load_fixes(SLUG)
        known = {str(n) for n in range(1, len(sections) + 1)}
        if set(fixes) - known:
            raise CommandError(f"ocr_fixes.json names unknown chapters: {sorted(set(fixes) - known)}")
        total = 0
        last_book = 0
        for order, ((title, book_no), body) in enumerate(
            zip([("Preface", 0), *((t, b) for b, t in CHAPTERS)], sections, strict=True),
            start=1,
        ):
            if book_no and book_no != last_book:
                body = f"<h2>Book {_ROMANS[book_no - 1]}: {BOOKS[book_no - 1]}</h2>" + body
                last_book = book_no
            curled, _ = convert(body, outer_guillemets=False)
            assert_punctuation_only(body, curled, f"{SLUG} ch {order}")
            body = settled_chapter_body(SLUG, order, clean_fragment(curled))
            # The fixes may add markup (a head, a blockquote), so the result is
            # sanitized again before it is stored.
            body = clean_fragment(arabic_book_numerals(apply_fixes(order, body, fixes)))
            body = settled_chapter_body(SLUG, order, body)
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words "
            f"({open_questions} open questions from the vote)"
        ))
