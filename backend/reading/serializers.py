from rest_framework import serializers

from .models import (
    Bookmark,
    ChapterMarks,
    CustomShelf,
    Favorite,
    JournalEntry,
    PlanProgress,
    ReadingProgress,
)


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = [
            "kind",
            "book_slug",
            "chapter_order",
            "paragraph_index",
            "bm_id",
            "snippet",
            "title",
        ]


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = [
            "entry_id",
            "kind",
            "title",
            "body",
            "answer",
            "answered_at",
            "ref",
            "collection",
            "pinned_at",
            "person",
            "group",
            "remind",
            "updates",
            "source",
            "deleted",
            "client_created_at",
            "client_updated_at",
        ]


class PlanProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanProgress
        fields = ["plan_slug", "started_at", "done", "updated_at"]
        read_only_fields = ["updated_at"]


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["kind", "slug", "created_at"]
        read_only_fields = ["created_at"]


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = [
            "kind",
            "book_slug",
            "language",
            "chapter_order",
            "paragraph_index",
            "updated_at",
            # The writing device's own clock. A second device compares it against
            # its local record to tell "further along elsewhere" from its own past.
            "client_updated_at",
            # When the reader finished this work (null while in progress). Set
            # through _upsert_progress's union rule, not deserialized from a
            # client field — the PUT carries `finished_at` / `unfinish` in its
            # body instead — so it is read-only here.
            "finished_at",
        ]
        read_only_fields = ["updated_at", "client_updated_at", "finished_at"]


class ChapterMarksSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterMarks
        fields = [
            "kind",
            "book_slug",
            "language",
            "chapter_order",
            "marks",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class CustomShelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomShelf
        fields = [
            "shelf_id",
            "name",
            "books",
            "deleted",
            "client_created_at",
            "client_updated_at",
        ]
