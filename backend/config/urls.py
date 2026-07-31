"""Top-level URL configuration for the Ochorus API."""

from django.contrib import admin
from django.urls import include, path

from accounts.views import MeView, health
from library.admin_import_views import (
    AdminAuthorCreateView,
    AdminImportLanguagesView,
    AdminImportParseView,
    AdminImportPublishView,
)
from library.admin_views import (
    AdminAuditView,
    AdminBookDetailView,
    AdminCoverageView,
    AdminEngagementView,
    AdminExportView,
    AdminLanguageCreateView,
    AdminLanguageDeployCheckView,
    AdminLanguageDetailView,
    AdminLanguageGoLiveView,
    AdminLanguageReadinessView,
    AdminLanguageSettingsView,
    AdminLanguageThresholdsView,
    AdminReviewQueueView,
    AdminSearchGapView,
    AdminSearchView,
    AdminStatsView,
    AdminTranslationJobsView,
    AdminUsersView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/search-stats/", AdminSearchView.as_view(), name="admin-search-stats"),
    path("api/admin/search-gap/", AdminSearchGapView.as_view(), name="admin-search-gap"),
    path("api/admin/coverage/", AdminCoverageView.as_view(), name="admin-coverage"),
    path("api/admin/audit/", AdminAuditView.as_view(), name="admin-audit"),
    path(
        "api/admin/engagement/",
        AdminEngagementView.as_view(),
        name="admin-engagement",
    ),
    path("api/admin/users/", AdminUsersView.as_view(), name="admin-users"),
    path("api/admin/export/", AdminExportView.as_view(), name="admin-export"),
    path("api/admin/authors/", AdminAuthorCreateView.as_view(), name="admin-author-create"),
    path(
        "api/admin/import/languages/",
        AdminImportLanguagesView.as_view(),
        name="admin-import-languages",
    ),
    path(
        "api/admin/import/parse/",
        AdminImportParseView.as_view(),
        name="admin-import-parse",
    ),
    path(
        "api/admin/import/publish/",
        AdminImportPublishView.as_view(),
        name="admin-import-publish",
    ),
    path(
        "api/admin/books/<slug:slug>/",
        AdminBookDetailView.as_view(),
        name="admin-book-detail",
    ),
    path(
        "api/admin/review-queue/",
        AdminReviewQueueView.as_view(),
        name="admin-review-queue",
    ),
    path(
        "api/admin/translation-jobs/",
        AdminTranslationJobsView.as_view(),
        name="admin-translation-jobs",
    ),
    # Creating a language is how a new one begins: the row is what the
    # translate_* commands read, so it must exist before any work can be queued.
    path(
        "api/admin/languages/",
        AdminLanguageCreateView.as_view(),
        name="admin-language-create",
    ),
    path(
        "api/admin/languages/<str:code>/",
        AdminLanguageDetailView.as_view(),
        name="admin-language-detail",
    ),
    # Identity (names, Bible, glossary) — refused for repo-defined languages,
    # whose rows the deploy re-asserts.
    path(
        "api/admin/languages/<str:code>/settings/",
        AdminLanguageSettingsView.as_view(),
        name="admin-language-settings",
    ),
    # Readiness is its own route: it makes a live Bible-API call, so it must not
    # ride along on every load of the detail page.
    path(
        "api/admin/languages/<str:code>/readiness/",
        AdminLanguageReadinessView.as_view(),
        name="admin-language-readiness",
    ),
    path(
        "api/admin/languages/<str:code>/thresholds/",
        AdminLanguageThresholdsView.as_view(),
        name="admin-language-thresholds",
    ),
    # The switch. POST re-runs the checks server-side, records the launch, and
    # triggers the reader's rebuild — a prerendered site needs a build, so this
    # is deliberately not a bare status write.
    path(
        "api/admin/languages/<str:code>/go-live/",
        AdminLanguageGoLiveView.as_view(),
        name="admin-language-go-live",
    ),
    # "status" is what was decided; this is what actually shipped.
    path(
        "api/admin/languages/<str:code>/deploy-check/",
        AdminLanguageDeployCheckView.as_view(),
        name="admin-language-deploy-check",
    ),
    path("api/library/", include("library.urls")),
    path("api/reading/", include("reading.urls")),
]
