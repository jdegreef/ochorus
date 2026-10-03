"""The weekly lines behind the Engagement page's pulse tiles.

Each series is oldest first and ends on the week in progress, on the same
Monday weeks as the weekly readers chart (``library.weeks``), so a tile's
points line up with the chart's bars.

Two tiles have no line on purpose. "Marked chapters" has none because a
reader's marks keep only a last-updated time, so there is no record of when
each was made. "Readers" has none of its own either; its history is
back-filled from the reading-day log (below), the one table that records
which day someone read.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.db.models import Count, Min, Q

from .weeks import day_of, start_of, week_start, week_starts, weekly_counts, weekly_sums

#: The rolling windows behind the "Active · 30d" line: six 30-day windows,
#: the last ending now, so its final point is the same window as the tile.
MONTH_WINDOWS = 6


def _running_total(now_total: int, new_per_week: list[int]) -> list[int]:
    """A running total that ends on ``now_total``, stepped back one week at a
    time by what that week added. Anything with no recorded start counts as
    having been there all along."""
    out, total = [], now_total
    for added in reversed(new_per_week):
        out.append(total)
        total -= added
    return out[::-1]


def active_readers(today, days: int, offset: int = 0) -> int:
    """Readers who read on any day of the ``days`` days ending ``offset`` days
    before ``today`` (``active_readers(today, 7)`` is the last 7 days,
    ``(today, 7, 7)`` the 7 before that). From the reading-day log, which
    keeps every day a reader read; saved progress keeps only each work's
    latest touch, so a reader active in two weeks would count in one."""
    from reading.models import ReadingDay

    end = today - timedelta(days=offset)
    return (
        ReadingDay.objects.filter(day__gt=end - timedelta(days=days), day__lte=end)
        .values("profile")
        .distinct()
        .count()
    )


def weekly_active(now, weeks: int) -> list[dict]:
    """Readers who read in each charted week, from the reading-day log: a
    reader counts in every week they read, in one query."""
    from reading.models import ReadingDay

    starts = week_starts(now, weeks)
    readers: dict = {s: set() for s in starts}
    for profile, day in ReadingDay.objects.filter(day__gte=starts[0]).values_list(
        "profile", "day"
    ):
        week = week_start(day)
        if week in readers:
            readers[week].add(profile)
    return [{"week": s.isoformat(), "readers": len(readers[s])} for s in starts]


def weekly_signups(starts) -> list[int]:
    """Accounts created in each week beginning ``starts``: the Users page's
    sign-up chart and the Registered users tile's line."""
    from accounts.models import UserProfile

    return weekly_counts(
        UserProfile.objects.filter(created_at__gte=start_of(starts[0])).values_list(
            "created_at", flat=True
        ),
        starts,
    )


def pulse_trends(now, weeks: int, *, readers: int, users: int) -> dict:
    """``readers`` and ``users`` are the tiles' own totals, so each running
    total ends exactly on the number shown above it."""
    from reading.models import Favorite, ReadingDay, ReadingProgress, ReadingSession

    starts = week_starts(now, weeks)
    since = start_of(starts[0])

    hearts = weekly_counts(
        Favorite.objects.filter(created_at__gte=since).values_list(
            "created_at", flat=True
        ),
        starts,
    )
    reading_seconds = weekly_sums(
        ReadingSession.objects.filter(
            last_seen_at__gte=since, seconds__gt=0
        ).values_list("last_seen_at", "seconds"),
        starts,
    )
    new_users = weekly_signups(starts)
    # A reader's first reading day, from the streak log: when they arrived.
    # Only readers the tile counts (they have saved progress), who read in the
    # charted weeks and never before them, so the back-filled total can't
    # fall below zero or count anyone the tile doesn't.
    arrived = Counter(
        week_start(day)
        for day in ReadingDay.objects.filter(
            day__gte=starts[0], profile__in=ReadingProgress.objects.values("profile")
        )
        .exclude(
            profile__in=ReadingDay.objects.filter(day__lt=starts[0]).values("profile")
        )
        .values("profile")
        .annotate(first=Min("day"))
        .values_list("first", flat=True)
    )
    new_readers = [arrived.get(s, 0) for s in starts]

    # Readers who read on any day of each window, in one pass: the same count
    # as the tile (``active_readers``), so the last point is its number.
    today = day_of(now)
    ends = [today - timedelta(days=30 * i) for i in range(MONTH_WINDOWS - 1, -1, -1)]
    counts = ReadingDay.objects.filter(
        day__gt=ends[0] - timedelta(days=30), day__lte=today
    ).aggregate(
        **{
            f"w{i}": Count(
                "profile",
                distinct=True,
                filter=Q(day__gt=end - timedelta(days=30), day__lte=end),
            )
            for i, end in enumerate(ends)
        }
    )

    return {
        "hearts": hearts,
        "reading_seconds": reading_seconds,
        "users": _running_total(users, new_users),
        "readers": _running_total(readers, new_readers),
        "active_30d": [
            {"end": end.isoformat(), "readers": counts[f"w{i}"]}
            for i, end in enumerate(ends)
        ],
    }
