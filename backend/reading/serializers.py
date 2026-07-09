from rest_framework import serializers

from .models import ChapterMarks, ReadingProgress


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = [
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
            "book_slug",
            "language",
            "chapter_order",
            "marks",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
