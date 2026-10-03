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

from django.db.models import Count, Min, Sum
from django.db.models.functions import TruncWeek

from .weeks import day_of, week_start, week_starts

#: The rolling windows behind the "Active · 30d" line: six 30-day windows,
#: the last ending now, so its final point is the same window as the tile.
MONTH_WINDOWS = 6


def _weekly(rows, starts) -> list[int]:
    """``(week datetime, n)`` rows from a TruncWeek query, as one value per
    charted week (0 where a week has none)."""
    by_week = {week_start(day_of(w)): n or 0 for w, n in rows}
    return [by_week.get(s, 0) for s in starts]


def _running_total(now_total: int, new_per_week: list[int]) -> list[int]:
    """A running total that ends on ``now_total``, stepped back one week at a
    time by what that week added. Anything with no recorded start counts as
    having been there all along."""
    out, total = [], now_total
    for added in reversed(new_per_week):
        out.append(total)
        total -= added
    return out[::-1]


def pulse_trends(now, weeks: int, *, readers: int, users: int) -> dict:
    """``readers`` and ``users`` are the tiles' own totals, so each running
    total ends exactly on the number shown above it."""
    from accounts.models import UserProfile
    from reading.models import Favorite, ReadingDay, ReadingSession

    starts = week_starts(now, weeks)
    first = starts[0]

    hearts = _weekly(
        Favorite.objects.filter(created_at__date__gte=first)
        .annotate(w=TruncWeek("created_at"))
        .values_list("w")
        .annotate(n=Count("id"))
        .order_by(),
        starts,
    )
    reading_seconds = _weekly(
        ReadingSession.objects.filter(last_seen_at__date__gte=first, seconds__gt=0)
        .annotate(w=TruncWeek("last_seen_at"))
        .values_list("w")
        .annotate(n=Sum("seconds"))
        .order_by(),
        starts,
    )
    new_users = _weekly(
        UserProfile.objects.filter(created_at__date__gte=first)
        .annotate(w=TruncWeek("created_at"))
        .values_list("w")
        .annotate(n=Count("id"))
        .order_by(),
        starts,
    )
    # A reader's first reading day, from the streak log: when they arrived.
    arrived = Counter(
        week_start(day)
        for day in ReadingDay.objects.values("profile")
        .annotate(first=Min("day"))
        .filter(first__gte=first)
        .values_list("first", flat=True)
    )
    new_readers = [arrived.get(s, 0) for s in starts]

    # Readers who read on any day of each window. From the reading-day log,
    # which keeps every day; the tile's own count comes from saved progress,
    # which keeps only the latest, so the two can differ by a reader or two.
    windows = []
    for i in range(MONTH_WINDOWS - 1, -1, -1):
        end = now.date() - timedelta(days=30 * i)
        windows.append(
            {
                "end": end.isoformat(),
                "readers": ReadingDay.objects.filter(
                    day__gt=end - timedelta(days=30), day__lte=end
                )
                .values("profile")
                .distinct()
                .count(),
            }
        )

    return {
        "weeks": [s.isoformat() for s in starts],
        "hearts": hearts,
        "reading_seconds": reading_seconds,
        "users": _running_total(users, new_users),
        "users_added": new_users,
        "readers": _running_total(readers, new_readers),
        "readers_added": new_readers,
        "active_30d": windows,
    }
