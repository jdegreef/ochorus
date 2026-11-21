"""Quotations as search results: "god's work done in god's way" finds the line.

The quote pages hold a few hundred reviewed, sourced sentences, and readers
search for them the way they search the web for a half-remembered line: a
fragment of it, or a writer plus a theme ("spurgeon on prayer"). Neither is a
title or a body match — the sentence is inside a chapter, and the chapter
ranks by everything else in it — so quotes are matched here, in Python, over
the whole set at once. Small enough to hold in memory (memoised per content
revision), and English-only, as the quotes themselves are.

A quote matches when each meaningful word of the query is one of its words
(or, from four letters, the start of one: "pray" finds "prayer"). When the
query names a writer ("spurgeon", "d l moody"), the quote must be theirs and
the rest of the query is what it must say. A quote holding the query's words
in a row, as typed, is a PHRASE match: the reader is quoting it, so it ranks
first and the search page leads with it.
"""

from __future__ import annotations

from .people import words

#: How many quotations the mixed list carries; the Quotes tab pages the rest.
QUOTE_CAP = 3

#: Words that say "a quote", not what it says: "spurgeon quotes on prayer".
_INTENT = frozenset({"quote", "quotes", "quotation", "quotations", "saying", "sayings", "said"})

#: Words too common to require. A query of only these finds no quote by its
#: words alone ("the", "of god"), though they still count toward a phrase.
_STOP = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "for", "from", "god", "has", "have", "he", "his", "how", "i", "if", "in", "is", "it", "its", "me", "my", "no", "not", "of", "on", "or", "our", "so", "that", "the", "their", "them", "then", "there", "they", "this", "to", "us", "was", "we", "what", "when", "who", "will", "with", "you", "your", "about"]
)

#: A typed word shorter than this must match a quote's word exactly.
_PREFIX_MIN = 4


def _rows() -> list[dict]:
    """Every reviewed quote, with its words folded once."""
    from .models import QUOTE_SOURCE_UNSERVED, Quote

    out = []
    qs = (
        Quote.objects.filter(reviewed=True)
        .select_related("author", "chapter__book", "sermon")
        .defer(*QUOTE_SOURCE_UNSERVED)
        .order_by("slug")
    )
    for q in qs:
        if q.sermon_id:
            source = {"kind": "sermon", "slug": q.sermon.slug, "title": q.sermon.title,
                      "work": q.sermon.title, "order": None}
            book = ""
        else:
            book = q.chapter.book.slug
            source = {"kind": "chapter", "slug": book, "title": q.chapter.title,
                      "work": q.chapter.book.title, "order": q.chapter.order}
        out.append(
            {
                "slug": q.slug,
                "text": q.text,
                "words": words(q.text),
                "author_id": q.author_id,
                "author_slug": q.author.slug,
                "author_name": q.author.name,
                "book": book,
                "paragraph": q.paragraph,
                "source": source,
            }
        )
    return out


def all_quotes() -> list[dict]:
    from .search import memoized

    return memoized("quotes", _rows)


def _hits_word(typed: str, have: list[str]) -> bool:
    if len(typed) < _PREFIX_MIN:
        return typed in have
    return any(w.startswith(typed) for w in have)


def _in_a_row(want: list[str], have: list[str]) -> bool:
    n = len(want)
    return any(have[i : i + n] == want for i in range(len(have) - n + 1))


def _marked(text: str, needles: list[str]) -> str:
    """``text`` with each word that matched wrapped in the search highlight."""
    import re

    from .people import fold
    from .search import HL_END, HL_START

    out = []
    for token in re.split(r"(\W+)", text):
        folded = fold(token)
        hit = folded and any(
            folded == n or (len(n) >= _PREFIX_MIN and folded.startswith(n)) for n in needles
        )
        out.append(f"{HL_START}{token}{HL_END}" if hit else token)
    return "".join(out)


def quote_hits(q: str, language: str, person=None, scope=None) -> list[dict]:
    """Every quote ``q`` finds, best first, as search hits.

    ``person`` is the writer the query names (search._Ctx.person, or one whose
    name is the whole query): only their quotes, matched by the query's other
    words. ``scope`` narrows to an author or a book; a topic scope finds none
    (quote themes are a separate vocabulary from book shelves).
    """
    if language != "en" or (scope and scope[0] == "topic"):
        return []
    from .people import asked_for

    typed = asked_for(q)
    if person is not None:
        rest = set(person.rest)
        content = [t for t in typed if t in rest]
    else:
        content = typed
    needles = [t for t in content if t not in _STOP and t not in _INTENT]
    if not needles and person is None:
        return []
    phrase = [t for t in content if t not in _INTENT]

    found = []
    for row in all_quotes():
        if person is not None and row["author_id"] != person.pk:
            continue
        if scope and scope[0] == "author" and row["author_slug"] != scope[1]:
            continue
        if scope and scope[0] == "book" and row["book"] != scope[1]:
            continue
        have = row["words"]
        if not all(_hits_word(t, have) for t in needles):
            continue
        in_a_row = len(phrase) >= 3 and _in_a_row(phrase, have)
        exact = sum(t in have for t in needles)
        found.append((not in_a_row, -exact, len(row["text"]), row["slug"], row, in_a_row))
    found.sort(key=lambda f: f[:4])
    return [_hit(row, needles, in_a_row) for *_, row, in_a_row in found]


def _hit(row: dict, needles: list[str], phrase: bool) -> dict:
    hit = {
        "type": "quote",
        "quote_slug": row["slug"],
        "text": row["text"],
        "author_slug": row["author_slug"],
        "author_name": row["author_name"],
        "paragraph": row["paragraph"],
        "source": row["source"],
        "snippet": _marked(row["text"], needles),
        "date": "",
    }
    if phrase:
        hit["phrase"] = True
    return hit
