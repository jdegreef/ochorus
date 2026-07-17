"""Admin dashboard API, split by concern.

Previously one 1,190-line module. The view classes are re-exported here so
``from library.admin_views import AdminStatsView`` (config/urls.py) is unchanged.
"""

from .analytics import AdminEngagementView, AdminUsersView
from .content import AdminCoverageView, AdminLanguageDetailView, AdminStatsView
from .detail import AdminBookDetailView, AdminExportView
from .jobs import AdminTranslationJobsView
from .quality import AdminAuditView, AdminReviewQueueView

__all__ = [
    "AdminAuditView",
    "AdminBookDetailView",
    "AdminCoverageView",
    "AdminEngagementView",
    "AdminExportView",
    "AdminLanguageDetailView",
    "AdminReviewQueueView",
    "AdminStatsView",
    "AdminTranslationJobsView",
    "AdminUsersView",
]
