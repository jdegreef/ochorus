"""Build the Bible reader's "Related passages" from the Open Word Bible's cross-references.

OWB carries OpenBible.info's crowd-voted cross-references (CC BY, credit
required: https://www.openbible.info/labs/cross-references/) as
`data/crossrefs/<CODE>.json` — for each verse its most-voted few (at most
five, each with at least three votes), most voted first, with both ends in
OWB's verse numbering. Run it against a checkout of
https://github.com/jdegreef/open-word-bible:

    uv run python manage.py build_owb_crossrefs /tmp/owb

and it writes `library/data/bible/crossrefs-en.json.gz` (BUNDLE), which the
chapter API reads for a chapter of the Bible itself (`library/bible_crossrefs`).

PER CHAPTER, NOT PER VERSE. The reader prints no verse numbers (a reader's
edition, `build_owb_book`), so a verse-by-verse margin has nowhere to stand;
the chapter's foot does. Each chapter keeps its PER_CHAPTER best passages:
every verse's references vote for their target, the first-ranked worth the
most (PER_VERSE - rank, the order OWB keeps them in — its file carries ranks,
not vote counts), and the targets inside the chapter itself are dropped. The
votes are then summed per TARGET CHAPTER, each shown by its best passage, so
the list spreads across the Bible rather than repeat one neighbouring chapter
and a chapter that answers this one through several verses rises. That caps the file at a few
dozen KB gzipped, served with the chapter, never in the JS bundle.

ENGLISH NUMBERING. OWB numbers the Old Testament by its Hebrew source, the
reader by English Bibles (`build_owb_book` places each sentence through
`data/versification.json`); both ends are moved back here, through the same
table and the same New Testament list, so a reference names the chapter the
reader prints it in. A verse with no English number (a psalm's title) belongs
to its own chapter.

Labels use the reader's own names ("Psalm 23:1-6", not "Psalms"), from the
editorial `library/data/owb/<CODE>/book.json` and OWB's `data/books.json`.
"""

from __future__ import annotations

import gzip
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.management.commands.build_owb_book import EDITORIAL, NEW_TESTAMENT_ENGLISH

BUNDLE = Path(settings.BASE_DIR) / "library" / "data" / "bible" / "crossrefs-en.json.gz"
#: How many related passages a chapter keeps: a short row, easy to ignore.
PER_CHAPTER = 6
#: OWB keeps at most this many references per verse, best first.
PER_VERSE = 5
CREDIT = "Cross-references from OpenBible.info (https://www.openbible.info/labs/cross-references/), CC BY."
TARGET = re.compile(r"([1-3]?[A-Z]{2,3})\.(\d+)\.(\d+)(?:-(?:(\d+)\.)?(\d+))?")


def _key(vid: str) -> tuple[str, int, int]:
    code, chapter, verse = vid.split(".")
    return code, int(chapter), int(verse)


class Command(BaseCommand):
    help = "Build library/data/bible/crossrefs-en.json.gz from an Open Word Bible checkout."

    def add_arguments(self, parser):
        parser.add_argument("root", help="A checkout of github.com/jdegreef/open-word-bible.")

    def handle(self, *args, **opts):
        root = Path(opts["root"])
        crossrefs = root / "data" / "crossrefs"
        if not crossrefs.is_dir():
            raise CommandError(f"{crossrefs} not found — is {root} an Open Word Bible checkout?")
        books = json.loads((root / "data" / "books.json").read_text("utf-8"))["books"]
        english = json.loads((root / "data" / "versification.json").read_text("utf-8"))["english"]
        english = english | NEW_TESTAMENT_ENGLISH

        meta = {code: json.loads((EDITORIAL / code / "book.json").read_text("utf-8")) for code in books}
        slug = {code: meta[code]["slug"] for code in books}
        label = {code: meta[code].get("chapter_label", books[code]["en"]) for code in books}

        def to_english(vid: str, last: bool = False) -> tuple[str, int, int]:
            """A source verse as the English verse it is printed as. A verse
            two English ones share is the first (or, ending a span, the last);
            a psalm's title (no English verse) is verse 0 of its chapter."""
            if vid not in english:
                return _key(vid)
            mapped = english[vid]
            if not mapped:
                code, chapter, _ = _key(vid)
                return code, chapter, 0
            return _key(mapped[-1] if last else mapped[0])

        def target(text: str) -> tuple[tuple[str, int, int], tuple[str, int, int]]:
            m = TARGET.fullmatch(text)
            if not m:
                raise CommandError(f"bad cross-reference: {text!r}")
            first = f"{m[1]}.{m[2]}.{m[3]}"
            last = f"{m[1]}.{m[4] or m[2]}.{m[5]}" if m[5] else first
            return to_english(first), to_english(last, last=True)

        def name(first, last) -> str:
            code, c1, v1 = first
            _, c2, v2 = last
            v1 = max(v1, 1)
            head = f"{label[code]} {c1}:{v1}"
            if (c1, v1) == (c2, v2):
                return head
            return f"{head}-{v2}" if c1 == c2 else f"{head}-{c2}:{v2}"

        out: dict[str, dict[str, list]] = {}
        for code in books:
            path = crossrefs / f"{code}.json"
            if not path.is_file():
                continue
            refs = json.loads(path.read_text("utf-8"))["refs"]
            score: dict[int, dict] = defaultdict(lambda: defaultdict(int))
            for source, targets in refs.items():
                chapter = to_english(source)[1]
                for rank, text in enumerate(targets):
                    first, last = target(text)
                    if first[0] == code and first[1] == chapter:
                        continue
                    score[chapter][(first, last)] += PER_VERSE - rank
            order = list(books)
            chapters = {}
            for chapter, votes in sorted(score.items()):
                # A target CHAPTER's weight is all its passages' votes together:
                # John 10 answers Psalm 23 through three verses, which is the
                # point. It is shown by its own best passage.
                weight: dict[tuple[str, int], int] = defaultdict(int)
                best: dict[tuple[str, int], tuple] = {}
                for (first, last), points in sorted(votes.items()):
                    where = (first[0], first[1])
                    weight[where] += points
                    if where not in best or points > votes[best[where]]:
                        best[where] = (first, last)
                ranked = sorted(weight, key=lambda w: (-weight[w], order.index(w[0]), w[1]))
                # [label, reader book slug, English chapter]
                chapters[str(chapter)] = [
                    [name(*best[w]), slug[w[0]], w[1]] for w in ranked[:PER_CHAPTER]
                ]
            out[slug[code]] = chapters

        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        source = json.loads((crossrefs / f"{next(iter(books))}.json").read_text("utf-8"))["source"]
        data = {
            "about": (
                "Related passages for each chapter of the library's Bible, in English "
                "chapter numbering: [label, reader book slug, chapter]. Built by "
                "manage.py build_owb_crossrefs."
            ),
            "credit": CREDIT,
            "license": "CC BY (OpenBible.info)",
            "source": f"{source}; via Open Word Bible data/crossrefs at {commit}",
            "books": out,
        }
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        # mtime=0: the same input gives the same bytes, so a rebuild with no
        # change in OWB leaves no diff.
        BUNDLE.write_bytes(gzip.compress(raw, mtime=0))
        total = sum(len(c) for b in out.values() for c in b.values())
        self.stdout.write(
            f"Wrote {BUNDLE.name}: {len(out)} books, {sum(len(b) for b in out.values())} chapters, "
            f"{total} passages, {BUNDLE.stat().st_size // 1024} KB."
        )
