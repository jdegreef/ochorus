import re

from django.db.models import Count, QuerySet, Sum
from django.urls import reverse
from django.utils.text import slugify
from rest_framework import serializers

from .alternate_titles import alternate_titles
from .contemporize import MODERN_LANGUAGE
from .cover_face import COVER_AUTHOR_FIELDS, cover_face
from .curated_art import credit
from .export_policy import is_exportable
from .localization import language_from_request
from .meta_descriptions import meta_description
from .models import (
    SERMON_CARD_DEFER,
    Article,
    Author,
    Book,
    BookPerson,
    Chapter,
    Plan,
    PlanDay,
    Series,
    Sermon,
    Topic,
    TopicBook,
)
from .opening import opening_candidate_orders, opening_excerpt
from .rights import is_public_domain
from .scripture import book_of
from .scripture_graph import treated_passages


def _link_scripture(body_html: str, links: dict[str, str] | None = None) -> str:
    """Annotate a body's Bible references AND link the ones that have a page.

    One place so chapters, sermons and articles treat citations alike: every
    reference becomes the reader's popover anchor, and those whose Bible chapter
    cleared the scripture-graph floor also carry an ``href`` to the reverse-index
    page — a real internal link a crawler follows, where before there were
    thousands of hrefless anchors. Kept here (not in scripture.py) because the
    resolver lives in scripture_graph, which imports scripture.
    """
    from .scripture import annotate_references, reference_candidates
    from .scripture_graph import scripture_links

    if links is None:
        links = scripture_links(reference_candidates(body_html))
    return annotate_references(body_html, links=links)

#: The annotations every book card needs. ``BookListSerializer`` reads
#: ``num_chapters`` and ``total_words`` off the instance; a queryset missing
#: either ships a card with that key absent rather than failing, so apply these
#: as a pair wherever books are serialized: ``.annotate(**BOOK_CARD_ANNOTATIONS)``.
BOOK_CARD_ANNOTATIONS = {
    "num_chapters": Count("chapters"),
    "total_words": Sum("chapters__word_count"),
}


def _modern_edition_available(slug: str) -> bool:
    """Whether a published Modern English edition of this work exists."""
    return Book.objects.filter(
        slug=slug, language=MODERN_LANGUAGE, is_published=True
    ).exists()


#: Slug suffixes that make a separate young-reader Book row of the same work — a
#: "(For Teens)" / "(For Children)" retelling. Unlike the Modern English edition
#: (a parallel-language row under the same slug), these are their own rows under
#: ``<base>-teens`` / ``<base>-children``, and NOTHING in the model joins them to
#: the full text: the relationship is the slug convention alone, derived here.
#: Ordered by descending reading age (teens before children) — this is what
#: drives the full → teens → children order the cross-links are shown in.
EDITION_SUFFIXES = ("-teens", "-children")


def _edition_base_slug(slug: str) -> str:
    """The full-text slug a young-reader edition retells, or the slug itself."""
    for suffix in EDITION_SUFFIXES:
        if slug.endswith(suffix):
            return slug[: -len(suffix)]
    return slug


def _edition_family(base: str) -> list[str]:
    """The full text and its young-reader editions in display order
    (full → teens → children). These are the slugs the convention allows, not a
    query — a member may or may not exist as a row."""
    return [base] + [base + suffix for suffix in EDITION_SUFFIXES]


def sibling_editions(book):
    """Published audience editions of the SAME work as ``book`` — the full text
    and its "(For Teens)" / "(For Children)" retellings — excluding ``book``
    itself, ordered full → teens → children.

    The relationship is derived from the slug convention
    (``<base>`` ⇄ ``<base>-teens`` ⇄ ``<base>-children``), not stored, so this
    is the one place that knows it. Same-language only: the retellings live in
    English today, but keying on ``book.language`` means a translated set would
    cross-link within its own language and never fall back across one — the
    no-English-fallback rule the whole content model rests on. The
    ``is_published`` filter runs per request, so an unpublished edition simply
    never appears — no separate prod check to keep in sync (a plain win over a
    hand-listed shelf, where an unpublished member silently vanishes)."""
    family = _edition_family(_edition_base_slug(book.slug))
    rank = {slug: i for i, slug in enumerate(family)}
    rows = (
        Book.objects.filter(
            slug__in=[s for s in family if s != book.slug],
            language=book.language,
            is_published=True,
        )
        .select_related("author")
        .prefetch_related("author__translations")
        .annotate(**BOOK_CARD_ANNOTATIONS)
    )
    return sorted(rows, key=lambda b: rank[b.slug])


def _series_total(numbers: set, position: int | None, here: int) -> int:
    """"Of N" for a series line — ONE rule for the book page and the cards.

    An ordered volume counts the series' published volume NUMBERS in every
    language (plus its own), so "Book 4 of 4" stays true on a page that lacks
    volume 3; a collection counts this language's published books (``here``,
    the book itself included).
    """
    return len(numbers | {position}) if position is not None else here


def series_block(book) -> dict | None:
    """Where ``book`` sits in its series, for the book page's series line and
    the last chapter's "next in series" — or None.

    None when the book is in no series, and ALSO when the series has no name in
    the edition's language: there is no English fallback (``Series.title_for``),
    so a Swahili edition of an unnamed series shows no series line at all.

    ``total`` counts the series' published volume NUMBERS across every
    language, not this language's editions: "Book 4 of 4" stays true of the
    series on a Luganda page that lacks volume 3, where a count of Luganda rows
    would say "Book 4 of 3". ``previous`` / ``next`` are the nearest published
    volumes IN THIS LANGUAGE, so they skip a volume that isn't translated yet
    rather than linking to a page that doesn't exist. An unordered series (a
    collection, no positions) has neither — there is no "next" in a collection.
    """
    if book.series_id is None:
        return None
    series = Series.objects.prefetch_related("translations").get(pk=book.series_id)
    title = series.title_for(book.language)
    if not title:
        return None
    # The series' published rows in every language — a handful — read once;
    # previous / next / total are then picked out here rather than queried.
    rows = list(
        Book.objects.filter(series_id=series.pk, is_published=True).values_list(
            "slug", "title", "language", "series_position"
        )
    )
    here = [r for r in rows if r[2] == book.language and r[0] != book.slug]
    position = book.series_position
    total = _series_total({r[3] for r in rows if r[3] is not None}, position, len(here) + 1)
    if position is None:
        return {
            "slug": series.slug,
            "title": title,
            "position": None,
            "total": total,
            "previous": None,
            "next": None,
        }

    def volume(candidates, pick):
        found = pick(candidates, key=lambda r: r[3], default=None)
        return {"slug": found[0], "title": found[1]} if found else None

    numbered = [r for r in here if r[3] is not None]
    return {
        "slug": series.slug,
        "title": title,
        "position": position,
        "total": total,
        "previous": volume([r for r in numbered if r[3] < position], max),
        "next": volume([r for r in numbered if r[3] > position], min),
    }


def book_series_map(language: str, series_ids) -> dict[int, dict]:
    """``series_id -> what a card needs`` for every series named in ``language``.

    The shelf-wide twin of :func:`series_block`, for the series in
    ``series_ids`` (the shelf's), so a shelf of series books costs three
    queries however many are on it: the series and their names, then their
    published rows. ``numbers`` are the published
    volume numbers in EVERY language (``series_block``'s ``total`` for an
    ordered series); ``here`` counts this language's published books (its
    total for a collection). A series unnamed in ``language`` is left out, so
    its books carry no series line — no English fallback.
    """
    named = {}
    for s in Series.objects.filter(pk__in=series_ids).prefetch_related("translations"):
        if title := s.title_for(language):
            named[s.pk] = {"slug": s.slug, "title": title, "numbers": set(), "here": 0}
    for series_id, lang, position in Book.objects.filter(
        series_id__in=named, is_published=True
    ).values_list("series_id", "language", "series_position"):
        entry = named[series_id]
        if position is not None:
            entry["numbers"].add(position)
        if lang == language:
            entry["here"] += 1
    return named


def _published_languages(model, **filters):
    """The distinct browsable languages of the published ``model`` rows matching
    ``filters`` — a values queryset, so callers can combine it (a UNION) before
    it runs. ``.order_by()`` clears the default ordering, which a UNION can't
    carry and which would otherwise leak into the DISTINCT."""
    return (
        model.objects.filter(is_published=True, **filters)
        .exclude(language=MODERN_LANGUAGE)
        .order_by()
        .values_list("language", flat=True)
        .distinct()
    )


def _available_languages(model, slug: str) -> list[str]:
    """Sorted content locales this work is published in — for hreflang.

    Books/sermons/plans are per-language rows with no English fallback, so a
    detail page must advertise ``<link rel="alternate" hreflang>`` only for the
    locales that actually have a row. Advertising every locale unconditionally
    (the old behaviour) points crawlers at localized URLs that soft-404. The
    Modern English edition (``en-modern``) is an in-page toggle, not a
    browsable locale, so it's excluded.
    """
    return sorted(_published_languages(model, slug=slug))


def _topic_membership_map(
    language: str, *, entries_attr: str, slug_attr: str
) -> dict[str, list[dict]]:
    """``work_slug -> [topic chip]`` for every published topic, in one pass.

    The shelf-wide twin of :func:`_topic_chips`: built whole rather than per work
    on purpose, so a shelf of forty works costs a fixed handful of queries, not
    forty topic lookups. ``entries_attr`` is the topic's reverse relation to its
    through-rows (``entries`` for books, ``article_entries`` for articles) and
    ``slug_attr`` the slug on each row — the only two things that differ between
    work types. Views that know their set hand the result to the serializer
    through a context key; the list serializer builds it on demand when a view
    hasn't, so chips are never silently empty just because a caller forgot.
    """
    mapping: dict[str, list[dict]] = {}
    topics = Topic.objects.filter(is_published=True).prefetch_related(
        "translations", entries_attr
    )
    for topic in topics:
        # Skip shelves with no title in this language — see _topic_chips.
        if not topic.is_translated_into(language):
            continue
        chip = {"slug": topic.slug, "title": topic.title_for(language)}
        for entry in getattr(topic, entries_attr).all():
            mapping.setdefault(getattr(entry, slug_attr), []).append(chip)
    for chips in mapping.values():
        chips.sort(key=lambda c: c["title"])
    return mapping


def book_topic_map(language: str) -> dict[str, list[dict]]:
    """``book_slug -> [topic chip]`` for every published topic (see
    :func:`_topic_membership_map`). ``BookListView`` supplies it as
    ``book_topics``; ``BookListSerializer`` builds it on demand otherwise."""
    return _topic_membership_map(language, entries_attr="entries", slug_attr="book_slug")


def _topic_chips(language: str, **membership) -> list[dict]:
    """Localized {slug, title} chips for the published topics a work belongs to.

    ``membership`` is the reverse-relation filter that selects the topic set —
    ``entries__book_slug=…`` for a book, ``sermon_entries__sermon_slug=…`` for a
    sermon. Shared by the book and sermon detail serializers so the chip shape
    and ordering live in one place.
    """
    topics = (
        Topic.objects.filter(is_published=True, **membership)
        .prefetch_related("translations")
        .distinct()
        .order_by("sort_order", "title")
    )
    # Untranslated shelves are skipped rather than shown in English — a chip
    # with no title in this language has nothing to render.
    return [
        {"slug": t.slug, "title": t.title_for(language)}
        for t in topics
        if t.is_translated_into(language)
    ]


