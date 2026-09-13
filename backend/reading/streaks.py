"""Reading-streak arithmetic over :class:`ReadingDay` dates.

A streak is a human, wall-clock notion (see :class:`reading.models.ReadingDay`):
a run of consecutive calendar days the reader read *something*, on any device.
The days are stored, not the streak — so it is derived here, from the set of
dates, wherever it's shown.

Pure and side-effect-free so it is cheap to unit-test: give it the dates, get
back the two numbers. Duplicate dates are tolerated (the store already dedupes
per day, but a caller passing a raw list shouldn't have to care).

The frontend has a parallel definition in ``frontend/src/lib/streak.ts``
(``currentStreak`` / ``longestStreak``), including the same "a run ending today
OR yesterday is still live" rule — keep the two in step if either changes.
"""

from __future__ import annotations

from datetime import date, timedelta


def reading_streaks(days, *, today: date) -> tuple[int, int]:
    """``(current, longest)`` streak lengths, in days, from reading dates.

    ``current`` counts back from ``today``: a run ending today or yesterday is
    live (today isn't over, so a reader who read yesterday but not yet today
    keeps their streak); an older run is not, so ``current`` is 0. ``longest``
    is the longest consecutive run anywhere in the history.

    ``today`` is passed in rather than read from the clock so the caller fixes
    the reader's local "today" (a streak is judged in the reader's wall time,
    not the server's) and the function stays pure.
    """
    seen = set(days)
    unique = sorted(seen)
    if not unique:
        return 0, 0

    longest = 1
    run = 1
    for prev, cur in zip(unique, unique[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)

    # Current: only counts if the most recent day is today or yesterday.
    last = unique[-1]
    if last < today - timedelta(days=1):
        current = 0
    else:
        current = 1
        # Walk backwards from the last day while days are contiguous.
        expected = last - timedelta(days=1)
        while expected in seen:
            current += 1
            expected -= timedelta(days=1)

    return current, longest
