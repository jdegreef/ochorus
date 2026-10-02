"""Where readers stop: how many readers reach each chapter of a book edition.

A book loses readers somewhere. A gentle slope is normal; a cliff at one chapter
usually means that chapter is broken, and the content checks (``library.qa``)
often already say so: a "giant" chapter that is really three merged, a
mid-sentence split, fragmented paragraphs. Putting the two side by side turns a
reading statistic into a fixable import problem.

For one edition (a book slug in one language), from ``ReadingProgress``:

* **reached chapter N**: the reader's furthest chapter is N or later, or they
  finished the book. Furthest is ``furthest_order`` (only grows, ignores
  peeking ahead from the contents), or ``chapter_order`` on rows from before it
  existed (0). Clamped to the edition's chapter count, so a re-import to fewer
  chapters can't put a reader past the end.
* **at chapter N**: their furthest chapter is exactly N and they haven't
  finished. Split by recency: **stopped** (no progress for ``STALL_DAYS``) or
  **still reading**. Only stopped readers are drop-off, so this week's readers
  don't read as an abandonment.

Books only: a sermon, biography or article is one document, with no chapters to
drop off between.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

# No progress for this long and a reader has stopped, not paused.
STALL_DAYS = 30

# A drop is only listed across the library (the content audit) once at least
# this many readers reached the chapter: fewer is noise, and small groups can
# point at a person.
MIN_READERS = 5


def _furthest(row: dict, chapters: int) -> int:
    if row["finished_at"] is not None:
        return chapters
    furthest = row["furthest_order"] or row["chapter_order"] or 1
    return max(1, min(furthest, chapters))


def reach(rows, chapters: int, *, now=None) -> list[dict]:
    """Per-chapter reach for one edition, from its progress rows (dicts with
    ``furthest_order``, ``chapter_order``, ``finished_at``, ``updated_at``):
    ``[{chapter, reached, stopped, still}]`` for chapters 1..``chapters``."""
    if chapters <= 0:
        return []
    stall = (now or timezone.now()) - timedelta(days=STALL_DAYS)
    reached = [0] * (chapters + 2)
    stopped = [0] * (chapters + 1)
    still = [0] * (chapters + 1)
    for row in rows:
        n = _furthest(row, chapters)
        reached[n] += 1  # suffix-summed below: reaching n means reaching 1..n
        if row["finished_at"] is None:
            (stopped if row["updated_at"] < stall else still)[n] += 1
    for n in range(chapters - 1, 0, -1):
        reached[n] += reached[n + 1]
    return [
        {"chapter": n, "reached": reached[n], "stopped": stopped[n], "still": still[n]}
        for n in range(1, chapters + 1)
    ]


def steepest_drop(curve: list[dict], *, min_readers: int = 1) -> dict | None:
    """The chapter that loses the largest share of the readers who reach it
    (stopped readers only), among chapters reached by at least ``min_readers``.
    The last chapter is excluded: stopping there is finishing, or near enough.
    ``{chapter, reached, stopped, rate}``, or None when nothing qualifies."""
    best = None
    for point in curve[:-1]:
        if point["reached"] < min_readers or not point["stopped"]:
            continue
        rate = point["stopped"] / point["reached"]
        if best is None or rate > best["rate"]:
            best = {**point, "rate": round(rate, 3)}
    if best:
        best.pop("still", None)
    return best


def progress_rows(language: str, slugs=None):
    """Book progress rows in ``language``, grouped by slug, in the shape
    ``reach`` reads. One query however many books."""
    from reading.models import ReadingProgress, WorkKind

    qs = ReadingProgress.objects.filter(kind=WorkKind.BOOK, language=language)
    if slugs is not None:
        qs = qs.filter(book_slug__in=list(slugs))
    out: dict[str, list[dict]] = defaultdict(list)
    for row in qs.values(
        "book_slug", "furthest_order", "chapter_order", "finished_at", "updated_at"
    ):
        out[row["book_slug"]].append(row)
    return out
