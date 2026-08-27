from django.urls import path

from .views import (
    AuthorDetailView,
    AuthorListView,
    BookDetailView,
    BookListView,
    ChapterDetailView,
    LanguageListView,
    PlanDetailView,
    PlanListView,
    PopularSearchesView,
    ScriptureGraphView,
    ScripturePagesView,
    ScriptureView,
    SearchClickView,
    SearchView,
    SermonDetailView,
    SermonListView,
    TopicDetailView,
    TopicListView,
)

urlpatterns = [
    path("authors/", AuthorListView.as_view(), name="author-list"),
    path("authors/<slug:slug>/", AuthorDetailView.as_view(), name="author-detail"),
    path("books/", BookListView.as_view(), name="book-list"),
    path("sermons/", SermonListView.as_view(), name="sermon-list"),
    path("languages/", LanguageListView.as_view(), name="language-list"),
    path("search/", SearchView.as_view(), name="search"),
    path("popular-searches/", PopularSearchesView.as_view(), name="popular-searches"),
    path("search-click/", SearchClickView.as_view(), name="search-click"),
    path("scripture/", ScriptureView.as_view(), name="scripture"),
    # Before the <book> patterns: "pages" is one segment, they are two or three,
    # so these cannot actually collide — the order is for a reader of this file.
    path("scripture/pages/", ScripturePagesView.as_view(), name="scripture-pages"),
    path(
        "scripture/<slug:book>/<int:chapter>/",
        ScriptureGraphView.as_view(),
        name="scripture-chapter",
    ),
    path(
        "scripture/<slug:book>/<int:chapter>/<int:verse>/",
        ScriptureGraphView.as_view(),
        name="scripture-verse",
    ),
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("plans/<slug:slug>/", PlanDetailView.as_view(), name="plan-detail"),
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<slug:slug>/", TopicDetailView.as_view(), name="topic-detail"),
    path("books/<slug:slug>/", BookDetailView.as_view(), name="book-detail"),
    path("sermons/<slug:slug>/", SermonDetailView.as_view(), name="sermon-detail"),
    path(
        "books/<slug:slug>/chapters/<int:order>/",
        ChapterDetailView.as_view(),
        name="chapter-detail",
    ),
]
