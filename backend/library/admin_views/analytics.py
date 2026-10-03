"""Admin dashboard API — reading & account analytics (engagement, users)."""

from __future__ import annotations

from functools import cached_property

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import is_admin_user, requires

from .. import dropoff
from ..audit import AdminAudited, actor_email
from ..demand import FAILED_QUERY_MIN_LEN
from ..engagement_trends import (
    distinct_readers,
    latest_day,
    pulse_trends,
    readers_per_work,
    reading_hours,
    retention_cohorts,
    weekly_active,
    weekly_signups,
    window,
)
from ..models import (
    AdminAction,
    Article,
    Author,
    Book,
    SearchClickLog,
    SearchDecision,
    Sermon,
    fold_query,
)
from ..search import MIN_QUERY_LEN
from ..search_triage import GRACE, PIN_KINDS, clear_rules, pinned_hit, with_status
from ..team_events import team_events
from ..views import _language_entry
from ..weeks import day_of, week_start, week_starts


def _prefer_en(rows, value_of):
    """``slug`` → value, keeping the English row where a slug has several
    language editions (else first-seen). The one place the "prefer en" rule
    lives, shared by every title/label resolver below.
    """
    out: dict[str, object] = {}
    for r in rows:
        if r["language"] == "en" or r["slug"] not in out:
            out[r["slug"]] = value_of(r)
    return out


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminEngagementView(APIView):
    """Reading-engagement analytics from ReadingProgress / ChapterMarks.

    Aggregate-only — counts and per-book/-language rollups, never individual
    readers' identities. "Active" is distinct readers who read on any day of
    the window, from the reading-day log (every day a reader read, not just
    each work's latest touch); "finishers" reached (or passed) the book's last
    English chapter.
    """


    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone

        from reading.models import ChapterMarks, Favorite, ReadingProgress

        now = timezone.now()
        range_key = request.query_params.get("range", "")
        if range_key not in self.RANGES:
            range_key = self.DEFAULT_RANGE
        days = self.RANGES[range_key]

        # Every active window in one query, from the reading-day log.
        active = distinct_readers(
            {
                "7d": window(now, 7),
                "7d_prev": window(now, 7, 7),
                "30d": window(now, 30),
                "30d_prev": window(now, 30, 30),
            }
        )

        def hearts(days, offset=0):
            """Favorites created in the same kind of window, for the hearts
            trend chip. Counts rows (a saved item), not distinct readers."""
            qs = Favorite.objects.filter(created_at__gte=now - timedelta(days=days + offset))
            if offset:
                qs = qs.filter(created_at__lt=now - timedelta(days=offset))
            return qs.count()

        overview = {
            "readers": ReadingProgress.objects.values("profile").distinct().count(),
            "progress_rows": ReadingProgress.objects.count(),
            # "Today" is the last 24 hours of saved progress: a rolling window
            # needs no history, and day-boundaries differ reader to reader.
            "active_1d": ReadingProgress.objects.filter(updated_at__gte=now - timedelta(days=1))
            .values("profile")
            .distinct()
            .count(),
            "active_7d": active["7d"],
            "active_7d_prev": active["7d_prev"],
            "active_30d": active["30d"],
            "active_30d_prev": active["30d_prev"],
            "readers_with_marks": ChapterMarks.objects.exclude(marks=[])
            .values("profile")
            .distinct()
            .count(),
            "marked_chapters": ChapterMarks.objects.exclude(marks=[]).count(),
            "hearts": Favorite.objects.count(),
            "hearts_7d": hearts(7),
            "hearts_7d_prev": hearts(7, 7),
            "total_users": self._total_users(),
        }
        return Response(
            {
                "overview": overview,
                "period": self._period(now, range_key, days),
                "time": self._reading_time(now, days),
                "top_content": self._top_content(),
                "rising": self._rising(now),
                "highlight_heatmap": self._highlight_heatmap(),
                "most_loved": self._most_loved(),
                "hearts_by_kind": self._hearts_by_kind(),
                "plan_funnel": self._plan_funnel(),
                "by_language": self._by_language(),
                "weekly_active": weekly_active(now, self.WEEKS),
                "events": self._events(now),
                "cohorts": retention_cohorts(now),
                "hours": reading_hours(now, days),
                # The tiles' lines; none for the empty state, which shows no tiles.
                "trends": pulse_trends(
                    now,
                    self.WEEKS,
                    readers=overview["readers"],
                    users=overview["total_users"],
                )
                if overview["readers"]
                else None,
            }
        )

    #: The page's date range (``?range=``): its days, None for all time. It
    #: drives the figures that are about a PERIOD (the pulse's period tiles,
    #: the Reading time card, When people read). Running totals stay all
    #: time, the weekly charts keep their own axis, and the work rollups
    #: (top content, most loved, by language) stay all time: they rest on
    #: saved progress, which keeps only each work's latest touch, so "read in
    #: the last 30 days" is a claim they can't make.
    RANGES = {"7d": 7, "30d": 30, "90d": 90, "all": None}
    DEFAULT_RANGE = "30d"

    def _period(self, now, range_key: str, days: int | None) -> dict:
        """The range-following pulse figures, each with the same-length period
        just before it to compare against (None for all time, which has no
        "before"). Active readers from the reading-day log, as the 7- and
        30-day tiles count them; hearts and sign-ups when they were made;
        reading time by when a sitting was last seen."""
        from datetime import date, timedelta

        from django.db.models import Sum

        from accounts.models import UserProfile
        from reading.models import Favorite, ReadingSession

        if days is None:
            active = distinct_readers({"cur": (date.min, latest_day(now))})
            return {
                "range": range_key,
                "days": None,
                "active": {"value": active["cur"], "prev": None},
                "hearts": {"value": Favorite.objects.count(), "prev": None},
                "signups": {"value": UserProfile.objects.count(), "prev": None},
                "seconds": {
                    "value": ReadingSession.objects.aggregate(s=Sum("seconds"))["s"] or 0,
                    "prev": None,
                },
            }
        active = distinct_readers({"cur": window(now, days), "prev": window(now, days, days)})
        start, before = now - timedelta(days=days), now - timedelta(days=2 * days)

        def split(qs, field, total=None):
            """This period's and the one before's count, or sum of ``total``,
            in one query."""
            cur = Q(**{f"{field}__gte": start})
            prev = Q(**{f"{field}__gte": before, f"{field}__lt": start})
            agg = (lambda q: Sum(total, filter=q)) if total else (lambda q: Count("pk", filter=q))
            row = qs.filter(**{f"{field}__gte": before}).aggregate(cur=agg(cur), prev=agg(prev))
            return {"value": row["cur"] or 0, "prev": row["prev"] or 0}

        return {
            "range": range_key,
            "days": days,
            "active": {"value": active["cur"], "prev": active["prev"]},
            "hearts": split(Favorite.objects, "created_at"),
            "signups": split(UserProfile.objects, "created_at"),
            "seconds": split(ReadingSession.objects, "last_seen_at", "seconds"),
        }

    def _reading_time(self, now, days: int | None = None):
        """Time-on-site rollup from ReadingSession (see reading.models).

        ``seconds`` is *active* reading time, so these are real reading totals,
        not tab-open time. Windows are on ``last_seen_at`` (when the sitting was
        last touched). ``avg_session_seconds`` is over sittings with any time.
        Empty (all zeros) until the instrumentation has data — the panel hides
        itself then.
        """
        from datetime import timedelta

        from django.db.models import Avg, Count, Sum

        from reading.models import ReadingSession

        sessions = ReadingSession.objects.filter(seconds__gt=0)
        # The page's range: totals, the median and the length buckets cover
        # sittings last seen inside it. The fixed 7/30-day figures don't move.
        in_range = (
            sessions.filter(last_seen_at__gte=now - timedelta(days=days)) if days else sessions
        )

        def window(days):
            return sessions.filter(
                last_seen_at__gte=now - timedelta(days=days)
            ).aggregate(secs=Sum("seconds"), readers=Count("profile", distinct=True))

        # The length buckets ride the totals' query, so their sums and the
        # totals the page divides them by are one snapshot.
        totals = in_range.aggregate(
            secs=Sum("seconds"),
            count=Count("id"),
            readers=Count("profile", distinct=True),
            avg=Avg("seconds"),
            **self._bucket_aggregates(),
        )
        w7, w30 = window(7), window(30)
        return {
            "total_seconds": totals["secs"] or 0,
            "sessions": totals["count"] or 0,
            "readers": totals["readers"] or 0,
            "avg_session_seconds": round(totals["avg"] or 0),
            "median_session_seconds": self._median_seconds(in_range, totals["count"] or 0),
            "lengths": [
                {
                    "min_seconds": low,
                    "max_seconds": high,
                    "sittings": totals[f"b{low}_n"],
                    "seconds": totals[f"b{low}_s"] or 0,
                }
                for low, high in self._bucket_bounds()
            ],
            "seconds_7d": w7["secs"] or 0,
            "readers_7d": w7["readers"] or 0,
            "seconds_30d": w30["secs"] or 0,
            "readers_30d": w30["readers"] or 0,
        }

    # Where sitting-length buckets start, in seconds; the last is open-ended.
    # The average hides the spread (a few long reads on many short looks reads
    # the same as everyone reading a little), so the page shows how many
    # sittings, and how much reading, fall in each. 15 minutes is where a
    # sitting stops being a look and becomes a read. The API sends each
    # bucket's bounds, so the page labels them from here and can't drift.
    SITTING_BUCKET_STARTS = (0, 60, 5 * 60, 15 * 60, 30 * 60)

    @classmethod
    def _bucket_bounds(cls):
        starts = cls.SITTING_BUCKET_STARTS
        return list(zip(starts, (*starts[1:], None), strict=True))

    @classmethod
    def _bucket_aggregates(cls):
        from django.db.models import Sum

        aggs = {}
        for low, high in cls._bucket_bounds():
            q = Q(seconds__gte=low) & (Q(seconds__lt=high) if high else Q())
            aggs[f"b{low}_n"] = Count("id", filter=q)
            aggs[f"b{low}_s"] = Sum("seconds", filter=q)
        return aggs

    @staticmethod
    def _median_seconds(sessions, count: int) -> int:
        """The middle sitting's length (the mean of the two middles when even,
        halves rounded up).

        Read by offset rather than a database percentile so it means the same
        on SQLite (tests) and Postgres. ``count`` comes from an earlier query,
        so a row deleted in between can leave the slice short or empty.
        """
        values = list(
            sessions.order_by("seconds").values_list("seconds", flat=True)[
                max(count - 1, 0) // 2 : count // 2 + 1
            ]
        )
        return int(sum(values) / len(values) + 0.5) if values else 0

    def _total_users(self) -> int:
        from accounts.models import UserProfile

        return UserProfile.objects.count()

    @cached_property
    def _work_meta(self) -> dict:
        """``(kind, slug)`` → ``(title, author)`` for every work a row can name.

        A ``cached_property`` so the three roll-ups that need it (most read,
        marked and loved) share one build per request instead of rebuilding the
        whole-catalogue map three times. The view instance is per-request, so
        the cache never outlives it.

        Keyed by kind as well as slug because ``ReadingProgress.book_slug`` names
        a book, a sermon OR an author biography (see ``WorkKind``), and those
        namespaces overlap: a sermon sharing a slug with a book used to be
        labelled with the BOOK's title and author.
        """
        meta: dict[tuple[str, str], tuple[str, str]] = {}

        def by_author(r):
            return (r["title"], r["author__name"])

        for kind, rows, value_of in (
            ("book", Book.objects.values("slug", "language", "title", "author__name"), by_author),
            ("sermon", Sermon.objects.values("slug", "language", "title", "author__name"), by_author),
            # An article's byline is the house, so it names no author.
            ("article", Article.objects.values("slug", "language", "h1"), lambda r: (r["h1"], "")),
        ):
            meta.update({(kind, slug): v for slug, v in _prefer_en(rows, value_of).items()})
        # A biography's slug names the AUTHOR, so the person is the title.
        for a in Author.objects.values("slug", "name"):
            meta[("bio", a["slug"])] = (a["name"], "")
        return meta

    def _row(self, meta, kind, slug, **extra) -> dict:
        title, author = meta.get((kind, slug), (slug, ""))
        return {"kind": kind, "slug": slug, "title": title, "author": author, **extra}

    def _leaderboard(self, work_kind, fav_kind, limit: int = 8) -> list[dict]:
        """Top works of one kind by readers, each carrying the four figures the
        page shows side by side: readers, finishers, hearts and distinct
        highlighters.

        Finishers come from the stored ``finished_at`` stamp — the same explicit,
        synced completion the reader's "Finished" shelf counts — as a conditional
        aggregate in the grouped read query (one scan, and it counts for every
        kind). Hearts and highlighters are two more grouped lookups scoped to the
        leaderboard's own slugs, so a tab is a bounded handful of queries however
        large the library grows.
        """
        from reading.models import ChapterMarks, Favorite, ReadingProgress

        top = list(
            ReadingProgress.objects.filter(kind=work_kind)
            .values("book_slug")
            .annotate(
                readers=Count("profile", distinct=True),
                finishers=Count(
                    "profile", filter=Q(finished_at__isnull=False), distinct=True
                ),
            )
            .order_by("-readers")[:limit]
        )
        slugs = [r["book_slug"] for r in top]
        hearts = {
            r["slug"]: r["n"]
            for r in Favorite.objects.filter(kind=fav_kind, slug__in=slugs)
            .values("slug")
            .annotate(n=Count("id"))
        }
        highlighters = {
            r["book_slug"]: r["n"]
            for r in ChapterMarks.objects.filter(kind=work_kind, book_slug__in=slugs)
            .exclude(marks=[])
            .values("book_slug")
            .annotate(n=Count("profile", distinct=True))
        }
        meta = self._work_meta
        return [
            self._row(
                meta,
                work_kind,
                r["book_slug"],
                readers=r["readers"],
                finishers=r["finishers"],
                hearts=hearts.get(r["book_slug"], 0),
                highlighters=highlighters.get(r["book_slug"], 0),
            )
            for r in top
        ]

    def _top_content(self) -> dict:
        """The reach-vs-depth leaderboard, split by kind so each tab holds its
        own top works. Books, sermons and biographies each carry both reads and
        marks, so the same four columns read across all three; plans and topics
        engage in different shapes (a funnel; saved-by-kind) and live elsewhere
        on the page."""
        from reading.models import FavoriteKind, WorkKind

        books = self._leaderboard(WorkKind.BOOK, FavoriteKind.BOOK)
        # A book also carries where its readers stop, chapter by chapter, for
        # its row's sparkline; the other kinds are one document each.
        curves = dropoff.work_curves([b["slug"] for b in books])
        for b in books:
            b["reach"] = curves.get(b["slug"])
        return {
            "book": books,
            "sermon": self._leaderboard(WorkKind.SERMON, FavoriteKind.SERMON),
            "bio": self._leaderboard(WorkKind.BIO, FavoriteKind.AUTHOR),
            "article": self._leaderboard(WorkKind.ARTICLE, FavoriteKind.ARTICLE),
        }

    def _hearts_by_kind(self) -> list[dict]:
        """Hearts (Favorites) per kind. Readers save more than the works they
        read — authors, plans, topics, articles and quotes too — so this is the
        one place the full shape of what's being saved shows, even where the
        individual items aren't titled below."""
        from reading.models import Favorite

        return [
            {"kind": r["kind"], "count": r["count"]}
            for r in Favorite.objects.values("kind")
            .annotate(count=Count("id"))
            .order_by("-count")
        ]

    def _most_loved(self, limit: int = 10) -> list[dict]:
        """Most-hearted works, named. A Favorite's ``author`` kind saves a
        person, which ``_work_meta`` keys as a ``bio``; books and sermons keep
        their kind. The other favoritable kinds (plans, topics, articles,
        quotes) are counted in ``_hearts_by_kind`` rather than titled here — they
        don't share ``_work_meta``'s (kind, slug) namespace."""
        from reading.models import Favorite, FavoriteKind

        meta = self._work_meta
        kind_to_meta = {
            FavoriteKind.BOOK: "book",
            FavoriteKind.SERMON: "sermon",
            FavoriteKind.AUTHOR: "bio",
        }
        top = (
            Favorite.objects.filter(kind__in=list(kind_to_meta))
            .values("kind", "slug")
            .annotate(hearts=Count("id"))
            .order_by("-hearts")[:limit]
        )
        return [
            self._row(meta, kind_to_meta[r["kind"]], r["slug"], hearts=r["hearts"])
            for r in top
        ]

    def _rising(self, now, limit: int = 8) -> list[dict]:
        """Works with the biggest gain in weekly readers — what's catching on
        NOW, beside the all-time leaderboard that a few classics dominate.
        Counts readers active on a work in each window
        (``library.engagement_trends.readers_per_work``), not brand-new
        readers — labelled as such on the page — and small movements wash out
        because only positive deltas rank."""
        this_week, prev_week = readers_per_work(now)
        meta = self._work_meta
        rows = []
        for (kind, slug), this_n in this_week.items():
            prev_n = prev_week.get((kind, slug), 0)
            delta = this_n - prev_n
            if delta <= 0:
                continue
            rows.append(
                self._row(meta, kind, slug, this_week=this_n, prev_week=prev_n, delta=delta)
            )
        rows.sort(key=lambda r: (-r["delta"], -r["this_week"]))
        return rows[:limit]

    def _highlight_heatmap(self) -> dict | None:
        """Per-chapter highlight density for the most-marked book — the heat
        strip that shows WHERE in a work readers mark up.

        A book, because the strip is per chapter: a single-document sermon or
        biography would be one cell. Every chapter is returned, unmarked ones
        included (0), so the frontend can draw the full strip; ``peak`` names the
        chapter that resonates most."""
        from reading.models import ChapterMarks, WorkKind

        from ..models import Chapter

        top = (
            ChapterMarks.objects.filter(kind=WorkKind.BOOK)
            .exclude(marks=[])
            .values("book_slug")
            .annotate(readers=Count("profile", distinct=True))
            .order_by("-readers")
            .first()
        )
        if not top:
            return None
        slug = top["book_slug"]
        per = {
            r["chapter_order"]: r["readers"]
            for r in ChapterMarks.objects.filter(kind=WorkKind.BOOK, book_slug=slug)
            .exclude(marks=[])
            .values("chapter_order")
            .annotate(readers=Count("profile", distinct=True))
        }
        # Draw the full strip: the English edition's chapter count, or (if that
        # book isn't in the catalogue) the highest marked chapter as a fallback.
        length = (
            Chapter.objects.filter(book__slug=slug, book__language="en").count()
            or max(per, default=0)
        )
        chapters = [{"chapter": i, "readers": per.get(i, 0)} for i in range(1, length + 1)]
        peak = max(chapters, key=lambda c: c["readers"], default=None)
        title, author = self._work_meta.get(("book", slug), (slug, ""))
        return {
            "slug": slug,
            "title": title,
            "author": author,
            "chapters": chapters,
            "peak_chapter": peak["chapter"] if peak and peak["readers"] else None,
            "peak_readers": peak["readers"] if peak else 0,
        }

    def _plan_funnel(self) -> dict:
        """Reading-plan engagement: the started → came-back → completed funnel,
        overall and per plan.

        A plan's length is its number of distinct days (identical across the
        per-language rows that share a slug); ``PlanProgress.done`` is the list of
        day-numbers a reader has ticked off, so *completed* is ``len(done) >=
        length`` and *came back* (used the plan past its first day) is
        ``len(done) >= 2``. The done lists are read once and bucketed in Python —
        a JSON array's length isn't a filter the DB can push down, and the row
        count here is readers×plans, not content-sized."""
        from reading.models import PlanProgress

        from ..models import Plan, PlanDay

        lengths = {
            r["plan__slug"]: r["n"]
            for r in PlanDay.objects.values("plan__slug").annotate(
                n=Count("day", distinct=True)
            )
        }
        # Prefer the English title; fall back to whatever language exists.
        titles: dict[str, str] = {}
        for p in Plan.objects.values("slug", "language", "title"):
            if p["language"] == "en" or p["slug"] not in titles:
                titles[p["slug"]] = p["title"]

        agg: dict[str, dict] = {}
        for slug, done in PlanProgress.objects.values_list("plan_slug", "done"):
            a = agg.setdefault(slug, {"started": 0, "returned": 0, "completed": 0})
            a["started"] += 1
            n = len(done or [])
            if n >= 2:
                a["returned"] += 1
            length = lengths.get(slug)
            if length and n >= length:
                a["completed"] += 1

        by_plan = sorted(
            (
                {"slug": slug, "title": titles.get(slug, slug), "length": lengths.get(slug), **a}
                for slug, a in agg.items()
            ),
            key=lambda r: -r["started"],
        )
        return {
            "started": sum(a["started"] for a in agg.values()),
            "returned": sum(a["returned"] for a in agg.values()),
            "completed": sum(a["completed"] for a in agg.values()),
            "by_plan": by_plan[:12],
        }

    def _by_language(self) -> list[dict]:
        from reading.models import ReadingProgress

        rows = (
            ReadingProgress.objects.values("language")
            .annotate(readers=Count("profile", distinct=True))
            .order_by("-readers")
        )
        out = []
        for r in rows:
            entry = _language_entry(r["language"])
            entry["readers"] = r["readers"]
            out.append(entry)
        return out

    WEEKS = 8

    def _events(self, now, weeks: int = WEEKS) -> list[dict]:
        """What the team did in the charted weeks (``library.team_events``),
        for the markers under the weekly chart: each with the ``week`` the
        chart keys it by, its ``date``, and whether it falls in the same last
        7 days as ``active_7d`` (``recent``), for the summary sentence."""

        first_recent, _ = window(now, 7)  # the same days as active_7d
        out = []
        for e in team_events(week_starts(now, weeks)[0]):
            at = e.pop("at")
            out.append(
                {
                    **e,
                    "week": week_start(day_of(at)).isoformat(),
                    "date": day_of(at).isoformat(),
                    "recent": day_of(at) >= first_recent,
                }
            )
        return out


