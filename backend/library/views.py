"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Author, Book, Chapter, Plan, Sermon
from .search import search_library
from .serializers import (
    AuthorDetailSerializer,
    AuthorListSerializer,
    BookDetailSerializer,
    BookListSerializer,
    ChapterDetailSerializer,
    PlanDetailSerializer,
    PlanListSerializer,
    SermonDetailSerializer,
    SermonListSerializer,
)

DEFAULT_LANGUAGE = "en"

# Display names for the languages we expect to publish in. Anything not listed
# falls back to its bare code so a new language still appears in the picker.
LANGUAGE_NAMES = {
    "en": ("English", "English"),
    "sw": ("Swahili", "Kiswahili"),
    "fr": ("French", "Français"),
    "es": ("Spanish", "Español"),
    "pt": ("Portuguese", "Português"),
    "lg": ("Luganda", "Luganda"),
    "sn": ("Shona", "chiShona"),
    "ny": ("Chichewa", "Chichewa"),
    "ln": ("Lingala", "Lingála"),
    "zh": ("Chinese", "中文"),
}


def _language(request) -> str:
    return request.query_params.get("language", DEFAULT_LANGUAGE)


def _language_entry(code: str) -> dict:
    name, native = LANGUAGE_NAMES.get(code, (code, code))
    return {"code": code, "name": name, "native_name": native}


# Snippet highlight markers. The API returns *plain text* snippets with matches
# wrapped in these; the client HTML-escapes the text and then swaps the markers
# for <mark> tags, so no HTML ever crosses the boundary unescaped.
class AuthorListView(generics.ListAPIView):
    """Authors for the Biographies page (those with a bio), with book counts."""

    serializer_class = AuthorListSerializer

    def get_queryset(self):
        # Count only books available in the requested language, so a localized
        # biographies page reflects what a reader can actually open in that
        # language (matches AuthorDetailSerializer, which lists books per-locale).
        # Authors with no book in this language fall to the "view biography"
        # link in the UI.
        lang = _language(self.request)
        return (
            Author.objects.exclude(bio="")
            .prefetch_related("translations")
            .annotate(
                num_books=Count(
                    "books",
                    filter=Q(books__is_published=True, books__language=lang),
                )
            )
            .order_by("name")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class AuthorDetailView(generics.RetrieveAPIView):
    """A single author with their published books (for the author page)."""

    serializer_class = AuthorDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Author.objects.prefetch_related("translations"), slug=self.kwargs["slug"]
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["language"] = _language(self.request)
        return ctx


class BookListView(generics.ListAPIView):
    """All published books for a language, ordered for the shelf."""

    serializer_class = BookListSerializer

    def get_queryset(self):
        return (
            Book.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .order_by("sort_order", "title")
        )


class BookDetailView(generics.RetrieveAPIView):
    serializer_class = BookDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Book.objects.filter(is_published=True)
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .prefetch_related("chapters"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )


class ChapterDetailView(generics.RetrieveAPIView):
    serializer_class = ChapterDetailSerializer

    def get_object(self):
        book = get_object_or_404(
            Book,
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
        )
        return get_object_or_404(
            Chapter.objects.select_related("book__author"),
            book=book,
            order=self.kwargs["order"],
        )


class SermonListView(generics.ListAPIView):
    """All published sermons for a language, ordered for the shelf."""

    serializer_class = SermonListSerializer

    def get_queryset(self):
        return (
            Sermon.objects.filter(is_published=True, language=_language(self.request))
            .select_related("author")
            .order_by("author__name", "sort_order", "title")
        )


class SermonDetailView(generics.RetrieveAPIView):
    serializer_class = SermonDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Sermon.objects.select_related("author"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
            is_published=True,
        )


class LanguageListView(APIView):
    """Distinct languages that have at least one published book.

    Powers the content-language selector in the header. Returns the BCP-47-ish
    code plus a human label/native name where we know one.
    """

    def get(self, request):
        codes = (
            Book.objects.filter(is_published=True)
            .values_list("language", flat=True)
            .distinct()
            .order_by("language")
        )
        return Response([_language_entry(c) for c in codes])


class PlanListView(generics.ListAPIView):
    """Published reading plans for a language."""

    serializer_class = PlanListSerializer

    def get_queryset(self):
        return (
            Plan.objects.filter(is_published=True, language=_language(self.request))
            .annotate(num_days=Count("days"))
            .order_by("sort_order", "title")
        )


class PlanDetailView(generics.RetrieveAPIView):
    serializer_class = PlanDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Plan.objects.filter(is_published=True)
            .annotate(num_days=Count("days"))
            .prefetch_related("days"),
            slug=self.kwargs["slug"],
            language=_language(self.request),
        )


class SearchView(APIView):
    """Ranked full-text search across published chapters and sermons.

    Delegates to ``library.search.search_library`` (see there for the Postgres
    vs SQLite behaviour). Snippets come back with matches marker-wrapped for the
    client to render as ``<mark>``.
    """

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        language = _language(request)
        if len(q) < 2:
            return Response({"query": q, "results": []})
        return Response({"query": q, "results": search_library(q, language)})
