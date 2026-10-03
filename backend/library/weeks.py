"""The admin charts' week: Monday-anchored, on the site clock.

One rule for every weekly series and everything drawn against one (the
engagement chart, its event markers, the sign-up chart), so a marker can never
land under the wrong bar because two copies of "which week" disagreed.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.utils import timezone


def day_of(dt: datetime) -> date:
    """A moment's calendar day on the site clock."""
    return timezone.localtime(dt).date()


def week_start(day: date) -> date:
    """The Monday of ``day``'s week."""
    return day - timedelta(days=day.weekday())


def week_starts(now: datetime, weeks: int) -> list[date]:
    """The Mondays of the last ``weeks`` weeks, oldest first, this week last."""
    this_week = week_start(day_of(now))
    return [this_week - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
