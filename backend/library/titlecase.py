"""Fix Title Case that capitalized the little words.

The PDF import title-cased chapter names by capitalizing every word, so minor
words that English title case keeps lowercase came out wrong: "The Glory Of The
Creature", "Humility In The Life Of Jesus", "Why Are We Saved By Faith?". Those
strings are the most weighted text on a chapter page — the ``<title>``, the
``<h1>``, the breadcrumb and the ``Chapter`` JSON-LD — so a scraped-looking
title reads as a scraped page.

``recase_title`` lowercases ONLY a minor word that sits mid-phrase in a title
that is otherwise Title Case. It is deliberately narrow — it never touches a
proper noun (they are not minor words), a word after a clause boundary
(``: ; . ! ?`` a dash, or a leading section number), the first or last word, or
a verb particle (``off``/``out``/``up``, which title case keeps capitalized as
in "Offering Up"). ``is_title_case`` gates it so sentence-case descriptive
headings — William Law's chapter-long summaries, "Section IV. Of the
Distinction…" — are left alone.

Shared by the backfill migration (``0121``) and the fixture guard test so the
two can never disagree about what a corrected title looks like.
"""

from __future__ import annotations

import re

#: Prepositions, articles and conjunctions English title case keeps lowercase
#: mid-title. NOT off/out/up — those double as verb particles ("Offering Up",
#: "Walking Out") that title case capitalizes.
MINOR = {
    "of", "the", "and", "in", "to", "a", "an", "for", "with", "on", "at", "by",
    "from", "as", "or", "nor", "but", "into", "over", "upon", "unto", "vs",
}

#: Chars that end a clause, so the next word starts one and keeps its capital.
_BOUNDARY = set(":;.!?")
#: Separator tokens after which the next word starts a clause.
_DASHES = {"—", "–", "-", "&", "·"}

#: Titles a human review flagged as wrong for the rule — a label word reads as a
#: minor word to the machine but is not ("Conclusion A Call…" is a heading label
#: plus a title, not "conclusion a call").
EXCLUDE = frozenset({
    "Conclusion A Call to Action and a Closing Prayer",
    # "Appendix A" is a label (the lettered appendix), not the article.
    "Appendix A: Scripture Texts That Moulded George Müller",
})


def is_title_case(t: str) -> bool:
    """Whether ``t`` looks like Title Case a reader would want the little words
    lowercased in — as opposed to a sentence-case descriptive heading."""
    if ". " in t.rstrip("."):  # more than one sentence → a descriptive heading
        return False
    words = [re.sub(r"[^A-Za-z]", "", w) for w in t.split()]
    words = [w for w in words if w]
    if len(words) < 2 or len(words) > 14:
        return False
    content = [w for w in words if w.lower() not in MINOR]
    if not content:
        return False
    return sum(1 for w in content if w[:1].isupper()) / len(content) >= 0.8


def recase_title(title: str) -> str:
    """The title with mid-phrase minor words lowercased. Idempotent, and a
    no-op on anything ``is_title_case`` rejects or ``EXCLUDE`` names."""
    t = title.strip()
    if not t or t in EXCLUDE or not is_title_case(t):
        return title
    toks = t.split(" ")
    out = []
    for i, tok in enumerate(toks):
        prev = toks[i - 1] if i > 0 else ""
        prev_letters = re.sub(r"[^A-Za-z]", "", prev)
        clause_start = (
            i == 0
            or prev[-1:] in _BOUNDARY
            or prev in _DASHES
            or (prev != "" and prev_letters == "")  # a section number like "1.3"
        )
        is_last = i == len(toks) - 1
        letters = re.sub(r"[^A-Za-z]", "", tok)
        if (
            letters
            and letters.lower() in MINOR
            and letters[:1].isupper()
            and not clause_start
            and not is_last
        ):
            out.append(tok.replace(letters, letters.lower(), 1))
        else:
            out.append(tok)
    return " ".join(out)
