"""Public read-only API for the library.

Books are addressed by their canonical ``slug`` plus a ``language`` query param
(default "en"). All endpoints are public (AllowAny via the project default).
"""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics

from .models import Author, Book, Chapter
from .serializers import (
    AuthorListSerializer,
    BookDetailSerializer,
    BookListSerializer,
    ChapterDetailSerializer,
)

DEFAULT_LANGUAGE = "en"


def _language(request) -> str:
    return request.query_params.get("language", DEFAULT_LANGUAGE)


class AuthorListView(generics.ListAPIView):
    """Authors for the Biographies page (those with a bio), with book counts."""

    serializer_class = AuthorListSerializer

    def get_queryset(self):
        return (
            Author.objects.exclude(bio="")
            .annotate(num_books=Count("books", filter=Q(books__is_published=True)))
            .order_by("name")
        )


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
        return get_object_or_404(Chapter, book=book, order=self.kwargs["order"])
