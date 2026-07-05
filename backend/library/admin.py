from django.contrib import admin

from .models import Author, Book, Chapter, Plan, PlanDay


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "birth_year", "death_year")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


class ChapterInline(admin.TabularInline):
    model = Chapter
    fields = ("order", "title", "word_count")
    readonly_fields = ("word_count",)
    extra = 0
    show_change_link = True


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "language",
        "source_type",
        "is_published",
        "sort_order",
    )
    list_filter = ("language", "source_type", "is_published", "author")
    search_fields = ("title", "slug")
    inlines = [ChapterInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("book", "order", "title", "word_count")
    list_filter = ("book__language", "book")
    search_fields = ("title",)


class PlanDayInline(admin.TabularInline):
    model = PlanDay
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "language", "is_published", "sort_order")
    list_filter = ("language", "is_published")
    search_fields = ("title", "slug")
    inlines = [PlanDayInline]
