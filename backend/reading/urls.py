from django.urls import path

from .views import MarksView, MergeView, ProgressView, StateView

urlpatterns = [
    path("state/", StateView.as_view(), name="reading-state"),
    path("merge/", MergeView.as_view(), name="reading-merge"),
    path("progress/<slug:slug>/", ProgressView.as_view(), name="reading-progress"),
    path(
        "marks/<slug:slug>/<int:order>/",
        MarksView.as_view(),
        name="reading-marks",
    ),
]
