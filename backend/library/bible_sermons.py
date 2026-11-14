"""The library's sermons on one book of the Bible — the "Sermons on this book"
shelf on a Bible book's page.

A sermon names its text in ``Sermon.scripture_ref`` ("Psalm 23", "John 3:16");
``scripture.book_of`` parses that to the book's canonical number, the same
parse the sermons shelf's book facet uses (``SermonListSerializer
.scripture_book_order``). A Bible book in the library is a ``the-bible`` series
row whose ``series_position`` IS that canonical number (``build_owb_book``), so
the two meet on the number — no table joins them.

Only the sermon's own text counts: a sermon on John 3:16 that quotes Genesis
along the way is not a sermon on Genesis. That is what the facet means too, so
the shelf's "See all" link (``/sermons?book=<name>``) lists the same sermons.
"""

from functools import lru_cache

from .models import SERMON_CARD_DEFER, Sermon
from .scripture import book_of, reference_verse_ids

#: The series the Bible's books are in (``build_owb_book.SERIES_SLUG``).
BIBLE_SERIES = "the-bible"

#: Sermons the shelf shows; the rest are one link away.
SHELF_SIZE = 6


@lru_cache(maxsize=8192)
def _parsed(ref: str) -> tuple[tuple[str, int] | None, frozenset]:
    """A sermon ref's (facet name, canonical number) and verse ids, parsed once
    per process: the shelves below read every sermon's ref on each request, and
    a Bible book's chapter batch asks once per chapter."""
    return book_of(ref), reference_verse_ids(ref)


def _sermons_in(position: int, window: range | None, language: str, limit: int) -> dict | None:
    """``{"book", "count", "sermons"}``: the published sermons in ``language``
    whose text is in the Bible book at canonical ``position`` — and, with a
    ``window`` of verse ids, touches it — the first ``limit`` in canon order of
    their first verse (in the window), then by title. None when there is none.
    Two queries: every ref (a short column, a few hundred rows), then the
    shelf's rows alone."""
    refs = (
        Sermon.objects.filter(is_published=True, language=language)
        .exclude(scripture_ref="")
        .values_list("pk", "title", "scripture_ref")
    )
    name = None
    hits = []
    for pk, title, ref in refs:
        info, ids = _parsed(ref)
        if info is None or info[1] != position:
            continue
        if window is not None:
            ids = [v for v in ids if v in window]
            if not ids:
                continue
        name = info[0]
        hits.append((min(ids, default=0), title, pk))
    if not hits:
        return None
    hits.sort()
    wanted = [pk for _, _, pk in hits[:limit]]
    rows = {
        s.pk: s
        for s in Sermon.objects.filter(pk__in=wanted)
        .select_related("author")
        .prefetch_related("author__translations")
        .defer(*SERMON_CARD_DEFER)
    }
    return {"book": name, "count": len(hits), "sermons": [rows[pk] for pk in wanted]}


def sermons_on_book(position: int, language: str, limit: int = SHELF_SIZE) -> dict | None:
    """``{"book", "count", "sermons"}`` for the Bible book at canonical
    ``position``, or None when the library has no sermon on it in ``language``.

    ``book`` is the facet's name for it ("Psalms", "Song of Songs" — the
    parser's, which the sermons shelf filters on, not the edition's title
    "The Psalms"). ``sermons`` are the first ``limit`` in canon order of their
    text (Genesis 1 before Genesis 3), then by title, as Sermon rows ready for
    the card serializer.
    """
    return _sermons_in(position, None, language, limit)


#: Sermons a Bible chapter lists; the rest are on the book's shelf.
CHAPTER_SIZE = 4


def sermons_on_chapter(
    position: int, chapter: int, language: str, limit: int = CHAPTER_SIZE
) -> dict | None:
    """``{"book", "count", "sermons"}`` for Bible chapter ``chapter`` of the book
    at canonical ``position``: the sermons whose text lies in it (a text that
    runs on into the next chapter counts in each it touches), or None when
    there is none. ``sermons_on_book``'s rule narrowed to the chapter; ``book``
    is the facet name for the "all on this book" link, ``count`` the
    chapter's own."""
    lo = position * 1_000_000 + chapter * 1000
    return _sermons_in(position, range(lo, lo + 1000), language, limit)
