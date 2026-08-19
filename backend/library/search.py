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
from django.db.models import Exists, F, OuterRef, Q

# Config lookup shared with the stored-vector write path (library/fts.py) so
# query config always matches what the row was indexed with.
from .fts import config_for
from .models import (
    Author,
    Book,
    Chapter,
    ChapterCitation,
    Plan,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from .scripture import reference_verse_ids

MAX_RESULTS = 30

# Shorter than this is a keystroke, not a query. Two rather than three because a
# 2-character query is a real search in e.g. Chinese; every caller that asks the
# engine for anything applies it, so it lives here rather than at each entry.
MIN_QUERY_LEN = 2

# Navigational (entity) matches lead over body-text matches: a book/author/topic
# whose title *is* the query is almost always what the reader wants.
ENTITY_BOOST = 1.6

# Per-type caps so one kind can't crowd the others out of the merged list.
CAPS = {"author": 5, "book": 8, "topic": 5, "plan": 5, "chapter": 20, "sermon": 6}

# How many matches of one type a "show more" page returns.
PAGE_SIZE = 20

# Counting is bounded, and the number the reader sees says so ("200+"). An exact
# count of every chapter matching "prayer" is a scan of the whole corpus on every
# keystroke, and nobody needs the difference between 340 and 200+ — they need to
# know the list in front of them is a sample rather than the library, which is
# exactly what the capped page could not tell them.
COUNT_CEILING = 200

HL_START = "⟦"
HL_END = "⟧"


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


#: The places a search can be narrowed to. Each names a shelf the reader is
#: already standing in — an author, a topic, or the book open in front of them.
SCOPES = ("author", "topic", "book")


def parse_scope(raw: str) -> tuple[str, str] | None:
    """``"author:andrew-murray"`` → ``("author", "andrew-murray")``.

    Returns None for anything malformed, which searches the whole library. A
    scope naming a place that doesn't EXIST is a different matter and is left to
    the filters: they find nothing, which is the honest answer.
    """
    kind, _, slug = (raw or "").strip().lower().partition(":")
    if kind in SCOPES and slug:
        return kind, slug
    return None


#: How each scope kind names itself, given its row.
_SCOPE_LABEL = {
    "author": lambda row, language: row.name,
    "topic": lambda row, language: row.title_for(language),
    "book": lambda row, language: row.title,
}


def scope_entry(scope: tuple[str, str], language: str) -> dict | None:
    """The scope as the reader sees it — ``{kind, slug, label}`` — or None.

    Resolved here so the page can name the shelf it is searching without a second
    request, and so a scope naming something that doesn't exist *in this
    language* comes back as None rather than as a chip labelling a place the
    reader can't reach. (There is no English fallback: a topic with no title in
    Swahili is not a Swahili shelf.)

    "Exists in this language" is asked of ``_base_querysets`` rather than
    restated, so the chip can never name a shelf the search then finds nothing
    in — the two answers come from the same filter.
    """
    kind, slug = scope
    row = _base_querysets(language)[kind].filter(slug=slug).first()
    label = _SCOPE_LABEL[kind](row, language) if row else None
    return {"kind": kind, "slug": slug, "label": label} if label else None


def _scoped(qs: dict, scope: tuple[str, str]) -> dict:
    """Narrow every type to what lives inside one author / topic / book.

    Only the things that can be *inside* a place take part: works and their
    passages. Authors, topics and plans are ways in to a scope rather than
    contents of one — searching within Andrew Murray and being shown Andrew
    Murray is noise — so they match nothing and their chips simply don't appear.
    Same for the scoped book itself: you are already in it.
    """
    kind, slug = scope
    empty = {k: v.none() for k, v in qs.items()}
    if kind == "author":
        return {
            **empty,
            "book": qs["book"].filter(author__slug=slug),
            "chapter": qs["chapter"].filter(book__author__slug=slug),
            "sermon": qs["sermon"].filter(author__slug=slug),
        }
    if kind == "topic":
        # Topic membership is by slug (see TopicBook) so it holds across
        # languages — the scope means the same shelf whatever you're reading in.
        # is_published on the topic as well as the works: an unpublished shelf
        # narrows to published books, so nothing unreleased is returned — but
        # diffing a scoped result set against an unscoped one would still read
        # off a draft shelf's curation.
        members = {"topic__slug": slug, "topic__is_published": True}
        books = TopicBook.objects.filter(**members).values("book_slug")
        sermons = TopicSermon.objects.filter(**members).values("sermon_slug")
        return {
            **empty,
            "book": qs["book"].filter(slug__in=books),
            "chapter": qs["chapter"].filter(book__slug__in=books),
            "sermon": qs["sermon"].filter(slug__in=sermons),
        }
    if kind == "book":
        return {**empty, "chapter": qs["chapter"].filter(book__slug=slug)}
    # A kind in SCOPES with no branch here would otherwise fall through to
    # whichever narrowing happened to be last — searching nothing is the safe
    # failure, and parse_scope already rejects kinds this doesn't know.
    return empty


def _base_querysets(language: str, scope: tuple[str, str] | None = None) -> dict:
    """What is eligible to match, per type, in one place.

    Extracted because three things need it now — the merged search, the per-type
    counts and the per-type pages — and a count computed from a different filter
    than the results is worse than no count at all. ``scope`` narrows all three
    together for the same reason.
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
    if language != "en":
        # A shelf with no title in this language doesn't exist here (see
        # TopicListView), so it must not surface as a titleless search hit.
        # Exists() rather than a join filter: a topic translated into Spanish
        # but not Swahili must not qualify for Swahili on a sibling row.
        topics = topics.filter(
            Exists(
                TopicTranslation.objects.filter(
                    topic=OuterRef("pk"), language=language
                ).exclude(title="")
            )
        )
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
    out = {
        "author": authors,
        "book": books,
        "topic": topics,
        "plan": plans,
        "chapter": chapters,
        "sermon": sermons,
    }
    return _scoped(out, scope) if scope else out


def search_library(q: str, language: str, scope=None) -> list[dict]:
    """Ranked search hits for ``q`` in ``language``.

    Entities (books, authors, topics, plans) plus passages (chapters, sermons),
    merged and capped at ``MAX_RESULTS``. ``scope`` narrows the search to one
    author / topic / book — see ``_scoped``.
    """
    qs = _base_querysets(language, scope)
    authors, books, topics = qs["author"], qs["book"], qs["topic"]
    plans, chapters, sermons = qs["plan"], qs["chapter"], qs["sermon"]

    ctx = _Ctx(q=q, language=language)
    if connection.vendor == "postgresql":
        base = _search_postgres(ctx, authors, books, topics, plans, chapters, sermons)
    else:
        base = _search_fallback(ctx, authors, books, topics, plans, chapters, sermons)

    # If the query is itself a scripture reference, lead with everything that
    # engages the passage — sermons preached on an overlapping text, then
    # chapters whose body CITES an overlapping reference (ChapterCitation
    # verse-id spans). Matched by verse id, so it works where plain text
    # search can't (abbreviations, chapter-only, a verse inside a range).
    extra = _scripture_sermon_hits(q, sermons, base)
    cite_hits = _scripture_chapter_hits(q, chapters)
    if cite_hits:
        # A chapter found by BOTH citation and plain text keeps its citation
        # hit (ranked by specificity, snippet centred on the reference) and
        # drops the text duplicate from the base list.
        cited = {(h["book_slug"], h["chapter_order"]) for h in cite_hits}
        base = [
            h
            for h in base
            if h["type"] != "chapter"
            or (h["book_slug"], h["chapter_order"]) not in cited
        ]
    extra += cite_hits
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

    config = config_for(ctx.language)
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

    # Chapters and sermons match against their STORED vector (GIN-indexed,
    # populated by library/fts.py with the same fields + weights the old
    # query-time vector used) — an index lookup instead of re-tokenising
    # every body on every keystroke.
    chapter_rows = (
        chapters.filter(search_vector=query)
        .annotate(
            rank=SearchRank(F("search_vector"), query),
            headline=headline("body_text"),
        )
        .order_by("-rank", "book__sort_order", "order")[: CAPS["chapter"]]
    )
    pairs += [(float(c.rank), _chapter_hit(c, snippet=c.headline)) for c in chapter_rows]

    sermon_rows = (
        sermons.filter(search_vector=query)
        .annotate(
            rank=SearchRank(F("search_vector"), query),
            headline=headline("body_text"),
        )
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


# --- Counting and per-type pages ----------------------------------------------
# The merged list above is a *sample*: MAX_RESULTS and the per-type CAPS mean a
# search for "prayer" returns twenty passages out of hundreds, and nothing in the
# response said so — the page rendered "30 results", which reads as the whole
# library. These are how the reader gets the real number, and then the rest of
# one type when they ask for it.
#
# Both go through `_match`, so a count and the results it describes can never
# come from different filters.


def _lite_q(kind: str, q: str) -> Q:
    """The SQLite (dev) match predicate for one type."""
    if kind == "author":
        return Q(name__icontains=q) | Q(bio__icontains=q)
    if kind == "book":
        return (
            Q(title__icontains=q)
            | Q(subtitle__icontains=q)
            | Q(description__icontains=q)
            | Q(author__name__icontains=q)
        )
    if kind == "topic":
        return (
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(translations__title__icontains=q)
            | Q(translations__description__icontains=q)
        )
    if kind == "plan":
        return Q(title__icontains=q) | Q(description__icontains=q)
    if kind == "chapter":
        return (
            Q(body_text__icontains=q)
            | Q(title__icontains=q)
            | Q(book__title__icontains=q)
            | Q(book__subtitle__icontains=q)
            | Q(book__author__name__icontains=q)
        )
    return (
        Q(body_text__icontains=q)
        | Q(title__icontains=q)
        | Q(scripture_ref__icontains=q)
        | Q(author__name__icontains=q)
    )


def _pg_vector(kind: str, config: str):
    """The weighted vector an ENTITY type matches against.

    Chapters and sermons are absent on purpose — they match their stored,
    GIN-indexed ``search_vector`` rather than a vector rebuilt per query.
    """
    from django.contrib.postgres.search import SearchVector

    def sv(field, weight):
        return SearchVector(field, weight=weight, config=config)

    if kind == "author":
        return sv("name", "A") + sv("bio", "C")
    if kind == "book":
        return (
            sv("title", "A")
            + sv("subtitle", "A")
            + sv("author__name", "B")
            + sv("description", "C")
        )
    return sv("title", "A") + sv("description", "C")  # topic, plan


def _match(kind: str, ctx, qs):
    """Rows of ``kind`` matching the query — unordered, un-paged."""
    if connection.vendor != "postgresql":
        matched = qs.filter(_lite_q(kind, ctx.q))
        return matched.distinct() if kind == "topic" else matched

    from django.contrib.postgres.search import SearchQuery

    config = config_for(ctx.language)
    query = SearchQuery(ctx.q, config=config, search_type="websearch")
    if kind in ("chapter", "sermon"):
        return qs.filter(search_vector=query)
    return qs.annotate(search=_pg_vector(kind, config)).filter(search=query)


#: Ordering per type per sort mode. "relevance" isn't here: on Postgres it is the
#: rank annotation, and on SQLite there is no rank, so "natural" stands in.
_ORDER = {
    "author": {"title": ("name",), "newest": ("-created_at",), "natural": ("name",)},
    "book": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
    "topic": {"title": ("title",), "newest": ("-created_at",), "natural": ("title",)},
    "plan": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
    "chapter": {
        "title": ("title", "order"),
        "newest": ("-book__created_at", "book__title", "order"),
        "natural": ("book__sort_order", "book__title", "order"),
    },
    "sermon": {
        "title": ("title",),
        "newest": ("-created_at",),
        "natural": ("sort_order", "title"),
    },
}

SORTS = ("relevance", "title", "newest")


def count_by_type(q: str, language: str, scope=None) -> tuple[dict, dict]:
    """(counts, capped) per type — how many matches actually exist.

    Counting stops at ``COUNT_CEILING`` and ``capped[kind]`` says when it did, so
    the reader is shown "200+" rather than a number we didn't finish computing.
    Slicing before ``.count()`` puts the LIMIT inside the subquery, so the
    database stops scanning once it has enough.
    """
    ctx = _Ctx(q=q, language=language)
    counts: dict[str, int] = {}
    capped: dict[str, bool] = {}
    for kind, qs in _base_querysets(language, scope).items():
        n = _match(kind, ctx, qs).values("pk")[:COUNT_CEILING].count()
        if n:
            counts[kind] = n
            capped[kind] = n >= COUNT_CEILING
    return counts, capped


def _pg_rank_order(kind, ctx, qs):
    from django.contrib.postgres.search import SearchQuery, SearchRank

    config = config_for(ctx.language)
    query = SearchQuery(ctx.q, config=config, search_type="websearch")
    vector = F("search_vector") if kind in ("chapter", "sermon") else _pg_vector(
        kind, config
    )
    return qs.annotate(rank=SearchRank(vector, query)).order_by(
        "-rank", *_ORDER[kind]["natural"]
    )


def page_by_type(
    q: str,
    language: str,
    kind: str,
    *,
    offset: int = 0,
    limit: int = PAGE_SIZE,
    sort: str = "relevance",
    scope=None,
) -> list[dict]:
    """One type's matches, ordered and paged — the "show more" path.

    Sorting lives here rather than in the browser for the reason the whole change
    exists: the client could only ever reorder the rows it had been handed, so
    "newest" meant "newest of the thirty most relevant". Ordering the full match
    set is the only way that control can mean what it says.
    """
    if kind not in CAPS:
        return []
    ctx = _Ctx(q=q, language=language)
    qs = _match(kind, ctx, _base_querysets(language, scope)[kind])

    if sort in ("title", "newest"):
        qs = qs.order_by(*_ORDER[kind][sort])
    elif connection.vendor == "postgresql":
        qs = _pg_rank_order(kind, ctx, qs)
    else:
        qs = qs.order_by(*_ORDER[kind]["natural"])

    return [_hit_for(kind, row, ctx) for row in qs[offset : offset + limit]]


def _hit_for(kind: str, row, ctx) -> dict:
    """Build a hit for a paged row, with the same snippet the merged list uses."""
    if kind == "author":
        return _author_hit(row, ctx)
    if kind == "book":
        return _book_hit(row, ctx)
    if kind == "topic":
        return _topic_hit(row, ctx)
    if kind == "plan":
        return _plan_hit(row, ctx)
    snippet = fallback_snippet(getattr(row, "body_text", ""), ctx.q)
    return _chapter_hit(row, snippet) if kind == "chapter" else _sermon_hit(row, snippet)


# --- Hit builders -------------------------------------------------------------


def _date(dt) -> str:
    """A hit's publish date as an ISO ``YYYY-MM-DD`` string (for the "newest"
    client sort), or "" when absent. Date-only on purpose: enough to order by,
    without leaking exact ingest timestamps."""
    return dt.date().isoformat() if dt else ""


def _author_hit(a, ctx):
    return {
        "type": "author",
        "author_slug": a.slug,
        "author_name": a.name,
        # A face and a cover make a list of titles scannable. Both may be blank,
        # and the client renders text-only when they are — no placeholder, which
        # would only add noise to a row that reads fine without one.
        "photo_url": a.photo_url,
        "snippet": fallback_snippet(a.bio_for(ctx.language), ctx.q),
        "date": _date(a.created_at),
    }


def _book_hit(b, ctx):
    return {
        "type": "book",
        "book_slug": b.slug,
        "book_title": b.title,
        "author_name": b.author.name,
        "cover_url": b.cover_url,
        # The cover's dominant colour, so the reserved box is filled with
        # something of the book's own while the image loads — and stays filled
        # if it never does. Reserving the space is what stops the list reflowing
        # under the reader's cursor.
        "cover_color": b.cover_color,
        "snippet": fallback_snippet(b.description, ctx.q),
        "date": _date(b.created_at),
    }


def _topic_hit(tp, ctx):
    return {
        "type": "topic",
        "topic_slug": tp.slug,
        "topic_title": tp.title_for(ctx.language),
        "snippet": fallback_snippet(tp.description_for(ctx.language), ctx.q),
        "date": _date(tp.created_at),
    }


def _plan_hit(p, ctx):
    return {
        "type": "plan",
        "plan_slug": p.slug,
        "plan_title": p.title,
        "snippet": fallback_snippet(p.description, ctx.q),
        "date": _date(p.created_at),
    }


def _chapter_hit(c, snippet):
    # Chapters have no date of their own; a chapter is as old as its book.
    return {
        "type": "chapter",
        "book_slug": c.book.slug,
        "book_title": c.book.title,
        "author_name": c.book.author.name,
        "chapter_order": c.order,
        "chapter_title": c.title,
        "cover_url": c.book.cover_url,
        "cover_color": c.book.cover_color,
        "snippet": snippet,
        "date": _date(c.book.created_at),
    }


def _sermon_hit(s, snippet):
    return {
        "type": "sermon",
        "sermon_slug": s.slug,
        "sermon_title": s.title,
        "author_name": s.author.name,
        "scripture_ref": s.scripture_ref,
        "snippet": snippet,
        "date": _date(s.created_at),
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

    Two-phase, like ``_scripture_chapter_hits``: the reference test only needs
    ``scripture_ref``, so the scan runs over row values and only the winners are
    fetched as instances. Iterating instances pulled every published sermon's
    ``body_html``, ``body_text`` and tsvector into memory to read one short
    field off each — for every query containing a verse number, i.e. per
    keystroke once the reader types a digit.
    """
    target = reference_verse_ids(q)
    if not target:
        return []
    already = {h["sermon_slug"] for h in base if h["type"] == "sermon"}
    winners = []
    for row in (
        sermons.exclude(scripture_ref="")
        .order_by("sort_order", "title")
        .values("pk", "slug", "scripture_ref")
    ):
        if row["slug"] in already:
            continue
        if reference_verse_ids(row["scripture_ref"]) & target:
            winners.append(row["pk"])
            if len(winners) >= CAPS["sermon"]:
                break
    if not winners:
        return []
    # Fetched in one query, then put back into the order the scan chose — an
    # `pk__in` fetch returns rows in whatever order the database likes.
    by_pk = {
        s.pk: s
        for s in Sermon.objects.filter(pk__in=winners)
        .select_related("author")
        .defer("body_html", "search_vector")
    }
    return [
        _sermon_hit(by_pk[pk], snippet=_lead(by_pk[pk].body_text))
        for pk in winners
        if pk in by_pk
    ]


