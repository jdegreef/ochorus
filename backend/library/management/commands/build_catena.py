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
editor can swap an excerpt by editing one id. `--refill` mends a shipped
book instead of reshuffling it: it drops only the pinned excerpts that can no
longer stand (a tightened filter, a new rejected.json entry) and tops up just
the passages that lost one. The rule, per passage: a word
budget in proportion to its verses; then, greedily, the excerpt that adds an
era and a voice the passage does not have yet, reads at a comfortable length,
spreads across the passage's verses, and keeps any one commentator from
crowding the book. An excerpt is never chosen if the scan has damaged it
(see `vocabulary`), if it carries Greek or Hebrew, or if an editor has turned
it down in `rejected.json`. Aquinas's Catena Aurea is left out on purpose — it is
itself a chain of the Fathers, and would repeat Augustine and Chrysostom.
A voice marked "lead": true in book.json is leaned towards (Spurgeon in the
Psalms).

TEXT. Each excerpt is the source's words in the source's order. Only
typography is touched: whitespace collapsed, the scan's spaces before
punctuation and inside quotation marks (straight or curled) closed up, a
stray byte-order mark and a leading verse number dropped, quotation marks
curled the house way. Old spelling and the commentators' own Bible wording (usually the King James) stand as printed.

VERSIFICATION. The text is numbered as English Bibles number it. A commentary
need not be: Logia keys each excerpt as its source edition did, and in the
Psalms that is usually the HEBREW numbering, where a psalm's title is verse 1
(or verses 1–2), so every verse after it runs one or two ahead of the English.
book.json's "versification" names each work's scheme — "english" (the
default), "hebrew" (read through OWB's own WLC-to-English map, vendored into
owb_sections.json as `english_versification`; a ref that maps to no English
verse, a title, attaches to verse 1), "english+N" (a slip: keys N ahead of the
English) or "skip" (leave the work out) — and may override it per chapter
(`{"scheme": "hebrew", "chapters": {"68": "english"}}`). `_start`/`_end` are the
English verses; the scheme is applied when the excerpts are loaded. What Logia
did for the Psalms, checked work by work against the verse numbers the
excerpts print and against the words they quote (data/catena/PSA/book.json):

* every work: Hebrew/English PSALM numbers, already normalised — Augustine's
  and Bellarmine's Vulgate "Psalm 22" is keyed PSA.23, and the Vulgate's joined
  Psalm 9 is split again (Augustine's "Why, O Lord, hast Thou withdrawn afar
  off?" is PSA.10.1).
* every work: HEBREW VERSE numbers. Spurgeon's PSA.46.2 prints "1. God is our
  refuge" (English 46:1); Augustine's PSA.3.2 quotes "(ver. 1)"; Calvin's
  PSA.3.5 prints "4."; Fausset's PSA.42.6 prints "5."; Henry's PSA.3.6 cites
  "(v. 5)"; Bellarmine's PSA.46.2 is headed "Our God is our refuge and
  strength"; Delitzsch prints the Hebrew number himself ("Ver. 9" for 4:8).
* the exceptions, by chapter: Spurgeon's Psalm 68 is keyed in English (PSA.68.1
  is "1. Let God arise"); his Psalms 15 and 29 run one ahead of the English
  (PSA.29.2 is "1. Give") and 44 two ahead (PSA.44.3 is "1. We have heard");
  Bellarmine's Psalm 72 is keyed one behind from verse 3 on, so it is skipped.

