"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

import logging

from django.db.models import Count, Prefetch, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from . import languages as languages_module
from .languages import entry as language_entry
from .localization import language_from_request
from .models import (
    Author,
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
)

logger = logging.getLogger(__name__)


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
class AuthorListView(generics.ListAPIView):
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
        has_bio = (Q(original_language=lang) & (~Q(bio="") | ~Q(bio_html=""))) | (
            Q(translations__language=lang)
            & (~Q(translations__bio="") | ~Q(translations__bio_html=""))
        )
        return (
            Author.objects.filter(is_imprint=False)
            .prefetch_related("translations")
            .with_work_counts(lang)
            .filter(Q(num_books__gt=0) | Q(num_sermons__gt=0) | has_bio)
            .distinct()
            .order_by("name")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class AuthorDetailView(generics.RetrieveAPIView):
    """A single author with their published books (for the author page)."""

    serializer_class = AuthorDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Author.objects.prefetch_related("translations"), slug=self.kwargs["slug"]
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class BookListView(generics.ListAPIView):
    """All published books for a language, ordered for the shelf."""

    serializer_class = BookListSerializer

    def get_queryset(self):
        return (
            Book.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(
                num_chapters=Count("chapters"),
                total_words=Sum("chapters__word_count"),
            )
            .order_by("sort_order", "title")
        )

    def get_serializer_context(self):
        """Attach a ``book_slug -> [topic chip]`` map so each book's topics
        cost the shelf a fixed handful of queries, not one per book."""
        ctx = super().get_serializer_context()
        lang = _language(self.request)
        book_topics: dict[str, list[dict]] = {}
        topics = Topic.objects.filter(is_published=True).prefetch_related(
            "translations", "entries"
        )
        for topic in topics:
            # Skip shelves with no title in this language — see _topic_chips.
            if not topic.is_translated_into(lang):
                continue
            chip = {"slug": topic.slug, "title": topic.title_for(lang)}
            for entry in topic.entries.all():
                book_topics.setdefault(entry.book_slug, []).append(chip)
        for chips in book_topics.values():
            chips.sort(key=lambda c: c["title"])
        ctx["book_topics"] = book_topics
        return ctx


class BookDetailView(generics.RetrieveAPIView):
    serializer_class = BookDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Book.objects.filter(is_published=True)
            .select_related("author")
            .annotate(
                num_chapters=Count("chapters"),
                total_words=Sum("chapters__word_count"),
            )
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


class ChapterDetailView(generics.RetrieveAPIView):
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


class SermonListView(generics.ListAPIView):
    """All published sermons for a language, ordered for the shelf."""

    serializer_class = SermonListSerializer

    def get_queryset(self):
        return (
            Sermon.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .prefetch_related("author__translations")
            .order_by("author__name", "sort_order", "title")
        )


class SermonDetailView(generics.RetrieveAPIView):
    serializer_class = SermonDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Sermon.objects.select_related("author"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
        )


class LanguageListView(APIView):
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
        with_books = set(
            Book.objects.filter(is_published=True)
            .values_list("language", flat=True)
            .distinct()
        )
        return Response([_language_entry(c) for c in live if c in with_books])


class PlanListView(generics.ListAPIView):
    """Published reading plans for a language."""

    serializer_class = PlanListSerializer

    def get_queryset(self):
        return (
            Plan.objects.filter(is_published=True, language=_language(self.request))
            .annotate(num_days=Count("days"))
            .prefetch_related("days")
            .order_by("sort_order", "title")
        )


class PlanDetailView(generics.RetrieveAPIView):
    serializer_class = PlanDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Plan.objects.filter(is_published=True)
            .annotate(num_days=Count("days"))
            .prefetch_related("days"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )


def _attach_books(topics, language):
    """Attach ``books_in_language`` (curated-ordered, published member books in
    ``language``) to each topic in ``topics``, using two queries total rather
    than per-topic — then callers can filter out topics that are empty in the
    language. Returns the same list for convenience."""
    from django.db.models import Count, Sum

    wanted = {e.book_slug for t in topics for e in t.entries.all()}
    books = (
        Book.objects.filter(slug__in=wanted, language=language, is_published=True)
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(num_chapters=Count("chapters"), total_words=Sum("chapters__word_count"))
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
    )
    by_slug = {s.slug: s for s in sermons}
    for t in topics:
        t.sermons_in_language = [
            by_slug[e.sermon_slug]
            for e in t.sermon_entries.all()
            if e.sermon_slug in by_slug
        ]
    return topics


class TopicListView(generics.ListAPIView):
    """Published topical shelves that have at least one member book in the
    requested language (so a partially-translated library never shows an empty
    shelf). Localized titles/descriptions, with a few sample covers each."""

    serializer_class = TopicListSerializer
    pagination_class = None

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


class TopicDetailView(generics.RetrieveAPIView):
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


class SearchView(APIView):
    """Ranked full-text search across published chapters and sermons.

    Delegates to ``library.search.search_library`` (see there for the Postgres
    vs SQLite behaviour). Snippets come back with matches marker-wrapped for the
    client to render as ``<mark>``.
    """

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
    MIN_COUNT = 5  # a query must recur to read as "popular", not a one-off blip
    MIN_DISTINCT = 4  # ...and there must be a real spread, or show nothing
    LIMIT = 8

    def get(self, request):
        from datetime import timedelta

        from django.db.models.functions import Length, Lower
        from django.utils import timezone

        language = _language(request)
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
            return Response({"queries": []})
        return Response({"queries": queries})


class _SearchClickThrottle(UserRateThrottle):
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
