"""Repairs to imported book text that the SOURCE itself got wrong.

Distinct from `corrections.py`, which fixes what the PDF *extractor* got wrong
(drop caps, borrowed titles, stray page numbers). These are defects in the text
we were given: a quotation that is not the verse it cites, a block the source
duplicated. They were found by translators, who hit them in five languages at
once and could not silently paper over them.

Two callers must agree, so the logic lives here and not in either of them:

* `scripts/` / the fixture, so a fresh database is built clean;
* migration 0058, so the rows already in production are repaired.

`seed_books` only creates chapters for a book it has never seen — it never
rewrites an existing book's chapter bodies (it reports the drift and moves on).
So a fixture edit alone would leave production exactly as wrong as it is now.
That is why the migration exists, and why editing these functions after they
have shipped changes nothing on its own.

Keyed by `(slug, order)` and applied to a chapter body in ANY language: each
repair either matches that language's text or no-ops.
"""

from __future__ import annotations

import re

_PARA = re.compile(r"<p>(.*?)</p>", re.S)

# ch01 prints the text of 2 Corinthians 10:13 under the reference "1 Corinthians
# 12:11", and then argues "Here, will is ascribed to the Spirit" — which only
# the real verse supports. Every replacement below is that edition's OWN
# rendering of the verse in ch20, so nothing is invented and a reader who meets
# the verse twice now meets it the same way. Luganda and Arabic already quote it
# correctly (their translators caught the error and quoted the real verse), so
# they need no entry.
WRONG_VERSE = [
    (
        "But we will not boast beyond limits, but will boast only about the "
        "area of influence God assigned to us, to reach even to you.",
        "All these are empowered by the same Spirit, who apportions to each "
        "one individually as he wills.",
    ),
    (
        "Pero nosotros no nos gloriaremos desmedidamente, sino conforme a la "
        "medida de la regla que Dios nos repartió, para llegar también hasta "
        "vosotros",
        "Mas todas estas cosas obra uno y el mismo Espíritu, repartiendo "
        "particularmente a cada uno como quiere",
    ),
    (
        "Lakini sisi hatutajisifu kupita kiasi, bali kwa kadiri ya eneo la "
        "utumishi Mungu alilotugawia, hata kuwafikia ninyi.",
        "Lakini kazi hizi zote huzitenda Roho yule mmoja, yeye yule, "
        "akimgawia kila mtu peke yake kama apendavyo yeye.",
    ),
    # OCR split inside the John 7:17 quotation repaired below.
    ("on my author ity", "on my authority"),
]


def fix_wrong_verse(body_html: str) -> str:
    for bad, good in WRONG_VERSE:
        body_html = body_html.replace(bad, good)
    return body_html


def fix_duplicated_block(body_html: str) -> str:
    """Collapse ch08's duplicated paragraphs 10-12 back into one.

    The source repeats itself here, and in the repetition it mangles a verse.
    Paragraph 10 opens a thought, then breaks off mid-quotation with a clause
    carried over from paragraph 9 — so it has Jesus saying, at John 7:17,
    "...he is saved there on the spot", which is not that verse and not
    anything he says. Paragraph 11 then repeats the tail of 9 and the head of
    10, and only paragraph 12 states the thought properly, verse and all.

    What the author wrote is paragraph 10's opening sentence followed by
    paragraph 12. Recover exactly that, and drop the wreckage.

    Deliberately structural rather than a list of strings to match: the same
    duplication was faithfully reproduced by every translator, so this has to
    work in five languages. Splitting on the first sentence is what does that —
    on the four editions that repeat themselves verbatim it agrees exactly with
    the longest-common-span the duplication itself defines, and it still works
    on the Arabic, which varied the wording between the two copies the way
    Arabic prose does.
    """
    paras = _PARA.findall(body_html)
    if len(paras) != 20:
        return body_html  # already repaired, or not the chapter we mean
    opening, _, rest = paras[9].partition(".")
    if not rest:
        return body_html
    merged = f"{opening}. {paras[11]}"
    kept = paras[:9] + [merged] + paras[12:]
    return "".join(f"<p>{p}</p>" for p in kept)


# (slug, chapter order) -> repairs, applied in order.
SOURCE_FIXES = {
    ("the-person-and-work-of-the-holy-spirit", 1): [fix_wrong_verse],
    ("the-person-and-work-of-the-holy-spirit", 8): [
        fix_duplicated_block,
        fix_wrong_verse,
    ],
}


def apply_source_fixes(slug: str, order: int, body_html: str) -> str:
    for fix in SOURCE_FIXES.get((slug, order), ()):
        body_html = fix(body_html)
    return body_html