def article_topic_map(language: str) -> dict[str, list[dict]]:
    """``article_slug -> [topic chip]`` for every published topic (see
    :func:`_topic_membership_map`) — powers the article index's filter tabs.
    ``ArticleListView`` supplies it as ``article_topics``; the list serializer
    builds it on demand otherwise."""
    return _topic_membership_map(
        language, entries_attr="article_entries", slug_attr="article_slug"
    )


def sermon_topic_map(language: str) -> dict[str, list[dict]]:
    """``sermon_slug -> [topic chip]`` for every published topic (see
    :func:`_topic_membership_map`) — powers the sermon shelf's topic filter.
    ``SermonListView`` supplies it as ``sermon_topics``; the list serializer
    builds it on demand otherwise."""
    return _topic_membership_map(
        language, entries_attr="sermon_entries", slug_attr="sermon_slug"
    )


class LocalizedMixin:
    """Mixin for serializers whose output depends on the reader's language.

    ``_language()`` prefers an explicit ``language`` in the context (a view
    that resolved it, or a parent serializer passing it down) and otherwise
    reads the request's own ``?language=`` through the shared resolver. That
    fallback is the point: a view can't serve English by forgetting to thread
    the context — which is exactly how the author mini-bio stayed English on
    every localized book page. Declared nested fields inherit the root's
    context automatically; hand-instantiated ones must be passed
    ``context=self.context``.
    """

    def _language(self) -> str:
        return self.context.get("language") or language_from_request(
            self.context.get("request")
        )


class AuthorSerializer(LocalizedMixin, serializers.ModelSerializer):
    """The author of a book/sermon card — name, portrait, and short bio.

    The bio is localized (``AuthorTranslation``), like the biographies page's.
    """

    bio = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ["slug", "name", "bio", "photo_url", "birth_year", "death_year"]

    def get_bio(self, obj):
        return obj.bio_for(self._language())


class AuthorListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """Authors for the Biographies page, with how many books each has."""

    book_count = serializers.IntegerField(source="num_books", read_only=True)
    sermon_count = serializers.IntegerField(source="num_sermons", read_only=True)
    bio = serializers.SerializerMethodField()
    # Whether a full long-form biography exists — so the card can signal a rich
    # read vs. a one-line stub. A boolean, not the HTML (kept out of the list
    # payload); the long bio itself lives on the author detail endpoint.
    has_long_bio = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            "slug", "name", "bio", "photo_url", "birth_year", "death_year",
            "book_count", "sermon_count", "has_long_bio",
        ]

    def get_has_long_bio(self, obj):
        # The long bio is localized like the short one; a translation counts.
        return bool(obj.bio_html_for(self._language()).strip())

    def get_bio(self, obj):
        return obj.bio_for(self._language())


class BookListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """Shelf view — enough to render a cover card, no chapter bodies.

    Every queryset serialized through this must carry BOTH the ``num_chapters``
    and ``total_words`` annotations (see ``BOOK_CARD_ANNOTATIONS``). DRF drops a
    source-less field silently, so a missing annotation doesn't raise — it just
    ships a card without ``word_count``, and the same serializer then emits two
    different shapes depending on which view rendered it.
    """

    author = AuthorSerializer(read_only=True)
    chapter_count = serializers.IntegerField(source="num_chapters", read_only=True)
    word_count = serializers.IntegerField(source="total_words", read_only=True)
    topics = serializers.SerializerMethodField()
    series = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "slug",
            "language",
            "title",
            "subtitle",
            "cover_title",
            "author",
            "source_type",
            "cover_color",
            "cover_url",
            # The volume numeral a cover sets over its title; null outside an
            # ordered series. A column, so it costs the shelf no query.
            "series_position",
            # The card's series line ("Book 2 of 6 in Rooted"): slug, title,
            # position, total — `series_block` without the neighbours.
            "series",
            "chapter_count",
            "word_count",
            "topics",
            # So a card's chapter link can honour "Prefer Modern English".
            "has_modern_edition",
            "created_at",
            # The sitemap's <lastmod>. `auto_now`, but seed_books diffs every
            # field and only calls save() when one really changed, so a deploy
            # that re-upserts an unchanged book does NOT re-stamp it — which is
            # what makes this honest enough to hand a crawler. created_at was
            # standing in for it and told them a corrected book was last
            # touched on its import day.
            "updated_at",
        ]

    def get_topics(self, obj):
        """Published topics this book belongs to, for the shelf's topic filter.

        Served from a slug→chips map built once per shelf rather than per book,
        so topics cost a fixed handful of queries however many books are on it.
        A view that already knows its book set passes the map in as
        ``book_topics`` context (``BookListView``); otherwise it's built here on
        first use and cached on the serializer, which for ``many=True`` is one
        shared instance — so the author, topic and "more like this" cards get
        real chips instead of the empty list they used to always return.
        """
        supplied = self.context.get("book_topics")
        if supplied is not None:
            return supplied.get(obj.slug, [])
        language = self._language()
        cached_for, cached = getattr(self, "_topic_map", (None, None))
        if cached_for != language:
            cached = book_topic_map(language)
            self._topic_map = (language, cached)
        return cached.get(obj.slug, [])

    def get_has_modern_edition(self, obj):
        """Same rule as the detail's, answered from ONE query per response (the
        published Modern English slugs, shared through the context) rather than
        one per card."""
        if obj.language == MODERN_LANGUAGE:
            return True
        if obj.language != "en":
            return False
        modern = self.context.get("_modern_slugs")
        if modern is None:
            modern = set(
                Book.objects.filter(language=MODERN_LANGUAGE, is_published=True).values_list(
                    "slug", flat=True
                )
            )
            self.context["_modern_slugs"] = modern
        return obj.slug in modern

    def get_series(self, obj):
        """The card's series line, or None — read from a map built on the first
        series book and cached on the serializer (one shared instance for
        ``many=True``), so a shelf with no series books pays no query at all.
        The map covers only the series on this shelf. A view whose cards never
        draw the line (the series page) passes ``book_series={}`` to skip it,
        as ``book_topics`` is skipped."""
        supplied = self.context.get("book_series")
        if obj.series_id is None or supplied == {}:
            return None
        cached_for, cached = getattr(self, "_series_map", (None, None))
        if cached_for != obj.language:
            # The shelf's books when this is a `many=True` card (a ListSerializer
            # parent holds the whole list); else just this book's series. Only a
            # re-iterable instance: walking a one-shot iterator here would eat
            # the cards the parent is still serializing.
            shelf = (
                self.parent.instance
                if isinstance(self.parent, serializers.ListSerializer)
                and isinstance(self.parent.instance, (list, tuple, QuerySet))
                else None
            )
            ids = {b.series_id for b in shelf if b.series_id} if shelf is not None else {obj.series_id}
            cached = book_series_map(obj.language, ids)
            self._series_map = (obj.language, cached)
        entry = cached.get(obj.series_id)
        if entry is None:
            return None
        position = obj.series_position
        return {
            "slug": entry["slug"],
            "title": entry["title"],
            "position": position,
            "total": _series_total(entry["numbers"], position, entry["here"]),
        }


class SermonListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """A sermon card — enough for the shelf and the author page (no body)."""

    author = AuthorSerializer(read_only=True)
    # Which Bible book the sermon's text is from, for the shelf's book facet
    # ("Malachi", canonical position 39). Null for unparseable/localized refs
    # ("" included — book_of returns None). lru_cached, so the paired calls
    # per row cost one parse total.
    scripture_book = serializers.SerializerMethodField()
    scripture_book_order = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()

    def get_scripture_book(self, obj):
        info = book_of(obj.scripture_ref)
        return info[0] if info else None

    def get_scripture_book_order(self, obj):
        info = book_of(obj.scripture_ref)
        return info[1] if info else None

    def get_topics(self, obj):
        """Published topics this sermon belongs to, for the shelf's topic filter.

        Mirrors ``BookListSerializer.get_topics``: a slug→chips map built once
        per shelf — ``SermonListView`` passes it as ``sermon_topics`` — otherwise
        built here on first use and cached on the serializer (one shared instance
        for ``many=True``), so the topic and author pages get real chips too
        instead of an empty list.
        """
        supplied = self.context.get("sermon_topics")
        if supplied is not None:
            return supplied.get(obj.slug, [])
        language = self._language()
        cached_for, cached = getattr(self, "_topic_map", (None, None))
        if cached_for != language:
            cached = sermon_topic_map(language)
            self._topic_map = (language, cached)
        return cached.get(obj.slug, [])

    class Meta:
        model = Sermon
        fields = [
            "slug",
            "language",
            "title",
            "scripture_ref",
            "scripture_book",
            "scripture_book_order",
            # The "In brief" TL;DR. The shelf lists one sermon per line and
            # shows it there, so a reader decides whether to read or listen
            # without opening the sermon first. Blank on sermons whose brief
            # hasn't been written yet — the row renders without it.
            "summary",
            "preached_on",
            "word_count",
            "author",
            "topics",
            "created_at",
            # The sitemap's <lastmod> — see BookListSerializer.updated_at.
            "updated_at",
        ]


