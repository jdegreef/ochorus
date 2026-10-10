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
    DJANGO_DEBUG=true uv run python manage.py build_reality_and_religion --hocr <saved _hocr.html>
"""

from __future__ import annotations

import re

from django.core.management.base import CommandError

from library.archive_book import ArchiveBookCommand, similar, small_caps, typeset
from library.archive_hocr import (
    Line,
    caps_core,
    hyphenated_forms,
    is_folio,
    join_lines,
    margins,
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

#: The running heads: the book's title (verso) and each chapter's (recto),
#: plus the front matter's.
_HEADS = ["REALITY AND RELIGION", "PREFACE", "INTRODUCTION",
          *(caps_core(t) for t in CHAPTER_TITLES)]
#: A page's top and foot, in the scan's pixel rows (pages are ~2420 tall; body
#: text runs from ~320 to ~1940). Only furniture is looked for there.
_TOP, _FOOT, _DROP = 350, 1800, 500
#: The scan reads a sentence-opening "T" with a stray opening quote before it
#: (". ‘The capacities", ". ‘This strength") — fourteen times, never a quote.
_STRAY_QUOTE = re.compile(r"(?<=[.?!] )‘(?=T[a-z])")


def _is_head(text: str) -> bool:
    """A running head: the book's title or a chapter's, folio stripped."""
    core = caps_core(re.sub(r"\d", "", text))
    return bool(core) and max(similar(core, h) for h in _HEADS) >= 0.7


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
        if n not in _GARBLED_HEADS and similar(caps_core(head), caps_core(title)) < 0.85:
            raise CommandError(f"ch {n}: heading {head!r} does not read {title!r}")
        parts.append((title, kept[start + k:stop]))
    return parts


class Command(ArchiveBookCommand):
    help = "Build Sadhu Sundar Singh's Reality and Religion from the 1924 scan."

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

    def build_chapters(self, lines: list[Line]) -> list[tuple[str, str]]:
        margin = margins(lines)
        keep = hyphenated_forms(lines)
        out = []
        for title, body in split_book(lines):
            paras = join_lines(body, margin, keep)
            if title not in ("Preface", "Introduction"):
                paras[0] = small_caps(paras[0])
            paras = [typeset(_STRAY_QUOTE.sub("", p)) for p in paras]
            out.append((title, "".join(f"<p>{p}</p>" for p in paras)))
        return out
