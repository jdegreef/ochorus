from django.urls import path

from .views import (
    AuthorListView,
    BookDetailView,
    BookListView,
    ChapterDetailView,
    LanguageListView,
    SearchView,
)

urlpatterns = [
    path("authors/", AuthorListView.as_view(), name="author-list"),
    path("books/", BookListView.as_view(), name="book-list"),
    path("languages/", LanguageListView.as_view(), name="language-list"),
    path("search/", SearchView.as_view(), name="search"),
    path("books/<slug:slug>/", BookDetailView.as_view(), name="book-detail"),
    path(
        "books/<slug:slug>/chapters/<int:order>/",
        ChapterDetailView.as_view(),
        name="chapter-detail",
    ),
]
