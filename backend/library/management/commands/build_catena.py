"""Build a catena on a book of the Bible: its text, passage by passage, with the Church's
commentators speaking under each verse, oldest first.

A *catena* ("chain") is the old way of reading Scripture slowly: under every
verse, excerpts from the great commentators, one after another. This command
builds one as a library book from two CC0 sources. Which commentators speak,
under what short work title and from which era, is the book's own editorial
choice, listed in `data/catena/<CODE>/book.json` ("voices": Logia author id,
name, short title, Logia work id, era); a new book is a new folder there
(`--vendor-owb` writes its passages) and an entry in BOOKS. An optional
"words_per_verse" there sets the selection's budget (WORDS_PER_VERSE by
default), for a book whose commentators run so long its chapters would grow
too big to read.

* **The text**: the Open Word Bible, English Balanced (`data/bible/owb-en-b.json.gz`,
  the wording the Scripture popover and `build_owb_book` use), cut into the
  passages OWB's own section headings mark (`data/catena/<CODE>/owb_sections.json`,
  vendored with its commit).
* **The commentary**: Logia's excerpts (https://logia.faith/open-data/, CC0),
  each copied word for word from a public-domain edition and keyed to verses.
  Download the file and pass its path:

      curl -sSLo /tmp/logia-en.json https://logia.faith/downloads/logia-en.json
      DJANGO_DEBUG=true uv run python manage.py build_catena /tmp/logia-en.json JHN

  then serialize the row to `fixtures/content/books/<slug>.en.json` (book-import
  skill, "Write its fixture file yourself").

SELECTION. Logia holds about two million words on John alone, so the book is a
choice: roughly one excerpt in twenty. `--select` makes it, deterministically,
and writes the excerpt ids to `data/catena/<CODE>/selection.json`; a plain run
reads that file, so a later Logia download cannot reshuffle the book, and an
editor can swap an excerpt by editing one id. The rule, per passage: a word
budget in proportion to its verses; then, greedily, the excerpt that adds an
era and a voice the passage does not have yet, reads at a comfortable length,
spreads across the passage's verses, and keeps any one commentator from
crowding the book. An excerpt is never chosen if the scan has damaged it
(see `vocabulary`), if it carries Greek or Hebrew, or if an editor has turned
it down in `rejected.json`. Aquinas's Catena Aurea is left out on purpose — it is
itself a chain of the Fathers, and would repeat Augustine and Chrysostom.

TEXT. Each excerpt is the source's words in the source's order. Only
typography is touched: whitespace collapsed, the scan's spaces before
punctuation and inside quotation marks closed up, a stray byte-order mark and a leading verse number dropped, quotation marks
curled the house way. Old spelling and the
commentators' own Bible wording (usually the King James) stand as printed.

LAYOUT. One chapter per Bible chapter, between an introduction and a back
chapter on the voices and their editions (both Ochorus's own writing, in
`data/catena/<CODE>/`). In a chapter, each OWB section is an `<h3>`; under it
the verses run in order as quoted blocks, each followed by the excerpts that
comment on it. Every verse is quoted exactly once.

An English original, like the house's other compiled books, so it is created
`public_domain` (the review state is for translations). Idempotent.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from functools import cached_property
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.archive_ocr import space_quotes
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.management.commands.build_owb_book import DISPUTED, curl_singles
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert
from library.sanitize import clean_fragment
from library.scripture import _OWB_PATH, _owb
from library.text import word_count

AUTHOR_SLUG = "ochorus-originals"
LANGUAGE = "en"
EDITORIAL = Path(settings.BASE_DIR) / "library" / "data" / "catena"
LOGIA = "https://logia.faith"

#: The books this command can build: code -> (English name as a reference
#: begins, OWB book number, a chapter's title with {n} for its number, how the
#: back chapter names the Bible text). Mark is left out until its disputed
#: endings are handled: DISPUTED's entry for them begins mid-verse (16:8.s2),
#: which text_block would read as the whole of 16:8.
BOOKS = {
    "PSA": ("Psalm", 19, "Psalm {n}", "The text of the Psalms"),
    "MAT": ("Matthew", 40, "Matthew {n}", "The Gospel text"),
    "LUK": ("Luke", 42, "Luke {n}", "The Gospel text"),
    "JHN": ("John", 43, "John {n}", "The Gospel text"),
    "ROM": ("Romans", 45, "Romans {n}", "The text of Romans"),
}

#: OWB's note on a passage the oldest manuscripts lack (build_owb_book.DISPUTED
#: lists them), worded for this book, which does not bracket it.
DISPUTED_NOTE = (
    "The earliest manuscripts of {book} do not have {ref}. Most Bibles print it, "
    "and so does this book, in the place it has always stood."
)

#: Words of commentary per verse of text, and a passage's floor and ceiling.
WORDS_PER_VERSE = 90
BUDGET_MIN, BUDGET_MAX = 500, 2600
#: Excerpt length bounds, in words. Wesley's and Bengel's notes are short by design.
MIN_WORDS, MIN_WORDS_SHORT, MAX_WORDS = 40, 20, 450
SHORT_VOICES = frozenset({"wesley", "bengel"})
#: A comfortable excerpt length, which the score leans towards.
IDEAL_WORDS = 200

#: Scan debris: stray asterisks, bars and carets, a degree sign, angle brackets.
_SCAN_NOISE = re.compile(r"[*|^°<>{}]")
#: A letter run broken by ? or ! or a digit inside a word: "ma?i", "c0me".
_MISREAD = re.compile(r"[a-z][?!][a-z]|[a-z]\d|\d[a-z]{3,}")
_SHORT_WORDS = frozenset({
    "a", "i", "o", "ah", "am", "an", "as", "at", "be", "by", "do", "go", "ha", "he", "ho", "if", "in",
    "is", "it", "lo", "me", "my", "no", "of", "oh", "on", "or", "ox", "so", "to", "up", "us", "we", "ye",
})
_NON_LATIN = re.compile(r"[Ͱ-Ͽἀ-῿֐-׿]")
_OPENS_MIDWAY = re.compile(r"^(?:and|but|or|nor|so|for|yet|then|thus|hence|therefore)\b", re.I)
_LEADING_VERSE = re.compile(r"^(?:(?:Ver|Verse)\.?\s*)?\d+\.\s+(?=\S)")
_SPACE_BEFORE = re.compile(r"\s+([,;:.?!)\]])")
BOM = "\ufeff"
#: A byte-order mark just inside a bracket or a curled quotation mark, with
#: the space it carries.
_BOM_INSIDE = re.compile(r"([(\[“‘])\ufeff\s*|\s*\ufeff\s*([”’])")
#: An old elision's apostrophe ('tis, 'twas, 'em), which curl_singles would
#: otherwise read as an opening quotation mark after a space.
_ELISION = re.compile(r"(?<!\w)'(?=(?:tis|twas|twere|twill|twould|em|gainst|neath|mongst)\b)", re.I)
_VERSE_REF = re.compile(r"(\d+)[.:](\d+)")
#: What an edition prints on purpose that the vocabulary check would read as a
#: misread word, set aside before it: a possessive's s ("God's"), "&c.", "i.e.",
#: a reference's abbreviation ("v. 6", "ch. xv. 22", "Ps. lxxxix. 3", "St.",
#: Haydock's "Wi." for Witham), a roman chapter number before its verse, and a
#: capital roman numeral heading a point ("II. The").
_NOT_A_WORD = re.compile(
    r"(?<=[A-Za-z])['’]s\b|&c\.|\bi\.\s?e\.|\b(?:v|vv|ver|ch|Ch|chap|Ps|cf|ib|ibid|St|Dr|Mr|Wi)\."
    r"|\b[ivxlc]+\.(?=\s*\d)|\b[IVXLC]+\."
)


def verse_key(ref: str) -> tuple[int, int]:
    """'JHN.3.16', '3:16' or 'MRK.16.8.s2' -> its chapter and verse."""
    m = _VERSE_REF.search(ref)
    return int(m[1]), int(m[2])


def ref(verse: tuple[int, int]) -> str:
    """(3, 16) -> '3:16', the form selection.json and owb_sections.json key on."""
    return f"{verse[0]}:{verse[1]}"


def span(code: str, first: tuple[int, int], last: tuple[int, int], books: dict = BOOKS) -> str:
    """'John 1:1–5', 'John 1:1', 'John 7:53–8:11'."""
    name = books[code][0]
    if first == last:
        return f"{name} {ref(first)}"
    if first[0] == last[0]:
        return f"{name} {ref(first)}–{last[1]}"
    return f"{name} {ref(first)}–{ref(last)}"


def open_at(verses: dict[tuple[int, int], str]) -> set[tuple[int, int]]:
    """The verses that begin inside a double-quoted speech. Each mark is read by
    its place, not counted, on a stack of the quotations open. A double mark
    at the start of a verse or after a space or bracket opens; any other
    closes the innermost double quotation (and a single one open inside it).
    A single mark opens after a space, bracket or double mark and before a
    letter, and closes only a single quotation that is open, so an apostrophe
    ("king's") is never read as one. So a double mark inside a single inside a
    double is nested (Matthew 22:4, John 10:34) and closes only itself. OWB
    reopens a long speech at each new paragraph without closing the last
    (John 14–16): a double mark opening while a double quotation is innermost
    reopens it rather than nesting. Read across chapters, since that
    discourse crosses two of them."""
    out, stack = set(), []
    for v in sorted(verses):
        if '"' in stack:
            out.add(v)
        text = verses[v]
        for i, mark in enumerate(text):
            if mark not in "\"'":
                continue
            before = text[i - 1] if i else " "
            after = text[i + 1] if i + 1 < len(text) else " "
            if mark == '"':
                if before in " ([—":
                    if not stack or stack[-1] == "'":
                        stack.append('"')
                elif '"' in stack:
                    while stack.pop() != '"':
                        pass
            elif before in " ([—\"" and (after.isalnum() or after == '"'):
                stack.append("'")
            elif stack and stack[-1] == "'" and not after.isalnum():
                stack.pop()
    return out


def tidy(text: str) -> list[str]:
    """An excerpt's paragraphs, with only the scan's typography repaired (see
    TEXT in the module docstring). The words and their order are untouched."""
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text.strip()):
        # CCEL's Ryle sets an invisible byte-order mark beside a reference or a
        # quotation: just inside a bracket or quotation mark it goes, with its
        # space; anywhere else it stands for a space ("leprosy<BOM> was").
        raw = _BOM_INSIDE.sub(r"\1\2", raw).replace(BOM, " ")
        para = _SPACE_BEFORE.sub(r"\1", " ".join(raw.split()))
        para = space_quotes(para).replace(" - ", " — ")  # a spaced hyphen is the edition's dash
        if para:
            paragraphs.append(para)
    if paragraphs:
        paragraphs[0] = _LEADING_VERSE.sub("", paragraphs[0])
    return paragraphs


def vendor_owb(checkout: Path, code: str) -> None:
    """Write data/catena/<CODE>/owb_sections.json from an open-word-bible
    checkout: its English section headings (the passages) and chapter
    summaries, settings at their defaults, with the commit they came from."""
    import subprocess

    from library.management.commands.build_owb_book import heading_text, plain

    commit = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    headings = json.loads((checkout / "data" / "headings" / f"{code}.json").read_text("utf-8"))["headings"]
    summaries = json.loads((checkout / "data" / "summaries" / f"{code}.json").read_text("utf-8"))["summaries"]
    sections = [
        {"start": ref(verse_key(rid)), "title": heading_text(h["en"])}
        for rid, h in sorted(headings.items(), key=lambda kv: verse_key(kv[0]))
    ]
    out = {
        "_note": [
            "Vendored from the Open Word Bible (CC0, https://github.com/jdegreef/open-word-bible)",
            f"at commit {commit}: data/headings/{code}.json (English section headings, settings at their",
            f"defaults) and data/summaries/{code}.json (English chapter summaries). The catena's passages",
            "follow these sections; build_catena reads this file, never the OWB checkout.",
        ],
        "owb_commit": commit,
        "sections": sections,
        "summaries": {n: plain(s["en"] if isinstance(s, dict) else s) for n, s in summaries.items()},
    }
    folder = EDITORIAL / code
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "owb_sections.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")


class Command(BaseCommand):
    help = "Build a verse-by-verse catena on a book of the Bible from Logia's excerpts and the Open Word Bible."

    def add_arguments(self, parser):
        parser.add_argument("logia", help="path to logia-en.json (https://logia.faith/downloads/logia-en.json)")
        parser.add_argument("code", choices=sorted(BOOKS), help="the book, e.g. JHN")
        parser.add_argument(
            "--vendor-owb", metavar="CHECKOUT",
            help="first write data/catena/<CODE>/owb_sections.json from an open-word-bible checkout",
        )
        parser.add_argument(
            "--select", action="store_true",
            help="choose the excerpts afresh and rewrite selection.json (otherwise it is read)",
        )

    # --- inputs -------------------------------------------------------------

    def read_logia(self, path: str) -> dict:
        """Logia's file, its digest noted and its licence checked; every
        excerpt kept for `typed_counts`."""
        raw = Path(path).read_bytes()
        self.logia_sha = hashlib.sha256(raw).hexdigest()
        logia = json.loads(raw)
        del raw
        if logia.get("licence") != "CC0-1.0":
            raise CommandError(f"unexpected Logia licence {logia.get('licence')!r}")
        self.logia_excerpts = logia["excerpts"]
        return logia

    @cached_property
    def typed_counts(self) -> Counter:
        """Word counts over Logia's excerpts from typed (not scanned) editions,
        for `vocabulary`; tallied only when a build needs it."""
        typed = Counter()
        for e in self.logia_excerpts:
            if "archive.org" not in e.get("source_url", ""):
                typed.update(map(str.lower, english_audit._WORD.findall(e["text"])))
        return typed

    def load(self, path: str, code: str):
        logia = self.read_logia(path)
        self.code = code
        folder = EDITORIAL / code
        self.meta = json.loads((folder / "book.json").read_text("utf-8"))
        #: Logia author id -> (name on an excerpt, short work title, era), in the
        #: order they lived, which is the order they speak under a verse; the
        #: era spreads a passage's excerpts across the centuries.
        self.voices = {v["id"]: (v["name"], v["title"], v["era"]) for v in self.meta["voices"]}
        #: Logia author id -> the Logia work their excerpts come from, whose
        #: edition the back chapter names.
        self.work_of = {v["id"]: v["work"] for v in self.meta["voices"]}
        self.rank = {a: i for i, a in enumerate(self.voices)}
        self.authors = logia["authors"]
        self.works = logia["works"]
        missing = sorted(set(self.work_of.values()) - set(self.works))
        if missing:
            raise CommandError(f"book.json names works Logia lacks: {missing}")
        self.excerpts = {}
        for e in logia["excerpts"]:
            if e["start"].startswith(code + ".") and self.work_of.get(e["author"]) == e["work"]:
                e["_start"], e["_end"] = verse_key(e["start"]), verse_key(e["end"])
                e["_words"] = word_count(e["text"])
                self.excerpts[e["id"]] = e
        self.load_owb(code)
        self.folder = folder
        rejected = folder / "rejected.json"
        self.rejected = set(json.loads(rejected.read_text("utf-8"))["excerpts"]) if rejected.exists() else set()

    def load_owb(self, code: str) -> None:
        """The book's OWB verses, the Bible's commit, and its vendored sections."""
        number = self.books[code][1]
        verses, joined = _owb()
        # A verse OWB prints together with the one before it is quoted there.
        self.verses = {
            (vid // 1000 % 1000, vid % 1000): text
            for vid, text in verses.items()
            if vid // 1_000_000 == number and vid not in joined
        }
        with gzip.open(_OWB_PATH, "rt", encoding="utf-8") as fh:
            self.bible_commit = json.load(fh)["meta"]["commit"]
        self.owb = json.loads((EDITORIAL / code / "owb_sections.json").read_text("utf-8"))
        if self.owb["owb_commit"] != self.bible_commit:
            # Sections vendored from another OWB commit than the bundled text:
            # harmless while every passage still starts on a verse it has.
            have = {(vid // 1000 % 1000, vid % 1000) for vid in verses if vid // 1_000_000 == number}
            lost = [s["start"] for s in self.owb["sections"] if verse_key(s["start"]) not in have]
            if lost:
                raise CommandError(
                    f"owb_sections.json (OWB {self.owb['owb_commit'][:12]}) starts passages at verses the "
                    f"bundled text (OWB {self.bible_commit[:12]}) lacks: {lost[:5]}; re-vendor with --vendor-owb"
                )
            self.stderr.write(
                f"note: owb_sections.json is from OWB {self.owb['owb_commit'][:12]}, the bundled text from "
                f"{self.bible_commit[:12]}; every passage starts on a verse the text has"
            )

    def passages(self) -> list[tuple[str, list[tuple[int, int]]]]:
        """[(section title, its verses in order)] — every verse in one passage."""
        starts = [(verse_key(s["start"]), s["title"]) for s in self.owb["sections"]]
        ordered = sorted(self.verses)
        # A book's opening line may stand before OWB's first heading (Mark 1:1,
        # "The beginning of the good news…"); it opens the first passage.
        out = [(title, []) for _, title in starts]
        section = 0
        for v in ordered:
            while section + 1 < len(starts) and v >= starts[section + 1][0]:
                section += 1
            out[section][1].append(v)
        if any(not vs for _, vs in out):
            raise CommandError("an OWB section holds no verse")
        return out

    # --- selection ----------------------------------------------------------

    @cached_property
    def vocabulary(self) -> set[str]:
        """Every word the library already prints at least three times —
        english_audit's corpus counts, plus Logia's excerpts from editions that
        were typed rather than scanned (CCEL, tertullian.org) — lower-cased.

        Several editions reach Logia through archive.org's OCR (Lapide, Bengel,
        Ryle, Westcott), and the scan misreads a word now and then: "ma?i",
        "whicli", "Tiie". english_audit's classes do not see these, so the
        selection passes over any excerpt with a word outside this list. A rare
        real word ("fornicatrix") is turned away too; there are twenty
        excerpts for every one this book takes, so the cost is nil. A short
        word must be a real one: scanned books elsewhere in the library carry
        the odd "tt" or "fid"."""
        counts = english_audit.library_word_counts() + self.typed_counts
        return {w for w, n in counts.items() if n >= 3 and (len(w) > 2 or w in _SHORT_WORDS)}

    @staticmethod
    def debris(text: str) -> bool:
        """A misread letter, scan debris, a word split at a hyphen or two run
        together across a full stop: damage a typed edition can carry too."""
        return bool(
            _MISREAD.search(text)
            or _SCAN_NOISE.search(text)
            or english_audit.HYPHEN_SPACE.search(text)
            or english_audit.RUN_TOGETHER.search(text)
        )

    def damaged(self, text: str) -> bool:
        """The scan has broken something: `debris`, or a word outside `vocabulary`."""
        if self.debris(text):
            return True
        known = self.vocabulary
        return any(w.lower() not in known for w in english_audit._WORD.findall(_NOT_A_WORD.sub(" ", text)))

    def unfit(self, e: dict, verses: list[tuple[int, int]]) -> str | None:
        """Why an excerpt cannot stand in this passage, or None if it can. The
        one rule for both --select and an editor's hand-edited selection.json."""
        if not (verses[0] <= e["_start"] <= verses[-1] and e["_end"] <= verses[-1]):
            return "it comments on verses outside the passage"
        floor = MIN_WORDS_SHORT if e["author"] in SHORT_VOICES else MIN_WORDS
        if not floor <= e["_words"] <= MAX_WORDS:
            return f"it is {e['_words']} words long"
        if e["id"] in self.rejected:
            return "an editor turned it down (rejected.json)"
        if _NON_LATIN.search(e["text"]):
            return "it carries Greek or Hebrew, which the reader's fonts and listen mode stumble on"
        if self.damaged(e["text"]):
            return "the scan has damaged it"
        if e["text"].count('"') % 2:
            return "a quotation mark is unpaired: the scan lost one, and curling would guess"
        return None

    def candidates(self, verses: list[tuple[int, int]]) -> list[dict]:
        out = [e for e in self.excerpts.values() if not self.unfit(e, verses)]
        return sorted(out, key=lambda e: e["id"])

    def select(self, passages) -> list[list[str]]:
        overall = Counter()  # each voice's excerpts so far, across the book
        return [self.select_passage(verses, overall) for _, verses in passages]

    def select_passage(self, verses: list[tuple[int, int]], overall: Counter) -> list[str]:
        """The excerpt ids for one passage, in the order they were chosen."""
        pool = self.candidates(verses)
        per_verse = self.meta.get("words_per_verse", WORDS_PER_VERSE)
        budget = max(BUDGET_MIN, min(BUDGET_MAX, per_verse * len(verses)))
        eras, voices, at_verse = Counter(), Counter(), Counter()
        picks, used = [], 0

        def score(e):
            a = e["author"]
            era = self.voices[a][2]
            s = 3.0 if eras[era] == 0 else -float(eras[era])
            s += 2.0 if voices[a] == 0 else -2.0 * voices[a]
            s -= overall[a] / 40
            s -= abs(e["_words"] - IDEAL_WORDS) / 150
            s -= 2.0 * at_verse[e["_start"]]
            if _OPENS_MIDWAY.match(_LEADING_VERSE.sub("", e["text"].lstrip()).lstrip("“\"' ")):
                s -= 1.5  # reads as the middle of an argument
            return s

        def take(e):
            nonlocal used
            pool.remove(e)
            picks.append(e["id"])
            used += e["_words"]
            a = e["author"]
            eras[self.voices[a][2]] += 1
            voices[a] += 1
            at_verse[e["_start"]] += 1
            overall[a] += 1

        # First, one excerpt in each stretch of the passage, so the comment
        # follows the text from its first verse to its last rather than
        # pooling where the commentators wrote most. Each stretch gets its
        # share of the budget, so a long excerpt early in the passage
        # cannot starve the verses after it.
        slots = max(1, min(len(verses), round(budget / IDEAL_WORDS)))
        share = budget / slots
        for i in range(slots):
            window = verses[len(verses) * i // slots : len(verses) * (i + 1) // slots]
            here = [e for e in pool if window and window[0] <= e["_start"] <= window[-1]]
            fits = [e for e in here if e["_words"] <= share * 1.5] or here
            if fits:
                take(max(fits, key=lambda e: (score(e), e["id"])))
        # Then fill what the budget allows, wherever the best voices are.
        while pool and used < budget:
            best = max(pool, key=lambda e: (score(e), e["id"]))
            if picks and used + best["_words"] > budget * 1.15:
                break
            take(best)
        return picks

    # --- rendering ----------------------------------------------------------

    def text_block(self, code: str, verses: list[tuple[int, int]]) -> str:
        """Verses of the text as one quoted block, after OWB's note where a
        passage the oldest manuscripts lack begins in it."""
        note = ""
        for first, last, _ in DISPUTED:
            begins = verse_key(first)
            # An entry that begins inside a verse ("MRK.16.8.s2") is not a
            # whole verse to set a note above; build_catena_aurea places Mark's.
            if not first.startswith(code + ".") or first.count(".") > 2 or begins not in verses:
                continue
            if begins != verses[0]:  # the note belongs at the verse, not above the block
                at = verses.index(begins)
                return self.text_block(code, verses[:at]) + self.text_block(code, verses[at:])
            where = span(code, begins, verse_key(last), self.books)
            note = f"<p><em>{escape(DISPUTED_NOTE.format(book=self.books[code][0], ref=where))}</em></p>"
        text = " ".join(curl_singles(self.verses[v]) for v in verses)
        # A speech that runs on from the block before (Jesus to Nicodemus,
        # 3:10–21) reopens here, as a quotation running over several
        # paragraphs reopens each one — unless OWB's paragraph already does.
        if verses[0] in self.open_at and not text.startswith('"'):
            text = '"' + text
        cite = span(code, verses[0], verses[-1], self.books)
        return f"{note}<blockquote><p>{escape(text, quote=False)}</p><p>— {cite}</p></blockquote>"

    @cached_property
    def open_at(self) -> set[tuple[int, int]]:
        return open_at(self.verses)

    def order_key(self, e: dict):
        """Where an excerpt stands among those on the same verse: oldest voice first."""
        return (self.rank[e["author"]], e["id"])

    def excerpt_html(self, e: dict) -> str:
        name, work, _ = self.voices[e["author"]]
        parts = [f"<p><strong>{escape(name)}</strong> · <em>{escape(work)}</em></p>"]
        for para in tidy(e["text"]):
            parts.append(f"<p>{escape(curl_singles(_ELISION.sub('’', para)), quote=False)}</p>")
        return "\n".join(parts)

    def passage_html(self, code: str, title: str, verses, ids: list[str]) -> str:
        by_start = defaultdict(list)
        for i in ids:
            by_start[self.excerpts[i]["_start"]].append(self.excerpts[i])
        # The index of the last verse at or before a reference (a verse OWB
        # omits, like John 5:4, falls back to the one before it).
        def at_or_before(v):
            return max(n for n, w in enumerate(verses) if w <= v)

        out = [f"<h3>{escape(title)}</h3>"]
        position = 0
        starts = sorted(by_start)
        for k, start in enumerate(starts):
            group = sorted(by_start[start], key=self.order_key)
            # Quote the verses a group comments on, but never past the verse
            # before the next group's: an overview of 3:9–21 must not carry
            # 3:16 above Calvin's note on it.
            end = at_or_before(max(e["_end"] for e in group))
            if k + 1 < len(starts):
                end = min(end, at_or_before(starts[k + 1]) - 1)
            end = max(end, at_or_before(start))
            if end >= position:
                out.append(self.text_block(code, verses[position : end + 1]))
                position = end + 1
            out.extend(self.excerpt_html(e) for e in group)
        if position < len(verses):
            out.append(self.text_block(code, verses[position:]))
        return "\n".join(out)

    #: How a chapter summary introduces the voices heard in it.
    voices_label = "With"

    def voices_sentence(self, names: list[str]) -> str:
        """'With Augustine, Chrysostom, Calvin and 4 more.', or '' for none."""
        if len(names) > 3:
            voices = ", ".join(names[:3]) + f" and {len(names) - 3} more"
        elif len(names) > 1:
            voices = ", ".join(names[:-1]) + f" and {names[-1]}"
        elif names:
            voices = names[0]
        else:
            return ""
        return f"{self.voices_label} {voices}."

    def summary(self, number: int, names: list[str]) -> str:
        base = self.owb["summaries"][str(number)]
        sentence = self.voices_sentence(names)
        return f"{base} {sentence}" if sentence else base

    # --- main ---------------------------------------------------------------

    def handle(self, *args, **opts):
        code = opts["code"]
        if opts["vendor_owb"]:
            vendor_owb(Path(opts["vendor_owb"]), code)
        self.load(opts["logia"], code)
        passages = self.passages()
        starts = [ref(vs[0]) for _, vs in passages]
        selection_path = self.folder / "selection.json"
        if opts["select"]:
            chosen = self.select(passages)
            selection_path.write_text(
                json.dumps(
                    {
                        "_note": "Excerpt ids chosen by `build_catena --select`; edit one to swap an excerpt.",
                        "logia_sha256": self.logia_sha,
                        "passages": [
                            {"start": start, "title": t, "excerpts": ids}
                            for start, (t, _), ids in zip(starts, passages, chosen, strict=True)
                        ],
                    },
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
                "utf-8",
            )
        saved = json.loads(selection_path.read_text("utf-8"))["passages"]
        if [p["start"] for p in saved] != starts:
            raise CommandError("selection.json no longer matches the OWB sections — rerun with --select")
        chosen = [p["excerpts"] for p in saved]
        missing = [i for ids in chosen for i in ids if i not in self.excerpts]
        if missing:
            raise CommandError(f"selection.json names excerpts this Logia file lacks: {missing[:5]}")
        unfit = [
            f"{i} ({why})"
            for (_, verses), ids in zip(passages, chosen, strict=True)
            for i in ids
            if (why := self.unfit(self.excerpts[i], verses))
        ]
        if unfit:
            raise CommandError("selection.json names excerpts that cannot stand: " + "; ".join(unfit[:5]))

        chapters = defaultdict(list)
        for (title, verses), ids in zip(passages, chosen, strict=True):
            # Where most of its verses are: 7:53–8:11 belongs to John 8.
            home = Counter(c for c, _ in verses).most_common(1)[0][0]
            chapters[home].append((title, verses, ids))

        bodies = [("Introduction", (self.folder / "introduction.html").read_text("utf-8"), "")]
        used = Counter()
        for number in sorted(chapters):
            html = "\n".join(self.passage_html(code, *p) for p in chapters[number])
            authors = Counter(self.excerpts[i]["author"] for _, _, ids in chapters[number] for i in ids)
            used.update(authors)
            names = [self.voices[a][0] for a in self.voices if a in authors]
            title = self.books[code][2].format(n=number)
            bodies.append((title, html, self.summary(number, names)))
        bodies.append(("The Voices and Their Books", self.voices_html(used), ""))
        book = self.write(bodies)
        english_audit.report(self, english_audit.audit_book(book), book.slug)

    def voices_html(self, used: Counter) -> str:
        """The back chapter: the editorial account of each voice, then the
        edition every excerpt was copied from."""
        intro = (self.folder / "voices.html").read_text("utf-8")
        rows = ["<h2>The editions</h2>"]
        for a in self.voices:
            if not used[a]:
                continue
            work = self.works[self.work_of[a]]
            detail = (work.get("translation") or work.get("edition") or "").rstrip(".")
            rows.append(
                f"<p><strong>{escape(self.authors[a]['name'])}</strong>, "
                f"<em>{escape(curl_singles(work['title']), quote=False)}</em>. "
                f"{escape(curl_singles(detail), quote=False)}. "
                f"{used[a]} excerpt{'s' if used[a] != 1 else ''} in this book.</p>"
            )
        rows.append(
            "<p>Every excerpt was gathered by Logia (logia.faith), which copies each one word for word "
            "from the public-domain edition above and offers the collection under CC0. "
            f"{self.bible_note()}</p>"
        )
        return intro + "\n" + "\n".join(rows)

    #: The books this command builds (a subclass may add one, as
    #: build_catena_aurea adds Mark).
    books = BOOKS
    author_slug = AUTHOR_SLUG

    def bible_note(self) -> str:
        """The back chapter's sentence on the Bible text, named per book (BOOKS)."""
        return (
            f"{self.books[self.code][3]} is the Open Word Bible (openwordbible.org), "
            "English, Balanced level, also CC0."
        )

    def attribution(self) -> str:
        return (
            f"Commentary excerpts from Logia ({LOGIA}, CC0), each from a public-domain edition; "
            f"{self.scripture_credit()}"
        )

    def scripture_credit(self) -> str:
        return (
            f"Scripture from the Open Word Bible (https://openwordbible.org), English, Balanced level, "
            f"commit {self.bible_commit[:12]}: dedicated to the public domain under CC0"
        )

    def extra_fields(self) -> dict:
        """Book fields a subclass sets beyond the shared ones (a series, say)."""
        return {}

    @transaction.atomic
    def write(self, bodies):
        meta = self.meta
        try:
            author = Author.objects.get(slug=self.author_slug)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {self.author_slug!r} not in the DB — loaddata authors.json first.") from exc
        slug = meta["slug"]
        content = {
            "author": author,
            "title": meta["title"],
            "subtitle": meta.get("subtitle", ""),
            "cover_title": meta.get("cover_title", ""),
            "cover_byline": meta.get("cover_byline", ""),
            "description": meta["description"],
            "qa": meta.get("qa", []),
            "cover_url": meta.get("cover_url", ""),
            "cover_color": meta["cover_color"],
            "source_url": f"{LOGIA}/",
            "attribution": self.attribution(),
            **self.extra_fields(),
        }
        book, _ = Book.objects.update_or_create(
            slug=slug,
            language=LANGUAGE,
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(slug),
            },
        )
        book.chapters.all().delete()
        total = 0
        for order, (title, body, summary) in enumerate(bodies, start=1):
            cleaned = clean_fragment(body)
            curled, _ = convert(cleaned, outer_guillemets=False)
            assert_punctuation_only(cleaned, curled, f"{slug} {title}")
            chapter = Chapter.objects.create(
                book=book,
                order=order,
                title=title,
                body_html=settled_chapter_body(slug, order, curled),
                summary=summary,
            )
            total += chapter.word_count
        self.stdout.write(f"built {slug}: {len(bodies)} chapters, {total} words (Logia sha256 {self.logia_sha[:12]})")
        return book
