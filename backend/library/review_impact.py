"""Reader impact of an edition awaiting review: which (work, language) to check first.

The review queue holds hundreds of AI translations and native reviewers are few,
so the order they work in decides how many READS land on reviewed text. Ordered
by age, a reviewer could spend a week on editions nobody opens while the one
every Swahili reader is halfway through waits. This ranks them by what readers
actually read.

The signal is saved reading progress (``reading.ReadingProgress``): one row per
signed-in reader per work, carrying the edition's language and when it was last
touched. It is the only per-edition engagement the API holds — page views live
in Plausible, which the API never reads, and anonymous readers leave nothing
server-side — so the score undercounts, but every unit is a real reader.

* **Measured** — distinct readers of THIS edition whose progress moved in the
  last ``WINDOW_DAYS``, with those in the last ``RECENT_DAYS`` counted twice
  (``activity``), so a work readers are on now outranks one they left in summer.
* **Estimated** — an edition nobody has read yet (a new language's whole
  catalogue arrives here at once) still needs an order. It gets the ENGLISH
  edition's activity scaled by the language's share of active readers (by their
  site language): what the work would draw if this language's readers read like
  everyone else. Used only when the measured figure is zero — a measured reader
  is evidence, a projection is not.

Both halves are aggregate counts; no reader is identifiable from the result.
Two grouped queries whatever the queue's size.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

WINDOW_DAYS = 90
RECENT_DAYS = 30

Edition = tuple[str, str, str]  # (kind, slug, language)

EXPLANATION = (
    f"Signed-in readers with progress in this edition over the last {WINDOW_DAYS} days, "
    f"those in the last {RECENT_DAYS} days counted twice. An edition nobody has read yet "
    "is estimated: its English edition's score × this language's share of active readers."
)


def activity(readers_window: int, readers_recent: int) -> int:
    """One edition's measured score. Named so every caller weighs recency alike."""
    return readers_window + readers_recent


def edition_impact(editions, *, now=None) -> tuple[dict[Edition, dict], dict[str, float]]:
    """``editions`` → (each edition's impact, each language's share of readers).

    An impact is ``{"score", "basis", "readers", "readers_recent", "en_score"}``,
    where ``basis`` is ``"readers"`` (measured), ``"estimate"`` (from English ×
    share) or ``"none"`` (no signal at all: score 0).
    """
    from reading.models import ReadingProgress

    now = now or timezone.now()
    since = now - timedelta(days=WINDOW_DAYS)
    recent = now - timedelta(days=RECENT_DAYS)
    editions = list(editions)
    kinds = {k for k, _, _ in editions}

    in_window = ReadingProgress.objects.filter(updated_at__gte=since)
    counts: dict[Edition, tuple[int, int]] = {
        (r["kind"], r["book_slug"], r["language"]): (r["n"], r["n_recent"])
        for r in in_window.filter(kind__in=kinds)
        .values("kind", "book_slug", "language")
        .annotate(
            n=Count("profile", distinct=True),
            n_recent=Count("profile", distinct=True, filter=Q(updated_at__gte=recent)),
        )
        .order_by()
    }
    # A profile has one site language, so the per-language counts sum to the
    # distinct total.
    by_locale = {
        r["profile__locale"]: r["n"]
        for r in in_window.values("profile__locale").annotate(n=Count("profile", distinct=True)).order_by()
    }
    total = sum(by_locale.values())
    share = {code: n / total for code, n in by_locale.items()} if total else {}

    out: dict[Edition, dict] = {}
    for kind, slug, language in editions:
        readers, readers_recent = counts.get((kind, slug, language), (0, 0))
        measured = activity(readers, readers_recent)
        en_score = activity(*counts.get((kind, slug, "en"), (0, 0)))
        if measured:
            score, basis = float(measured), "readers"
        elif en_score and share.get(language):
            score, basis = round(en_score * share[language], 2), "estimate"
        else:
            score, basis = 0.0, "none"
        out[(kind, slug, language)] = {
            "score": score,
            "basis": basis,
            "readers": readers,
            "readers_recent": readers_recent,
            "en_score": en_score,
        }
    return out, share
