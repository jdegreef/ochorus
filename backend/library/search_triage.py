"""Triage of unanswered searches: what happened after a decision, and when it reopens.

A :class:`~library.models.SearchDecision` takes a query off the admin's Open
list. That's only safe if the list can say when the decision didn't work, so
every decision carries what readers did since it was made — how often the query
was searched, how often it still found nothing — and a translated query whose
misses carry on past a grace period goes back to Open on its own.

``translate``, ``synonym`` and ``pinned`` reopen when the query keeps finding
nothing (see :data:`GRACE`). ``wanted`` and ``out_of_scope`` are decisions that
the query WILL keep missing, so misses afterwards are the expected outcome, not
a sign the decision failed (for ``wanted`` they're the demand signal, and the
Wanted tab ranks by them). A pin answers a query that already found things, so
misses mean its page has gone; its usual measure is opens.

Two outcomes also change what readers get back, via :func:`rules`: a
``synonym`` runs the search on another word, and a ``pinned`` page leads the
results (:func:`pinned_hit`).
"""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.db.models.functions import Lower

from .models import SearchClickLog, SearchDecision, SearchQueryLog, fold_query

#: A translation takes days to ship, so misses inside this window prove nothing.
REOPEN_GRACE = timedelta(days=14)
#: Misses after the grace period that reopen a translated query. Two, so a single
#: stray search for a work that has since landed doesn't bounce it back.
REOPEN_MISSES = 2

#: The outcomes that reopen when their query keeps finding nothing, and how long
#: after the decision misses start to count: a translation has to ship; a
#: synonym works the moment it's saved; a pin's query found things already, so
#: a miss means the pinned page (and everything else) has gone.
GRACE = {
    SearchDecision.Outcome.TRANSLATE: REOPEN_GRACE,
    SearchDecision.Outcome.SYNONYM: timedelta(0),
    SearchDecision.Outcome.PINNED: timedelta(0),
}

#: What a pin may point at: the kinds a slug alone identifies. A chapter needs
#: its book and order, and pinning a passage is what a book pin is for anyway.
PIN_KINDS = ("author", "book", "topic", "plan", "article", "sermon")

#: The per-language rules every unscoped search reads. Short-lived because the
#: cache is per process: a decision clears this worker's copy at once, the
#: others within a minute.
RULES_TTL = 60


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
    # Opens of the pinned page since, the measure of a pin. The click log keeps
    # a result's type and position, not its slug; the pin is the first row
    # readers see, so a click on its type at position 1 is the pin being read.
    pinned = [d for d in decisions if d.outcome == SearchDecision.Outcome.PINNED]
    opens: dict[tuple[str, str], list] = {}
    if pinned:
        for q, language, at, kind in (
            SearchClickLog.objects.filter(
                created_at__gte=min(d.decided_at for d in pinned),
                language__in={d.language for d in pinned},
                position=1,
            )
            .annotate(q=Lower("query"))
            .filter(q__in={d.query for d in pinned})
            .values_list("q", "language", "created_at", "result_type")
        ):
            opens.setdefault((fold_query(q), language), []).append((at, kind))

    out = []
    for d in decisions:
        since = [(at, n) for at, n in by_key.get((d.query, d.language), []) if at >= d.decided_at]
        misses = [at for at, n in since if n == 0]
        grace = GRACE.get(d.outcome)
        late_misses = (
            sum(1 for at in misses if at >= d.decided_at + grace) if grace is not None else 0
        )
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
                "opens_since": sum(
                    1
                    for at, kind in opens.get((d.query, d.language), [])
                    if at >= d.decided_at and kind == d.target.partition(":")[0]
                ),
                "reopened": late_misses >= REOPEN_MISSES,
            }
        )
    return out


def _rules_key(language: str) -> str:
    return f"search-rules:{language}"


def rules(language: str) -> dict[str, tuple[str, str]]:
    """``{folded query: (outcome, target)}`` for the decisions that change what
    readers get back in ``language`` — synonyms and pins. Read on every unscoped
    search, so cached; :func:`clear_rules` runs on every decide and undo."""
    cached = cache.get(_rules_key(language))
    if cached is not None:
        return cached
    out = {
        query: (outcome, target)
        for query, outcome, target in SearchDecision.objects.filter(
            language=language,
            outcome__in=[SearchDecision.Outcome.SYNONYM, SearchDecision.Outcome.PINNED],
        ).values_list("query", "outcome", "target")
    }
    cache.set(_rules_key(language), out, RULES_TTL)
    return out


def clear_rules(language: str) -> None:
    cache.delete(_rules_key(language))


def hit_key(hit: dict) -> tuple[str, str]:
    """A hit's identity for de-duplication: its type and slug (the slug field
    per type is ``search.HIT_WORK``'s, the one mapping of it)."""
    from .search import HIT_WORK

    kind = hit.get("type", "")
    spec = HIT_WORK.get(kind)
    return kind, hit.get(spec[1], "") if spec else ""


def pinned_hit(target: str, q: str, language: str) -> dict | None:
    """The result row for a pin's ``"kind:slug"`` target, or ``None`` when it
    doesn't resolve — an unknown kind, or a page that isn't published in this
    language (any more). A pin to a missing page then does nothing, rather than
    sending readers to a dead link."""
    from .search import _base_querysets, _Ctx, _hit_for

    kind, _, slug = target.partition(":")
    if kind not in PIN_KINDS or not slug:
        return None
    row = _base_querysets(language)[kind].filter(slug=slug).first()
    if row is None:
        return None
    return {**_hit_for(kind, row, _Ctx(q=q, language=language)), "pinned": True}
