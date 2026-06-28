from django.urls import path

from .views import BookDetailView, BookListView, ChapterDetailView

urlpatterns = [
    path("books/", BookListView.as_view(), name="book-list"),
    path("books/<slug:slug>/", BookDetailView.as_view(), name="book-detail"),
    path(
        "books/<slug:slug>/chapters/<int:order>/",
        ChapterDetailView.as_view(),
        name="chapter-detail",
    ),
]
