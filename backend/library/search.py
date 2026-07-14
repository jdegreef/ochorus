"""Full-text search across published chapters and sermons.

The one place the search query lives. On Postgres (production): websearch-style
parsing, weighted ranking (chapter/book titles > author > body) via ``SearchRank``,
and ``SearchHeadline`` snippets with matches wrapped in ``HL_START`` / ``HL_END``.
On SQLite (dev): a case-insensitive substring fallback producing the same
response shape. Snippets are plain text either way; the client escapes them and
renders the markers as ``<mark>``.
"""

from __future__ import annotations

import re

from django.db import connection
from django.db.models import Q

from .models import Chapter, Sermon

MAX_RESULTS = 30

HL_START = "⟦"
HL_END = "⟧"

# Postgres text-search configs by language (falls back to "simple").
FTS_CONFIGS = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "pt": "portuguese",
}


def fallback_snippet(text: str, query: str, radius: int = 90) -> str:
    """Excerpt centred on the first match, with all matches marker-wrapped.

    Used on SQLite (dev); Postgres builds use SearchHeadline instead.
    """
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[: radius * 2] + ("…" if len(text) > radius * 2 else "")
    start = max(0, idx - radius)
    end = min(len(text), idx + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    excerpt = text[start:end]
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    excerpt = pattern.sub(lambda m: f"{HL_START}{m.group(0)}{HL_END}", excerpt)
    return f"{prefix}{excerpt}{suffix}"


def search_library(q: str, language: str) -> list[dict]:
    """Ranked search hits (chapters + sermons) for ``q`` in ``language``."""
    base = Chapter.objects.filter(
        book__is_published=True, book__language=language
    ).select_related("book", "book__author")
    sermons = Sermon.objects.filter(
        is_published=True, language=language
    ).select_related("author")

    if connection.vendor == "postgresql":
        return _search_postgres(base, sermons, q, language)
    return _search_fallback(base, sermons, q)


def _search_postgres(base, sermons, q, language):
    from django.contrib.postgres.search import (
        SearchHeadline,
        SearchQuery,
        SearchRank,
        SearchVector,
    )

    config = FTS_CONFIGS.get(language, "simple")
    query = SearchQuery(q, config=config, search_type="websearch")

    def headline(field):
        return SearchHeadline(
            field,
            query,
            config=config,
            start_sel=HL_START,
            stop_sel=HL_END,
            max_words=40,
            min_words=20,
        )

    vector = (
        SearchVector("title", weight="A", config=config)
        + SearchVector("book__title", weight="A", config=config)
        + SearchVector("book__author__name", weight="B", config=config)
        + SearchVector("body_text", weight="C", config=config)
    )
    chapters = (
        base.annotate(
            search=vector,
            rank=SearchRank(vector, query),
            headline=headline("body_text"),
        )
        .filter(search=query)
        .order_by("-rank", "book__sort_order", "order")[:MAX_RESULTS]
    )

    sermon_vector = (
        SearchVector("title", weight="A", config=config)
        + SearchVector("author__name", weight="B", config=config)
        + SearchVector("scripture_ref", weight="B", config=config)
        + SearchVector("body_text", weight="C", config=config)
    )
    sermon_hits = (
        sermons.annotate(
            search=sermon_vector,
            rank=SearchRank(sermon_vector, query),
            headline=headline("body_text"),
        )
        .filter(search=query)
        .order_by("-rank", "sort_order")[:MAX_RESULTS]
    )

    merged = [
        (c.rank, _hit(c, snippet=c.headline)) for c in chapters
    ] + [
        (s.rank, _sermon_hit(s, snippet=s.headline)) for s in sermon_hits
    ]
    merged.sort(key=lambda pair: pair[0], reverse=True)
    return [hit for _, hit in merged[:MAX_RESULTS]]


def _search_fallback(base, sermons, q):
    chapters = base.filter(
        Q(body_text__icontains=q)
        | Q(title__icontains=q)
        | Q(book__title__icontains=q)
        | Q(book__subtitle__icontains=q)
        | Q(book__author__name__icontains=q)
    ).order_by("book__sort_order", "book__title", "order")[:MAX_RESULTS]
    # Unranked fallback: reserve a few slots so sermon matches aren't crowded out
    # when many chapters match a common word.
    sermon_hits = list(
        sermons.filter(
            Q(body_text__icontains=q)
            | Q(title__icontains=q)
            | Q(scripture_ref__icontains=q)
            | Q(author__name__icontains=q)
        ).order_by("sort_order", "title")[:6]
    )
    results = [
        _hit(c, snippet=fallback_snippet(c.body_text, q))
        for c in chapters[: MAX_RESULTS - len(sermon_hits)]
    ]
    results += [
        _sermon_hit(s, snippet=fallback_snippet(s.body_text, q))
        for s in sermon_hits
    ]
    return results


def _hit(c, snippet):
    return {
        "type": "chapter",
        "book_slug": c.book.slug,
        "book_title": c.book.title,
        "author_name": c.book.author.name,
        "chapter_order": c.order,
        "chapter_title": c.title,
        "snippet": snippet,
    }


def _sermon_hit(s, snippet):
    return {
        "type": "sermon",
        "sermon_slug": s.slug,
        "sermon_title": s.title,
        "author_name": s.author.name,
        "scripture_ref": s.scripture_ref,
        "snippet": snippet,
    }
