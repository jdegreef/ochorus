"""The year-long devotionals' "today's reading" — one dated entry out of a month.

A handful of books are written to be read by the CALENDAR: Simpson's *Days of
Heaven upon Earth*, Spurgeon's *Morning by Morning*, and so on. Each is stored
as twelve month chapters, and inside a month every day opens with a short
date marker — an ``<h3>`` ("January 1", "1 de enero", "Januari 1"), or, in the
Cheque Book, a ``<p>`` ("Jan. 1") above the promise's own ``<h3>`` title.

Nothing in the model records the days. They are read off the served body here,
the same way the reader sees it: an entry runs from its marker to the next
one, and its position is the marker's index among the body's TOP-LEVEL
children — the unit the reader's ``?p=`` jump counts (``quote_blocks``), so
"read in context" lands on the day's heading.

The marker is found by shape, not by month name, so a translated edition needs
no word list: a marker of the book's tag, short, holding exactly one number of
one or two digits and no colon (a verse reference has one). The month comes
from the chapter's position — ``first_month`` is the January chapter's order
(the Cheque Book's preface is chapter 1). ``tests_daily_readings`` holds every
published dated edition to twelve months of strictly increasing, in-range
days, so an import that breaks the shape fails the build rather than a reader.

A date the book has no entry for — 29 February in a 365-day book, or one of
the two days lost in the source (Our Daily Walk's 22 September, Thoughts for
the Quiet Hour's 3 October) — resolves to the nearest entry BEFORE it, and the
payload says which date it really is.
"""

from __future__ import annotations

import calendar
import re
import string
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class DatedBook:
    #: The tag a day's date marker is.
    marker: str
    #: The order of the January chapter.
    first_month: int = 1


#: The books read by the calendar, by slug — every language edition of each.
DATED_BOOKS: dict[str, DatedBook] = {
    "days-of-heaven-upon-earth": DatedBook("h3"),
    "morning-by-morning": DatedBook("h3"),
    "evening-by-evening": DatedBook("h3"),
    "our-daily-walk": DatedBook("h3"),
    "thoughts-for-the-quiet-hour": DatedBook("h3"),
    "diary-of-an-old-soul": DatedBook("h3"),
    "cheque-book": DatedBook("p", first_month=2),
}

#: A date marker is a line, not a paragraph; past this it is prose.
_MARKER_MAX = 40
_NUMBER = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")
#: A heading-like first block: a heading tag, or a short paragraph that is all
#: bold (Our Daily Walk's "MAKING A FRESH START").
_HEADING_MAX = 80
_EXCERPT_MAX = 220
#: Any leap year: the calendar every dated book is written against.
_LEAP = 2024


def _text(el) -> str:
    # A <br> is a line break in a poem (The Diary of an Old Soul); get_text()
    # would run "…to song" and "Some far-off day" together.
    parts = (
        " " if getattr(node, "name", None) == "br" else node
        for node in el.descendants
        if isinstance(node, str) or getattr(node, "name", None) == "br"
    )
    return " ".join("".join(parts).split())


def _marker_day(el, tag: str) -> int | None:
    """The day of the month ``el`` marks, or None when it is not a marker."""
    if el.name != tag:
        return None
    text = _text(el)
    if len(text) > _MARKER_MAX or ":" in text:
        return None
    numbers = _NUMBER.findall(text)
    if len(numbers) != 1:
        return None
    day = int(numbers[0])
    return day if 1 <= day <= 31 else None


def _blocks(body_html: str) -> list:
    return BeautifulSoup(f"<div>{body_html}</div>", "lxml").div.find_all(recursive=False)


@dataclass(frozen=True)
class Entry:
    day: int
    #: Top-level index of the date marker (the reader's ``?p=``).
    start: int
    #: One past the entry's last block.
    end: int
    #: The first block the day page shows: past the marker, and past the
    #: heading too when there is one (the page sets it as its own title).
    body_start: int
    label: str
    heading: str
    excerpt: str


def _tidy_heading(text: str) -> str:
    # The Cheque Book and Our Daily Walk set their titles in capitals; a card
    # line reads better in title case. Only an all-capitals line in a cased
    # script — `upper() == text` is true of every Amharic or Hindi line.
    if text.upper() == text and text.lower() != text:
        return string.capwords(text.lower())
    return text


def _is_heading(el) -> bool:
    if el.name in ("h2", "h3", "h4"):
        return True
    text = _text(el)
    if el.name != "p" or not text or len(text) > _HEADING_MAX:
        return False
    bold = "".join(_text(b) for b in el.find_all(("b", "strong"), recursive=False))
    return bold == text


