from rest_framework import serializers

from .models import ChapterMarks, ReadingProgress, SermonMarks


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


class SermonMarksSerializer(serializers.ModelSerializer):
    class Meta:
        model = SermonMarks
        fields = [
            "sermon_slug",
            "language",
            "marks",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