class SermonDetailSerializer(serializers.ModelSerializer):
    """A single sermon with its full body, for the reader."""

    author_name = serializers.CharField(source="author.name", read_only=True)
    author_slug = serializers.CharField(source="author.slug", read_only=True)
    author_photo = serializers.CharField(source="author.photo_url", read_only=True)
    body_html = serializers.SerializerMethodField()
    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    difficulty = serializers.SerializerMethodField()
    # The preacher's entity identifiers, for the sermon's JSON-LD author — the
    # same list BookDetail carries as author_same_as, so a sermon's Person node
    # names WHICH person it is, not just a matching name.
    author_same_as = serializers.SerializerMethodField()

    def get_author_same_as(self, obj):
        return obj.author.same_as or []

    def get_difficulty(self, obj):
        from .readability import difficulty

        return difficulty(obj.body_text)

    def get_body_html(self, obj):
        # Wrap Bible references as clickable spans (the reader's scripture
        # popover) and link the ones with a scripture page (a crawlable
        # internal link), the same treatment chapters get.
        return _link_scripture(obj.body_html)

    scripture_refs = serializers.SerializerMethodField()

    def _scripture_refs(self, obj):
        """The distinct passages this sermon engages — its text first, then
        references cited in the body. The main text is deduped against body
        citations by verse overlap so "Mark 9:23" doesn't appear twice under
        two spellings. Cached on the instance: the body parse is not free and
        both ``scripture_refs`` and ``scripture_links`` want the same list."""
        cache = getattr(obj, "_scripture_refs_cache", None)
        if cache is not None:
            return cache
        from .scripture import cited_references, reference_verse_ids

        refs: list[str] = []
        main_ids = frozenset()
        if obj.scripture_ref:
            refs.append(obj.scripture_ref)
            main_ids = reference_verse_ids(obj.scripture_ref)
        for r in cited_references(obj.body_html):
            ids = reference_verse_ids(r)
            if main_ids and ids and ids <= main_ids:
                continue
            refs.append(r)
        obj._scripture_refs_cache = refs[:8]
        return obj._scripture_refs_cache

    def get_scripture_refs(self, obj):
        """The passages this sermon engages, for the scripture-index chip row."""
        return self._scripture_refs(obj)

    scripture_links = serializers.SerializerMethodField()

    def get_scripture_links(self, obj):
        """Map of those references to their ``/scripture/<book>/<chapter>/`` page,
        for the ones whose Bible chapter cleared the scripture-graph floor. Lets
        the chip row link to the crawlable reverse-index page (a real internal
        link) instead of a search query; refs with no page keep the search
        fallback on the frontend. Reuses the resolver the body links with."""
        from .scripture_graph import scripture_links

        return scripture_links(self._scripture_refs(obj))

    def _neighbours(self, obj):
        """The (prev, next) sermon in this author's corpus, in shelf order.

        Sequential reading through one preacher's published sermons in this
        language, ordered like the author page (sort_order, then title). Cached
        on the instance so prev and next share one query. Ends are ``None``."""
        cache = getattr(obj, "_neighbour_cache", None)
        if cache is None:
            corpus = list(
                Sermon.objects.filter(
                    author_id=obj.author_id,
                    language=obj.language,
                    is_published=True,
                )
                .order_by("sort_order", "title")
                .values("slug", "title")
            )
            i = next((n for n, s in enumerate(corpus) if s["slug"] == obj.slug), None)
            prev_ = corpus[i - 1] if i not in (None, 0) else None
            next_ = corpus[i + 1] if i is not None and i + 1 < len(corpus) else None
            cache = (prev_, next_)
            obj._neighbour_cache = cache
        return cache

    def get_prev(self, obj):
        return self._neighbours(obj)[0]

    def get_next(self, obj):
        return self._neighbours(obj)[1]

    topics = serializers.SerializerMethodField()

    def get_topics(self, obj):
        """Published topics this sermon belongs to, localized — small chips
        linking to each topical shelf. Mirrors BookDetailSerializer.get_topics;
        the author and topic pages already surface this membership, the sermon
        page didn't."""
        return _topic_chips(obj.language, sermon_entries__sermon_slug=obj.slug)

    available_languages = serializers.SerializerMethodField()

    def get_available_languages(self, obj):
        return _available_languages(Sermon, obj.slug)

    # How many reviewed quotations this sermon's author has, so the page can show
    # a "Quotes from {author}" link (English only, as the quote pages are).
    # Mirrors BookDetailSerializer.author_quote_count.
    author_quote_count = serializers.SerializerMethodField()

    def get_author_quote_count(self, obj) -> int:
        return obj.author.quotes.filter(reviewed=True).count()

    class Meta:
        model = Sermon
        fields = [
            "slug",
            "language",
            "title",
            "scripture_ref",
            "preached_on",
            "word_count",
            "body_html",
            "source_type",
            "source_url",
            "attribution",
            "author_name",
            "author_slug",
            "author_photo",
            "author_same_as",
            "prev",
            "next",
            "scripture_refs",
            "scripture_links",
            "summary",
            "study_questions",
            "difficulty",
            "topics",
            "available_languages",
            "author_quote_count",
            # For the sermon page's JSON-LD `dateModified`. Honest as a
            # modification date: seed_sermons diffs before saving, so `auto_now`
            # doesn't re-stamp every row on every deploy (same reasoning that
            # lets the sitemap use it as <lastmod>).
            "updated_at",
        ]


_ARTICLE_H2 = re.compile(r"<h2>([\s\S]*?)</h2>")
_HTML_TAG = re.compile(r"<[^>]+>")


def inject_heading_ids(body_html: str) -> tuple[str, list[dict]]:
    """Give each ``<h2>`` section a stable id and return ``(html, toc)``.

    The stored body carries bare ``<h2>`` headings — the rich sanitize profile
    scrubs every attribute save ``class`` on ``<aside>`` / ``href`` on ``<a>``
    (see sanitize.py), so a heading never arrives with an id or any other
    attribute, and the bare-tag match below is safe. The id is injected here, at
    read time, after sanitize — the same stage ``annotate_references`` runs — and
    the returned ``toc`` lists the very ids injected. One pass produces both, so
    an article page's jump links and the headings they target come from a single
    source and cannot drift. Ids are slugified from the heading text (unicode
    preserved so a translated heading keeps a real anchor).
    """
    toc: list[dict] = []
    used: set[str] = set()

    def add_id(m: re.Match) -> str:
        inner = m.group(1)
        text = _HTML_TAG.sub("", inner).strip()
        base = slugify(text, allow_unicode=True) or "section"
        # Uniqueness is checked against every id already assigned, not a
        # per-base counter: a suffixed id ("section-2") must not collide with the
        # slug of a differently-worded heading ("Section 2"), or the toc would
        # carry duplicate keys and the page's keyed {#each} would fail.
        heading_id = base
        n = 1
        while heading_id in used:
            n += 1
            heading_id = f"{base}-{n}"
        used.add(heading_id)
        toc.append({"id": heading_id, "text": text})
        return f'<h2 id="{heading_id}">{inner}</h2>'

    return _ARTICLE_H2.sub(add_id, body_html), toc


def related_entries(related) -> list[tuple[str, str]]:
    """An article's ``related`` as validated ``(kind, slug)`` pairs, in order.

    ``related`` is a hand-authored JSON field with no schema, so a malformed
    entry (a bare slug string, a non-dict, a non-list, an unknown type, a blank
    slug) is skipped rather than raising. The one parser of the field: the
    Read-next cards, the lead book and the author page's articles all read it
    through here, so they agree on what counts as an entry.
    """
    entries: list[tuple[str, str]] = []
    for item in related if isinstance(related, list) else []:
        if not isinstance(item, dict):
            continue
        slug, kind = item.get("slug"), item.get("type")
        # A non-string slug (a list, a number) is malformed too — and would
        # break the set/dict lookups every caller does with it.
        if isinstance(slug, str) and slug and kind in ("book", "sermon", "author"):
            entries.append((kind, slug))
    return entries


def resolve_related(related, language: str) -> list[dict]:
    """Turn an article's stored ``related`` soft-references into ready-to-render
    "Read next" cards: ``[{type, slug, title, url, <thumbnail fields>}, ...]``.

    A book card also carries ``cover_url`` + ``cover_color`` and an author card
    ``photo_url``, so the block renders covers and portraits, not bare links; a
    sermon carries neither (its shelf tile is a drawn emblem, not an image).

    Each entry names a ``type`` (book / sermon / author) and a ``slug``; this
    resolves it to the published row's display title and its reader URL, in the
    article's language. A reference that doesn't resolve — an unpublished target,
    or a book/sermon with no row in this language (there is no English fallback)
    — is dropped rather than shipped as a dead link, and order is preserved.

    Books and sermons are looked up by (slug, language); an author is a single
    language-agnostic row, so it is looked up by slug alone. One query per type
    present, not one per reference.

    Malformed entries are skipped (``related_entries``); the validated ones
    are collected once, in order, and reused for both the batched lookup and
    the final card list.
    """
    entries = related_entries(related)

    by_type: dict[str, list[str]] = {}
    for kind, slug in entries:
        by_type.setdefault(kind, []).append(slug)

    # (kind, slug) -> the card's display fields, INCLUDING the thumbnail a card
    # needs to render a real shopfront rather than a text link: a book carries
    # its cover (url + colour fallback), an author their portrait, a sermon has
    # neither (its shelf tile is a drawn emblem, not an image) and stays text.
    found: dict[tuple[str, str], dict] = {}
    if by_type.get("book"):
        for slug, title, cover_url, cover_color in Book.objects.filter(
            slug__in=by_type["book"], language=language, is_published=True
        ).values_list("slug", "title", "cover_url", "cover_color"):
            found[("book", slug)] = {
                "title": title,
                "cover_url": cover_url,
                "cover_color": cover_color,
            }
    if by_type.get("sermon"):
        for slug, title in Sermon.objects.filter(
            slug__in=by_type["sermon"], language=language, is_published=True
        ).values_list("slug", "title"):
            found[("sermon", slug)] = {"title": title}
    if by_type.get("author"):
        for slug, name, photo_url in Author.objects.filter(
            slug__in=by_type["author"]
        ).values_list("slug", "name", "photo_url"):
            found[("author", slug)] = {"title": name, "photo_url": photo_url}

    prefix = {"book": "/books/", "sermon": "/sermons/", "author": "/authors/"}
    cards = []
    for kind, slug in entries:
        data = found.get((kind, slug))
        if data is None:
            continue
        cards.append(
            {
                "type": kind,
                "slug": slug,
                "url": f"{prefix[kind]}{slug}/",
                # title, then whichever thumbnail fields the type carries.
                **data,
            }
        )
    return cards


# A reader's guide is an article whose slug ends ``-guide`` — the repo's
# convention (the ``write-article`` playbook's book guides). There is no typed
# flag on Article, so the suffix IS the definition; everything that asks "is
# this a guide?" reads it from here.
GUIDE_SLUG_SUFFIX = "-guide"


def is_guide_slug(slug: str) -> bool:
    return slug.endswith(GUIDE_SLUG_SUFFIX)


def first_book_slug(related) -> str | None:
    """The article's PRIMARY book: the first ``book`` entry in its Read-next
    ``related`` (see ``guides_for_book`` for why the first one is the subject).
    Malformed entries are skipped (``related_entries``); an article with no
    book gets ``None``."""
    return next((slug for kind, slug in related_entries(related) if kind == "book"), None)


class CoverAuthorSerializer(serializers.ModelSerializer):
    """The author fields a book COVER draws — the frontend's ``CoverBook.author``
    (``COVER_AUTHOR_KEYS``), and nothing else: no bio, no portrait."""

    class Meta:
        model = Author
        fields = list(COVER_AUTHOR_FIELDS)


class CoverBookSerializer(BookListSerializer):
    """A book cut down to what its cover and card draw — the frontend's
    ``CoverBook`` (``COVER_BOOK_KEYS`` + a ``CoverAuthorSerializer`` author).
    Rides on an article card as its ``lead_book``, so the fields are kept to
    exactly what ``BookCover`` reads: an index of ~130 articles carries one each.
    Like its parent, the queryset must carry ``BOOK_CARD_ANNOTATIONS``."""

    author = CoverAuthorSerializer(read_only=True)

    class Meta(BookListSerializer.Meta):
        fields = [
            "slug",
            "language",
            "title",
            "subtitle",
            "cover_title",
            "author",
            "source_type",
            "cover_color",
            "cover_url",
            "series_position",
            "chapter_count",
            "word_count",
        ]


def lead_book_cards(related_by_article: dict[str, object], language: str) -> dict[str, dict]:
    """``article_slug -> cover card`` of each article's primary book, for the
    ``lead_book`` an article card shows (its cover, and the "Leads to" line).

    ``related_by_article`` maps each article slug to its raw ``related`` JSON.
    The primary book resolves like ``resolve_related`` does: a published row in
    the ARTICLE's language (no English fallback), else the article simply has no
    lead book. One book query for the whole set, not one per article.
    """
    firsts = {slug: first_book_slug(rel) for slug, rel in related_by_article.items()}
    wanted = {b for b in firsts.values() if b}
    if not wanted:
        return {}
    books = (
        Book.objects.filter(slug__in=wanted, language=language, is_published=True)
        .select_related("author")
        .annotate(**BOOK_CARD_ANNOTATIONS)
    )
    cards = {b.slug: CoverBookSerializer(b).data for b in books}
    return {a: cards[b] for a, b in firsts.items() if b in cards}


def article_lead_book_map(language: str) -> dict[str, dict]:
    """``article_slug -> lead book card`` for every published article in
    ``language`` — the index's covers, built once per shelf (two queries,
    whatever the shelf's size), mirroring ``article_topic_map``."""
    rows = Article.objects.filter(is_published=True, language=language).values_list(
        "slug", "related"
    )
    return lead_book_cards(dict(rows), language)


