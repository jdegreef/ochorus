from rest_framework import serializers

from .models import Author, Book, Chapter


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["slug", "name", "bio", "birth_year", "death_year"]


class BookListSerializer(serializers.ModelSerializer):
    """Shelf view — enough to render a cover card, no chapter bodies."""

    author = AuthorSerializer(read_only=True)
    chapter_count = serializers.IntegerField(source="num_chapters", read_only=True)

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
        ]


class ChapterTocSerializer(serializers.ModelSerializer):
    """A chapter's metadata for the table of contents (no body)."""

    class Meta:
        model = Chapter
        fields = ["order", "title", "word_count"]


class BookDetailSerializer(BookListSerializer):
    """Book detail — adds description and the chapter table of contents."""

    chapters = ChapterTocSerializer(many=True, read_only=True)

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "description", "source_url", "pdf_url", "chapters",
        ]


class ChapterDetailSerializer(serializers.ModelSerializer):
    """A single chapter with its full body and prev/next navigation."""

    prev = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)

    class Meta:
        model = Chapter
        fields = [
            "order", "title", "body_html", "word_count",
            "book_title", "book_slug", "prev", "next",
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
