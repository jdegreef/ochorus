"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

import hashlib
import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, F, Prefetch, Q, Sum
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.params import clamp_int
from common.throttling import ScopedCacheThrottle

from . import book_export
from . import languages as languages_module
from .contemporize import MODERN_LANGUAGE
from .export_policy import EXPORT_EDITIONS, is_exportable
from .http_cache import (
    CACHE_CONTROL,
    PublicContentCacheMixin,
    _if_none_match,
    content_etag,
)
from .hubs import Hubs
from .languages import entry as language_entry
from .leader_guides import chapter_extras, guide_editions, guide_for
from .localization import language_from_request
from .models import (
    SERMON_CARD_DEFER,
    Article,
    Author,
    Book,
    BookPerson,
    Chapter,
    ContentRevision,
    Plan,
    PlanDay,
    SearchClickLog,
    SearchDecision,
    SearchQueryLog,
    Series,
    Sermon,
    Topic,
    fold_query,
)
from .search import (
    CAPS,
    MAX_RESULTS,
    MIN_QUERY_LEN,
    PAGE_SIZE,
    SORTS,
    count_by_type,
    page_by_type,
    parse_scope,
    scope_entry,
    search_library,
    suggest,
)
from .search_triage import hit_key, pinned_hit, rules
from .serializers import (
    AUDIENCE_EDITION_SUFFIX,
    BOOK_CARD_ANNOTATIONS,
    ArticleDetailSerializer,
    ArticleListSerializer,
    AuthorDetailSerializer,
    AuthorListSerializer,
    BookDetailSerializer,
    BookListSerializer,
    ChapterBatch,
    ChapterDetailSerializer,
    PlanDetailSerializer,
    PlanListSerializer,
    SermonDetailSerializer,
    SermonListSerializer,
    TopicDetailSerializer,
    TopicListSerializer,
    _book_cover,
    _edition_base_slug,
    _edition_family,
    _is_retold,
    _retold_bases,
    article_lead_book_map,
    article_topic_map,
    book_topic_map,
    lead_book_cards,
    plan_article_index,
    plan_book_index,
    plan_chapter_index,
    sermon_topic_map,
)

logger = logging.getLogger(__name__)

#: See LanguageListView — short enough that an admin go-live shows up promptly.
LANGUAGES_CACHE_SECONDS = 30


def _language(request) -> str:
    return language_from_request(request)


def _language_entry(code: str) -> dict:
    """Display entry for a language code, from the Language registry.

    Was a hardcoded map here, which had drifted: it was missing Arabic (so an
    Arabic row rendered as "ar / ar") while listing five languages — French,
    Shona, Chichewa, Lingala, Chinese — that have never had a word of content.
    The registry is now the single source, and `languages.entry` caches it.
    """
    return language_entry(code)


# Snippet highlight markers. The API returns *plain text* snippets with matches
# wrapped in these; the client HTML-escapes the text and then swaps the markers
# for <mark> tags, so no HTML ever crosses the boundary unescaped.
class AuthorListView(PublicContentCacheMixin, generics.ListAPIView):
    """Authors for the Biographies page: anyone with a bio OR a book to read."""

    serializer_class = AuthorListSerializer

    def get_queryset(self):
        # Count only books available in the requested language, so a localized
        # biographies page reflects what a reader can actually open in that
        # language (matches AuthorDetailSerializer, which lists books per-locale).
        # Authors with no book in this language fall to the "view biography"
        # link in the UI.
        #
        # Include an author who has books here even with no bio yet: they are
        # part of the library, so hiding them from the page that lists the
        # library's writers loses them entirely (the card then shows their works
        # and omits the bio blurb rather than faking one). An author with
        # neither a bio nor a book in this language still has nothing to show.
        #
        # Imprints are excluded: this page — and the schema.org ItemList it
        # emits — describes people, and a house byline is not one.
        # Sermons count too — a sermon-only author is part of the library and
        # shouldn't read as empty on the shelf. The bio clause is per-language:
        # an author with nothing but an English essay would render a blank card
        # on the Swahili page. `list_in_biographies=False` withholds a real
        # person by choice (their books stay on /books); `is_imprint` excludes a
        # non-person byline. The rule lives on the queryset because the hub
        # pages list the same writers.
        return (
            Author.objects.listed_in_biographies(_language(self.request))
            .with_work_counts(_language(self.request))
            .with_quote_count()
            .prefetch_related("translations")
            .order_by("name")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class AuthorEraPresenceView(PublicContentCacheMixin, APIView):
    """``{language: [birth_year, ...]}`` for the writers on each live language's
    Biographies shelf (``listed_in_biographies``, the author list's own rule) —
    distinct years, ``null`` last for the undated.

    For the era pages' hreflang: an era page has writers only where that
    locale's shelf has someone born in the era. The eras are drawn in the
    frontend (`$lib/eras`), so the API hands over the years and leaves the
    bucketing to the one place that defines it.

    One query per live language, so it is cached per content revision and live
    set (the scripture_graph.current_pages idiom): every era page in every
    locale asks during prerender, and the answer only moves with content or a
    language going live.
    """

    def get(self, request):
        live = languages_module.live_codes()
        key = (ContentRevision.current(), tuple(live))
        cached = cache.get("author-era-presence")
        if cached is not None and cached[0] == key:
            return Response(cached[1])
        years = {
            lang: sorted(
                set(Author.objects.listed_in_biographies(lang).values_list("birth_year", flat=True)),
                key=lambda y: (y is None, y or 0),
            )
            for lang in live
        }
        cache.set("author-era-presence", (key, years), timeout=None)
        return Response(years)


class AuthorDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    """A single author with their published books (for the author page)."""

    serializer_class = AuthorDetailSerializer

    def get_object(self):
        # `reviewed_quotes` is ANNOTATED (`with_quote_count`, the same count the
        # A–Z list carries), not counted per object: the serializer
        # asking `obj.quotes.filter(...).count()` added a query to every author
        # page, which `BookCardPayloadTests` budgets and caught.
        return get_object_or_404(
            Author.objects.prefetch_related(
                "translations",
                # appears_in reads these (BookPerson rows for this person);
                # prefetching keeps it out of the serializer as a lazy query and
                # in the page's fixed budget (BookCardPayloadTests).
                "featured_in_books",
            ).with_quote_count(),
            slug=self.kwargs["slug"],
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


def _book_shelf(language: str):
    """Published books in ``language``, shaped for ``BookListSerializer`` cards
    and in shelf order — shared so every shelf gets the same prefetches and
    annotations (``BookCardPayloadTests`` budgets them)."""
    return (
        Book.objects.filter(is_published=True, language=language)
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(**BOOK_CARD_ANNOTATIONS)
        .order_by("sort_order", "title")
    )


class OriginalsView(PublicContentCacheMixin, APIView):
    """The house imprint's own shelf, for the /originals page.

    Ochorus Originals is a byline, not a person (``Author.is_imprint``), so it
    gets a publisher's page rather than an author page: its books in the
    requested language, the series they run in, and how many it has in each
    language so the page can point readers at their own.

    A series groups only when it has a name in this language — the no-fallback
    rule ``Series.title_for`` keeps — so an unnamed one's volumes simply stand
    alone on the shelf rather than sitting under an English heading.
    """

    def get(self, request):
        lang = _language(request)
        imprint = Q(author__is_imprint=True, is_published=True)
        books = list(_book_shelf(lang).filter(author__is_imprint=True))
        series_rows = Series.objects.filter(
            pk__in={b.series_id for b in books if b.series_id}
        ).prefetch_related("translations")
        series = []
        for s in series_rows:
            title = s.title_for(lang)
            if not title:
                continue
            # Stable sort: ties keep the shelf order the queryset gave them.
            members = sorted(
                (b for b in books if b.series_id == s.pk),
                key=lambda b: b.series_position or 0,
            )
            series.append(
                {
                    "slug": s.slug,
                    "title": title,
                    "description": s.description_for(lang),
                    # Who it's for: the page groups its series by it, as /series does.
                    "audience": s.audience,
                    "books": [b.slug for b in members],
                }
            )
        languages = (
            Book.objects.filter(imprint)
            .values("language")
            .annotate(count=Count("pk"))
            .order_by("-count", "language")
        )
        # No topic chips: nothing on this page filters or shows them, and the
        # map is a walk over every topic in the library.
        ctx = {"request": request, "language": lang, "book_topics": {}}
        return Response(
            {
                "books": BookListSerializer(books, many=True, context=ctx).data,
                "series": series,
                "languages": [
                    {"code": row["language"], "count": row["count"]} for row in languages
                ],
            }
        )


class BookListView(PublicContentCacheMixin, generics.ListAPIView):
    """All published books for a language, ordered for the shelf."""

    serializer_class = BookListSerializer

    def get_queryset(self):
        return _book_shelf(_language(self.request))

    def get_serializer_context(self):
        """Attach a ``book_slug -> [topic chip]`` map so each book's topics
        cost the shelf a fixed handful of queries, not one per book."""
        ctx = super().get_serializer_context()
        ctx["book_topics"] = book_topic_map(_language(self.request))
        return ctx


class BookDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = BookDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Book.objects.filter(is_published=True)
            .select_related("author")
            .annotate(**BOOK_CARD_ANNOTATIONS)
            .prefetch_related(
                # TOC fields only. An unrestricted prefetch loaded every
                # chapter's body_text AND body_html — the whole book, twice —
                # per detail request, just to render a chapter list; the
                # prerender crawl requesting every book back-to-back ratcheted
                # the workers into the 2026-08-14 OOM. The difficulty badge
                # samples its text separately (see BookDetailSerializer).
                Prefetch(
                    "chapters",
                    queryset=Chapter.objects.only(
                        "order", "title", "word_count", "book_id"
                    ),
                ),
                "author__translations",
            ),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )


#: Chapter columns the chapter payload never reads. body_text and search_vector
#: are each about the size of the body, so loading them tripled what a chapter
#: request held in memory.
_CHAPTER_UNSERVED = ("body_text", "search_vector", "citations_indexed_at")


class ChapterDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = ChapterDetailSerializer

    def get_object(self):
        book = get_object_or_404(
            Book,
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
        )
        return get_object_or_404(
            Chapter.objects.select_related("book__author").defer(*_CHAPTER_UNSERVED),
            book=book,
            order=self.kwargs["order"],
        )


#: The most chapters one batch request returns. The longest book is 142
#: chapters and 3.7 MB of HTML; a run of 25 keeps a response near 1 MB, so a
#: batch never costs a worker more memory than a few ordinary requests.
CHAPTER_BATCH_MAX = 25


class _ChapterBatchThrottle(ScopedCacheThrottle):
    """A batch serializes up to 25 chapters, so it gets a ceiling. Far above the
    web build's sequential crawl (a few batches a second at most, and a 429 only
    sends it back to per-chapter requests) and far below a scraper."""

    scope = "chapter-batch"


class ChapterBatchView(PublicContentCacheMixin, APIView):
    """A run of one book edition's chapters, each exactly as ChapterDetailView
    serves it: ``?language=xx&from=N&limit=M`` returns chapters N..N+M-1.

    For the web build, which prerenders every chapter page and now fetches them
    a run at a time (frontend ``$lib/chapterBatch.ts``). Same 404 as the single
    endpoint when the edition isn't published, so the build's English fallback
    still keys on it.
    """

    throttle_classes = [_ChapterBatchThrottle]

    def get(self, request, slug):
        book = get_object_or_404(
            Book.objects.select_related("author"),
            slug=slug,
            language=_language(request),
            is_published=True,
        )
        params = request.query_params
        # No book comes near 10,000 chapters; the bound keeps a huge ?from= from
        # reaching Postgres as an out-of-range integer.
        start = clamp_int(params.get("from"), default=1, low=1, high=10_000)
        limit = clamp_int(
            params.get("limit"), default=CHAPTER_BATCH_MAX, low=1, high=CHAPTER_BATCH_MAX
        )
        chapters = list(
            Chapter.objects.filter(book=book, order__gte=start, order__lt=start + limit)
            .defer(*_CHAPTER_UNSERVED)
            .order_by("order")
        )
        for chapter in chapters:
            chapter.book = book  # one book row for the run, not a join per chapter
        serializer = ChapterDetailSerializer(
            chapters,
            many=True,
            context={"request": request, "chapter_batch": ChapterBatch(book, chapters)},
        )
        return Response(serializer.data)


class _BookDownloadThrottle(ScopedCacheThrottle):
    """A download builds a whole book, so it gets its own ceiling — far above a
    reader (nobody downloads 30 books a minute) and well below a scraper."""

    scope = "book-download"


class BookEpubView(APIView):
    """A book as an EPUB file, built per request from the live chapters.

    See ``library/book_export.py``. 404 for anything not exportable
    (``export_policy``), so a guessed URL can't pull an edition we haven't
    vetted.

    Not ``PublicContentCacheMixin``: its tag moves with the content, but the
    renderer (book_export.py) is deliberately not a content root, so a deploy
    that changes the FILE FORMAT would keep answering 304. The tag here is the
    shared content tag plus the release commit, still checked before the book
    is built.
    """

    throttle_classes = [_BookDownloadThrottle]

    def get(self, request, slug):
        etag = _epub_etag(request)
        if _if_none_match(request, etag):
            response = HttpResponseNotModified()
        else:
            book = get_object_or_404(
                Book.objects.select_related("author"),
                slug=slug,
                language=_language(request),
            )
            if not is_exportable(book):
                raise Http404
            data = book_export.render_epub(book_export.build_edition(book))
            response = HttpResponse(data, content_type="application/epub+zip")
            response["Content-Disposition"] = (
                f'attachment; filename="{book_export.export_filename(book, "epub")}"'
            )
        response["ETag"] = etag
        response["Cache-Control"] = CACHE_CONTROL
        return response


def _epub_etag(request) -> str:
    material = f"{content_etag(request)}|{settings.RELEASE_COMMIT}"
    return 'W/"' + hashlib.sha256(material.encode()).hexdigest()[:16] + '"'


class SermonListView(PublicContentCacheMixin, generics.ListAPIView):
    """All published sermons for a language, ordered for the shelf."""

    serializer_class = SermonListSerializer

    def get_queryset(self):
        return (
            Sermon.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .prefetch_related("author__translations")
            .defer(*SERMON_CARD_DEFER)
            .order_by("author__name", "sort_order", "title")
        )

    def get_serializer_context(self):
        # Build the slug→chips map ONCE for the shelf, so each card's topics
        # (the shelf's topic filter) cost a fixed handful of queries, not one per
        # sermon. Mirrors BookListView / ArticleListView.
        ctx = super().get_serializer_context()
        ctx["sermon_topics"] = sermon_topic_map(_language(self.request))
        return ctx


class SermonDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = SermonDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Sermon.objects.select_related("author"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
        )


class ArticleListView(PublicContentCacheMixin, generics.ListAPIView):
    """All published articles for a language, newest curation first."""

    serializer_class = ArticleListSerializer

    def get_queryset(self):
        # The index needs no bodies — defer body_html so the shelf query stays
        # small even as articles grow long (they run 1,500–2,000 words each).
        return (
            Article.objects.filter(
                is_published=True, language=_language(self.request)
            )
            .defer("body_html")
            .order_by("sort_order", "h1")
        )

    def get_serializer_context(self):
        # Build the slug→chips map ONCE for the shelf, so each card's topics
        # (the index's filter tabs) cost a fixed handful of queries, not one per
        # article. Mirrors BookListView. See ArticleListSerializer.get_topics.
        ctx = super().get_serializer_context()
        language = _language(self.request)
        ctx["article_topics"] = article_topic_map(language)
        # Same for each card's lead-book cover: one map for the shelf.
        ctx["article_lead_books"] = article_lead_book_map(language)
        return ctx


class ArticleDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = ArticleDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Article.objects.filter(is_published=True),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )


