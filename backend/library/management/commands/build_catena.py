"""Build a catena on a Gospel: its text, passage by passage, with the Church's
commentators speaking under each verse, oldest first.

A *catena* ("chain") is the old way of reading Scripture slowly: under every
verse, excerpts from the great commentators, one after another. This command
builds one as a library book from two CC0 sources:

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
crowding the book. Aquinas's Catena Aurea is left out on purpose — it is
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
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.management.commands.build_owb_book import DISPUTED_NOTE, curl_singles
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert
from library.sanitize import clean_fragment

AUTHOR_SLUG = "ochorus-originals"
LANGUAGE = "en"
EDITORIAL = Path(settings.BASE_DIR) / "library" / "data" / "catena"
BIBLE = Path(settings.BASE_DIR) / "library" / "data" / "bible" / "owb-en-b.json.gz"
LOGIA = "https://logia.faith"

#: The Gospels this command knows: OSIS-style code -> (English name, OWB book number).
GOSPELS = {"MAT": ("Matthew", 40), "MRK": ("Mark", 41), "LUK": ("Luke", 42), "JHN": ("John", 43)}

#: The voices, keyed by Logia's author id: (name on an excerpt, short work title).
#: Order is chronological, and it is the order the voices speak under a verse.
VOICES = {
    "origen": ("Origen", "Commentary on John"),
    "chrysostom": ("John Chrysostom", "Homilies on John"),
    "augustine": ("Augustine", "Tractates on John"),
    "cyril": ("Cyril of Alexandria", "Commentary on John"),
    "calvin": ("John Calvin", "Commentary on John"),
    "lapide": ("Cornelius a Lapide", "The Great Commentary"),
    "henry": ("Matthew Henry", "Commentary on the Whole Bible"),
    "bengel": ("J. A. Bengel", "Gnomon of the New Testament"),
    "wesley": ("John Wesley", "Explanatory Notes"),
    "ryle": ("J. C. Ryle", "Expository Thoughts on John"),
    "westcott": ("B. F. Westcott", "The Gospel According to St. John"),
}
#: Era of each voice, for spreading a passage's excerpts across the centuries.
ERA = {
    "origen": 0, "chrysostom": 0, "augustine": 0, "cyril": 0,
    "calvin": 1, "lapide": 1,
    "henry": 2, "bengel": 2, "wesley": 2,
    "ryle": 3, "westcott": 3,
}

#: Words of commentary per verse of text, and a passage's floor and ceiling.
WORDS_PER_VERSE = 90
BUDGET_MIN, BUDGET_MAX = 500, 2600
#: Excerpt length bounds, in words. Wesley's notes are short by design.
MIN_WORDS, MIN_WORDS_SHORT, MAX_WORDS = 40, 20, 450
SHORT_VOICES = frozenset({"wesley", "bengel"})
#: A comfortable excerpt length, which the score leans towards.
IDEAL_WORDS = 200

#: Scan debris: stray asterisks, bars and carets, a degree sign, angle brackets,
#: a word broken at a hyphen ("seems- to"). An excerpt carrying any is passed over.
_SCAN_NOISE = re.compile(r"[*|^°<>{}]|\w- \w")
_NON_LATIN = re.compile(r"[Ͱ-Ͽἀ-῿֐-׿]")
_OPENS_MIDWAY = re.compile(r"^(?:and|but|or|nor|so|for|yet|then|thus|hence|therefore)\b", re.I)
_LEADING_VERSE = re.compile(r"^(?:(?:Ver|Verse)\.?\s*)?\d+\.\s+(?=\S)")
_SPACE_BEFORE = re.compile(r"\s+([,;:.?!)\]])")
_OPEN_QUOTE_SPACE = re.compile(r'(^|[\s(\[—])"\s+(?=\w)')
_CLOSE_QUOTE_SPACE = re.compile(r'(?<=[\w.,;:?!’])\s+"(?=[\s,;:.?!)\]—]|$)')


def verse_key(ref: str) -> tuple[int, int]:
    """'JHN.3.16' or '3:16' -> (3, 16)."""
    parts = re.split(r"[.:]", ref)
    return int(parts[-2]), int(parts[-1])


def span(code: str, first: tuple[int, int], last: tuple[int, int]) -> str:
    """'John 1:1–5', 'John 1:1', 'John 7:53–8:11'."""
    name = GOSPELS[code][0]
    if first == last:
        return f"{name} {first[0]}:{first[1]}"
    if first[0] == last[0]:
        return f"{name} {first[0]}:{first[1]}–{last[1]}"
    return f"{name} {first[0]}:{first[1]}–{last[0]}:{last[1]}"


def tidy(text: str) -> list[str]:
    """An excerpt's paragraphs, with only the scan's typography repaired (see
    TEXT in the module docstring). The words and their order are untouched."""
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(raw.split())
        para = _OPEN_QUOTE_SPACE.sub(r'\1"', para)
        para = _CLOSE_QUOTE_SPACE.sub('"', para)
        para = _SPACE_BEFORE.sub(r"\1", para)
        para = para.replace(" - ", " — ")  # a spaced hyphen is the edition's dash
        if para:
            paragraphs.append(para)
    if paragraphs:
        paragraphs[0] = _LEADING_VERSE.sub("", paragraphs[0])
    return paragraphs


def words(text: str) -> int:
    return len(text.split())


class Command(BaseCommand):
    help = "Build a verse-by-verse catena on a Gospel from Logia's excerpts and the Open Word Bible."

    def add_arguments(self, parser):
        parser.add_argument("logia", help="path to logia-en.json (https://logia.faith/downloads/logia-en.json)")
        parser.add_argument("code", choices=sorted(GOSPELS), help="the Gospel, e.g. JHN")
        parser.add_argument(
            "--select", action="store_true",
            help="choose the excerpts afresh and rewrite selection.json (otherwise it is read)",
        )

    # --- inputs -------------------------------------------------------------

    def load(self, path: str, code: str):
        raw = Path(path).read_bytes()
        logia = json.loads(raw)
        if logia.get("licence") != "CC0-1.0":
            raise CommandError(f"unexpected Logia licence {logia.get('licence')!r}")
        self.logia_sha = hashlib.sha256(raw).hexdigest()
        self.authors = logia["authors"]
        self.works = logia["works"]
        self.excerpts = {
            e["id"]: e for e in logia["excerpts"]
            if e["start"].startswith(code + ".") and e["author"] in VOICES
        }
        number = GOSPELS[code][1]
        bible = json.loads(gzip.open(BIBLE).read())
        self.verses = {
            (int(k[-6:-3]), int(k[-3:])): text
            for k, text in bible["verses"].items()
            if len(k) == 8 and int(k[:-6]) == number
        }
        self.bible_commit = bible["meta"]["commit"]
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
        out = []
        for i, (first, title) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else (10**6, 0)
            out.append((title, [v for v in ordered if first <= v < end]))
        if sum(len(vs) for _, vs in out) != len(ordered) or ordered[0] < starts[0][0]:
            raise CommandError("the OWB sections do not cover every verse exactly once")
        return out

    # --- selection ----------------------------------------------------------

    def candidates(self, verses: list[tuple[int, int]]) -> list[dict]:
        first, last = verses[0], verses[-1]
        out = []
        for e in self.excerpts.values():
            start, end = verse_key(e["start"]), verse_key(e["end"])
            n = words(e["text"])
            floor = MIN_WORDS_SHORT if e["author"] in SHORT_VOICES else MIN_WORDS
            if not (first <= start <= last and end <= last and floor <= n <= MAX_WORDS):
                continue
            if _NON_LATIN.search(e["text"]):
                continue  # Greek or Hebrew: the reader's fonts and listen mode both stumble
            if _SCAN_NOISE.search(e["text"]) or e["id"] in self.rejected:
                continue  # an OCR slip, or an excerpt an editor has turned down (rejected.json)
            if e["text"].count('"') % 2:
                continue  # an unpaired quotation mark: the scan lost one, and curling would guess
            out.append({**e, "_start": start, "_words": n})
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
                s = 3.0 if eras[ERA[a]] == 0 else -float(eras[ERA[a]])
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
                eras[ERA[a]] += 1
                voices[a] += 1
                at_verse[e["_start"]] += 1
                overall[a] += 1

            # First, one excerpt in each stretch of the passage, so the comment
            # follows the text from its first verse to its last rather than
            # pooling where the commentators wrote most.
            # Each stretch gets its share of the budget, so a long excerpt early
            # in the passage cannot starve the verses after it.
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

    def verse_html(self, code: str, verses: list[tuple[int, int]]) -> str:
        text = " ".join(curl_singles(self.verses[v]) for v in verses)
        cite = span(code, verses[0], verses[-1])
        return f"<blockquote><p>{escape(text, quote=False)}</p><p>— {cite}</p></blockquote>"

    def excerpt_html(self, e: dict) -> str:
        name, work = VOICES[e["author"]]
        parts = [f"<p><strong>{escape(name)}</strong> · <em>{escape(work)}</em></p>"]
        for para in tidy(e["text"]):
            parts.append(f"<p>{escape(curl_singles(para), quote=False)}</p>")
        return "\n".join(parts)

    def passage_html(self, code: str, title: str, verses, ids: list[str]) -> str:
        picks = [self.excerpts[i] for i in ids]
        by_start = defaultdict(list)
        for e in picks:
            by_start[verse_key(e["start"])].append(e)
        order = list(VOICES)
        out = [f"<h3>{escape(title)}</h3>"]
        # A block of text may only end where no quotation is open, or a
        # speech split across two blocks loses a mark in each.
        depth, closed = 0, set()
        for v in verses:
            depth += self.verses[v].count('"')
            if depth % 2 == 0:
                closed.add(v)
        position = 0
        starts = sorted(by_start)
        for n, start in enumerate(starts):
            group = sorted(by_start[start], key=lambda e: (order.index(e["author"]), e["id"]))
            # Quote the verses a group comments on, but never past the verse
            # before the next group's: an overview of 3:9–21 must not carry 3:16
            # above Calvin's note on it.
            reach = max(max(verse_key(e["end"]) for e in group), start)
            if n + 1 < len(starts):
                reach = max(start, min(reach, max(v for v in verses if v < starts[n + 1])))
            reach = max(v for v in verses if v <= reach)  # John 5:4 is not in the text
            while reach not in closed and reach < verses[-1]:
                reach = verses[verses.index(reach) + 1]
            block = [v for v in verses[position:] if v <= reach]
            if block:
                out.append(self.disputed(code, block) + self.verse_html(code, block))
                position += len(block)
            out.extend(self.excerpt_html(e) for e in group)
        if position < len(verses):
            rest = verses[position:]
            out.append(self.disputed(code, rest) + self.verse_html(code, rest))
        return "\n".join(out)

    def disputed(self, code: str, block) -> str:
        """John 7:53–8:11, which the oldest manuscripts lack: OWB's note, once."""
        if code == "JHN" and (7, 53) in block:
            ref = "John 7:53–8:11"
            return f"<p><em>{escape(DISPUTED_NOTE.format(book='John', ref=ref))}</em></p>"
        return ""

    def summary(self, number: int, names: list[str]) -> str:
        base = self.owb["summaries"][str(number)]
        if len(names) > 3:
            voices = ", ".join(names[:3]) + f" and {len(names) - 3} more"
        else:
            voices = ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]
        return f"{base} With {voices}."

    # --- main ---------------------------------------------------------------

    def handle(self, *args, **opts):
        code = opts["code"]
        self.load(opts["logia"], code)
        passages = self.passages()
        selection_path = self.folder / "selection.json"
        if opts["select"]:
            chosen = self.select(passages)
            selection_path.write_text(
                json.dumps(
                    {
                        "_note": "Excerpt ids chosen by `build_catena --select`; edit one to swap an excerpt.",
                        "logia_sha256": self.logia_sha,
                        "passages": [
                            {"start": f"{vs[0][0]}:{vs[0][1]}", "title": t, "excerpts": ids}
                            for (t, vs), ids in zip(passages, chosen)
                        ],
                    },
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
                "utf-8",
            )
        saved = json.loads(selection_path.read_text("utf-8"))["passages"]
        if [p["start"] for p in saved] != [f"{vs[0][0]}:{vs[0][1]}" for _, vs in passages]:
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
        self.write(bodies)

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
