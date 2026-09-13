"""Admin dashboard API — reading & account analytics (engagement, users)."""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import Author, Book, SearchClickLog, Sermon
from ..views import _language_entry


class AdminEngagementView(APIView):
    """Reading-engagement analytics from ReadingProgress / ChapterMarks.

    Aggregate-only — counts and per-book/-language rollups, never individual
    readers' identities. "Active" is distinct profiles whose progress was
    touched within the window; "finishers" reached (or passed) the book's last
    English chapter.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone

        from reading.models import ChapterMarks, ReadingProgress

        now = timezone.now()

        def active(days, offset=0):
            """Distinct readers whose progress moved in a window ending ``offset``
            days ago. ``active(7)`` is the last 7 days; ``active(7, 7)`` is the 7
            days before that, so the page can show an honest week-over-week delta
            rather than a bare count."""
            qs = ReadingProgress.objects.filter(
                updated_at__gte=now - timedelta(days=days + offset)
            )
            if offset:
                qs = qs.filter(updated_at__lt=now - timedelta(days=offset))
            return qs.values("profile").distinct().count()

        overview = {
            "readers": ReadingProgress.objects.values("profile").distinct().count(),
            "progress_rows": ReadingProgress.objects.count(),
            "active_1d": active(1),
            "active_7d": active(7),
            "active_7d_prev": active(7, 7),
            "active_30d": active(30),
            "active_30d_prev": active(30, 30),
            "readers_with_marks": ChapterMarks.objects.exclude(marks=[])
            .values("profile")
            .distinct()
            .count(),
            "marked_chapters": ChapterMarks.objects.exclude(marks=[]).count(),
            "total_users": self._total_users(),
        }
        return Response(
            {
                "overview": overview,
                "time": self._reading_time(now),
                "most_read": self._most_read(),
                "most_marked": self._most_marked(),
                "by_language": self._by_language(),
                "weekly_active": self._weekly_active(now),
            }
        )

    def _reading_time(self, now):
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

        def window(days):
            return sessions.filter(
                last_seen_at__gte=now - timedelta(days=days)
            ).aggregate(secs=Sum("seconds"), readers=Count("profile", distinct=True))

        totals = sessions.aggregate(
            secs=Sum("seconds"),
            count=Count("id"),
            readers=Count("profile", distinct=True),
            avg=Avg("seconds"),
        )
        w7, w30 = window(7), window(30)
        return {
            "total_seconds": totals["secs"] or 0,
            "sessions": totals["count"] or 0,
            "readers": totals["readers"] or 0,
            "avg_session_seconds": round(totals["avg"] or 0),
            "seconds_7d": w7["secs"] or 0,
            "readers_7d": w7["readers"] or 0,
            "seconds_30d": w30["secs"] or 0,
            "readers_30d": w30["readers"] or 0,
        }

    def _total_users(self) -> int:
        from accounts.models import UserProfile

        return UserProfile.objects.count()

    def _work_meta(self) -> dict:
        """``(kind, slug)`` → ``(title, author)`` for every work a row can name.

        Keyed by kind as well as slug because ``ReadingProgress.book_slug`` names
        a book, a sermon OR an author biography (see ``WorkKind``), and those
        namespaces overlap: a sermon sharing a slug with a book used to be
        labelled with the BOOK's title and author.
        """
        meta: dict[tuple[str, str], tuple[str, str]] = {}
        for b in Book.objects.values("slug", "language", "title", "author__name"):
            key = ("book", b["slug"])
            if b["language"] == "en" or key not in meta:
                meta[key] = (b["title"], b["author__name"])
        for sm in Sermon.objects.values("slug", "language", "title", "author__name"):
            key = ("sermon", sm["slug"])
            if sm["language"] == "en" or key not in meta:
                meta[key] = (sm["title"], sm["author__name"])
        # A biography's slug names the AUTHOR, so the person is the title.
        for a in Author.objects.values("slug", "name"):
            meta[("bio", a["slug"])] = (a["name"], "")
        return meta

    def _row(self, meta, kind, slug, **extra) -> dict:
        title, author = meta.get((kind, slug), (slug, ""))
        return {"kind": kind, "slug": slug, "title": title, "author": author, **extra}

    def _most_read(self, limit: int = 10) -> list[dict]:
        from reading.models import ReadingProgress

        meta = self._work_meta()
        # Grouped by KIND as well as slug. Without it a sermon and a book sharing
        # a slug merged into one row wearing the book's title, and every sermon
        # reader was counted against that book.
        #
        # Finishers come from the stored `finished_at` stamp — the same explicit,
        # synced completion the reader's "Finished" shelf counts (reaching the end
        # of a work, or marking it done). Counting it as a conditional aggregate
        # in the SAME grouped query means one scan, not a COUNT per row; it counts
        # for EVERY kind (so a sermon or biography gets a real finisher number),
        # and the group's (kind, book_slug) keeps a sermon finish from counting
        # toward a book sharing its slug. This replaces the old "reached the last
        # chapter" guess, which was books-only and counted merely opening it.
        top = (
            ReadingProgress.objects.values("kind", "book_slug")
            .annotate(
                readers=Count("profile", distinct=True),
                finishers=Count(
                    "profile", filter=Q(finished_at__isnull=False), distinct=True
                ),
            )
            .order_by("-readers")[:limit]
        )
        return [
            self._row(
                meta,
                r["kind"],
                r["book_slug"],
                readers=r["readers"],
                finishers=r["finishers"],
            )
            for r in top
        ]

    def _most_marked(self, limit: int = 10) -> list[dict]:
        from reading.models import ChapterMarks

        meta = self._work_meta()
        top = (
            ChapterMarks.objects.exclude(marks=[])
            .values("kind", "book_slug")
            .annotate(readers=Count("profile", distinct=True), chapters=Count("id"))
            .order_by("-readers", "-chapters")[:limit]
        )
        return [
            self._row(
                meta,
                r["kind"],
                r["book_slug"],
                readers=r["readers"],
                chapters=r["chapters"],
            )
            for r in top
        ]

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

    def _weekly_active(self, now, weeks: int = 8) -> list[dict]:
        from datetime import timedelta

        from reading.models import ReadingProgress

        today = now.date()
        this_week = today - timedelta(days=today.weekday())  # Monday
        out = []
        for i in range(weeks - 1, -1, -1):
            start = this_week - timedelta(weeks=i)
            end = start + timedelta(weeks=1)
            readers = (
                ReadingProgress.objects.filter(
                    updated_at__date__gte=start, updated_at__date__lt=end
                )
                .values("profile")
                .distinct()
                .count()
            )
            out.append({"week": start.isoformat(), "readers": readers})
        return out


# Human labels for the reader themes stored on UserProfile.
THEME_LABELS = {"paper": "Paper (light)", "light": "Light", "dark": "Lamplight (dark)"}

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


# How many of the most recent sign-ups the admin page lists individually.
RECENT_SIGNUPS_LIMIT = 25


class AdminUsersView(APIView):
    """Account analytics: sign-up growth, locale/theme split, activation.

    Mostly aggregate over ``accounts.UserProfile`` (+ a distinct-reader count
    from ReadingProgress for activation). The ``recent`` list is the exception:
    it names individual accounts (display name, email, sign-in method) so the
    founder can see who is actually signing up — admin-only, behind
    ``IsAdminEmail``, and served to no one else.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

        from accounts.models import UserProfile
        from reading.models import ReadingProgress

        now = timezone.now()
        total = UserProfile.objects.count()
        with_activity = ReadingProgress.objects.values("profile").distinct().count()

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
                "signups_7d": signups_between(7),
                "signups_30d": signups_between(30),
                # The immediately preceding window, so the UI can show a trend
                # delta (this 7 days vs the 7 before it, this 30 vs the prior 30).
                "signups_prev_7d": signups_between(14, 7),
                "signups_prev_30d": signups_between(60, 30),
                "weekly_signups": self._weekly_signups(now),
                "by_method": self._by_method(),
                "recent": self._recent(),
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

    def _recent(self):
        """The most recent sign-ups, named — see the class docstring on why."""
        from accounts.models import UserProfile

        rows = UserProfile.objects.order_by("-created_at")[:RECENT_SIGNUPS_LIMIT]
        return [
            {
                # The stable handle the per-user detail page is keyed by.
                "uid": str(p.supabase_uid),
                "display_name": p.display_name,
                "email": p.email,
                # Labeled server-side (like ``by_method``) so the frontend needs
                # no copy of the provider→label map to keep in sync.
                "providers": [
                    {"code": c, "label": _provider_label(c)} for c in p.provider_list
                ],
                "locale": p.locale,
                "joined_at": p.created_at.isoformat(),
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
            }
            for p in rows
        ]

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
        from datetime import timedelta

        from accounts.models import UserProfile

        today = now.date()
        this_week = today - timedelta(days=today.weekday())  # Monday
        buckets = {}
        # One pass over sign-up dates, counted into their Monday-anchored week.
        for (created,) in UserProfile.objects.values_list("created_at"):
            wk = created.date() - timedelta(days=created.date().weekday())
            buckets[wk] = buckets.get(wk, 0) + 1
        out = []
        for i in range(weeks - 1, -1, -1):
            wk = this_week - timedelta(weeks=i)
            out.append({"week": wk.isoformat(), "count": buckets.get(wk, 0)})
        return out