def guides_for_book(book_slug: str, language: str) -> list[dict]:
    """The published articles that are a reader's guide *to* this book — so a
    book page can surface the guide that explains it, the reverse of the
    article→book Read-next funnel.

    Two conditions, both needed to name the *guide* rather than the many
    topical/definitional articles that merely funnel a reader to a good book:

    * the article is a guide at all — its slug ends ``-guide``, the repo's
      convention for a reader's guide (the ``write-article`` playbook's book
      guides; there is no typed flag on Article, so the convention is the
      definition — adjust here if one is added); and
    * this book is the guide's PRIMARY subject — the first book in its Read-next
      ``related``. A guide can point on to sibling works (Augustine's guide also
      lists *Grace Abounding*), so keying on the first book attributes each guide
      to the one work it is about, not to every book it mentions.

    Returns ``[{slug, h1, description}, ...]`` in article sort order (normally
    one), in the requested language only — articles are per-language rows like
    everything else, so a localized edition gets its own guide or none, never the
    English one (the no-English-fallback rule). A translated guide therefore
    surfaces only where the BOOK also has an edition in that language, which is
    why translating a guide alone does not make it appear. ``related`` is a
    schema-less hand-authored JSON field, so a malformed entry is skipped rather
    than raising. One scan of the article table (no bodies), paid on a book
    DETAIL page only — never a shelf.
    """
    rows = (
        Article.objects.filter(
            is_published=True, language=language, slug__endswith=GUIDE_SLUG_SUFFIX
        )
        .order_by("sort_order", "h1")
        .values("slug", "h1", "description", "related")
    )
    out = []
    for row in rows:
        if first_book_slug(row["related"]) == book_slug:
            out.append(
                {
                    "slug": row["slug"],
                    "h1": row["h1"],
                    "description": row["description"],
                }
            )
    return out


def articles_for_author(author_slug: str, language: str) -> list[dict]:
    """The published articles that name this person — so an author page can
    surface them, the reverse of the article→author funnel.

    The counterpart of ``guides_for_book``, and the reason it exists: an article
    reached only from the /articles hub sits too deep in the link graph to earn a
    crawl, while author pages are among the most-crawled on the site.

    ONE rule: the article names this person in its Read-next ``related``. That is
    an editorial judgement made when the article is written — a reader's guide
    names the author of the book it explains, an essay names whoever it leans on
    — so it deliberately includes a person the article DISCUSSES without their
    having written anything (the guide to Augustine's *Confessions* names Monica,
    and lands on her page). That is wanted: those bio-only pages are the sparsest
    on the site and the article genuinely talks about them.

    There is deliberately no second rule keying on the guided book's author. It
    was written, measured against the whole corpus, and deleted: all 73 ``-guide``
    articles already name their book's author here, so it selected a strict subset
    of this rule while costing a ``Book`` query on all 891 author pages a build
    renders. It also could not do what a second rule in a UNION can never do —
    narrow. The authoring invariant it relied on is now written down in the
    ``write-article`` skill instead.

    Returns ``[{slug, h1, description}, ...]`` in article sort order, in the
    requested language only — articles are per-language rows like everything
    else, so a locale with translated articles gets them and a locale without
    gets an empty list rather than the English ones (the no-English-fallback
    rule). ``related`` is schema-less hand-authored JSON, so a malformed entry is
    skipped rather than raising. One scan of the article table (no bodies), paid
    on an author DETAIL page only — never a shelf.
    """
    rows = (
        Article.objects.filter(is_published=True, language=language)
        .order_by("sort_order", "h1")
        .values("slug", "h1", "description", "related")
    )
    out = []
    for row in rows:
        if ("author", author_slug) in related_entries(row["related"]):
            out.append(
                {
                    "slug": row["slug"],
                    "h1": row["h1"],
                    "description": row["description"],
                }
            )
    return out


class ArticleListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """An article card — enough for the /articles index (no body).

    Carries ``word_count`` (the "N min read" estimate) and ``topics`` (the
    index's filter tabs and the funnel back to the topic pages), so the card
    matches the book/sermon shelf cards rather than being a bare title.
    """

    topics = serializers.SerializerMethodField()
    lead_book = serializers.SerializerMethodField()
    kind = serializers.SerializerMethodField()

    def get_kind(self, obj):
        """``"guide"`` for a reader's guide to one book, else ``"article"`` — the
        index's Questions / Book guides switch. See ``GUIDE_SLUG_SUFFIX``."""
        return "guide" if is_guide_slug(obj.slug) else "article"

    def get_lead_book(self, obj):
        """The cover card of the article's primary book (the first book it sends
        the reader to), or ``None`` — so the index can show the classic behind
        each article, not a wall of text. Every caller passes the batch as
        ``article_lead_books`` context — the list view the whole shelf's map,
        the topic page just its own articles' (``lead_book_cards``) — so a card
        never resolves a book on its own; without that context it is ``None``."""
        return (self.context.get("article_lead_books") or {}).get(obj.slug)

    def get_topics(self, obj):
        """The (published, localized) topics this card belongs to, so the index
        can offer topic-filter tabs. Mirrors ``BookListSerializer.get_topics``:
        served from a slug→chips map built once per shelf, passed in as
        ``article_topics`` context by ``ArticleListView`` or built here on first
        use and cached on the shared ``many=True`` instance otherwise. Language
        comes from the reader (context/request) via ``LocalizedMixin``, the same
        source the batch path uses — never a hardcoded English default."""
        supplied = self.context.get("article_topics")
        if supplied is not None:
            return supplied.get(obj.slug, [])
        language = self._language()
        cached_for, cached = getattr(self, "_topic_map", (None, None))
        if cached_for != language:
            cached = article_topic_map(language)
            self._topic_map = (language, cached)
        return cached.get(obj.slug, [])

    class Meta:
        model = Article
        fields = [
            "slug",
            "language",
            "h1",
            "meta_title",
            "description",
            # Review state, so the reader can badge an unreviewed AI translation
            # (CLAUDE.md: never present one as an original). Shares Book's
            # vocabulary; an English original is "public_domain" (no badge).
            "source_type",
            # The reading-time source, derived from body_html on save(); the
            # index defers the body but this column loads with the row.
            "word_count",
            "sort_order",
            "created_at",
            # The sitemap's <lastmod> — see BookListSerializer.updated_at. The
            # seed keeps this honest by only save()-ing a genuinely changed row.
            "updated_at",
            # Topic chips — the index filter tabs and the detail page's
            # back-links. Batched by the list view; per-object on detail.
            "topics",
            # The primary book's cover card (or null) and guide/article — the
            # index's covers, "Leads to" line and Questions / Book guides switch.
            "lead_book",
            "kind",
        ]


