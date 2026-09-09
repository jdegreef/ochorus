"""Admin dashboard API — the unified "needs attention" signals.

Read-only aggregation. It gathers the cheap content-health and demand signals
that otherwise live one-per-page (the dashboard, search, coverage) into a single
call, so the dashboard can lead with a prioritised "what needs me now?" panel.
The client owns the ranking, labels and links; this view only returns numbers.

Deliberately cheap: every query here is a count or a small aggregate. The heavy
book-qa scan (the advisory "quality flags") stays on ``/api/admin/audit/`` — it
would make this endpoint slow, and it is advisory, not attention.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import Author, Book, Chapter, Language, Plan, SearchQueryLog, Sermon


class AdminAttentionView(APIView):
    """Aggregated signals for the dashboard's attention hub. Ranked by the client."""

    permission_classes = [IsAdminEmail]

    def get(self, request):
        return Response(
            {
                "unreviewed_translations": Book.objects.filter(
                    source_type=Book.SourceType.AI_UNREVIEWED
                ).count(),
                "unpublished_books": Book.objects.filter(is_published=False).count(),
                "unpublished_sermons": Sermon.objects.filter(is_published=False).count(),
                # Imprints are bylines, not people — they never get a bio, so
                # counting them would leave this to-do permanently unfinishable
                # (mirrors AdminStatsView._attention).
                "authors_without_bio": Author.objects.filter(
                    bio="", is_imprint=False
                ).count(),
                # Integrity — cheap structural defects readers hit directly. The
                # fuller audit (broken plan days, chapter-order gaps) stays on
                # /api/admin/audit/; these two are counts, so they belong here.
                "empty_chapters": Chapter.objects.filter(word_count=0).count(),
                # Published only: a published book with no chapters renders an
                # empty reading page (a defect); an unpublished draft with none
                # yet is just work in progress.
                "empty_books": Book.objects.filter(is_published=True)
                .exclude(id__in=Chapter.objects.values("book_id"))
                .count(),
                "languages_missing_books": self._languages_missing_books(),
                "searches": self._searches(),
            }
        )

    def _languages_missing_books(self) -> list[dict]:
        """Registry languages that have OTHER content but no books — a reader can
        pick the language yet find nothing to read. A language with nothing at all
        is 'not started', not 'attention', so it is excluded."""
        book_langs = set(Book.objects.values_list("language", flat=True).distinct())
        sermon_counts = {
            r["language"]: r["n"]
            for r in Sermon.objects.values("language").annotate(n=Count("id"))
        }
        plan_langs = set(Plan.objects.values_list("language", flat=True).distinct())
        out = []
        for lang in Language.objects.all():
            if lang.code in book_langs:
                continue
            sermons = sermon_counts.get(lang.code, 0)
            if sermons or lang.code in plan_langs:
                out.append({"code": lang.code, "name": lang.name, "sermons": sermons})
        return out

    def _searches(self) -> dict:
        """Zero-result share over the last 30 days — the headline demand signal.
        Cheap aggregate over the anonymous SearchQueryLog (mirrors AdminSearchView)."""
        now = timezone.now()
        agg = SearchQueryLog.objects.filter(
            created_at__gte=now - timedelta(days=30)
        ).aggregate(total=Count("id"), zero=Count("id", filter=Q(result_count=0)))
        total = agg["total"] or 0
        zero = agg["zero"] or 0
        return {
            "total_30d": total,
            "zero_30d": zero,
            "zero_rate": round(zero / total, 3) if total else 0.0,
        }
