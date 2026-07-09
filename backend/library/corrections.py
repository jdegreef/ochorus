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
    "talks-to-the-farmer": {
        # Ch.1's title block is fused with the subhead and opening body text in
        # one oversized block ("THE SLUGGARD'S FARM  Introduction  From a
        # neglected field…"), so no title can be borrowed. From the TOC:
        "chapter_titles": {1: "The Sluggard's Farm"},
    },
}


def chapter_title_overrides(slug: str) -> dict[int, str]:
    return CORRECTIONS.get(slug, {}).get("chapter_titles", {})


# --- Body-text corrections ------------------------------------------------------
# Extraction artifacts inside chapter bodies that heuristics can't fix:
#
#   dropcap_letters: {order: "G"} — the chapter's opening letter was an IMAGE
#     drop cap in the source, so the text layer starts one letter short
#     ("reat numbers…"). The letter is unambiguous from context; we restore it.
#   replacements: [(old, new)] — exact-string repairs for OCR damage (a letter
#     split off before punctuation: "blesse d!" → "blessed!"). Kept as literal
#     pairs — no clever regex — so scripture citations like "Song i." are never
#     touched. Verify each in context before adding.
#
# Applied on every import AND backfillable over stored rows (management command
# `apply_body_corrections`, plus a data migration for prod).

import re as _re

BODY_CORRECTIONS: dict[str, dict] = {
    "the-way-to-god": {
        # Source defect (Gutenberg #30449, ch. 8): the epigraph line lost its
        # quotation and opening paren — only "Colossians iii. 11.)" remains.
        "replacements": [
            ("<p>Colossians iii. 11.)</p>", "<p>(Colossians iii. 11.)</p>"),
        ],
    },
    "around-the-wicket-gate": {
        # Image drop caps (Gutenberg source) — first letter of every chapter.
        "dropcap_letters": {
            1: "G",   # G(reat numbers of persons…)
            2: "W",   # W(e cannot, too often…)
            3: "T",   # T(here is a wretched tendency…)
            4: "T",   # T(o many, faith seems…)
            5: "I",   # I(t is an odd product…)
            6: "I",   # I(t may be that the reader…)
            7: "T",   # T(o help the seeker…)
            8: "A",   # A(lthough it is by no means…)
            9: "I",   # I(n these days…)
            10: "S",  # S(ome think it hard…)
            11: "F",  # F(riends, if now you have begun…)
        },
    },
    "the-unselfishness-of-god": {
        "replacements": [
            ("blesse d!", "blessed!"),
            ("crystallize d,", "crystallized,"),
            ("scepti c!", "sceptic!"),
            ("lif e.", "life."),
            ("evangelical s,", "evangelicals,"),
        ],
    },
    "feasting-at-the-table": {
        "replacements": [("repea t:", "repeat:"), ("wif e!", "wife!")],
    },
    "the-christians-secret-of-a-happy-life-4": {
        "replacements": [("sel f,", "self,")],
    },
    "men-of-prayer-2": {
        "replacements": [("conversatio n.", "conversation.")],
    },
    "the-person-and-work-of-the-holy-spirit": {
        "replacements": [
            ("Jesu s,", "Jesus,"),
            ("faithfulnes s.", "faithfulness."),
            ("eart h”", "earth”"),
            ("saved i. e. ,", "saved i.e.,"),
            ("salvatio n,", "salvation,"),
        ],
    },
}

# First lowercase letter opening the first paragraph of a body.
_FIRST_LOWER = _re.compile(r"<p[^>]*>\s*([a-z])")


def apply_body_corrections(slug: str, order: int, body_html: str) -> str:
    """Apply this book's body corrections to one chapter's HTML. Idempotent."""
    entry = BODY_CORRECTIONS.get(slug)
    if not entry:
        return body_html
    for old, new in entry.get("replacements", []):
        body_html = body_html.replace(old, new)
    letter = entry.get("dropcap_letters", {}).get(order)
    if letter:
        # Only when the first paragraph still starts lowercase (not yet fixed).
        m = _FIRST_LOWER.search(body_html, 0, 200)
        if m:
            body_html = body_html[: m.start(1)] + letter + body_html[m.start(1) :]
    return body_html