class ArticleDetailSerializer(ArticleListSerializer):
    """A single article with its body and its resolved "Read next" links."""

    body_html = serializers.SerializerMethodField()
    toc = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()
    more_articles = serializers.SerializerMethodField()
    scripture_refs = serializers.SerializerMethodField()
    scripture_links = serializers.SerializerMethodField()

    # How many "More on this topic" cards the page shows.
    MORE_ARTICLES = 3

    def get_topics(self, obj):
        """Published topics this article belongs to (localized) — the chips that
        close the funnel back to the topic pages. A single article needs no
        batch map, so this overrides the list serializer with a direct query;
        the topic page already lists the article in return."""
        return _topic_chips(obj.language, article_entries__article_slug=obj.slug)

    def _rendered(self, obj):
        # The read-time body pipeline, run once and cached: annotate Bible
        # references as clickable spans (the same treatment chapters/sermons
        # get), then give each <h2> a stable id and collect the table of
        # contents. Both run AFTER the stored body was sanitized, so neither the
        # scripture <a> nor the heading id is re-stripped. body_html and toc read
        # from this one pass, so the page's jump links match the ids in the HTML.
        cache = self.__dict__.setdefault("_rendered_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = inject_heading_ids(_link_scripture(obj.body_html))
        return cache[obj.pk]

    def get_body_html(self, obj):
        return self._rendered(obj)[0]

    def get_toc(self, obj):
        """The article's `<h2>` sections as ``[{id, text}]`` jump targets — the
        client renders the on-this-page nav from this and never parses the body."""
        return self._rendered(obj)[1]

    def get_related(self, obj):
        return resolve_related(obj.related, obj.language)

    def _more(self, obj) -> list:
        """Up to ``MORE_ARTICLES`` other published articles in this language that
        share a topic with this one — the "More on …" row, so a reader who
        finished has somewhere to go that isn't back to the index.

        Ranked by how many topics they share (the closest first; the same
        overlap count ``BookDetailSerializer.get_related`` ranks by), then, for
        a question article, questions ahead of reader's guides (a guide is about
        one book, a poor next step from "How to pray"), then curated order.
        Cached per article: ``more_articles`` and ``lead_book`` both read it.
        """
        cache = self.__dict__.setdefault("_more_cache", {})
        if obj.pk in cache:
            return cache[obj.pk]
        from .models import TopicArticle

        topic_ids = TopicArticle.objects.filter(
            article_slug=obj.slug, topic__is_published=True
        ).values_list("topic_id", flat=True)
        shared = {
            row["article_slug"]: row["shared"]
            for row in TopicArticle.objects.filter(topic_id__in=topic_ids)
            .exclude(article_slug=obj.slug)
            .values("article_slug")
            .annotate(shared=Count("topic_id", distinct=True))
        }
        rows = list(
            Article.objects.filter(
                slug__in=shared, language=obj.language, is_published=True
            )
            .defer("body_html")
            .order_by("sort_order", "h1")
        ) if shared else []
        prefer_questions = not is_guide_slug(obj.slug)
        rows.sort(
            key=lambda a: (-shared[a.slug], prefer_questions and is_guide_slug(a.slug))
        )  # stable: ties keep the curated order
        cache[obj.pk] = rows[: self.MORE_ARTICLES]
        return cache[obj.pk]

    def _lead_books(self, obj) -> dict[str, dict]:
        """Cover cards for this article's book AND the "More on" cards' books,
        in one lookup (it aggregates each book's chapters, so it isn't free)."""
        cache = self.__dict__.setdefault("_lead_cache", {})
        if obj.pk not in cache:
            related = {a.slug: a.related for a in self._more(obj)}
            related[obj.slug] = obj.related
            cache[obj.pk] = lead_book_cards(related, obj.language)
        return cache[obj.pk]

    def get_lead_book(self, obj):
        # The page's hero cover and share image.
        return self._lead_books(obj).get(obj.slug)

    def get_more_articles(self, obj):
        # Index cards with covers. Their topic chips are not drawn on this row,
        # so `article_topics={}` spares the whole-language topic map the list
        # serializer would otherwise build for three cards.
        return ArticleListSerializer(
            self._more(obj),
            many=True,
            context={
                **self.context,
                "language": obj.language,
                "article_topics": {},
                "article_lead_books": self._lead_books(obj),
            },
        ).data

    def _scripture_refs(self, obj) -> list[str]:
        """The passages the article cites, in order of first mention, capped
        like a sermon's chip row. Cached: refs and links want the same list."""
        cache = self.__dict__.setdefault("_refs_cache", {})
        if obj.pk not in cache:
            from .scripture import cited_references

            cache[obj.pk] = cited_references(obj.body_html)
        return cache[obj.pk]

    def get_scripture_refs(self, obj):
        """The passages this article cites, for the "Scriptures in this
        article" chip row — the same field the sermon page's row reads."""
        return self._scripture_refs(obj)

    def get_scripture_links(self, obj):
        """Those references' ``/scripture/<book>/<chapter>/`` pages, where one
        exists — so the chips link to the crawlable index, as the sermon's do."""
        from .scripture_graph import scripture_links

        return scripture_links(self._scripture_refs(obj))

    def get_available_languages(self, obj):
        return _available_languages(Article, obj.slug)

    class Meta(ArticleListSerializer.Meta):
        # topics + word_count already ride on the list serializer's fields;
        # detail just overrides get_topics with a direct query and adds the body,
        # its table of contents, the Read-next links and source/languages.
        fields = ArticleListSerializer.Meta.fields + [
            "body_html",
            "toc",
            "related",
            "source_url",
            "available_languages",
            # The "More on …" cards (index-card shape, with covers).
            "more_articles",
            # The cited passages, and their scripture pages where they exist.
            "scripture_refs",
            "scripture_links",
        ]


class AuthorDetailSerializer(LocalizedMixin, serializers.ModelSerializer):
    """An author page: bio, dates, their books and their sermons in a language."""

    book_count = serializers.SerializerMethodField()
    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    bio_html = serializers.SerializerMethodField()
    bio_source_type = serializers.SerializerMethodField()
    # The Q&A set shown at the foot of the page, in the requested language only
    # ([] when this locale has no translated set — same no-fallback rule as the
    # bio). Detail-only: a card has nowhere to show it.
    faq = serializers.SerializerMethodField()
    # Books this person is FOUND IN but did not write (BookPerson) — the reverse
    # of BookDetailSerializer.featured_people, so a bio can offer "appears in".
    appears_in = serializers.SerializerMethodField()
    # Articles that name this person — see ``articles_for_author`` for the rule
    # and why it is the only one. Per-language like the rest of the page, so a
    # locale with no translated article renders no section. Detail-only: it
    # scans the article table, nothing a shelf should pay.
    articles = serializers.SerializerMethodField()

    # Present so AuthorDetail honours the AuthorBio contract the list shares;
    # the detail page already has the full sermons array + bio_html, so these
    # are just the summary numbers.
    sermon_count = serializers.SerializerMethodField()
    has_long_bio = serializers.SerializerMethodField()
    # The locales where this page has something of the writer's OWN — a bio, a
    # published book or a published sermon — for the page's hreflang. The same
    # rule as the frontend's ``hasOwnContent`` (which noindexes the rest) and the
    # sitemap's author entries, so an alternate never names a noindexed page.
    available_languages = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            "slug", "name", "bio", "bio_html", "bio_source_type", "faq", "photo_url",
            "available_languages",
            # Portrait credit — only the detail page renders it (a card shows the
            # thumbnail without a caption, which the CC licences allow because
            # every card links here, so the credit is one click from any
            # thumbnail). A non-linking reuse of a portrait (an OG/share image,
            # an email digest) would have to carry the credit with it.
            "photo_attribution", "photo_source_url", "birth_year",
            "death_year", "book_count", "sermon_count", "has_long_bio",
            "books", "sermons", "topics", "appears_in", "articles",
            # Authoritative identifiers for the Person markup — see the field.
            # Only the DETAIL serializer carries them: a card never emits
            # Person markup, so shipping them on every book row would be bytes
            # nothing reads.
            "same_as",
            # How many REVIEWED quotations this author has, so the page can
            # offer the quote page only when one exists. Counting unreviewed
            # rows would link to a page the review gate keeps 404ing.
            "quote_count",
            # Life-and-ministry events for the timeline (plain JSON on the model,
            # so it serializes as-is). Only the detail page draws the timeline.
            "milestones",
        ]

    # Reads the view's annotation; falls back to a count only when a caller
    # serialized an un-annotated Author (the admin does).
    quote_count = serializers.SerializerMethodField()

    def get_quote_count(self, obj):
        n = getattr(obj, "reviewed_quotes", None)
        return n if n is not None else obj.quotes.filter(reviewed=True).count()

    def get_bio(self, obj):
        return obj.bio_for(self._language())

    def get_bio_html(self, obj):
        return obj.bio_html_for(self._language())

    def get_faq(self, obj):
        return obj.faq_for(self._language())

    def get_bio_source_type(self, obj):
        """How the bio shown in the requested language got here, so the page can
        badge an unreviewed AI translation (CLAUDE.md: never present one as an
        original). Reuses Book.source_type's vocabulary so the frontend shares
        SourceBadge unchanged: the source-language original is "public_domain"
        (no badge); a translated bio is "ai_reviewed" once a native speaker signs
        it off (AuthorTranslation.reviewed), "ai_unreviewed" until then. When the
        requested language has no translated prose, get_bio_html serves nothing,
        so there is nothing to badge either."""
        language = self._language()
        if not language or language == obj.original_language:
            return "public_domain"
        tr = next(
            (t for t in obj.translations.all() if t.language == language), None
        )
        if not tr or not (tr.bio_html or tr.bio):
            return "public_domain"
        return "ai_reviewed" if tr.reviewed else "ai_unreviewed"

    def get_articles(self, obj) -> list[dict]:
        # No English-only gate, deliberately — translated article rows exist, so
        # the language filter is the whole rule. BookDetailSerializer.guides
        # follows it too.
        return articles_for_author(obj.slug, self._language())

    def get_sermon_count(self, obj):
        return len(self._sermons(obj))

    def get_has_long_bio(self, obj):
        return bool(obj.bio_html_for(self._language()).strip())

    def get_available_languages(self, obj) -> list[str]:
        langs: set[str] = set()
        if not obj.is_imprint:
            # A translation row in the source language is never served
            # (`Author._localized` reads the source fields there), so it can't
            # count; the source bio speaks for that language.
            langs.update(
                t.language
                for t in obj.translations.all()
                if (t.bio or t.bio_html) and t.language != obj.original_language
            )
            if obj.bio or obj.bio_html:
                langs.add(obj.original_language)
        # ONE query for both kinds: the page is walked once per author per
        # locale on every prerender.
        langs.update(
            _published_languages(Book, author=obj).union(_published_languages(Sermon, author=obj))
        )
        return sorted(langs)

    def _cached(self, key, obj, build):
        """Run ``build`` once per (field, author, language) and reuse the list.

        Several of this serializer's fields want the same result sets, and each
        used to re-run its own query — books three ways (the list, ``.count()``,
        ``.values_list()``), sermons twice, and the topic walk once per chip
        field. The author page is walked once per author per locale on every
        prerender, so those repeats were paid on every build. Measured on a
        one-book/one-sermon/one-topic author: 15 queries down to 10, and the
        book cards now carry topic chips they previously never got.
        """
        cache = getattr(self, "_result_cache", None)
        if cache is None:
            cache = self._result_cache = {}
        ck = (key, obj.pk, self._language())
        if ck not in cache:
            cache[ck] = build()
        return cache[ck]

    def _sermons(self, obj):
        return self._cached(
            "sermons",
            obj,
            lambda: list(
                obj.sermons.filter(is_published=True, language=self._language())
                .select_related("author")
                .prefetch_related("author__translations")
                .defer(*SERMON_CARD_DEFER)
                .order_by("sort_order", "title")
            ),
        )

    def _books(self, obj):
        return self._cached(
            "books",
            obj,
            lambda: list(
                obj.books.filter(is_published=True, language=self._language())
                .select_related("author")
                .prefetch_related("author__translations")
                # total_words too, not just the chapter count: without it these
                # cards shipped without word_count while every other path had
                # it, so reading-time estimates vanished on author pages alone.
                .annotate(**BOOK_CARD_ANNOTATIONS)
                .order_by("sort_order", "title")
            ),
        )

    def get_books(self, obj):
        # The book cards' own topic chips come from the same pass this page
        # already makes over published topics — without threading it through,
        # BookListSerializer would fetch the whole topic set a second time.
        ctx = {**self.context, "book_topics": self._topic_pass(obj)[1]}
        return BookListSerializer(self._books(obj), many=True, context=ctx).data

    def get_book_count(self, obj):
        return len(self._books(obj))

    def get_sermons(self, obj):
        # The sermon cards' topic chips come from the same topic walk this page
        # already makes (via _topic_pass), threaded in the way get_books threads
        # book_topics — otherwise SermonListSerializer would fetch the whole
        # topic set a second time (BookCardPayloadTests budgets this page).
        ctx = {**self.context, "sermon_topics": self._topic_pass(obj)[2]}
        return SermonListSerializer(self._sermons(obj), many=True, context=ctx).data

    def _topic_pass(self, obj):
        """One walk over published topics, serving both chip fields.

        Returns ``(author chips, book_slug -> chips, sermon_slug -> chips)``: the
        shelves this author appears in, and the per-book and per-sermon maps the
        nested cards need. Three fields want the same topic rows, so they share
        one fetch — otherwise the author page would pull the whole topic set
        (plus its translations and both membership tables) more than once.
        """
        return self._cached("topic_pass", obj, lambda: self._build_topic_pass(obj))

    def _build_topic_pass(self, obj):
        from .models import Topic

        lang = self._language()
        # Derived from the memoized lists the other fields already fetched —
        # the slugs are right there, and re-querying for them cost two more
        # round-trips per author page.
        book_slugs = {b.slug for b in self._books(obj)}
        sermon_slugs = {s.slug for s in self._sermons(obj)}
        if not book_slugs and not sermon_slugs:
            return [], {}, {}
        topics = Topic.objects.filter(is_published=True).prefetch_related(
            "translations", "entries", "sermon_entries"
        )
        chips = []
        by_book: dict[str, list[dict]] = {}
        by_sermon: dict[str, list[dict]] = {}
        for topic in topics:
            # Untranslated shelves are skipped rather than shown in English —
            # a chip with no title in this language has nothing to render.
            if not topic.is_translated_into(lang):
                continue
            chip = {"slug": topic.slug, "title": topic.title_for(lang)}
            book_hits = [e.book_slug for e in topic.entries.all() if e.book_slug in book_slugs]
            for slug in book_hits:
                by_book.setdefault(slug, []).append(chip)
            sermon_hits = [
                e.sermon_slug
                for e in topic.sermon_entries.all()
                if e.sermon_slug in sermon_slugs
            ]
            for slug in sermon_hits:
                by_sermon.setdefault(slug, []).append(chip)
            if book_hits or sermon_hits:
                chips.append(chip)
        chips.sort(key=lambda c: c["title"])
        for book_chips in by_book.values():
            book_chips.sort(key=lambda c: c["title"])
        for sermon_chips in by_sermon.values():
            sermon_chips.sort(key=lambda c: c["title"])
        return chips, by_book, by_sermon

    def get_topics(self, obj):
        """The published topical shelves this author appears in — any topic
        that includes one of their published books or sermons in this language.
        Chips link back to the topic pages, so a reader can jump from an author
        to the themes their work sits under (cross-navigation into browse)."""
        return self._topic_pass(obj)[0]

    def get_appears_in(self, obj):
        """The books this person is found IN but did not write (BookPerson) —
        book cards, each carrying the ``role`` they play, so the bio can link
        out to those works. Published books in this language only (no English
        fallback), and a book they actually wrote is left out: it's already in
        ``books``, and showing it twice would read as a bug.

        Inline (not via ``_cached``): unlike books/sermons/topics, one field
        reads this set, so there's nothing to share it with."""
        lang = self._language()
        # Ordered by the person's curated BookPerson.sort_order (the model's
        # Meta ordering), so their appearances show in the order a curator set —
        # the reverse of featured_people honoring the same field.
        rows = list(obj.featured_in_books.all())
        if not rows:
            return []
        roles = {r.book_slug: r.role for r in rows}
        order = {r.book_slug: i for i, r in enumerate(rows)}
        books = (
            Book.objects.filter(slug__in=roles.keys(), is_published=True, language=lang)
            .exclude(author=obj)
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(**BOOK_CARD_ANNOTATIONS)
        )
        # Empty book_topics so BookListSerializer doesn't scan the whole topic
        # set again for this secondary section — the author's own book cards
        # already paid for one such walk (get_books). No topic chips on the
        # "appears in" cards is a fair price for not doubling that query.
        ctx = {**self.context, "book_topics": {}}
        data = BookListSerializer(books, many=True, context=ctx).data
        for card in data:
            card["role"] = roles.get(card["slug"])
        data.sort(key=lambda c: order.get(c["slug"], 0))
        return data