class LanguageListView(PublicContentCacheMixin, APIView):
    """Languages a reader is offered — LIVE in the registry, with books to read.

    Powers the content-language selector, and (with ``?all=1``) the build, which
    asks which locales to prerender and advertise.

    Both conditions, deliberately. Status alone would offer a language an admin
    launched before its content landed; published-books alone was the old rule,
    and it offered whatever happened to exist — which is how Portuguese came to
    be advertised with nothing behind it. The registry adds intent to presence.
    """

    def get(self, request):
        live = languages_module.live_codes()
        if request.query_params.get("all"):
            # The build's view: every live language in display order, whether or
            # not books have landed yet. It needs the intent, not the inventory —
            # a locale can be live and still be filling up.
            return Response([_language_entry(c) for c in live])
        # Which languages have anything published is a scan of every book, and
        # the answer changes when content ships or an admin takes a locale
        # live — never between two requests a second apart. Memoised briefly so
        # the language switcher, which every page renders, stops paying for it.
        # Short TTL because an admin going live should see it almost at once.
        with_books = cache.get_or_set(
            "languages-with-books",
            lambda: set(
                Book.objects.filter(is_published=True)
                .values_list("language", flat=True)
                .distinct()
            ),
            LANGUAGES_CACHE_SECONDS,
        )
        return Response([_language_entry(c) for c in live if c in with_books])


def _plan_cards(language: str):
    """Published plans in ``language``, shaped for ``PlanListSerializer`` cards
    and in shelf order — shared by /plans and the young-reader hubs."""
    return (
        Plan.objects.filter(is_published=True, language=language)
        .annotate(num_days=Count("days"))
        .prefetch_related("days")
        .order_by("sort_order", "title")
    )


def _plan_card_context(plans, language: str) -> dict:
    """Resolve every plan's chapters and books ONCE for the page.

    Each card shows total words, where the plan starts, and a cover strip,
    and each of those used to fetch its own rows — three queries per plan.
    The same pattern BookListView uses for topic chips.
    """
    return {
        "plan_chapters": plan_chapter_index(plans, language),
        "plan_books": plan_book_index(plans, language),
        "plan_articles": plan_article_index(plans, language),
    }


class PlanListView(PublicContentCacheMixin, generics.ListAPIView):
    """Published reading plans for a language."""

    serializer_class = PlanListSerializer

    def get_queryset(self):
        return _plan_cards(_language(self.request))

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx.update(_plan_card_context(list(self.get_queryset()), _language(self.request)))
        return ctx


class PlanDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = PlanDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Plan.objects.filter(is_published=True)
            .annotate(num_days=Count("days"))
            .prefetch_related("days"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )

    def get_serializer_context(self):
        """One index for all four consumers on this page.

        The detail payload needs the same chapters four times over — total
        words, day one, the cover strip, and the day list — and each resolved
        them separately.
        """
        ctx = super().get_serializer_context()
        plan = self.get_object()
        ctx["plan_chapters"] = plan_chapter_index(
            [plan], plan.language, with_openings=True
        )
        ctx["plan_books"] = plan_book_index([plan], plan.language)
        ctx["plan_articles"] = plan_article_index([plan], plan.language)
        return ctx


def _attach_books(topics, language):
    """Attach ``books_in_language`` (curated-ordered, published member books in
    ``language``) to each topic in ``topics``, using two queries total rather
    than per-topic — then callers can filter out topics that are empty in the
    language. Returns the same list for convenience."""

    wanted = {e.book_slug for t in topics for e in t.entries.all()}
    books = (
        Book.objects.filter(slug__in=wanted, language=language, is_published=True)
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(**BOOK_CARD_ANNOTATIONS)
    )
    by_slug = {b.slug: b for b in books}
    for t in topics:
        t.books_in_language = [
            by_slug[e.book_slug] for e in t.entries.all() if e.book_slug in by_slug
        ]
    return topics


def _attach_sermons(topics, language):
    """Attach ``sermons_in_language`` (curated-ordered, published member sermons
    in ``language``) to each topic, in two queries total — the sermon companion
    to ``_attach_books``."""
    wanted = {e.sermon_slug for t in topics for e in t.sermon_entries.all()}
    sermons = (
        Sermon.objects.filter(slug__in=wanted, language=language, is_published=True)
        .select_related("author")
        .prefetch_related("author__translations")
        .defer(*SERMON_CARD_DEFER)
    )
    by_slug = {s.slug: s for s in sermons}
    for t in topics:
        t.sermons_in_language = [
            by_slug[e.sermon_slug]
            for e in t.sermon_entries.all()
            if e.sermon_slug in by_slug
        ]
    return topics


def _attach_articles(topics, language):
    """Attach ``articles_in_language`` (curated-ordered, published member
    articles in ``language``) to each topic, in two queries total — the article
    companion to ``_attach_books``."""
    wanted = {e.article_slug for t in topics for e in t.article_entries.all()}
    articles = Article.objects.filter(
        slug__in=wanted, language=language, is_published=True
    ).defer("body_html")
    by_slug = {a.slug: a for a in articles}
    for t in topics:
        t.articles_in_language = [
            by_slug[e.article_slug]
            for e in t.article_entries.all()
            if e.article_slug in by_slug
        ]
    return topics


# A series' reading order: volume order where it has one; a collection (no
# positions) falls back to the library's own sort order, as a shelf would.
SERIES_READING_ORDER = (F("series_position").asc(nulls_last=True), "sort_order", "title")


def _series_books(series, language: str) -> list:
    """A series' published books in ``language``, as cards, in reading order."""
    return list(
        Book.objects.filter(series=series, language=language, is_published=True)
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(**BOOK_CARD_ANNOTATIONS)
        .order_by(*SERIES_READING_ORDER)
    )


def _held_languages(series_ids) -> dict[int, set[str]]:
    """Each series' languages with a published book — one query for any number."""
    held: dict[int, set[str]] = {}
    for series_id, lang in (
        Book.objects.filter(series_id__in=series_ids, is_published=True)
        .exclude(language=MODERN_LANGUAGE)
        .values_list("series_id", "language")
        .distinct()
    ):
        held.setdefault(series_id, set()).add(lang)
    return held


def _series_languages(series, held: set[str]) -> list[str]:
    """The languages ``series`` has a page in: a name there and a published
    book there (``held``, from ``_held_languages``). Feeds hreflang, which must
    not advertise a page that 404s."""
    named = {"en"} | {t.language for t in series.translations.all()}
    return sorted(named & held)


def _series_for(series) -> dict:
    """Who a series is for — the index's group — and its age range: "" / null
    where it hasn't been given one. Shared by the list and the page."""
    return {"audience": series.audience, "min_age": series.min_age, "max_age": series.max_age}


def _is_ordered(books) -> bool:
    """Read in order (any volume carries a number) or a collection — one test
    for the series index's card and the series page alike."""
    return any(b.series_position is not None for b in books)


def _chapter_words(books) -> int | None:
    """A series' typical chapter length in words: each book's average over its
    chapters WITH text (a heading-only divider or a not-yet-filled row would
    drag it down), then the mean of those, so one book of many short chapters
    doesn't outweigh the rest. None when no book has text yet — the card then
    draws no minutes. Reads the `text_words` / `text_chapters` annotations."""
    per_book = [b.text_words / b.text_chapters for b in books if b.text_chapters]
    return round(sum(per_book) / len(per_book)) if per_book else None


#: How many covers a series card fans out.
SERIES_CARD_COVERS = 4


