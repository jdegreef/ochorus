from django.contrib import admin

from .models import ChapterMarks, ReadingProgress


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ("profile", "book_slug", "language", "chapter_order", "updated_at")
    list_filter = ("language",)
    search_fields = ("book_slug", "profile__email")


@admin.register(ChapterMarks)
class ChapterMarksAdmin(admin.ModelAdmin):
    list_display = ("profile", "book_slug", "chapter_order", "updated_at")
    list_filter = ("language",)
    search_fields = ("book_slug", "profile__email")
