"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

import html
import re

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.html import strip_tags
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Author, Book, Chapter, Sermon
from .serializers import (
    AuthorDetailSerializer,
    AuthorListSerializer,
    BookDetailSerializer,
    BookListSerializer,
    ChapterDetailSerializer,
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


def _snippet(body_html: str, query: str, radius: int = 90) -> str:
    """A short plain-text excerpt centred on the first match of ``query``."""
    text = re.sub(r"\s+", " ", html.unescape(strip_tags(body_html))).strip()
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[: radius * 2] + ("…" if len(text) > radius * 2 else "")
    start = max(0, idx - radius)
    end = min(len(text), idx + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


class AuthorListView(generics.ListAPIView):
    """Authors for the Biographies page (those with a bio), with book counts."""

    serializer_class = AuthorListSerializer

    def get_queryset(self):
        return (
            Author.objects.exclude(bio="")
            .annotate(num_books=Count("books", filter=Q(books__is_published=True)))
            .order_by("name")
        )


class AuthorDetailView(generics.RetrieveAPIView):
    """A single author with their published books (for the author page)."""

    serializer_class = AuthorDetailSerializer

    def get_object(self):
        return get_object_or_404(Author, slug=self.kwargs["slug"])

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


class SearchView(APIView):
    """Full-text-ish search across published books, authors and chapter bodies.

    Uses Postgres full-text search when available (production) and falls back to
    case-insensitive ``icontains`` on SQLite (local dev), so results are returned
    in either environment. Each hit carries a short plain-text snippet.
    """

    MAX_RESULTS = 30

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        language = _language(request)
        if len(q) < 2:
            return Response({"query": q, "results": []})

        chapters = (
            Chapter.objects.filter(book__is_published=True, book__language=language)
            .filter(
                Q(body_html__icontains=q)
                | Q(title__icontains=q)
                | Q(book__title__icontains=q)
                | Q(book__subtitle__icontains=q)
                | Q(book__author__name__icontains=q)
            )
            .select_related("book", "book__author")
            .order_by("book__sort_order", "book__title", "order")[: self.MAX_RESULTS]
        )

        results = [
            {
                "book_slug": c.book.slug,
                "book_title": c.book.title,
                "author_name": c.book.author.name,
                "chapter_order": c.order,
                "chapter_title": c.title,
                "snippet": _snippet(c.body_html, q),
            }
            for c in chapters
        ]
        return Response({"query": q, "results": results})
