from rest_framework import serializers

from .contemporize import MODERN_LANGUAGE
from .models import Author, Book, Chapter, Plan, PlanDay, Sermon, Topic, TopicBook
from .scripture import book_of


def _modern_edition_available(slug: str) -> bool:
    """Whether a published Modern English edition of this work exists."""
    return Book.objects.filter(
        slug=slug, language=MODERN_LANGUAGE, is_published=True
    ).exists()


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["slug", "name", "bio", "photo_url", "birth_year", "death_year"]


class AuthorListSerializer(serializers.ModelSerializer):
    """Authors for the Biographies page, with how many books each has."""

    book_count = serializers.IntegerField(source="num_books", read_only=True)
    bio = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ["slug", "name", "bio", "photo_url", "birth_year", "death_year", "book_count"]

    def get_bio(self, obj):
        return obj.bio_for(self.context.get("language", "en"))


class BookListSerializer(serializers.ModelSerializer):
    """Shelf view — enough to render a cover card, no chapter bodies."""

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
        ]

    def get_topics(self, obj):
        """Published topics this book belongs to, for the shelf's topic filter.
        Served from a slug→chips map the view builds once (see
        ``BookListView.get_serializer_context``) so the shelf stays one query
        for topics regardless of how many books are on it."""
        return self.context.get("book_topics", {}).get(obj.slug, [])


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
            "preached_on",
            "word_count",
            "author",
        ]


class SermonDetailSerializer(serializers.ModelSerializer):
    """A single sermon with its full body, for the reader."""

    author_name = serializers.CharField(source="author.name", read_only=True)
    author_slug = serializers.CharField(source="author.slug", read_only=True)
    author_photo = serializers.CharField(source="author.photo_url", read_only=True)
    body_html = serializers.SerializerMethodField()

    def get_body_html(self, obj):
        # Wrap Bible references as clickable spans, so the reader's scripture
        # popover works in sermons too (same treatment chapters get).
        from .scripture import annotate_references

        return annotate_references(obj.body_html)

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
        ]


class AuthorDetailSerializer(serializers.ModelSerializer):
    """An author page: bio, dates, their books and their sermons in a language."""

    book_count = serializers.SerializerMethodField()
    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    bio_html = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            "slug", "name", "bio", "bio_html", "photo_url", "birth_year",
            "death_year", "book_count", "books", "sermons", "topics",
        ]

    def _language(self):
        return self.context.get("language", "en")

    def get_bio(self, obj):
        return obj.bio_for(self._language())

    def get_bio_html(self, obj):
        return obj.bio_html_for(self._language())

    def _books(self, obj):
        from django.db.models import Count

        return (
            obj.books.filter(is_published=True, language=self._language())
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .order_by("sort_order", "title")
        )

    def get_books(self, obj):
        return BookListSerializer(self._books(obj), many=True).data

    def get_book_count(self, obj):
        return self._books(obj).count()

    def get_sermons(self, obj):
        sermons = (
            obj.sermons.filter(is_published=True, language=self._language())
            .select_related("author")
            .order_by("sort_order", "title")
        )
        return SermonListSerializer(sermons, many=True).data

    def get_topics(self, obj):
        """The published topical shelves this author appears in — any topic
        that includes one of their published books or sermons in this language.
        Chips link back to the topic pages, so a reader can jump from an author
        to the themes their work sits under (cross-navigation into browse)."""
        from .models import Topic

        lang = self._language()
        book_slugs = set(self._books(obj).values_list("slug", flat=True))
        sermon_slugs = set(
            obj.sermons.filter(is_published=True, language=lang).values_list(
                "slug", flat=True
            )
        )
        if not book_slugs and not sermon_slugs:
            return []
        topics = Topic.objects.filter(is_published=True).prefetch_related(
            "translations", "entries", "sermon_entries"
        )
        chips = []
        for topic in topics:
            in_topic = any(
                e.book_slug in book_slugs for e in topic.entries.all()
            ) or any(e.sermon_slug in sermon_slugs for e in topic.sermon_entries.all())
            if in_topic:
                chips.append({"slug": topic.slug, "title": topic.title_for(lang)})
        chips.sort(key=lambda c: c["title"])
        return chips


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
    # A parallel "Modern English" edition (language en-modern) can exist for an
    # English work; these let the reader offer a per-book toggle to it.
    is_modern_edition = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()

    # How many related books to surface, and how much a shared topic counts
    # relative to sharing the author (a shared topic is the stronger signal).
    RELATED_LIMIT = 6
    TOPIC_WEIGHT = 2
    AUTHOR_WEIGHT = 1

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "description", "source_url", "pdf_url", "chapters",
            "publication_year", "attribution", "topics", "related",
            "is_modern_edition", "has_modern_edition",
        ]

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
        topics = (
            Topic.objects.filter(is_published=True, entries__book_slug=obj.slug)
            .prefetch_related("translations")
            .distinct()
            .order_by("sort_order", "title")
        )
        return [{"slug": t.slug, "title": t.title_for(obj.language)} for t in topics]

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
            .annotate(num_chapters=Count("chapters"), total_words=Sum("chapters__word_count"))
        )
        ranked = sorted(
            candidates, key=lambda b: (-scores.get(b.slug, 0), b.sort_order, b.title)
        )
        return BookListSerializer(ranked[: self.RELATED_LIMIT], many=True).data


