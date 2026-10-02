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

from datetime import date, timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from .. import readiness
from ..demand import readers_elsewhere
from ..models import Book, Chapter, Language, LanguageHealthSnapshot, Sermon

# What the composite weighs, and by how much (weights sum to 1). Readiness leads
# — a language that fails its go-live bar isn't serving readers whatever else is
# true — then breadth of content, then how much of it a human has confirmed, then
# real usage. Engagement is real but modest: reader counts are still small and
# noisy, so a large weight would let a handful of readers swing the ranking.
_WEIGHTS = {"readiness": 0.35, "coverage": 0.30, "review": 0.20, "engagement": 0.15}

# Engagement is readers against this fixed target (capped at 1), not against the
# busiest language: measured that way, every new English reader lowered every
# other language's score while nothing in those languages had changed. Raise it
# as the site grows; the page reads it from the response.
_ENGAGEMENT_TARGET = 25

# Coverage blends every kind of content a reader can arrive through, not books
# alone (a language with 81% of the sermons scored 36% when only books counted).
# Books still lead, so a sermon-only language can't read as complete. Weights sum
# to 1; a kind the source shelf has none of drops out and the rest renormalise.
_COVERAGE_MIX = {"books": 0.50, "sermons": 0.25, "bios": 0.15, "plans": 0.10}

# Readers are counted over this many days, not all-time: against a fixed target,
# an all-time count only ever rises, so a language that once had 25 readers
# would keep full credit with nobody reading it.
_READER_WINDOW_DAYS = 90

# The formula a snapshot was scored with. Bump it whenever the weights, a
# signal's definition, the coverage mix, the target or the window change: the
# trend only joins points of the same version, so a formula change starts a new
# line instead of reading as a week of real movement. (1 = books-only coverage
# against the busiest language; 2 = fixed engagement target; 3 = 90-day readers
# and the blended shelf.)
SCORE_VERSION = 3

# How much history the page gets: eight weeks of daily points.
_TREND_DAYS = 56


def record_snapshots(rows: list[dict], day: date) -> None:
    """Upsert each language's score for ``day`` (one row per language per day)."""
    for r in rows:
        LanguageHealthSnapshot.objects.update_or_create(
            language=r["code"],
            date=day,
            defaults={
                "score_version": SCORE_VERSION,
                "health": r["health"],
                **{k: r["scores"][k] for k in _WEIGHTS},
            },
        )


