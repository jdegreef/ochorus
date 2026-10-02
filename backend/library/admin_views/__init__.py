"""Admin dashboard API, split by concern.

Previously one 1,190-line module. The view classes are re-exported here so
``from library.admin_views import AdminStatsView`` (config/urls.py) is unchanged
— which is what lets a module be split again without touching the URL conf.
"""

from .activity import AdminActivityView
from .analytics import (
    AdminEngagementView,
    AdminSearchDecisionListView,
    AdminSearchDecisionView,
    AdminSearchGapView,
    AdminSearchPreviewView,
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
    AdminTranslationMarkCurrentView,
)
from .content_jobs import AdminContentEditJobsView
from .demand import AdminLanguageWantedView
from .detail import (
    AdminBookDetailView,
    AdminBookPublishView,
    AdminExportView,
    AdminSermonDetailView,
    AdminSermonPublishView,
)
from .health import AdminLanguageHealthView
from .jobs import AdminTranslationJobsView
from .languages import (
    AdminLanguageCreateView,
    AdminLanguageDeployCheckView,
    AdminLanguageGoLiveView,
    AdminLanguageReadinessView,
    AdminLanguageSettingsView,
    AdminLanguageThresholdsView,
)
from .manual import AdminLanguageManualView, AdminManualView
from .quality import (
    AdminAuditDismissView,
    AdminAuditView,
    AdminReviewDetailView,
    AdminReviewQueueView,
    AdminVerseReviewView,
)
from .team import AdminRolesView, AdminTeamView
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
    "AdminTranslationMarkCurrentView",
    "AdminLanguageHealthView",
    "AdminLanguageManualView",
    "AdminManualView",
    "AdminEngagementView",
    "AdminSearchDecisionListView",
    "AdminSearchDecisionView",
    "AdminSearchGapView",
    "AdminSearchPreviewView",
    "AdminSearchView",
    "AdminExportView",
    "AdminLanguageCreateView",
    "AdminLanguageDeployCheckView",
    "AdminLanguageDetailView",
    "AdminLanguageWantedView",
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
    "AdminRolesView",
    "AdminTeamView",
    "AdminTranslationJobsView",
    "AdminUnpublishedView",
    "AdminUserDetailView",
    "AdminUserDirectoryView",
    "AdminUsersView",
]
