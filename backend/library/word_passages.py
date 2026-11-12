"""Real passages from the library that use a word — the glossary pages' examples.

/glossary/<term>/ shows a few sentences from the classics where the term
actually occurs, each linked to the paragraph it sits in. Two rules make that
honest, and both live here:

**Only real matches.** A candidate work is found with the full-text index
(stemmed, so "abide" would also find "abiding"), but a passage is shown only
when the WORD ITSELF is in the sentence — a whole-word, case-insensitive match
on the served text. Stemming finds where to look; it never decides what is
shown.

**The link lands on the sentence.** The paragraph index is counted over the
blocks the reader serves (``quote_blocks.served_block_texts`` — the same count
a quote's ``?p=`` uses), so the link opens the chapter at that paragraph.

A few glossary words are also ordinary modern words with another meaning
("art" the noun), so they match only in the archaic phrase (``PHRASES``) —
an example of "art" that is about painting would teach the wrong thing.

English only: the glossary is English, and so are the works it quotes.
"""

from __future__ import annotations

import hashlib
import re

from django.db import connection

#: Glossary words that are also an everyday word with another sense: match the
#: archaic use only. The regex runs on the served text; the phrase feeds the
#: full-text prefilter.
PHRASES: dict[str, tuple[str, str]] = {
    "art": (r"\b(?:thou\s+art|art\s+thou)\b", "thou art"),
    "wilt": (r"\b(?:thou\s+wilt|wilt\s+thou)\b", "thou wilt"),
}

#: A word the endpoint will look up: letters, optionally hyphenated
#: ("mercy-seat"), short. Anything else is not a glossary word.
WORD_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
MAX_WORD = 30

#: Passages returned, and the most candidate works read to find them — each
#: read is a chapter parse, so the bound is the endpoint's cost.
LIMIT = 3
MAX_READS = 12
#: A sentence longer than this is cut to a window around the word.
MAX_CHARS = 260

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"“‘'(\[A-Z])")


def pattern_for(word: str) -> re.Pattern:
    if word in PHRASES:
        return re.compile(PHRASES[word][0], re.IGNORECASE)
    parts = [re.escape(p) for p in word.split("-")]
    return re.compile(r"\b" + r"[-\s]".join(parts) + r"\b", re.IGNORECASE)


def _rank(word: str, key: str) -> str:
    # A stable, word-specific order over candidate works, so "wherefore" and
    # "whence" don't both open on the same book.
    return hashlib.sha256(f"{word}:{key}".encode()).hexdigest()


def sentence_around(text: str, match: re.Match) -> tuple[str, str, str]:
    """(before, match, after) for the sentence holding ``match``, cut to
    ``MAX_CHARS`` around it at word boundaries when the sentence runs long."""
    start = 0
    for m in _SENTENCE.finditer(text):
        if m.end() > match.start():
            break
        start = m.end()
    end_m = _SENTENCE.search(text, match.end())
    end = end_m.start() if end_m else len(text)
    before, hit, after = text[start : match.start()], match.group(0), text[match.end() : end]
    room = max(0, MAX_CHARS - len(hit))
    if len(before) + len(after) > room:
        keep_before = min(len(before), room // 2)
        keep_after = min(len(after), room - keep_before)
        keep_before = min(len(before), room - keep_after)
        if keep_before < len(before):
            cut = before[len(before) - keep_before :]
            before = "… " + cut.split(" ", 1)[1] if " " in cut else "… " + cut
        if keep_after < len(after):
            cut = after[:keep_after]
            after = (cut.rsplit(" ", 1)[0] if " " in cut else cut) + " …"
    return before, hit, after


def _candidates(word: str):
    """Published English chapters and sermons that may use ``word``, as
    (kind, id, work key, author id) — light rows, no bodies."""
    from .fts import search_query
    from .models import Chapter, Sermon

    regex_word = PHRASES.get(word, (None, word.replace("-", " ")))[1]
    chapters = Chapter.objects.filter(book__is_published=True, book__language="en")
    sermons = Sermon.objects.filter(is_published=True, language="en")
    if connection.vendor == "postgresql":
        query = search_query(regex_word, "en")
        chapters = chapters.filter(search_vector=query)
        sermons = sermons.filter(search_vector=query)
    else:
        first = regex_word.split()[-1]
        chapters = chapters.filter(body_text__icontains=first)
        sermons = sermons.filter(body_text__icontains=first)
    rows = [
        ("chapter", pk, f"b{book}", author)
        for pk, book, author in chapters.values_list("pk", "book_id", "book__author_id")[:2000]
    ] + [("sermon", pk, f"s{pk}", author) for pk, author in sermons.values_list("pk", "author_id")[:2000]]
    rows.sort(key=lambda r: _rank(word, f"{r[0]}{r[1]}"))
    return rows


def _passage(kind: str, pk: int, pattern: re.Pattern) -> dict | None:
    """The first served paragraph of this chapter/sermon using the word, as a
    passage — or None when only the stem was there."""
    from .models import Chapter, Sermon
    from .quote_blocks import served_block_texts

    if kind == "chapter":
        obj = Chapter.objects.select_related("book__author").get(pk=pk)
        author = obj.book.author
    else:
        obj = Sermon.objects.select_related("author").get(pk=pk)
        author = obj.author
    for i, block in enumerate(served_block_texts(obj.body_html)):
        m = pattern.search(block)
        if not m:
            continue
        before, hit, after = sentence_around(block, m)
        if kind == "chapter":
            href = f"/books/{obj.book.slug}/{obj.order}/?p={i}"
            work, title = obj.book.title, obj.title
        else:
            href = f"/sermons/{obj.slug}/?p={i}"
            work, title = obj.title, ""
        return {
            "before": before,
            "match": hit,
            "after": after,
            "kind": kind,
            "work": work,
            "title": title,
            "author": {"slug": author.slug, "name": author.name},
            "href": href,
        }
    return None


def passages_for(word: str) -> list[dict]:
    """Up to ``LIMIT`` passages using ``word``, one per work — and from
    different writers while there are enough to go round. At most
    ``MAX_READS`` candidates are read."""
    pattern = pattern_for(word)
    rows = _candidates(word)
    read: dict[tuple[str, int], dict | None] = {}
    out: list[dict] = []
    works: set[str] = set()
    authors: set[int] = set()
    for spread_writers in (True, False):
        for kind, pk, work, author in rows:
            if len(out) >= LIMIT:
                return out
            if work in works or (spread_writers and author in authors):
                continue
            if (kind, pk) not in read:
                if len(read) >= MAX_READS:
                    return out
                read[(kind, pk)] = _passage(kind, pk, pattern)
            if read[(kind, pk)]:
                out.append(read[(kind, pk)])
                works.add(work)
                authors.add(author)
    return out
