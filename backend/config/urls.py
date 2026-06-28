"""Top-level URL configuration for the Ochorus API."""

from django.contrib import admin
from django.urls import include, path

from accounts.views import MeView, health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/library/", include("library.urls")),
]