LAYOUT. One chapter per Bible chapter, between an introduction and a back
chapter on the voices and their editions (both Ochorus's own writing, in
`data/catena/<CODE>/`). In a chapter, each OWB section is an `<h3>`; under it
the verses run in order as quoted blocks, each followed by the excerpts that
comment on it. Every verse is quoted exactly once. In the back chapter's
list of editions, a voice's "edition" in book.json may reword Logia's
catalogue note (scan identifiers, a translator's apology).

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
#: The score's lean towards a book's leading voice: enough to be heard in most
#: passages, not enough to outweigh a fresh era.
LEAD_BONUS = 1.5

#: Scan debris: stray asterisks, bars and carets, a degree sign, angle brackets.
_SCAN_NOISE = re.compile(r"[*|^°<>{}]")
#: A letter run broken by ? or ! or a digit inside a word: "ma?i", "c0me".
_MISREAD = re.compile(r"[a-z][?!][a-z]|[a-z]\d|\d[a-z]{3,}")
#: An exclamation mark read as "I" or "1" ("the Mount I The word", "O sinner 1
#: Take heed", "weepest thou 7 This"), a "0" for "O" ("Thou, 0 Lord"): a lone
#: figure or capital I between a word and a capitalised one, unless it numbers
#: a book (1 Samuel) or is the pronoun before a capitalised one ("I Am").
_MISREAD_MARK = re.compile(
    r"(?<=[a-z,;:]) \d (?=[A-Z][a-z])(?!Sam|Kings?\b|Kgs|Chr|Cor|Thes|Tim|Pet|John|Jn|Joh|Macc|Esd)"
    r"|(?<=[a-z,;:]) [Il] (?=[A-Z][a-z])(?!Am\b|Myself|Thee|Thou|Thy|Him|His|He\b|Me\b|My\b)"
    r"|(?<!\d[.,]) 0 (?=[A-Za-z])"
    r"""|(?<=[a-z]) [1I7] (?=["“”])"""
)
#: A quotation mark the scan has broken: a doubled single mark for a double
#: one ("‘‘ Happy,” says he").
_BROKEN_MARK = re.compile(r"‘‘|’’|''|``|‘“|“‘")
#: A closing single mark (not an apostrophe inside a word): more opening marks
#: than these means the scan read a double mark as a single (‘hell, ‘here).
_CLOSING_SINGLE = re.compile(r"’(?![A-Za-z])")
#: An excerpt that ends a sentence, not one Logia cut at a comma.
_ENDS_WHOLE = re.compile(r"""[.!?…][”’")\]]*\s*$""")
#: Slips only a scan makes, sought in scanned editions alone: a stop or comma
#: glued between two words ("goes.on", "especially;.and"), a lower-case word
#: after a full stop that ends no abbreviation ("lays. low", "to. no. one"),
#: a figure for a word ("had 80 often"), a dollar sign, an accent no English
#: word has ("theréat"), a hyphen joining two lower-case words ("and-crime"),
#: a running head ("ON THE PSALMS."), doubled punctuation ("xiii,,"), a figure
#: for a letter ("7'o thee", "saying, 1 pray"), a stray bullet, a doubled word,
#: a full stop set before a word ("the .Evangelist", which tidy would glue).
_SCAN_SLIP = re.compile(
    r"[a-z][.;:,]{1,2}[a-z]{2,}"
    r"|(?<![A-Za-z])(?!(?:cf|viz|ver|vers|ch|chap|sq|sqq|comp|ib|ibid|al|etc|ed|vol|p|pp|v|vv|ii?i?|iv|vi|i\.e|e\.g)\.)"
    r"[a-z]{2,}\. [a-z]{2,}"
    r"|[a-z] \d+ [a-z]{2,}\b(?<!\bto)"
    r"|\$|[a-z][éèêëàâîïôûç][a-z]|\b(?:and|or|the)-[a-z]|[a-z]-(?:and|or|the)\b"
    r"|\b[A-Z]{2,}(?: [A-Z]{2,})+\."
    r"|,[,.]|\d'[a-z]|(?<=[,;:] )[1l] (?=[a-z])"
    r"|[•■□▪]|\b(?P<word>[a-z]{2,}) (?P=word)\b| \.[A-Za-z]"
)
#: A word a scan broke in two at the end of a line ("faith fulness", "con
#: founding", "them selves"): two pieces that make a known word, one of them a
#: piece no one writes alone in these books.
_PAIR = re.compile(r"\b([A-Za-z]+) (?=([a-z]+)\b)")
_SUFFIXES = frozenset({
    "ness", "ship", "ment", "ments", "tion", "tions", "sion", "sions", "ance", "ence", "ing", "ings",
    "ful", "fully", "fulness", "selves", "ly", "ity", "ous", "ously", "hood", "dom", "able", "ible",
    "tude", "haps", "fore", "kind", "standing", "hanging", "vidence", "fidence", "tended",
})
_PREFIXES = frozenset({"con", "com", "pre", "pro", "sub", "extra", "per", "dis", "inter", "trans", "salva"})
_SHORT_WORDS = frozenset({
    "a", "i", "o", "ah", "am", "an", "as", "at", "be", "by", "do", "go", "ha", "he", "ho", "if", "in",
    "is", "it", "lo", "me", "my", "no", "of", "oh", "on", "or", "ox", "so", "to", "up", "us", "we", "ye",
})
_NON_LATIN = re.compile(r"[Ͱ-Ͽἀ-῿֐-׿]")
_OPENS_MIDWAY = re.compile(r"^(?:and|but|or|nor|so|for|yet|then|thus|hence|therefore)\b", re.I)
_LEADING_VERSE = re.compile(r"^(?:(?:Ver|Verse)\.?\s*)?\d+\.\s+(?=\S)")
_SPACE_BEFORE = re.compile(r"\s+([,;:.?!)\]])")
#: A space the scan put inside a curled double mark (“ prevented,” in Bellarmine).
_SPACE_IN_CURLED = re.compile(r"“\s+|\s+”")
BOM = "\ufeff"
#: A byte-order mark just inside a bracket or a curled quotation mark, with
#: the space it carries.
_BOM_INSIDE = re.compile(r"([(\[“‘])\ufeff\s*|\s*\ufeff\s*([”’])")
#: An old elision's apostrophe ('tis, 'twas, 'em), which curl_singles would
#: otherwise read as an opening quotation mark after a space.
_ELISION = re.compile(r"(?<!\w)'(?=(?:tis|twas|twere|twill|twould|em|gainst|neath|mongst)\b)", re.I)
_VERSE_REF = re.compile(r"(\d+)[.:](\d+)")
#: A versification scheme in book.json: "english", "hebrew", "english+1" or "skip".
_SCHEME = re.compile(r"(english|hebrew|skip)(?:\+(\d+))?")
#: What an edition prints on purpose that the vocabulary check would read as a
#: misread word, set aside before it: a possessive's s ("God's"), "&c.", "i.e.",
#: a reference's abbreviation ("v. 6", "ch. xv. 22", "Ps. lxxxix. 3", "St.",
#: Haydock's "Wi." for Witham), a roman chapter number before its verse, and a
#: capital roman numeral heading a point ("II. The").
_NOT_A_WORD = re.compile(
    r"(?<=[A-Za-z])['’](?:s|t|d|ll|ve|re|st)\b|&c\.|\bi\.\s?e\.|\b(?:v|vv|ver|vers|ch|Ch|chap|Ps|Pss|cf|comp|"
    r"sq|sqq|ib|ibid|viz|St|Dr|Mr|Wi|Ge|Gen|Ex|Le|Nu|Num|De|Deut|Jos|Sa|Sam|Ki|Kgs|Chr|Ne|Neh|Es|Pr|Prov|Ec|"
    r"Eccl|Isa|Jer|La|Eze|Ezek|Da|Dan|Ho|Hos|Joe|Am|Ob|Jon|Mic|Na|Hab|Zep|Hag|Zec|Zech|Mal|Mt|Matt|Mr|Mk|Lu|"
    r"Lk|Joh|Jn|Ac|Ro|Rom|Co|Cor|Ga|Gal|Eph|Php|Phil|Col|Thess|Ti|Tim|Tit|Heb|Jas|Pe|Pet|Jud|Rev)\."
    r"|\b[ivxlc]+[.,;:)]|\b[IVXLC]+\."
)


def verse_key(ref: str) -> tuple[int, int]:
    """'JHN.3.16', '3:16' or 'MRK.16.8.s2' -> its chapter and verse."""
    m = _VERSE_REF.search(ref)
    return int(m[1]), int(m[2])


def ref(verse: tuple[int, int]) -> str:
    """(3, 16) -> '3:16', the form selection.json and owb_sections.json key on."""
    return f"{verse[0]}:{verse[1]}"


def span(code: str, first: tuple[int, int], last: tuple[int, int]) -> str:
    """'John 1:1–5', 'John 1:1', 'John 7:53–8:11'."""
    name = BOOKS[code][0]
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
        para = _SPACE_IN_CURLED.sub(lambda m: m[0].strip(), para)
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

    from library.management.commands.build_owb_book import (
        english_versification,
        heading_text,
        plain,
    )

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
    # Where the book's source numbering is not the English (a psalm's title is
    # its first verse in Hebrew), the map from one to the other (VERSIFICATION).
    english = {
        k: v for k, v in sorted(english_versification(checkout).items(), key=lambda kv: verse_key(kv[0]))
        if k.startswith(code + ".")
    }
    if english:
        out["_note"].append(
            f"english_versification: data/versification.json's \"english\" map (WLC verse -> English verses) for {code}."
        )
        out["english_versification"] = english
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
            "--refill", action="store_true",
            help="mend selection.json: drop the excerpts that can no longer stand, top up only those passages",
        )
        parser.add_argument(
            "--select", action="store_true",
            help="choose the excerpts afresh and rewrite selection.json (otherwise it is read)",
        )

    # --- inputs -------------------------------------------------------------

    def load(self, path: str, code: str):
        raw = Path(path).read_bytes()
        self.logia_sha = hashlib.sha256(raw).hexdigest()
        logia = json.loads(raw)
        del raw
        if logia.get("licence") != "CC0-1.0":
            raise CommandError(f"unexpected Logia licence {logia.get('licence')!r}")
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
        #: The voice the book leads with, and editions book.json words itself.
        self.lead = {v["id"] for v in self.meta["voices"] if v.get("lead")}
        self.editions = {v["id"]: v["edition"] for v in self.meta["voices"] if v.get("edition")}
        self.rank = {a: i for i, a in enumerate(self.voices)}
        self.authors = logia["authors"]
        self.works = logia["works"]
        missing = sorted(set(self.work_of.values()) - set(self.works))
        if missing:
            raise CommandError(f"book.json names works Logia lacks: {missing}")
        self.owb = json.loads((folder / "owb_sections.json").read_text("utf-8"))
        to_english = self.versification(code)
        self.excerpts = {}
        typed = Counter()
        for e in logia["excerpts"]:
            if "archive.org" not in e.get("source_url", ""):
                typed.update(map(str.lower, english_audit._WORD.findall(e["text"])))
            if e["start"].startswith(code + ".") and self.work_of.get(e["author"]) == e["work"]:
                e["_start"], e["_end"] = to_english(e["work"], e["start"], e["end"])
                if e["_start"] is None or e["_end"] is None:
                    continue
                e["_words"] = word_count(e["text"])
                self.excerpts[e["id"]] = e
        self.typed_counts = typed
        number = BOOKS[code][1]
        verses, joined = _owb()
        # A verse OWB prints together with the one before it is quoted there.
        self.verses = {
            (vid // 1000 % 1000, vid % 1000): text
            for vid, text in verses.items()
            if vid // 1_000_000 == number and vid not in joined
        }
        with gzip.open(_OWB_PATH, "rt", encoding="utf-8") as fh:
            self.bible_commit = json.load(fh)["meta"]["commit"]
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
        self.folder = folder
        rejected = folder / "rejected.json"
        self.rejected = set(json.loads(rejected.read_text("utf-8"))["excerpts"]) if rejected.exists() else set()

    def versification(self, code: str):
        """A function (work id, start ref, end ref) -> an excerpt's first and
        last verse in English numbering, or None for a work skipped there, by
        the scheme book.json names for its work (VERSIFICATION in the module
        docstring). A work's value is a scheme, or {"scheme": ..., "chapters":
        {"68": ...}} for a work whose keys change scheme in a few chapters."""
        schemes = self.meta.get("versification", {})
        english = self.owb.get("english_versification", {})
        if schemes and not english and any(s != "english" for s in schemes.values()):
            raise CommandError("book.json names a versification but owb_sections.json has no map: --vendor-owb")

        def scheme(work: str, chapter: int) -> tuple[str, int]:
            s = schemes.get(work, "english")
            if isinstance(s, dict):
                s = s.get("chapters", {}).get(str(chapter), s["scheme"])
            m = _SCHEME.fullmatch(s)
            if not m or (m[1] != "english" and m[2]):
                raise CommandError(f"unknown versification {s!r} for {work}")
            return m[1], int(m[2] or 0)

        def convert(work: str, ref_: str, last: bool) -> tuple[int, int] | None:
            verse = verse_key(ref_)
            name, ahead = scheme(work, verse[0])
            if name == "skip":
                return None
            if name == "english":
                return (verse[0], max(1, verse[1] - ahead))
            mapped = english.get(f"{code}.{verse[0]}.{verse[1]}")
            if mapped is None:
                return verse  # numbered alike in both
            if not mapped:
                return (verse[0], 1)  # a psalm's title: it belongs with the first verse
            return verse_key(mapped[-1] if last else mapped[0])

        return lambda work, start, end: (convert(work, start, False), convert(work, end, True))

    def passages(self) -> list[tuple[str, list[tuple[int, int]]]]:
        """[(section title, its verses in order)] — every verse in one passage."""
        starts = [(verse_key(s["start"]), s["title"]) for s in self.owb["sections"]]
        ordered = sorted(self.verses)
        if ordered[0] < starts[0][0]:
            raise CommandError("the OWB sections start after the book does")
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

    def damaged(self, e: dict) -> bool:
        """The scan has broken something: a misread word or mark (_MISREAD,
        _MISREAD_MARK), debris, a broken or unpaired quotation mark, a word split
        at a hyphen or two run together across a full stop — or Logia cut the
        excerpt off mid-sentence. In a scanned edition also the slips only a
        scan makes (_SCAN_SLIP), a word broken in two at a line's end
        (_SUFFIXES, _PREFIXES), and any word outside the vocabulary; a typed
        edition (CCEL) is spared that last, which mostly turns away its
        abbreviations and rare real words."""
        text = e["text"]
        if (
            _MISREAD.search(text)
            or _MISREAD_MARK.search(text)
            or _BROKEN_MARK.search(text)
            or text.count("“") != text.count("”")
            or text.count("‘") > len(_CLOSING_SINGLE.findall(text))
            or not _ENDS_WHOLE.search(text)
            or _SCAN_NOISE.search(text)
            or english_audit.HYPHEN_SPACE.search(text)
            or english_audit.RUN_TOGETHER.search(text)
        ):
            return True
        if "archive.org" not in e.get("source_url", ""):
            return False
        if _SCAN_SLIP.search(text):
            return True
        known = self.vocabulary
        for m in _PAIR.finditer(text):
            first, second = m[1].lower(), m[2]
            if (second in _SUFFIXES or first in _PREFIXES) and first + second in known:
                return True
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
        if self.damaged(e):
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

    def refill(self, passages, pinned: list[list[str]]) -> tuple[list[list[str]], list[int]]:
        """The committed selection, mended: every pinned excerpt that can no
        longer stand (the damage filter, rejected.json) is dropped, and a
        passage that lost one is topped up to its budget by the same rule,
        counting the picks it keeps and the voices the whole book already
        has. Every other passage is left exactly as it was. Returns the new
        selection and the indexes of the passages it touched."""
        kept = [[i for i in ids if i in self.excerpts and not self.unfit(self.excerpts[i], vs)]
                for (_, vs), ids in zip(passages, pinned, strict=True)]
        overall = Counter(self.excerpts[i]["author"] for ids in kept for i in ids)
        out, touched = [], []
        for n, ((_, verses), ids, keep) in enumerate(zip(passages, pinned, kept, strict=True)):
            if keep == ids:
                out.append(ids)
                continue
            touched.append(n)
            out.append(self.select_passage(verses, overall, keep))
        return out, touched

    def select_passage(self, verses: list[tuple[int, int]], overall: Counter, kept: list[str] = ()) -> list[str]:
        """The excerpt ids for one passage, in the order they were chosen,
        after any `kept` (already counted in `overall`), which stand first."""
        pool = [e for e in self.candidates(verses) if e["id"] not in kept]
        per_verse = self.meta.get("words_per_verse", WORDS_PER_VERSE)
        budget = max(BUDGET_MIN, min(BUDGET_MAX, per_verse * len(verses)))
        eras, voices, at_verse = Counter(), Counter(), Counter()
        picks, used = list(kept), 0
        for i in kept:
            e = self.excerpts[i]
            used += e["_words"]
            eras[self.voices[e["author"]][2]] += 1
            voices[e["author"]] += 1
            at_verse[e["_start"]] += 1

        def score(e):
            a = e["author"]
            era = self.voices[a][2]
            s = 3.0 if eras[era] == 0 else -float(eras[era])
            s += 2.0 if voices[a] == 0 else -2.0 * voices[a]
            s -= overall[a] / 40
            if a in self.lead:
                s += LEAD_BONUS
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
            if any(window and window[0] <= self.excerpts[i]["_start"] <= window[-1] for i in kept):
                continue  # a kept pick already speaks here
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
            if not first.startswith(code + ".") or begins not in verses:
                continue
            if begins != verses[0]:  # the note belongs at the verse, not above the block
                at = verses.index(begins)
                return self.text_block(code, verses[:at]) + self.text_block(code, verses[at:])
            where = span(code, begins, verse_key(last))
            note = f"<p><em>{escape(DISPUTED_NOTE.format(book=BOOKS[code][0], ref=where))}</em></p>"
        text = " ".join(curl_singles(self.verses[v]) for v in verses)
        # A speech that runs on from the block before (Jesus to Nicodemus,
        # 3:10–21) reopens here, as a quotation running over several
        # paragraphs reopens each one — unless OWB's paragraph already does.
        if verses[0] in self.open_at and not text.startswith('"'):
            text = '"' + text
        cite = span(code, verses[0], verses[-1])
        return f"{note}<blockquote><p>{escape(text, quote=False)}</p><p>— {cite}</p></blockquote>"

    @cached_property
    def open_at(self) -> set[tuple[int, int]]:
        return open_at(self.verses)

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
            group = sorted(by_start[start], key=lambda e: (self.rank[e["author"]], e["id"]))
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

    def summary(self, number: int, names: list[str]) -> str:
        base = self.owb["summaries"][str(number)]
        if len(names) > 3:
            voices = ", ".join(names[:3]) + f" and {len(names) - 3} more"
        elif len(names) > 1:
            voices = ", ".join(names[:-1]) + f" and {names[-1]}"
        elif names:
            voices = names[0]
        else:
            return base
        return f"{base} With {voices}."

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
        elif opts["refill"]:
            pinned = json.loads(selection_path.read_text("utf-8"))
            if [p["start"] for p in pinned["passages"]] != starts:
                raise CommandError("selection.json no longer matches the OWB sections — rerun with --select")
            chosen, touched = self.refill(passages, [p["excerpts"] for p in pinned["passages"]])
            for p, ids in zip(pinned["passages"], chosen, strict=True):
                p["excerpts"] = ids
            selection_path.write_text(json.dumps(pinned, ensure_ascii=False, indent=1) + "\n", "utf-8")
            self.stdout.write(f"refilled {len(touched)} of {len(passages)} passages")
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
            title = BOOKS[code][2].format(n=number)
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
            detail = (self.editions.get(a) or work.get("translation") or work.get("edition") or "").rstrip(".")
            rows.append(
                f"<p><strong>{escape(self.authors[a]['name'])}</strong>, "
                f"<em>{escape(curl_singles(work['title']), quote=False)}</em>. "
                f"{escape(curl_singles(detail), quote=False)}. "
                f"{used[a]} excerpt{'s' if used[a] != 1 else ''} in this book.</p>"
            )
        rows.append(
            "<p>Every excerpt was gathered by Logia (logia.faith), which copies each one word for word "
            "from the public-domain edition above and offers the collection under CC0. "
            f"{BOOKS[self.code][3]} is the Open Word Bible (openwordbible.org), "
            "English, Balanced level, also CC0.</p>"
        )
        return intro + "\n" + "\n".join(rows)

    @transaction.atomic
    def write(self, bodies):
        meta = self.meta
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first.") from exc
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
            "attribution": (
                f"Commentary excerpts from Logia ({LOGIA}, CC0), each from a public-domain edition; "
                f"Scripture from the Open Word Bible (https://openwordbible.org), English, Balanced level, "
                f"commit {self.bible_commit[:12]}: dedicated to the public domain under CC0"
            ),
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
