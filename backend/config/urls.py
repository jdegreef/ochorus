"""Top-level URL configuration for the Ochorus API."""

from django.contrib import admin
from django.urls import include, path

from accounts.views import MeView, health
from library.admin_views import (
    AdminCoverageView,
    AdminLanguageDetailView,
    AdminStatsView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/coverage/", AdminCoverageView.as_view(), name="admin-coverage"),
    path(
        "api/admin/languages/<str:code>/",
        AdminLanguageDetailView.as_view(),
        name="admin-language-detail",
    ),
    path("api/library/", include("library.urls")),
    path("api/reading/", include("reading.urls")),
]