# Human labels for the reader themes stored on UserProfile.
THEME_LABELS = {
    "": "Not yet set",
    "system": "Match device",
    "light": "Light",
    "paper": "Paper (light, legacy)",
    "dark": "Lamplight (dark)",
    "sepia": "Sepia",
}

# Human labels for the Supabase auth providers stored on UserProfile.providers.
# Anything unlisted is title-cased so a new provider still reads sensibly.
PROVIDER_LABELS = {
    "email": "Email",
    "google": "Google",
    "apple": "Apple",
    "facebook": "Facebook",
    "github": "GitHub",
    "azure": "Microsoft",
}


def _provider_label(code: str) -> str:
    return PROVIDER_LABELS.get(code, code.replace("_", " ").title())


# Human labels for the logged-out home sign-up band arms (see
# accounts.models.SIGNUP_VARIANTS). "progress" is the progress-targeted variant,
# shown only to readers who already have local reading — a warmer audience than
# the random A/B arms, so it is not comparable head-to-head; the UI keeps it
# labelled and set apart. Anything unlisted is title-cased.
SIGNUP_VARIANT_LABELS = {
    "keep": "Keep what you find",
    "habit": "Reading rhythm",
    "library": "Build your shelf",
    "progress": "Progress-targeted",
}


def _signup_variant_label(code: str) -> str:
    return SIGNUP_VARIANT_LABELS.get(code, code.replace("_", " ").title())


