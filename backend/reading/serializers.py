from rest_framework import serializers

from .models import (
    Bookmark,
    ChapterMarks,
    CustomShelf,
    Favorite,
    JournalEntry,
    PlanProgress,
    PlanSchedule,
    ReadingGroup,
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


class PlanScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanSchedule
        fields = [
            "plan_slug",
            "start_on",
            "reading_days",
            "remind_at",
            "email_reminder",
            "client_updated_at",
        ]
        read_only_fields = fields


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
            # The furthest chapter reached (0 = unknown) and the percent through
            # the work, by words (null = unmeasured). Both resolved by
            # _upsert_progress, never deserialized directly.
            "furthest_order",
            "pct",
        ]
        read_only_fields = [
            "updated_at",
            "client_updated_at",
            "finished_at",
            "furthest_order",
            "pct",
        ]


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


class ReadingGroupSerializer(serializers.ModelSerializer):
    """A group's own facts — what its link already carries, and its code.
    Never its creator or its members."""

    class Meta:
        model = ReadingGroup
        fields = ["code", "plan_slug", "start_on", "reading_days"]
