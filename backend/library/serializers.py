import re

from django.db.models import Count, Sum
from django.utils.text import slugify
from rest_framework import serializers

from .alternate_titles import alternate_titles
from .contemporize import MODERN_LANGUAGE
from .curated_art import credit
from .localization import language_from_request
from .models import (
    SERMON_CARD_DEFER,
    Article,
    Author,
    Book,
    BookPerson,
    Chapter,
    Plan,
    PlanDay,
    Sermon,
    Topic,
    TopicBook,
)
from .opening import opening_excerpt
from .scripture import book_of
from .scripture_graph import treated_passages


def _link_scripture(body_html: str) -> str:
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

    return annotate_references(
        body_html, links=scripture_links(reference_candidates(body_html))
    )

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


def _available_languages(model, slug: str) -> list[str]:
    """Sorted content locales this work is published in — for hreflang.

    Books/sermons/plans are per-language rows with no English fallback, so a
    detail page must advertise ``<link rel="alternate" hreflang>`` only for the
    locales that actually have a row. Advertising every locale unconditionally
    (the old behaviour) points crawlers at localized URLs that soft-404. The
    Modern English edition (``en-modern``) is an in-page toggle, not a
    browsable locale, so it's excluded.
    """
    return sorted(
        model.objects.filter(slug=slug, is_published=True)
        .exclude(language=MODERN_LANGUAGE)
        .values_list("language", flat=True)
        .distinct()
    )


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

    class Meta:
        model = Book
        fields = [
            "slug",
            "language",
            "title",
            "subtitle",
            "author",
            "source_type",
            "cover_color",
            "cover_url",
            "chapter_count",
            "word_count",
            "topics",
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


class SermonListSerializer(serializers.ModelSerializer):
    """A sermon card — enough for the shelf and the author page (no body)."""

    author = AuthorSerializer(read_only=True)
    # Which Bible book the sermon's text is from, for the shelf's book facet
    # ("Malachi", canonical position 39). Null for unparseable/localized refs
    # ("" included — book_of returns None). lru_cached, so the paired calls
    # per row cost one parse total.
    scripture_book = serializers.SerializerMethodField()
    scripture_book_order = serializers.SerializerMethodField()

    def get_scripture_book(self, obj):
        info = book_of(obj.scripture_ref)
        return info[0] if info else None

    def get_scripture_book_order(self, obj):
        info = book_of(obj.scripture_ref)
        return info[1] if info else None

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

    def get_difficulty(self, obj):
        from .readability import difficulty

        return difficulty(obj.body_text)

    def get_body_html(self, obj):
        # Wrap Bible references as clickable spans (the reader's scripture
        # popover) and link the ones with a scripture page (a crawlable
        # internal link), the same treatment chapters get.
        return _link_scripture(obj.body_html)

    scripture_refs = serializers.SerializerMethodField()

    def get_scripture_refs(self, obj):
        """The distinct passages this sermon engages — its text first, then
        references cited in the body — for the scripture-index chip row. The
        main text is deduped against body citations by verse overlap so
        "Mark 9:23" doesn't appear twice under two spellings."""
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
        return refs[:8]

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
            "author_name",
            "author_slug",
            "author_photo",
            "prev",
            "next",
            "scripture_refs",
            "summary",
            "difficulty",
            "topics",
            "available_languages",
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

    ``related`` is a hand-authored JSON field with no schema, so a malformed
    entry (a bare slug string, a non-list) is skipped rather than 500-ing the
    page. Validated entries are collected once, in order, and reused for both
    the batched lookup and the final card list.
    """
    entries: list[tuple[str, str]] = []  # (kind, slug), in order, validated
    for item in related if isinstance(related, list) else []:
        if not isinstance(item, dict):
            continue
        slug, kind = item.get("slug"), item.get("type")
        if slug and kind in ("book", "sermon", "author"):
            entries.append((kind, slug))

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


class ArticleListSerializer(LocalizedMixin, serializers.ModelSerializer):
    """An article card — enough for the /articles index (no body).

    Carries ``word_count`` (the "N min read" estimate) and ``topics`` (the
    index's filter tabs and the funnel back to the topic pages), so the card
    matches the book/sermon shelf cards rather than being a bare title.
    """

    topics = serializers.SerializerMethodField()

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
        ]


class ArticleDetailSerializer(ArticleListSerializer):
    """A single article with its body and its resolved "Read next" links."""

    body_html = serializers.SerializerMethodField()
    toc = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

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
    # Books this person is FOUND IN but did not write (BookPerson) — the reverse
    # of BookDetailSerializer.featured_people, so a bio can offer "appears in".
    appears_in = serializers.SerializerMethodField()

    # Present so AuthorDetail honours the AuthorBio contract the list shares;
    # the detail page already has the full sermons array + bio_html, so these
    # are just the summary numbers.
    sermon_count = serializers.SerializerMethodField()
    has_long_bio = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            "slug", "name", "bio", "bio_html", "bio_source_type", "photo_url",
            # Portrait credit — only the detail page renders it (a card shows the
            # thumbnail without a caption, which the CC licences allow because
            # every card links here, so the credit is one click from any
            # thumbnail). A non-linking reuse of a portrait (an OG/share image,
            # an email digest) would have to carry the credit with it.
            "photo_attribution", "photo_source_url", "birth_year",
            "death_year", "book_count", "sermon_count", "has_long_bio",
            "books", "sermons", "topics", "appears_in",
            # Authoritative identifiers for the Person markup — see the field.
            # Only the DETAIL serializer carries them: a card never emits
            # Person markup, so shipping them on every book row would be bytes
            # nothing reads.
            "same_as",
            # How many REVIEWED quotations this author has, so the page can
            # offer the quote page only when one exists. Counting unreviewed
            # rows would link to a page the review gate keeps 404ing.
            "quote_count",
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

    def get_sermon_count(self, obj):
        return len(self._sermons(obj))

    def get_has_long_bio(self, obj):
        return bool(obj.bio_html_for(self._language()).strip())

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
        return SermonListSerializer(
            self._sermons(obj), many=True, context=self.context
        ).data

    def _topic_pass(self, obj):
        """One walk over published topics, serving both chip fields.

        Returns ``(author chips, book_slug -> chips)``: the shelves this author
        appears in, and the per-book map the nested cards need. Two fields want
        the same topic rows, so they share one fetch — otherwise the author page
        would pull the whole topic set (plus its translations and both
        membership tables) twice.
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
            return [], {}
        topics = Topic.objects.filter(is_published=True).prefetch_related(
            "translations", "entries", "sermon_entries"
        )
        chips = []
        by_book: dict[str, list[dict]] = {}
        for topic in topics:
            # Untranslated shelves are skipped rather than shown in English —
            # a chip with no title in this language has nothing to render.
            if not topic.is_translated_into(lang):
                continue
            chip = {"slug": topic.slug, "title": topic.title_for(lang)}
            entries = [e.book_slug for e in topic.entries.all()]
            for slug in entries:
                if slug in book_slugs:
                    by_book.setdefault(slug, []).append(chip)
            in_topic = any(s in book_slugs for s in entries) or any(
                e.sermon_slug in sermon_slugs for e in topic.sermon_entries.all()
            )
            if in_topic:
                chips.append(chip)
        chips.sort(key=lambda c: c["title"])
        for book_chips in by_book.values():
            book_chips.sort(key=lambda c: c["title"])
        return chips, by_book

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
    # A parallel "Modern English" edition (language en-modern) can exist for an
    # English work; these let the reader offer a per-book toggle to it.
    is_modern_edition = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()
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

    def get_author_same_as(self, obj):
        return obj.author.same_as or []

    def get_alternate_titles(self, obj) -> list[str]:
        return alternate_titles(obj.slug, obj.language, obj.title)

    def get_opening(self, obj) -> dict | None:
        chapters = obj.chapters.order_by("order").values_list(
            "order", "title", "body_html"
        )
        text, chapter = opening_excerpt(list(chapters))
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
            "available_languages", "artwork_credit", "author_same_as",
            "alternate_titles", "about_html", "scripture", "opening",
            "featured_people",
        ]

    def get_available_languages(self, obj):
        return _available_languages(Book, obj.slug)

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
        from django.db.models import Count, Sum

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

        if not scores:
            return []

        candidates = (
            Book.objects.filter(
                slug__in=scores.keys(), language=obj.language, is_published=True
            )
            .select_related("author")
            .prefetch_related("author__translations")
            .annotate(num_chapters=Count("chapters"), total_words=Sum("chapters__word_count"))
        )
        ranked = sorted(
            candidates, key=lambda b: (-scores.get(b.slug, 0), b.sort_order, b.title)
        )
        return BookListSerializer(ranked[: self.RELATED_LIMIT], many=True, context=self.context).data


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
        from .scripture import cited_references
        from .scripture_graph import pages_for

        if obj.book.language != "en":
            return []
        refs = cited_references(obj.body_html)
        if not refs:
            return []
        pages = pages_for(refs)
        return [{"ref": r, "page": pages.get(r)} for r in refs]

    def get_available_languages(self, obj):
        return _available_languages(Book, obj.book.slug)

    def get_body_html(self, obj):
        return _link_scripture(obj.body_html)

    def get_is_modern_edition(self, obj):
        return obj.book.language == MODERN_LANGUAGE

    def get_has_modern_edition(self, obj):
        if obj.book.language == MODERN_LANGUAGE:
            return True
        if obj.book.language != "en":
            return False
        return _modern_edition_available(obj.book.slug)

    class Meta:
        model = Chapter
        fields = [
            "order", "title", "body_html", "word_count",
            "book_title", "book_slug", "author_name", "author_slug",
            "is_modern_edition", "has_modern_edition", "available_languages",
            "source_type",
            "prev", "next",
            # The scripture index row at the foot of the chapter — see above.
            "scripture_refs",
        ]

    def _sibling(self, obj, delta):
        sib = (
            Chapter.objects.filter(book=obj.book, order=obj.order + delta)
            .values("order", "title")
            .first()
        )
        return sib

    def get_prev(self, obj):
        return self._sibling(obj, -1)

    def get_next(self, obj):
        return self._sibling(obj, +1)


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
    return {b.slug: b for b in Book.objects.filter(slug__in=slugs, language=language)}


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
    """A book as a strip tile. Shared by the plan strip and the topic fan so the
    two payloads cannot drift — `kind`/`slug` were once on the topic side only,
    which is what forced the frontend type to make them optional."""
    return {
        "kind": "book",
        "slug": book.slug,
        "cover_url": book.cover_url,
        "cover_color": book.cover_color,
        "title": book.title,
    }


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

    class Meta:
        model = PlanDay
        fields = [
            "day", "book_slug", "chapter_order", "book_title", "chapter_title",
            "word_count",
        ]


class PlanDetailSerializer(PlanListSerializer):
    days = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta(PlanListSerializer.Meta):
        fields = PlanListSerializer.Meta.fields + ["days", "available_languages"]

    def get_available_languages(self, obj):
        return _available_languages(Plan, obj.slug)

    def get_days(self, obj):
        days = list(obj.days.all())
        # The same lookup the card fields need, so it is built once for the
        # whole response rather than a fourth time here.
        lookup = self._chapters(obj)
        for d in days:
            c = lookup.get((d.book_slug, d.chapter_order))
            d.book_title = c["book__title"] if c else ""
            d.chapter_title = c["title"] if c else ""
            d.word_count = c["word_count"] if c else 0
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


class TopicDetailSerializer(TopicListSerializer):
    """A topic page — the shelf metadata plus the full list of member books."""

    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()
    scripture_ref = serializers.SerializerMethodField()
    scripture_text = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            "scripture_ref",
            "scripture_text",
            "available_languages",
            "books",
            "sermons",
            "articles",
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

    def get_books(self, obj):
        return BookListSerializer(self._books(obj), many=True, context=self.context).data

    def get_sermons(self, obj):
        return SermonListSerializer(self._sermons(obj), many=True, context=self.context).data

    def get_articles(self, obj):
        return ArticleListSerializer(
            self._articles(obj), many=True, context=self.context
        ).data
