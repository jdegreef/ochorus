"""Related passages for a chapter of the Bible itself — the reader's
cross-references, from OpenBible.info's crowd-voted list (CC BY).

The data is ``library/data/bible/crossrefs-en.json.gz``, built from the Open
Word Bible's ``data/crossrefs`` by ``manage.py build_owb_crossrefs`` (which
says how a chapter's few are chosen). CC BY requires the credit: the file
carries it with the data, and the reader prints it under every list
(``reader.crossrefsCredit``).

Every language with the Bible: the data is references, the same in any
language (a book slug and a chapter, which every edition shares). Only the
label is English ("Luke 3:35"); for another edition its book name is that
edition's own, taken from the book's chapter titles ("Lucas 3", "Psaume 23"),
so a chip reads like the chapter it opens.
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

#: How many related passages a chapter shows: a short row, easy to ignore.
PER_CHAPTER = 6

#: A Bible book's reader chapter is titled with its Bible chapter ("Romans 8",
#: "Psalm 23"); the introduction and conclusion carry no number.
_TRAILING_NUMBER = re.compile(r"\s(\d+)$")


@lru_cache(maxsize=1)
def _books() -> dict[str, dict[str, list]]:
    if not BUNDLE.is_file():
        return {}
    return json.loads(gzip.decompress(BUNDLE.read_bytes()))["books"]


def is_bible_book(book) -> bool:
    """An English edition in the Bible series (``build_owb_book``). The gate
    for what is still English-only (the overview card); cross-references use
    ``is_bible_edition``."""
    return book.language == "en" and is_bible_edition(book)


def is_bible_edition(book) -> bool:
    """An edition of the Bible itself in any language (series ``the-bible``)."""
    return book.series_id is not None and book.series.slug == BIBLE_SERIES


#: A cross-reference label: the book's English name, then chapter (and verses).
_LABEL = re.compile(r"^(?P<name>.+?) (?P<ref>\d+(?::\S+)?)$")


def localized_label(label: str, slug: str, names: dict[str, str]) -> str:
    """``label`` ("Luke 3:35") with the book's name in the edition's language
    (``names``: slug -> name, from its chapter titles); unchanged when the name
    is unknown or the label is not of that shape."""
    m = _LABEL.match(label)
    name = names.get(slug)
    return f"{name} {m['ref']}" if m and name else label


def chapter_names(language: str) -> dict[str, str]:
    """slug -> the book's name as its chapters are titled in ``language``
    ("gospel-of-luke" -> "Lucas", "psalms" -> "Salmo"): the title of its first
    Bible chapter (reader chapter 2) without the number."""
    from .models import Chapter

    rows = Chapter.objects.filter(
        book__series__slug=BIBLE_SERIES, book__language=language, book__is_published=True, order=2
    ).values_list("book__slug", "title")
    return {
        slug: title[: m.start()]
        for slug, title in rows
        if (m := _TRAILING_NUMBER.search(title or ""))
    }


def related_passages(book, chapter, published, names=None) -> list[dict]:
    """The passages to read beside reader chapter ``chapter`` of Bible book
    ``book``: ``[{"reference", "book", "order"}]``, each a reader chapter of a
    published Bible book (``published()``: their slugs, asked only when there
    is a row to filter). [] for the introduction
    and conclusion, and for a chapter whose title disagrees with its place
    (Bible chapter n is reader chapter n + 1) — never another chapter's list.
    ``names()`` gives the edition's book names for the labels (English keeps
    the data's own).
    """
    m = _TRAILING_NUMBER.search(chapter.title or "")
    if not m or int(m.group(1)) != chapter.order - 1:
        return []
    rows = _books().get(book.slug, {}).get(m.group(1), [])
    if not rows:
        return []
    shown = [(label, slug, n) for label, slug, n in rows if slug in published()][:PER_CHAPTER]
    local = names() if names is not None and book.language != "en" else {}
    return [
        {"reference": localized_label(label, slug, local), "book": slug, "order": n + 1}
        for label, slug, n in shown
    ]


def published_bible_slugs(language: str = "en") -> frozenset[str]:
    """The published Bible books in ``language``: a passage links only where
    that edition has the book (no English fallback)."""
    from .models import Book

    return frozenset(
        Book.objects.filter(
            series__slug=BIBLE_SERIES, language=language, is_published=True
        ).values_list("slug", flat=True)
    )