class ChapterDetailSerializer(serializers.ModelSerializer):
    """A single chapter with its full body and prev/next navigation."""

    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    body_html = serializers.SerializerMethodField()
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    author_name = serializers.CharField(source="book.author.name", read_only=True)
    author_slug = serializers.CharField(source="book.author.slug", read_only=True)
    # Lets the reader show the Modern English ⇄ Original toggle in place.
    is_modern_edition = serializers.SerializerMethodField()
    has_modern_edition = serializers.SerializerMethodField()

    def get_body_html(self, obj):
        from .scripture import annotate_references

        return annotate_references(obj.body_html)

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
            "is_modern_edition", "has_modern_edition",
            "prev", "next",
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

    class Meta:
        model = Plan
        fields = [
            "slug", "language", "title", "description", "day_count",
            "total_words", "covers",
        ]

    def get_total_words(self, obj):
        return _plan_total_words(obj, obj.language)

    def get_covers(self, obj):
        return _plan_covers(obj, obj.language)


def _plan_total_words(plan, language):
    """Sum the word counts of every day's chapter for a plan (one query for the
    chapters; days are prefetched on the list, queried on detail)."""
    pairs = [(d.book_slug, d.chapter_order) for d in plan.days.all()]
    if not pairs:
        return 0
    slugs = {slug for slug, _ in pairs}
    wc = {
        (c["book__slug"], c["order"]): c["word_count"]
        for c in Chapter.objects.filter(
            book__slug__in=slugs, book__language=language
        ).values("book__slug", "order", "word_count")
    }
    return sum(wc.get(p, 0) for p in pairs)


def _plan_covers(plan, language, limit=5):
    """The distinct books a plan draws from (first-appearance order), as small
    cover descriptors — mirrors a topic's covers strip. One query for books."""
    order = []
    for d in plan.days.all():
        if d.book_slug not in order:
            order.append(d.book_slug)
    if not order:
        return []
    books = {
        b.slug: b
        for b in Book.objects.filter(slug__in=order, language=language)
    }
    covers = []
    for slug in order:
        b = books.get(slug)
        if b:
            covers.append(
                {"cover_url": b.cover_url, "cover_color": b.cover_color, "title": b.title}
            )
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

    class Meta(PlanListSerializer.Meta):
        fields = PlanListSerializer.Meta.fields + ["days"]

    def get_days(self, obj):
        days = list(obj.days.all())
        # Resolve chapter/book titles for every day in two queries, not 2N.
        slugs = {d.book_slug for d in days}
        chapters = Chapter.objects.filter(
            book__slug__in=slugs, book__language=obj.language
        ).values("book__slug", "book__title", "order", "title", "word_count")
        lookup = {(c["book__slug"], c["order"]): c for c in chapters}
        for d in days:
            c = lookup.get((d.book_slug, d.chapter_order))
            d.book_title = c["book__title"] if c else ""
            d.chapter_title = c["title"] if c else ""
            d.word_count = c["word_count"] if c else 0
        return PlanDaySerializer(days, many=True).data


class TopicListSerializer(serializers.ModelSerializer):
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

    def _language(self):
        return self.context.get("language", "en")

    def get_title(self, obj):
        return obj.title_for(self._language())

    def get_description(self, obj):
        return obj.description_for(self._language())

    def get_book_count(self, obj):
        return len(self._books(obj))

    def get_sermon_count(self, obj):
        return len(self._sermons(obj))

    def get_covers(self, obj):
        return [
            {"cover_url": b.cover_url, "cover_color": b.cover_color, "title": b.title}
            for b in self._books(obj)[:4]
        ]

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
            ).select_related("author")
        }
        return [by_slug[s] for s in order if s in by_slug]


class TopicDetailSerializer(TopicListSerializer):
    """A topic page — the shelf metadata plus the full list of member books."""

    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    scripture_ref = serializers.SerializerMethodField()
    scripture_text = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            "scripture_ref",
            "scripture_text",
            "books",
            "sermons",
        ]

    def get_scripture_ref(self, obj):
        return obj.scripture_ref_for(self._language())

    def get_scripture_text(self, obj):
        return obj.scripture_text_for(self._language())

    def get_books(self, obj):
        return BookListSerializer(self._books(obj), many=True).data

    def get_sermons(self, obj):
        return SermonListSerializer(self._sermons(obj), many=True).data