def attach_trend(rows: list[dict], today: date) -> None:
    """Give each row its last ``_TREND_DAYS`` of daily scores (``trend``, oldest
    first) and its change since a week ago (``week_change``: today's score minus
    the latest point at least seven days old, or None with no such point). Only
    points scored by the current formula count; see ``SCORE_VERSION``."""
    since = today - timedelta(days=_TREND_DAYS)
    history: dict[str, list[dict]] = {}
    for snap in LanguageHealthSnapshot.objects.filter(
        date__gte=since, score_version=SCORE_VERSION
    ).order_by("date"):
        history.setdefault(snap.language, []).append(
            {"date": snap.date.isoformat(), "health": snap.health}
        )
    week_ago = (today - timedelta(days=7)).isoformat()
    for r in rows:
        points = history.get(r["code"], [])
        older = [p for p in points if p["date"] <= week_ago]
        r["trend"] = points
        r["week_change"] = r["health"] - older[-1]["health"] if older else None


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageHealthView(APIView):
    """GET a ranked per-language health score with its component breakdown."""

    def get(self, request):
        payload = self.compute()
        today = timezone.localdate()
        # The page view is one of the two writers of the daily point (the deploy
        # step is the other), so a day anyone looked at the scoreboard is a day
        # the trend has. An upsert: opening it twice writes one row.
        record_snapshots(payload["languages"], today)
        attach_trend(payload["languages"], today)
        payload["score_version"] = SCORE_VERSION
        return Response(payload)

    @classmethod
    def compute(cls) -> dict:
        """The scoreboard payload, ranked healthiest first. Shared by the view
        and ``snapshot_language_health`` so a snapshot is the exact score the
        page showed."""
        languages = list(Language.objects.all())
        # verify_bible=False: the scoreboard scores every language at once, so it
        # must not fan out one live Bible-API call per language on each load — the
        # go-live decision runs the real check on the per-language readiness page.
        reports = {
            lang.code: readiness.report(lang, verify_bible=False) for lang in languages
        }

        # Three grouped queries cover every language at once (no per-language N+1).
        published = cls._published_by_language()
        volume = cls._volume_by_language()
        readers = cls._readers_by_language()
        # Readers whose site language this is, reading a work it has no edition
        # of. Shown beside the score, not folded into it, so the score keeps
        # its meaning; the language page lists the works themselves.
        elsewhere = readers_elsewhere([lang.code for lang in languages])

        # Coverage is measured against the source language's published shelf — the
        # ceiling any translation is working toward.
        source = next((lang for lang in languages if lang.is_source), None)
        source_published = published.get(source.code, {}).get("total", 0) if source else 0
        source_shelf = (
            cls._shelf(
                {c.key: c for c in reports[source.code].checks}, source_published
            )
            if source
            else dict.fromkeys(_COVERAGE_MIX, 0)
        )

        rows = []
        for lang in languages:
            report = reports[lang.code]
            pub = published.get(lang.code, {"total": 0, "unreviewed": 0})
            vol = volume.get(lang.code, {"chapters": 0, "words": 0})
            n_readers = readers.get(lang.code, 0)
            counts = {c.key: c for c in report.checks}

            scores = {
                "readiness": cls._readiness_score(report),
                "coverage": (
                    1.0
                    if lang.is_source
                    else cls._coverage(cls._shelf(counts, pub["total"]), source_shelf)
                ),
                "review": (
                    1.0
                    if lang.is_source or not pub["total"]
                    else (pub["total"] - pub["unreviewed"]) / pub["total"]
                ),
                "engagement": min(1.0, n_readers / _ENGAGEMENT_TARGET),
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
                        "sermons": cls._current(counts.get("sermons")),
                        "bios": cls._current(counts.get("bios")),
                        "plans": cls._current(counts.get("plans")),
                        "chapters": vol["chapters"],
                        "words": vol["words"],
                    },
                    "readiness": {
                        "ready": report.ready,
                        # The check's own label, so the page never keeps a
                        # second (drifting) copy of what each key is called.
                        "blocking": [
                            {"key": c.key, "label": c.label} for c in report.blockers
                        ],
                    },
                    "readers": n_readers,
                    "reading_elsewhere": elsewhere.get(lang.code, 0),
                }
            )

        # Healthiest first; the frontend can invert to lead with what needs work.
        rows.sort(key=lambda r: (-r["health"], r["name"]))
        # The weights ride along so the page can show what each signal is worth
        # (and what it has lost) without keeping a second copy of them.
        return {
            "source_published_books": source_published,
            "weights": _WEIGHTS,
            "engagement_target": _ENGAGEMENT_TARGET,
            "coverage_mix": _COVERAGE_MIX,
            "source_shelf": source_shelf,
            "reader_window_days": _READER_WINDOW_DAYS,
            "languages": rows,
        }

    # --- component scores ------------------------------------------------------

    @classmethod
    def _shelf(cls, counts: dict, published_books: int) -> dict[str, int]:
        """A language's count of each kind in ``_COVERAGE_MIX``, from its readiness
        checks by key. Books are the published count the rest of the view uses;
        the others come from the readiness report, which counts them for every
        language."""
        shelf = {k: cls._current(counts.get(k)) for k in _COVERAGE_MIX}
        shelf["books"] = published_books
        return shelf

    @staticmethod
    def _coverage(have: dict[str, int], source: dict[str, int]) -> float:
        """The mix-weighted share of the source shelf present, each kind capped
        at 1. Kinds the source has none of are left out and the weights of the
        rest renormalised; with no source shelf at all, coverage is full."""
        kinds = [k for k in _COVERAGE_MIX if source.get(k)]
        total = sum(_COVERAGE_MIX[k] for k in kinds)
        if not total:
            return 1.0
        return (
            sum(_COVERAGE_MIX[k] * min(1.0, have[k] / source[k]) for k in kinds)
            / total
        )

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
        """Distinct readers whose progress in each language moved within the last
        ``_READER_WINDOW_DAYS`` — "active" the way the engagement page counts it
        (``updated_at``, the server's clock)."""
        from datetime import timedelta

        from django.utils import timezone

        from reading.models import ReadingProgress

        since = timezone.now() - timedelta(days=_READER_WINDOW_DAYS)
        return {
            r["language"]: r["n"]
            for r in ReadingProgress.objects.filter(updated_at__gte=since)
            .values("language")
            .annotate(n=Count("profile", distinct=True))
        }
