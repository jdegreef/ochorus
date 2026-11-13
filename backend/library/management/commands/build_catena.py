"""Build a catena on a book of the Bible: its text, passage by passage, with the Church's
commentators speaking under each verse, oldest first.

A *catena* ("chain") is the old way of reading Scripture slowly: under every
verse, excerpts from the great commentators, one after another. This command
builds one as a library book from two CC0 sources. Which commentators speak,
under what short work title and from which era, is the book's own editorial
choice, listed in `data/catena/<CODE>/book.json` ("voices"); a new book is a new
folder there (`--vendor-owb` writes its passages) and an entry in BOOKS.

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
book.json can tune this per book: "words_per_verse" (default 90; the Psalms,
2,460 verses, take 35), a voice's "lead": true (the score leans to it: Spurgeon
in the Psalms), and "scan_filter": 2, the finer reading of scans described in
`damaged` (the Catena on John keeps the first, so its selection stands).

TEXT. Each excerpt is the source's words in the source's order. Only
typography is touched: whitespace collapsed, the scan's spaces before
punctuation and inside quotation marks closed up, a leading verse number
dropped, quotation marks curled the house way. Old spelling and the
commentators' own Bible wording (usually the King James) stand as printed.

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
list of editions, book.json's "scripture_credit" names the text ("The Gospel
text" by default) and a voice's "edition" may reword Logia's catalogue note.

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
#: begins, OWB book number, a chapter's title with {n} for its number).
BOOKS = {
    "PSA": ("Psalm", 19, "Psalm {n}"),
    "MAT": ("Matthew", 40, "Matthew {n}"),
    "MRK": ("Mark", 41, "Mark {n}"),
    "LUK": ("Luke", 42, "Luke {n}"),
    "JHN": ("John", 43, "John {n}"),
    "ROM": ("Romans", 45, "Romans {n}"),
}

#: OWB's note on a passage the oldest manuscripts lack (build_owb_book.DISPUTED
#: lists them), worded for this book, which does not bracket it.
DISPUTED_NOTE = (
    "The earliest manuscripts of {book} do not have {ref}. Most Bibles print it, "
    "and so does this book, in the place it has always stood."
)

#: Words of commentary per verse of text (book.json "words_per_verse" may set
#: its own), and a passage's floor and ceiling.
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
#: Take heed"), a "0" for "O" ("Thou, 0 Lord"), or a quotation mark read as
#: "6" — a lone figure or capital I between a word and a capitalised one,
#: unless it numbers a book (1 Samuel) or is the pronoun before a divine name
#: or a capitalised pronoun ("I Am", "I Myself").
_MISREAD_MARK = re.compile(
    r"(?<=[a-z,;:]) \d (?=[A-Z][a-z])(?!Sam|Kings?\b|Kgs|Chr|Cor|Thes|Tim|Pet|John|Jn|Joh|Macc|Esd)"
    r"|(?<=[a-z,;:]) [Il] (?=[A-Z][a-z])(?!Am\b|Myself|Thee|Thou|Thy|Him|His|He\b|Me\b|My\b)"
    r"|(?<!\d[.,]) 0 (?=[A-Za-z])"
    r"""|(?<=[a-z]) [1I7] (?=["“”])"""
)
#: A quotation mark the scan has broken: a doubled single mark for a double
#: one ("‘‘ Happy,” says he"), or more curled opening marks than closing.
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
#: a running head ("ON THE PSALMS."), doubled punctuation ("xiii,,"), and a
#: figure for a letter ("7'o thee", "saying, 1 pray").
_SCAN_SLIP = re.compile(
    r"[a-z][.;:,]{1,2}[a-z]{2,}"
    r"|(?<![A-Za-z])(?!(?:cf|viz|ver|vers|ch|chap|sq|sqq|comp|ib|ibid|al|etc|ed|vol|p|pp|v|vv|ii?i?|iv|vi|i\.e|e\.g)\.)"
    r"[a-z]{2,}\. [a-z]{2,}"
    r"|[a-z] \d+ [a-z]{2,}\b(?<!\bto)"
    r"|\$|[a-z][éèêëàâîïôûç][a-z]|\b(?:and|or|the)-[a-z]|[a-z]-(?:and|or|the)\b"
    r"|\b[A-Z]{2,}(?: [A-Z]{2,})+\."
    r"|,[,.]|\d'[a-z]|(?<=[,;:] )[1l] (?=[a-z])"
    r"|[•■□▪]|\b(?P<word>[a-z]{2,}) (?P=word)\b"
)
#: A word the scan broke in two at the end of a line ("faith fulness", "con
#: founding", "them selves"): two pieces that make a known word, one of them
#: a piece no one writes alone in these books.
_SUFFIXES = frozenset({
    "ness", "ship", "ment", "ments", "tion", "tions", "sion", "sions", "ance", "ence", "ing", "ings",
    "ful", "fully", "fulness", "selves", "ly", "ity", "ous", "ously", "hood", "dom", "able", "ible",
    "tude", "haps", "fore", "kind", "standing", "hanging", "vidence", "fidence", "tended",
})
_PAIR = re.compile(r"\b([A-Za-z]+) (?=([a-z]+)\b)")
_PREFIXES = frozenset({"con", "com", "pre", "pro", "sub", "extra", "per", "dis", "inter", "trans", "salva"})

#: What a word outside the vocabulary may be under scan_filter 2: the tail of
#: an elision or possessive, a Roman numeral, or the abbreviation in a reference.
_CLITICS = frozenset({"s", "t", "d", "ll", "ve", "re", "st"})
_ROMAN = re.compile(r"(?=[mdclxvi])m*(?:c[md]|d?c{0,3})(?:x[cl]|l?x{0,3})(?:i[xv]|v?i{0,3})")
_ABBREVIATIONS = frozenset({
    "ps", "pss", "v", "vv", "ver", "vers", "cf", "comp", "ch", "chap", "sq", "sqq", "ib", "ibid",
    "viz", "ge", "gen", "ex", "le", "nu", "num", "de", "deut", "jos", "sa", "sam", "ki", "kgs",
    "chr", "ne", "neh", "es", "pr", "prov", "ec", "eccl", "isa", "jer", "la", "eze", "ezek",
    "da", "dan", "ho", "hos", "joe", "am", "ob", "jon", "mic", "na", "hab", "zep", "hag", "zec",
    "zech", "mal", "mt", "matt", "mr", "mk", "lu", "lk", "joh", "jn", "ac", "ro", "rom", "co",
    "cor", "ga", "gal", "eph", "php", "phil", "col", "thess", "ti", "tim", "tit", "heb",
    "jas", "pe", "pet", "jud", "rev", "st", "dr", "ed",
})
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
#: An old elision's apostrophe ('tis, 'twas, 'em), which curl_singles would
#: otherwise read as an opening quotation mark after a space.
_ELISION = re.compile(r"(?<!\w)'(?=(?:tis|twas|twere|twill|twould|em|gainst|neath|mongst)\b)", re.I)
_VERSE_REF = re.compile(r"(\d+)[.:](\d+)")
#: A versification scheme in book.json: "english", "hebrew", "english+1" or "skip".
_SCHEME = re.compile(r"(english|hebrew|skip)(?:\+(\d+))?")


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


def tidy(text: str, curled: bool = False) -> list[str]:
    """An excerpt's paragraphs, with only the scan's typography repaired (see
    TEXT in the module docstring). The words and their order are untouched.
    `curled` also closes up a space inside a curled double mark (scan_filter 2;
    the Catena on John was built without it)."""
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text.strip()):
        para = _SPACE_BEFORE.sub(r"\1", " ".join(raw.split()))
        para = space_quotes(para).replace(" - ", " — ")  # a spaced hyphen is the edition's dash
        if curled:
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
    # its first verse in Hebrew), the map from one to the other, so a commentary
    # keyed in the source numbering can be read in the English (VERSIFICATION).
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
        folder = EDITORIAL / code
        self.meta = json.loads((folder / "book.json").read_text("utf-8"))
        #: Logia author id -> (name on an excerpt, short work title, era), in the
        #: order they lived, which is the order they speak under a verse; the
        #: era spreads a passage's excerpts across the centuries.
        self.voices = {v["id"]: (v["name"], v["work"], v["era"]) for v in self.meta["voices"]}
        #: A long book (the Psalms) takes fewer words a verse than a Gospel.
        self.words_per_verse = self.meta.get("words_per_verse", WORDS_PER_VERSE)
        #: A voice the book leads with ("lead": true): Spurgeon in the Psalms.
        self.lead = {v["id"] for v in self.meta["voices"] if v.get("lead")}
        self.editions = {v["id"]: v["edition"] for v in self.meta["voices"] if v.get("edition")}
        self.rank = {a: i for i, a in enumerate(self.voices)}
        self.authors = logia["authors"]
        self.works = logia["works"]
        self.owb = json.loads((folder / "owb_sections.json").read_text("utf-8"))
        to_english = self.versification(code)
        self.excerpts = {}
        typed = Counter()
        for e in logia["excerpts"]:
            if "archive.org" not in e.get("source_url", ""):
                typed.update(map(str.lower, english_audit._WORD.findall(e["text"])))
            if e["start"].startswith(code + ".") and e["author"] in self.voices:
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
        self.folder = folder
        rejected = folder / "rejected.json"
        self.rejected = set(json.loads(rejected.read_text("utf-8"))["excerpts"]) if rejected.exists() else set()

    def versification(self, code: str):
        """A function (work id, start ref, end ref) -> an excerpt's first and
        last verse in English numbering, by the scheme book.json names for its
        work (VERSIFICATION in the module docstring). "english", the default,
        reads the refs as they are; "hebrew" reads them as the Hebrew text
        numbers them, through owb_sections.json's english_versification map;
        "english+N" reads a ref N verses ahead of the English one (a source
        that slipped); "skip" leaves the work out of a chapter whose keys
        cannot be read either way (None). A work's value is a scheme, or {"scheme": ...,
        "chapters": {"68": ...}} for a work whose keys change scheme in a
        few chapters."""
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
            raise CommandError("the OWB sections start after the Gospel does")
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
        """The scan has broken something: a misread word, debris, a word split
        at a hyphen or two run together across a full stop.

        A book whose book.json sets "scan_filter": 2 reads more finely. It
        also turns away a misread or broken punctuation mark (_MISREAD_MARK,
        _BROKEN_MARK, curled marks that do not pair), which the OCR'd Psalms
        commentaries (Spurgeon, Bellarmine) are full of, and an excerpt Logia
        cut off mid-sentence (_ENDS_WHOLE); in a scanned edition, the slips
        only a scan makes (_SCAN_SLIP) and a word broken in two at a line's end
        (_SUFFIXES, _PREFIXES); and it asks the
        vocabulary question (below) only of a scanned edition, and lets a word
        pass that is a possessive's s, a Roman numeral or a reference's
        abbreviation ("God’s", "Ps. xv. 3", "v. 4", "cf."), which the
        typed commentaries on the Psalms print on almost every page. It is a
        flag because the Catena on John was selected under the first filter,
        and its selection still holds a few excerpts the second turns away."""
        text = e["text"]
        finer = self.meta.get("scan_filter", 1) >= 2
        if finer and (
            _MISREAD_MARK.search(text)
            or _BROKEN_MARK.search(text)
            or text.count("“") != text.count("”")
            or text.count("‘") > len(_CLOSING_SINGLE.findall(text))
            or not _ENDS_WHOLE.search(text)
            or ("archive.org" in e.get("source_url", "") and _SCAN_SLIP.search(text))
        ):
            return True
        if (
            _MISREAD.search(text)
            or _SCAN_NOISE.search(text)
            or english_audit.HYPHEN_SPACE.search(text)
            or english_audit.RUN_TOGETHER.search(text)
        ):
            return True
        known = self.vocabulary
        if not finer:
            return any(w.lower() not in known for w in english_audit._WORD.findall(text))
        if "archive.org" not in e.get("source_url", ""):
            return False
        for m in _PAIR.finditer(text):
            first, second = m[1].lower(), m[2]
            if (second in _SUFFIXES or first in _PREFIXES) and first + second in known:
                return True
        for m in english_audit._WORD.finditer(text):
            w = m[0].lower()
            if w in known:
                continue
            before, after = text[m.start() - 1 : m.start()], text[m.end() : m.end() + 1]
            if w in _CLITICS and before and before in "’'":
                continue
            if after and after in ".,;:)" and (_ROMAN.fullmatch(w) or w in _ABBREVIATIONS):
                continue
            return True
        return False

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

    def select_passage(self, verses: list[tuple[int, int]], overall: Counter) -> list[str]:
        """The excerpt ids for one passage, in the order they were chosen."""
        pool = self.candidates(verses)
        budget = max(BUDGET_MIN, min(BUDGET_MAX, self.words_per_verse * len(verses)))
        eras, voices, at_verse = Counter(), Counter(), Counter()
        picks, used = [], 0

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
        """Verses of the Gospel as one quoted block, after OWB's note where a
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
        """The verses that begin inside a quotation. Each double mark is read
        by its place, not counted: one at the start of a verse or after a
        space or bracket opens, any other closes. OWB reopens a long speech at
        each new paragraph without closing the last (John 14–16), so a mere
        count drifts out of step. Read across chapters, since that discourse
        crosses two of them."""
        open_at, inside = set(), False
        for v in sorted(self.verses):
            if inside:
                open_at.add(v)
            for m in re.finditer('"', self.verses[v]):
                before = self.verses[v][m.start() - 1] if m.start() else " "
                inside = before in " ([—"
        return open_at

    def excerpt_html(self, e: dict) -> str:
        name, work, _ = self.voices[e["author"]]
        parts = [f"<p><strong>{escape(name)}</strong> · <em>{escape(work)}</em></p>"]
        for para in tidy(e["text"], curled=self.meta.get("scan_filter", 1) >= 2):
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
            # The work its excerpts come from: an author's John is not his Psalms.
            work = self.works[Counter(e["work"] for e in self.excerpts.values() if e["author"] == a).most_common(1)[0][0]]
            # book.json may word the edition itself where Logia's note is a
            # cataloguer's (scan identifiers, a translator's apology).
            detail = (
                self.editions.get(a) or work.get("translation") or work.get("edition") or ""
            ).rstrip(".")
            rows.append(
                f"<p><strong>{escape(self.authors[a]['name'])}</strong>, <em>{escape(work['title'])}</em>. "
                f"{escape(detail)}. {used[a]} excerpt{'s' if used[a] != 1 else ''} in this book.</p>"
            )
        text = self.meta.get("scripture_credit", "The Gospel text")
        rows.append(
            "<p>Every excerpt was gathered by Logia (logia.faith), which copies each one word for word "
            f"from the public-domain edition above and offers the collection under CC0. {escape(text)} is "
            "the Open Word Bible (openwordbible.org), English, Balanced level, also CC0.</p>"
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
