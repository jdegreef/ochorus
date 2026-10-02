"""The "Readers are asking for" list on a language's admin page. The signal
itself (what counts as demand, and how it is scored) lives in ``library.demand``."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..corrections import translation_blocked
from ..demand import (
    EDITION_MODELS,
    Work,
    demand_score,
    existing_editions,
    reading_elsewhere,
    searched_elsewhere,
)
from .analytics import _prefer_en


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
        readers: dict[Work, int] = {}
        searches: dict[Work, int] = {}
        if code != "en":
            readers = reading_elsewhere([code]).get(code, {})
            since = timezone.now() - timedelta(days=self.SEARCH_DAYS)
            have = existing_editions(code)
            searches = {
                w: n for w, n in searched_elsewhere(code, since=since).items() if w not in have
            }
        evidence = {w: (readers.get(w, 0), searches.get(w, 0)) for w in readers.keys() | searches.keys()}
        ranked = sorted(evidence, key=lambda w: (-demand_score(*evidence[w]), -evidence[w][0], w))
        ranked = ranked[: self.LIMIT]
        titles = _titles(ranked)
        works = []
        for kind, slug in ranked:
            title, author = titles.get((kind, slug), (slug, ""))
            n_readers, n_searches = evidence[(kind, slug)]
            works.append(
                {
                    "type": kind,
                    "slug": slug,
                    "title": title,
                    "author": author,
                    "readers": n_readers,
                    "searches": n_searches,
                    "blocked": translation_blocked(kind, slug),
                }
            )
        return Response({"language": code, "days": self.SEARCH_DAYS, "works": works})


def _titles(works) -> dict[Work, tuple[str, str]]:
    """(kind, slug) → (title, author), preferring the English edition and
    falling back to whichever edition exists (the analytics pages' rule)."""
    out: dict[Work, tuple[str, str]] = {}
    for kind, model in EDITION_MODELS.items():
        slugs = [s for k, s in works if k == kind]
        if not slugs:
            continue
        qs = model.objects.filter(slug__in=slugs)
        if kind == "article":  # an article's byline is the house: no author
            rows, value_of = qs.values("slug", "language", "h1"), lambda r: (r["h1"], "")
        else:
            rows = qs.values("slug", "language", "title", "author__name")
            value_of = lambda r: (r["title"], r["author__name"] or "")  # noqa: E731
        out.update({(kind, slug): v for slug, v in _prefer_en(rows, value_of).items()})
    return out
