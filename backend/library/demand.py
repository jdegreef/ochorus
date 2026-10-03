"""Which works each language's readers want: demand for one work in one language.

The admin already shows demand per LANGUAGE (readers, failed searches) and
popularity per WORK (readers in any language). This is the link between them:
Swahili readers reaching for *The Pursuit of God* in English, because there is
no Swahili edition. Two signals, both aggregate:

* **reading elsewhere** — a reader whose site language is X has progress on a
  work in another language, and no X edition of that work exists. One reader,
  one vote for (work, X). Readers who never changed their site language read as
  English and are never counted: we don't guess a person's language from their
  time zone, so the signal undercounts but every vote is real. Cheap and bulk
  (one grouped query for any number of languages).
* **searching for it** — a search in X found nothing, but the same query finds
  the work in English. Only a SPECIFIC query counts (one that finds at most
  ``SPECIFIC_QUERY_WORKS`` works): "prayer" finding twenty books says readers
  want prayer, not any one of them. And each distinct query counts once, since
  the search log is anonymous and one reader retrying a search would otherwise
  outvote many readers. Real searches, so it is per language and bounded; a
  caller that needs every language at once should use the reading signal alone.

Books, sermons and articles only: each is one row per language sharing a slug,
so "no X edition" is a plain lookup and a vote maps 1:1 onto a translation job.
Bios (a side table) and plans would need their own existence rule.
"""

from __future__ import annotations

from datetime import datetime
from functools import reduce
from operator import or_

from django.db.models import Count, Exists, F, OuterRef, Q
from django.db.models.functions import Length, Lower

from .models import Article, Book, SearchQueryLog, Sermon

# Work kind → the model holding its per-language editions. The kind values are
# both ReadingProgress kinds and translation-job types.
EDITION_MODELS = {"book": Book, "sermon": Sermon, "article": Article}

Work = tuple[str, str]  # (kind, slug)

# The search report's floor for a query worth listing: shorter ones are mostly
# typing fragments.
FAILED_QUERY_MIN_LEN = 3

# A failed query that finds more works than this in English is a topic, not a
# request for a work, and votes for none of them.
SPECIFIC_QUERY_WORKS = 3


def demand_score(readers: int, searches: int) -> int:
    """How strongly a language wants one work: its readers reading it elsewhere
    plus the distinct specific searches that would have found it. Named so any
    other ranking of the same signal uses the same rule."""
    return readers + searches


def _wanting(codes):
    """Progress rows that are votes: a reader of a language in ``codes``, on a
    work in another language that has no edition in theirs."""
    from reading.models import ReadingProgress

    no_edition = reduce(
        or_,
        (
            Q(kind=kind)
            & ~Exists(
                model.objects.filter(slug=OuterRef("book_slug"), language=OuterRef("profile__locale"))
            )
            for kind, model in EDITION_MODELS.items()
        ),
    )
    return (
        ReadingProgress.objects.filter(profile__locale__in=[c for c in codes if c != "en"])
        .exclude(language=F("profile__locale"))
        .filter(no_edition)
    )


def reading_elsewhere(codes) -> dict[str, dict[Work, int]]:
    """For each language in ``codes``: the works its readers read in another
    language for want of their own, each with how many readers."""
    out: dict[str, dict[Work, int]] = {}
    for r in (
        _wanting(codes)
        .values("profile__locale", "kind", "book_slug")
        .annotate(n=Count("profile", distinct=True))
    ):
        out.setdefault(r["profile__locale"], {})[(r["kind"], r["book_slug"])] = r["n"]
    return out


def readers_elsewhere(codes) -> dict[str, int]:
    """For each language in ``codes``: how many distinct readers are reading at
    least one work in another language for want of their own."""
    return {
        r["profile__locale"]: r["n"]
        for r in _wanting(codes).values("profile__locale").annotate(n=Count("profile", distinct=True))
    }


def existing_editions(code: str, works) -> set[Work]:
    """Which of ``works`` already have an edition in ``code``, drafts included:
    a draft exists, so a job for it would be refused (409)."""
    have: set[Work] = set()
    for kind, model in EDITION_MODELS.items():
        slugs = [s for k, s in works if k == kind]
        if slugs:
            have.update(
                (kind, slug)
                for slug in model.objects.filter(language=code, slug__in=slugs).values_list("slug", flat=True)
            )
    return have


def failed_queries(languages, *, since: datetime, limit: int = 10) -> dict[str, list[dict]]:
    """Each language's most frequent searches that found nothing since
    ``since``: case-folded, at the report's minimum length, ``limit`` per
    language. Shared by the search report and the demand list, so both pages
    agree on what a language failed to find."""
    out: dict[str, list[dict]] = {code: [] for code in languages}
    for r in (
        SearchQueryLog.objects.filter(created_at__gte=since, result_count=0, language__in=list(out))
        .annotate(q=Lower("query"), qlen=Length("query"))
        .filter(qlen__gte=FAILED_QUERY_MIN_LEN)
        .values("language", "q")
        .annotate(count=Count("id"))
        .order_by("-count", "q")
    ):
        queries = out[r["language"]]
        if len(queries) < limit:
            queries.append({"query": r["q"], "count": r["count"]})
    return out


def searched_elsewhere(code: str, *, since: datetime, queries: int = 10) -> dict[Work, int]:
    """Works ``code`` lacks that its top failed searches find in English, each
    with how many distinct specific queries would have found it.

    A query only counts once it has led to a work ``code`` lacks, so queries
    answered by works the language already has (a title searched in English,
    say) don't use up the budget; at most twice the budget is searched. A
    handful of real searches, on a page an admin opened on purpose.
    """
    from .search import hit_work, search_library

    out: dict[Work, int] = {}
    useful = 0
    for row in failed_queries([code], since=since, limit=queries * 2)[code]:
        if useful == queries:
            break
        found = {
            (w["type"], w["slug"])
            for hit in search_library(row["query"], "en")
            if (w := hit_work(hit)) and w["type"] in EDITION_MODELS
        }
        if len(found) > SPECIFIC_QUERY_WORKS:
            continue
        wanted = found - existing_editions(code, found)
        if wanted:
            useful += 1
        for work in wanted:
            out[work] = out.get(work, 0) + 1
    return out
