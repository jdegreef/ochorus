"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

import logging

from django.core.cache import cache
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.throttling import ScopedCacheThrottle

from . import languages as languages_module
from .http_cache import PublicContentCacheMixin
from .languages import entry as language_entry
from .localization import language_from_request
from .models import (
    SERMON_CARD_DEFER,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Plan,
    SearchClickLog,
    SearchQueryLog,
    Sermon,
    Topic,
)
from .search import (
    CAPS,
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
from .serializers import (
    BOOK_CARD_ANNOTATIONS,
    AuthorDetailSerializer,
    AuthorListSerializer,
    BookDetailSerializer,
    BookListSerializer,
    ChapterDetailSerializer,
    PlanDetailSerializer,
    PlanListSerializer,
    SermonDetailSerializer,
    SermonListSerializer,
    TopicDetailSerializer,
    TopicListSerializer,
    book_topic_map,
    plan_book_index,
    plan_chapter_index,
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
        lang = _language(self.request)
        # Sermons count too — a sermon-only author is part of the library and
        # shouldn't read as empty on the shelf.
        #
        # The bio clause is per-language: qualifying on the English `bio` would
        # put an author with nothing but an English essay on the Swahili page,
        # where their card would then render blank (the serializer no longer
        # falls back). An author earns a place here by having a work in this
        # language, or a bio a reader of this language can actually read.
        # Exists(), not a join. Joining `translations` fanned this query out a
        # third way and forced the trailing .distinct() — which then made
        # Postgres de-duplicate over every selected column, `bio` and `bio_html`
        # included. A correlated EXISTS asks the same question without
        # multiplying rows, so no DISTINCT is needed and the biography text
        # never reaches a GROUP BY.
        translated_bio = Exists(
            AuthorTranslation.objects.filter(author=OuterRef("pk"), language=lang)
            .exclude(bio="", bio_html="")
        )
        own_bio = Q(original_language=lang) & (~Q(bio="") | ~Q(bio_html=""))
        return (
            Author.objects.filter(is_imprint=False)
            .prefetch_related("translations")
            .with_work_counts(lang)
            .filter(Q(num_books__gt=0) | Q(num_sermons__gt=0) | own_bio | translated_bio)
            .order_by("name")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class AuthorDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    """A single author with their published books (for the author page)."""

    serializer_class = AuthorDetailSerializer

    def get_object(self):
        # `reviewed_quotes` is ANNOTATED, not counted per object: the serializer
        # asking `obj.quotes.filter(...).count()` added a query to every author
        # page, which `BookCardPayloadTests` budgets and caught.
        return get_object_or_404(
            Author.objects.prefetch_related("translations").annotate(
                reviewed_quotes=Count(
                    "quotes", filter=Q(quotes__reviewed=True), distinct=True
                )
            ),
            slug=self.kwargs["slug"],
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class BookListView(PublicContentCacheMixin, generics.ListAPIView):
    """All published books for a language, ordered for the shelf."""

    serializer_class = BookListSerializer

    def get_queryset(self):
        return (
            Book.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(**BOOK_CARD_ANNOTATIONS)
            .order_by("sort_order", "title")
        )

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
            Chapter.objects.select_related("book__author"),
            book=book,
            order=self.kwargs["order"],
        )


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


class SermonDetailView(PublicContentCacheMixin, generics.RetrieveAPIView):
    serializer_class = SermonDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Sermon.objects.select_related("author"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
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


class PlanListView(PublicContentCacheMixin, generics.ListAPIView):
    """Published reading plans for a language."""

    serializer_class = PlanListSerializer

    def get_queryset(self):
        return (
            Plan.objects.filter(is_published=True, language=_language(self.request))
            .annotate(num_days=Count("days"))
            .prefetch_related("days")
            .order_by("sort_order", "title")
        )

    def get_serializer_context(self):
        """Resolve every plan's chapters and books ONCE for the page.

        Each card shows total words, where the plan starts, and a cover strip,
        and each of those used to fetch its own rows — three queries per plan.
        The same pattern BookListView uses for topic chips.
        """
        ctx = super().get_serializer_context()
        plans = list(self.get_queryset())
        language = _language(self.request)
        ctx["plan_chapters"] = plan_chapter_index(plans, language)
        ctx["plan_books"] = plan_book_index(plans, language)
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
        ctx["plan_chapters"] = plan_chapter_index([plan], plan.language)
        ctx["plan_books"] = plan_book_index([plan], plan.language)
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
            .prefetch_related("translations", "entries", "sermon_entries")
            .order_by("sort_order", "title")
        )
        _attach_books(topics, language)
        _attach_sermons(topics, language)
        # A shelf needs both something to hold and a name a reader of this
        # language can read: an untranslated title would render blank now that
        # the serializer no longer falls back to English.
        return [
            t
            for t in topics
            if (t.books_in_language or t.sermons_in_language)
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
                "translations", "entries", "sermon_entries"
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
        kind = (request.query_params.get("type") or "").strip().lower()
        if kind:
            return Response(self._page(q, language, kind, request, scope))

        results = search_library(q, language, scope)
        counts, capped = count_by_type(q, language, scope)
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
            SearchQueryLog.objects.create(
                query=q[:200],
                language=language[:10],
                result_count=len(results),
                suggested="suggestion" in payload,
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
                    query=q,
                    language=_language(request)[:10],
                    result_type=result_type,
                    position=position,
                )
            except Exception:
                logger.warning("search click logging failed", exc_info=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            key=self._reading_order,
        )
        if not rows:
            raise Http404("No published quotes for this author.")
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
                "quotes": [self._quote(q) for q in rows],
            }
        )

    @staticmethod
    def _reading_order(q):
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

    def _quote(self, q):
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
                # page groups BY work — see `_reading_order`.
                "cover_color": q.chapter.book.cover_color,
            }
        return {"slug": q.slug, "text": q.text, "paragraph": q.paragraph, "source": source}


class QuoteAuthorsView(APIView):
    """Authors with at least one reviewed quotation — the build's page list.

    Read by the prerender entry generator and the sitemap, so neither can
    advertise a quote page the review gate has not opened.
    """

    def get(self, request):
        from .models import Quote

        slugs = (
            Quote.objects.filter(reviewed=True)
            .values_list("author__slug", flat=True)
            .distinct()
            .order_by("author__slug")
        )
        return Response(list(slugs))


class ScripturePagesView(APIView):
    """Every scripture page that has earned a URL — the build's page list.

    Read at build time by the reader's prerender entry generator and its sitemap
    section, so both get the list from the same place the detail view enforces.
    Not a reader-facing endpoint.
    """

    def get(self, request):
        from .scripture_graph import qualifying_pages

        return Response(qualifying_pages())


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
        return Response(data)


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