def mask_email(email: str) -> str:
    """Mask an address for a non-super admin — the server-side twin of the
    frontend's ``maskEmail``: first char of the local part, bullets, then the
    domain.

    Reader emails are PII. Only the ``ADMIN_EMAILS`` super admins may see them in
    the clear; a scoped ``USERS`` grantee (a language admin) gets them masked *at
    the source*, so the raw address never reaches their browser — the client-side
    "Reveal emails" toggle was cosmetic on its own (a founder decision, 2026-09-21).
    """
    at = (email or "").find("@")
    if at <= 0:
        return "•••"
    local = email[:at]
    return f"{local[:1]}{'•' * max(3, len(local) - 1)}{email[at:]}"


def _profile_summary(p, *, reveal: bool) -> dict:
    """The per-account fields shared by the recent-signups list and the user
    directory. One home for the provider→label contract (labelled server-side so
    the frontend keeps no copy of the map — see ``_recent``); the directory adds
    its own rollups on top of this.

    ``reveal`` is the caller's super-admin flag and is REQUIRED (no default): this
    is the single chokepoint that emits a reader's email, so the caller must state
    the PII decision every time rather than fall through to cleartext. Emails are
    masked for everyone but a super admin (see :func:`mask_email`).
    """
    return {
        # The stable handle the per-user detail page is keyed by.
        "uid": str(p.supabase_uid),
        "display_name": p.display_name,
        "email": p.email if reveal else mask_email(p.email),
        "providers": [{"code": c, "label": _provider_label(c)} for c in p.provider_list],
        "locale": p.locale,
        "joined_at": p.created_at.isoformat(),
        "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
    }


