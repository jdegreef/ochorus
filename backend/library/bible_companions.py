"""Read alongside: the library's classics written ON a book of the Bible.

Two shelves read this:

* a Bible book's page lists the whole works (``companion_books``) — Calvin and
  Chrysostom on Romans, Ryle and Chrysostom on Matthew, the catenas;
* a Bible CHAPTER lists the companion chapters that treat it
  (``companion_chapters``) — Romans 8 opens Calvin's "Romans 8" and Chrysostom's
  "Homily XIII: Romans 7:14", John 15 opens Murray's The True Vine.

WHICH works is declared, not derived (``COMPANIONS``): a book whose citations
lean on one Bible book is not thereby a book about it — Evening by Evening
cites the Psalms on every page, and Chrysostom's Homilies on Romans cite
Matthew more than Romans — so a work joins only when it is, by its own title, a
commentary, a catena or an exposition of that book (or of a passage in it, with
``PASSAGES``). A slug here that is not published in a language is simply
absent there.

WHERE in a work is read off its own chapter titles, which name their passage
("Romans 3", "John 1:29–51", "Homily III: Romans 1:18"), through the same
reference parser the reader's popover uses. A title spanning more than
``MAX_SPAN`` Bible chapters ("Homily I: The Gospel of Matthew") is about the
whole book and treats no chapter in particular. Works whose chapters are not
titled so (Watson's Beatitudes) hang on the one passage they expound
(``PASSAGES``). The catenas are left out of the chapter list: the chapter page
already opens their excerpts verse by verse (``library/catena``).

English only today, as the Bible books are.
"""

from __future__ import annotations

from functools import lru_cache

from .catena import CATENAS
from .content_fixtures import content_digest
from .scripture import reference_verse_ids

#: {canonical number of a book of the Bible: the works on it, in the order the
#: shelf shows them — the close commentaries first, then the catenas, then a
#: book on one passage of it}.
COMPANIONS: dict[int, tuple[str, ...]] = {
    2: ("ten-commandments",),
    19: ("catena-on-the-psalms",),
    22: ("union-and-communion",),
    40: (
        "expository-thoughts-on-matthew",
        "homilies-on-matthew",
        "catena-aurea-matthew",
        "catena-on-matthew",
        "the-beatitudes",
        "the-lords-prayer",
    ),
    41: ("catena-aurea-mark",),
    42: ("catena-aurea-luke",),
    43: ("catena-aurea-john", "catena-on-john", "true-vine"),
    45: ("commentary-on-romans", "homilies-on-romans", "catena-on-romans"),
    58: ("way-into-holiest",),
    62: ("homilies-on-the-first-epistle-of-john",),
}

#: Works on one passage whose chapters do not name it: (canonical number, the
#: Bible chapter they expound). The whole work is listed on that chapter.
PASSAGES: dict[str, tuple[int, int]] = {
    "ten-commandments": (2, 20),
    "the-beatitudes": (40, 5),
    "the-lords-prayer": (40, 6),
    "true-vine": (43, 15),
}

#: A chapter title naming more Bible chapters than this is about the book, not
#: a chapter of it ("The Gospel of Matthew", "Romans 9–16").
MAX_SPAN = 3

#: How many companion chapters a Bible chapter lists.
CHAPTER_LIMIT = 6


def companion_slugs(position: int) -> tuple[str, ...]:
    """The works declared on the Bible book at canonical ``position``."""
    return COMPANIONS.get(position, ())


def companion_books(position: int, language: str):
    """The published works on the Bible book at ``position`` in ``language``,
    in ``COMPANIONS`` order, as Book rows ready for the card serializer."""
    from .models import Book
    from .serializers import BOOK_CARD_ANNOTATIONS

    slugs = companion_slugs(position)
    if not slugs:
        return []
    found = {
        b.slug: b
        for b in Book.objects.filter(slug__in=slugs, language=language, is_published=True)
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(**BOOK_CARD_ANNOTATIONS)
    }
    return [found[s] for s in slugs if s in found]


def title_chapters(title: str, position: int) -> tuple[int, ...]:
    """The Bible chapters of book ``position`` a companion chapter's title
    names ("Homily I: 1 John 1:1–2:11" -> (1, 2)), or () when it names none,
    another book, or more than ``MAX_SPAN`` chapters."""
    ids = reference_verse_ids(title or "")
    if not ids:
        return ()
    first, last = min(ids), max(ids)
    if first // 1_000_000 != position or last // 1_000_000 != position:
        return ()
    c1, c2 = first // 1000 % 1000, last // 1000 % 1000
    if c2 - c1 + 1 > MAX_SPAN:
        return ()
    return tuple(range(c1, c2 + 1))


@lru_cache(maxsize=4)
def _index(language: str, digest: str) -> dict[tuple[int, int], tuple[dict, ...]]:
    """{(canonical number, Bible chapter): the companion chapters on it} for
    ``language`` — built once per deploy (``digest`` is the shipped content's)
    from every companion's chapter titles, published or not (that is asked
    live, in ``companion_chapters``). Catenas are left out (see the module
    doc); a passage work is one entry on its passage."""
    from .models import Book, Chapter

    catenas = set(CATENAS.values())
    books = {
        b.pk: b
        for b in Book.objects.filter(
            slug__in=[s for slugs in COMPANIONS.values() for s in slugs if s not in catenas],
            language=language,
        ).select_related("author")
    }
    position_of = {s: pos for pos, slugs in COMPANIONS.items() for s in slugs}
    out: dict[tuple[int, int], list[dict]] = {}

    def entry(book, order, title):
        return {
            "book": book.slug,
            "book_title": book.title,
            "author_name": book.author.name,
            "order": order,
            "title": title,
        }

    for book in books.values():
        if book.slug in PASSAGES:
            out.setdefault(PASSAGES[book.slug], []).append(entry(book, None, ""))
    rows = Chapter.objects.filter(book_id__in=[pk for pk, b in books.items() if b.slug not in PASSAGES])
    for book_id, order, title in rows.order_by("book_id", "order").values_list("book_id", "order", "title"):
        book = books[book_id]
        position = position_of[book.slug]
        for chapter in title_chapters(title, position):
            out.setdefault((position, chapter), []).append(entry(book, order, title))
    # Each Bible chapter's list in COMPANIONS order, then chapter order.
    rank = {s: i for slugs in COMPANIONS.values() for i, s in enumerate(slugs)}
    return {
        key: tuple(sorted(v, key=lambda e: (rank[e["book"]], e["order"] or 0)))
        for key, v in out.items()
    }


def companion_chapters(position: int, chapter: int, language: str) -> list[dict]:
    """The companion chapters on Bible chapter ``chapter`` of the book at
    ``position``: ``[{book, book_title, author_name, order, title}]``, at most
    ``CHAPTER_LIMIT``. ``order`` is None (and ``title`` "") for a passage
    work, which opens at its start."""
    from .models import Book

    if not any(s not in CATENAS.values() for s in companion_slugs(position)):
        return []
    entries = _index(language, content_digest()).get((position, chapter), ())
    if not entries:
        return []
    # The layout is the deploy's; whether each work is published is asked now,
    # as catena does, so an unpublished one drops out at once, not next deploy.
    live = set(
        Book.objects.filter(
            slug__in={e["book"] for e in entries}, language=language, is_published=True
        ).values_list("slug", flat=True)
    )
    return [e for e in entries if e["book"] in live][:CHAPTER_LIMIT]
