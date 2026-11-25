"""Admin dashboard API — the library's inventory, one list per kind of content.

Before this, a book's admin page could only be reached from a dashboard row or
a language's drill-down, a sermon's from a search, and authors, plans, topics,
articles, quotes and series had no admin page at all. ``GET
/api/admin/catalog/<kind>/`` lists one kind with search, filters, sorting and
pagination, so each gets a browsable admin shelf (``routes/admin/<kind>``).

Read-only, and a reporting view like the stats it sits beside — the same gate
as the book and sermon admin pages it links to (``reporting:view``).

Every kind is one :class:`Kind` in :data:`KINDS`: its queryset, the fields the
search box matches, the filters and sorts it offers, and how a row is drawn.
Adding a content type to the admin is adding an entry there and a column list
in ``frontend/src/lib/adminCatalog.ts``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from django.db.models import Count, IntegerField, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..models import (
    Article,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Plan,
    PlanDay,
    Quote,
    Series,
    SeriesTranslation,
    Sermon,
    Topic,
    TopicArticle,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)

PAGE_SIZE = 50
#: A hard stop for ``page_size`` — a list, not an export.
MAX_PAGE_SIZE = 200
#: How much of a quote's text a row carries; the full text is on its page.
QUOTE_EXCERPT = 240

_PUBLISHED = {
    "published": Q(is_published=True),
    "unpublished": Q(is_published=False),
}


@dataclass(frozen=True)
class Kind:
    """One listable kind of content."""

    #: The rows to filter and count — no aggregate annotations, so the facet
    #: counts' GROUP BY is only the facet.
    queryset: Callable[[], QuerySet]
    #: What a listed page needs on top: joins and per-row counts. Applied to
    #: the one page of rows, and what the sorts may order by.
    decorate: Callable[[QuerySet], QuerySet]
    row: Callable[[Any], dict]
    #: Fields the search box matches (``icontains``, OR-ed).
    search: tuple[str, ...]
    #: sort key → ``order_by`` fields; the first entry is the default.
    sorts: dict[str, tuple[str, ...]]
    #: status key → filter; offered as the status pills, with counts.
    statuses: dict[str, Q] = field(default_factory=dict)
    #: The (possibly annotated) field holding a row's language, when it has one.
    language: str | None = None
    #: Whether the kind carries ``source_type`` (public domain / AI).
    has_source: bool = False


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _author(a: Author) -> dict:
    return {"slug": a.slug, "name": a.name}


def _per_row(model, fk: str, agg) -> Coalesce:
    """``agg`` over the ``model`` rows pointing at the outer row through ``fk``,
    as a correlated subquery (0 when there are none).

    Not ``Count("relation")`` on the outer queryset: two of those join both
    relations at once and count their product — an author with 50 book rows and
    500 sermons is 25,000 rows before ``distinct`` sorts it out."""
    sub = (
        model.objects.filter(**{fk: OuterRef("pk")})
        .order_by()
        .values(fk)
        .annotate(v=agg)
        .values("v")
    )
    return Coalesce(Subquery(sub, output_field=IntegerField()), 0)


# -- the kinds ---------------------------------------------------------------------


def _books(qs: QuerySet) -> QuerySet:
    return qs.select_related("author", "series").annotate(
        num_chapters=_per_row(Chapter, "book", Count("pk")),
        words=_per_row(Chapter, "book", Sum("word_count")),
    )


def _book_row(b: Book) -> dict:
    return {
        "slug": b.slug,
        "language": b.language,
        "title": b.title,
        "author": _author(b.author),
        "series": b.series.title if b.series_id else "",
        "source_type": b.source_type,
        "is_published": b.is_published,
        "chapters": b.num_chapters,
        "words": b.words,
        "has_cover": bool(b.cover_url),
        "has_pdf": bool(b.pdf_url),
        "created_at": _iso(b.created_at),
        "updated_at": _iso(b.updated_at),
    }


def _sermons(qs: QuerySet) -> QuerySet:
    return qs.select_related("author")


def _sermon_row(s: Sermon) -> dict:
    return {
        "slug": s.slug,
        "language": s.language,
        "title": s.title,
        "author": _author(s.author),
        "scripture_ref": s.scripture_ref,
        "source_type": s.source_type,
        "is_published": s.is_published,
        "words": s.word_count,
        "questions": len(s.study_questions or []),
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
    }


def _authors(qs: QuerySet) -> QuerySet:
    return qs.annotate(
        num_books=_per_row(Book, "author", Count("slug", distinct=True)),
        num_sermons=_per_row(Sermon, "author", Count("slug", distinct=True)),
        num_translations=_per_row(AuthorTranslation, "author", Count("pk")),
    )


def _author_row(a: Author) -> dict:
    return {
        "slug": a.slug,
        "title": a.name,
        "years": (
            f"{a.birth_year or '?'}–{a.death_year or '?'}"
            if a.birth_year or a.death_year
            else ""
        ),
        "is_imprint": a.is_imprint,
        "has_bio": bool(a.bio_html),
        "has_summary": bool(a.bio),
        "has_photo": bool(a.photo_url),
        "books": a.num_books,
        "sermons": a.num_sermons,
        "translations": a.num_translations,
        "created_at": _iso(a.created_at),
    }


def _plans(qs: QuerySet) -> QuerySet:
    return qs.annotate(num_days=_per_row(PlanDay, "plan", Count("pk")))


def _plan_row(p: Plan) -> dict:
    return {
        "slug": p.slug,
        "language": p.language,
        "title": p.title,
        "is_published": p.is_published,
        "days": p.num_days,
        "created_at": _iso(p.created_at),
        "updated_at": _iso(p.updated_at),
    }


def _topics(qs: QuerySet) -> QuerySet:
    return qs.annotate(
        num_books=_per_row(TopicBook, "topic", Count("pk")),
        num_sermons=_per_row(TopicSermon, "topic", Count("pk")),
        num_articles=_per_row(TopicArticle, "topic", Count("pk")),
        num_translations=_per_row(TopicTranslation, "topic", Count("pk")),
    )


def _topic_row(t: Topic) -> dict:
    return {
        "slug": t.slug,
        "title": t.title,
        "is_published": t.is_published,
        "books": t.num_books,
        "sermons": t.num_sermons,
        "articles": t.num_articles,
        "translations": t.num_translations,
        "created_at": _iso(t.created_at),
    }


def _articles(qs: QuerySet) -> QuerySet:
    return qs


def _article_row(a: Article) -> dict:
    return {
        "slug": a.slug,
        "language": a.language,
        "title": a.h1,
        "source_type": a.source_type,
        "is_published": a.is_published,
        "words": a.word_count,
        "created_at": _iso(a.created_at),
        "updated_at": _iso(a.updated_at),
    }


def _quotes(qs: QuerySet) -> QuerySet:
    return qs.select_related("author", "chapter__book", "sermon")


def _quote_row(q: Quote) -> dict:
    if q.chapter_id:
        source = {
            "kind": "book",
            "slug": q.chapter.book.slug,
            "title": q.chapter.book.title,
        }
    elif q.sermon_id:
        source = {"kind": "sermon", "slug": q.sermon.slug, "title": q.sermon.title}
    else:
        source = None
    text = (
        q.text
        if len(q.text) <= QUOTE_EXCERPT
        else q.text[: QUOTE_EXCERPT - 1].rstrip() + "…"
    )
    return {
        "slug": q.slug,
        "language": q.lang or "",
        "title": text,
        "author": _author(q.author),
        "source": source,
        "reviewed": q.reviewed,
        "created_at": _iso(q.created_at),
    }


def _series(qs: QuerySet) -> QuerySet:
    return qs.annotate(
        num_books=_per_row(Book, "series", Count("slug", distinct=True)),
        num_translations=_per_row(SeriesTranslation, "series", Count("pk")),
    )


def _series_row(s: Series) -> dict:
    return {
        "slug": s.slug,
        "title": s.title,
        "audience": s.audience,
        "books": s.num_books,
        "planned": s.planned_count,
        "translations": s.num_translations,
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
    }


KINDS: dict[str, Kind] = {
    "books": Kind(
        Book.objects.all,
        _books,
        _book_row,
        search=("title", "slug", "author__name", "series__title"),
        sorts={
            "title": ("title", "language"),
            "newest": ("-created_at", "slug"),
            "updated": ("-updated_at", "slug"),
            "words": ("-words", "slug"),
            "author": ("author__name", "title"),
        },
        statuses=_PUBLISHED,
        language="language",
        has_source=True,
    ),
    "sermons": Kind(
        Sermon.objects.all,
        _sermons,
        _sermon_row,
        search=("title", "slug", "author__name", "scripture_ref"),
        sorts={
            "title": ("title", "language"),
            "newest": ("-created_at", "slug"),
            "updated": ("-updated_at", "slug"),
            "words": ("-word_count", "slug"),
            "author": ("author__name", "title"),
        },
        statuses=_PUBLISHED,
        language="language",
        has_source=True,
    ),
    "authors": Kind(
        Author.objects.all,
        _authors,
        _author_row,
        search=("name", "slug", "tagline"),
        sorts={
            "title": ("name",),
            "works": ("-num_books", "-num_sermons", "name"),
            "newest": ("-created_at", "name"),
        },
        statuses={
            # Imprints are bylines, not people: they never get a bio, so they
            # stay out of the "missing" lists (as on the dashboard's to-do).
            # The LONG biography (``bio_html``, the write-biography deliverable)
            # — not the dashboard's "without a bio", which is the short summary.
            "no_long_bio": Q(bio_html="", is_imprint=False),
            "no_photo": Q(photo_url="", is_imprint=False),
            "imprint": Q(is_imprint=True),
        },
    ),
    "plans": Kind(
        Plan.objects.all,
        _plans,
        _plan_row,
        search=("title", "slug"),
        sorts={
            "title": ("title", "language"),
            "newest": ("-created_at", "slug"),
            "days": ("-num_days", "slug"),
        },
        statuses=_PUBLISHED,
        language="language",
    ),
    "topics": Kind(
        Topic.objects.all,
        _topics,
        _topic_row,
        search=("title", "slug"),
        sorts={
            "title": ("title",),
            "works": ("-num_books", "-num_sermons", "title"),
            "newest": ("-created_at", "slug"),
        },
        statuses=_PUBLISHED,
    ),
    "articles": Kind(
        Article.objects.all,
        _articles,
        _article_row,
        search=("h1", "slug", "meta_title"),
        sorts={
            "title": ("h1", "language"),
            "newest": ("-created_at", "slug"),
            "updated": ("-updated_at", "slug"),
            "words": ("-word_count", "slug"),
        },
        statuses=_PUBLISHED,
        language="language",
        has_source=True,
    ),
    "quotes": Kind(
        lambda: Quote.objects.annotate(
            lang=Coalesce("chapter__book__language", "sermon__language")
        ),
        _quotes,
        _quote_row,
        search=("text", "author__name", "chapter__book__title", "sermon__title"),
        sorts={
            "newest": ("-created_at", "slug"),
            "author": ("author__name", "slug"),
        },
        statuses={"reviewed": Q(reviewed=True), "unreviewed": Q(reviewed=False)},
        language="lang",
    ),
    "series": Kind(
        Series.objects.all,
        _series,
        _series_row,
        search=("title", "slug", "tagline"),
        sorts={
            "title": ("title",),
            "books": ("-num_books", "title"),
            "newest": ("-created_at", "slug"),
        },
    ),
}


@cache
def _derived(kind: str) -> frozenset[str]:
    """The fields a kind's ``decorate`` adds — what ordering by needs it."""
    spec = KINDS[kind]
    plain = spec.queryset()
    return frozenset(spec.decorate(plain).query.annotations) - set(
        plain.query.annotations
    )


