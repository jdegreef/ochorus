"""Hand-written search snippets for book editions.

A book's ``description`` is its blurb: two to five sentences, written for the
book page. As a ``<meta name="description">`` it was cut at ~160 characters
mid-thought (136 of 154 English descriptions ran past 300), so Google either
showed the fragment or wrote its own snippet from the page. A snippet is a
different piece of writing: one sentence, 90–125 characters, saying what the
book IS, sized so the page's "Free PDF & EPUB download." lead still fits.

Curated in ``data/book_meta/<language>.json`` rather than as a Book column
for the reason ``alternate_titles`` gives: it is editorial copy that sits
BESIDE the content, keyed by the slug that is the work's identity, and a new
column would mean a migration plus an edit to every fixture file for text the
reader never sees on the page. One file per language, keyed by slug, so a
translated edition gets its own when someone writes it (the same layout as
``data/plan_translations``). An edition with none keeps the old
behaviour (its description, trimmed), so a missing entry is never a regression.

Every value is written from the book's own description, never invented; the
fixture gate in ``tests_meta_descriptions`` holds the keys to published books
and the lengths to the budget.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).parent / "data" / "book_meta"

#: The budget a snippet is written to: ~160 characters is what Google shows,
#: less the ~35 of "Free PDF & EPUB download. " the book page may lead with.
MAX_LENGTH = 125


@lru_cache(maxsize=1)
def table() -> dict[str, dict[str, str]]:
    """``{language: {slug: snippet}}`` from every ``<language>.json``."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(DIR.glob("*.json"))
    }


def meta_description(slug: str, language: str) -> str:
    """The edition's search snippet, or ``""`` when none has been written."""
    return table().get(language, {}).get(slug, "")
