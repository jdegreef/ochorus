"""Build Sadhu Sundar Singh's *Reality and Religion* (1924).

Twenty-seven short meditations "on God, Man and Nature", written in Urdu at
Sabathu in 1923 and translated with Dr. A. J. Appasamy's help, with the
Sadhu's Preface and an Introduction by Canon B. H. Streeter. Public domain —
first published 1924 by Macmillan and Co., London.

SOURCE. No transcription exists, so this is the OCR of a 1924 London copy on
the Internet Archive (`bwb_T4-ALE-256`), read from its hOCR rather than its
plain-text layer so that paragraphs follow the print's own first-line indents
across page breaks (`library.archive_hocr`). Three things are done to it here:

* **Page furniture out.** Running heads (the book's title on the verso, the
  chapter's on the recto) and folios sit at the top of a page, folios and
  printer's signatures at the foot; a chapter opens on a fresh page under a
  roman numeral dropped to mid-page.
* **Chapters split by page.** Each of the twenty-seven opens on a page whose
  first line is its numeral; the heading line(s) under it are dropped and the
  titles come from the Contents (two headings OCR to noise).
* **OCR repairs from `data/reality-and-religion/ocr_fixes.json`**: literal
  `(find, replace)` pairs per chapter, found by aligning this scan with two
  other 1924 copies (`RealityAndReligion-MeditationsOnGodManAndNatureBySadhu
  SundarSingh`, London; `realityreligionm0000sing`, New York) — a reading two
  witnesses agree on beats the one that differs — and then by proofreading.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/reality-and-religion.en.json`, resolving the existing
`sadhu-sundar-singh` author. No `catalog.py` entry. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_reality_and_religion
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.archive_hocr import (
    Line,
    caps_core,
    fetch_hocr,
    hyphenated_forms,
    is_folio,
    join_lines,
    margins,
    parse,
)
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter

SLUG = "reality-and-religion"
AUTHOR_SLUG = "sadhu-sundar-singh"
TITLE = "Reality and Religion"
SUBTITLE = "Meditations on God, Man and Nature"
PUBLICATION_YEAR = 1924
COVER_COLOR = "#6b4f2a"
ARCHIVE_ID = "bwb_T4-ALE-256"
ATTRIBUTION = (
    "Public domain — first published 1924 by Macmillan and Co., London; "
    "translated from the Urdu with the help of Dr. A. J. Appasamy, with an "
    "introduction by Canon B. H. Streeter. Text from the Internet Archive scan "
    "of a 1924 copy, checked against two other 1924 copies."
)
DESCRIPTION = (
    "Twenty-seven short meditations by the Indian Christian sadhu, written in "
    "Urdu in the Simla hills in 1923. “I am neither a philosopher nor a "
    "theologian,” he writes, “but a humble servant of the Lord, whose "
    "delight it is to meditate on the love of God and on the great wonders of "
    "His creation.” On creation and the Incarnation, prayer and meditation, "
    "the new birth, the cross, conscience, sin and salvation, and time and "
    "eternity — each truth set out in numbered thoughts and parables drawn "
    "from nature. With an introduction by Canon B. H. Streeter."
)

#: The Contents, in order (the twenty-seven chapters after the Preface and the
#: Introduction).
CHAPTER_TITLES = [
    "The Purpose of Creation",
    "The Incarnation",
    "Prayer",
    "Meditation",
    "The Future Life",
    "The New Birth",
    "Love",
    "Thought and Sense",
    "Philosophy and Intuition",
    "Perfection",
    "Real Progress and Success",
    "The Cross",
    "Free Will",
    "Rules of Health",
    "Conscience",
    "The Worship of God",
    "The Search after Reality",
    "Repentance and Salvation",
    "Original Sin",
    "The Vedanta and Pantheism",
    "Christ our Refuge",
    "Enemies Big and Small",
    "“Strangers and Pilgrims on the Earth”",
    "Faith and Purity",
    "Revelations of Christ",
    "Humility",
    "Time and Eternity",
]
#: Heading lines under the numeral, where a heading wraps (default one).
_HEAD_LINES = {23: 2}
#: Headings the OCR turned to noise ("HHP e LURE LIKE", "Pat lnionNDEPURTEY,"):
#: their numeral and page still place them, so only the title check is waived.
_GARBLED_HEADS = {5, 24}

_DATA = Path(__file__).resolve().parent / "data" / SLUG
#: A page's top and foot, in the scan's pixel rows (pages are ~2420 tall; body
#: text runs from ~320 to ~1940). Only furniture is looked for there.
_TOP, _FOOT, _DROP = 350, 1800, 500
#: The book's spaced stops ("depends !", "hand ?") — its typesetting, not text.
_SPACED_STOP = re.compile(r"(?<=[\w”’)]) +([;:!?])")
#: The scan reads a sentence-opening "T" with a stray opening quote before it
#: (". ‘The capacities", ". ‘This strength") — fourteen times, never a quote.
_STRAY_QUOTE = re.compile(r"(?<=[.?!] )‘(?=T[a-z])")
_FIRST_WORD = re.compile(r"^((?:\d+|[IVX]+)\. )?([A-Za-z]+)(?: ([A-Za-z]+))?")


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def _is_head(text: str) -> bool:
    """A running head: the book's title or a chapter's, folio stripped."""
    core = caps_core(re.sub(r"\d", "", text))
    heads = ["REALITY AND RELIGION", "PREFACE", "INTRODUCTION",
             *(caps_core(t) for t in CHAPTER_TITLES)]
    return bool(core) and max(_similar(core, h) for h in heads) >= 0.7


def _is_roman_folio(text: str) -> bool:
    """A front-matter folio ("vii", "vill" for viii)."""
    return bool(re.fullmatch(r"[ivxlIVXL1]{1,5}[.,]?", text.strip()))


def body_lines(lines: list[Line]) -> tuple[list[Line], list[int]]:
    """Furniture out; also the index of each page's first kept line where that
    line is a chapter-opening numeral."""
    pages: dict[int, list[Line]] = {}
    for ln in lines:
        pages.setdefault(ln.page, []).append(ln)
    kept: list[Line] = []
    opens: list[int] = []
    for _, page in sorted(pages.items()):
        page = [
            ln for ln in page
            if not (ln.y0 < _TOP and (_is_head(ln.text) or is_folio(ln.text)
                                      or _is_roman_folio(ln.text)))
        ]
        while page and page[-1].y0 > _FOOT and is_folio(page[-1].text):
            page.pop()
        if page and page[0].y0 > _DROP and is_folio(page[0].text):
            opens.append(len(kept))
        kept.extend(page)
    return kept, opens


def split_book(lines: list[Line]) -> list[tuple[str, list[Line]]]:
    kept, opens = body_lines(lines)

    def find(core: set[str], start: int = 0) -> int:
        for i in range(start, len(kept)):
            if caps_core(kept[i].text) in core:
                return i
        raise CommandError(f"no line reading {sorted(core)} after line {start}")

    pre = find({"PREFACE", "PREBACE"})
    intro = find({"INTRODUCTION"}, pre)
    contents = find({"CONTENTS"}, intro)
    opens = [i for i in opens if i > contents]
    if len(opens) != len(CHAPTER_TITLES):
        raise CommandError(f"found {len(opens)} chapter openings, expected {len(CHAPTER_TITLES)}")
    end = find({"THE END"}, opens[-1])
    parts = [("Preface", kept[pre + 1:intro]), ("Introduction", kept[intro + 1:contents])]
    for n, start in enumerate(opens, start=1):
        stop = opens[n] if n < len(opens) else end
        k = 1 + _HEAD_LINES.get(n, 1)
        head = " ".join(ln.text for ln in kept[start + 1:start + k])
        title = CHAPTER_TITLES[n - 1]
        if n not in _GARBLED_HEADS and _similar(caps_core(head), caps_core(title)) < 0.85:
            raise CommandError(f"ch {n}: heading {head!r} does not read {title!r}")
        parts.append((title, kept[start + k:stop]))
    return parts


def _small_caps(para: str) -> str:
    """A chapter's opening word is set in small capitals ("THERE are", "A
    cHILD may", "WirHout faith"): set it, and a one-letter word's partner, as
    ordinary words. Misreads the case fold cannot mend are in the fixes."""
    m = _FIRST_WORD.match(para)
    if not m:
        return para
    num, first, second = m.group(1) or "", m.group(2), m.group(3)
    words = first[0].upper() + first[1:].lower()
    if len(first) == 1 and second:
        words += " " + second.lower()
    elif second:
        words += " " + second
    return num + words + para[m.end():]


def _typeset(para: str) -> str:
    """The scan's spacing and stray marks, not the author's text."""
    para = _SPACED_STOP.sub(r"\1", para)
    para = _STRAY_QUOTE.sub("", para)
    # Quotation marks set off the word ("the “ Prince of Peace”").
    para = re.sub(r"([“‘]) +(?=\w)", r"\1", para)
    para = re.sub(r"(?<=[\w.,;:!?]) +([”’])(?!\w)", r"\1", para)
    return escape(para, quote=False)


def build_chapters(lines: list[Line]) -> list[tuple[str, str]]:
    margin = margins(lines)
    keep = hyphenated_forms(lines)
    out = []
    for title, body in split_book(lines):
        paras = join_lines(body, margin, keep)
        if title not in ("Preface", "Introduction"):
            paras[0] = _small_caps(paras[0])
        paras = [_typeset(p) for p in paras]
        html = "".join(f"<p>{p}</p>" for p in paras)
        out.append((title, html))
    return out


def _fixes() -> dict[str, list[list[str]]]:
    path = _DATA / "ocr_fixes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def apply_fixes(order: int, html: str, fixes: dict[str, list[list[str]]]) -> str:
    """The data file's repairs for one chapter, each matching exactly once."""
    for find, replace in fixes.get(str(order), []):
        if html.count(find) != 1:
            raise CommandError(
                f"ch {order}: OCR fix {find!r} matches {html.count(find)} times, not once"
            )
        html = html.replace(find, replace)
    return html


class Command(BaseCommand):
    help = "Build Sadhu Sundar Singh's Reality and Religion from the 1924 scan."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        chapters = build_chapters(parse(fetch_hocr(ARCHIVE_ID)))
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
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

        fixes = _fixes()
        unknown = set(fixes) - {str(n) for n in range(1, len(chapters) + 1)}
        if unknown:
            raise CommandError(f"ocr_fixes.json names chapters that do not exist: {sorted(unknown)}")
        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            body = settled_chapter_body(SLUG, order, apply_fixes(order, body, fixes))
            wc = word_count(body)
            if wc < 150:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