def _int(raw, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(raw)))
    except (TypeError, ValueError):
        return default


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminCatalogView(APIView):
    """One kind's inventory: ``?q=&language=&status=&source=&sort=&page=``.

    Answers the page's rows plus the counts its filter controls show — per
    language and per status, each counted with the OTHER filters applied, so a
    pill's number is what clicking it would list.
    """

    def get(self, request, kind: str):
        spec = KINDS.get(kind)
        if spec is None:
            raise Http404(f"no such list: {kind}")
        params = request.query_params

        qs = spec.queryset()
        q = (params.get("q") or "").strip()
        if q:
            match = Q()
            for f in spec.search:
                match |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(match)

        source = (params.get("source") or "").strip() if spec.has_source else ""
        if source:
            qs = qs.filter(source_type=source)

        language = (params.get("language") or "").strip() if spec.language else ""
        status_key = (params.get("status") or "").strip()
        status_q = spec.statuses.get(status_key)

        # Facets: languages counted under the status filter, statuses under the
        # language filter — never under their own.
        languages = []
        if spec.language:
            by_lang = qs.filter(status_q) if status_q is not None else qs
            languages = [
                {"code": r[spec.language], "count": r["n"]}
                for r in by_lang.order_by()
                .values(spec.language)
                .annotate(n=Count("pk"))
                .order_by("-n", spec.language)
                if r[spec.language]
            ]
            if language:
                qs = qs.filter(**{spec.language: language})
        # The total and every status pill's count in one query: each re-runs the
        # whole filter (a quote search is a LIKE over every quote's text).
        counts = qs.aggregate(
            total=Count("pk", filter=status_q) if status_q is not None else Count("pk"),
            **{
                f"status_{key}": Count("pk", filter=cond)
                for key, cond in spec.statuses.items()
            },
        )
        statuses = {key: counts[f"status_{key}"] for key in spec.statuses}
        if status_q is not None:
            qs = qs.filter(status_q)

        sort = (
            params.get("sort")
            if params.get("sort") in spec.sorts
            else next(iter(spec.sorts))
        )
        total = counts["total"]
        page_size = _int(params.get("page_size"), PAGE_SIZE, 1, MAX_PAGE_SIZE)
        pages = max(1, -(-total // page_size))
        page = _int(params.get("page"), 1, 1, pages)
        start = (page - 1) * page_size
        # Pick the page first, then decorate only its rows: the per-row counts
        # are subqueries, and computing them for every row just to keep fifty
        # cost ~2 s on the books list. A sort BY one of them has to compute it
        # for every row to order them, so only that case orders the decorated set.
        order = spec.sorts[sort]
        derived = _derived(kind)
        ordered = (
            spec.decorate(qs) if any(f.lstrip("-") in derived for f in order) else qs
        )
        pks = list(
            # ``pk`` last: LIMIT/OFFSET needs a total order, and plan translations
            # tie on (days, slug) — without it a row can repeat or vanish across pages.
            ordered.order_by(*order, "pk").values_list("pk", flat=True)[
                start : start + page_size
            ]
        )
        by_pk = {r.pk: r for r in spec.decorate(spec.queryset().filter(pk__in=pks))}
        rows = [by_pk[pk] for pk in pks]

        return Response(
            {
                "kind": kind,
                "total": total,
                "page": page,
                "pages": pages,
                "page_size": page_size,
                "sort": sort,
                "sorts": list(spec.sorts),
                "results": [spec.row(r) for r in rows],
                "facets": {
                    "languages": languages,
                    "statuses": statuses,
                    "sources": (
                        [c for c, _ in Book.SourceType.choices]
                        if spec.has_source
                        else []
                    ),
                },
            }
        )
