"""Which book editions may be downloaded as EPUB / PDF.

Split out of ``book_export`` on purpose: the book page shows its EPUB button
from this gate at serialize time, so this module is a prerender content root
(``content_sources.json``, ``render.yaml`` buildFilter) — widening the pilot
must rebuild the reader. Keeping the gate tiny keeps the renderers and their
CSS out of the build filter.

PILOT: only these editions are exportable while the format is proven on real
e-readers. Adding one needs its language's back matter in
``book_export.STRINGS`` (``tests_book_export.PilotTests`` holds that).
"""

from __future__ import annotations

#: (slug, language) editions that may be downloaded.
EXPORT_PILOT = frozenset({
    ("the-secret-of-guidance", "en"),
    # Gareth Evans — every published edition of his five books. In copyright,
    # shared with his permission: see book_export.is_in_copyright.
    ("feasting-at-the-table", "en"),
    ("feasting-at-the-table", "fr"),
    ("feasting-at-the-table", "lg"),
    ("feasting-at-the-table", "sw"),
    ("he-holds-my-tomorrows", "ar"),
    ("he-holds-my-tomorrows", "en"),
    ("he-holds-my-tomorrows", "es"),
    ("he-holds-my-tomorrows", "fr"),
    ("he-holds-my-tomorrows", "hi"),
    ("he-holds-my-tomorrows", "lg"),
    ("he-holds-my-tomorrows", "pt"),
    ("he-holds-my-tomorrows", "sw"),
    ("he-holds-my-tomorrows", "uk"),
    ("soar-like-the-eagle-3", "en"),
    ("soar-like-the-eagle-3", "es"),
    ("soar-like-the-eagle-3", "fr"),
    ("soar-like-the-eagle-3", "hi"),
    ("soar-like-the-eagle-3", "lg"),
    ("soar-like-the-eagle-3", "pt"),
    ("soar-like-the-eagle-3", "sw"),
    ("stepping-stones-2", "ar"),
    ("stepping-stones-2", "en"),
    ("stepping-stones-2", "es"),
    ("stepping-stones-2", "fr"),
    ("stepping-stones-2", "hi"),
    ("stepping-stones-2", "lg"),
    ("stepping-stones-2", "pt"),
    ("stepping-stones-2", "sw"),
    ("stepping-stones-2", "uk"),
    ("the-key-in-my-hand", "ar"),
    ("the-key-in-my-hand", "en"),
    ("the-key-in-my-hand", "es"),
    ("the-key-in-my-hand", "fr"),
    ("the-key-in-my-hand", "hi"),
    ("the-key-in-my-hand", "lg"),
    ("the-key-in-my-hand", "pt"),
    ("the-key-in-my-hand", "sw"),
    ("the-key-in-my-hand", "uk"),
})


def is_exportable(book) -> bool:
    return book.is_published and (book.slug, book.language) in EXPORT_PILOT