def _excerpt(text: str) -> str:
    if len(text) <= _EXCERPT_MAX:
        return text
    cut = text[:_EXCERPT_MAX].rsplit(" ", 1)[0]
    return f"{cut}…"


def month_entries(body_html: str, marker: str, blocks: list | None = None) -> list[Entry]:
    """Each dated entry in one month chapter's body, in order."""
    blocks = _blocks(body_html) if blocks is None else blocks
    starts = [(i, d) for i, el in enumerate(blocks) if (d := _marker_day(el, marker))]
    entries = []
    for n, (start, day) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(blocks)
        rest = [(i, el) for i, el in enumerate(blocks[start + 1 : end], start + 1) if _text(el)]
        heading = ""
        body_start = start + 1
        if rest and _is_heading(rest[0][1]):
            heading = _tidy_heading(_text(rest[0][1]))
            body_start = rest[0][0] + 1
            rest = rest[1:]
        entries.append(
            Entry(
                day=day,
                start=start,
                end=end,
                body_start=body_start,
                label=_text(blocks[start]),
                heading=heading,
                excerpt=_excerpt(_text(rest[0][1])) if rest else "",
            )
        )
    return entries


def parse_date(value: str) -> tuple[int, int] | None:
    """``"MM-DD"`` → (month, day), or None when it is not a calendar date."""
    m = re.fullmatch(r"(\d{2})-(\d{2})", value or "")
    if not m:
        return None
    month, day = int(m[1]), int(m[2])
    if not 1 <= month <= 12 or not 1 <= day <= calendar.monthrange(_LEAP, month)[1]:
        return None
    return month, day


def format_date(month: int, day: int) -> str:
    return f"{month:02d}-{day:02d}"


def _neighbour(month: int, day: int, step: int) -> tuple[int, int]:
    """The calendar day ``step`` (±1) from (month, day), wrapping the year."""
    day += step
    if day < 1:
        month = 12 if month == 1 else month - 1
        day = calendar.monthrange(_LEAP, month)[1]
    elif day > calendar.monthrange(_LEAP, month)[1]:
        month, day = (1 if month == 12 else month + 1), 1
    return month, day


def chapter_order(slug: str, month: int) -> int:
    return DATED_BOOKS[slug].first_month + month - 1


def find_entry(book, month: int, day: int, *, served: callable):
    """The entry for (month, day) in ``book`` or the nearest one before it.

    ``served`` turns a raw body into the served one (the reader's annotation),
    so indices count what the reader counts. Walks back at most a year, across
    month chapters. Returns (month, entry, blocks) — None when the edition has
    no dated entries at all.
    """
    spec = DATED_BOOKS[book.slug]
    cache: dict[int, tuple[list, list[Entry]]] = {}

    def entries_of(m: int):
        # One month's body at a time: a month is ~60 KB of HTML, and the walk
        # back almost always ends in the month asked for (the Today shelf does
        # this for every dated book on each request).
        if m not in cache:
            body = (
                book.chapters.filter(order=chapter_order(book.slug, m))
                .values_list("body_html", flat=True)
                .first()
            )
            blocks = _blocks(served(body or ""))
            cache[m] = (blocks, month_entries("", spec.marker, blocks))
        return cache[m]

    m, d = month, day
    for _ in range(367):
        blocks, entries = entries_of(m)
        hit = next((e for e in entries if e.day == d), None)
        if hit:
            return m, hit, blocks
        m, d = _neighbour(m, d, -1)
    return None


def entry_payload(month: int, entry: Entry, requested: tuple[int, int], slug: str) -> dict:
    return {
        "date": format_date(month, entry.day),
        "requested": format_date(*requested),
        "label": entry.label,
        "heading": entry.heading,
        "excerpt": entry.excerpt,
        "chapter": chapter_order(slug, month),
        "paragraph": entry.start,
    }


def entry_html(entry: Entry, blocks: list) -> str:
    """The entry's own blocks, its date line and heading excluded (the page
    heads it with both itself)."""
    return "".join(str(el) for el in blocks[entry.body_start : entry.end])


def neighbours(month: int, day: int) -> tuple[str, str]:
    """The calendar dates either side of (month, day), as ``MM-DD``. A date the
    book lacks resolves backwards on request, so these never dead-end."""
    return format_date(*_neighbour(month, day, -1)), format_date(*_neighbour(month, day, 1))
