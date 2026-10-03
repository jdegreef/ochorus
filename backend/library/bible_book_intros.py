"""A short overview of each book of the Bible, for its ``/scripture/<book>/`` page.

The book page lists what the library does with a book of the Bible — its
chapter pages, the verses the writers stop at, the works that return to it —
and for a short or little-quoted book that was a few dozen words: a page that
names "Jonah" and says nothing about it. One paragraph of house-written
orientation (what the book is, who it is traditionally attributed to, what it
is about) gives a reader somewhere to start and the page a body of its own.

Editorial copy beside the content, keyed by the scripture slug
(``scripture_graph.book_slug``), in ``data/bible_books/<language>.json`` — the
``data/book_meta`` layout. English only today, like the scripture graph. Kept
conservative on purpose: authorship is "traditionally attributed" wherever it
is debated, and quotations are the familiar KJV wording.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).parent / "data" / "bible_books"


@lru_cache(maxsize=1)
def table() -> dict[str, dict[str, str]]:
    """``{language: {book_slug: intro}}`` from every ``<language>.json``."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(DIR.glob("*.json"))
    }


def intro(book_slug: str, language: str = "en") -> str:
    """The book's overview, or ``""`` when none has been written."""
    return table().get(language, {}).get(book_slug, "")
