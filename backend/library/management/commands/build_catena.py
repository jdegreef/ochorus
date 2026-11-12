"""Build a catena on John: its text, passage by passage, with the Church's
commentators speaking under each verse, oldest first.

A *catena* ("chain") is the old way of reading Scripture slowly: under every
verse, excerpts from the great commentators, one after another. This command
builds one as a library book from two CC0 sources. Only John so far: the voices
(VOICES) and their short work titles are John's, so another Gospel starts by
adding its own.

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
punctuation and inside quotation marks closed up, a leading verse number
dropped, quotation marks curled the house way. Old spelling and the
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

#: The Gospels this command can build: code -> (English name, OWB book number).
GOSPELS = {"JHN": ("John", 43)}

#: The voices, keyed by Logia's author id: (name on an excerpt, short work
#: title, era). Listed in the order they lived, which is the order they speak
#: under a verse; the era spreads a passage's excerpts across the centuries.
VOICES = {
    "origen": ("Origen", "Commentary on John", 0),
    "chrysostom": ("John Chrysostom", "Homilies on John", 0),
    "augustine": ("Augustine", "Tractates on John", 0),
    "cyril": ("Cyril of Alexandria", "Commentary on John", 0),
    "calvin": ("John Calvin", "Commentary on John", 1),
    "lapide": ("Cornelius a Lapide", "The Great Commentary", 1),
    "henry": ("Matthew Henry", "Commentary on the Whole Bible", 2),
    "bengel": ("J. A. Bengel", "Gnomon of the New Testament", 2),
    "wesley": ("John Wesley", "Explanatory Notes", 2),
    "ryle": ("J. C. Ryle", "Expository Thoughts on John", 3),
    "westcott": ("B. F. Westcott", "The Gospel According to St. John", 3),
}
RANK = {a: i for i, a in enumerate(VOICES)}

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
_SHORT_WORDS = frozenset(
    "a i o ah am an as at be by do go ha he ho if in is it lo me my no of oh on or ox so to up us we ye".split()
)
_NON_LATIN = re.compile(r"[Ͱ-Ͽἀ-῿֐-׿]")
_OPENS_MIDWAY = re.compile(r"^(?:and|but|or|nor|so|for|yet|then|thus|hence|therefore)\b", re.I)
_LEADING_VERSE = re.compile(r"^(?:(?:Ver|Verse)\.?\s*)?\d+\.\s+(?=\S)")
_SPACE_BEFORE = re.compile(r"\s+([,;:.?!)\]])")
_VERSE_REF = re.compile(r"(\d+)[.:](\d+)")


def verse_key(ref: str) -> tuple[int, int]:
    """'JHN.3.16', '3:16' or 'MRK.16.8.s2' -> its chapter and verse."""
    m = _VERSE_REF.search(ref)
    return int(m[1]), int(m[2])


def ref(verse: tuple[int, int]) -> str:
    """(3, 16) -> '3:16', the form selection.json and owb_sections.json key on."""
    return f"{verse[0]}:{verse[1]}"


def span(code: str, first: tuple[int, int], last: tuple[int, int]) -> str:
    """'John 1:1–5', 'John 1:1', 'John 7:53–8:11'."""
    name = GOSPELS[code][0]
    if first == last:
        return f"{name} {ref(first)}"
    if first[0] == last[0]:
        return f"{name} {ref(first)}–{last[1]}"
    return f"{name} {ref(first)}–{ref(last)}"


def tidy(text: str) -> list[str]:
    """An excerpt's paragraphs, with only the scan's typography repaired (see
    TEXT in the module docstring). The words and their order are untouched."""
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text.strip()):
        para = _SPACE_BEFORE.sub(r"\1", " ".join(raw.split()))
        para = space_quotes(para).replace(" - ", " — ")  # a spaced hyphen is the edition's dash
        if para:
            paragraphs.append(para)
    if paragraphs:
        paragraphs[0] = _LEADING_VERSE.sub("", paragraphs[0])
    return paragraphs


class Command(BaseCommand):
    help = "Build a verse-by-verse catena on John from Logia's excerpts and the Open Word Bible."

    def add_arguments(self, parser):
        parser.add_argument("logia", help="path to logia-en.json (https://logia.faith/downloads/logia-en.json)")
        parser.add_argument("code", choices=sorted(GOSPELS), help="the Gospel, e.g. JHN")
        parser.add_argument(
            "--select", action="store_true",
            help="choose the excerpts afresh and rewrite selection.json (otherwise it is read)",
        )

    # --- inputs -------------------------------------------------------------

    def load(self, path: str, code: str, select: bool):
        raw = Path(path).read_bytes()
        self.logia_sha = hashlib.sha256(raw).hexdigest()
        logia = json.loads(raw)
        del raw
        if logia.get("licence") != "CC0-1.0":
            raise CommandError(f"unexpected Logia licence {logia.get('licence')!r}")
        self.authors = logia["authors"]
        self.works = logia["works"]
        self.excerpts = {}
        typed = Counter()
        for e in logia["excerpts"]:
            if select and "archive.org" not in e.get("source_url", ""):
                typed.update(map(str.lower, english_audit._WORD.findall(e["text"])))
            if e["start"].startswith(code + ".") and e["author"] in VOICES:
                e["_start"], e["_end"] = verse_key(e["start"]), verse_key(e["end"])
                e["_words"] = word_count(e["text"])
                self.excerpts[e["id"]] = e
        self.typed_counts = typed
        number = GOSPELS[code][1]
        verses, joined = _owb()
        # A verse OWB prints together with the one before it is quoted there.
        self.verses = {
            (vid // 1000 % 1000, vid % 1000): text
            for vid, text in verses.items()
            if vid // 1_000_000 == number and vid not in joined
        }
        with gzip.open(_OWB_PATH, "rt", encoding="utf-8") as fh:
            self.bible_commit = json.load(fh)["meta"]["commit"]
        folder = EDITORIAL / code
        self.owb = json.loads((folder / "owb_sections.json").read_text("utf-8"))
        self.meta = json.loads((folder / "book.json").read_text("utf-8"))
        self.folder = folder
        rejected = folder / "rejected.json"
        self.rejected = set(json.loads(rejected.read_text("utf-8"))["excerpts"]) if rejected.exists() else set()

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

    def damaged(self, text: str) -> bool:
        """The scan has broken something: a misread word, debris, a word split
        at a hyphen or two run together across a full stop."""
        if (
            _MISREAD.search(text)
            or _SCAN_NOISE.search(text)
            or english_audit.HYPHEN_SPACE.search(text)
            or english_audit.RUN_TOGETHER.search(text)
        ):
            return True
        known = self.vocabulary
        return any(w.lower() not in known for w in english_audit._WORD.findall(text))

    def candidates(self, verses: list[tuple[int, int]]) -> list[dict]:
        first, last = verses[0], verses[-1]
        out = []
        for e in self.excerpts.values():
            floor = MIN_WORDS_SHORT if e["author"] in SHORT_VOICES else MIN_WORDS
            if not (first <= e["_start"] <= last and e["_end"] <= last and floor <= e["_words"] <= MAX_WORDS):
                continue
            if e["id"] in self.rejected or _NON_LATIN.search(e["text"]) or self.damaged(e["text"]):
                continue  # turned down by an editor; Greek or Hebrew; or the scan damaged it
            if e["text"].count('"') % 2:
                continue  # an unpaired quotation mark: the scan lost one, and curling would guess
            out.append(e)
        return sorted(out, key=lambda e: e["id"])

    def select(self, passages) -> list[list[str]]:
        overall = Counter()
        chosen = []
        for _, verses in passages:
            pool = self.candidates(verses)
            budget = max(BUDGET_MIN, min(BUDGET_MAX, WORDS_PER_VERSE * len(verses)))
            eras, voices, at_verse = Counter(), Counter(), Counter()
            picks, used = [], 0

            def score(e):
                a = e["author"]
                era = VOICES[a][2]
                s = 3.0 if eras[era] == 0 else -float(eras[era])
                s += 2.0 if voices[a] == 0 else -2.0 * voices[a]
                s -= overall[a] / 40
                s -= abs(e["_words"] - IDEAL_WORDS) / 150
                s -= 2.0 * at_verse[e["_start"]]
                if _OPENS_MIDWAY.match(e["text"].lstrip("“\"' ")):
                    s -= 1.5  # reads as the middle of an argument
                return s

            def take(e):
                nonlocal used
                pool.remove(e)
                picks.append(e["id"])
                used += e["_words"]
                a = e["author"]
                eras[VOICES[a][2]] += 1
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
            chosen.append(picks)
        return chosen

    # --- rendering ----------------------------------------------------------

    def text_block(self, code: str, verses: list[tuple[int, int]]) -> str:
        """Verses of the Gospel as one quoted block, after OWB's note where a
        passage the oldest manuscripts lack begins in it."""
        note = ""
        for first, last, _ in DISPUTED:
            if first.startswith(code + ".") and verse_key(first) in verses:
                where = span(code, verse_key(first), verse_key(last))
                note = f"<p><em>{escape(DISPUTED_NOTE.format(book=GOSPELS[code][0], ref=where))}</em></p>"
        text = " ".join(curl_singles(self.verses[v]) for v in verses)
        # A speech that runs on from the block before (Jesus to Nicodemus,
        # 3:10–21) reopens here, as a quotation running over several
        # paragraphs reopens each one.
        if verses[0] in self.open_at:
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
        name, work, _ = VOICES[e["author"]]
        parts = [f"<p><strong>{escape(name)}</strong> · <em>{escape(work)}</em></p>"]
        for para in tidy(e["text"]):
            parts.append(f"<p>{escape(curl_singles(para), quote=False)}</p>")
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
            group = sorted(by_start[start], key=lambda e: (RANK[e["author"]], e["id"]))
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
        else:
            voices = names[0]
        return f"{base} With {voices}."

    # --- main ---------------------------------------------------------------

    def handle(self, *args, **opts):
        code = opts["code"]
        self.load(opts["logia"], code, opts["select"])
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
                            for start, (t, _), ids in zip(starts, passages, chosen)
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
        refused = [i for ids in chosen for i in ids if i in self.rejected]
        if refused:
            raise CommandError(f"selection.json still names rejected excerpts: {refused[:5]} — rerun with --select")
        missing = [i for ids in chosen for i in ids if i not in self.excerpts]
        if missing:
            raise CommandError(f"selection.json names excerpts this Logia file lacks: {missing[:5]}")

        chapters = defaultdict(list)
        for (title, verses), ids in zip(passages, chosen):
            chapters[verses[0][0]].append((title, verses, ids))

        bodies = [("Introduction", (self.folder / "introduction.html").read_text("utf-8"), "")]
        used = Counter()
        for number in sorted(chapters):
            html = "\n".join(self.passage_html(code, *p) for p in chapters[number])
            authors = Counter(self.excerpts[i]["author"] for _, _, ids in chapters[number] for i in ids)
            used.update(authors)
            names = [VOICES[a][0] for a in VOICES if a in authors]
            bodies.append((f"{GOSPELS[code][0]} {number}", html, self.summary(number, names)))
        bodies.append(("The Voices and Their Books", self.voices_html(used), ""))
        book = self.write(bodies)
        english_audit.report(self, english_audit.audit_book(book), book.slug)

    def voices_html(self, used: Counter) -> str:
        """The back chapter: the editorial account of each voice, then the
        edition every excerpt was copied from."""
        intro = (self.folder / "voices.html").read_text("utf-8")
        rows = ["<h2>The editions</h2>"]
        for a in VOICES:
            if not used[a]:
                continue
            work = self.works[a]
            detail = (work.get("translation") or work.get("edition") or "").rstrip(".")
            rows.append(
                f"<p><strong>{escape(self.authors[a]['name'])}</strong>, <em>{escape(work['title'])}</em>. "
                f"{escape(detail)}. {used[a]} excerpt{'s' if used[a] != 1 else ''} in this book.</p>"
            )
        rows.append(
            "<p>Every excerpt was gathered by Logia (logia.faith), which copies each one word for word "
            "from the public-domain edition above and offers the collection under CC0. The Gospel text is "
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