# How many of the most recent sign-ups the admin page lists individually.
RECENT_SIGNUPS_LIMIT = 25


def _activation_counts() -> dict[str, int]:
    """Sign-up to habit: how many accounts reach each step, where every step
    is a subset of the one before it, so the drop between two steps is real.

    * signed_up — every account;
    * started — has any reading progress (the Users page's "Activated");
    * returned — read on two or more days, from ``ReadingDay`` (the streak log:
      one row per reader per LOCAL date). A sitting that runs past midnight
      counts as two days, and readers from before that log existed, or on a
      client that never sent it, can read as not having come back;
    * finished — of those, finished a book, sermon, biography or article (the
      stored ``finished_at`` stamp). Because steps nest, a reader who finished
      in a single day stops at "started", so this is lower than the
      engagement page's finisher counts.

    Each account's three facts are annotated once and then counted, so every
    subquery runs once per account rather than once per step.
    """
    from django.db.models import Exists, OuterRef, Subquery
    from django.db.models.functions import Coalesce

    from accounts.models import UserProfile
    from reading.models import ReadingDay, ReadingProgress

    progress = ReadingProgress.objects.filter(profile=OuterRef("pk"))
    days = (
        ReadingDay.objects.filter(profile=OuterRef("pk"))
        .values("profile")
        .annotate(n=Count("pk"))
        .values("n")
    )
    started, returned = Q(has_progress=True), Q(has_progress=True, days__gte=2)
    return UserProfile.objects.annotate(
        has_progress=Exists(progress),
        days=Coalesce(Subquery(days), 0),
        has_finished=Exists(progress.filter(finished_at__isnull=False)),
    ).aggregate(
        signed_up=Count("pk"),
        started=Count("pk", filter=started),
        returned=Count("pk", filter=returned),
        finished=Count("pk", filter=returned & Q(has_finished=True)),
    )


