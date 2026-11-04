"""The year-long devotionals read by the calendar (library/daily_readings.py)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatedBook:
    #: The tag a day's date marker is.
    marker: str = "h3"
    #: The order of the January chapter.
    first_month: int = 1
    #: Each day's title is an all-bold paragraph rather than a heading tag.
    bold_titles: bool = False


#: The books read by the calendar, by slug — every language edition of each.
#: The book page bakes ``slug in DATED_BOOKS`` (its "Today's reading" button),
#: which is why this module is a content root (content_sources.json). It is a
#: leaf on purpose: the serializers import it, and daily_readings' parser
#: pulls in ingest/search, which would join the serializers' import graph.
DATED_BOOKS: dict[str, DatedBook] = {
    "days-of-heaven-upon-earth": DatedBook(),
    "morning-by-morning": DatedBook(),
    "evening-by-evening": DatedBook(),
    "our-daily-walk": DatedBook(bold_titles=True),
    "thoughts-for-the-quiet-hour": DatedBook(),
    "diary-of-an-old-soul": DatedBook(),
    "cheque-book": DatedBook("p", first_month=2),
}
