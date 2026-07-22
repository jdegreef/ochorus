from django.urls import path

from .views import (
    FavoriteView,
    MarksView,
    MergeView,
    ProgressView,
    SermonMarksView,
    StateView,
)

urlpatterns = [
    path("state/", StateView.as_view(), name="reading-state"),
    path("merge/", MergeView.as_view(), name="reading-merge"),
    path(
        "favorites/<slug:kind>/<slug:slug>/",
        FavoriteView.as_view(),
        name="reading-favorite",
    ),
    path("progress/<slug:slug>/", ProgressView.as_view(), name="reading-progress"),
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
