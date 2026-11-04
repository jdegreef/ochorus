"""The year-long devotionals' "today's reading" — one dated entry out of a month.

A handful of books are written to be read by the CALENDAR: Simpson's *Days of
Heaven upon Earth*, Spurgeon's *Morning by Morning*, and so on. Each is stored
as twelve month chapters, and inside a month every day opens with a short
date marker — an ``<h3>`` ("January 1", "1 de enero", "Januari 1"), or, in the
Cheque Book, a ``<p>`` ("Jan. 1") above the promise's own ``<h3>`` title.

Nothing in the model records the days. They are read off the body here: an
entry runs from its marker to the next one, and its position is the marker's
index among the body's TOP-LEVEL children — the unit the reader's ``?p=`` jump
counts (``quote_blocks``), so "read in the book" lands on the day's heading.
The index is taken on the stored body, not the served one: annotating Scripture
references only wraps text inside blocks, never adds or moves one, and
``tests_daily_readings`` holds every dated month to that.

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
payload says which date it really is. Never further back than a week: an
edition missing whole months would otherwise offer June's reading as today's.

An edition's month indexes are cached against the content version (the pair
the public ETag keys on) under ONE key per edition — the default cache is a
300-entry LocMem, and a key per month (444) would cull everything else — so
the home page's Today shelf reads no chapter body once a month has been seen.
The day page re-reads its own month and serves the entry from that read, so a
stale index can never slice the wrong blocks.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup
from django.core.cache import cache

from .daily_books import DATED_BOOKS, DatedBook

#: A date marker is a line, not a paragraph; past this it is prose.
_MARKER_MAX = 40
_NUMBER = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")
_HEADING_MAX = 80
_EXCERPT_MAX = 220
#: How far back a missing date may resolve (see the module docstring).
_FALLBACK_DAYS = 7
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


def _marker_day(el, text: str, tag: str) -> int | None:
    """The day of the month ``el`` marks, or None when it is not a marker."""
    if el.name != tag or len(text) > _MARKER_MAX or ":" in text:
        return None
    numbers = _NUMBER.findall(text)
    if len(numbers) != 1:
        return None
    day = int(numbers[0])
    return day if 1 <= day <= 31 else None


def blocks(body_html: str) -> list:
    """The body's top-level elements — what the reader's ``?p=`` counts."""
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
    #: The words the day page shows (heading and body) — a plan day's
    #: reading time.
    words: int = 0

    @property
    def title(self) -> str:
        """The day as a list names it: its date line, and the entry's own title
        where the book gives one ("January 1 — Making a Fresh Start")."""
        return f"{self.label} — {self.heading}" if self.heading else self.label


def _tidy_heading(text: str) -> str:
    # The Cheque Book and Our Daily Walk set their titles in capitals; a card
    # line reads better in title case. Only an all-capitals line in a cased
    # script — `upper() == text` is true of every Amharic or Hindi line.
    if text.upper() == text and text.lower() != text:
        from .ingest import titlecase_caps

        return titlecase_caps(text)
    return text


def _is_heading(el, text: str, spec: DatedBook) -> bool:
    if el.name in ("h2", "h3", "h4"):
        return True
    if not spec.bold_titles or el.name != "p" or not text or len(text) > _HEADING_MAX:
        return False
    # All of its words are bold, however many runs they are set in.
    return all(
        not s.strip() or s.find_parent(("b", "strong")) is not None
        for s in el.find_all(string=True)
    )


def _excerpt(text: str) -> str:
    from .search import to_word_end

    return text if len(text) <= _EXCERPT_MAX else f"{to_word_end(text, _EXCERPT_MAX, 0)}…"


def month_entries(els: list, spec: DatedBook) -> list[Entry]:
    """Each dated entry among one month chapter's top-level blocks, in order."""
    texts = [_text(el) for el in els]
    starts = [
        (i, day) for i, el in enumerate(els) if (day := _marker_day(el, texts[i], spec.marker))
    ]
    entries = []
    for n, (start, day) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(els)
        filled = (i for i in range(start + 1, end) if texts[i])
        first = next(filled, None)
        heading, body_start = "", start + 1
        if first is not None and _is_heading(els[first], texts[first], spec):
            heading, body_start = _tidy_heading(texts[first]), first + 1
            first = next(filled, None)
        entries.append(
            Entry(
                day=day,
                start=start,
                end=end,
                body_start=body_start,
                label=texts[start],
                heading=heading,
                excerpt=_excerpt(texts[first]) if first is not None else "",
                words=sum(len(texts[i].split()) for i in range(start + 1, end)),
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


def chapter_order(slug: str, month: int) -> int:
    return DATED_BOOKS[slug].first_month + month - 1


def month_body(book, month: int) -> str:
    return (
        book.chapters.filter(order=chapter_order(book.slug, month))
        .values_list("body_html", flat=True)
        .first()
        or ""
    )


def content_version() -> tuple[str, int]:
    """What a cached month index is valid for: the repo content digest and the
    admin content revision — the pair the public ETag keys on (http_cache)."""
    from .content_fixtures import content_digest
    from .models import ContentRevision

    return content_digest(), ContentRevision.current()


def _index_key(book) -> str:
    return f"daily-index:{book.pk}"


def _months(
    book, version: tuple[str, int], months, fresh: dict[int, list[Entry]] | None = None
) -> dict[int, list[Entry]]:
    """``month_entries`` for ``months`` of ``book``, through the edition's one
    cache key: ONE read, the missing months parsed, ONE write if any were.
    (LocMem unpickles the whole edition on every get, so reading it once per
    month cost a year's index twelve times over.) ``fresh`` months, parsed by
    the caller from a body it just read, replace whatever was cached. The one
    place the cache is written."""
    cached = cache.get(_index_key(book))
    index = cached[1] if cached is not None and cached[0] == version else {}
    fresh = fresh or {}
    missing = [m for m in months if m not in index and m not in fresh]
    if missing or fresh:
        spec = DATED_BOOKS[book.slug]
        index = {
            **index,
            **fresh,
            **{m: month_entries(blocks(month_body(book, m)), spec) for m in missing},
        }
        cache.set(_index_key(book), (version, index), timeout=None)
    return index


def month_index(book, month: int, version: tuple[str, int]) -> list[Entry]:
    """``month_entries`` for one month of ``book``, cached against ``version``."""
    return _months(book, version, [month])[month]


def _days_back(month: int, day: int, to_month: int, to_day: int) -> int:
    """Days from (to_month, to_day) forward to (month, day), round the year."""
    return (date(_LEAP, month, day) - date(_LEAP, to_month, to_day)).days % 366


def year_entries(book, version: tuple[str, int]) -> list[tuple[int, Entry]]:
    """Every dated entry of ``book``, January first, as (month, entry) — a
    devotional plan's days in order."""
    index = _months(book, version, range(1, 13))
    return [(m, e) for m in range(1, 13) for e in index[m]]


def entry_on(book, entry_date: str, version: tuple[str, int]) -> Entry | None:
    """The entry dated exactly ``entry_date`` ("MM-DD") — a plan day's, which
    the seed took from a real entry, so it needs no fallback. None if gone."""
    when = parse_date(entry_date)
    if when is None:
        return None
    month, day = when
    return next((e for e in month_index(book, month, version) if e.day == day), None)


def find_entry(book, month: int, day: int, version: tuple[str, int]) -> tuple[int, Entry] | None:
    """(month, entry) for the entry on (month, day) in ``book``, or the nearest
    one before it within ``_FALLBACK_DAYS`` — into the previous month (and
    year) when the date is early in its own. None when there is none."""
    for m in (month, 12 if month == 1 else month - 1):
        last = day if m == month else 31
        before = [e for e in month_index(book, m, version) if e.day <= last]
        if before:
            entry = before[-1]
            return (m, entry) if _days_back(month, day, m, entry.day) <= _FALLBACK_DAYS else None
    return None


def find_day(book, month: int, day: int, version: tuple[str, int]) -> tuple[int, Entry, str] | None:
    """For the day page: (month, entry, its stored HTML) from ONE fresh read of
    the month, so the blocks served are the blocks the entry was found in. The
    HTML leaves out the date line and heading (the page sets both itself); the
    caller links its Scripture."""
    found = find_entry(book, month, day, version)
    if found is None:
        return None
    m, cached = found
    els = blocks(month_body(book, m))
    fresh = month_entries(els, DATED_BOOKS[book.slug])
    _months(book, version, [m], fresh={m: fresh})
    entry = next((e for e in fresh if e.day == cached.day), None)
    if entry is None:  # the cached index was stale; it is fresh now
        return None
    return m, entry, "".join(str(el) for el in els[entry.body_start : entry.end])


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


def neighbours(month: int, day: int) -> tuple[str, str]:
    """The calendar dates either side of (month, day), as ``MM-DD``. A date the
    book lacks resolves backwards on request, so these never dead-end."""
    if day > 1:
        prev = (month, day - 1)
    else:
        m = 12 if month == 1 else month - 1
        prev = (m, calendar.monthrange(_LEAP, m)[1])
    if day < calendar.monthrange(_LEAP, month)[1]:
        nxt = (month, day + 1)
    else:
        nxt = (1 if month == 12 else month + 1, 1)
    return format_date(*prev), format_date(*nxt)
