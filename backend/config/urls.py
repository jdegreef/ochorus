"""Top-level URL configuration for the Ochorus API."""

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from accounts.views import MeView, PromptEventView, SignupSourceView, health
from config.lazy_views import lazy_view
from library.build_facts_view import build_facts


def robots_txt(_request):
    # Served on the API host (api.ochorus.com). Nothing here is for crawlers to
    # INDEX — the library lives on the prerendered reader (ochorus.com) — but the
    # public library endpoints must stay FETCHABLE. Every prerendered page
    # re-runs its load() on hydration and calls /api/library/ from the browser,
    # and Googlebot's renderer obeys robots.txt for those requests too. A blanket
    # `Disallow: /` (#1946) made that fetch fail under Google's render, so the
    # page hydrated into +error.svelte and Google read its noindex — articles
    # were reported "Excluded by 'noindex' tag". Everything else (admin, auth,
    # reading) stays disallowed. Bad bots ignore this either way — that's the
    # CDN's job (docs/egress-cloudflare.md).
    return HttpResponse(
        "User-agent: *\nAllow: /api/library/\nDisallow: /\n", content_type="text/plain"
    )


urlpatterns = [
    path("robots.txt", robots_txt, name="robots"),
    path("api/health/", health, name="health"),
    # Token-gated, 404 unless BUILD_FACTS_TOKEN is set (library/build_facts_view.py).
    path("api/build-facts/", build_facts, name="build-facts"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/signup-source/", SignupSourceView.as_view(), name="signup-source"),
    path("api/auth/prompt-event/", PromptEventView.as_view(), name="prompt-event"),
    # The admin dashboard's views (and the email / import / jobs stacks behind
    # them) load on first use, not at startup: importing them eagerly was ~38 MB
    # of the worker's baseline, paid on every recycle, for routes reader traffic
    # never hits. Name the module that DEFINES the view (config/lazy_views.py).
    path(
        "api/admin/stats/",
        lazy_view("library.admin_views.content", "AdminStatsView"),
        name="admin-stats",
    ),
    path(
        "api/admin/attention/",
        lazy_view("library.admin_views.attention", "AdminAttentionView"),
        name="admin-attention",
    ),
    path(
        "api/admin/unpublished/",
        lazy_view("library.admin_views.attention", "AdminUnpublishedView"),
        name="admin-unpublished",
    ),
    path(
        "api/admin/authors-without-bio/",
        lazy_view("library.admin_views.attention", "AdminAuthorsWithoutBioView"),
        name="admin-authors-without-bio",
    ),
    path(
        "api/admin/covers/",
        lazy_view("library.admin_views.covers", "AdminCoversView"),
        name="admin-covers",
    ),
    path(
        "api/admin/search-stats/",
        lazy_view("library.admin_views.analytics", "AdminSearchView"),
        name="admin-search-stats",
    ),
    path(
        "api/admin/search-gap/",
        lazy_view("library.admin_views.analytics", "AdminSearchGapView"),
        name="admin-search-gap",
    ),
    path(
        "api/admin/search-preview/",
        lazy_view("library.admin_views.analytics", "AdminSearchPreviewView"),
        name="admin-search-preview",
    ),
    path(
        "api/admin/search-decisions/",
        lazy_view("library.admin_views.analytics", "AdminSearchDecisionListView"),
        name="admin-search-decisions",
    ),
    path(
        "api/admin/search-decisions/decide/",
        lazy_view("library.admin_views.analytics", "AdminSearchDecisionView"),
        name="admin-search-decide",
    ),
    path(
        "api/admin/catalog/<slug:kind>/",
        lazy_view("library.admin_views.catalog", "AdminCatalogView"),
        name="admin-catalog",
    ),
    path(
        "api/admin/coverage/",
        lazy_view("library.admin_views.content", "AdminCoverageView"),
        name="admin-coverage",
    ),
    path(
        "api/admin/drop-off/",
        lazy_view("library.admin_views.dropoff", "AdminDropOffView"),
        name="admin-drop-off",
    ),
    path(
        "api/admin/coverage/mark-current/",
        lazy_view("library.admin_views.content", "AdminTranslationMarkCurrentView"),
        name="admin-translation-mark-current",
    ),
    path(
        "api/admin/language-health/",
        lazy_view("library.admin_views.health", "AdminLanguageHealthView"),
        name="admin-language-health",
    ),
    path(
        "api/admin/manual/",
        lazy_view("library.admin_views.manual", "AdminManualView"),
        name="admin-manual",
    ),
    path(
        "api/admin/language-manual/",
        lazy_view("library.admin_views.manual", "AdminLanguageManualView"),
        name="admin-language-manual",
    ),
    path(
        "api/admin/audit/",
        lazy_view("library.admin_views.quality", "AdminAuditView"),
        name="admin-audit",
    ),
    path(
        "api/admin/audit/dismiss/",
        lazy_view("library.admin_views.quality", "AdminAuditDismissView"),
        name="admin-audit-dismiss",
    ),
    path(
        "api/admin/activity/",
        lazy_view("library.admin_views.activity", "AdminActivityView"),
        name="admin-activity",
    ),
    path(
        "api/admin/engagement/",
        lazy_view("library.admin_views.analytics", "AdminEngagementView"),
        name="admin-engagement",
    ),
    path(
        "api/admin/users/",
        lazy_view("library.admin_views.analytics", "AdminUsersView"),
        name="admin-users",
    ),
    path(
        "api/admin/users/directory/",
        lazy_view("library.admin_views.user_directory", "AdminUserDirectoryView"),
        name="admin-user-directory",
    ),
    path(
        "api/admin/users/<uuid:uid>/",
        lazy_view("library.admin_views.user_detail", "AdminUserDetailView"),
        name="admin-user-detail",
    ),
    path(
        "api/admin/users/<uuid:uid>/account/",
        lazy_view("library.admin_views.user_delete", "AdminUserDeleteView"),
        name="admin-user-delete",
    ),
    path(
        "api/admin/export/",
        lazy_view("library.admin_views.detail", "AdminExportView"),
        name="admin-export",
    ),
    path(
        "api/admin/authors/",
        lazy_view("library.admin_import_views", "AdminAuthorCreateView"),
        name="admin-author-create",
    ),
    path(
        "api/admin/import/languages/",
        lazy_view("library.admin_import_views", "AdminImportLanguagesView"),
        name="admin-import-languages",
    ),
    path(
        "api/admin/import/parse/",
        lazy_view("library.admin_import_views", "AdminImportParseView"),
        name="admin-import-parse",
    ),
    path(
        "api/admin/import/publish/",
        lazy_view("library.admin_import_views", "AdminImportPublishView"),
        name="admin-import-publish",
    ),
    path(
        "api/admin/books/<slug:slug>/publish/",
        lazy_view("library.admin_views.detail", "AdminBookPublishView"),
        name="admin-book-publish",
    ),
    path(
        "api/admin/books/<slug:slug>/",
        lazy_view("library.admin_views.detail", "AdminBookDetailView"),
        name="admin-book-detail",
    ),
    path(
        "api/admin/sermons/<slug:slug>/publish/",
        lazy_view("library.admin_views.detail", "AdminSermonPublishView"),
        name="admin-sermon-publish",
    ),
    path(
        "api/admin/sermons/<slug:slug>/",
        lazy_view("library.admin_views.detail", "AdminSermonDetailView"),
        name="admin-sermon-detail",
    ),
    path(
        "api/admin/review-queue/",
        lazy_view("library.admin_views.quality", "AdminReviewQueueView"),
        name="admin-review-queue",
    ),
    path(
        "api/admin/review-queue/detail/",
        lazy_view("library.admin_views.quality", "AdminReviewDetailView"),
        name="admin-review-detail",
    ),
    path(
        "api/admin/review-queue/verse/",
        lazy_view("library.admin_views.quality", "AdminVerseReviewView"),
        name="admin-review-verse",
    ),
    path(
        "api/admin/translation-jobs/",
        lazy_view("library.admin_views.jobs", "AdminTranslationJobsView"),
        name="admin-translation-jobs",
    ),
    path(
        "api/admin/team/",
        lazy_view("library.admin_views.team", "AdminTeamView"),
        name="admin-team",
    ),
    path(
        "api/admin/roles/",
        lazy_view("library.admin_views.team", "AdminRolesView"),
        name="admin-roles",
    ),
    path(
        "api/admin/feedback/",
        lazy_view("feedback.admin_views", "AdminFeedbackListView"),
        name="admin-feedback",
    ),
    path(
        "api/admin/feedback/<int:pk>/",
        lazy_view("feedback.admin_views", "AdminFeedbackDetailView"),
        name="admin-feedback-detail",
    ),
    path(
        "api/admin/email-metrics/",
        lazy_view("emails.admin_views", "AdminEmailMetricsView"),
        name="admin-email-metrics",
    ),
    path(
        "api/admin/broadcasts/",
        lazy_view("emails.admin_views", "AdminBroadcastsView"),
        name="admin-broadcasts",
    ),
    path(
        "api/admin/broadcasts/audience-preview/",
        lazy_view("emails.admin_views", "AdminAudiencePreviewView"),
        name="admin-audience-preview",
    ),
    path(
        "api/admin/broadcasts/<int:pk>/",
        lazy_view("emails.admin_views", "AdminBroadcastDetailView"),
        name="admin-broadcast-detail",
    ),
    path(
        "api/admin/broadcasts/<int:pk>/action/",
        lazy_view("emails.admin_views", "AdminBroadcastActionView"),
        name="admin-broadcast-action",
    ),
    path(
        "api/admin/broadcasts/<int:pk>/translations/",
        lazy_view("emails.admin_design", "AdminBroadcastTranslationView"),
        name="admin-broadcast-translations",
    ),
    path(
        "api/admin/emails/auto/",
        lazy_view("emails.admin_auto", "AdminAutoEmailsView"),
        name="admin-email-auto",
    ),
    path(
        "api/admin/automations/",
        lazy_view("emails.admin_automations", "AdminAutomationsView"),
        name="admin-automations",
    ),
    path(
        "api/admin/automations/vocabulary/",
        lazy_view("emails.admin_automations", "AdminAutomationVocabularyView"),
        name="admin-automation-vocabulary",
    ),
    path(
        "api/admin/automations/<int:pk>/",
        lazy_view("emails.admin_automations", "AdminAutomationDetailView"),
        name="admin-automation",
    ),
    path(
        "api/admin/automations/<int:pk>/action/",
        lazy_view("emails.admin_automations", "AdminAutomationActionView"),
        name="admin-automation-action",
    ),
    path(
        "api/admin/automations/<int:pk>/emails/",
        lazy_view("emails.admin_automations", "AdminAutomationEmailsView"),
        name="admin-automation-emails",
    ),
    path(
        "api/admin/automation-emails/<int:pk>/",
        lazy_view("emails.admin_automations", "AdminAutomationEmailDetailView"),
        name="admin-automation-email",
    ),
    path(
        "api/admin/automation-emails/<int:pk>/translations/",
        lazy_view("emails.admin_automations", "AdminAutomationEmailTranslationView"),
        name="admin-automation-email-translations",
    ),
    path(
        "api/admin/emails/lifecycle/",
        lazy_view("emails.admin_lifecycle", "AdminLifecycleListView"),
        name="admin-email-lifecycle",
    ),
    path(
        "api/admin/emails/lifecycle/<str:step>/",
        lazy_view("emails.admin_lifecycle", "AdminLifecycleDetailView"),
        name="admin-email-lifecycle-detail",
    ),
    path(
        "api/admin/emails/lifecycle/<str:step>/action/",
        lazy_view("emails.admin_lifecycle", "AdminLifecycleActionView"),
        name="admin-email-lifecycle-action",
    ),
    path(
        "api/admin/emails/auto/build/",
        lazy_view("emails.admin_auto", "AdminAutoEmailBuildView"),
        name="admin-email-auto-build",
    ),
    path(
        "api/admin/emails/preview/",
        lazy_view("emails.admin_design", "AdminEmailPreviewView"),
        name="admin-email-preview",
    ),
    path(
        "api/admin/emails/library/",
        lazy_view("emails.admin_design", "AdminEmailLibraryView"),
        name="admin-email-library",
    ),
    path(
        "api/admin/emails/merge-tags/",
        lazy_view("emails.admin_design", "AdminEmailMergeTagsView"),
        name="admin-email-merge-tags",
    ),
    path(
        "api/admin/emails/library/search/",
        lazy_view("emails.admin_design", "AdminEmailLibrarySearchView"),
        name="admin-email-library-search",
    ),
    path(
        "api/admin/emails/images/",
        lazy_view("emails.admin_design", "AdminEmailImageView"),
        name="admin-email-images",
    ),
    path(
        "api/admin/emails/templates/",
        lazy_view("emails.admin_design", "AdminEmailTemplatesView"),
        name="admin-email-templates",
    ),
    path(
        "api/admin/emails/templates/<int:pk>/",
        lazy_view("emails.admin_design", "AdminEmailTemplateDetailView"),
        name="admin-email-template-detail",
    ),
    path(
        "api/admin/users/<uuid:uid>/emails/",
        lazy_view("emails.admin_views", "AdminReaderEmailsView"),
        name="admin-user-emails",
    ),
    path(
        "api/admin/content-edit-jobs/",
        lazy_view("library.admin_views.content_jobs", "AdminContentEditJobsView"),
        name="admin-content-edit-jobs",
    ),
    # Creating a language is how a new one begins: the row is what the
    # translate_* commands read, so it must exist before any work can be queued.
    path(
        "api/admin/languages/",
        lazy_view("library.admin_views.languages", "AdminLanguageCreateView"),
        name="admin-language-create",
    ),
    path(
        "api/admin/languages/<str:code>/",
        lazy_view("library.admin_views.content", "AdminLanguageDetailView"),
        name="admin-language-detail",
    ),
    path(
        "api/admin/languages/<str:code>/wanted/",
        lazy_view("library.admin_views.demand", "AdminLanguageWantedView"),
        name="admin-language-wanted",
    ),
    # This language against the named Level 1 content targets
    # (library.content_targets), every item with its state.
    path(
        "api/admin/languages/<str:code>/targets/",
        lazy_view("library.admin_views.targets", "AdminLanguageTargetsView"),
        name="admin-language-targets",
    ),
    # Identity (names, Bible, glossary) — refused for repo-defined languages,
    # whose rows the deploy re-asserts.
    path(
        "api/admin/languages/<str:code>/settings/",
        lazy_view("library.admin_views.languages", "AdminLanguageSettingsView"),
        name="admin-language-settings",
    ),
    # Readiness is its own route: it makes a live Bible-API call, so it must not
    # ride along on every load of the detail page.
    path(
        "api/admin/languages/<str:code>/readiness/",
        lazy_view("library.admin_views.languages", "AdminLanguageReadinessView"),
        name="admin-language-readiness",
    ),
    path(
        "api/admin/languages/<str:code>/thresholds/",
        lazy_view("library.admin_views.languages", "AdminLanguageThresholdsView"),
        name="admin-language-thresholds",
    ),
    # The switch. POST re-runs the checks server-side, records the launch, and
    # triggers the reader's rebuild — a prerendered site needs a build, so this
    # is deliberately not a bare status write.
    path(
        "api/admin/languages/<str:code>/go-live/",
        lazy_view("library.admin_views.languages", "AdminLanguageGoLiveView"),
        name="admin-language-go-live",
    ),
    # "status" is what was decided; this is what actually shipped.
    path(
        "api/admin/languages/<str:code>/deploy-check/",
        lazy_view("library.admin_views.languages", "AdminLanguageDeployCheckView"),
        name="admin-language-deploy-check",
    ),
    path("api/emails/", include("emails.urls")),
    path("api/feedback/", include("feedback.urls")),
    path("api/library/", include("library.urls")),
    path("api/reading/", include("reading.urls")),
]

# Django's own admin is mounted only in local DEBUG. In production the admin
# surface is the SPA dashboard, gated per-request by IsAdminEmail on the
# api/admin/* views; Django's password login is a redundant, weaker second door
# — unthrottled, no lockout, no 2FA — and mounting it on the public API origin
# is a standing brute-force target that bypasses the whole Supabase/allowlist
# model if a superuser is ever cracked. Kept in DEBUG, where clicking through
# models by hand is genuinely useful.
if settings.DEBUG:
    urlpatterns.append(path("admin/", admin.site.urls))
