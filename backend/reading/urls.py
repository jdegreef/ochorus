from django.urls import path

from .views import (
    ActivityView,
    BookmarksView,
    FavoriteView,
    JournalView,
    MarksView,
    MergeView,
    PlanProgressView,
    ProgressView,
    SermonMarksView,
    SessionsView,
    StateView,
)

urlpatterns = [
    path("state/", StateView.as_view(), name="reading-state"),
    path("merge/", MergeView.as_view(), name="reading-merge"),
    path("sessions/", SessionsView.as_view(), name="reading-sessions"),
    path("activity/<str:day>/", ActivityView.as_view(), name="reading-activity"),
    path(
        "favorites/<slug:kind>/<slug:slug>/",
        FavoriteView.as_view(),
        name="reading-favorite",
    ),
    path(
        "bookmarks/<slug:kind>/<slug:slug>/<int:order>/<int:p>/",
        BookmarksView.as_view(),
        name="reading-bookmark",
    ),
    path("journal/<str:entry_id>/", JournalView.as_view(), name="reading-journal"),
    path("progress/<slug:slug>/", ProgressView.as_view(), name="reading-progress"),
    path("plan/<slug:slug>/", PlanProgressView.as_view(), name="reading-plan"),
    path(
        "marks/<slug:slug>/<int:order>/",
        MarksView.as_view(),
        name="reading-marks",
    ),
    path(
        "sermon-marks/<slug:slug>/",
        SermonMarksView.as_view(),
        name="reading-sermon-marks",
    ),
]
