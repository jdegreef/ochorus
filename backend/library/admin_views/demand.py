"""Which works each language's readers want: demand for one work in one language.

The admin already shows demand per LANGUAGE (readers, failed searches) and
popularity per WORK (readers in any language). What it couldn't show is the
link between them: Swahili readers reaching for *The Pursuit of God* in
English, because there is no Swahili edition. Two signals, both aggregate:

* **reading elsewhere** — a reader whose site language is X has progress on a
  work in another language, and no X edition of that work exists. One reader,
  one vote for (work, X). Readers who never changed their site language read as
  English and are never counted: we don't guess a person's language from their
  time zone, so the signal undercounts but every vote is real.
* **searching for it** — a search in X found nothing, but the same query finds
  the work in English. The search-gap drill-down's logic, run over a language's
  top failed queries at once.

Books, sermons and articles only: each is one row per language sharing a slug,
so "no X edition" is a plain lookup and a vote maps 1:1 onto a translation job.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, F
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..corrections import COPYRIGHT_BLOCKED_SLUGS
from ..models import Article, Book, Sermon

# Reading-progress kind → the model holding a work's per-language editions.
# The kind values double as translation-job types ("book", "sermon", "article").
EDITION_MODELS = {"book": Book, "sermon": Sermon, "article": Article}

Work = tuple[str, str]  # (kind, slug)


def _existing(codes) -> set[tuple[str, str, str]]:
    """Every (kind, slug, language) edition in ``codes``, drafts included: a
    draft exists, so a job for it would be refused (409)."""
    return {
        (kind, slug, lang)
        for kind, model in EDITION_MODELS.items()
        for slug, lang in model.objects.filter(language__in=codes).values_list(
            "slug", "language"
        )
    }


def reading_elsewhere(codes) -> dict[str, dict[Work, set[int]]]:
    """For each language in ``codes``: the works its readers read in another
    language for want of their own, each with the set of reader (profile) ids.

    Sets rather than counts so a caller can also take the union across works
    (how many distinct readers a language is losing) without a second query.
    """
    from reading.models import ReadingProgress

    codes = [c for c in codes if c != "en"]
    rows = (
        ReadingProgress.objects.filter(
            kind__in=list(EDITION_MODELS), profile__locale__in=codes
        )
        .exclude(language=F("profile__locale"))
        .values_list("profile_id", "profile__locale", "kind", "book_slug")
    )
    existing = _existing(codes)
    out: dict[str, dict[Work, set[int]]] = defaultdict(lambda: defaultdict(set))
    for profile_id, lang, kind, slug in rows:
        if (kind, slug, lang) not in existing:
            out[lang][(kind, slug)].add(profile_id)
    return out


def searched_elsewhere(code: str, *, days: int = 90, queries: int = 10) -> dict[Work, int]:
    """Works that ``code``'s failed searches find in English, each with how many
    of those searches it would have answered.

    Bounded to the language's ``queries`` most frequent failed searches, each
    searched once in English (the source language, which has every work): a
    handful of searches per page load, on a page an admin opened on purpose.
    """
    from ..models import SearchQueryLog
    from ..search import MIN_QUERY_LEN, search_library
    from .analytics import _gap_work

    top = (
        SearchQueryLog.objects.filter(
            language=code,
            result_count=0,
            created_at__gte=timezone.now() - timedelta(days=days),
        )
        .values("query")
        .annotate(n=Count("id"))
        .order_by("-n")[: queries * 2]
    )
    existing = _existing([code])
    out: dict[Work, int] = defaultdict(int)
    asked = 0
    for row in top:
        q = row["query"].strip()
        if len(q) < MIN_QUERY_LEN:
            continue
        if asked == queries:
            break
        asked += 1
        found = set()
        for hit in search_library(q, "en"):
            work = _gap_work(hit)
            if work and work["type"] in EDITION_MODELS:
                found.add((work["type"], work["slug"]))
        for kind, slug in found:
            if (kind, slug, code) not in existing:
                out[(kind, slug)] += row["n"]
    return out


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageWantedView(APIView):
    """``GET /api/admin/languages/<code>/wanted/``: the works ``code``'s readers
    are reaching for in another language, most wanted first, each with its
    evidence (readers reading elsewhere, failed searches it would answer).

    Its own endpoint rather than part of the language detail payload, because the
    search half runs real searches: the page asks for it once, after it loads.
    """

    LIMIT = 15
    SEARCH_DAYS = 90

    def get(self, request, code):
        code = code.lower()
        if code == "en":
            return Response({"language": code, "days": self.SEARCH_DAYS, "works": []})
        readers = reading_elsewhere([code]).get(code, {})
        searches = searched_elsewhere(code, days=self.SEARCH_DAYS)
        works = set(readers) | set(searches)
        ranked = sorted(
            works,
            key=lambda w: (-(len(readers.get(w, ())) + searches.get(w, 0)), -len(readers.get(w, ()))),
        )[: self.LIMIT]
        titles = _english_titles(ranked)
        return Response(
            {
                "language": code,
                "days": self.SEARCH_DAYS,
                "works": [
                    {
                        "type": kind,
                        "slug": slug,
                        "title": titles.get((kind, slug), (slug, ""))[0],
                        "author": titles.get((kind, slug), (slug, ""))[1],
                        "readers": len(readers.get((kind, slug), ())),
                        "searches": searches.get((kind, slug), 0),
                        # Under copyright: no job can be filed (the job API
                        # answers 451), so the page shows it without a button.
                        "blocked": kind == "book" and slug in COPYRIGHT_BLOCKED_SLUGS,
                    }
                    for kind, slug in ranked
                ],
            }
        )


def _english_titles(works) -> dict[Work, tuple[str, str]]:
    """(kind, slug) → (title, author) from each work's English edition."""
    out: dict[Work, tuple[str, str]] = {}
    for kind, model in EDITION_MODELS.items():
        slugs = [s for k, s in works if k == kind]
        if not slugs:
            continue
        qs = model.objects.filter(slug__in=slugs, language="en")
        if kind == "article":
            rows = qs.values_list("slug", "h1")
            out.update({(kind, slug): (h1, "") for slug, h1 in rows})
        else:
            rows = qs.values_list("slug", "title", "author__name")
            out.update({(kind, slug): (t, a or "") for slug, t, a in rows})
    return out
