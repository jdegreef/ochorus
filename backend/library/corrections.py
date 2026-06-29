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

CORRECTIONS: dict[str, dict] = {
    "the-normal-christian-life": {
        # Ch.12's title is inline ("Chapter 12: The Cross and the Soul Life") in
        # the PDF, so it isn't detected as a standalone heading. From the TOC:
        "chapter_titles": {12: "Chapter 12. The Cross and the Soul Life"},
    },
}


def chapter_title_overrides(slug: str) -> dict[int, str]:
    return CORRECTIONS.get(slug, {}).get("chapter_titles", {})
