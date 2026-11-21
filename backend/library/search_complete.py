"""Suggestions as you type: the people, books, topics and plans a few letters
already point at.

Full-text search matches whole words, so "mo" finds nothing and "moo" finds
nothing — the reader has to finish "moody" before anything comes back. Most
searches are someone heading somewhere ("spurgeon", "pilgrim's progress", "the
prayer topic"), and for those the answer is usually clear after two or three
letters. This matches every typed word as the START of a word in a name or
title (initials included: "d l mo" is Dwight L. Moody), in Python, over a
per-language list of a few hundred entities, memoised until content changes.

Navigational only: no passages, no logging (a keystroke is not a search), and
the hits share the shape of /search's so the palette renders both alike.
"""

from __future__ import annotations

from django.db.models import Exists, OuterRef

from .models import Author, Book, Plan, Sermon, Topic
from .people import words
from .search import _author_hit, _book_hit, _Ctx, _plan_hit, _topic_hit, memoized
from .search_aliases import other_names

LIMIT = 8

#: Which kind leads an equal-length tie: a person, a work, a shelf.
_KIND_ORDER = {"author": 0, "book": 1, "topic": 2, "plan": 3}


def _candidates(language: str) -> list[tuple[str, int, tuple[tuple[str, ...], ...], int]]:
    """(kind, pk, spellings, length) for everything a reader can be sent to in
    ``language``. ``spellings`` are folded word tuples: a title, or an author's
    name plus the other names it is searched by."""

    def compute():
        out = []
        published = {"author": OuterRef("pk"), "is_published": True, "language": language}
        authors = Author.objects.filter(is_imprint=False).filter(
            Exists(Book.objects.filter(**published)) | Exists(Sermon.objects.filter(**published))
        )
        for pk, name, slug in authors.values_list("pk", "name", "slug"):
            spellings = [tuple(words(name))] + [tuple(words(o)) for o in other_names(slug)]
            # A person is looked for by surname first: "mo" opens Moody as
            # surely as "dw" does, so the surname counts as an opening word.
            if len(spellings[0]) > 1:
                spellings.append(spellings[0][-1:])
            out.append(("author", pk, tuple(s for s in spellings if s), len(name)))
        for pk, title in Book.objects.filter(is_published=True, language=language).values_list(
            "pk", "title"
        ):
            out.append(("book", pk, (tuple(words(title)),), len(title)))
        for pk, title in Plan.objects.filter(is_published=True, language=language).values_list(
            "pk", "title"
        ):
            out.append(("plan", pk, (tuple(words(title)),), len(title)))
        for topic in Topic.objects.filter(is_published=True).prefetch_related("translations"):
            title = topic.title_for(language)
            if title:
                out.append(("topic", topic.pk, (tuple(words(title)),), len(title)))
        return out

    return memoized("complete-candidates", compute, language)


def _score(typed: list[str], spelling: tuple[str, ...]) -> int:
    """How well ``typed`` opens ``spelling``: 0 when it doesn't.

    Every typed word must open a distinct word of the spelling, in order (an
    initial opens its word: "d" opens "dwight"). 3 when the typed words open
    the spelling's FIRST words in a row ("the way to g" on "The Way to God"),
    2 when they open later words in a row ("way to g"), 1 otherwise.
    """
    positions = []
    start = 0
    for t in typed:
        j = next((j for j in range(start, len(spelling)) if spelling[j].startswith(t)), None)
        if j is None:
            return 0
        positions.append(j)
        start = j + 1
    consecutive = all(b == a + 1 for a, b in zip(positions, positions[1:], strict=False))
    if consecutive and positions[0] == 0:
        return 3
    return 2 if consecutive else 1


def complete(q: str, language: str) -> list[dict]:
    """Up to LIMIT navigational hits whose name or title ``q`` opens."""
    typed = words(q)
    if not typed:
        return []

    def compute():
        scored = []
        for kind, pk, spellings, length in _candidates(language):
            best = max((_score(typed, s) for s in spellings), default=0)
            if best:
                # Shorter first among equals: "Prayer" (the shelf) before "Prayer
                # and Praying Men"; then a person before a work before a shelf.
                scored.append((-best, length, _KIND_ORDER[kind], kind, pk))
        scored.sort()
        top = scored[:LIMIT]
        ctx = _Ctx(q=q, language=language)
        rows = {
            "author": Author.objects.prefetch_related("translations"),
            "book": Book.objects.select_related("author"),
            "topic": Topic.objects.prefetch_related("translations"),
            "plan": Plan.objects.all(),
        }
        build = {"author": _author_hit, "book": _book_hit, "topic": _topic_hit, "plan": _plan_hit}
        hits = []
        for kind in _KIND_ORDER:
            pks = [pk for *_, k, pk in top if k == kind]
            if pks:
                by_pk = {r.pk: r for r in rows[kind].filter(pk__in=pks)}
                hits += [((k, pk), build[kind](by_pk[pk], ctx)) for *_, k, pk in top if k == kind and pk in by_pk]
        order = {(k, pk): i for i, (*_, k, pk) in enumerate(top)}
        hits.sort(key=lambda pair: order[pair[0]])
        return [hit for _, hit in hits]

    return memoized("complete", compute, " ".join(typed), language)
