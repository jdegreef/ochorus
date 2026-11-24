"""A book chapter's URL segment: the backend twin of the frontend's
``chapterSegment`` (``frontend/src/lib/reading-schema.ts``).

A Bible book (the ``the-bible`` series) is stored as an introduction at order
1, its N chapters at 2..N+1 and a conclusion at N+2 (``build_owb_book``). Its
URLs follow the Bible's numbering instead (bug #15): ``introduction``, ``1`` ..
``N``, ``conclusion``. Every other book's segment is its order. Anything that
writes a reader-site chapter link — an email, a glossary passage — builds it
here, so it opens the chapter the stored order names.
"""

BIBLE_SERIES = "the-bible"


def bible_chapter_counts() -> dict[str, int]:
    """{slug: Bible chapters} for the published English Bible books, once per
    content revision. The layout is the same in every language that has them."""
    from django.db.models import Count

    from .invalidation import revision_cached
    from .models import Book

    def compute():
        rows = (
            Book.objects.filter(series__slug=BIBLE_SERIES, language="en")
            .annotate(n=Count("chapters"))
            .values_list("slug", "n")
        )
        return {slug: n - 2 for slug, n in rows if n >= 3}

    return revision_cached("default", "bible-chapter-counts", compute, timeout=3600)


def chapter_segment(slug: str, order: int) -> str:
    """The URL segment for stored chapter ``order`` of book ``slug``."""
    n = bible_chapter_counts().get(slug)
    if n is None:
        return str(order)
    if order <= 1:
        return "introduction"
    if order >= n + 2:
        return "conclusion"
    return str(order - 1)
