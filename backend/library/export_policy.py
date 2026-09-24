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
EXPORT_PILOT = frozenset({("the-secret-of-guidance", "en")})


def is_exportable(book) -> bool:
    return book.is_published and (book.slug, book.language) in EXPORT_PILOT
