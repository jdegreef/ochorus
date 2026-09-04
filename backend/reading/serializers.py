from rest_framework import serializers

from .models import Bookmark, ChapterMarks, Favorite, PlanProgress, ReadingProgress


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
        ]
        read_only_fields = ["updated_at", "client_updated_at"]


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

