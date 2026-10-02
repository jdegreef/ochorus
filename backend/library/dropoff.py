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
  existed (0). Clamped to the edition's last chapter, so a re-import to fewer
  chapters can't put a reader past the end. Chapters are keyed by their
  ``order``, gaps and all, so a point always names a real chapter.
* **at chapter N**: their furthest chapter is exactly N and they haven't
  finished. Split by recency: **stopped** (no progress for ``STALL_DAYS``) or
  **still reading**. Only stopped readers are drop-off, so this week's readers
  don't read as an abandonment.

Books only: a sermon, biography or article is one document, with no chapters to
drop off between.

A reader has one progress row per work, not per edition, so one who switches
editions is counted in the edition they opened last. Rare, and the data holds
nothing better.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

# No progress for this long and a reader has stopped, not paused.
STALL_DAYS = 30

# A drop is only listed across the library (the content audit) once at least
# this many readers reached the chapter: fewer is noise, and small groups can
# point at a person.
MIN_READERS = 5

# One book's own admin page names its steepest drop from this many readers:
# the admin is already looking at that book, so a small group still says
# something there.
MIN_READERS_BOOK = 2


def _furthest(row: dict, last: int) -> int:
    if row["finished_at"] is not None:
        return last
    return min(row["furthest_order"] or row["chapter_order"] or 1, last)


def reach(rows, orders: list[int], *, now=None) -> list[dict]:
    """Per-chapter reach for one edition, from its progress rows (dicts with
    ``furthest_order``, ``chapter_order``, ``finished_at``, ``updated_at``) and
    its chapter orders, ascending: ``[{chapter, reached, stopped, still}]``,
    one per chapter. A reader whose furthest falls in a gap is "at" the last
    chapter before it."""
    if not orders:
        return []
    stall = (now or timezone.now()) - timedelta(days=STALL_DAYS)
    at, stopped, still = Counter(), Counter(), Counter()
    for row in rows:
        # Index of the last chapter at or before the reader's furthest; a
        # furthest before the first chapter counts as the first.
        i = max(0, bisect_right(orders, _furthest(row, orders[-1])) - 1)
        at[i] += 1
        if row["finished_at"] is None:
            (stopped if row["updated_at"] < stall else still)[i] += 1
    curve, reached = [], 0
    for i in range(len(orders) - 1, -1, -1):  # reaching one means reaching all before it
        reached += at[i]
        curve.append(
            {"chapter": orders[i], "reached": reached, "stopped": stopped[i], "still": still[i]}
        )
    return curve[::-1]


def steepest_drop(curve: list[dict], *, min_readers: int = 1) -> dict | None:
    """The chapter that loses the largest share of the readers who reach it
    (stopped readers only), among chapters reached by at least ``min_readers``.
    The last chapter is excluded: stopping there is finishing, or near enough.
    ``{chapter, reached, stopped, rate}``, or None when nothing qualifies."""
    candidates = [p for p in curve[:-1] if p["reached"] >= min_readers and p["stopped"]]
    if not candidates:
        return None
    p = max(candidates, key=lambda p: p["stopped"] / p["reached"])
    return {
        "chapter": p["chapter"],
        "reached": p["reached"],
        "stopped": p["stopped"],
        "rate": round(p["stopped"] / p["reached"], 3),
    }


def progress_rows(*, slugs=None, language: str | None = None):
    """Book progress rows, grouped by edition ``(slug, language)``, in the
    shape ``reach`` reads. One query, narrowed to some works and/or one
    language when given."""
    from reading.models import ReadingProgress, WorkKind

    qs = ReadingProgress.objects.filter(kind=WorkKind.BOOK).order_by()
    if slugs is not None:
        qs = qs.filter(book_slug__in=list(slugs))
    if language:
        qs = qs.filter(language=language)
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in qs.values(
        "book_slug", "language", "furthest_order", "chapter_order", "finished_at", "updated_at"
    ):
        out[(row["book_slug"], row["language"])].append(row)
    return out


def work_curves(slugs) -> dict[str, dict]:
    """One curve per book work, for a list of works side by side (the
    engagement leaderboard): ``{slug: {language, chapters, reached,
    steepest}}``, where ``reached`` is the readers reaching each of
    ``chapters`` (the edition's chapter orders).

    A work's editions aren't pooled: chapter N of one translation needn't be
    chapter N of another. Each work shows its most-read edition (ties to
    English, then by code), which is where its readers mostly are. Two
    queries however many works."""
    from .models import Chapter

    by_work: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    for (slug, lang), rows in progress_rows(slugs=slugs).items():
        by_work[slug][lang] = rows
    chosen = {
        slug: min(eds, key=lambda lang: (-len(eds[lang]), lang != "en", lang))
        for slug, eds in by_work.items()
    }
    orders: dict[tuple[str, str], list[int]] = defaultdict(list)
    for slug, lang, order in (
        Chapter.objects.filter(book__slug__in=list(chosen))
        .order_by("order")
        .values_list("book__slug", "book__language", "order")
    ):
        if chosen[slug] == lang:
            orders[(slug, lang)].append(order)
    out = {}
    for slug, lang in chosen.items():
        curve = reach(by_work[slug][lang], orders.get((slug, lang), []))
        if curve:
            out[slug] = {
                "language": lang,
                "chapters": [p["chapter"] for p in curve],
                "reached": [p["reached"] for p in curve],
                "steepest": steepest_drop(curve, min_readers=MIN_READERS_BOOK),
            }
    return out
