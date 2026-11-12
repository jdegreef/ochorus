"""Related passages for a chapter of the Bible itself — the reader's
cross-references, from OpenBible.info's crowd-voted list (CC BY).

The data is ``library/data/bible/crossrefs-en.json.gz``, built from the Open
Word Bible's ``data/crossrefs`` by ``manage.py build_owb_crossrefs`` (which
says how a chapter's few are chosen). CC BY requires the credit, so the reader
shows ``CREDIT`` wherever it shows the list; the file carries it too.

English only: the Bible books are English rows, and so are the labels.
"""

from __future__ import annotations

import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent / "data" / "bible" / "crossrefs-en.json.gz"

#: The series whose books are the Bible itself — ``build_owb_book.SERIES_SLUG``
#: (a test holds the two together; a command module is not imported here).
BIBLE_SERIES = "the-bible"

#: A Bible book's reader chapter is titled with its Bible chapter ("Romans 8",
#: "Psalm 23"); the introduction and conclusion carry no number.
_TRAILING_NUMBER = re.compile(r"\s(\d+)$")


@lru_cache(maxsize=1)
def _books() -> dict[str, dict[str, list]]:
    if not BUNDLE.is_file():
        return {}
    return json.loads(gzip.decompress(BUNDLE.read_bytes()))["books"]


def is_bible_book(book) -> bool:
    """An English edition in the Bible series (``build_owb_book``)."""
    return book.language == "en" and book.series_id is not None and book.series.slug == BIBLE_SERIES


def related_passages(book, chapter, published: frozenset[str]) -> list[dict]:
    """The passages to read beside reader chapter ``chapter`` of Bible book
    ``book``: ``[{"reference", "book", "order"}]``, each a reader chapter of a
    published Bible book (``published``: their slugs). [] for the introduction
    and conclusion, and for a chapter whose title disagrees with its place
    (Bible chapter n is reader chapter n + 1) — never another chapter's list.
    """
    m = _TRAILING_NUMBER.search(chapter.title or "")
    if not m or int(m.group(1)) != chapter.order - 1:
        return []
    rows = _books().get(book.slug, {}).get(m.group(1), [])
    return [
        {"reference": label, "book": slug, "order": n + 1}
        for label, slug, n in rows
        if slug in published
    ]


def published_bible_slugs() -> frozenset[str]:
    from .models import Book

    return frozenset(
        Book.objects.filter(
            series__slug=BIBLE_SERIES, language="en", is_published=True
        ).values_list("slug", flat=True)
    )
