"""Build one book of the Open Word Bible (CC0, openwordbible.org) as a library book.

The English Balanced text (OWB-B), the same wording the reader's Scripture
popover quotes (`scripts/build_owb_bible.py`), set as a reading edition: one
chapter per Bible chapter, between an introduction and a conclusion. Run it
against a checkout of https://github.com/jdegreef/open-word-bible:

    git clone https://github.com/jdegreef/open-word-bible /tmp/owb
    DJANGO_DEBUG=true uv run python manage.py build_owb_book /tmp/owb JHN

then serialize the row to `fixtures/content/books/<slug>.en.json` (book-import
skill, "Write its fixture file yourself").

SOURCE. Only OWB's DATA is read — `content/<CODE>/*.json` (the sentence
records), `data/headings/<CODE>.json`, and the Greek / Hebrew word extracts
under `data/grc|hbo/` for paragraphing — never its code, so the rules below are
a small port of the ones its site builder (`scripts/build_site.py`) applies:

* **Settings** at their defaults: a `{{setting:a|b}}` span reads `a`.
* **Poetry lines** run together in prose books: a `\\q` break reads as a
  space. In a book of verse (`POETRY`) each line is its own: a `\\q` break and
  the start of every verse become a `<br>`, inside the paragraphs below.
* **English chapters.** Records carry the source text's numbering, which in
  some Old Testament books differs from English Bibles (Hebrew Genesis 32:1 is
  English 31:55; Malachi 4 is Hebrew 3:19-24). A sentence goes in the ENGLISH
  chapter of its first verse, through OWB's `data/versification.json`.
* **Psalm titles** ("A psalm of David"), which English Bibles print unnumbered
  above verse 1, are the verses that map to no English number: they open the
  chapter as an italic paragraph of their own. Where the Hebrew counts a short
  title as part of verse 1 ("A psalm of David. The LORD is my shepherd"), the
  title's sentences are told by their words (`PSALM_TITLE`) and set the same way.
* **No verse numbers**: a reader's edition, chapters and paragraphs only. A bare
  `<sup>16</sup>` is footnote residue to this library — the deploy's
  `corrections.strip_footnote_markers` removes every one, and listen mode would
  read it aloud — and verse lookup already has the Scripture popover and the
  /scripture/ pages. A sentence that runs into the next chapter (John 7:53-8:1)
  stays in the chapter it starts in.
* **Single quotation marks and apostrophes** are curled here (`curl_singles`);
  `quote_marks.convert` curls only the double ones.
* **Paragraphs** open where the source text opens one: SBLGNT capitalises the
  first word of a paragraph (and of a quotation, which follows a raised dot or
  a comma, so a capital after a full stop is required, and a name, capitalised
  in the dictionary too, does not count); the Hebrew codex marks a paragraph's
  end with a pe or samekh after its last word. A section heading (`<h3>`)
  always opens one.
* **A disputed passage** (`DISPUTED`) is set apart as a `<blockquote>` after a
  note saying so, as OWB sets it.

Footnotes, the Literal and Readable levels and the other languages are not
carried (yet). Quotation marks are curled the house way.

EDITORIAL lives beside the command in `library/data/owb/<CODE>/`: `book.json`
(slug, title, description, Q&A), `introduction.html` and `conclusion.html`.
Both are Ochorus's own writing, deliberately not OWB's shorter
`data/intros/<CODE>.md`: longer, a reader's guide to the book's shape and
meaning, and the conclusion points into the library. `{{OWB:<record id>}}` in
either is replaced with that sentence's text, so a quotation can't drift from
the translation; any other quotation of the text must match OWB-B by hand.

Every sentence of OWB is an AI-assisted draft until a reviewer approves it, so
the edition is created `ai_unreviewed`; `approve_translation` promotes it. Like
every book, `seed_books` creates it on deploy from the fixture. Idempotent.
"""

from __future__ import annotations

import json
import re
import subprocess
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert
from library.sanitize import clean_fragment

AUTHOR_SLUG = "open-word-bible"
LANGUAGE = "en"
LEVEL = "B"
SITE = "https://openwordbible.org"
EDITORIAL = Path(settings.BASE_DIR) / "library" / "data" / "owb"

#: Passages the oldest manuscripts lack, as (first verse, last verse) — OWB's
#: own list (`build_site.DISPUTED`).
DISPUTED = (("JHN.7.53", "JHN.8.11"),)
DISPUTED_NOTE = (
    "The earliest manuscripts of {book} do not have {ref}. Most Bibles print it, "
    "as here, set apart and in brackets."
)

#: Matthew's place in OWB's canonical book order (`data/books.json`): it and
#: every book after it are Greek (`data/grc/`), the ones before Hebrew (`data/hbo/`).
FIRST_NT_INDEX = 39

