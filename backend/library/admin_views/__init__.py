"""Admin dashboard API, split by concern.

Previously one 1,190-line module. The view classes are re-exported here so
``from library.admin_views import AdminStatsView`` keeps working wherever it is
written. config/urls.py is the exception: it routes each view lazily by the
submodule that DEFINES it (config/lazy_views.py), so moving a view to another
submodule means updating its line there — config.tests_lazy_views names it.
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
from .covers import AdminCoversView
from .demand import AdminLanguageWantedView
from .detail import (
    AdminBookDetailView,
    AdminBookPublishView,
    AdminExportView,
    AdminSermonDetailView,
    AdminSermonPublishView,
)
from .dropoff import AdminDropOffView
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
from .targets import AdminLanguageTargetsView
from .team import AdminRolesView, AdminTeamView
from .user_delete import AdminUserDeleteView
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
    "AdminCoversView",
    "AdminDropOffView",
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
    "AdminLanguageTargetsView",
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
    "AdminUserDeleteView",
    "AdminUserDetailView",
    "AdminUserDirectoryView",
    "AdminUsersView",
]
