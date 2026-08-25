from django import forms
from django.contrib import admin

from .models import Author, Book, Chapter, Plan, PlanDay
from .sanitize import clean_bio_html, clean_fragment


class ChapterAdminForm(forms.ModelForm):
    """Sanitize hand-edited chapter HTML.

    The reader renders ``body_html`` with ``{@html}``, so this textarea is a
    direct path from a Django-admin session to script execution in every
    reader's browser. Cleaning here means the invariant holds for the admin the
    same way it holds for the importers.
    """

    class Meta:
        model = Chapter
        fields = "__all__"

    def clean_body_html(self):
        return clean_fragment(self.cleaned_data.get("body_html") or "")


class AuthorAdminForm(forms.ModelForm):
    """Sanitize hand-edited biography HTML (the wider bio profile).

    ``bio_html`` legitimately carries ``<aside class="prayer">`` callouts,
    ``<cite>`` attributions and internal links, so it takes the biography
    allowlist — the chapter one would strip all three.
    """

    class Meta:
        model = Author
        fields = "__all__"

    def clean_bio_html(self):
        return clean_bio_html(self.cleaned_data.get("bio_html") or "")


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    form = AuthorAdminForm
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
    form = ChapterAdminForm
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