#: Books set as verse, line by line (see the module doc).
POETRY = frozenset({"PSA"})

#: Books whose chapters open with a title English Bibles print unnumbered: the
#: Psalms (see the module doc).
TITLED = frozenset({"PSA"})

#: One sentence of a psalm's title, by the few words titles are made of: "For
#: the music director.", "A psalm of David.", "Of the sons of Korah.", "A song of
#: ascents." Peeled from the front of a psalm's first verse only, and only where
#: no verse of the psalm is a title already. "Praise the LORD!" is not one:
#: English Bibles print it as the psalm's first words.
PSALM_TITLE = re.compile(
    r"(?:For the music director|(?:A |An )?(?:psalm|song|prayer|maskil|miktam|shiggaion)\b[^.!?\n]*"
    r"|Of (?:the sons of Korah|[A-Z][a-z]+))\.[ \n]*"
)


def split_psalm_title(text: str) -> tuple[str, str]:
    """(the title sentences at the start of `text`, the rest)."""
    end = 0
    while m := PSALM_TITLE.match(text, end):
        end = m.end()
    return " ".join(text[:end].split()), text[end:]

_SPAN = re.compile(r"\{\{([a-z_]+):([^{}]*)\}\}")
_VERSE = re.compile(r"\\v (\d+) ?")
_LINE = re.compile(r" ?\\q ?")
_EMBED = re.compile(r"\{\{OWB:([A-Z0-9]+\.\d+\.\d+\.s\d+)\}\}")
_SINGLE = re.compile(r"""(^|(?<=[\s(\[{—–\-"“]))?'""")
#: Pe and samekh, the codex's paragraph signs.
_HEBREW_PARAGRAPH = re.compile("[פס]")


def verse_key(vid: str) -> tuple[int, int]:
    """(chapter, verse) of "JHN.3.16"."""
    _, chapter, verse = vid.split(".")
    return int(chapter), int(verse)


def record_key(record: dict) -> tuple[int, int, int]:
    """Bible order: the first verse, then the sentence's number within it."""
    return (*verse_key(record["refs"][0]), int(record["id"].rsplit(".s", 1)[1]))


def is_disputed(vid: str) -> bool:
    book = vid.split(".")[0]
    return any(
        a.startswith(book + ".") and verse_key(a) <= verse_key(vid) <= verse_key(b)
        for a, b in DISPUTED
    )


def curl_singles(text: str) -> str:
    """Straight ' as ‘ where it opens (at the start, or after a space, bracket,
    dash or double mark), else as ’ — a closing mark or an apostrophe."""
    return _SINGLE.sub(lambda m: "‘" if m[1] is not None else "’", text)


def plain(text: str, lines: bool = False) -> str:
    """A rendering with every setting at its default. Its poetry lines run
    together, or with `lines` are kept apart by a newline."""
    text = _SPAN.sub(lambda m: m[2].split("|")[0], text)
    if not lines:
        return curl_singles(" ".join(_LINE.sub(" ", text).split()))
    return "\n".join(curl_singles(" ".join(line.split())) for line in _LINE.split(text))


def heading_text(heading: str) -> str:
    """A section heading, capitalised: OWB sets Psalm 121's as "the LORD guards
    your going and coming", lower case where its divine-name setting begins it."""
    text = plain(heading)
    return text[:1].upper() + text[1:]


def verses_of(record: dict, lines: bool = False) -> list[tuple[str, str]]:
    """[(verse id, text)] for one sentence, split at its verse markers. A
    record's markers follow its refs in order. `lines` as for `plain`."""
    parts = _VERSE.split(record["renderings"][LANGUAGE][LEVEL])
    texts = [parts[0], *parts[2::2]]
    if len(texts) != len(record["refs"]):
        raise CommandError(
            f"{record['id']}: {len(texts)} verse parts for refs {record['refs']}"
        )
    return [
        (vid, plain(text, lines))
        for vid, text in zip(record["refs"], texts, strict=True)
    ]


