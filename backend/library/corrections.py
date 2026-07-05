"""Manual, per-book corrections applied after automatic PDF extraction.

The importer gets most things right, but some books have quirks the heuristics
can't infer — e.g. a chapter whose title is formatted inline rather than as a
separate heading. Record those fixes here, keyed by book slug, so they survive
every re-import. Keep this list small and specific; if a pattern recurs across
books, prefer improving the importer over adding one-off entries here.

Shape:
    CORRECTIONS = {
        "<book-slug>": {
            "chapter_titles": {<order:int>: "<exact final title>"},
        },
    }
"""

from __future__ import annotations

# Catalogue slugs to skip on a full import (e.g. duplicate/teen editions we don't
# want in the library). An explicit `import_ochorus <slug>` still imports them.
EXCLUDED_SLUGS: set[str] = {
    # Teens edition of "The Person and Work of the Holy Spirit"; we keep the
    # adult original (the-person-and-work-of-the-holy-spirit).
    "the-person-and-work-of-the-holy-spirit-2",
}

CORRECTIONS: dict[str, dict] = {
    "the-normal-christian-life": {
        # Ch.12's title is inline ("Chapter 12: The Cross and the Soul Life") in
        # the PDF, so it isn't detected as a standalone heading. From the TOC:
        "chapter_titles": {12: "The Cross and the Soul Life"},
    },
    "jesus-himself-2": {
        # Ch.2's title is a long quoted sentence that wraps across lines in the
        # PDF, so the title-borrow captured only the final word ("You"). Full
        # title from the PDF's table of contents:
        "chapter_titles": {2: "I will come and dwell with you, and I will never leave you"},
    },
}


def chapter_title_overrides(slug: str) -> dict[int, str]:
    return CORRECTIONS.get(slug, {}).get("chapter_titles", {})
