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
from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..admin_cache import ALIAS
from ..content_targets import LEVEL_1
from ..corrections import RETIRED_BOOKS
from ..engagement_trends import distinct_readers, latest_day, window
from ..models import (
    Book,
    Language,
    ReviewOutcome,
    SearchQueryLog,
    Sermon,
)
from ..views import _language_entry
from ..weeks import start_of, week_starts
from .health import health_history
from .targets import level_summary

#: Weekly points per sparkline — the Engagement page's own span.
WEEKS = 8
#: How long one computation is reused. Reader numbers move by the minute but
#: nobody reads a dashboard to the minute; Refresh (``?refresh=1``) recomputes.
CACHE_SECONDS = 300
_CACHE_KEY = "admin-trends"
_AI = (Book.SourceType.AI_REVIEWED, Book.SourceType.AI_UNREVIEWED)
#: Every pulse number's four windows: name → (days long, days back it ends).
_WINDOWS = {"d7": (7, 0), "d7_prev": (7, 7), "d30": (30, 0), "d30_prev": (30, 30)}


def _ai_editions(model) -> QuerySet:
    """A model's AI-translated editions — the review queue's population. A
    retired duplicate is unpublished and unreviewed for good, so it is never
    in it (``corrections.RETIRED_BOOKS``; books only)."""
    qs = model.objects.filter(source_type__in=_AI)
    return qs.exclude(slug__in=RETIRED_BOOKS) if model is Book else qs


def _counted(qs, field: str, now, starts, *, total=None) -> dict:
    """``qs`` counted (or ``total`` summed) in each pulse window and each
    charted week, in ONE aggregate — bucketed in the database rather than
    pulling every row of eight weeks into Python."""
    agg = (
        (lambda f: Sum(total, filter=f)) if total else (lambda f: Count("pk", filter=f))
    )
    spans = {
        name: (now - timedelta(days=days + back), now - timedelta(days=back))
        for name, (days, back) in _WINDOWS.items()
    }
    edges = [start_of(s) for s in starts] + [now + timedelta(days=1)]
    for n in range(len(starts)):
        spans[f"w{n}"] = (edges[n], edges[n + 1])
    out = qs.aggregate(
        **{
            name: agg(Q(**{f"{field}__gte": a, f"{field}__lt": b}))
            for name, (a, b) in spans.items()
        }
    )
    out = {k: v or 0 for k, v in out.items()}
    return {
        **{name: out[name] for name in _WINDOWS},
        "weekly": [out[f"w{n}"] for n in range(len(starts))],
    }


def _pulse(now) -> dict:
    """Readers, sign-ups, reading time and searches that found nothing: each
    as the last 7 and 30 days beside the 7 and 30 before, plus a weekly line."""
    from accounts.models import UserProfile
    from reading.models import ReadingSession

    starts = week_starts(now, WEEKS)

    # Readers come from the reading-day log, on its own day windows (the
    # Engagement page's rule: a reader is someone who read that day) — the four
    # pulse windows and the eight weeks in one query.
    ends = [s + timedelta(days=6) for s in starts]
    ends[-1] = max(ends[-1], latest_day(now))
    readers = distinct_readers(
        {name: window(now, days, back) for name, (days, back) in _WINDOWS.items()}
        | {f"w{n}": (s, e) for n, (s, e) in enumerate(zip(starts, ends, strict=True))}
    )
    return {
        "readers": {
            **{name: readers[name] for name in _WINDOWS},
            "weekly": [readers[f"w{n}"] for n in range(WEEKS)],
        },
        "signups": _counted(UserProfile.objects.all(), "created_at", now, starts),
        "reading_seconds": _counted(
            ReadingSession.objects.filter(seconds__gt=0),
            "last_seen_at",
            now,
            starts,
            total="seconds",
        ),
        "zero_searches": _counted(
            SearchQueryLog.objects.filter(result_count=0), "created_at", now, starts
        ),
        "weeks": [s.isoformat() for s in starts],
    }


def _languages(today) -> list[dict]:
    """Every target language's Level 1 progress, the share of its AI
    translations a person has approved, and its health line — the Language
    health page's own snapshots (``health_history``), read and never written:
    a dashboard load must not stamp a score of its own."""
    languages = [lang for lang in Language.objects.all() if not lang.is_source]
    codes = [lang.code for lang in languages]
    if not codes:
        return []
    level1 = level_summary(LEVEL_1, codes)

    ai: dict[str, dict] = {c: {"ai": 0, "unreviewed": 0} for c in codes}
    for model in (Book, Sermon):
        for r in (
            _ai_editions(model)
            .filter(language__in=codes)
            .values("language")
            .annotate(
                n=Count("pk"),
                waiting=Count(
                    "pk", filter=Q(source_type=Book.SourceType.AI_UNREVIEWED)
                ),
            )
        ):
            ai[r["language"]]["ai"] += r["n"]
            ai[r["language"]]["unreviewed"] += r["waiting"]

    history = health_history(today)
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
    waiting = 0
    oldest = None
    arrivals = [0] * WEEKS
    for kind, model in (("book", Book), ("sermon", Sermon)):
        ai = _ai_editions(model)
        unreviewed = ai.filter(source_type=Book.SourceType.AI_UNREVIEWED)
        waiting += unreviewed.count()
        first = unreviewed.order_by("created_at", "pk").values(
            "slug", "language", "title", "created_at"
        )[:1]
        for row in first:
            if oldest is None or row["created_at"] < oldest["created_at"]:
                oldest = {**row, "kind": kind}
        weekly = _counted(ai, "created_at", now, starts)["weekly"]
        arrivals = [a + b for a, b in zip(arrivals, weekly, strict=True)]

    decisions = ReviewOutcome.objects.filter(kind__in=("book", "sermon"))
    approvals = _counted(
        decisions.filter(outcome=ReviewOutcome.Outcome.APPROVED),
        "confirmed_at",
        now,
        starts,
    )["weekly"]
    if oldest:
        oldest["created_at"] = oldest["created_at"].isoformat()
    return {
        "waiting": waiting,
        "oldest": oldest,
        "weeks": [s.isoformat() for s in starts],
        "arrived": arrivals,
        "approved": approvals,
        "has_decisions": decisions.exists(),
    }


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