class Source:
    """One book's data, read from an OWB checkout."""

    def __init__(self, root: Path, code: str):
        self.root, self.code = root, code
        files = sorted((root / "content" / code).glob(f"{code}.*.json"))
        if not files:
            raise CommandError(f"no content/{code}/ in {root}")
        records = [
            r for f in files for r in json.loads(f.read_text("utf-8"))["records"]
        ]
        missing = [
            r["id"] for r in records if LEVEL not in r["renderings"].get(LANGUAGE, {})
        ]
        if missing:
            raise CommandError(
                f"{len(missing)} sentences have no {LANGUAGE}-{LEVEL}: {missing[:5]}"
            )
        self.records = sorted(records, key=record_key)
        self.by_id = {r["id"]: r for r in self.records}
        headings = root / "data" / "headings" / f"{code}.json"
        self.headings = (
            {
                rid: h[LANGUAGE]
                for rid, h in json.loads(headings.read_text("utf-8"))[
                    "headings"
                ].items()
                if LANGUAGE in h
            }
            if headings.exists()
            else {}
        )
        books = json.loads((root / "data" / "books.json").read_text("utf-8"))["books"]
        self.name = books[code][LANGUAGE]
        self.greek = list(books).index(code) >= FIRST_NT_INDEX
        self.poetry = code in POETRY
        # Source verse -> its English verses, for the verses numbered otherwise
        # in English ([] for a psalm title). See the module doc.
        self.english = {
            vid: english
            for vid, english in json.loads(
                (root / "data" / "versification.json").read_text("utf-8")
            )["english"].items()
            if vid.startswith(f"{code}.")
        }
        self.carry_headings_forward()
        self.commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def english_chapter(self, vid: str) -> int:
        """The English chapter a source verse is printed in. A psalm title has
        no English verse and stays in its own chapter."""
        english = self.english.get(vid, [vid])
        return verse_key(english[0] if english else vid)[0]

    def is_title(self, record: dict) -> bool:
        """A sentence that is all psalm title: no verse of it has an English
        number. Only in a TITLED book: elsewhere (Numbers, 1 Samuel,
        1 Chronicles) an unnumbered verse is a merge, not a title."""
        return self.code in TITLED and all(self.english.get(vid) == [] for vid in record["refs"])

    def carry_headings_forward(self) -> None:
        """A heading over a verse that English numbers into the chapter BEFORE
        (Hebrew Genesis 32:1 is English 31:55) opens the passage that goes on in
        the next chapter, not the last verse of this one: it moves to the next
        sentence, if that has none of its own."""
        for r, after in zip(self.records, self.records[1:], strict=False):
            source = verse_key(r["refs"][0])[0]
            if (
                r["id"] in self.headings
                and self.english_chapter(r["refs"][0]) < source
                and after["id"] not in self.headings
            ):
                self.headings[after["id"]] = self.headings.pop(r["id"])

    def chapters(self) -> dict[int, list[dict]]:
        """{English chapter: its sentences}, each in the chapter it starts in."""
        out: dict[int, list[dict]] = {}
        for r in self.records:
            out.setdefault(self.english_chapter(r["refs"][0]), []).append(r)
        return out

    def _words(self, chapter: int) -> list[dict]:
        folder = "grc" if self.greek else "hbo"
        path = self.root / "data" / folder / f"{self.code}.{chapter}.json"
        if not path.exists():
            return []
        return [
            w
            for verse in json.loads(path.read_text("utf-8"))["verses"].values()
            for w in verse
        ]

    def paragraph_starts(self, chapter: int, records: list[dict]) -> set[str]:
        """The ids of the sentences that open a paragraph (see the module doc)."""
        chapters = {verse_key(v)[0] for r in records for v in r["refs"]}
        order = [w for c in sorted(chapters) for w in self._words(c)]
        by_id = {w["id"]: w for w in order}
        before = {b["id"]: a for a, b in zip(order, order[1:], strict=False)}
        starts = set()
        for i, r in enumerate(records):
            first = r["source"]["tokens"][0]
            word, prev = by_id.get(first), before.get(first)
            if (
                i == 0
                or prev is None
                or _HEBREW_PARAGRAPH.search(prev["after"])
                or (
                    word
                    and word["text"][:1].isupper()
                    and word["lemma"][:1].islower()
                    and prev["after"].strip().endswith(".")
                )
            ):
                starts.add(r["id"])
        return starts

    def chapter_html(self, chapter: int, records: list[dict]) -> str:
        starts = self.paragraph_starts(chapter, records)
        out: list[str] = []
        para: list[str] | None = None
        in_disputed = False

        title: list[str] = []
        # Verse sets each line on its own; prose runs its verses together.
        joiner = "<br>" if self.poetry else " "

        def close():
            """End the paragraph in hand, if any."""
            nonlocal para
            if para:
                out.append("<p>" + joiner.join(para) + "</p>")
            para = None

        def close_title():
            if title:
                out.append("<p><em>" + " ".join(title) + "</em></p>")
                title.clear()

        # A psalm whose title shares its first verse (see PSALM_TITLE).
        peel = self.code in TITLED and not any(self.is_title(r) for r in records)
        for r in records:
            if self.is_title(r):
                # A psalm's title follows its heading and precedes its first line.
                close()
                heading = self.headings.get(r["id"])
                if heading and not title:
                    out.append(f"<h3>{escape(heading_text(heading), quote=False)}</h3>")
                title.extend(escape(text, quote=False) for _, text in verses_of(r))
                continue
            close_title()
            disputed = any(is_disputed(v) for v in r["refs"])
            heading = self.headings.get(r["id"])
            if heading or disputed != in_disputed:
                close()
            # The passage's heading above its note, so the note and the
            # bracketed text it explains stay together.
            if in_disputed and not disputed:
                out.append("</blockquote>")
            if heading:
                out.append(f"<h3>{escape(heading_text(heading), quote=False)}</h3>")
            if disputed and not in_disputed:
                out.append(
                    f"<p><em>{escape(self.disputed_note(r), quote=False)}</em></p><blockquote>"
                )
            in_disputed = disputed
            texts = [text for _, text in verses_of(r, self.poetry)]
            if peel:
                peel = False
                heading_title, texts[0] = split_psalm_title(texts[0])
                if heading_title:
                    close()
                    title.append(escape(heading_title, quote=False))
                    close_title()
            if para is None or r["id"] in starts:
                close()
                para = []
            # A verse the peeled title used up whole leaves nothing to set.
            para.extend(escape(text, quote=False).replace("\n", "<br>") for text in texts if text)
        close()
        if in_disputed:
            out.append("</blockquote>")
        return "".join(out)

    def disputed_note(self, record: dict) -> str:
        first, last = next(
            (a, b)
            for a, b in DISPUTED
            if a.startswith(f"{self.code}.")
            and verse_key(a) <= verse_key(record["refs"][0]) <= verse_key(b)
        )
        (c1, v1), (c2, v2) = verse_key(first), verse_key(last)
        span = f"{c1}:{v1}–" + (str(v2) if c1 == c2 else f"{c2}:{v2}")
        return DISPUTED_NOTE.format(book=self.name, ref=f"{self.name} {span}")

    def embed(self, html: str) -> str:
        """Replace each {{OWB:<record id>}} with that sentence's text."""

        def text(m: re.Match) -> str:
            if m[1] not in self.by_id:
                raise CommandError(f"editorial quotes unknown sentence {m[1]}")
            return escape(
                " ".join(t for _, t in verses_of(self.by_id[m[1]])), quote=False
            )

        return _EMBED.sub(text, html)


