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

from .models import SERMON_CARD_DEFER, Sermon
from .scripture import book_of, reference_verse_ids

#: The series the Bible's books are in (``build_owb_book.SERIES_SLUG``).
BIBLE_SERIES = "the-bible"

#: Sermons the shelf shows; the rest are one link away.
SHELF_SIZE = 6


def sermons_on_book(position: int, language: str, limit: int = SHELF_SIZE) -> dict | None:
    """``{"book", "count", "sermons"}`` for the Bible book at canonical
    ``position``, or None when the library has no sermon on it in ``language``.

    ``book`` is the facet's name for it ("Psalms", "Song of Songs" — the
    parser's, which the sermons shelf filters on, not the edition's title
    "The Psalms"). ``sermons`` are the first ``limit`` in canon order of their
    text (Genesis 1 before Genesis 3), then by title, as Sermon rows ready for
    the card serializer. Two queries: every ref (a short column, a few hundred
    rows), then the shelf's rows alone.
    """
    refs = (
        Sermon.objects.filter(is_published=True, language=language)
        .exclude(scripture_ref="")
        .values_list("pk", "title", "scripture_ref")
    )
    name = None
    hits = []
    for pk, title, ref in refs:
        info = book_of(ref)
        if info is None or info[1] != position:
            continue
        name = info[0]
        hits.append((min(reference_verse_ids(ref), default=0), title, pk))
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