def _series_rows(language: str, audience: str | None = None) -> list[dict]:
    """The series index's rows for ``language`` (see ``SeriesListView``) —
    every series, or only those written for ``audience``. Shared with the
    young-reader hubs (``AudienceShelfView``) so a series card there carries
    exactly what the /series index's does."""
    members: dict[int, list] = {}
    books = Book.objects.filter(language=language, is_published=True, series__isnull=False)
    if audience is not None:
        books = books.filter(series__audience=audience)
    for book in (
        books.select_related("author")
        # The tile's cover_face fields (and the author it names), no more.
        .only(
            "slug", "language", "title", "subtitle", "cover_title", "cover_byline",
            "cover_url",
            "cover_color", "series", "series_position",
            "author__slug", "author__name", "author__birth_year",
        )
        # Each book's chapter text, for the card's minutes (`_chapter_words`)
        # — on this same query, not one more.
        .annotate(
            text_words=Sum("chapters__word_count"),
            text_chapters=Count("chapters", filter=Q(chapters__word_count__gt=0)),
        )
        .order_by(*SERIES_READING_ORDER)
    ):
        members.setdefault(book.series_id, []).append(book)
    held = _held_languages(members)
    rows = []
    for series in Series.objects.filter(pk__in=members).prefetch_related("translations"):
        title = series.title_for(language)
        if title:
            books = members[series.pk]
            rows.append(
                {
                    "slug": series.slug,
                    "title": title,
                    "description": series.description_for(language),
                    "book_count": len(books),
                    **_series_for(series),
                    "covers": [_book_cover(b) for b in books[:SERIES_CARD_COVERS]],
                    # Every book, in reading order — the reader's progress
                    # through the series is read against these on the card.
                    "books": [b.slug for b in books],
                    # Their titles, in the same order — the card's "Books in
                    # this series" list names every volume, not just the fan's.
                    "titles": [b.title for b in books],
                    "languages": _series_languages(series, held.get(series.pk, set())),
                    "ordered": _is_ordered(books),
                    "chapter_words": _chapter_words(books),
                }
            )
    return rows


class SeriesListView(PublicContentCacheMixin, APIView):
    """Every series with a page in the requested language — the /series index,
    the Books page's Book Series shelf, the prerender's entries and the sitemap.
    A series needs a name here and at least one published book here; one that
    has neither in a language doesn't exist in it (the no-English-fallback rule,
    as for topics).

    Each row carries its first four covers in reading order, for the card's fan,
    every book's slug (the card's progress) and title (its book list), the
    languages it has a page in — the index's hreflang is their union — and
    its format: whether it reads in order, and its words per chapter.
    Both are read in bulk for the whole list rather than per series.
    """

    def get(self, request):
        return Response(_series_rows(_language(request)))


#: The young-reader hubs (/young-readers/, /teens/): each audience's curated
#: topic shelf, whose books the hub gathers too. Its retold editions are the
#: slug convention's (``AUDIENCE_EDITION_SUFFIX``, beside ``EDITION_SUFFIXES``).
AUDIENCE_TOPICS = {
    Series.Audience.YOUNG_READERS: "for-young-readers",
    Series.Audience.TEENS: "for-teens",
}

#: Each hub's "Start here" pick, in order of preference: the first one the
#: language's hub holds, else its first book. An editor's call, so slugs here
#: rather than a flag on the book; ``tests_audience_shelf`` holds each to a
#: real book, so a rename can't silently fall through.
AUDIENCE_STARTS = {
    Series.Audience.YOUNG_READERS: (
        "pilgrims-progress-children",
        "pilgrims-progress-words-of-one-syllable",
    ),
    Series.Audience.TEENS: ("around-the-wicket-gate", "pilgrims-progress-teens", "all-of-grace"),
}

#: Each hub's daily devotional series, framed as a challenge — and how many
#: days each volume runs. A volume is an introduction (chapter 1), then one
#: chapter a day (chapter n + 1 is day n), so a reader's furthest chapter is
#: the day they've reached; ``tests_audience_shelf`` holds the fixture to it.
AUDIENCE_CHALLENGES = {
    Series.Audience.YOUNG_READERS: ("rooted", 30),
    Series.Audience.TEENS: ("anchored", 30),
}

#: Each hub's spotlight — the one story the hub sells hardest, set out as a
#: banner with its pitch (the book's own ``hook``) and its edition ladder. The
#: first published in the page's language wins; none, no banner. Teens only:
#: the young-readers hub's start pick is already its Pilgrim's Progress, and
#: one book on two banners is a louder page, not a better one.
AUDIENCE_SPOTLIGHTS = {
    Series.Audience.TEENS: ("pilgrims-progress-teens",),
}

#: Hubs where a series holding a single book in the page's language shows that
#: book as a card, not as a one-cover series tile: the teens hub sells its books
#: one by one (each card leads with its hook), and a lone volume in a tile is a
#: book hidden behind a click (Real Questions, while it is Book 1 alone). The
#: book heads More to read rather than taking its place in the topic's order. Not
#: the young readers' hub, whose path cards point at its series by name (Brave
#: for God has one translated volume in several languages).
SOLO_SERIES_AS_BOOKS = {Series.Audience.TEENS}


def _audience_topic(audience: str):
    """The audience's curated topic, with its entries and translations — or None."""
    return (
        Topic.objects.filter(is_published=True, slug=AUDIENCE_TOPICS[audience])
        .prefetch_related("translations", "entries", "article_entries")
        .first()
    )


def _audience_rows(audience: str, topic) -> set[tuple[str, str]]:
    """``(language, slug)`` for every book the audience's hub shows in some
    language — a book in a series of its that is named there, a retold edition,
    or a book of its topic where the topic has a title — in one pass over the
    candidate rows, with the same three tests ``AudienceShelfView`` sorts a
    language's books by. Its languages are the page's hreflang and the
    sitemap's (``_audience_languages``); without the topic, the admin's
    young-reader engagement (``audience_book_slugs``). Plans need no test of their own: a plan
    lands on the hub only when every book it reads already does.

    Keep the three tests in step with the view's (and ``_series_rows``'): a rule
    added there and not here advertises a locale whose hub is empty."""
    suffix = AUDIENCE_EDITION_SUFFIX[audience]
    topic_slugs = {e.book_slug for e in topic.entries.all()} if topic else set()
    rows = list(
        Book.objects.filter(is_published=True)
        .exclude(language=MODERN_LANGUAGE)
        .filter(Q(series__audience=audience) | Q(slug__endswith=suffix) | Q(slug__in=topic_slugs))
        .values_list("language", "slug", "series_id")
        .distinct()
    )
    bases = _retold_bases({slug for _, slug, _ in rows}, suffix)
    series = {
        s.pk: s
        for s in Series.objects.filter(audience=audience).prefetch_related("translations")
    }
    return {
        (language, slug)
        for language, slug, series_id in rows
        if (series_id in series and series[series_id].title_for(language))
        or _is_retold(slug, suffix, bases)
        or (slug in topic_slugs and topic.is_translated_into(language))
    }


def _audience_languages(audience: str, topic) -> list[str]:
    """Every language where the audience's hub has something to show."""
    return sorted({language for language, _ in _audience_rows(audience, topic)})


def audience_book_slugs(audience: str) -> set[str]:
    """Every book written for the audience, in any language: its series' books
    and its retold editions — the hub's rows without its topic shelf, which
    also holds whole classics for every age (All of Grace on the teens'). For
    counting who reads books FOR the audience, which that shelf would swell
    with adults."""
    return {slug for _, slug in _audience_rows(audience, None)}


class AudienceLanguagesView(PublicContentCacheMixin, APIView):
    """``{audience: [languages]}`` for both young-reader hubs — what the home
    page's hub links and the sitemap need, without building either shelf."""

    def get(self, request):
        return Response(
            {audience: _audience_languages(audience, _audience_topic(audience)) for audience in AUDIENCE_TOPICS}
        )


#: How many faces a hub's people strip carries at most — a strip, not a roll.
AUDIENCE_PEOPLE_MAX = 16

#: What parts a story chapter's "Name: The Boy Who Looked" title, in every
#: script the anthologies are translated into (Amharic writes ፦).
_STORY_TITLE_SEP = re.compile(r"\s*[:：፦]\s*")