class Command(BaseCommand):
    help = "Build one book of the Open Word Bible (English, Balanced) from an OWB checkout."

    def add_arguments(self, parser):
        parser.add_argument(
            "owb", type=Path, help="a checkout of the open-word-bible repo"
        )
        parser.add_argument("code", help="the book's USFM code, e.g. JHN")

    def handle(self, *args, **opts):
        code = opts["code"].upper()
        editorial = EDITORIAL / code
        if not editorial.is_dir():
            raise CommandError(f"no editorial in {editorial}")
        meta = json.loads((editorial / "book.json").read_text("utf-8"))
        source = Source(opts["owb"].resolve(), code)

        bodies = [
            (
                "Introduction",
                source.embed((editorial / "introduction.html").read_text("utf-8")),
            )
        ]
        # "Psalm 23", not "Psalms 23": a chapter of the book can have its own label.
        label = meta.get("chapter_label", source.name)
        bodies += [
            (f"{label} {chapter}", source.chapter_html(chapter, records))
            for chapter, records in sorted(source.chapters().items())
        ]
        bodies.append(
            (
                "Conclusion",
                source.embed((editorial / "conclusion.html").read_text("utf-8")),
            )
        )
        with transaction.atomic():
            self._write(meta, source, bodies)

    def _write(self, meta: dict, source: Source, bodies: list[tuple[str, str]]) -> None:
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None
        slug = meta["slug"]
        content = {
            "author": author,
            "title": meta["title"],
            "subtitle": meta["subtitle"],
            "cover_title": meta.get("cover_title", ""),
            "description": meta["description"],
            "qa": meta["qa"],
            "cover_color": meta["cover_color"],
            "source_url": f"{SITE}/read/#{source.code.lower()}",
            "attribution": (
                f"Scripture from the Open Word Bible ({SITE}), English, Balanced level, "
                f"commit {source.commit[:12]}: dedicated to the public domain under CC0 1.0. "
                "The introduction and conclusion are by Ochorus."
            ),
        }
        book, _ = Book.objects.update_or_create(
            slug=slug,
            language=LANGUAGE,
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.AI_UNREVIEWED,
                "is_published": True,
                "sort_order": book_sort_order(slug),
            },
        )
        book.chapters.all().delete()
        total = 0
        for order, (title, body) in enumerate(bodies, start=1):
            cleaned = clean_fragment(body)
            curled, _ = convert(cleaned, outer_guillemets=False)
            assert_punctuation_only(cleaned, curled, f"{slug} {title}")
            chapter = Chapter.objects.create(
                book=book,
                order=order,
                title=title,
                body_html=settled_chapter_body(slug, order, curled),
            )
            total += chapter.word_count
        self.stdout.write(
            f"built {slug}: {len(bodies)} chapters, {total} words (OWB {source.commit[:12]})"
        )
