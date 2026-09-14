"""Admin dashboard API — a ranked per-language health score.

One number per language that composes the three signals an admin otherwise reads
off three separate pages — **readiness** (is the go-live bar met?), **coverage**
(how much of the English library exists in this language?) and **engagement**
(are readers actually using it?) — plus a **review** signal (what share of the
translations a human has confirmed). It answers "where should the next hour go?"
at a glance, and links each row on to the page that acts on its weakest signal.

Read-only and derived — it stores nothing. It leans on the existing machinery
rather than re-deriving it: ``readiness.report`` already counts a language's
published books / sermons / biographies / plans and runs every go-live check, so
this borrows those counts instead of issuing them again. Only the extra signals
(reading-volume, unreviewed share, readers) are queried here, each grouped across
all languages in one query rather than per-language.
"""

from __future__ import annotations

from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from .. import readiness
from ..models import Book, Chapter, Language, Sermon

# What the composite weighs, and by how much (weights sum to 1). Readiness leads
# — a language that fails its go-live bar isn't serving readers whatever else is
# true — then breadth of content, then how much of it a human has confirmed, then
# real usage. Engagement is real but modest: English will always dominate it, so
# a large weight would just rank languages by age.
_WEIGHTS = {"readiness": 0.35, "coverage": 0.30, "review": 0.20, "engagement": 0.15}


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageHealthView(APIView):
    """GET a ranked per-language health score with its component breakdown."""

    def get(self, request):
        languages = list(Language.objects.all())
        # verify_bible=False: the scoreboard scores every language at once, so it
        # must not fan out one live Bible-API call per language on each load — the
        # go-live decision runs the real check on the per-language readiness page.
        reports = {
            lang.code: readiness.report(lang, verify_bible=False) for lang in languages
        }

        # Three grouped queries cover every language at once (no per-language N+1).
        published = self._published_by_language()
        volume = self._volume_by_language()
        readers = self._readers_by_language()
        max_readers = max(readers.values(), default=0)

        # Coverage is measured against the source language's published shelf — the
        # ceiling any translation is working toward.
        source = next((lang for lang in languages if lang.is_source), None)
        source_published = published.get(source.code, {}).get("total", 0) if source else 0

        rows = []
        for lang in languages:
            report = reports[lang.code]
            pub = published.get(lang.code, {"total": 0, "unreviewed": 0})
            vol = volume.get(lang.code, {"chapters": 0, "words": 0})
            n_readers = readers.get(lang.code, 0)
            counts = {c.key: c for c in report.checks}

            scores = {
                "readiness": self._readiness_score(report),
                "coverage": (
                    1.0
                    if lang.is_source or not source_published
                    else min(1.0, pub["total"] / source_published)
                ),
                "review": (
                    1.0
                    if lang.is_source or not pub["total"]
                    else (pub["total"] - pub["unreviewed"]) / pub["total"]
                ),
                "engagement": (n_readers / max_readers) if max_readers else 0.0,
            }
            health = round(100 * sum(scores[k] * w for k, w in _WEIGHTS.items()))

            rows.append(
                {
                    "code": lang.code,
                    "name": lang.name,
                    "native_name": lang.native_name,
                    "rtl": lang.rtl,
                    "is_source": lang.is_source,
                    "is_live": lang.is_live,
                    "health": health,
                    "scores": {k: round(v, 3) for k, v in scores.items()},
                    "content": {
                        "published_books": pub["total"],
                        "unreviewed_books": pub["unreviewed"],
                        "sermons": self._current(counts.get("sermons")),
                        "bios": self._current(counts.get("bios")),
                        "plans": self._current(counts.get("plans")),
                        "chapters": vol["chapters"],
                        "words": vol["words"],
                    },
                    "readiness": {
                        "ready": report.ready,
                        "blocking": [c.key for c in report.blockers],
                    },
                    "readers": n_readers,
                }
            )

        # Healthiest first; the frontend can invert to lead with what needs work.
        rows.sort(key=lambda r: (-r["health"], r["name"]))
        return Response(
            {"source_published_books": source_published, "languages": rows}
        )

    # --- component scores ------------------------------------------------------

    @staticmethod
    def _readiness_score(report: readiness.Report) -> float:
        """Mean credit across the checks that apply to this language. A count check
        (books, sermons…) earns partial credit toward its bar, so a language at 4
        of 5 books reads as most-of-the-way, not a bare fail; a yes/no check
        (Bible, interface) is all-or-nothing. Skipped and unknown checks — a bar
        set to zero, an unresolved catalogue — don't count either way."""
        credits: list[float] = []
        for c in report.checks:
            if c.status in (readiness.SKIPPED, readiness.UNKNOWN):
                continue
            if c.required:  # a count check with a non-zero bar
                credits.append(min(1.0, (c.current or 0) / c.required))
            else:
                credits.append(1.0 if c.status == readiness.PASS else 0.0)
        return sum(credits) / len(credits) if credits else 1.0

    @staticmethod
    def _current(check) -> int:
        return (check.current or 0) if check is not None else 0

    # --- grouped signal queries ------------------------------------------------

    @staticmethod
    def _published_by_language() -> dict[str, dict]:
        """Published book totals and the unreviewed (AI, not yet human-confirmed)
        share, per language — one grouped query."""
        out: dict[str, dict] = {}
        for r in (
            Book.objects.filter(is_published=True)
            .values("language", "source_type")
            .annotate(n=Count("id"))
        ):
            row = out.setdefault(r["language"], {"total": 0, "unreviewed": 0})
            row["total"] += r["n"]
            if r["source_type"] == Book.SourceType.AI_UNREVIEWED:
                row["unreviewed"] += r["n"]
        return out

    @staticmethod
    def _volume_by_language() -> dict[str, dict]:
        """Reading volume (chapters + words) per language — book chapters and
        sermon bodies together, so a sermon-only language isn't shown as empty."""
        out: dict[str, dict] = {}
        for r in Chapter.objects.values("book__language").annotate(
            n=Count("id"), words=Sum("word_count")
        ):
            row = out.setdefault(r["book__language"], {"chapters": 0, "words": 0})
            row["chapters"] += r["n"]
            row["words"] += r["words"] or 0
        for r in Sermon.objects.values("language").annotate(words=Sum("word_count")):
            row = out.setdefault(r["language"], {"chapters": 0, "words": 0})
            row["words"] += r["words"] or 0
        return out

    @staticmethod
    def _readers_by_language() -> dict[str, int]:
        """Distinct readers whose progress touches content in each language — the
        same signal the engagement page's per-language rollup uses."""
        from reading.models import ReadingProgress

        return {
            r["language"]: r["n"]
            for r in ReadingProgress.objects.values("language").annotate(
                n=Count("profile", distinct=True)
            )
        }