def split_story_title(title: str) -> tuple[str, str] | None:
    """``(name, hook)`` from a story chapter's "Name: The Boy Who Looked"
    title, or None when it isn't in that shape."""
    parts = _STORY_TITLE_SEP.split(title, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 and all(parts) else None


def _audience_people(series_rows: list[dict], language: str) -> list[dict]:
    """The hub's people strip: one face per story chapter of its series'
    anthologies (``BookPerson.chapter``), in reading order — series, volume,
    chapter. Name and hook come from the chapter's own title in ``language``
    ("Charles Spurgeon: The Boy Who Looked"), so a translated anthology brings
    its names and hooks with it; a chapter missing in the language drops out,
    and a chapter told about two people (Jim and Elisabeth Elliot) is one face,
    the first person's."""
    order = {slug: i for i, slug in enumerate(s for row in series_rows for s in row["books"])}
    members = sorted(
        BookPerson.objects.filter(book_slug__in=order, chapter__isnull=False)
        .select_related("person")
        .only("book_slug", "chapter", "sort_order", "person__slug", "person__name",
              "person__photo_url"),
        key=lambda m: (order[m.book_slug], m.chapter, m.sort_order),
    )
    if not members:
        return []
    # The member books' member chapter numbers — a superset of the stories
    # (dropped below), not every chapter of every hub series book.
    chapters = {
        (slug, n): (title, words)
        for slug, n, title, words in Chapter.objects.filter(
            book__language=language,
            book__is_published=True,
            book__slug__in={m.book_slug for m in members},
            order__in={m.chapter for m in members},
        ).values_list("book__slug", "order", "title", "word_count")
    }
    people: dict[tuple[str, int], dict] = {}
    for m in members:
        key = (m.book_slug, m.chapter)
        if key in people or key not in chapters:
            continue
        title, words = chapters[key]
        name, hook = split_story_title(title) or (m.person.name, title)
        people[key] = {
            "slug": m.person.slug,
            "name": name,
            "hook": hook,
            "photo_url": m.person.photo_url,
            "book": m.book_slug,
            "chapter": m.chapter,
            "words": words or None,
        }
        if len(people) >= AUDIENCE_PEOPLE_MAX:
            break
    return list(people.values())


#: How many "In their own words" quotations a hub carries — one per person.
AUDIENCE_QUOTES_MAX = 3


def _audience_quotes(people: list[dict], language: str) -> list[dict]:
    """Short reviewed quotations by the people in the hub's strip, one each, in
    the strip's order: the faces, then their own words. English only, like
    every quote (the /quotes hub is drawn from the English works), and short
    enough to stand alone (``FEATURED_MAX_CHARS``, the /quotes lead's bar).
    Within a person the pick is the shortest — the line that lands on a young
    reader — ties broken by slug, so it is stable across deploys."""
    if language != "en" or not people:
        return []
    order: dict[str, int] = {}
    for p in people:
        order.setdefault(p["slug"], len(order))
    picks = {}
    for q in _short_quotes().filter(author__slug__in=order).order_by("chars", "slug"):
        picks.setdefault(q.author.slug, q)
    chosen = sorted(picks.values(), key=lambda q: order[q.author.slug])
    return [_quote_card_payload(q) for q in chosen[:AUDIENCE_QUOTES_MAX]]


class BookGuideView(PublicContentCacheMixin, APIView):
    """A young-reader edition's printable leader's guide (/books/<slug>/guide).

    The guide's own file (``library/leader_guides``) holds the leader's intro
    and, per week, a summary, a memory verse and an activity; each week is
    joined here to its chapter's title, study questions, opening verse and
    closing prayer, which the book already carries. 404 when the edition is
    unpublished or has no guide — never an English fallback.
    """

    def get(self, request, slug):
        language = _language(request)
        guide = guide_for(slug, language)
        if guide is None:
            raise Http404("No leader's guide for this edition")
        book = get_object_or_404(_book_shelf(language), slug=slug)
        chapters = {
            order: (title, questions, body)
            for order, title, questions, body in book.chapters.values_list(
                "order", "title", "study_questions", "body_html"
            )
        }
        weeks = []
        for week in guide["weeks"]:
            # A week whose chapter is not in this edition (the fixture gate
            # forbids it, but the DB can drift from the file) is dropped rather
            # than rendered as a blank session with a dead "Read chapter" link.
            if week["chapter"] not in chapters:
                continue
            title, questions, body = chapters[week["chapter"]]
            weeks.append(
                {
                    "chapter": week["chapter"],
                    "title": title,
                    "summary": week["summary"],
                    "memory_verse": week["memory_verse"],
                    "activity": week["activity"],
                    "questions": questions or [],
                    **chapter_extras(body),
                }
            )
        # The page's hreflang: the languages with a guide file AND a published
        # edition, so no alternate points at a 404.
        guided = {lang for s, lang in guide_editions() if s == slug}
        available = sorted(
            Book.objects.filter(slug=slug, is_published=True, language__in=guided)
            .values_list("language", flat=True)
            .distinct()
        )
        ctx = {"request": request, "language": language, "book_topics": {}}
        return Response(
            {
                "book": BookListSerializer(book, context=ctx).data,
                "available_languages": available,
                "intro": guide["intro"],
                "weeks": weeks,
            }
        )


#: A ladder rung's name for each audience's edition suffix.
_EDITION_RUNG = {"young_readers": "children", "teens": "teens"}


def _edition_rung(slug: str) -> str:
    """Which step of the edition ladder a slug is: children, teens or full —
    read off ``AUDIENCE_EDITION_SUFFIX``, the one place the suffixes are spelled."""
    for audience, suffix in AUDIENCE_EDITION_SUFFIX.items():
        if slug.endswith(suffix):
            return _EDITION_RUNG[audience]
    return "full"


def _edition_ladders(slugs, language: str) -> dict[str, list[dict]]:
    """For each young-reader edition in ``slugs``, its family's published
    editions in ``language`` — itself included — as cover tiles with their rung,
    youngest first (children → teens → full): the hub's "Ready for more" step
    and the spotlight's ladder. A family with one edition here has no ladder.
    One query for all of them; the family is the slug convention's
    (``_edition_family``), as on the book page."""
    families = {s: _edition_family(_edition_base_slug(s)) for s in slugs}
    books = {
        b.slug: b
        for b in Book.objects.filter(
            slug__in={m for fam in families.values() for m in fam},
            language=language,
            is_published=True,
        ).select_related("author")
    }
    ladders = {}
    for slug, family in families.items():
        rungs = [
            {"rung": _edition_rung(m), **_book_cover(books[m])}
            for m in reversed(family)
            if m in books
        ]
        if len(rungs) > 1:
            ladders[slug] = rungs
    return ladders


def _audience_challenge(audience: str, series: list[dict]) -> dict | None:
    """The hub's challenge (``AUDIENCE_CHALLENGES``) when its series is on the
    shelf in this language — ``{series, days}`` — else None."""
    if audience not in AUDIENCE_CHALLENGES:
        return None
    slug, days = AUDIENCE_CHALLENGES[audience]
    return {"series": slug, "days": days} if any(r["slug"] == slug for r in series) else None


class AudienceShelfView(PublicContentCacheMixin, APIView):
    """Everything written for one young audience in the requested language —
    the /young-readers/ and /teens/ hubs, which gather what /series, /originals,
    /topics and /plans each hold a part of.

    Four parts, each book appearing once, in this order of claim:

    - ``series`` — the series whose ``audience`` is this one (the /series rows),
      less one holding a single book here on a ``SOLO_SERIES_AS_BOOKS`` hub,
      whose book leads ``more`` (or joins ``editions``) as a card instead;
    - ``editions`` — the retold editions (``-children`` / ``-teens``) that no
      such series already holds;
    - ``more`` — the rest of the audience's curated topic shelf, when that
      topic exists in this language (``topic`` names it for the page's link);
    - ``plans`` — published plans that read ONLY these books, so an adult plan
      that happens to visit one of them never lands on a children's page;
    - ``articles`` — the topic's articles in this language (the teens' Big
      Questions), in its curator's order; companions, so they claim no book.

    ``people`` is the series' anthologies told as faces, each opening its
    chapter (``_audience_people``), and ``quotes`` a few of their own words
    (``_audience_quotes``). ``start`` is the one book a newcomer should
    open first (``AUDIENCE_STARTS``); ``spotlight`` the story the hub sells
    hardest (``AUDIENCE_SPOTLIGHTS``), and ``ladders`` each retold edition's
    family — children, teens, full — for the "Ready for more" step;
    ``challenge`` its daily devotional series as a challenge
    (``AUDIENCE_CHALLENGES``), when that series is here;
    ``printable`` lists the slugs among them with a free PDF / EPUB
    (``export_policy``), for the page's "print it" line; ``leader_guides``, the
    book cards among them with a printable leader's guide
    (``library/leader_guides``); ``languages``, every language the hub has
    something in (its hreflang). Nothing here falls back to English: a language
    with no rows gets empty lists, and the page hides.
    """

    # Its shape grows with the hub (people, quotes, ladders, challenge…), and a
    # code-only deploy moves neither the content digest nor the revision.
    etag_tracks_release = True

    def get(self, request, audience):
        if audience not in AUDIENCE_TOPICS:
            raise Http404("No such audience")
        language = _language(request)
        suffix = AUDIENCE_EDITION_SUFFIX[audience]
        topic = _audience_topic(audience)
        languages = _audience_languages(audience, topic)
        if topic is not None and not topic.is_translated_into(language):
            topic = None

        series = all_series = _series_rows(language, audience)
        solo = []
        if audience in SOLO_SERIES_AS_BOOKS:
            solo = [row["books"][0] for row in series if row["book_count"] == 1]
            series = [row for row in series if row["book_count"] != 1]
        claimed = {slug for row in series for slug in row["books"]}

        topic_slugs = [e.book_slug for e in topic.entries.all()] if topic else []
        books = list(
            _book_shelf(language).filter(
                Q(slug__endswith=suffix) | Q(slug__in=topic_slugs) | Q(slug__in=solo)
            )
        )
        bases = _retold_bases([b.slug for b in books], suffix)
        editions = [
            b for b in books if _is_retold(b.slug, suffix, bases) and b.slug not in claimed
        ]
        claimed |= {b.slug for b in editions}
        # The topic's own order — its curator's — not the shelf's. An original
        # whose slug merely ends in the suffix (Divine Songs) reaches the hub here.
        by_slug = {b.slug: b for b in books}
        # A lone series volume leads — the newest series' first book, which a
        # topic-ordered shelf would otherwise bury at its end.
        more = [
            by_slug[s]
            for s in dict.fromkeys([*solo, *topic_slugs])
            if s in by_slug and s not in claimed
        ]
        claimed |= {b.slug for b in more}
        hub_books = [b.slug for b in editions + more]
        start = next(
            (s for s in AUDIENCE_STARTS[audience] if s in hub_books),
            hub_books[0] if hub_books else None,
        )

        # Which plans read nothing but the hub's books, from their day rows
        # alone — before any plan card is built.
        reads: dict[int, set[str]] = {}
        for plan_id, slug in (
            PlanDay.objects.filter(plan__language=language, plan__is_published=True)
            .exclude(book_slug="")
            .values_list("plan_id", "book_slug")
        ):
            reads.setdefault(plan_id, set()).add(slug)
        plans = list(
            _plan_cards(language).filter(pk__in=[p for p, read in reads.items() if read <= claimed])
        )

        printable = sorted(slug for slug in claimed if (slug, language) in EXPORT_EDITIONS)

        # Never the start pick too: one book on two banners is a louder page,
        # not a better one. A pick ending in the hub's suffix is already in
        # `by_slug`; only one that doesn't costs a query.
        picks = [s for s in AUDIENCE_SPOTLIGHTS.get(audience, ()) if s != start]
        found = {s: by_slug[s] for s in picks if s in by_slug}
        if missing := [s for s in picks if s not in found]:
            found |= {b.slug: b for b in _book_shelf(language).filter(slug__in=missing)}
        spotlight = next((found[s] for s in picks if s in found), None)
        ladders = _edition_ladders(
            [b.slug for b in editions] + ([spotlight.slug] if spotlight else []), language
        )

        # The hub's books that have a printable leader's guide, in shelf order:
        # the series' volumes, then the retold editions, then the rest.
        guided = {s for s, lang in guide_editions() if lang == language}
        guide_slugs = [
            s
            for s in dict.fromkeys(
                [*(s for row in series for s in row["books"]), *(b.slug for b in editions + more)]
            )
            if s in guided
        ]
        # Editions and the topic's books are already in memory; only a series
        # volume the shelf query did not fetch costs a (single) query.
        guide_books = {s: by_slug[s] for s in guide_slugs if s in by_slug}
        unfetched = [s for s in guide_slugs if s not in guide_books]
        if unfetched:
            guide_books |= {b.slug: b for b in _book_shelf(language).filter(slug__in=unfetched)}
        leader_guides = [guide_books[s] for s in guide_slugs if s in guide_books]

        # The topic's articles here, in its curator's order — the teens' Big
        # Questions (doubt, suffering, the resurrection…) that meet a reader at
        # the question and point on to the books. Same rows the topic page shows.
        article_order = [e.article_slug for e in topic.article_entries.all()] if topic else []
        by_article = {
            a.slug: a
            for a in Article.objects.filter(
                slug__in=article_order, language=language, is_published=True
            ).defer("body_html")
        }
        articles = [by_article[s] for s in article_order if s in by_article]
        article_ctx = {
            "request": request,
            "language": language,
            "article_lead_books": lead_book_cards({a.slug: a.related for a in articles}, language),
        }
        people = _audience_people(all_series, language)
        # No topic chips: nothing on the hub filters or shows them.
        ctx = {"request": request, "language": language, "book_topics": {}}
        plan_ctx = {"request": request, **_plan_card_context(plans, language)}
        return Response(
            {
                "series": series,
                "people": people,
                "quotes": _audience_quotes(people, language),
                "editions": BookListSerializer(editions, many=True, context=ctx).data,
                "more": BookListSerializer(more, many=True, context=ctx).data,
                "plans": PlanListSerializer(plans, many=True, context=plan_ctx).data,
                "articles": ArticleListSerializer(articles, many=True, context=article_ctx).data,
                "leader_guides": BookListSerializer(leader_guides, many=True, context=ctx).data,
                "topic": {"slug": topic.slug, "title": topic.title_for(language)} if topic else None,
                "start": start,
                "challenge": _audience_challenge(audience, series),
                "spotlight": (
                    BookListSerializer(spotlight, context=ctx).data if spotlight else None
                ),
                "ladders": ladders,
                "printable": printable,
                "languages": languages,
            }
        )


class SeriesDetailView(PublicContentCacheMixin, APIView):
    """One series page: its name and description in the requested language, and
    its books there in reading order. 404 where the series has no name or no
    book in that language, so the reader gets the not-found page rather than an
    empty or English-named one."""

    def get(self, request, slug):
        language = _language(request)
        series = get_object_or_404(Series.objects.prefetch_related("translations"), slug=slug)
        title = series.title_for(language)
        books = _series_books(series, language) if title else []
        if not books:
            raise Http404("No series in this language")
        ordered = _is_ordered(books)
        return Response(
            {
                "slug": series.slug,
                "title": title,
                "description": series.description_for(language),
                "ordered": ordered,
                **_series_for(series),
                "books": BookListSerializer(
                    books,
                    many=True,
                    # No topic chips and no series line on these cards (the page
                    # IS the series): skip building either map.
                    context={
                        "request": request,
                        "language": language,
                        "book_topics": {},
                        "book_series": {},
                    },
                ).data,
                "available_languages": _series_languages(
                    series, _held_languages([series.pk]).get(series.pk, set())
                ),
            }
        )


class HubListView(PublicContentCacheMixin, APIView):
    """Biography hubs (writers by tradition and by place) that exist in the
    requested language — prose there and enough listed writers. See
    ``library/hubs.py`` for the rule and the data. The list is small (a few
    dozen), so it is the one endpoint for both the index rows and a hub page."""

    def get(self, request):
        return Response(Hubs().for_language(_language(request)))


class TopicListView(PublicContentCacheMixin, generics.ListAPIView):
    """Published topical shelves that have at least one member — book OR sermon —
    in the requested language, so a partially-translated library never shows an
    empty shelf. Localized titles/descriptions, with a few sample tiles each."""

    serializer_class = TopicListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx

    def get_queryset(self):
        language = _language(self.request)
        topics = list(
            Topic.objects.filter(is_published=True)
            .prefetch_related("translations", "entries", "sermon_entries", "article_entries")
            .order_by("sort_order", "title")
        )
        _attach_books(topics, language)
        _attach_sermons(topics, language)
        _attach_articles(topics, language)
        # A shelf needs both something to hold — a book, sermon, or article in
        # this language — and a name a reader of this language can read: an
        # untranslated title would render blank now that the serializer no
        # longer falls back to English.
        return [
            t
            for t in topics
            if (
                t.books_in_language
                or t.sermons_in_language
                or t.articles_in_language
            )
            and t.is_translated_into(language)
        ]


class TopicDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    """A single topical shelf with its member books in the requested language."""

    serializer_class = TopicDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx

    def get_object(self):
        topic = get_object_or_404(
            Topic.objects.filter(is_published=True).prefetch_related(
                "translations", "entries", "sermon_entries", "article_entries"
            ),
            slug=self.kwargs["slug"],
        )
        language = _language(self.request)
        # Consistent with the list: a shelf with no title in this language does
        # not exist here, so the reader gets the not-found page rather than an
        # untitled shelf.
        if not topic.is_translated_into(language):
            raise Http404("No topic in this language")
        _attach_books([topic], language)
        _attach_sermons([topic], language)
        _attach_articles([topic], language)
        return topic


class _SearchThrottle(ScopedCacheThrottle):
    """Bounds search, which is a read that writes: every unscoped query appends
    a ``SearchQueryLog`` row, and a query with no hits additionally runs the
    full-vocabulary difflib scan behind "did you mean". Unbounded, that let
    anyone grow the table and skew the popular-searches report that steers
    translation work — for free, one row per request.

    Its own bucket, and deliberately far above a reader: the page debounces at
    250ms, so even continuous typing settles well under this, and a rate that
    caught search-as-you-type would be worse than the abuse. ``UserRateThrottle``
    for the same reason as ``_SearchClickThrottle`` — ``apiFetch`` sends a token
    when there is one, which ``AnonRateThrottle`` would then exempt.
    """

    scope = "search"


class SearchView(APIView):
    """Ranked full-text search across published chapters and sermons.

    Delegates to ``library.search.search_library`` (see there for the Postgres
    vs SQLite behaviour). Snippets come back with matches marker-wrapped for the
    client to render as ``<mark>``.
    """

    throttle_classes = [_SearchThrottle]

    #: Beyond this the reader is paging, not searching — a guard on the offset so
    #: a crafted URL can't ask the database to skip a million rows.
    MAX_OFFSET = 500

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        language = _language(request)

        # "Search inside this author / topic / book". Narrows every type at once
        # (library.search._scoped), so the counts and the "show more" pages agree
        # with the list — a scope the results honoured but the counts didn't
        # would be worse than no scope at all.
        scope = parse_scope(request.query_params.get("in") or "")

        if len(q) < MIN_QUERY_LEN:
            # Resolved even with nothing to search for: a reader arrives here
            # from "search inside this book" before typing anything, and the
            # page has to be able to name the shelf they are standing in.
            empty = {"query": q, "results": []}
            if scope:
                empty["scope"] = scope_entry(scope, language)
            return Response(empty)

        # "Show more of this type", and the sort that goes with it. A separate
        # branch on purpose: it returns one type rather than the merged list, it
        # is ordered over ALL matches rather than the page the reader was given,
        # and it must not be logged — paging isn't a new search, and counting it
        # as one would quietly inflate the popular-queries report.
        # An admin's triage of this query (search_triage.rules): a synonym runs
        # the search on another word, a pin leads the results. Neither applies
        # inside a scope — they answer "the library", not one author's shelf.
        outcome, target = (
            (None, "") if scope else rules(language).get(fold_query(q), (None, ""))
        )
        searched = target if outcome == SearchDecision.Outcome.SYNONYM else q

        kind = (request.query_params.get("type") or "").strip().lower()
        best = (
            pinned_hit(target, q, language) if outcome == SearchDecision.Outcome.PINNED else None
        )
        if kind:
            page = self._page(searched, language, kind, request, scope)
            # The pin leads its own type's pages too, or it would vanish the
            # moment a reader picks that facet or asks for more.
            if best and best["type"] == kind and page["offset"] == 0:
                page["results"] = [best, *[h for h in page["results"] if hit_key(h) != hit_key(best)]]
            return Response(page)

        results = search_library(searched, language, scope)
        counts, capped = count_by_type(searched, language, scope)
        if best:
            if all(hit_key(h) != hit_key(best) for h in results):
                # Not one of the text matches: count it, so its group's total
                # agrees with the rows under it.
                counts = {**counts, best["type"]: counts.get(best["type"], 0) + 1}
            results = [best, *[h for h in results if hit_key(h) != hit_key(best)]][:MAX_RESULTS]
        payload = {
            "query": q,
            "results": results,
            # What the merged list is a sample OF. Without these the page could
            # only report how many rows it had been handed, which reads as the
            # size of the library rather than the size of the page.
            "totals": counts,
            "totals_capped": capped,
            "page_size": PAGE_SIZE,
        }
        if searched != q:
            # Said out loud, so a reader isn't left wondering why their word
            # isn't in any of the results.
            payload["searched_for"] = searched
        if scope:
            # Resolved (or dropped) here so the page can name the shelf without a
            # second request. None means the place doesn't exist in this
            # language, and the page says so rather than showing an empty list
            # under a confident label.
            payload["scope"] = scope_entry(scope, language)
        # Only pay the fuzzy-match cost when nothing was found — the "did you
        # mean" case. A hit means the spelling was close enough already. Not
        # offered inside a scope: the suggester looks at the whole library, so
        # it would propose a spelling this author never used and send the reader
        # to a second empty page. Inside a scope, empty usually means "not
        # here", and the way out is to widen the search, not to respell it.
        if not results and not scope:
            hint = suggest(q, language)
            if hint:
                payload["suggestion"] = hint
        # Anonymous analytics (admin "what do readers search for / not find").
        # Fail-open: a logging hiccup must never break search itself. Warning
        # level on purpose — an exception-level event would carry the request
        # URL (raw ?q= text) into Sentry and fire once per search during a
        # durable DB issue; server logs still record it.
        #
        # SCOPED searches are not logged. A scoped miss means "this author
        # didn't write about that", not "the library lacks it" — recording it
        # would put phantom gaps into the translation worklist that the
        # zero-result report exists to produce.
        if scope:
            return Response(payload)
        try:
            SearchQueryLog.record(
                q, language, result_count=len(results), suggested="suggestion" in payload
            )
        except Exception:
            logger.warning("search query logging failed", exc_info=True)
        return Response(payload)

    def _page(self, q, language, kind, request, scope=None):
        def _int(name, default, high):
            try:
                return max(0, min(high, int(request.query_params.get(name, default))))
            except (TypeError, ValueError):
                return default

        offset = _int("offset", 0, self.MAX_OFFSET)
        limit = _int("limit", PAGE_SIZE, PAGE_SIZE)
        sort = (request.query_params.get("sort") or "relevance").strip().lower()
        if sort not in SORTS:
            sort = "relevance"
        return {
            "query": q,
            "type": kind,
            "sort": sort,
            "offset": offset,
            "results": page_by_type(
                q, language, kind, offset=offset, limit=limit, sort=sort, scope=scope
            ),
        }


class PopularSearchesView(APIView):
    """The queries readers search most — for the search page's empty state.

    Public and aggregate-only. The privacy guarantee is structural: a query is
    only returned if ``result_count > 0``, i.e. it matched published library
    content — so a reader's private text (which won't match the corpus) never
    surfaces, however many times it's typed. The log is fully anonymous (no
    user column), so counts are of rows, not readers; MIN_COUNT is therefore a
    noise filter — "this is a real recurring query, not a fluke" — not the
    privacy mechanism. Fragments under 3 chars (type-ahead prefixes) are
    dropped, and results are scoped to the reader's language.

    MIN_DISTINCT is the young-site guard. On a site with barely any traffic a
    handful of repeated development searches clear MIN_COUNT easily, and the
    empty state then advertises two items — one of them a half-typed author
    name — under the heading "Popular searches". A one- or two-chip row isn't
    a signal, it's noise wearing a label, so the whole section stays hidden
    until enough DISTINCT queries qualify for it to mean something.
    """

    WINDOW_DAYS = 30
    #: Five minutes. The window is thirty days; nobody can tell the difference,
    #: and it bounds this scan to once per worker per five minutes.
    CACHE_SECONDS = 300
    MIN_COUNT = 5  # a query must recur to read as "popular", not a one-off blip
    MIN_DISTINCT = 4  # ...and there must be a real spread, or show nothing
    LIMIT = 8

    def get(self, request):
        from datetime import timedelta

        from django.db.models.functions import Length, Lower
        from django.utils import timezone

        language = _language(request)
        cached = cache.get(f"popular-searches:{language}")
        if cached is not None:
            return Response({"queries": cached})

        since = timezone.now() - timedelta(days=self.WINDOW_DAYS)
        rows = (
            SearchQueryLog.objects.filter(
                created_at__gte=since, language=language, result_count__gt=0
            )
            .annotate(q=Lower("query"), qlen=Length("query"))
            .filter(qlen__gte=3)
            .values("q")
            .annotate(count=Count("id"))
            .filter(count__gte=self.MIN_COUNT)
            .order_by("-count", "q")[: self.LIMIT]
        )
        queries = [r["q"] for r in rows]
        if len(queries) < self.MIN_DISTINCT:
            queries = []
        # A GROUP BY over thirty days of the search log, recomputed for every
        # reader who opened the search page. It is an aggregate of a month —
        # per-request freshness is worth nothing, and the table it scans is the
        # one search itself is designed to grow.
        cache.set(f"popular-searches:{language}", queries, self.CACHE_SECONDS)
        return Response({"queries": queries})


class _SearchClickThrottle(ScopedCacheThrottle):
    """Its own bucket, so the one write endpoint can't ride the reader's quota
    (and vice versa). Rate in settings.REST_FRAMEWORK.DEFAULT_THROTTLE_RATES.

    ``UserRateThrottle`` rather than ``AnonRateThrottle``: the latter exempts
    authenticated requests by design, and ``apiFetch`` sends the reader's
    Supabase token on every call — so the "anonymous" throttle would have
    covered nobody who had signed up. This keys on the account when there is
    one and the client address otherwise, which is the population that needs
    bounding either way.
    """

    scope = "search-click"


class SearchClickView(APIView):
    """Record that a search result was opened. Anonymous, fire-and-forget.

    The half of search analytics the query log can't see: it knows a query
    returned forty matches, not whether any of them was the one. A query with
    plenty of results and no opens is a *silent* failure — invisible in the
    zero-result report, and often a better content signal than the loud one.

    The one write endpoint on a read-only API, so it is bounded rather than
    trusted: the query must be a string of sane length, the type must be one the
    search actually produces, the position must be inside a page the reader
    could have been shown, and it is throttled per account-or-address. Apart
    from a throttle rejection it answers 204 whatever happens — there is nothing
    to tell the browser, and nothing worth telling a prober.

    **JSON only.** Not a formality: an ``APIView`` is CSRF-exempt and this API
    authenticates by bearer token, so with the form parser enabled any page on
    the internet could make its visitors write rows here with a plain
    cross-origin ``<form>`` — no preflight, CORS irrelevant for a write nobody
    reads back. Requiring ``application/json`` means the browser must preflight,
    and the forged-form route closes.
    """

    parser_classes = [JSONParser]
    throttle_classes = [_SearchClickThrottle]

    #: A click can only come from a page the reader was served, and both the
    #: merged list and a "show more" page are bounded well below this.
    MAX_POSITION = SearchView.MAX_OFFSET + PAGE_SIZE

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        raw_q = data.get("query")
        # A string, not str() of whatever arrived: a posted list would otherwise
        # be stored as "['a', 'b']" — junk in the report rather than a rejection.
        q = raw_q.strip() if isinstance(raw_q, str) else ""
        raw_type = data.get("type")
        result_type = raw_type.strip().lower() if isinstance(raw_type, str) else ""
        try:
            position = int(data.get("position"))
        except (TypeError, ValueError):
            position = 0

        if (
            MIN_QUERY_LEN <= len(q) <= 200
            and result_type in CAPS
            and 1 <= position <= self.MAX_POSITION
        ):
            # Fail-open like the query log: analytics must never be the reason a
            # reader's click doesn't open what they clicked.
            try:
                SearchClickLog.objects.create(
                    # Spacing folded like the query log's, so a click joins its search.
                    query=" ".join(q.split()),
                    language=_language(request)[:10],
                    result_type=result_type,
                    position=position,
                )
            except Exception:
                logger.warning("search click logging failed", exc_info=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Quotes: shared payload helpers -------------------------------------------
# One implementation of "sort into reading order" and "shape a card", used by the
# author page, the theme pages and the author-theme pages, so a citation never
# drifts between them.


def _quote_reading_order(q):
    """Books before sermons, then through each work in its own order.

    Ordering used to be by `slug`, which is a hash of the text — so the
    sequence was arbitrary and a reader scrolling sixty cards could not
    predict what came next. Reading order does three things instead: the
    page walks each work from its first chapter to its last, the citation
    becomes the page's structure rather than a footnote under each card,
    and consecutive quotations share a work, which is what lets the page
    GROUP them. That grouping is what earns the colour: the house rule is
    that a list's hue tracks whatever it is grouped by (STYLE_GUIDE §5), so
    an ungrouped list has no claim to one.

    Books first because they are the substantial works; sermons are one
    group of their own at the foot, since six sermons carrying nine
    quotations between them would otherwise be six groups of one or two.
    """
    if q.sermon_id:
        return (1, q.sermon.title, 0, q.paragraph)
    return (0, q.chapter.book.title, q.chapter.order, q.paragraph)


def _quote_payload(q):
    # The citation is the product. A card without a source is the thing the
    # aggregators already publish, and the reason they cannot be trusted.
    if q.sermon_id:
        source = {
            "kind": "sermon",
            "slug": q.sermon.slug,
            "title": q.sermon.title,
            "work": q.sermon.title,
            "order": None,
            # Sermons carry no cover colour; the page tints their group from
            # the author's era instead, which is what the sermons index does.
            "cover_color": "",
        }
    else:
        source = {
            "kind": "chapter",
            "slug": q.chapter.book.slug,
            "title": q.chapter.title,
            "work": q.chapter.book.title,
            "order": q.chapter.order,
            # The work's own hue, for the group heading. Sent because the
            # page groups BY work — see `_quote_reading_order`.
            "cover_color": q.chapter.book.cover_color,
        }
    return {"slug": q.slug, "text": q.text, "paragraph": q.paragraph, "source": source}


def _quote_card_payload(q):
    # `_quote_payload` plus the author. The author page groups by author, so its
    # cards need no byline; a shelf that MIXES authors (the reader's saved
    # quotes) does, so each card must name its own. Callers select_related
    # "author" alongside the source relations.
    data = _quote_payload(q)
    data["author"] = {"slug": q.author.slug, "name": q.author.name}
    return data


#: A "Quotes on X" theme page needs this many reviewed quotations before it is
#: built, and an "<Author> Quotes on X" page this many. A quote page has no
#: primary text under it, so a thin one is the doorway shape search engines judge
#: a whole domain by (see quote_seed.py). The entry generators and the sitemap
#: apply these, so a page below the bar is never advertised — it simply waits for
#: the theme to be tagged deeper.
QUOTE_TOPIC_MIN = 8
QUOTE_AUTHOR_TOPIC_MIN = 4


class QuotePageView(APIView):
    """An author's reviewed quotations, each with the citation that sources it.

    REVIEWED ONLY, and that is the whole publication gate: extraction is
    mechanical plus judgement, and neither is a person deciding a sentence may
    be printed under an author's name. Unreviewed rows exist in the database and
    reach no reader, exactly as an unapproved translation does.

    404 when an author has none, so a page is never built for an empty shelf.
    """

    def get(self, request, author):
        from .models import Author, Quote

        writer = Author.objects.filter(slug=author).first()
        if writer is None:
            raise Http404("No such author.")
        rows = sorted(
            Quote.objects.filter(author=writer, reviewed=True).select_related(
                "chapter__book", "sermon"
            ),
            key=_quote_reading_order,
        )
        if not rows:
            raise Http404("No published quotes for this author.")
        # The themes this author has enough quotations on to earn a page, so the
        # author page can offer the "on Prayer" chips without a second request.
        topics = self._author_topics(writer)
        return Response(
            {
                "author": {
                    "slug": writer.slug,
                    "name": writer.name,
                    "photo_url": writer.photo_url,
                    # The sermons group has no cover colour of its own, so the
                    # page tints it from the writer's era — the same hue their
                    # row wears on the sermons index.
                    "birth_year": writer.birth_year,
                },
                "topics": topics,
                "quotes": [_quote_payload(q) for q in rows],
            }
        )

    @staticmethod
    def _author_topics(writer):
        from .models import QuoteTopic

        # Same shape as QuoteAuthorsView: annotate a filtered count, then filter
        # on it — no join-level filter on the queryset, so no double-counting.
        rows = (
            QuoteTopic.objects.annotate(
                n=Count("quotes", filter=Q(quotes__author=writer, quotes__reviewed=True))
            )
            .filter(n__gte=QUOTE_AUTHOR_TOPIC_MIN)
            .order_by("sort_order", "title")
            .values("slug", "title", "n")
        )
        return [{"slug": r["slug"], "title": r["title"], "count": r["n"]} for r in rows]


class QuoteTopicDetailView(APIView):
    """A theme's reviewed quotations across every author — "Quotes on Prayer".

    Grouped by author (each group heads a link to that author's own theme page),
    and REVIEWED ONLY, the same gate the author page carries. 404 when the theme
    is unknown or holds nothing reviewed, so no empty page is ever built.
    """

    def get(self, request, topic):
        from collections import defaultdict

        from .models import Quote, QuoteTopic

        t = QuoteTopic.objects.filter(slug=topic).first()
        if t is None:
            raise Http404("No such topic.")
        rows = list(
            Quote.objects.filter(reviewed=True, topics=t).select_related(
                "author", "chapter__book", "sermon"
            )
        )
        if not rows:
            raise Http404("No published quotes on this topic.")
        by_author = defaultdict(list)
        for q in rows:
            by_author[q.author].append(q)
        authors = []
        for writer in sorted(by_author, key=lambda a: a.name.lower()):
            quotes = sorted(by_author[writer], key=_quote_reading_order)
            authors.append(
                {
                    "author": {
                        "slug": writer.slug,
                        "name": writer.name,
                        "birth_year": writer.birth_year,
                    },
                    "count": len(quotes),
                    # Whether this author has enough on the theme to have earned
                    # their own "<Author> Quotes on X" page — the same bar the
                    # prerender list uses, so the heading only links to a page
                    # that was actually built (not the SPA fallback).
                    "has_page": len(quotes) >= QUOTE_AUTHOR_TOPIC_MIN,
                    "quotes": [_quote_payload(q) for q in quotes],
                }
            )
        return Response({"topic": _topic_brief(t), "authors": authors})


class QuoteAuthorTopicView(APIView):
    """One author's reviewed quotations on one theme — "Andrew Murray Quotes on Prayer".

    Reading order within the author, the same shape as the author page. 404 when
    the author or theme is unknown or the pair holds nothing reviewed.
    """

    def get(self, request, author, topic):
        from .models import Author, Quote, QuoteTopic

        writer = Author.objects.filter(slug=author).first()
        if writer is None:
            raise Http404("No such author.")
        t = QuoteTopic.objects.filter(slug=topic).first()
        if t is None:
            raise Http404("No such topic.")
        rows = sorted(
            Quote.objects.filter(author=writer, reviewed=True, topics=t).select_related(
                "chapter__book", "sermon"
            ),
            key=_quote_reading_order,
        )
        if not rows:
            raise Http404("No published quotes for this author on this topic.")
        return Response(
            {
                "author": {
                    "slug": writer.slug,
                    "name": writer.name,
                    "photo_url": writer.photo_url,
                    "birth_year": writer.birth_year,
                },
                "topic": _topic_brief(t),
                "quotes": [_quote_payload(q) for q in rows],
            }
        )


def _topic_brief(t):
    return {
        "slug": t.slug,
        "title": t.title,
        "blurb": t.blurb,
        "scripture_ref": t.scripture_ref,
        "scripture_text": t.scripture_text,
    }


class QuoteTopicsView(APIView):
    """Themes with enough reviewed quotations to earn a page — the build's list.

    Read by the /quotes/topics index page, its prerender entry generator and the
    sitemap, so none can advertise a theme page the review gate and the depth
    threshold have not opened.
    """

    def get(self, request):
        from django.db.models import Count, Max, Q

        from .models import QuoteTopic

        reviewed = Q(quotes__reviewed=True)
        rows = (
            QuoteTopic.objects.annotate(
                n=Count("quotes", filter=reviewed, distinct=True),
                # The sitemap's <lastmod>: when the newest quotation on the page
                # was added. A lower bound (an approval or re-tag has no date of
                # its own), which is the direction a lastmod may safely err.
                updated=Max("quotes__created_at", filter=reviewed),
            )
            .filter(n__gte=QUOTE_TOPIC_MIN)
            .order_by("sort_order", "title")
            .values("slug", "title", "blurb", "n", "updated")
        )
        return Response(
            [
                {"slug": r["slug"], "title": r["title"],
                 "blurb": r["blurb"], "count": r["n"], "updated_at": r["updated"]}
                for r in rows
            ]
        )


class QuoteTopicPagesView(APIView):
    """Every (author, theme) pair deep enough to earn a page — the build's list.

    The author-theme companion to QuoteTopicsView: read by that page's prerender
    entry generator and the sitemap, so both build exactly the pairs the detail
    view will serve.
    """

    def get(self, request):
        from django.db.models import Count, Max, Q

        from .models import Quote, QuoteTopic

        # A pair only earns a page when its THEME also has a page — otherwise the
        # author-theme page's parent "Quotes on X" link would point at a theme
        # that was never built (a topic carried almost entirely by one author:
        # its pair clears 4 but the theme total misses 8). Restricting to themes
        # over QUOTE_TOPIC_MIN keeps the theme → author-theme mesh whole.
        qualifying = set(
            QuoteTopic.objects.annotate(
                n=Count("quotes", filter=Q(quotes__reviewed=True), distinct=True)
            )
            .filter(n__gte=QUOTE_TOPIC_MIN)
            .values_list("slug", flat=True)
        )
        rows = (
            Quote.objects.filter(reviewed=True, topics__isnull=False)
            .values("author__slug", "topics__slug")
            # `updated_at` — the newest quotation's date, as for QuoteTopicsView.
            .annotate(n=Count("id"), updated=Max("created_at"))
            .filter(n__gte=QUOTE_AUTHOR_TOPIC_MIN)
        )
        return Response(
            [
                {"author": r["author__slug"], "topic": r["topics__slug"],
                 "updated_at": r["updated"]}
                for r in rows
                if r["topics__slug"] in qualifying
            ]
        )


class QuoteAuthorsView(APIView):
    """Authors with at least one reviewed quotation — the build's page list.

    Read by the prerender entry generator and the sitemap, so neither can
    advertise a quote page the review gate has not opened.
    """

    def get(self, request):
        from django.db.models import Count, Max, Q

        from .models import Author, Quote

        # Author objects, not bare slugs: the /quotes index page renders a card
        # per author (portrait, name, era hue, how many quotations), and the
        # prerender entry generator and the sitemap take `.slug` from the same
        # rows. One query, annotated — never a count() per author. photo_url is
        # blank for authors with no free image; the card falls back to initials.
        rows = (
            Author.objects.annotate(
                n=Count("quotes", filter=Q(quotes__reviewed=True)),
                # `updated_at` — the newest quotation's date, as for QuoteTopicsView.
                updated=Max("quotes__created_at", filter=Q(quotes__reviewed=True)),
            )
            .filter(n__gt=0)
            .order_by("name")
            .values("id", "slug", "name", "birth_year", "photo_url", "n", "updated")
        )

        # A teaser line and a "works" count per author, so the index card is
        # something to browse rather than a bare directory entry. Both come from
        # ONE pass over the reviewed quotes — a few hundred rows on a page that
        # prerenders, so a grouped query beats a per-author subquery and stays
        # trivially testable. The teaser is the author's SHORTEST quote: the
        # punchiest line, and the one that fits the card's two lines without
        # truncation. Ties break lexicographically so the pick is stable across
        # deploys. The quote text is English (as on the author pages), so it is
        # content the card prints as-is, not a localized string. A quote is
        # sourced from exactly one of chapter/sermon, so the (book, sermon) id
        # pair — one side always null — is itself the work's distinct identity,
        # and a set of those pairs counts the distinct works.
        # The teaser keeps its citation (`teaser_source`), shaped as QuoteSource:
        # a sermon is its own work, with no chapter order.
        teaser: dict[int, tuple[tuple[int, str], dict]] = {}
        works: dict[int, set] = {}
        for (author_id, text, book_id, sermon_id,
             book_title, chapter_order, sermon_title) in Quote.objects.filter(
            reviewed=True
        ).values_list(
            "author_id", "text", "chapter__book_id", "sermon_id",
            "chapter__book__title", "chapter__order", "sermon__title",
        ):
            key = (len(text), text)
            if author_id not in teaser or key < teaser[author_id][0]:
                source = (
                    {"work": sermon_title, "order": None}
                    if sermon_id is not None
                    else {"work": book_title, "order": chapter_order}
                )
                teaser[author_id] = (key, source)
            works.setdefault(author_id, set()).add((book_id, sermon_id))

        def teaser_fields(author_id: int) -> dict:
            if author_id not in teaser:
                return {"teaser": "", "teaser_source": None}
            (_, text), source = teaser[author_id]
            return {"teaser": text, "teaser_source": source}

        return Response(
            [
                {"slug": r["slug"], "name": r["name"],
                 "birth_year": r["birth_year"], "photo_url": r["photo_url"],
                 "count": r["n"], **teaser_fields(r["id"]),
                 "work_count": len(works.get(r["id"], ())),
                 "updated_at": r["updated"]}
                for r in rows
            ]
        )


#: A quote whose work is unpublished links to a page that 404s, and its context
#: would hand out text the work's own pages withhold.
_PUBLISHED_SOURCE = Q(chapter__book__is_published=True) | Q(sermon__is_published=True)

#: The featured pool: up to this many quotes per author, each short enough to
#: stand as the page's lead without truncation.
FEATURED_PER_AUTHOR = 6
FEATURED_MAX_CHARS = 160


def _short_quotes():
    """Reviewed quotations from published works, short enough to stand alone
    (``FEATURED_MAX_CHARS``, annotated as ``chars``), ready for
    ``_quote_card_payload`` — the /quotes lead's pool and the young-reader
    hubs' "In their own words" both draw from it."""
    from django.db.models.functions import Length

    from .models import Quote

    return (
        Quote.objects.filter(reviewed=True)
        .filter(_PUBLISHED_SOURCE)
        .annotate(chars=Length("text"))
        .filter(chars__lte=FEATURED_MAX_CHARS)
        .select_related("author", "chapter__book", "sermon")
        # The card needs titles and slugs, never the bodies they sit in.
        .defer("chapter__body_html", "chapter__body_text", "chapter__search_vector",
               "sermon__body_html", "sermon__body_text", "sermon__search_vector")
    )


class QuoteFeaturedView(APIView):
    """The pool the /quotes index draws its featured quotation from.

    A small, stable list rather than one "quote of the day": the page is
    prerendered, so the day's pick is made in the browser from this list (and
    "Another quote" walks it) without a request per click. Up to
    `FEATURED_PER_AUTHOR` short quotes per writer, interleaved round-robin so
    consecutive days rotate writers. Within a writer the order is the quote
    slug's — an author + content hash, so stable across deploys yet unrelated
    to reading order. Reviewed only, as every quote view.
    """

    def get(self, request):
        rows = _short_quotes().order_by("author__name", "slug")
        by_author: dict[int, list] = {}
        for q in rows:
            picks = by_author.setdefault(q.author_id, [])
            if len(picks) < FEATURED_PER_AUTHOR:
                picks.append(q)
        groups = list(by_author.values())
        pool = [g[i] for i in range(FEATURED_PER_AUTHOR) for g in groups if i < len(g)]
        return Response([_quote_card_payload(q) for q in pool])


def quote_block_text(quote) -> str | None:
    """The plain text of the block a quote's `paragraph` points at, AS SERVED
    (see `library.quote_blocks`). None if the index no longer lands — a work
    edited out from under its quote."""
    from .quote_blocks import served_block_texts

    body = quote.sermon.body_html if quote.sermon_id else quote.chapter.body_html
    blocks = served_block_texts(body)
    return blocks[quote.paragraph] if 0 <= quote.paragraph < len(blocks) else None


class _QuoteContextThrottle(ScopedCacheThrottle):
    """Each context call parses a whole chapter (scripture annotation, then
    lxml), so it gets its own bucket — generous for a reader opening cards,
    a ceiling for a script walking every slug."""

    scope = "quote-context"


class QuoteContextView(APIView):
    """A quotation's whole source paragraph — "read it in context".

    Plain text, not HTML: the card highlights the sentence inside it and links
    on to the reader for the real page, so nothing here needs markup (and the
    page needs no `{@html}`). Reviewed quotes from published works only; 404
    for anything else, or a paragraph index that no longer resolves.

    The parse is the cost, so the text is cached per quote for an hour: a body
    repair reaches it within that, and a popular card costs one parse.
    """

    throttle_classes = [_QuoteContextThrottle]

    def get(self, request, quote):
        from .models import Quote

        key = f"quote-context:{quote}"
        text = cache.get(key)
        if text is None:
            q = (
                Quote.objects.filter(slug=quote, reviewed=True)
                .filter(_PUBLISHED_SOURCE)
                .select_related("chapter", "sermon")
                .first()
            )
            text = quote_block_text(q) if q else None
            if text is None:
                raise Http404("No such quotation.")
            cache.set(key, text, 60 * 60)
        return Response({"slug": quote, "paragraph_text": text})


class _QuoteResolveThrottle(ScopedCacheThrottle):
    """Bounds the one unauthenticated POST on this module. The batch is already
    capped at 200 slugs, so a single call is a bounded read — but nothing stops a
    script from firing it in a loop, each call an ``slug__in`` query with four
    joins. Its own bucket so it can't ride (or starve) the search quotas, and far
    above a reader: the shelf resolves once per page load. ``UserRateThrottle``
    for the same reason as the search throttles — ``apiFetch`` sends a token when
    there is one, which ``AnonRateThrottle`` would exempt.
    """

    scope = "quote-resolve"


class QuoteResolveView(APIView):
    """Resolve a batch of quote slugs to their cards — the reader's saved-quotes
    shelf.

    A quote is favorited by its own slug, but there is no per-quote page to hang
    a title on and the shelf can hold quotes from any author, so it POSTs the
    slugs it has stored and gets back exactly those cards, each with its author
    and citation.

    POST, not GET: the slug list is unbounded and belongs in the body. Reviewed
    only, the same publication gate every other quote view carries. Unknown or
    now-unreviewed slugs are silently dropped (never a 404) — a saved favorite
    whose quote was pulled shouldn't error the whole shelf; the reader simply
    sees it fall away.
    """

    throttle_classes = [_QuoteResolveThrottle]

    def post(self, request):
        from .models import Quote

        slugs = request.data.get("slugs")
        if not isinstance(slugs, list):
            return Response({"detail": "Expected a list of slugs."}, status=400)
        # Cap the batch so a malformed client can't ask for the whole table in
        # one request; a reader's saved shelf is far under this.
        wanted = [s for s in slugs if isinstance(s, str)][:200]
        rows = Quote.objects.filter(slug__in=wanted, reviewed=True).select_related(
            "author", "chapter__book", "sermon"
        )
        by_slug = {q.slug: _quote_card_payload(q) for q in rows}
        # Preserve the caller's order — favorites arrive most-recent-first, and
        # the shelf renders them in that order.
        return Response([by_slug[s] for s in wanted if s in by_slug])


class ScripturePagesView(APIView):
    """Every scripture page that has earned a URL — the build's page list.

    Read at build time by the reader's prerender entry generator and its sitemap
    section, so both get the list from the same place the detail view enforces.
    Not a reader-facing endpoint.
    """

    def get(self, request):
        from .scripture_graph import current_pages

        return Response(current_pages())


class ScriptureGraphView(APIView):
    """The passages in the library that cite a verse, or a Bible chapter.

    The reverse of the popover below: that one answers "what does this
    reference say", this one answers "who in the library preached it". Search
    has been able to do this since citations were indexed; this gives it a URL.

    404 for a reference no page exists for — an unreal one (Romans 99), one the
    bundled ASV has no text for, or one under the citation floor. The floor
    lives in ``scripture_graph.qualifying_pages`` and is checked HERE too, so a
    URL guessed by hand cannot reach a page the sitemap never advertised.
    """

    def get(self, request, book, chapter, verse=None):
        from .scripture import VERSION_LABEL
        from .scripture_graph import (
            MAX_PASSAGES,
            VERSE_SPAN_CAP,
            book_from_slug,
            citing_rows,
            english_chapters,
            reference_label,
            verse_ids_for,
            verse_text,
        )
        from .search import fallback_snippet

        target = book_from_slug(book)
        if target is None:
            raise Http404("No such book of the Bible.")
        ids = verse_ids_for(target, chapter, verse)
        if not ids:
            raise Http404("No such chapter or verse.")

        chapters = english_chapters()
        rows = citing_rows(ids, chapters)
        # The floor, enforced on the page itself and not only in the page list:
        # a hand-typed URL for a once-cited verse must 404 rather than render
        # the thin page the list deliberately withheld.
        floor = _scripture_floor(verse)
        if len(rows) < floor:
            raise Http404("Too few citations for a page.")

        # The TRUE number of citing chapters, taken before the cap. Reporting
        # len(passages) here would have said "40" for a passage 113 chapters
        # treat — understating the page's own evidence, and disagreeing with
        # the count the page list published for the same reference.
        citing_count = len(rows)
        all_rows = rows
        rows = sorted(rows, key=lambda r: -r["count"])[:MAX_PASSAGES]
        bodies = {
            c.pk: c
            for c in chapters.filter(pk__in=[r["chapter_id"] for r in rows])
            .select_related("book__author")
        }
        passages = [
            {
                "book_slug": ch.book.slug,
                "book_title": ch.book.title,
                "author_name": ch.book.author.name,
                "author_slug": ch.book.author.slug,
                "chapter_order": ch.order,
                "chapter_title": ch.title,
                "ref": r["ref_text"],
                "excerpt": fallback_snippet(ch.body_text or "", r["ref_text"]),
            }
            for r in rows
            if (ch := bodies.get(r["chapter_id"])) is not None
        ]

        data = {
            "reference": reference_label(target, chapter, verse),
            "book": {"slug": book, "title": target.title, "order": target.value},
            "chapter": chapter,
            "verse": verse,
            "version": VERSION_LABEL,
            "citing_count": citing_count,
            "passages": passages,
            #: How many of them this payload actually carries. The page says
            #: "40 of 113" rather than quietly showing a fraction as the whole.
            "passages_shown": len(passages),
        }
        if verse is not None:
            data["text"] = verse_text(ids[0])
        else:
            # A chapter page shows the verses the library ACTUALLY treats, not
            # the whole chapter: the full ASV text is the one part of this page
            # that is not ours and that every other site already has. What makes
            # it worth a visit is which verses these writers stopped at.
            #
            # Counted from the rows ALREADY fetched for this chapter, not with a
            # query per verse. The per-verse version issued one query for each
            # of Romans 8's 39 verses, which across a build of 604 chapter pages
            # is roughly eighteen thousand queries to render a list this loop
            # can produce from data it is already holding.
            per_verse: dict[int, set[int]] = {}
            for r in all_rows:
                span = range(
                    max(r["start_verse_id"], ids[0]), min(r["end_verse_id"], ids[-1]) + 1
                )
                # A citation of the WHOLE chapter says nothing about which verse
                # a writer stopped at, so it is not evidence for any single one.
                if len(span) >= len(ids):
                    continue
                for vid in span:
                    per_verse.setdefault(vid, set()).add(r["chapter_id"])
            # `has_page` — whether THIS verse cleared the higher verse floor and
            # so has a page of its own. The server owns the floor, so the server
            # says what is linkable: the chapter page linked every cited verse
            # before this, and the build died on /scripture/genesis/1/27/, a
            # verse cited but under the floor. The reader must never be handed a
            # link to a page the floor deliberately withheld.
            from .scripture_graph import VERSE_FLOOR

            cited = [
                {
                    "number": vid % 1000,
                    "text": verse_text(vid),
                    "citing_count": len(cids),
                    "has_page": len(cids) >= VERSE_FLOOR,
                }
                for vid, cids in per_verse.items()
                if verse_text(vid)
            ]
            data["verses"] = sorted(
                cited, key=lambda v: (-v["citing_count"], v["number"])
            )[:VERSE_SPAN_CAP]
            # Prev/next among the chapter pages, so a reader (and a crawler) can
            # walk the reverse index. Here rather than in the page: the page used
            # to fetch the whole ~155 KB page list for two neighbours.
            from .scripture_graph import chapter_neighbours

            data["prev"], data["next"] = chapter_neighbours(book, chapter)
        return Response(data)


class ScriptureBookView(APIView):
    """One book of the Bible across the library — the ``/scripture/<book>/`` page.

    The hub lists a book's chapter pages; this answers the questions only the
    server can: how many library passages treat the book at all (distinct
    citing chapters, across every chapter of it, not a sum of per-chapter
    counts, which would count a passage citing Romans 5 and 8 twice), which
    library books return to it most, the ASV text of its most-quoted verses,
    one excerpt from each of those books, and a short house overview of the
    book itself (``bible_book_intros``).

    It exists only where at least one of the book's chapters has earned a page
    (``current_pages``), so it is never thinner than the pages it links to and
    the route's entries, the sitemap and this view agree on what exists. 404
    otherwise, like the chapter and verse pages.
    """

    #: Library books named as the ones that quote this book most.
    TOP_BOOKS = 6
    #: Verse pages surfaced with their text.
    TOP_VERSES = 8

    def get(self, request, book):
        from .bible_book_intros import intro as book_intro
        from .models import ChapterCitation
        from .scripture import VERSION_LABEL
        from .scripture_graph import (
            _SPAN_GUARD,
            book_from_slug,
            current_pages,
            english_chapters,
            verse_text,
        )
        from .search import fallback_snippet

        target = book_from_slug(book)
        if target is None:
            raise Http404("No such book of the Bible.")
        pages = current_pages()
        mine = [p for p in pages if p["book"] == book]
        chapters = [
            {"chapter": p["chapter"], "citing_count": p["citing_count"]}
            for p in mine
            if p["verse"] is None
        ]
        if not chapters:
            raise Http404("No chapter of this book has a page.")

        # Every citation overlapping the book: verse ids are book * 1,000,000 +
        # chapter * 1,000 + verse. A span is clamped the way `bucket` clamps it
        # (to _SPAN_GUARD ids past its start), so a mis-parsed citation running
        # from Acts to Revelation can't vote for every book in between here when
        # it votes for none of their chapter pages.
        lo = target.value * 1_000_000
        rows = (
            ChapterCitation.objects.filter(
                start_verse_id__lte=lo + 999_999,
                start_verse_id__gte=lo - _SPAN_GUARD,
                end_verse_id__gte=lo,
                chapter__in=english_chapters().values("pk"),
            )
            .values(
                "chapter_id",
                "chapter__book__slug",
                "chapter__book__title",
                "chapter__book__author__name",
                "chapter__book__author__slug",
                # For the excerpts: the reference as the work prints it, and
                # its span, so each work is quoted at its narrowest citation.
                "ref_text",
                "start_verse_id",
                "end_verse_id",
            )
            .distinct()
        )
        # One query, folded here. A work's "(For Teens)" / "(For Children)"
        # editions are separate Book rows quoting the same verses, so they are
        # one work for this ranking (the slug convention, `_edition_base_slug`),
        # named by the full edition when it is among them.
        citing: set[int] = set()
        works: dict[str, dict] = {}
        for r in rows:
            citing.add(r["chapter_id"])
            slug = r["chapter__book__slug"]
            base = _edition_base_slug(slug)
            w = works.setdefault(base, {"chapters": set(), "row": r, "cite": None})
            w["chapters"].add(r["chapter_id"])
            if slug == base:
                w["row"] = r
            # The citation its excerpt quotes: one that starts IN this book (a
            # clamped span from the book before would label the excerpt with
            # another book), the narrowest, from the work's own edition rather
            # than a teens/children one, then a stable tie-break so the
            # prerendered page doesn't churn between builds on DISTINCT order.
            key = (
                r["start_verse_id"] < lo,
                r["end_verse_id"] - r["start_verse_id"],
                slug != base,
                r["chapter_id"],
                r["ref_text"],
            )
            if w["cite"] is None or key < w["cite"][0]:
                w["cite"] = (key, r)
        top_books = sorted(
            works.values(),
            key=lambda w: (-len(w["chapters"]), w["row"]["chapter__book__title"]),
        )[: self.TOP_BOOKS]

        # One excerpt per top work, at its narrowest citation of this book —
        # what the page shows as "what the writers say". One query for the six
        # chapter bodies; the excerpt is the same snippet the chapter page uses.
        cites = [w["cite"][1] for w in top_books]
        bodies = {
            c.pk: c
            for c in english_chapters()
            .filter(pk__in=[r["chapter_id"] for r in cites])
            .select_related("book__author")
        }
        passages = [
            {
                "book_slug": ch.book.slug,
                "book_title": ch.book.title,
                "author_name": ch.book.author.name,
                "author_slug": ch.book.author.slug,
                "chapter_order": ch.order,
                "chapter_title": ch.title,
                "ref": r["ref_text"],
                "excerpt": fallback_snippet(ch.body_text or "", r["ref_text"]),
            }
            for r in cites
            if (ch := bodies.get(r["chapter_id"])) is not None
        ]

        verses = sorted(
            (p for p in mine if p["verse"] is not None),
            key=lambda p: (-p["citing_count"], p["chapter"], p["verse"]),
        )[: self.TOP_VERSES]

        # Adjacent books that have a page, in canonical order: walk the Bible
        # book by book, as the chapter pages walk it chapter by chapter.
        books = []
        for p in pages:
            if p["verse"] is None and (not books or books[-1]["book"] != p["book"]):
                books.append({"book": p["book"], "book_title": p["book_title"]})
        i = next(n for n, b in enumerate(books) if b["book"] == book)

        return Response(
            {
                "book": {"slug": book, "title": target.title, "order": target.value},
                "intro": book_intro(book),
                "version": VERSION_LABEL,
                "citing_count": len(citing),
                "passages": passages,
                "books_count": len(works),
                "chapters": chapters,
                "verses": [
                    {
                        "chapter": p["chapter"],
                        "verse": p["verse"],
                        "citing_count": p["citing_count"],
                        "text": verse_text(lo + p["chapter"] * 1000 + p["verse"]),
                    }
                    for p in verses
                ],
                "top_books": [
                    {
                        "slug": w["row"]["chapter__book__slug"],
                        "title": w["row"]["chapter__book__title"],
                        "author_name": w["row"]["chapter__book__author__name"],
                        "author_slug": w["row"]["chapter__book__author__slug"],
                        "citing_count": len(w["chapters"]),
                    }
                    for w in top_books
                ],
                "prev": books[i - 1] if i > 0 else None,
                "next": books[i + 1] if i + 1 < len(books) else None,
            }
        )


def _scripture_floor(verse):
    from .scripture_graph import CHAPTER_FLOOR, VERSE_FLOOR

    return VERSE_FLOOR if verse is not None else CHAPTER_FLOOR


class ScriptureView(APIView):
    """Verse text for a Bible reference — the reader's cross-reference popover.

    Public-domain American Standard Version, resolved locally (no external Bible
    API, so it works offline). ``?ref=John 3:16`` — ranges and common
    abbreviations are accepted.
    """

    def get(self, request):
        from .scripture import lookup

        ref = (request.query_params.get("ref") or "").strip()
        if not ref:
            return Response({"detail": "A 'ref' query parameter is required."}, status=400)
        data = lookup(ref[:120])
        if not data:
            return Response({"detail": "No such reference."}, status=404)
        return Response(data)
