from rest_framework import serializers

from .models import Author, Book, Chapter, Plan, PlanDay, Sermon, Topic


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
        ]


class SermonListSerializer(serializers.ModelSerializer):
    """A sermon card — enough for the shelf and the author page (no body)."""

    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Sermon
        fields = [
            "slug",
            "language",
            "title",
            "scripture_ref",
            "preached_on",
            "word_count",
            "author",
        ]


class SermonDetailSerializer(serializers.ModelSerializer):
    """A single sermon with its full body, for the reader."""

    author_name = serializers.CharField(source="author.name", read_only=True)
    author_slug = serializers.CharField(source="author.slug", read_only=True)

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
            "source_url",
            "author_name",
            "author_slug",
        ]


class AuthorDetailSerializer(serializers.ModelSerializer):
    """An author page: bio, dates, their books and their sermons in a language."""

    book_count = serializers.SerializerMethodField()
    books = serializers.SerializerMethodField()
    sermons = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    bio_html = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            "slug", "name", "bio", "bio_html", "photo_url", "birth_year",
            "death_year", "book_count", "books", "sermons",
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


class ChapterTocSerializer(serializers.ModelSerializer):
    """A chapter's metadata for the table of contents (no body)."""

    class Meta:
        model = Chapter
        fields = ["order", "title", "word_count"]


class BookDetailSerializer(BookListSerializer):
    """Book detail — adds description, the chapter TOC, and topic chips."""

    chapters = ChapterTocSerializer(many=True, read_only=True)
    topics = serializers.SerializerMethodField()

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "description", "source_url", "pdf_url", "chapters",
            "publication_year", "attribution", "topics",
        ]

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


class ChapterDetailSerializer(serializers.ModelSerializer):
    """A single chapter with its full body and prev/next navigation."""

    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    body_html = serializers.SerializerMethodField()
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    author_name = serializers.CharField(source="book.author.name", read_only=True)
    author_slug = serializers.CharField(source="book.author.slug", read_only=True)

    def get_body_html(self, obj):
        from .scripture import annotate_references

        return annotate_references(obj.body_html)

    class Meta:
        model = Chapter
        fields = [
            "order", "title", "body_html", "word_count",
            "book_title", "book_slug", "author_name", "author_slug",
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

    class Meta:
        model = Plan
        fields = ["slug", "language", "title", "description", "day_count"]


class PlanDaySerializer(serializers.ModelSerializer):
    """One day's reading, enriched with display titles for the linked chapter."""

    book_title = serializers.CharField(read_only=True, default="")
    chapter_title = serializers.CharField(read_only=True, default="")

    class Meta:
        model = PlanDay
        fields = ["day", "book_slug", "chapter_order", "book_title", "chapter_title"]


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
        ).values("book__slug", "book__title", "order", "title")
        lookup = {(c["book__slug"], c["order"]): c for c in chapters}
        for d in days:
            c = lookup.get((d.book_slug, d.chapter_order))
            d.book_title = c["book__title"] if c else ""
            d.chapter_title = c["title"] if c else ""
        return PlanDaySerializer(days, many=True).data


class TopicListSerializer(serializers.ModelSerializer):
    """A topical shelf card — localized title/description, member count, and a
    handful of member covers for the browse page. ``book_count`` and ``covers``
    are computed against the requested language (see ``TopicListView``)."""

    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    book_count = serializers.SerializerMethodField()
    covers = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ["slug", "title", "description", "book_count", "covers"]

    def _language(self):
        return self.context.get("language", "en")

    def get_title(self, obj):
        return obj.title_for(self._language())

    def get_description(self, obj):
        return obj.description_for(self._language())

    def get_book_count(self, obj):
        return len(self._books(obj))

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


class TopicDetailSerializer(TopicListSerializer):
    """A topic page — the shelf metadata plus the full list of member books."""

    books = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + ["books"]

    def get_books(self, obj):
        return BookListSerializer(self._books(obj), many=True).data
