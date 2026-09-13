"""Admin dashboard API — one reader's profile and activity.

The per-identity companion to the aggregate :class:`AdminUsersView`. Where that
page never names an individual beyond the recent-sign-ups list, this one is
entirely about a single account: who they are, what they're reading, what they
saved, how consistently they show up. Admin-only (``IsAdminEmail``), keyed by
the Supabase UUID so the URL leaks neither the Django pk nor the email.

Everything here is *derived on request* from the reading tables (there is no
per-user rollup) — cheap because it is scoped to one profile. No time-on-site or
session data exists anywhere in the app, so the finest activity signal is the
day-level ``ReadingDay`` (the streak/calendar) plus ``last_seen_at``.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..views import _language_entry
from .analytics import THEME_LABELS, _provider_label

# How many rows each capped list returns; the timeline merges several of these.
LIST_LIMIT = 50
TIMELINE_LIMIT = 40


def _iso(dt):
    return dt.isoformat() if dt else None


def _reader_today(tz_name):
    """The reader's *local* calendar date.

    ``ReadingDay`` stores reader-local dates and a streak is a wall-clock notion
    (see the model), so "today" must be judged in the reader's own zone — the
    server's UTC date can be a day ahead near their midnight and break a live
    streak. Falls back to the server date when the zone is blank or unknown.
    """
    from django.utils import timezone

    now = timezone.now()
    if tz_name:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            return now.astimezone(ZoneInfo(tz_name)).date()
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return now.date()


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


def _work_titles(pairs):
    """``(kind, slug)`` → ``(title, author)`` for reading rows.

    ``kind`` is a :class:`reading.models.WorkKind` (book / sermon / bio); the
    slug names a book, a sermon, or — for a bio — the author themselves.

    Mirrors :meth:`AdminEngagementView._work_meta`, including keying by kind so a
    sermon and a book that share a slug don't collide (the bug that method's
    docstring documents at length). Kept separate rather than shared because
    ``_work_meta`` scans the whole table for the aggregate dashboard, while this
    filters ``slug__in`` to one reader's works.
    """
    from ..models import Author, Book, Sermon

    book_slugs = [s for k, s in pairs if k == "book"]
    sermon_slugs = [s for k, s in pairs if k == "sermon"]
    bio_slugs = [s for k, s in pairs if k == "bio"]

    def title_author(r):
        return (r["title"], r.get("author__name") or "")

    meta: dict[tuple[str, str], tuple[str, str]] = {}
    if book_slugs:
        rows = Book.objects.filter(slug__in=book_slugs).values(
            "slug", "language", "title", "author__name"
        )
        meta.update({("book", s): v for s, v in _prefer_en(rows, title_author).items()})
    if sermon_slugs:
        rows = Sermon.objects.filter(slug__in=sermon_slugs).values(
            "slug", "language", "title", "author__name"
        )
        meta.update({("sermon", s): v for s, v in _prefer_en(rows, title_author).items()})
    if bio_slugs:
        for a in Author.objects.filter(slug__in=bio_slugs).values("slug", "name"):
            meta[("bio", a["slug"])] = (a["name"], "")
    return meta


def _favorite_labels(pairs):
    """``(kind, slug)`` → display label for the seven favoritable kinds.

    Best-effort: a favorite outlives the thing it points at (slug-referenced, so
    it survives re-imports), and a quote's slug is an opaque address, so an
    unresolved favorite falls back to its slug rather than vanishing.
    """
    from ..models import Article, Author, Book, Plan, Sermon, Topic

    by_kind: dict[str, list[str]] = {}
    for k, s in pairs:
        by_kind.setdefault(k, []).append(s)

    labels: dict[tuple[str, str], str] = {}

    def add(kind, rows, field):
        for slug, val in _prefer_en(rows, lambda r: r[field]).items():
            labels[(kind, slug)] = val

    if by_kind.get("book"):
        add("book", Book.objects.filter(slug__in=by_kind["book"]).values("slug", "language", "title"), "title")
    if by_kind.get("sermon"):
        add("sermon", Sermon.objects.filter(slug__in=by_kind["sermon"]).values("slug", "language", "title"), "title")
    if by_kind.get("plan"):
        add("plan", Plan.objects.filter(slug__in=by_kind["plan"]).values("slug", "language", "title"), "title")
    if by_kind.get("article"):
        add("article", Article.objects.filter(slug__in=by_kind["article"]).values("slug", "language", "h1"), "h1")
    if by_kind.get("topic"):
        for t in Topic.objects.filter(slug__in=by_kind["topic"]).values("slug", "title"):
            labels[("topic", t["slug"])] = t["title"]
    if by_kind.get("author"):
        for a in Author.objects.filter(slug__in=by_kind["author"]).values("slug", "name"):
            labels[("author", a["slug"])] = a["name"]
    # Quotes keep their opaque slug — no title row to resolve to.
    return labels


class AdminUserDetailView(APIView):
    """One reader: profile, reading, favorites, plans, streak, and a timeline.

    Keyed by ``supabase_uid``. Returns 404 for an unknown id. Read-only — a
    place to understand an account, not to act on it (any admin action on a user
    is a separate, audited endpoint).
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, uid):
        from accounts.geo import country_for_timezone, country_name
        from accounts.models import UserProfile
        from reading.streaks import reading_streaks

        profile = UserProfile.objects.filter(supabase_uid=uid).first()
        if profile is None:
            return Response({"detail": "No such user."}, status=404)

        # --- Reading progress (in-progress vs finished) ----------------------
        progress = list(profile.progress.all())
        work_pairs = {(p.kind, p.book_slug) for p in progress}

        # --- Favorites -------------------------------------------------------
        favorites = list(profile.favorites.all())
        fav_pairs = {(f.kind, f.slug) for f in favorites}

        # --- Marks (highlights + notes) and bookmarks ------------------------
        marks = [m for m in profile.marks.all() if m.marks]
        bookmarks = list(profile.bookmarks.all())
        work_pairs |= {(m.kind, m.book_slug) for m in marks}
        work_pairs |= {(b.kind, b.book_slug) for b in bookmarks}

        titles = _work_titles(work_pairs)
        fav_labels = _favorite_labels(fav_pairs)

        def work_title(kind, slug):
            return titles.get((kind, slug), (slug, ""))

        def progress_row(p):
            title, author = work_title(p.kind, p.book_slug)
            return {
                "kind": p.kind,
                "slug": p.book_slug,
                "language": p.language,
                "title": title,
                "author": author,
                "chapter_order": p.chapter_order,
                "paragraph_index": p.paragraph_index,
                "updated_at": _iso(p.updated_at),
                "finished_at": _iso(p.finished_at),
            }

        in_progress = sorted(
            (progress_row(p) for p in progress if p.finished_at is None),
            key=lambda r: r["updated_at"] or "",
            reverse=True,
        )
        finished = sorted(
            (progress_row(p) for p in progress if p.finished_at is not None),
            key=lambda r: r["finished_at"] or "",
            reverse=True,
        )

        # --- Reading days → streak + calendar --------------------------------
        days = [d.day for d in profile.reading_days.all()]
        local_today = _reader_today(profile.timezone)
        current_streak, longest_streak = reading_streaks(days, today=local_today)
        sorted_days = sorted(days)

        # --- Plans (title + day-count in one annotated query) ----------------
        plan_progress = list(profile.plan_progress.all())
        plan_meta = self._plan_meta([pp.plan_slug for pp in plan_progress])
        plans = []
        for pp in plan_progress:
            title, total = plan_meta.get(pp.plan_slug, (pp.plan_slug, None))
            done = len(pp.done or [])
            plans.append(
                {
                    "slug": pp.plan_slug,
                    "title": title,
                    "started_at": _iso(pp.started_at),
                    "updated_at": _iso(pp.updated_at),
                    "done": done,
                    "total_days": total,
                    "pct": round(done / total * 100) if total else None,
                }
            )
        plans.sort(key=lambda r: r["updated_at"] or "", reverse=True)

        # --- Highlights / notes ---------------------------------------------
        highlight_rows = []
        for m in marks:
            title, _ = work_title(m.kind, m.book_slug)
            items = [
                {
                    "text": (mk.get("text") or "").strip()[:300],
                    "note": (mk.get("note") or "").strip()[:500],
                }
                for mk in (m.marks or [])
            ]
            highlight_rows.append(
                {
                    "kind": m.kind,
                    "slug": m.book_slug,
                    "language": m.language,
                    "title": title,
                    "chapter_order": m.chapter_order,
                    "count": len(items),
                    "marks": items,
                    "updated_at": _iso(m.updated_at),
                }
            )
        highlight_rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
        total_marks = sum(r["count"] for r in highlight_rows)

        # --- Bookmarks -------------------------------------------------------
        bookmark_rows = []
        for b in bookmarks:
            title, _ = work_title(b.kind, b.book_slug)
            bookmark_rows.append(
                {
                    "kind": b.kind,
                    "slug": b.book_slug,
                    "title": title,
                    "chapter_order": b.chapter_order,
                    "paragraph_index": b.paragraph_index,
                    "snippet": b.snippet,
                    "label": b.title,
                    "created_at": _iso(b.created_at),
                }
            )
        bookmark_rows.sort(key=lambda r: r["created_at"] or "", reverse=True)

        # --- Favorites (labelled) -------------------------------------------
        favorite_rows = [
            {
                "kind": f.kind,
                "slug": f.slug,
                "label": fav_labels.get((f.kind, f.slug), f.slug),
                "created_at": _iso(f.created_at),
            }
            for f in sorted(favorites, key=lambda f: f.created_at, reverse=True)
        ]

        # --- Timeline: one merged, reverse-chron stream ---------------------
        timeline = self._timeline(
            progress, favorites, bookmarks, marks, plan_progress, work_title, fav_labels, plan_meta
        )

        country = country_for_timezone(profile.timezone or "")

        return Response(
            {
                "profile": {
                    "uid": str(profile.supabase_uid),
                    "display_name": profile.display_name,
                    "email": profile.email,
                    "providers": [
                        {"code": c, "label": _provider_label(c)}
                        for c in profile.provider_list
                    ],
                    "locale": profile.locale,
                    "locale_name": _language_entry(profile.locale)["name"],
                    "theme": profile.theme,
                    "theme_label": THEME_LABELS.get(profile.theme, profile.theme),
                    "font_scale": profile.font_scale,
                    "joined_at": _iso(profile.created_at),
                    "last_seen_at": _iso(profile.last_seen_at),
                    "timezone": profile.timezone,
                    "country": {"code": country, "name": country_name(country)}
                    if country
                    else None,
                },
                "stats": {
                    "works_started": len(progress),
                    "works_finished": len(finished),
                    "books": sum(1 for p in progress if p.kind == "book"),
                    "sermons": sum(1 for p in progress if p.kind == "sermon"),
                    "bios": sum(1 for p in progress if p.kind == "bio"),
                    "favorites": len(favorites),
                    "highlights": total_marks,
                    "bookmarks": len(bookmarks),
                    "plans": len(plans),
                    "days_read": len(days),
                    "streak_current": current_streak,
                    "streak_longest": longest_streak,
                },
                "reading": {
                    "in_progress": in_progress[:LIST_LIMIT],
                    "finished": finished[:LIST_LIMIT],
                    "last_read": in_progress[0] if in_progress else (finished[0] if finished else None),
                },
                "favorites": favorite_rows[:LIST_LIMIT],
                "plans": plans,
                "highlights": highlight_rows[:LIST_LIMIT],
                "bookmarks": bookmark_rows[:LIST_LIMIT],
                "activity": {
                    "days": [d.isoformat() for d in sorted_days],
                    "first": sorted_days[0].isoformat() if sorted_days else None,
                    "last": sorted_days[-1].isoformat() if sorted_days else None,
                    # The reader's own local "today", so the heatmap aligns its
                    # grid to the same day the streak was judged against.
                    "today": local_today.isoformat(),
                },
                "timeline": timeline[:TIMELINE_LIMIT],
            }
        )

    def _plan_meta(self, slugs):
        """``plan_slug`` → ``(title, day_count)``, one annotated query, en first."""
        from django.db.models import Count

        from ..models import Plan

        if not slugs:
            return {}
        meta: dict[str, tuple[str, int]] = {}
        for r in (
            Plan.objects.filter(slug__in=slugs)
            .values("slug", "language", "title")
            .annotate(n=Count("days"))
        ):
            if r["language"] == "en" or r["slug"] not in meta:
                meta[r["slug"]] = (r["title"], r["n"])
        return meta

    def _timeline(
        self, progress, favorites, bookmarks, marks, plan_progress, work_title, fav_labels, plan_meta
    ):
        """Merge every dated per-user event into one reverse-chron list.

        Each event carries a machine ``type`` and the identifiers the frontend
        needs to render a label and (where it makes sense) a link; the copy is
        the frontend's. Timestamps are compared as ISO strings, which sort
        correctly because they are all timezone-aware ISO-8601.
        """
        events = []

        for p in progress:
            title, _ = work_title(p.kind, p.book_slug)
            if p.finished_at:
                events.append(
                    {
                        "type": "finished",
                        "at": _iso(p.finished_at),
                        "kind": p.kind,
                        "slug": p.book_slug,
                        "language": p.language,
                        "title": title,
                    }
                )
            events.append(
                {
                    "type": "read",
                    "at": _iso(p.updated_at),
                    "kind": p.kind,
                    "slug": p.book_slug,
                    "language": p.language,
                    "title": title,
                    "chapter_order": p.chapter_order,
                }
            )
        for f in favorites:
            events.append(
                {
                    "type": "favorite",
                    "at": _iso(f.created_at),
                    "kind": f.kind,
                    "slug": f.slug,
                    "title": fav_labels.get((f.kind, f.slug), f.slug),
                }
            )
        for b in bookmarks:
            title, _ = work_title(b.kind, b.book_slug)
            events.append(
                {
                    "type": "bookmark",
                    "at": _iso(b.created_at),
                    "kind": b.kind,
                    "slug": b.book_slug,
                    "title": title,
                    "chapter_order": b.chapter_order,
                    "snippet": b.snippet,
                }
            )
        for m in marks:
            title, _ = work_title(m.kind, m.book_slug)
            events.append(
                {
                    "type": "highlight",
                    "at": _iso(m.updated_at),
                    "kind": m.kind,
                    "slug": m.book_slug,
                    "title": title,
                    "chapter_order": m.chapter_order,
                    "count": len(m.marks or []),
                }
            )
        for pp in plan_progress:
            title, _ = plan_meta.get(pp.plan_slug, (pp.plan_slug, None))
            events.append(
                {
                    "type": "plan_started",
                    "at": _iso(pp.started_at),
                    "kind": "plan",
                    "slug": pp.plan_slug,
                    "title": title,
                }
            )

        events = [e for e in events if e["at"]]
        events.sort(key=lambda e: e["at"], reverse=True)
        return events
