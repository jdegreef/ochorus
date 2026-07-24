from rest_framework import serializers

from .models import ChapterMarks, Favorite, PlanProgress, ReadingProgress


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
        ]
        read_only_fields = ["updated_at"]


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