class AdminSearchView(APIView):
    """Search analytics — what readers look for, and what they don't find.

    Aggregate-only, from the anonymous SearchQueryLog. Zero-result queries are
    the roadmap signal: each one is a reader asking for content or spelling
    tolerance we don't have yet. Top lists skip fragments under 3 characters
    (search-as-you-type prefixes) and fold case.

    Overview counts are searches SERVED, so type-ahead prefixes inflate them
    relative to typed intent (deliberate: 2-char queries are real searches in
    e.g. Chinese, and the engine did the work either way). Compare trends, not
    absolutes.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from datetime import timedelta

        from django.db.models.functions import Length, Lower, TruncDate
        from django.utils import timezone

        from ..models import SearchQueryLog

        now = timezone.now()
        window = SearchQueryLog.objects.filter(created_at__gte=now - timedelta(days=30))

        def overview(qs):
            counts = qs.aggregate(
                searches=Count("id"), zero=Count("id", filter=Q(result_count=0))
            )
            return {
                "searches": counts["searches"],
                "distinct_queries": qs.annotate(q=Lower("query"))
                .values("q")
                .distinct()
                .count(),
                "zero_results": counts["zero"],
                "zero_rate": round(counts["zero"] / counts["searches"], 3)
                if counts["searches"]
                else 0.0,
            }

        def top(qs, limit=20):
            rows = (
                qs.annotate(q=Lower("query"), qlen=Length("query"))
                .filter(qlen__gte=3)
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
        for r in (
            window.filter(result_count=0, language__in=list(per_language))
            .annotate(q=Lower("query"), qlen=Length("query"))
            .filter(qlen__gte=3)
            .values("language", "q")
            .annotate(count=Count("id"))
            .order_by("-count", "q")
        ):
            queries = per_language[r["language"]]
            if len(queries) < 10:
                queries.append({"query": r["q"], "count": r["count"]})

        unanswered = [
            {
                **_language_entry(r["language"]),
                "total": r["zero"],
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
            r["q"]: r["n"]
            for r in SearchClickLog.objects.filter(
                created_at__gte=now - timedelta(days=30)
            )
            .annotate(q=Lower("query"))
            .values("q")
            .annotate(n=Count("id"))
        }
        answered = top(window.filter(result_count__gt=0))
        unopened = [r for r in answered if not clicked.get(r["query"])][:10]

        return Response(
            {
                "overview": {
                    "7d": overview(
                        window.filter(created_at__gte=now - timedelta(days=7))
                    ),
                    "30d": overview(window),
                    # Whether search is answering at all, in one number. Rows,
                    # not readers — the logs are anonymous — so read it as a
                    # trend, not as "x% of people".
                    "clicks_30d": sum(clicked.values()),
                },
                "unopened_queries": unopened,
                "top_queries": answered,
                "zero_result_queries": top(window.filter(result_count=0)),
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


# A search hit reduced to the translatable WORK behind it, named the way the
# translation queue names it: a chapter is its book; an author is a bio job.
# type -> (job_type, slug field, title field) on the hit.
_GAP_WORK = {
    "book": ("book", "book_slug", "book_title"),
    "chapter": ("book", "book_slug", "book_title"),
    "sermon": ("sermon", "sermon_slug", "sermon_title"),
    "plan": ("plan", "plan_slug", "plan_title"),
    "author": ("bio", "author_slug", "author_name"),
    "topic": ("topic", "topic_slug", "topic_title"),
    "article": ("article", "article_slug", "article_title"),
}


def _gap_work(hit: dict) -> dict | None:
    """One search hit as a queueable work, or None for a hit that isn't one
    (a scripture navigational row, or anything missing a slug)."""
    spec = _GAP_WORK.get(hit.get("type"))
    if spec is None:
        return None
    job_type, slug_key, title_key = spec
    slug = hit.get(slug_key)
    if not slug:
        return None
    return {"type": job_type, "slug": slug, "title": hit.get(title_key) or slug}


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

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from ..languages import live_codes
        from ..search import MIN_QUERY_LEN, count_by_type, search_library

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
                work = _gap_work(hit)
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