class ChapterTocSerializer(serializers.ModelSerializer):
    """A chapter's metadata for the table of contents (no body)."""

    class Meta:
        model = Chapter
        fields = ["order", "title", "word_count"]


class BookDetailSerializer(BookListSerializer):
    """Book detail — adds description, the chapter TOC, topic chips, and a
    "more like this" list of related books."""

    chapters = ChapterTocSerializer(many=True, read_only=True)
    topics = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()
    difficulty = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    public_domain = serializers.SerializerMethodField()
    # A parallel "Modern English" edition (language en-modern) can exist for an
    # English work; these let the reader offer a per-book toggle to it.
    is_modern_edition = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()
    # Other audience editions of the SAME work — the "(For Children)" /
    # "(For Teens)" retellings and the full text they retell — cross-linked both
    # ways. Detail only, like related: it is one extra query, nothing on a page
    # and 130× nothing a shelf shouldn't pay.
    editions = serializers.SerializerMethodField()
    # Where this edition sits in its series (see `series_block`); null outside one.
    series = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()
    artwork_credit = serializers.SerializerMethodField()
    # The author's authoritative identifiers, for the Person inside this page's
    # Book markup. NOT on AuthorSerializer, which draws cards: a card emits no
    # Person markup, so putting them there would ship the same handful of URLs
    # on all 130 rows of a shelf for nothing to read. Only the page that marks
    # the author up needs them.
    author_same_as = serializers.SerializerMethodField()
    # Other names this same work is published and searched under — see
    # library/alternate_titles.py. Detail only, for the same reason as
    # author_same_as: a card has no room to show them and no markup to carry
    # them, so a shelf would ship the strings 130 times over for nothing.
    alternate_titles = serializers.SerializerMethodField()
    # The API path of this edition's EPUB ("" = not downloadable), the twin of
    # ``pdf_url`` — see library/export_policy.py and library/book_export.py.
    epub_url = serializers.SerializerMethodField()
    # The passages this book keeps returning to, derived from its own text —
    # see library/scripture_graph.treated_passages. Detail only: it costs two
    # queries, which is nothing on one page and 130 times nothing on a shelf.
    scripture = serializers.SerializerMethodField()
    # The book's first paragraph of actual prose — see library/opening.py.
    # Detail only, and it is the one field here that reads chapter BODIES, so a
    # shelf carrying it would drag 130 books' HTML through the join.
    opening = serializers.SerializerMethodField()
    # The people found IN this work who have a bio of their own (BookPerson) —
    # chips linking to their author pages. Localized: only people with a bio in
    # THIS edition's language are shown, the usual no-English-fallback rule.
    featured_people = serializers.SerializerMethodField()
    # How many reviewed quotations this book's author has, so the page can show a
    # "Quotes from {author}" link (English only, as the quote pages are) when it
    # is non-zero. Detail-only like author_same_as: a card carries no such link,
    # so a shelf would run this count 130 times for nothing.
    author_quote_count = serializers.SerializerMethodField()
    # The reader's guide(s) for this work — published articles whose Read-next
    # funnel points back here (see ``guides_for_book``). The reverse of the
    # article→book funnel, so a reader landing on the book finds the guide that
    # explains it, and the guide gets an internal link from a high-value page.
    # Per-language, like everything else on the page. Detail-only: it scans the
    # article table, nothing a shelf should pay (pinned by
    # BookCardPayloadTests.test_book_detail_query_count_is_the_same_in_every_language).
    guides = serializers.SerializerMethodField()

    def get_guides(self, obj) -> list[dict]:
        # No language gate: guides_for_book already filters on this edition's
        # language. A blanket English-only gate here predated the translated
        # guide rows and suppressed all of them.
        return guides_for_book(obj.slug, obj.language)

    def get_author_same_as(self, obj):
        return obj.author.same_as or []

    def get_author_quote_count(self, obj) -> int:
        return obj.author.quotes.filter(reviewed=True).count()

    def get_alternate_titles(self, obj) -> list[str]:
        return alternate_titles(obj.slug, obj.language, obj.title)

    def get_opening(self, obj) -> dict | None:
        # Read body_html for only the few chapters an opening could come from,
        # never the whole book. obj.chapters is prefetched TOC-only (bodies
        # deferred) by BookDetailView, so a fresh ``values_list("body_html")``
        # here issues a NEW query that drags EVERY chapter's HTML out of Postgres
        # to render one paragraph — the exact per-book egress that prefetch
        # exists to avoid, paid again on every crawl of every book URL (the
        # 2026-08-14 OOM was this shape). Titles pick the candidates off the
        # prefetch (no query, and already in `order` sequence via Chapter.Meta,
        # like the TOC field beside it); bodies are fetched for those orders alone.
        meta = [(c.order, c.title) for c in obj.chapters.all()]
        wanted = opening_candidate_orders(meta)
        if not wanted:
            return None
        rows = (
            obj.chapters.filter(order__in=wanted)
            .order_by("order")
            .values_list("order", "title", "body_html")
        )
        text, chapter = opening_excerpt(list(rows))
        return {"text": text, "chapter": chapter} if text else None

    def get_featured_people(self, obj) -> list[dict]:
        """The bios of people found in this work — {slug, name, photo_url,
        role}, in ``BookPerson.sort_order``. Language-gated: a person with no
        bio in this edition's language has nothing to link to here, so they're
        omitted (like an untranslated topic chip).

        ``role`` is carried for a UI that phrases the relationship ("the subject
        of", "mentioned in"); the reader doesn't render it yet, so it's the
        curated data made available, not a live label — see BookPerson."""
        lang = obj.language
        rows = (
            BookPerson.objects.filter(book_slug=obj.slug)
            .select_related("person")
            .prefetch_related("person__translations")
        )
        out = []
        for row in rows:
            person = row.person
            if not person.has_bio_in(lang):
                continue
            out.append(
                {
                    "slug": person.slug,
                    "name": person.name,
                    "photo_url": person.photo_url,
                    "birth_year": person.birth_year,
                    "death_year": person.death_year,
                    "role": row.role,
                }
            )
        return out

    def get_scripture(self, obj) -> list[dict]:
        # English only. The citation index is built from English bodies
        # (`english_citation_rows`), so a translated edition has no rows of its
        # own — and answering from the English book's would put English chapter
        # counts on a Swahili page and link into a graph that has no Swahili
        # pages to land on.
        if obj.language != "en":
            return []
        return treated_passages(obj.pk)

    # How many related books to surface, and how much a shared topic counts
    # relative to sharing the author (a shared topic is the stronger signal).
    RELATED_LIMIT = 6
    TOPIC_WEIGHT = 2
    AUTHOR_WEIGHT = 1

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "description", "source_url", "pdf_url", "chapters",
            "publication_year", "attribution", "topics", "related",
            "difficulty", "is_modern_edition", "has_modern_edition",
            "editions", "available_languages", "artwork_credit", "author_same_as",
            "alternate_titles", "about_html", "qa", "scripture", "opening",
            "featured_people", "author_quote_count", "guides", "series",
            "epub_url", "meta_description", "public_domain",
        ]

    def get_public_domain(self, obj) -> bool:
        """Whether the page may mark this edition public domain in its JSON-LD
        (``library/rights``)."""
        return is_public_domain(obj)

    def get_meta_description(self, obj) -> str:
        """The hand-written search snippet (``library/meta_descriptions``), or
        ``""`` — the page then trims ``description`` as before."""
        return meta_description(obj.slug, obj.language)

    def get_epub_url(self, obj) -> str:
        if not is_exportable(obj):
            return ""
        return f"{reverse('book-epub', args=[obj.slug])}?language={obj.language}"

    def get_editions(self, obj):
        """Sibling audience editions (full ⇄ teens ⇄ children) as cover cards,
        so a reader who lands on the full text finds the young-reader retelling
        and vice versa. Empty for the vast majority of works, which have no
        retelling — the section then simply doesn't render.

        Pass an empty ``book_topics`` so the card serializer returns no topic
        chips without building the shelf-wide topic map: the edition cards don't
        render chips, and get_related already pays for its own map build on the
        same page — one is enough."""
        rows = sibling_editions(obj)
        context = {**self.context, "book_topics": {}}
        return BookListSerializer(rows, many=True, context=context).data

    def get_available_languages(self, obj):
        return _available_languages(Book, obj.slug)

    def get_series(self, obj):
        return series_block(obj)

    def get_artwork_credit(self, obj) -> str | None:
        """Who painted the cover art, for the books that wear a real painting.

        The credit used to sit in the composited SVG's ``<desc>``, where no
        reader saw it and no screen reader announced it. The painting is now a
        plain image with the type drawn over it in HTML, so the credit needs
        somewhere real to live — and it should be somewhere real regardless:
        every collection these come from releases CC0, so attribution is not
        required of us, but crediting the painter is right and it lets a reader
        check the provenance ``curated_art`` records. Which institution it names
        is the manifest's to say — there is more than one now.
        """
        # Keyed on the cover this edition actually wears, not on the manifest:
        # the fixture gate deliberately allows an edition to carry designed
        # artwork of its own, and crediting a painter for a cover nobody is
        # looking at is worse than saying nothing.
        if not (obj.cover_url or "").startswith("/covers/art/"):
            return None
        return credit(obj.slug)

    def get_difficulty(self, obj):
        """A relative reading-difficulty badge, sampled from the opening
        chapters. Fetched as its own tiny query rather than from the chapters
        prefetch: the prefetch deliberately carries TOC fields only (see
        BookDetailView), so reading body_text off those rows would issue one
        deferred-field query per chapter — and prefetching bodies for all
        chapters is exactly the whole-book-in-memory allocation this replaced."""
        from .readability import difficulty

        text = " ".join(
            obj.chapters.order_by("order").values_list("body_text", flat=True)[:5]
        )
        return difficulty(text)

    def get_is_modern_edition(self, obj):
        return obj.language == MODERN_LANGUAGE

    def get_has_modern_edition(self, obj):
        if obj.language == MODERN_LANGUAGE:
            return True
        if obj.language != "en":
            return False
        return _modern_edition_available(obj.slug)

    def get_topics(self, obj):
        """Published topics this work belongs to, localized to the book's
        language — small chips linking to each topical shelf."""
        return _topic_chips(obj.language, entries__book_slug=obj.slug)

    def get_related(self, obj):
        """"More like this" — other books in the same language ranked by how
        many topics they share with this one (the strong signal), then a boost
        for being by the same author. Books present only in another language are
        excluded, so every suggestion is one the reader can open here."""
        scores: dict[str, int] = {}

        # Shared-topic overlap: how many of this work's topics each other work
        # also sits in. (topic, book_slug) is unique, so each row is one topic.
        topic_ids = list(
            TopicBook.objects.filter(book_slug=obj.slug).values_list("topic_id", flat=True)
        )
        if topic_ids:
            overlaps = (
                TopicBook.objects.filter(topic_id__in=topic_ids)
                .exclude(book_slug=obj.slug)
                .values("book_slug")
                .annotate(shared=Count("topic_id", distinct=True))
            )
            for row in overlaps:
                scores[row["book_slug"]] = row["shared"] * self.TOPIC_WEIGHT

        # Same-author boost — limited to works published in this language.
        author_slugs = (
            Book.objects.filter(
                author_id=obj.author_id, language=obj.language, is_published=True
            )
            .exclude(slug=obj.slug)
            .values_list("slug", flat=True)
        )
        for slug in author_slugs:
            scores[slug] = scores.get(slug, 0) + self.AUTHOR_WEIGHT

        # A young-reader edition of THIS work shares its author (and often its
        # topics), so it would surface here as "more like this" — but it is the
        # same work, already shown in its own "Other editions" section above. Drop
        # the whole edition family so a card never appears twice on the page.
        for slug in _edition_family(_edition_base_slug(obj.slug)):
            scores.pop(slug, None)

        if not scores:
            return []

        candidates = (
            Book.objects.filter(
                slug__in=scores.keys(), language=obj.language, is_published=True
            )
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(**BOOK_CARD_ANNOTATIONS)
        )
        ranked = sorted(
            candidates, key=lambda b: (-scores.get(b.slug, 0), b.sort_order, b.title)
        )
        top = ranked[: self.RELATED_LIMIT]
        data = BookListSerializer(top, many=True, context=self.context).data

        # Why each work is suggested, so the page can label it: another book by
        # the same author, else one that shares a topic shelf. Only the reason
        # KIND (and, for a topic, its slug) is returned — the page composes the
        # visible label from data it already holds (the card's own author name,
        # the book's localized topic titles), so this stays language-agnostic and
        # adds no query per candidate. Same-author wins when a work is both, as it
        # is the clearer label. One extra query, over only the works returned.
        author_set = set(author_slugs)
        shared_topic: dict[str, str] = {}
        if topic_ids:
            rows = (
                TopicBook.objects.filter(
                    topic_id__in=topic_ids, book_slug__in=[b.slug for b in top]
                )
                .exclude(book_slug=obj.slug)
                .values_list("book_slug", "topic__slug")
            )
            for bslug, tslug in rows:
                shared_topic.setdefault(bslug, tslug)
        for item in data:
            slug = item["slug"]
            if slug in author_set:
                item["reason"] = {"kind": "author"}
            elif slug in shared_topic:
                item["reason"] = {"kind": "topic", "topic": shared_topic[slug]}
            else:
                item["reason"] = None
        return data


