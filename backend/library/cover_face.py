"""What a cover DRAWS, for any payload that shows one small.

Every cover file is now a ground — a painting or a plate — and the title is set
over it by the frontend's ``BookCover`` (see ``$lib/coverArt.isPlateCover``).
A payload that sent only ``cover_url`` left its thumbnail a bare ground: the
plan and topic fans and the search rows drew flat colour blocks for every
plate-covered book. These are the fields ``BookCover`` reads (its
``CoverFace`` type) — nothing about the card, so a tile stays small.

The author must be loaded with the book (``select_related("author")``); every
caller's queryset already joins it.
"""


# The author fields a cover draws; ``CoverAuthorSerializer`` uses the same list.
COVER_AUTHOR_FIELDS = ("slug", "name", "birth_year")

# Everything else a cover reads (the frontend's ``COVER_FACE_KEYS``).
COVER_FACE_FIELDS = (
    "slug", "language", "title", "subtitle", "cover_title", "cover_byline",
    "cover_url", "cover_color", "series_position",
)


def cover_face(book) -> dict:
    return {
        **{f: getattr(book, f) for f in COVER_FACE_FIELDS},
        "author": {f: getattr(book.author, f) for f in COVER_AUTHOR_FIELDS},
    }
