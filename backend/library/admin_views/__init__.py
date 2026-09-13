"""Admin dashboard API, split by concern.

Previously one 1,190-line module. The view classes are re-exported here so
``from library.admin_views import AdminStatsView`` (config/urls.py) is unchanged
— which is what lets a module be split again without touching the URL conf.
"""

from .activity import AdminActivityView
from .analytics import (
    AdminEngagementView,
    AdminSearchGapView,
    AdminSearchView,
    AdminUsersView,
)
from .attention import (
    AdminAttentionView,
    AdminAuthorsWithoutBioView,
    AdminUnpublishedView,
)
from .content import (
    AdminCoverageView,
    AdminLanguageDetailView,
    AdminStatsView,
)
from .content_jobs import AdminContentEditJobsView
from .detail import (
    AdminBookDetailView,
    AdminBookPublishView,
    AdminExportView,
    AdminSermonDetailView,
    AdminSermonPublishView,
)
from .jobs import AdminTranslationJobsView
from .languages import (
    AdminLanguageCreateView,
    AdminLanguageDeployCheckView,
    AdminLanguageGoLiveView,
    AdminLanguageReadinessView,
    AdminLanguageSettingsView,
    AdminLanguageThresholdsView,
)
from .quality import (
    AdminAuditDismissView,
    AdminAuditView,
    AdminReviewDetailView,
    AdminReviewQueueView,
    AdminVerseReviewView,
)
from .user_detail import AdminUserDetailView
from .user_directory import AdminUserDirectoryView

__all__ = [
    "AdminActivityView",
    "AdminAttentionView",
    "AdminAuthorsWithoutBioView",
    "AdminAuditDismissView",
    "AdminAuditView",
    "AdminBookDetailView",
    "AdminBookPublishView",
    "AdminContentEditJobsView",
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
    "AdminReviewDetailView",
    "AdminReviewQueueView",
    "AdminSermonDetailView",
    "AdminSermonPublishView",
    "AdminVerseReviewView",
    "AdminStatsView",
    "AdminTranslationJobsView",
    "AdminUnpublishedView",
    "AdminUserDetailView",
    "AdminUserDirectoryView",
    "AdminUsersView",
]
