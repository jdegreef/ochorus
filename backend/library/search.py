"""Full-text search across the library.

The one place the search query lives. Two kinds of hit come back:

* **Entities** — a book, author, topic or plan *itself* (a navigational match):
  "take me to that page". Ranked above body matches so typing a title or an
  author's name leads with the thing you meant.
* **Passages** — a chapter or sermon whose body text matches (a content match),
  with the matched words wrapped in ``HL_START`` / ``HL_END`` markers.

On Postgres (production): websearch-style parsing, weighted ranking via
``SearchRank`` and ``SearchHeadline`` snippets. On SQLite (dev): a
case-insensitive substring fallback producing the same response shape. Snippets
are plain text either way; the client escapes them and renders the markers as
``<mark>``.
"""

from __future__ import annotations

import difflib
import re

from django.db import connection
from django.db.models import Q

from .models import Author, Book, Chapter, Plan, Sermon, Topic
from .scripture import reference_verse_ids

MAX_RESULTS = 30

# Navigational (entity) matches lead over body-text matches: a book/author/topic
# whose title *is* the query is almost always what the reader wants.
ENTITY_BOOST = 1.6

# Per-type caps so one kind can't crowd the others out of the merged list.
CAPS = {"author": 5, "book": 8, "topic": 5, "plan": 5, "chapter": 20, "sermon": 6}

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

    Used on SQLite (dev), and for entity snippets everywhere (a book/author's
    own prose is short enough not to need SearchHeadline). Returns "" for empty
    text, and the head of the text when the query isn't found in it.
    """
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        head = text[: radius * 2]
        return head + ("…" if len(text) > radius * 2 else "")
    start = max(0, idx - radius)
    end = min(len(text), idx + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    excerpt = text[start:end]
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    excerpt = pattern.sub(lambda m: f"{HL_START}{m.group(0)}{HL_END}", excerpt)
    return f"{prefix}{excerpt}{suffix}"


def search_library(q: str, language: str) -> list[dict]:
    """Ranked search hits for ``q`` in ``language``.

    Entities (books, authors, topics, plans) plus passages (chapters, sermons),
    merged and capped at ``MAX_RESULTS``.
    """
    chapters = Chapter.objects.filter(
        book__is_published=True, book__language=language
    ).select_related("book", "book__author")
    sermons = Sermon.objects.filter(
        is_published=True, language=language
    ).select_related("author")
    books = Book.objects.filter(is_published=True, language=language).select_related(
        "author"
    )
    plans = Plan.objects.filter(is_published=True, language=language)
    topics = Topic.objects.filter(is_published=True).prefetch_related("translations")
    # Only authors who actually have something published to read in this language,
    # mirroring the biographies roster (no ghost authors from unpublished drafts).
    authors = (
        Author.objects.filter(
            Q(books__is_published=True, books__language=language)
            | Q(sermons__is_published=True, sermons__language=language)
        )
        .distinct()
        .prefetch_related("translations")
    )

    ctx = _Ctx(q=q, language=language)
    if connection.vendor == "postgresql":
        base = _search_postgres(ctx, authors, books, topics, plans, chapters, sermons)
    else:
        base = _search_fallback(ctx, authors, books, topics, plans, chapters, sermons)

    # If the query is itself a scripture reference, add every sermon that
    # expounds an overlapping passage — matched by verse id, so it works where
    # plain text search can't (abbreviations, chapter-only, a verse inside a
    # range). Scripture matches lead, since the reference is the reader's intent.
    extra = _scripture_sermon_hits(q, sermons, base)
    if extra:
        return (extra + base)[:MAX_RESULTS]
    return base


class _Ctx:
    """Small carrier so the per-type builders stay readable."""

    def __init__(self, q: str, language: str):
        self.q = q
        self.language = language


# --- Postgres -----------------------------------------------------------------


def _search_postgres(ctx, authors, books, topics, plans, chapters, sermons):
    from django.contrib.postgres.search import (
        SearchHeadline,
        SearchQuery,
        SearchRank,
        SearchVector,
    )

    config = FTS_CONFIGS.get(ctx.language, "simple")
    query = SearchQuery(ctx.q, config=config, search_type="websearch")

    def sv(field, weight):
        return SearchVector(field, weight=weight, config=config)

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

    def entity(qs, vector, builder, kind):
        rows = (
            qs.annotate(search=vector, rank=SearchRank(vector, query))
            .filter(search=query)
            .order_by("-rank")[: CAPS[kind]]
        )
        return [(float(r.rank) * ENTITY_BOOST, builder(r, ctx)) for r in rows]

    pairs: list[tuple[float, dict]] = []

    pairs += entity(
        authors, sv("name", "A") + sv("bio", "C"), _author_hit, "author"
    )
    pairs += entity(
        books,
        sv("title", "A") + sv("subtitle", "A") + sv("author__name", "B")
        + sv("description", "C"),
        _book_hit,
        "book",
    )
    pairs += entity(
        topics, sv("title", "A") + sv("description", "C"), _topic_hit, "topic"
    )
    pairs += entity(
        plans, sv("title", "A") + sv("description", "C"), _plan_hit, "plan"
    )

    chapter_vector = (
        sv("title", "A") + sv("book__title", "A") + sv("book__author__name", "B")
        + sv("body_text", "C")
    )
    chapter_rows = (
        chapters.annotate(
            search=chapter_vector,
            rank=SearchRank(chapter_vector, query),
            headline=headline("body_text"),
        )
        .filter(search=query)
        .order_by("-rank", "book__sort_order", "order")[: CAPS["chapter"]]
    )
    pairs += [(float(c.rank), _chapter_hit(c, snippet=c.headline)) for c in chapter_rows]

    sermon_vector = (
        sv("title", "A") + sv("author__name", "B") + sv("scripture_ref", "B")
        + sv("body_text", "C")
    )
    sermon_rows = (
        sermons.annotate(
            search=sermon_vector,
            rank=SearchRank(sermon_vector, query),
            headline=headline("body_text"),
        )
        .filter(search=query)
        .order_by("-rank", "sort_order")[: CAPS["sermon"]]
    )
    pairs += [(float(s.rank), _sermon_hit(s, snippet=s.headline)) for s in sermon_rows]

    pairs.sort(key=lambda pair: pair[0], reverse=True)
    return [hit for _, hit in pairs[:MAX_RESULTS]]


# --- SQLite fallback (dev) ----------------------------------------------------


def _search_fallback(ctx, authors, books, topics, plans, chapters, sermons):
    q = ctx.q
    author_hits = [
        _author_hit(a, ctx)
        for a in authors.filter(
            Q(name__icontains=q) | Q(bio__icontains=q)
        ).order_by("name")[: CAPS["author"]]
    ]
    book_hits = [
        _book_hit(b, ctx)
        for b in books.filter(
            Q(title__icontains=q)
            | Q(subtitle__icontains=q)
            | Q(description__icontains=q)
            | Q(author__name__icontains=q)
        ).order_by("sort_order", "title")[: CAPS["book"]]
    ]
    topic_hits = [
        _topic_hit(tp, ctx)
        for tp in topics.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(translations__title__icontains=q)
            | Q(translations__description__icontains=q)
        )
        .distinct()
        .order_by("title")[: CAPS["topic"]]
    ]
    plan_hits = [
        _plan_hit(p, ctx)
        for p in plans.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).order_by("sort_order", "title")[: CAPS["plan"]]
    ]

    chapter_hits = [
        _chapter_hit(c, snippet=fallback_snippet(c.body_text, q))
        for c in chapters.filter(
            Q(body_text__icontains=q)
            | Q(title__icontains=q)
            | Q(book__title__icontains=q)
            | Q(book__subtitle__icontains=q)
            | Q(book__author__name__icontains=q)
        ).order_by("book__sort_order", "book__title", "order")[: CAPS["chapter"]]
    ]
    sermon_hits = [
        _sermon_hit(s, snippet=fallback_snippet(s.body_text, q))
        for s in sermons.filter(
            Q(body_text__icontains=q)
            | Q(title__icontains=q)
            | Q(scripture_ref__icontains=q)
            | Q(author__name__icontains=q)
        ).order_by("sort_order", "title")[: CAPS["sermon"]]
    ]

    # Entities first (navigational), then passages, capped overall.
    results = (
        author_hits + book_hits + topic_hits + plan_hits + chapter_hits + sermon_hits
    )
    return results[:MAX_RESULTS]


# --- Hit builders -------------------------------------------------------------


def _author_hit(a, ctx):
    return {
        "type": "author",
        "author_slug": a.slug,
        "author_name": a.name,
        "snippet": fallback_snippet(a.bio_for(ctx.language), ctx.q),
    }


def _book_hit(b, ctx):
    return {
        "type": "book",
        "book_slug": b.slug,
        "book_title": b.title,
        "author_name": b.author.name,
        "snippet": fallback_snippet(b.description, ctx.q),
    }


def _topic_hit(tp, ctx):
    return {
        "type": "topic",
        "topic_slug": tp.slug,
        "topic_title": tp.title_for(ctx.language),
        "snippet": fallback_snippet(tp.description_for(ctx.language), ctx.q),
    }


def _plan_hit(p, ctx):
    return {
        "type": "plan",
        "plan_slug": p.slug,
        "plan_title": p.title,
        "snippet": fallback_snippet(p.description, ctx.q),
    }


def _chapter_hit(c, snippet):
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


def _lead(text: str, n: int = 160) -> str:
    """A plain lead excerpt (no highlight markers) for scripture-match snippets,
    whose query is a reference, not words found in the body."""
    text = (text or "").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _scripture_sermon_hits(q, sermons, base):
    """Sermons whose ``scripture_ref`` overlaps the query's referenced verses.

    Returns [] when ``q`` isn't a scripture reference. Deduped against sermons
    already present in ``base`` so a sermon found by text search isn't repeated.
    """
    target = reference_verse_ids(q)
    if not target:
        return []
    already = {h["sermon_slug"] for h in base if h["type"] == "sermon"}
    hits = []
    for s in sermons.exclude(scripture_ref="").order_by("sort_order", "title"):
        if s.slug in already:
            continue
        if reference_verse_ids(s.scripture_ref) & target:
            hits.append(_sermon_hit(s, snippet=_lead(s.body_text)))
            if len(hits) >= CAPS["sermon"]:
                break
    return hits


# --- Did-you-mean -------------------------------------------------------------

_SUGGEST_CUTOFF = 0.72
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)


def suggest(q: str, language: str) -> str | None:
    """Closest library term to a query that found nothing — the "did you mean".

    Fuzzy-matches (difflib, DB-agnostic) against a small vocabulary of author
    names and book/topic/plan titles plus their significant words, so a
    misspelt author ("Spurgen") or title ("humilty") resolves. Returns None
    when nothing is close enough or the best match is the query itself.
    """
    ql = q.strip().lower()
    if len(ql) < 3:
        return None

    # search-key (lowercased) -> display term, deduped. Each source string
    # contributes itself and its individual long words, so a surname buried in
    # a full name is reachable.
    vocab: dict[str, str] = {}

    def add(s: str) -> None:
        if not s:
            return
        vocab.setdefault(s.lower(), s)
        for w in _WORD.findall(s):
            vocab.setdefault(w.lower(), w)

    names = (
        Author.objects.filter(
            Q(books__is_published=True, books__language=language)
            | Q(sermons__is_published=True, sermons__language=language)
        )
        .distinct()
        .values_list("name", flat=True)
    )
    for name in names:
        add(name)
    for title in Book.objects.filter(
        is_published=True, language=language
    ).values_list("title", flat=True):
        add(title)
    for title in Plan.objects.filter(
        is_published=True, language=language
    ).values_list("title", flat=True):
        add(title)
    for title in Topic.objects.filter(is_published=True).values_list(
        "title", flat=True
    ):
        add(title)

    best = difflib.get_close_matches(ql, list(vocab), n=1, cutoff=_SUGGEST_CUTOFF)
    if not best or best[0] == ql:
        return None
    return vocab[best[0]]
