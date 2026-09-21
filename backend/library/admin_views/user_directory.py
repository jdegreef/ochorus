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

from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import is_admin_user, requires

from ..views import _language_entry
from .analytics import _profile_summary, mask_email
from .csv_export import csv_response, csv_safe

# One page of the directory. Fixed (not client-controlled) so a caller can't ask
# for an unbounded slice.
PAGE_SIZE = 50

# The orderings the table offers, as order_by args. Every one ends in
# ``supabase_uid`` so paging is stable — without a unique final key, rows that tie
# on the visible columns (e.g. two blank-name accounts under "name") have an
# undefined order and can repeat or vanish across pages. ``seen`` keeps never-seen
# accounts (null ``last_seen_at``) at the bottom regardless of direction.
SORTS = {
    "recent": ["-created_at", "supabase_uid"],
    "seen": [F("last_seen_at").desc(nulls_last=True), "-created_at", "supabase_uid"],
    "active": ["-reading_seconds", "-created_at", "supabase_uid"],
    "name": ["display_name", "email", "supabase_uid"],
}
DEFAULT_SORT = "recent"


@requires(AdminCapability.USERS, verb=AdminVerb.VIEW)
class AdminUserDirectoryView(APIView):
    """A searchable, paginated index of every account, each linking to its page."""


    def get(self, request):
        # Reader emails are PII: only a super admin sees them in the clear; a
        # scoped USERS grantee (a language admin) gets them masked at the source.
        # Computed first because `_queryset` also uses it — a non-super caller must
        # not be able to search or sort on the cleartext column (an oracle that
        # would defeat the display masking), so the email filter/sort is theirs only.
        reveal = is_admin_user(request.user, request)
        qs, sort, q = self._queryset(request, reveal=reveal)

        # ``?fmt=csv`` downloads every matching row (the whole filtered/sorted
        # set, no pagination) — see AdminExportView for the same convention and
        # why it isn't the DRF-reserved ``format`` param.
        if request.query_params.get("fmt", "").lower() == "csv":
            return self._csv(qs, reveal=reveal)

        total = qs.count()
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = self._page(request, pages)
        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start : start + PAGE_SIZE])

        return Response(
            {
                "results": [self._row(p, reveal=reveal) for p in rows],
                "total": total,
                "page": page,
                "pages": pages,
                "page_size": PAGE_SIZE,
                "sort": sort,
                "q": q,
            }
        )

    def _queryset(self, request, *, reveal: bool):
        """The annotated, searched, sorted queryset shared by the JSON page and
        the CSV export. Returns ``(qs, sort, q)``.

        ``reveal`` (the requester's super-admin flag) governs whether the *raw
        email column* may be searched or sorted on: for a non-super caller it may
        not, or the ``icontains`` search and the name-sort tiebreak would be a
        cleartext-PII oracle that reads around the display masking."""
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
            # Search display name always; the email column only for a super admin —
            # otherwise `icontains` is a cleartext oracle over addresses the caller
            # is only allowed to see masked.
            cond = Q(display_name__icontains=q)
            if reveal:
                cond |= Q(email__icontains=q)
            qs = qs.filter(cond)

        sort = request.query_params.get("sort") or DEFAULT_SORT
        if sort not in SORTS:
            sort = DEFAULT_SORT
        # Same reason: drop the email tiebreak from the ordering for a non-super
        # caller (alphabetical-by-email leaks order over cleartext). Stability is
        # kept — every ordering still ends in the unique supabase_uid.
        order = SORTS[sort] if reveal else [k for k in SORTS[sort] if k != "email"]
        qs = qs.order_by(*order)
        return qs, sort, q

    def _csv(self, qs, *, reveal: bool = False):
        """The directory as a CSV download. For a super admin, emails are in the
        clear — this is an authed admin export, its whole purpose — unlike the
        masked-by-default UI; for a scoped USERS grantee they are masked here too,
        so the export can't route around the source-level masking.
        ``reading_seconds`` is raw for spreadsheet analysis; iterate so a large
        user base doesn't all sit in memory at once."""
        import csv
        import io

        from django.utils import timezone

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "name",
                "email",
                "providers",
                "language",
                "joined",
                "last_seen",
                "works",
                "reading_seconds",
            ]
        )
        for p in qs.iterator():
            writer.writerow(
                [
                    csv_safe(p.display_name),
                    csv_safe(p.email if reveal else mask_email(p.email)),
                    csv_safe(" ".join(p.provider_list)),
                    csv_safe(p.locale),
                    p.created_at.date().isoformat(),
                    p.last_seen_at.date().isoformat() if p.last_seen_at else "",
                    p.works,
                    p.reading_seconds,
                ]
            )
        stamp = timezone.now().date().isoformat()
        return csv_response(buf.getvalue(), f"ochorus-users-{stamp}.csv")

    def _page(self, request, pages) -> int:
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        return min(max(1, page), pages)

    def _row(self, p, *, reveal: bool = False) -> dict:
        # The shared per-account summary (uid/name/email/providers/locale/dates),
        # plus this page's rollups. ``reveal`` masks the email for non-super admins.
        return {
            **_profile_summary(p, reveal=reveal),
            "locale_name": _language_entry(p.locale)["name"],
            "works": p.works,
            "reading_seconds": p.reading_seconds,
        }
