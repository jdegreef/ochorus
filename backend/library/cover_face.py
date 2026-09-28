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


def cover_face(book) -> dict:
    return {
        "slug": book.slug,
        "language": book.language,
        "title": book.title,
        "subtitle": book.subtitle,
        "cover_title": book.cover_title,
        "cover_url": book.cover_url,
        "cover_color": book.cover_color,
        "series_position": book.series_position,
        "author": {
            "slug": book.author.slug,
            "name": book.author.name,
            "birth_year": book.author.birth_year,
        },
    }