class ChapterDetailSerializer(serializers.ModelSerializer):
    """A single chapter with its full body and prev/next navigation."""

    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    body_html = serializers.SerializerMethodField()
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    author_name = serializers.CharField(source="book.author.name", read_only=True)
    author_slug = serializers.CharField(source="book.author.slug", read_only=True)
    # The book's review state, so the reader can badge an unreviewed AI
    # translation — a whole chapter of one would otherwise read as an original
    # (CLAUDE.md). Chapters are per-language rows under a per-language Book, so
    # book.source_type IS this edition's.
    source_type = serializers.CharField(source="book.source_type", read_only=True)
    # Lets the reader show the Modern English ⇄ Original toggle in place.
    is_modern_edition = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()
    # The book's published locales, so the chapter page advertises hreflang only
    # for translations that exist at this same chapter URL (per-language rows,
    # no English fallback). Chapter counts match across a book's translations.
    available_languages = serializers.SerializerMethodField()

    scripture_refs = serializers.SerializerMethodField()

    # The book's rights, for the chapter's JSON-LD `license` (library/rights).
    public_domain = serializers.SerializerMethodField()

    def get_public_domain(self, obj) -> bool:
        # One answer per book per request: a batch run serializes many chapters
        # of the same edition, and the rule may query the English row.
        memo = self.context.setdefault("_public_domain", {})
        if obj.book_id not in memo:
            memo[obj.book_id] = is_public_domain(obj.book)
        return memo[obj.book_id]

    def get_scripture_refs(self, obj):
        """The passages this chapter treats, and where each one has a page.

        The sermon page has carried this row since citations were indexed; book
        chapters — 1,264 of them, the bulk of the library — never had it. It is
        the cheapest thing that makes a chapter page unlike every other copy of
        the same public-domain text: the body is Bunyan's and everyone has it,
        but which passages this chapter engages is DERIVED from our own citation
        index and is ours.

        `page` is null unless a scripture page really exists for that reference
        — the reader must never be handed a link to a page the citation floor
        deliberately withheld, and the crawler must never be handed a dead one.

        ENGLISH ONLY, because the citations are. `extract_citations` validates
        against pythonbible's English book names, so a translated edition yields
        a handful of residual English strings and nothing else; the scripture
        pages those chips point at are English too. Running the row on a Spanish
        chapter would offer a reader two or three stray references and call it
        an index.
        """
        return self._batch(obj).scripture_refs(obj)

    def get_available_languages(self, obj):
        return self._batch(obj).available_languages

    def get_body_html(self, obj):
        return _link_scripture(obj.body_html, links=self._batch(obj).scripture_links)

    def get_is_modern_edition(self, obj):
        return obj.book.language == MODERN_LANGUAGE

    def get_has_modern_edition(self, obj):
        return self._batch(obj).has_modern_edition

    class Meta:
        model = Chapter
        fields = [
            "order", "title", "body_html", "word_count",
            "book_title", "book_slug", "author_name", "author_slug",
            "is_modern_edition", "has_modern_edition", "available_languages",
            "source_type", "public_domain",
            "prev", "next",
            # The scripture index row at the foot of the chapter — see above.
            "scripture_refs",
        ]

    def _batch(self, obj):
        """The run's shared lookups: ChapterBatchView supplies one for the whole
        run; a single chapter is a run of one."""
        batch = self.context.get("chapter_batch")
        if batch is None or not batch.holds(obj):
            batch = self.context["chapter_batch"] = ChapterBatch(obj.book, [obj])
        return batch

    def get_prev(self, obj):
        return self._batch(obj).siblings.get(obj.order - 1)

    def get_next(self, obj):
        return self._batch(obj).siblings.get(obj.order + 1)


class ChapterBatch:
    """What a run of one book edition's chapters shares, looked up once.

    ChapterDetailSerializer reads every per-book field from here, so the single
    and batch endpoints (ChapterBatchView) are one code path. The scripture
    lookup covers the union of the run's references in ONE ``pages_for`` call.
    A superset is safe: each chapter only reads its own references, and
    ``pages_for`` answers a reference the same whatever else is asked alongside
    it (a citation row is fetched when it overlaps the reference's Bible
    chapter, whichever other chapters are in the query).
    """

    def __init__(self, book, chapters):
        from .scripture import cited_references, reference_candidates
        from .scripture_graph import page_url, pages_for

        self.available_languages = _available_languages(Book, book.slug)
        if book.language == MODERN_LANGUAGE:
            self.has_modern_edition = True
        else:
            self.has_modern_edition = book.language == "en" and _modern_edition_available(
                book.slug
            )
        orders = [c.order for c in chapters]
        self.siblings = (
            {
                row["order"]: row
                for row in Chapter.objects.filter(
                    book=book, order__gte=min(orders) - 1, order__lte=max(orders) + 1
                ).values("order", "title")
            }
            if orders
            else {}
        )
        # English only — see ChapterDetailSerializer.get_scripture_refs.
        self._cited = {
            c.pk: cited_references(c.body_html) if book.language == "en" else []
            for c in chapters
        }
        candidates = [ref for c in chapters for ref in reference_candidates(c.body_html)]
        refs = [ref for cited in self._cited.values() for ref in cited]
        pages = pages_for(list(dict.fromkeys(candidates + refs)))
        self.scripture_links = {
            ref: page_url(pages[ref]) for ref in candidates if pages.get(ref)
        }
        self._pages = pages

    def holds(self, chapter) -> bool:
        return chapter.pk in self._cited

    def scripture_refs(self, chapter):
        return [{"ref": r, "page": self._pages.get(r)} for r in self._cited[chapter.pk]]


class PlanListSerializer(serializers.ModelSerializer):
    """Plans index — enough for a browse card."""

    day_count = serializers.IntegerField(source="num_days", read_only=True)
    total_words = serializers.SerializerMethodField()
    covers = serializers.SerializerMethodField()
    day_one = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "slug", "language", "title", "description", "day_count",
            "total_words", "covers", "day_one",
        ]

    def _chapters(self, obj):
        """The page-wide chapter index, or one built for this plan alone.

        The view puts it in the context so a shelf of plans costs one query
        rather than one per plan. The fallback keeps any other caller — and the
        serializer used directly — working, at the old cost.
        """
        index = self.context.get("plan_chapters")
        if index is None:
            index = plan_chapter_index([obj], obj.language)
            self.context["plan_chapters"] = index
        return index

    def _books(self, obj):
        index = self.context.get("plan_books")
        if index is None:
            index = plan_book_index([obj], obj.language)
            self.context["plan_books"] = index
        return index

    def get_total_words(self, obj):
        return _plan_total_words(obj, self._chapters(obj))

    def get_covers(self, obj):
        return _plan_covers(obj, self._books(obj))

    def get_day_one(self, obj):
        return _plan_day_one(obj, self._chapters(obj))


def plan_chapter_index(plans, language):
    """``{(book_slug, order): chapter values}`` for every day of every plan.

    ONE query for a whole page. The three plan card fields — total words, day
    one, the cover strip — plus the detail page's day list all need the same
    chapters, and each used to fetch them itself: three queries per plan on the
    shelf (a 3N+1), and four overlapping ones on the detail page.

    Carries every column any of those four needs, so they read a dict instead of
    the database. Same shape ``get_days`` already built for itself.
    """
    pairs = {(d.book_slug, d.chapter_order) for plan in plans for d in plan.days.all()}
    if not pairs:
        return {}
    slugs = {slug for slug, _ in pairs}
    return {
        (c["book__slug"], c["order"]): c
        for c in Chapter.objects.filter(
            book__slug__in=slugs, book__language=language
        ).values("book__slug", "book__title", "order", "title", "word_count")
    }


def plan_book_index(plans, language):
    """``{slug: Book}`` for every book any of these plans draws from — one query."""
    slugs = {d.book_slug for plan in plans for d in plan.days.all()}
    if not slugs:
        return {}
    # select_related the author so a plan can name the writers it reads through
    # (PlanDetailSerializer.get_authors) without an N+1; the covers/day fields
    # ignore it, at the cost of one join.
    return {
        b.slug: b
        for b in Book.objects.filter(slug__in=slugs, language=language).select_related(
            "author"
        )
    }


def _plan_total_words(plan, chapters):
    """Sum the word counts of every day's chapter, from a prebuilt index."""
    return sum(
        (chapters.get((d.book_slug, d.chapter_order)) or {}).get("word_count", 0)
        for d in plan.days.all()
    )


