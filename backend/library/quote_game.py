"""Whose words? — the daily quotation game's schedule.

One reviewed quotation a day, four writers to choose from, one guess. Two
properties carry the game, and both live here as pure functions so they can be
tested without a database:

**Everyone gets the same puzzle on a given date.** The pick is a function of
the date and the pool alone — no randomness, no server clock (the reader's own
calendar day arrives in the URL, as the dated devotionals' does).

**No quotation comes round again for a long while.** The days are cut into
CYCLES. A cycle deals out its pool once, in a shuffled order seeded by the
cycle's number, so within a cycle nothing repeats; the next cycle starts the
day after the last card. A cycle's pool is the quotes that had JOINED (were
created) before the cycle began — a quote added mid-cycle waits for the next
deal instead of reshuffling the one under way, which is what keeps "today" from
changing under a reader when a deploy lands at lunchtime. (A quote REMOVED
mid-cycle does reshuffle the rest of that cycle; that is a rare, deliberate
act — a pulled line — and the cost is one odd day, not a broken game.)

Within a deal no writer is the answer two days running (where the pool has
more than one writer): Spurgeon alone is a sixth of the pool, and a shuffle
would otherwise give him Monday and Tuesday often enough to feel rigged.

The three wrong answers are other quoted writers WITH A PORTRAIT, nearest in
era to the right one — Spurgeon against Moody and Ryle, not against Augustine —
picked and ordered by the same date seed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

#: Puzzle No. 1. Fixed for ever: the number on a shared result line counts
#: from here, and moving it would renumber every result already shared.
GAME_EPOCH = date(2026, 11, 11)

#: Answers offered per puzzle, the right one included.
CHOICES = 4

#: How many of the nearest-in-era writers the three decoys are drawn from: a
#: little wider than three, so the same neighbours do not appear every time the
#: same writer is the answer.
DECOY_POOL = 6


def _rank(*parts: object) -> int:
    """A stable pseudo-random rank — sha256, so it never varies with Python's
    per-process hash seed or between deploys."""
    key = ":".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


@dataclass(frozen=True)
class PoolQuote:
    slug: str
    #: The day the quotation joined the pool (its row's creation date).
    joined: date
    #: The writer's slug — no writer is the answer two days running.
    author: str = ""


def _spread(deal: list[PoolQuote]) -> list[PoolQuote]:
    """The deal reordered so no writer comes two days running, where the pool
    allows it: a card that would repeat yesterday's writer swaps with the next
    card by someone else; once only that writer is left (the tail of a deal),
    the card moves back into the first gap between two other writers. Still a
    permutation, still deterministic. The first card never moves."""
    out = list(deal)
    i = 1
    while i < len(out):
        prev = out[i - 1].author
        if out[i].author != prev:
            i += 1
            continue
        j = next((j for j in range(i + 1, len(out)) if out[j].author != prev), None)
        if j is not None:
            out[i], out[j] = out[j], out[i]
            i += 1
            continue
        card = out.pop(i)
        k = next(
            (k for k in range(1, i) if card.author not in (out[k - 1].author, out[k].author)),
            None,
        )
        if k is None:  # Nowhere it fits: one writer's pool, or nearly.
            out.insert(i, card)
            i += 1
        else:
            out.insert(k, card)
    return out


def puzzle_number(day: date) -> int:
    """1 on ``GAME_EPOCH``; 0 or less before it."""
    return (day - GAME_EPOCH).days + 1


def quote_for_day(pool: Sequence[PoolQuote], day: date) -> str | None:
    """The slug of ``day``'s quotation, or None before the epoch or with no pool."""
    n = (day - GAME_EPOCH).days
    if n < 0 or not pool:
        return None
    start, cycle, prev_last = GAME_EPOCH, 0, None
    while True:
        members = [q for q in pool if q.joined < start]
        if not members:
            # Nothing had joined yet (a fresh database, or the first cycle of
            # a pool created on the epoch itself): deal the whole pool.
            members = list(pool)
        members.sort(key=lambda q: (_rank("cycle", cycle, q.slug), q.slug))
        # Yesterday's card leads as a sentinel (the spread never moves the
        # first card), so the new deal does not open on yesterday's writer —
        # nor, therefore, on yesterday's quotation.
        members = _spread([prev_last, *members])[1:] if prev_last else _spread(members)
        if prev_last and len(members) > 1 and members[0].slug == prev_last.slug:
            # A one-writer pool, where the spread has nothing to swap in.
            members[0], members[1] = members[1], members[0]
        if n < len(members):
            return members[n].slug
        n -= len(members)
        start += timedelta(days=len(members))
        prev_last = members[-1]
        cycle += 1


@dataclass(frozen=True)
class Writer:
    slug: str
    birth_year: int | None


def choices_for(answer: Writer, writers: Sequence[Writer], day: date) -> list[str] | None:
    """The ``CHOICES`` writer slugs offered on ``day`` (the answer among them),
    in their shuffled display order — or None when too few writers qualify."""
    others = [w for w in writers if w.slug != answer.slug]
    if len(others) < CHOICES - 1:
        return None

    def distance(w: Writer) -> int:
        if answer.birth_year is None or w.birth_year is None:
            return 10_000
        return abs(w.birth_year - answer.birth_year)

    nearest = sorted(others, key=lambda w: (distance(w), w.slug))[:DECOY_POOL]
    decoys = sorted(nearest, key=lambda w: (_rank("decoy", day, w.slug), w.slug))[: CHOICES - 1]
    offered = [answer.slug, *(w.slug for w in decoys)]
    return sorted(offered, key=lambda s: (_rank("order", day, s), s))