@requires(AdminCapability.USERS, verb=AdminVerb.VIEW)
class AdminUsersView(APIView):
    """Account analytics: sign-up growth, locale/theme split, activation.

    Mostly aggregate over ``accounts.UserProfile``. ``total``, ``with_activity``
    and the ``activation`` funnel all come from ``_activation_counts``, so the
    tiles and the funnel always agree. The ``recent`` list is the exception:
    it names individual accounts (display name, email, sign-in method) so the
    founder can see who is actually signing up — admin-only, behind
    ``IsAdminEmail``, and served to no one else.
    """


    def get(self, request):
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

        from accounts.models import UserProfile

        now = timezone.now()
        # Total and activated come from the same counts as the funnel, so the
        # tiles and the funnel's first two steps can never disagree.
        activation = _activation_counts()
        total = activation["signed_up"]
        with_activity = activation["started"]

        def signups_between(start_days, end_days=0):
            qs = UserProfile.objects.filter(created_at__gte=now - timedelta(days=start_days))
            if end_days:
                qs = qs.filter(created_at__lt=now - timedelta(days=end_days))
            return qs.count()

        return Response(
            {
                "total": total,
                "with_activity": with_activity,
                "dormant": max(0, total - with_activity),
                "activation": [{"step": k, "count": n} for k, n in activation.items()],
                "signups_7d": signups_between(7),
                "signups_30d": signups_between(30),
                # The immediately preceding window, so the UI can show a trend
                # delta (this 7 days vs the 7 before it, this 30 vs the prior 30).
                "signups_prev_7d": signups_between(14, 7),
                "signups_prev_30d": signups_between(60, 30),
                "weekly_signups": self._weekly_signups(now),
                "by_method": self._by_method(),
                "by_signup_variant": self._by_signup_variant(),
                "recent": self._recent(reveal=is_admin_user(request.user, request)),
                "by_locale": self._by_locale(),
                **self._geography(),
                "by_theme": [
                    {
                        "theme": r["theme"],
                        "label": THEME_LABELS.get(r["theme"], r["theme"]),
                        "count": r["n"],
                    }
                    for r in UserProfile.objects.values("theme")
                    .annotate(n=Count("id"))
                    .order_by("-n")
                ],
            }
        )

    def _by_method(self):
        """Accounts per sign-in provider.

        A provider is counted for every account that has it, so an account with
        both email and Google adds to both rows (the totals overlap, on
        purpose). ``unknown`` collects accounts with nothing recorded yet — a
        row created before providers were captured, whose owner hasn't signed in
        since. Shown by the UI only when non-zero.
        """
        from collections import Counter

        from accounts.models import UserProfile, split_providers

        counter: Counter[str] = Counter()
        unknown = 0
        for providers in UserProfile.objects.values_list("providers", flat=True):
            codes = split_providers(providers)
            if codes:
                counter.update(codes)
            else:
                unknown += 1

        out = [
            {"method": code, "label": _provider_label(code), "count": n}
            for code, n in counter.most_common()
        ]
        if unknown:
            out.append({"method": "unknown", "label": "Unknown", "count": unknown})
        return out

    def _by_signup_variant(self):
        """Accounts per logged-out sign-up band arm — the home page's A/B test.

        Each account counts once, under the arm that was showing when it was
        created (create-only, so a later login can't move it). ``targeted``
        flags the progress-targeted variant: it is shown only to readers who
        already had local reading, so its rate is NOT comparable head-to-head
        with the random arms — the UI sets it apart. ``unknown`` collects
        accounts with nothing recorded (created before this shipped, or a
        sign-up that carried no variant, e.g. Google OAuth). Only the four known
        arms are ever stored (validated on capture), so no junk reaches here.
        """
        from django.db.models import Count

        from accounts.models import UserProfile

        rows = {
            r["signup_variant"]: r["n"]
            for r in UserProfile.objects.values("signup_variant").annotate(n=Count("id"))
        }
        unknown = rows.pop("", 0)
        out = [
            {
                "variant": code,
                "label": _signup_variant_label(code),
                "count": n,
                "targeted": code == "progress",
            }
            for code, n in sorted(rows.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        if unknown:
            out.append(
                {"variant": "unknown", "label": "Unknown", "count": unknown, "targeted": False}
            )
        return out

    def _recent(self, *, reveal: bool = False):
        """The most recent sign-ups, named — see the class docstring on why.

        ``reveal`` is the requester's super-admin flag; it defaults to fail-closed
        (masked) so a caller that forgets it never leaks cleartext PII. Emails are
        masked for a scoped ``USERS`` grantee (see :func:`mask_email`)."""
        from accounts.models import UserProfile

        rows = UserProfile.objects.order_by("-created_at")[:RECENT_SIGNUPS_LIMIT]
        return [_profile_summary(p, reveal=reveal) for p in rows]

    def _by_locale(self):
        from django.db.models import Count

        from accounts.models import UserProfile

        out = []
        for r in (
            UserProfile.objects.values("locale")
            .annotate(n=Count("id"))
            .order_by("-n")
        ):
            entry = _language_entry(r["locale"])
            entry["count"] = r["n"]
            out.append(entry)
        return out

    def _geography(self, tz_limit: int = 12):
        """Where readers are, from the captured browser timezone — as two
        breakdowns off ONE grouped scan of the ``timezone`` column.

        Approximate by design (a timezone names a region, not a person; no IP is
        stored). ``by_country`` derives an ISO country per zone
        (``accounts.geo``) — a dict lookup over the handful of distinct zones,
        not every account — and folds unmapped and blank zones into a single
        ``"unknown"`` bucket (the same string-sentinel convention as
        ``by_method``), ordered last regardless of size. ``by_timezone`` is the
        raw zones (blanks dropped — the country "unknown" bucket already counts
        them), capped with the tail folded into an ``"Other"`` row.
        """
        from collections import Counter

        from django.db.models import Count

        from accounts.geo import country_for_timezone, country_name
        from accounts.models import UserProfile

        rows = list(UserProfile.objects.values("timezone").annotate(n=Count("id")))

        # Country: fold the grouped zones through the derivation.
        counter: Counter[str | None] = Counter()
        for r in rows:
            counter[country_for_timezone(r["timezone"] or "")] += r["n"]
        unknown = counter.pop(None, 0)
        by_country = [
            {"code": code, "name": country_name(code), "count": n}
            for code, n in counter.most_common()
        ]
        if unknown:
            by_country.append({"code": "unknown", "name": "Unknown", "count": unknown})

        # Timezone: the raw zones, blanks excluded, top-N with an "Other" tail.
        tz_rows = sorted(
            (r for r in rows if r["timezone"]), key=lambda r: (-r["n"], r["timezone"])
        )
        by_timezone = [
            {"timezone": r["timezone"], "count": r["n"]} for r in tz_rows[:tz_limit]
        ]
        rest = sum(r["n"] for r in tz_rows[tz_limit:])
        if rest:
            by_timezone.append({"timezone": "Other", "count": rest})

        return {"by_country": by_country, "by_timezone": by_timezone}

    def _weekly_signups(self, now, weeks: int = 12):

        starts = week_starts(now, weeks)
        return [
            {"week": wk.isoformat(), "count": n}
            for wk, n in zip(starts, weekly_signups(starts), strict=True)
        ]


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSearchView(APIView):
    """Search analytics — what readers look for, and what they don't find.

    Aggregate-only, from the anonymous SearchQueryLog. Zero-result queries are
    the roadmap signal: each one is a reader asking for content or spelling
    tolerance we don't have yet. Top lists skip fragments under 3 characters
    (search-as-you-type prefixes) and fold case.

    Counts are searches readers finished typing: the type-ahead fragments a
    longer search extended ("pra" on the way to "prayer") are hidden by
    SearchQueryLog's default manager, so they inflate neither the volume nor
    the zero-result rate. A 2-char query that WASN'T extended still counts
    (they're real searches in e.g. Chinese). Rows, not readers: compare
    trends, not absolutes.
    """


    def get(self, request):
        from datetime import timedelta

        from django.db.models.functions import Length, Lower, TruncDate
        from django.utils import timezone

        from ..models import SearchQueryLog

        now = timezone.now()
        window = SearchQueryLog.objects.filter(created_at__gte=now - timedelta(days=30))

        # Each period and the one before it (the baseline the page's deltas
        # divide by), as conditional counts over ONE scan per log: the four
        # windows overlap inside the last 60 days.
        windows = {"7d": (7, 0), "30d": (30, 0), "7d_prev": (7, 7), "30d_prev": (30, 30)}

        def span(key):
            # The current windows stay open-ended, like the lists on this page,
            # so a row logged mid-request can't land in one section but not
            # another.
            days, offset = windows[key]
            q = Q(created_at__gte=now - timedelta(days=days + offset))
            return q & Q(created_at__lt=now - timedelta(days=offset)) if offset else q

        recent = Q(created_at__gte=now - timedelta(days=60))
        counts = SearchQueryLog.objects.filter(recent).aggregate(
            **{
                f"{k}_{name}": Count(expr, filter=span(k) & extra, distinct=distinct)
                for k in windows
                for name, expr, extra, distinct in (
                    ("searches", "id", Q(), False),
                    ("zero", "id", Q(result_count=0), False),
                    ("distinct", Lower("query"), Q(), True),
                )
            }
        )
        # Opened results in each window. Rows, not readers (the logs are
        # anonymous), so a rate built on it is a trend, not "x% of people".
        clicks = SearchClickLog.objects.filter(recent).aggregate(
            **{k: Count("id", filter=span(k)) for k in windows}
        )

        def overview(k):
            searches, zero = counts[f"{k}_searches"], counts[f"{k}_zero"]
            return {
                "searches": searches,
                "clicks": clicks[k],
                "distinct_queries": counts[f"{k}_distinct"],
                "zero_results": zero,
                "zero_rate": round(zero / searches, 3) if searches else 0.0,
            }

        def top(qs, limit=20):
            rows = (
                qs.annotate(q=Lower("query"), qlen=Length("query"))
                .filter(qlen__gte=FAILED_QUERY_MIN_LEN)
                .values("q")
                .annotate(count=Count("id"))
                .order_by("-count", "q")[:limit]
            )
            return [{"query": r["q"], "count": r["count"]} for r in rows]

        # Exactly the last 14 UTC calendar days, zero-filled — a sparse
        # aggregate would render adjacent bars for non-adjacent dates.
        days = [(now - timedelta(days=i)).date() for i in range(13, -1, -1)]
        buckets = {
            str(r["day"]): r
            for r in SearchQueryLog.objects.filter(created_at__date__gte=days[0])
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                searches=Count("id"),
                zero=Count("id", filter=Q(result_count=0)),
            )
        }
        daily = [
            {
                "day": str(d),
                "searches": buckets.get(str(d), {}).get("searches", 0),
                "zero": buckets.get(str(d), {}).get("zero", 0),
            }
            for d in days
        ]

        # Capped: language comes from an unauthenticated query param, so junk
        # codes (≤10 chars) can create rows — don't let them flood the page.
        by_language = list(
            window.values("language")
            .annotate(
                searches=Count("id"),
                zero=Count("id", filter=Q(result_count=0)),
            )
            .order_by("-searches")[:20]
        )

        # The same zero-result signal, split BY LANGUAGE — which is the form that
        # can be acted on. "Readers searched this 31 times and found nothing" is
        # only a translation priority once you know which language they were
        # reading in; the global list mixes a Swahili gap with an English one and
        # neither can be queued from it.
        #
        # One grouped query for the queries, and the totals come from the
        # ``by_language`` rows already computed above — so the two sections of
        # the report can never disagree about how many searches a language
        # missed. Whether the content exists ELSEWHERE to translate from is the
        # expensive question, answered on demand by AdminSearchGapView rather
        # than for every row of a report that mostly gets skimmed.
        #
        # ``total`` counts every unanswered search in the language; ``queries``
        # lists the top ones at the report's usual 3-character floor, so the two
        # differ where readers missed on short fragments.
        worst = [
            r for r in sorted(by_language, key=lambda row: -row["zero"])[:10] if r["zero"]
        ]
        # Scoped to those ten languages so the fetched rows stay bounded by the
        # report rather than by how many distinct things readers have ever
        # failed to find.
        per_language: dict[str, list[dict]] = {r["language"]: [] for r in worst}
        # A triaged query leaves this list (it's on the Handled or Wanted tab)
        # unless its decision has stopped working — then it comes back, flagged,
        # carrying the decision so the page can say what was tried. Only the
        # outcomes that can stop working (search_triage.GRACE) need the since-scan.
        decisions = SearchDecision.objects.filter(language__in=list(per_language))
        decided = {(d.query, d.language) for d in decisions}
        reopened = {
            (d["query"], d["language"]): d
            for d in with_status(decisions.filter(outcome__in=list(GRACE)))
            if d["reopened"]
        }
        # Misses on triaged queries, so each language's header counts what's
        # still open rather than everything readers missed.
        settled: dict[str, int] = {}
        for r in (
            window.filter(result_count=0, language__in=list(per_language))
            .annotate(q=Lower("query"), qlen=Length("query"))
            .filter(qlen__gte=FAILED_QUERY_MIN_LEN)
            .values("language", "q")
            .annotate(count=Count("id"))
            .order_by("-count", "q")
        ):
            key = (fold_query(r["q"]), r["language"])
            if key in decided and key not in reopened:
                settled[r["language"]] = settled.get(r["language"], 0) + r["count"]
                continue
            queries = per_language[r["language"]]
            if len(queries) < 10:
                row = {"query": r["q"], "count": r["count"]}
                if key in reopened:
                    row["reopened"] = reopened[key]
                queries.append(row)

        unanswered = [
            {
                **_language_entry(r["language"]),
                "total": r["zero"] - settled.get(r["language"], 0),
                "queries": per_language[r["language"]],
            }
            for r in worst
            if per_language[r["language"]]
        ]

        # Queries that FOUND things and were never opened — the silent failure.
        # A query returning forty near-misses is indistinguishable from a good
        # one in every count above; both are "found something". Only the click
        # log separates them, and the gap is often the better content signal,
        # because nobody complains about a search that returned results.
        #
        # Two grouped queries and a dict lookup: the logs share no key but the
        # query text, on purpose (see SearchClickLog), so they are joined here
        # rather than in SQL.
        clicked = {
            (fold_query(r["q"]), r["language"])
            for r in SearchClickLog.objects.filter(created_at__gte=now - timedelta(days=30))
            .annotate(q=Lower("query"))
            .values("q", "language")
            .distinct()
        }
        answered = top(window.filter(result_count__gt=0))
        # Per language, because a pin is: "prayer" in English and "oración" in
        # Spanish are answered by different pages. A pinned query leaves the
        # list (it's on the Handled tab, with its opens since).
        pinned = set(
            SearchDecision.objects.filter(outcome=SearchDecision.Outcome.PINNED).values_list(
                "query", "language"
            )
        )
        unopened = []
        for r in (
            window.filter(result_count__gt=0)
            .annotate(q=Lower("query"), qlen=Length("query"))
            .filter(qlen__gte=FAILED_QUERY_MIN_LEN)
            .values("q", "language")
            .annotate(count=Count("id"))
            .order_by("-count", "q")[:60]
        ):
            key = (fold_query(r["q"]), r["language"])
            if key not in clicked and key not in pinned:
                unopened.append({"query": r["q"], "language": r["language"], "count": r["count"]})
                if len(unopened) == 10:
                    break

        return Response(
            {
                "overview": {k: overview(k) for k in windows},
                "unopened_queries": unopened,
                "top_queries": answered,
                "unanswered_by_language": unanswered,
                "daily": daily,
                "by_language": [
                    {
                        **_language_entry(r["language"]),
                        "searches": r["searches"],
                        "zero": r["zero"],
                    }
                    for r in by_language
                ],
            }
        )


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSearchGapView(APIView):
    """For one unanswered query: does the library have it in another language?

    The follow-up question to the zero-result list, and the one that turns a gap
    into a job — "nobody found `toba` in Swahili, and there are 40 English
    matches" means the content exists and needs translating, while zero
    everywhere means it does not exist at all and translation won't help.

    Its own endpoint, and only ever called for a row an admin opened. It runs the
    real search counters in every live language — and because it is asked only
    about queries that found NOTHING, the counters' ceiling never short-circuits:
    proving a language has no match means scanning it. Tens of queries per click,
    which is fine once on demand and would not be fine on every report load.

    This is an ADMIN planning signal, not a reader-facing fallback. Readers are
    never offered another language's results — a language shows what it has, and
    the answer to a thin language is to translate into it, which is exactly what
    this is for.
    """


    def get(self, request):
        from ..languages import live_codes
        from ..search import MIN_QUERY_LEN, count_by_type, hit_work, search_library

        q = (request.query_params.get("q") or "").strip()
        language = (request.query_params.get("language") or "").strip().lower()
        if len(q) < MIN_QUERY_LEN or not language:
            return Response(
                {"detail": f"q ({MIN_QUERY_LEN}+ chars) and language are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elsewhere = []
        # The specific works behind the matches, deduped across languages, so a
        # gap can be turned into a translation in one click. Keyed by (type, slug).
        works: dict[tuple[str, str], dict] = {}
        for code in live_codes():
            if code == language:
                continue
            counts, _ = count_by_type(q, code)
            total = sum(counts.values())
            if not total:
                continue
            elsewhere.append(
                {**_language_entry(code), "matches": total, "by_type": counts}
            )
            # Only languages that HAVE matches are searched in full, bounding the
            # extra work to the few that qualify (the counters above already
            # scanned every language; this adds a full search only where it pays).
            for hit in search_library(q, code):
                work = hit_work(hit)
                if work is None:
                    continue
                entry = works.setdefault((work["type"], work["slug"]), {**work, "languages": []})
                if code not in entry["languages"]:
                    entry["languages"].append(code)
        elsewhere.sort(key=lambda r: -r["matches"])
        # Most-corroborated works first (found in the most languages).
        ranked = sorted(works.values(), key=lambda w: (-len(w["languages"]), w["title"]))
        return Response(
            {
                "query": q,
                "language": language,
                "elsewhere": elsewhere,
                "works": ranked[:12],
            }
        )


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSearchDecisionListView(APIView):
    """Triaged unanswered searches — the Search page's Handled and Wanted tabs.

    Each decision comes with what readers did since (see
    :func:`library.search_triage.with_status`). Language is per row, so scope is
    enforced here rather than by the gate: a language-scoped admin sees only
    their languages' decisions.
    """

    def get(self, request):
        from accounts.permissions import allowed_languages

        qs = SearchDecision.objects.all()
        allowed = allowed_languages(request, AdminCapability.REPORTING, AdminVerb.VIEW)
        if allowed is not None:
            qs = qs.filter(language__in=allowed)
        return Response({"decisions": with_status(qs)})


@requires(
    AdminCapability.TRANSLATE,
    verbs={"POST": AdminVerb.ACT, "DELETE": AdminVerb.ACT},
    language_arg="language",
)
class AdminSearchDecisionView(AdminAudited, APIView):
    """Triage one unanswered search (POST), or undo that (DELETE).

    Gated on the translation queue at ``act`` in the query's language: deciding
    what a language's readers are missing is the same planning work, and it's
    the grant a language admin holds for their own languages (contributors and
    reviewers only ``suggest``). ``translate`` itself is super-admin-only, like
    filing the translation job it records (see AdminTranslationJobsView).
    """

    def audit_action_for(self, request):
        return (
            AdminAction.Action.SEARCH_UNDO
            if request.method == "DELETE"
            else AdminAction.Action.SEARCH_DECIDE
        )

    def audit_entry(self, request, response):
        src = request.query_params if request.method == "DELETE" else request.data
        target = f"{(src.get('language') or '').strip().lower()}:{fold_query(src.get('query') or '')}"
        # The target too: a synonym or pin changes what every reader gets back,
        # and once it's replaced or undone this row is the only record of it.
        detail = {"outcome": (response.data or {}).get("outcome", "")}
        if request.method != "DELETE":
            detail["to"] = (response.data or {}).get("target", "")
        return target, detail

    @staticmethod
    def _key(src) -> tuple[str, str] | None:
        query = fold_query(str(src.get("query") or ""))
        language = str(src.get("language") or "").strip().lower()
        if len(query) < 3 or not language:
            return None
        return query, language

    @staticmethod
    def _guard_translate(request, query, language):
        """A queued translation is a super admin's record — the job behind it is
        theirs to file — so only a super admin may replace or undo it."""
        if is_admin_user(request.user, request):
            return None
        if SearchDecision.objects.filter(
            query=query, language=language, outcome=SearchDecision.Outcome.TRANSLATE
        ).exists():
            return Response(
                {"detail": "A queued translation can only be changed by a super admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def post(self, request):
        from django.utils import timezone

        key = self._key(request.data)
        outcome = str(request.data.get("outcome") or "").strip()
        if key is None or outcome not in SearchDecision.Outcome.values:
            return Response(
                {
                    "detail": "query (3+ chars), language and outcome ("
                    + ", ".join(SearchDecision.Outcome.values)
                    + ") are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if outcome == SearchDecision.Outcome.TRANSLATE and not is_admin_user(
            request.user, request
        ):
            return Response(
                {"detail": "Only a super admin can queue translation work."},
                status=status.HTTP_403_FORBIDDEN,
            )
        query, language = key
        if refusal := self._guard_translate(request, query, language):
            return refusal
        target = str(request.data.get("target") or "").strip()[:200]
        if outcome == SearchDecision.Outcome.SYNONYM:
            # Stored folded, like the query, and refused when it's the query
            # itself: a synonym that searches for the same word does nothing.
            target = fold_query(target)
            if len(target) < MIN_QUERY_LEN or target == query:
                return Response(
                    {"detail": "A synonym needs a different word to search for."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if outcome == SearchDecision.Outcome.PINNED and pinned_hit(target, query, language) is None:
            return Response(
                {
                    "detail": "A pin must name a published page in this language, as "
                    f"kind:slug (kind one of {', '.join(PIN_KINDS)})."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = SearchDecision.objects.update_or_create(
            query=query,
            language=language,
            defaults={
                "outcome": outcome,
                "target": target,
                "note": str(request.data.get("note") or "").strip()[:300],
                "decided_by": actor_email(request),
                "decided_at": timezone.now(),
            },
        )
        clear_rules(language)
        return Response(
            {"ok": True, "query": query, "language": language, "outcome": outcome, "target": target},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        key = self._key(request.query_params)
        if key is None:
            return Response(
                {"detail": "query and language are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        query, language = key
        if refusal := self._guard_translate(request, query, language):
            return refusal
        deleted, _ = SearchDecision.objects.filter(query=query, language=language).delete()
        if not deleted:
            return Response({"detail": "No such decision to undo."}, status=status.HTTP_404_NOT_FOUND)
        clear_rules(language)
        return Response({"ok": True, "query": query, "language": language})


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSearchPreviewView(APIView):
    """What a search returns in one language — for the triage dialogs.

    The synonym dialog previews the word it would search instead; the pin
    dialog lists the pages a query already finds. Not the public endpoint, on
    purpose: that one logs every search, so previewing would put the admin's
    own lookups into the very report being triaged, and it applies the
    synonyms and pins being decided. This runs the bare search, unlogged.
    """

    def get(self, request):
        from ..search import search_library

        q = (request.query_params.get("q") or "").strip()
        language = (request.query_params.get("language") or "").strip().lower()
        if len(q) < MIN_QUERY_LEN or not language:
            return Response(
                {"detail": f"q ({MIN_QUERY_LEN}+ chars) and language are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"query": q, "results": search_library(q, language)})
