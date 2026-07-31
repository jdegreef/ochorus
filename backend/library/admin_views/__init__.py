"""Admin dashboard API, split by concern.

Previously one 1,190-line module. The view classes are re-exported here so
``from library.admin_views import AdminStatsView`` (config/urls.py) is unchanged.
"""

from .analytics import (
    AdminEngagementView,
    AdminSearchGapView,
    AdminSearchView,
    AdminUsersView,
)
from .content import (
    AdminCoverageView,
    AdminLanguageCreateView,
    AdminLanguageDeployCheckView,
    AdminLanguageDetailView,
    AdminLanguageGoLiveView,
    AdminLanguageReadinessView,
    AdminLanguageSettingsView,
    AdminLanguageThresholdsView,
    AdminStatsView,
)
from .detail import AdminBookDetailView, AdminExportView
from .jobs import AdminTranslationJobsView
from .quality import AdminAuditView, AdminReviewQueueView

__all__ = [
    "AdminAuditView",
    "AdminBookDetailView",
    "AdminCoverageView",
    "AdminEngagementView",
    "AdminSearchGapView",
    "AdminSearchView",
    "AdminExportView",
    "AdminLanguageCreateView",
    "AdminLanguageDeployCheckView",
    "AdminLanguageDetailView",
    "AdminLanguageGoLiveView",
    "AdminLanguageReadinessView",
    "AdminLanguageSettingsView",
    "AdminLanguageThresholdsView",
    "AdminReviewQueueView",
    "AdminStatsView",
    "AdminTranslationJobsView",
    "AdminUsersView",
]