def _scripture_chapter_hits(q, chapters):
    """Chapters whose body cites a reference overlapping the query's verses.

    Takes the eligible ``chapters`` queryset rather than re-deriving it, so the
    citation lead is published/language-filtered and SCOPED exactly like every
    other kind of hit — searching inside one book must not surface a citation
    from another.

    The verse-id range filter is only a PREFILTER: a multi-reference query
    ("John 3:16 and Romans 8:28") spans two books, and everything cited in
    between falls inside min..max — so rows are re-checked against the exact
    verse-id set before ranking (the same set-intersection contract as
    _scripture_sermon_hits). Bare book names ("Matthew") parse as whole-book
    references and would bury the text results under twenty incidental
    citations, so the citation lead requires a chapter-or-verse query (a
    digit). Row values first, winner chapters fetched after — a whole-book
    prefilter can match hundreds of rows, and dragging each chapter's body
    through the join costs tens of MB (measured 40 MB for "Matthew").
    """
    if not any(ch.isdigit() for ch in q):
        return []
    target = reference_verse_ids(q)
    if not target:
        return []
    rows = ChapterCitation.objects.filter(
        start_verse_id__lte=max(target),
        end_verse_id__gte=min(target),
        chapter__in=chapters.values("pk"),
    ).values("chapter_id", "start_verse_id", "end_verse_id", "count", "ref_text")
    matches = [
        r
        for r in rows
        if not target.isdisjoint(range(r["start_verse_id"], r["end_verse_id"] + 1))
    ]
    # Narrowest citation first (most specific), then most-repeated; one pass
    # keeps each chapter's best row via insertion order.
    best: dict[int, dict] = {}
    for r in sorted(
        matches, key=lambda r: (r["end_verse_id"] - r["start_verse_id"], -r["count"])
    ):
        best.setdefault(r["chapter_id"], r)
    winners = list(best.values())[: CAPS["chapter"]]
    chapters = {
        c.pk: c
        for c in Chapter.objects.filter(pk__in=[w["chapter_id"] for w in winners])
        .select_related("book__author")
        .defer("body_html", "search_vector")
    }
    return [
        _chapter_hit(
            chapters[w["chapter_id"]],
            snippet=fallback_snippet(
                chapters[w["chapter_id"]].body_text or "", w["ref_text"]
            ),
        )
        for w in winners
        if w["chapter_id"] in chapters
    ]


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
