"""Triage of unanswered searches: what happened after a decision, and when it reopens.

A :class:`~library.models.SearchDecision` takes a query off the admin's Open
list. That's only safe if the list can say when the decision didn't work, so
every decision carries what readers did since it was made — how often the query
was searched, how often it still found nothing — and a translated query whose
misses carry on past a grace period goes back to Open on its own.

Only ``translate`` reopens. ``wanted`` and ``out_of_scope`` are decisions that
the query WILL keep missing, so misses afterwards are the expected outcome, not
a sign the decision failed (for ``wanted`` they're the demand signal, and the
Wanted tab ranks by them).
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models.functions import Lower

from .models import SearchDecision, SearchQueryLog, fold_query

#: A translation takes days to ship, so misses inside this window prove nothing.
REOPEN_GRACE = timedelta(days=14)
#: Misses after the grace period that reopen a translated query. Two, so a single
#: stray search for a work that has since landed doesn't bounce it back.
REOPEN_MISSES = 2


def with_status(decisions) -> list[dict]:
    """Each decision as a dict, plus ``searches_since``, ``misses_since`` and
    ``reopened``.

    One scan of the log since the oldest decision, restricted to the decided
    queries and languages, then counted per decision in Python. The decision set
    is admin-sized (tens to hundreds), so this stays cheap however busy search is.

    Rows are grouped by :func:`fold_query`, the folding decisions are stored
    under, so both sides agree on the key. The SQL pre-filter still uses
    ``LOWER``, which folds non-ASCII letters on production Postgres (a UTF-8
    collation) but not on SQLite or a C-collated database; there an accented
    query's since-counts read low. That's acceptable for a dev database.
    """
    decisions = list(decisions)
    if not decisions:
        return []
    rows = (
        SearchQueryLog.objects.filter(
            created_at__gte=min(d.decided_at for d in decisions),
            language__in={d.language for d in decisions},
        )
        .annotate(q=Lower("query"))
        .filter(q__in={d.query for d in decisions})
        .values_list("q", "language", "created_at", "result_count")
    )
    by_key: dict[tuple[str, str], list[tuple]] = {}
    for q, language, at, results in rows:
        by_key.setdefault((fold_query(q), language), []).append((at, results))

    out = []
    for d in decisions:
        since = [(at, n) for at, n in by_key.get((d.query, d.language), []) if at >= d.decided_at]
        misses = [at for at, n in since if n == 0]
        late_misses = sum(1 for at in misses if at >= d.decided_at + REOPEN_GRACE)
        out.append(
            {
                "query": d.query,
                "language": d.language,
                "outcome": d.outcome,
                "outcome_label": d.get_outcome_display(),
                "target": d.target,
                "note": d.note,
                "decided_by": d.decided_by,
                "decided_at": d.decided_at.isoformat(),
                "searches_since": len(since),
                "misses_since": len(misses),
                "reopened": d.outcome == SearchDecision.Outcome.TRANSLATE
                and late_misses >= REOPEN_MISSES,
            }
        )
    return out
