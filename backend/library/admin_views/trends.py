"""Admin dashboard API — how things are moving: the reader pulse, each
language's progress toward its Level 1 target, and the review backlog.

The stats beside it (``content.AdminStatsView``) are what the library *is*;
this is what it is *doing*. Its numbers move with time, not with content, so
they get a short time-based memo rather than the stats' content-revision one.

Everything here is a summary of something a fuller page already shows — the
Engagement page's pulse, the Language health page's Level 1 pill and trend, the
review queue — computed with those pages' own helpers so a number on the
dashboard is the number you find when you click through.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import caches
from django.db.models import Count, Min, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..admin_cache import ALIAS
from ..content_targets import LEVEL_1
from ..corrections import RETIRED_BOOKS
from ..engagement_trends import distinct_readers, weekly_active, weekly_signups, window
from ..models import (
    Book,
    Language,
    LanguageHealthSnapshot,
    ReviewOutcome,
    SearchQueryLog,
    Sermon,
)
from ..views import _language_entry
from ..weeks import start_of, week_starts, weekly_counts, weekly_sums
from .health import SCORE_VERSION
from .targets import level_summary

#: Weekly points per sparkline — the Engagement page's own span.
WEEKS = 8
#: How long one computation is reused. Reader numbers move by the minute but
#: nobody reads a dashboard to the minute; Refresh (``?refresh=1``) recomputes.
CACHE_SECONDS = 300
_CACHE_KEY = "admin-trends"
_AI = (Book.SourceType.AI_REVIEWED, Book.SourceType.AI_UNREVIEWED)


def _periods(now) -> dict[str, tuple]:
    """The four windows every pulse number is given in, as moments."""
    return {
        "d7": (now - timedelta(days=7), now),
        "d7_prev": (now - timedelta(days=14), now - timedelta(days=7)),
        "d30": (now - timedelta(days=30), now),
        "d30_prev": (now - timedelta(days=60), now - timedelta(days=30)),
    }


def _in_periods(qs, field: str, now, *, total=None) -> dict[str, int]:
    """``qs`` counted (or ``total`` summed) in each of the four windows, in one
    query."""
    agg = (
        (lambda f: Sum(total, filter=f)) if total else (lambda f: Count("pk", filter=f))
    )
    out = qs.aggregate(
        **{
            name: agg(Q(**{f"{field}__gte": a, f"{field}__lt": b}))
            for name, (a, b) in _periods(now).items()
        }
    )
    return {k: v or 0 for k, v in out.items()}


def _pulse(now) -> dict:
    """Readers, sign-ups, reading time and searches that found nothing: each
    as the last 7 and 30 days beside the 7 and 30 before, plus a weekly line."""
    from accounts.models import UserProfile
    from reading.models import ReadingSession

    starts = week_starts(now, WEEKS)
    since = start_of(starts[0])

    # Readers come from the reading-day log, on its own day windows (the
    # Engagement page's rule: a reader is someone who read that day).
    reader_windows = {
        "d7": window(now, 7),
        "d7_prev": window(now, 7, 7),
        "d30": window(now, 30),
        "d30_prev": window(now, 30, 30),
    }
    readers = distinct_readers(reader_windows)

    sessions = ReadingSession.objects.filter(seconds__gt=0)
    zero = SearchQueryLog.objects.filter(result_count=0)
    return {
        "readers": {
            **readers,
            "weekly": [w["readers"] for w in weekly_active(now, WEEKS)],
        },
        "signups": {
            **_in_periods(UserProfile.objects.all(), "created_at", now),
            "weekly": weekly_signups(starts),
        },
        "reading_seconds": {
            **_in_periods(sessions, "last_seen_at", now, total="seconds"),
            "weekly": weekly_sums(
                sessions.filter(last_seen_at__gte=since).values_list(
                    "last_seen_at", "seconds"
                ),
                starts,
            ),
        },
        "zero_searches": {
            **_in_periods(zero, "created_at", now),
            "weekly": weekly_counts(
                zero.filter(created_at__gte=since).values_list("created_at", flat=True),
                starts,
            ),
        },
        "weeks": [s.isoformat() for s in starts],
    }


def _languages(today) -> list[dict]:
    """Every target language's Level 1 progress, the share of its AI
    translations a person has approved, and its health line.

    The health line is READ from the daily snapshots, never written: the
    Language health page records them (and the deploy chain does), and a
    dashboard load must not stamp a score of its own."""
    languages = [lang for lang in Language.objects.all() if not lang.is_source]
    codes = [lang.code for lang in languages]
    if not codes:
        return []
    level1 = level_summary(LEVEL_1, codes)

    ai: dict[str, dict] = {c: {"ai": 0, "unreviewed": 0} for c in codes}
    for model in (Book, Sermon):
        rows = (
            model.objects.filter(language__in=codes, source_type__in=_AI)
            .exclude(slug__in=RETIRED_BOOKS if model is Book else ())
            .values("language")
            .annotate(
                n=Count("pk"),
                waiting=Count(
                    "pk", filter=Q(source_type=Book.SourceType.AI_UNREVIEWED)
                ),
            )
        )
        for r in rows:
            ai[r["language"]]["ai"] += r["n"]
            ai[r["language"]]["unreviewed"] += r["waiting"]

    history: dict[str, list[int]] = {}
    for code, health in (
        LanguageHealthSnapshot.objects.filter(
            language__in=codes,
            score_version=SCORE_VERSION,
            date__gt=today - timedelta(weeks=WEEKS),
        )
        .order_by("date")
        .values_list("language", "health")
    ):
        history.setdefault(code, []).append(health)

    out = []
    for lang in languages:
        counts = ai[lang.code]
        reviewed = counts["ai"] - counts["unreviewed"]
        out.append(
            {
                "code": lang.code,
                "name": _language_entry(lang.code)["name"],
                "is_live": lang.status == Language.Status.LIVE,
                "level1": level1[lang.code],
                "ai_translations": counts["ai"],
                "unreviewed": counts["unreviewed"],
                # None, not 0%, for a language with no AI translations at all.
                "reviewed_share": round(reviewed / counts["ai"], 3)
                if counts["ai"]
                else None,
                "health": history.get(lang.code, []),
            }
        )
    # The furthest from its target first: that is where the work is.
    out.sort(
        key=lambda r: (r["level1"]["done"] / (r["level1"]["total"] or 1), r["code"])
    )
    return out


def _review(now) -> dict:
    """The AI-translation review backlog: what is waiting, the oldest of it,
    and each week's arrivals beside each week's approvals.

    "Arrived" is when an AI edition's row was created (it enters the queue as
    unreviewed); "approved" is when an approver confirmed it (a provisional
    decision isn't an approval yet). Books and sermons — the queue's bios have
    no creation date that means "arrived for review"."""
    starts = week_starts(now, WEEKS)
    since = start_of(starts[0])

    waiting = 0
    oldest = None
    arrivals = [0] * WEEKS
    for kind, model in (("book", Book), ("sermon", Sermon)):
        ai = model.objects.filter(source_type__in=_AI)
        if model is Book:
            ai = ai.exclude(slug__in=RETIRED_BOOKS)
        unreviewed = ai.filter(source_type=Book.SourceType.AI_UNREVIEWED)
        waiting += unreviewed.count()
        first = unreviewed.order_by("created_at", "pk").values(
            "slug", "language", "title", "created_at"
        )[:1]
        for row in first:
            if oldest is None or row["created_at"] < oldest["created_at"]:
                oldest = {**row, "kind": kind}
        weekly = weekly_counts(
            ai.filter(created_at__gte=since).values_list("created_at", flat=True),
            starts,
        )
        arrivals = [a + b for a, b in zip(arrivals, weekly, strict=True)]

    approvals = weekly_counts(
        ReviewOutcome.objects.filter(
            kind__in=("book", "sermon"),
            outcome=ReviewOutcome.Outcome.APPROVED,
            confirmed_at__gte=since,
        ).values_list("confirmed_at", flat=True),
        starts,
    )
    if oldest:
        oldest["created_at"] = oldest["created_at"].isoformat()
    return {
        "waiting": waiting,
        "oldest": oldest,
        "weeks": [s.isoformat() for s in starts],
        "arrived": arrivals,
        "approved": approvals,
        "first_decision": _first(
            ReviewOutcome.objects.aggregate(at=Min("decided_at"))["at"]
        ),
    }


def _first(at) -> str | None:
    return at.isoformat() if at else None


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminTrendsView(APIView):
    """``GET /api/admin/trends/`` — pulse, language progress, review backlog."""

    def get(self, request):
        cache = caches[ALIAS]
        refresh = request.query_params.get("refresh") in ("1", "true", "yes")
        data = None if refresh else cache.get(_CACHE_KEY)
        if data is None:
            now = timezone.now()
            data = {
                "pulse": _pulse(now),
                "languages": _languages(timezone.localdate()),
                "review": _review(now),
                "computed_at": now.isoformat(),
            }
            cache.set(_CACHE_KEY, data, CACHE_SECONDS)
        return Response(data)
