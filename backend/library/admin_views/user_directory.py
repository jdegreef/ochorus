"""Admin dashboard API — the searchable user directory.

The aggregate :class:`AdminUsersView` names only the 25 most recent sign-ups, so
every other account was unreachable — you couldn't open its per-user page
(:class:`AdminUserDetailView`) because you couldn't find it. This is the index
that makes every reader reachable: search by name or email, sort by sign-up /
last-seen / activity, paginate, and click through.

Admin-only (``IsAdminEmail``). Read-only, and each row carries only the
at-a-glance fields the table shows plus the ``uid`` to link on; the full picture
lives on the detail page.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..views import _language_entry
from .analytics import _provider_label

# One page of the directory. Fixed (not client-controlled) so a caller can't ask
# for an unbounded slice.
PAGE_SIZE = 50

# The orderings the table offers. Each is a list of order_by args; last_seen puts
# never-seen accounts last regardless of direction.
SORTS = {
    "recent": ["-created_at"],
    "seen": ["-last_seen_at", "-created_at"],
    "active": ["-reading_seconds", "-created_at"],
    "name": ["display_name", "email"],
}
DEFAULT_SORT = "recent"


class AdminUserDirectoryView(APIView):
    """A searchable, paginated index of every account, each linking to its page."""

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from django.db.models import (
            Count,
            IntegerField,
            OuterRef,
            Q,
            Subquery,
            Sum,
        )
        from django.db.models.functions import Coalesce

        from accounts.models import UserProfile
        from reading.models import ReadingProgress, ReadingSession

        # Per-profile rollups as correlated subqueries — NOT two annotate() joins,
        # which would multiply (each progress row × each session row) and inflate
        # both totals.
        works_sq = Subquery(
            ReadingProgress.objects.filter(profile=OuterRef("pk"))
            .values("profile")
            .annotate(n=Count("id"))
            .values("n")[:1],
            output_field=IntegerField(),
        )
        seconds_sq = Subquery(
            ReadingSession.objects.filter(profile=OuterRef("pk"), seconds__gt=0)
            .values("profile")
            .annotate(s=Sum("seconds"))
            .values("s")[:1],
            output_field=IntegerField(),
        )
        qs = UserProfile.objects.annotate(
            works=Coalesce(works_sq, 0),
            reading_seconds=Coalesce(seconds_sq, 0),
        )

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(display_name__icontains=q))

        sort = request.query_params.get("sort") or DEFAULT_SORT
        if sort not in SORTS:
            sort = DEFAULT_SORT
        # `last_seen_at` is nullable; keep never-seen accounts at the bottom of the
        # "seen" sort rather than letting NULLs float to the top.
        if sort == "seen":
            from django.db.models import F

            qs = qs.order_by(F("last_seen_at").desc(nulls_last=True), "-created_at")
        else:
            qs = qs.order_by(*SORTS[sort])

        total = qs.count()
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = self._page(request, pages)
        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start : start + PAGE_SIZE])

        return Response(
            {
                "results": [self._row(p) for p in rows],
                "total": total,
                "page": page,
                "pages": pages,
                "page_size": PAGE_SIZE,
                "sort": sort,
                "q": q,
            }
        )

    def _page(self, request, pages) -> int:
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        return min(max(1, page), pages)

    def _row(self, p) -> dict:
        return {
            "uid": str(p.supabase_uid),
            "display_name": p.display_name,
            "email": p.email,
            "providers": [
                {"code": c, "label": _provider_label(c)} for c in p.provider_list
            ],
            "locale": p.locale,
            "locale_name": _language_entry(p.locale)["name"],
            "joined_at": p.created_at.isoformat(),
            "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
            "works": p.works,
            "reading_seconds": p.reading_seconds,
        }
