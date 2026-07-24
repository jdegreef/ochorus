from django.urls import path

from .views import (
    ActivityView,
    FavoriteView,
    MarksView,
    MergeView,
    PlanProgressView,
    ProgressView,
    SermonMarksView,
    StateView,
)

urlpatterns = [
    path("state/", StateView.as_view(), name="reading-state"),
    path("merge/", MergeView.as_view(), name="reading-merge"),
    path("activity/<str:day>/", ActivityView.as_view(), name="reading-activity"),
    path(
        "favorites/<slug:kind>/<slug:slug>/",
        FavoriteView.as_view(),
        name="reading-favorite",
    ),
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