def _plan_day_one(plan, chapters):
    """Day 1's book + chapter titles, so a card can say where the plan starts.

    Days are prefetched and ordered by day, so ``days.all()[0]`` is day one.
    """
    days = list(plan.days.all())
    if not days:
        return None
    first = days[0]
    chapter = chapters.get((first.book_slug, first.chapter_order))
    if chapter is None:
        return None
    return {"book_title": chapter["book__title"], "chapter_title": chapter["title"]}


def _book_cover(book):
    """A book as a strip tile. Shared by the plan strip, the topic fan and the
    series fan so the payloads cannot drift — `kind`/`slug` were once on the
    topic side only, which is what forced the frontend type to make them
    optional. The rest is ``cover_face``: what the thumbnail's type needs."""
    return {"kind": "book", **cover_face(book)}


def _plan_covers(plan, books, limit=5):
    """The distinct books a plan draws from (first-appearance order), as small
    cover descriptors — mirrors a topic's covers strip. Reads a prebuilt index."""
    order = []
    for d in plan.days.all():
        if d.book_slug not in order:
            order.append(d.book_slug)
    if not order:
        return []
    covers = []
    for slug in order:
        b = books.get(slug)
        if b:
            covers.append(_book_cover(b))
        if len(covers) >= limit:
            break
    return covers


class PlanDaySerializer(serializers.ModelSerializer):
    """One day's reading, enriched with display titles for the linked chapter."""

    book_title = serializers.CharField(read_only=True, default="")
    chapter_title = serializers.CharField(read_only=True, default="")
    word_count = serializers.IntegerField(read_only=True, default=0)
    # A published Modern English edition of the day's book exists — so the
    # reader's "Prefer Modern English" can be honoured on the day's link.
    has_modern_edition = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = PlanDay
        fields = [
            "day", "book_slug", "chapter_order", "book_title", "chapter_title",
            "word_count", "has_modern_edition",
        ]


class PlanDetailSerializer(PlanListSerializer):
    days = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()

    class Meta(PlanListSerializer.Meta):
        fields = PlanListSerializer.Meta.fields + [
            "days",
            "available_languages",
            "authors",
        ]

    def get_available_languages(self, obj):
        return _available_languages(Plan, obj.slug)

    def get_authors(self, obj):
        """The distinct writers this plan reads through, in the order their books
        first appear across the days — a link out to each author page, so a plan
        is a way into their work, not only a sequence of chapters. Reads the
        page-wide book index (author select_related), so no extra query."""
        books = self._books(obj)
        authors: list[dict] = []
        seen: set[str] = set()
        for day in obj.days.all():
            book = books.get(day.book_slug)
            if book and book.author.slug not in seen:
                seen.add(book.author.slug)
                authors.append({"slug": book.author.slug, "name": book.author.name})
        return authors

    def get_days(self, obj):
        days = list(obj.days.all())
        # The same lookup the card fields need, so it is built once for the
        # whole response rather than a fourth time here.
        lookup = self._chapters(obj)
        # Modern English is an English edition: a plan in any other language
        # links its own translations, never it.
        modern = (
            set(
                Book.objects.filter(
                    slug__in={d.book_slug for d in days},
                    language=MODERN_LANGUAGE,
                    is_published=True,
                ).values_list("slug", flat=True)
            )
            if obj.language == "en"
            else set()
        )
        for d in days:
            c = lookup.get((d.book_slug, d.chapter_order))
            d.book_title = c["book__title"] if c else ""
            d.chapter_title = c["title"] if c else ""
            d.word_count = c["word_count"] if c else 0
            d.has_modern_edition = d.book_slug in modern
        return PlanDaySerializer(days, many=True).data


class TopicListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """A topical shelf card — localized title/description, member count, and a
    handful of member covers for the browse page. ``book_count`` and ``covers``
    are computed against the requested language (see ``TopicListView``)."""

    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    book_count = serializers.SerializerMethodField()
    sermon_count = serializers.SerializerMethodField()
    covers = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ["slug", "title", "description", "book_count", "sermon_count", "covers"]

    def get_title(self, obj):
        return obj.title_for(self._language())

    def get_description(self, obj):
        return obj.description_for(self._language())

    def get_book_count(self, obj):
        return len(self._books(obj))

    def get_sermon_count(self, obj):
        return len(self._sermons(obj))

    def get_covers(self, obj):
        """Up to four member tiles for the card's fan — books first, then sermons.

        Sermons are here because the shelf is LISTED when it has books or
        sermons (`TopicListView.get_queryset`) while this drew only books, so a
        shelf whose members in this language are sermons was published with an
        empty band. Books first, so a shelf that can fill the fan with covers
        still looks exactly as it did.

        A sermon tile is not a cover — `ShelfCard` draws it as the round emblem
        chip a sermon wears elsewhere. It carries the SLUG and nothing about the
        art: which emblem, and the hue derived from it, live in the frontend
        catalogue the API cannot see.
        """
        tiles = [_book_cover(b) for b in self._books(obj)] + [
            {"kind": "sermon", "slug": s.slug, "title": s.title}
            for s in self._sermons(obj)
        ]
        # Four is what `.cover-fan` lays out before it overflows its band.
        return tiles[:4]

    def _books(self, obj):
        """Member books present in the requested language, in the topic's curated
        order. ``obj.books_in_language`` is attached by the view (one query for
        all topics); fall back to a direct query if it isn't."""
        cached = getattr(obj, "books_in_language", None)
        if cached is not None:
            return cached
        from django.db.models import Count, Sum

        from .models import Book

        order = [e.book_slug for e in obj.entries.all()]
        by_slug = {
            b.slug: b
            for b in Book.objects.filter(
                slug__in=order, language=self._language(), is_published=True
            )
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(num_chapters=Count("chapters"), total_words=Sum("chapters__word_count"))
        }
        return [by_slug[s] for s in order if s in by_slug]

    def _sermons(self, obj):
        """Member sermons present in the requested language, in curated order.
        ``sermons_in_language`` is attached by the view; fall back to a query."""
        cached = getattr(obj, "sermons_in_language", None)
        if cached is not None:
            return cached
        from .models import Sermon

        order = [e.sermon_slug for e in obj.sermon_entries.all()]
        by_slug = {
            s.slug: s
            for s in Sermon.objects.filter(
                slug__in=order, language=self._language(), is_published=True
            )
            .select_related("author")
            # author__translations was missing here alone: AuthorSerializer.get_bio
            # reads them, so this fallback N+1'd one query per sermon.
            .prefetch_related("author__translations")
            .defer(*SERMON_CARD_DEFER)
        }
        return [by_slug[s] for s in order if s in by_slug]

    def _articles(self, obj):
        """Member articles present in the requested language, in curated order.
        ``articles_in_language`` is attached by the view; fall back to a query."""
        cached = getattr(obj, "articles_in_language", None)
        if cached is not None:
            return cached
        from .models import Article

        order = [e.article_slug for e in obj.article_entries.all()]
        by_slug = {
            a.slug: a
            for a in Article.objects.filter(
                slug__in=order, language=self._language(), is_published=True
            ).defer("body_html")
        }
        return [by_slug[s] for s in order if s in by_slug]


# How many sibling shelves a topic page offers under "Related topics". Mirrors
# RELATED_LIMIT (the book page's "More like this"): enough to explore, not a wall.
RELATED_TOPIC_LIMIT = 6


class TopicDetailSerializer(TopicListSerializer):
    """A topic page — the shelf metadata plus the full list of member books."""

    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    related_topics = serializers.SerializerMethodField()
    scripture_ref = serializers.SerializerMethodField()
    scripture_text = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    qa = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            "scripture_ref",
            "scripture_text",
            "seo_title",
            "meta_description",
            "qa",
            "available_languages",
            "books",
            "sermons",
            "articles",
            "authors",
            "related_topics",
        ]

    def get_available_languages(self, obj):
        """Locales this shelf actually exists in — for hreflang.

        Matches Book.available_languages in purpose: the page 404s in a locale
        with no translated title (TopicDetailView), so advertising an alternate
        there would point search engines at a missing page.
        """
        langs = ["en"] if obj.title.strip() else []
        langs += sorted(
            t.language for t in obj.translations.all() if t.title.strip() and t.language != "en"
        )
        return langs

    def get_scripture_ref(self, obj):
        return obj.scripture_ref_for(self._language())

    def get_scripture_text(self, obj):
        return obj.scripture_text_for(self._language())

    def get_seo_title(self, obj):
        return obj.seo_title_for(self._language())

    def get_meta_description(self, obj):
        return obj.meta_description_for(self._language())

    def get_qa(self, obj):
        return obj.qa_for(self._language())

    def get_books(self, obj):
        return BookListSerializer(self._books(obj), many=True, context=self.context).data

    def get_sermons(self, obj):
        return SermonListSerializer(self._sermons(obj), many=True, context=self.context).data

    def get_articles(self, obj):
        # The cards' lead books from THIS topic's articles only — the shelf-wide
        # fallback would resolve every article in the language for a handful.
        articles = self._articles(obj)
        lead_books = lead_book_cards({a.slug: a.related for a in articles}, self._language())
        return ArticleListSerializer(
            articles, many=True, context={**self.context, "article_lead_books": lead_books}
        ).data

    def get_authors(self, obj):
        """The distinct authors behind this shelf's books and sermons, in the
        shelf's curated order (books first, then sermons). A shelf's authors are
        a strong lateral link — a reader here often wants more of a voice, not
        only more of the theme. Zero extra queries: the works are already loaded
        with their author (``_attach_books`` / ``_attach_sermons`` select it)."""
        seen: dict[str, dict] = {}
        for work in list(self._books(obj)) + list(self._sermons(obj)):
            author = work.author
            if author and author.slug not in seen:
                seen[author.slug] = {
                    "slug": author.slug,
                    "name": author.name,
                    "photo_url": author.photo_url,
                    "birth_year": author.birth_year,
                    "death_year": author.death_year,
                }
        return list(seen.values())

    def get_related_topics(self, obj):
        """Sibling shelves that share books with this one, most-shared first.

        Overlap is over ``TopicBook`` membership (``idx_topicbook_slug`` serves
        the ``book_slug`` lookup). Constant queries — one aggregate, one fetch —
        never one per candidate. Only shelves with a title in this language are
        offered, so a chip never leads to a 404 (a topic 404s in a locale it
        isn't translated into; see ``TopicDetailView``)."""
        from django.db.models import Count

        from .models import Topic, TopicBook

        book_slugs = [e.book_slug for e in obj.entries.all()]
        if not book_slugs:
            return []
        rows = list(
            TopicBook.objects.filter(book_slug__in=book_slugs)
            .exclude(topic_id=obj.id)
            .values("topic_id")
            .annotate(shared=Count("book_slug"))
            .order_by("-shared", "topic_id")
        )
        if not rows:
            return []
        language = self._language()
        by_id = {
            t.id: t
            for t in Topic.objects.filter(
                id__in=[r["topic_id"] for r in rows], is_published=True
            ).prefetch_related("translations")
        }
        related: list[dict] = []
        for row in rows:
            topic = by_id.get(row["topic_id"])
            if topic and topic.is_translated_into(language):
                related.append({"slug": topic.slug, "title": topic.title_for(language)})
                if len(related) >= RELATED_TOPIC_LIMIT:
                    break
        return related
