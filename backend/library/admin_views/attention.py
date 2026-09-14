"""Admin dashboard API — the unified "needs attention" signals.

Read-only aggregation. It gathers the cheap content-health and demand signals
that otherwise live one-per-page (the dashboard, search, coverage) into a single
call, so the dashboard can lead with a prioritised "what needs me now?" panel.
The client owns the ranking, labels and links; this view only returns numbers.

Deliberately cheap: every query here is a count or a small aggregate. The heavy
book-qa scan (the advisory "quality flags") stays on ``/api/admin/audit/`` — it
would make this endpoint slow, and it is advisory, not attention.

Two of those counts also get an enumerated worklist here — unpublished content
(``AdminUnpublishedView``) and authors without a bio
(``AdminAuthorsWithoutBioView``) — the same signals, listed, so the dashboard's
attention chips can link somewhere actionable instead of reporting a number with
no way to act on it. They are separate endpoints, fetched only when the reader
opens the worklist, so the dashboard's own attention call stays counts-only.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..models import Author, Book, Chapter, Language, Plan, SearchQueryLog, Sermon


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminAttentionView(APIView):
    """Aggregated signals for the dashboard's attention hub. Ranked by the client."""


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


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminUnpublishedView(APIView):
    """The unpublished books and sermons behind the dashboard's unpublished
    counts — the worklist its "unpublished books/sermons" chips link to.

    Books link on to their admin detail page, where the publish toggle lives;
    sermons have no admin detail yet, so the client links them to their reader
    page. Ordered author-then-title so a person's drafts sit together. No
    pagination: unpublished work is a bounded backlog, not a growing log.
    """


    def get(self, request):
        books = [
            {
                "slug": b.slug,
                "language": b.language,
                "title": b.title,
                "author": b.author.name,
                "chapters": b.num_chapters,
                "words": b.words or 0,
            }
            for b in Book.objects.filter(is_published=False)
            .select_related("author")
            .annotate(num_chapters=Count("chapters"), words=Sum("chapters__word_count"))
            .order_by("author__name", "title", "language")
        ]
        sermons = [
            {
                "slug": s.slug,
                "language": s.language,
                "title": s.title,
                "author": s.author.name,
            }
            for s in Sermon.objects.filter(is_published=False)
            .select_related("author")
            .order_by("author__name", "title", "language")
        ]
        return Response({"books": books, "sermons": sermons})


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminAuthorsWithoutBioView(APIView):
    """Authors with an empty short bio — the worklist behind the "authors
    without a bio" chip, feeding the write-biography workflow.

    Imprints are excluded for the same reason the count excludes them: a byline
    like "Ochorus Originals" is not a person and never gets a bio, so counting
    it would leave the to-do permanently unfinishable. Ranked by how much
    content the author carries, so the highest-value gaps come first.
    """


    def get(self, request):
        # Count distinct WORKS, not editions: `books__slug` collapses the same
        # book in several languages to one, so an author isn't ranked "5 books"
        # for one work translated five ways. `n_books`/`n_sermons` (not
        # `books`/`sermons`) because an annotation may not shadow the
        # reverse-relation accessor of the same name (related_name), which raises
        # at query build; `distinct=True` also undoes the books×sermons join
        # cross-product so each count stands alone.
        authors = (
            Author.objects.filter(bio="", is_imprint=False)
            .annotate(
                n_books=Count("books__slug", distinct=True),
                n_sermons=Count("sermons__slug", distinct=True),
            )
            .order_by("-n_books", "-n_sermons", "name")
        )
        return Response(
            [
                {"slug": a.slug, "name": a.name, "books": a.n_books, "sermons": a.n_sermons}
                for a in authors
            ]
        )
