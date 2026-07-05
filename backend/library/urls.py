from django.urls import path

from .views import (
    AuthorDetailView,
    AuthorListView,
    BookDetailView,
    BookListView,
    ChapterDetailView,
    LanguageListView,
    SearchView,
    SermonDetailView,
    SermonListView,
)

urlpatterns = [
    path("authors/", AuthorListView.as_view(), name="author-list"),
    path("authors/<slug:slug>/", AuthorDetailView.as_view(), name="author-detail"),
    path("books/", BookListView.as_view(), name="book-list"),
    path("sermons/", SermonListView.as_view(), name="sermon-list"),
    path("languages/", LanguageListView.as_view(), name="language-list"),
    path("search/", SearchView.as_view(), name="search"),
    path("books/<slug:slug>/", BookDetailView.as_view(), name="book-detail"),
    path("sermons/<slug:slug>/", SermonDetailView.as_view(), name="sermon-detail"),
    path(
        "books/<slug:slug>/chapters/<int:order>/",
        ChapterDetailView.as_view(),
        name="chapter-detail",
    ),
]
