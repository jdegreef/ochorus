"""Authenticated API for a reader's own progress, highlights and notes.

Every endpoint requires a signed-in user and operates only on that user's rows
(scoped by their :class:`accounts.UserProfile`). The frontend mirrors the same
data in localStorage; these views are the synced source of truth. On first
sign-in the client POSTs its local state to :class:`MergeView`, which unions it
with anything already on the server (so nothing a reader did offline is lost) and
returns the merged whole.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from accounts.models import UserProfile

from .marks import clean_mark_list, from_legacy, merge_mark_lists
from .models import (
    ChapterMarks,
    Favorite,
    FavoriteKind,
    PlanProgress,
    ReadingDay,
    ReadingProgress,
    WorkKind,
)
from .serializers import (
    ChapterMarksSerializer,
    FavoriteSerializer,
    PlanProgressSerializer,
    ReadingProgressSerializer,
)


def _profile(request) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"supabase_uid": request.user.username, "email": request.user.email},
    )
    return profile


# Upper bound on days accepted in one activity merge — generous (well over a
# decade of daily reading) but finite, so an oversized bundle can't fan out.
MAX_ACTIVITY_MERGE = 6000

# Per-list cap on any other merge section (progress, marks, favorites, sermon
# marks, plan progress). Generous — no honest reader has 2,000 books, favorites,
# or annotated chapters — but finite, so even after the per-row guards a single
# oversized bundle can't fan the merge out into an unbounded number of writes.
MAX_MERGE_ROWS = 2000

# Slugs come from the URL (<slug:…>, unbounded) and from JSON payloads; the DB
# columns are SlugField(max_length=160). An over-long slug is a Postgres
# DataError (a 500) on write — reject/skip it. Chapter orders are 1-based; the
# ceiling stops an out-of-range int from becoming a PositiveInteger DataError.
SLUG_MAX = 160
MAX_CHAPTER_ORDER = 100_000


class _ReadingWriteThrottle(UserRateThrottle):
    """Bounds how fast one signed-in account can mutate its reading state.

    These endpoints are ``IsAuthenticated``, so this caps a single account
    (keyed by user id); combined with the per-list merge caps it stops a scripted
    or compromised account from amplifying sync into unbounded DB writes.
    Generous enough that real highlight/scroll bursts never hit it — a bound, not
    access control (per-worker local-memory cache, like the search-click one)."""

    scope = "reading"


def _valid_slug(slug) -> bool:
    """A non-empty slug that fits the SlugField columns (varchar(160))."""
    return isinstance(slug, str) and 0 < len(slug) <= SLUG_MAX


def _valid_order(value) -> int | None:
    """A parsed 1-based chapter order within bounds, or None. Chapters are
    1-based, so 0/negative is junk, and the ceiling keeps an out-of-range int
    from reaching the DB as a DataError."""
    try:
        order = int(value)
    except (TypeError, ValueError):
        return None
    return order if 1 <= order <= MAX_CHAPTER_ORDER else None


def _parse_day(value) -> date | None:
    """A 'YYYY-MM-DD' string → a date, or None if malformed."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _clamp_int(value, default=0, low=0) -> int:
    try:
        return max(low, int(value))
    except (TypeError, ValueError):
        return default


def _as_dict(data) -> dict:
    """A request body coerced to a dict — a JSON array/scalar body (a stale or
    buggy client shape) becomes ``{}`` instead of 500ing on ``.get``. Only safe
    where an empty body is a harmless no-op (the merge, whose sections then
    default to ``[]``); see ``_dict_body`` for the mutating single-resource PUTs.
    """
    return data if isinstance(data, dict) else {}


def _dict_body(request) -> dict:
    """The PUT body as a dict, or a 400. A malformed (array/scalar) body must be
    *rejected*, not coerced to ``{}``: for marks an empty body means "delete this
    chapter's marks" and for progress it means "write default position", so
    coercing would turn a garbage request into silent data loss (a wiped
    highlight, a reset reading position) instead of a clean error."""
    if isinstance(request.data, dict):
        return request.data
    raise ValidationError("Expected a JSON object.")


# Generous upper bound on a plan's day number — well beyond any real plan
# (the longest today is ~36 days), so it never drops a legitimate completion,
# while still bounding the accepted set so a malformed payload can't store an
# unbounded list.
MAX_PLAN_DAYS = 1000


def _clean_done(value) -> set[int]:
    """A client 'done days' payload → a set of valid 1-based day numbers."""
    if not isinstance(value, list):
        return set()
    days = set()
    for v in value:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= MAX_PLAN_DAYS:
            days.add(n)
    return days


def _upsert_plan_progress(profile, slug, done, started):
    """Merge one plan's progress into the reader's row and return it.

    ``done`` UNIONS with whatever the row already has and ``started`` takes the
    EARLIEST — the same lossless reconciliation whether the write comes from a
    live PUT or the sign-in merge, so a completion earned on any device is never
    lost. (The tradeoff: un-marking a day is therefore device-local and may not
    propagate — deliberately, since silently losing a day a reader completed is
    far worse than an un-check that doesn't sync.)

    The read-union-write runs inside a transaction with the existing row locked
    (``select_for_update``): without it, two devices PUTting at once can both read
    the same old ``done`` and the second write clobbers the first's union — losing
    a completed day, the exact thing this function promises never happens. On
    SQLite the lock is a no-op (single-writer already); on Postgres it serializes
    the two writers. Nested inside MergeView's atomic block it's just a savepoint.
    """
    with transaction.atomic():
        existing = (
            PlanProgress.objects.select_for_update()
            .filter(profile=profile, plan_slug=slug)
            .first()
        )
        if existing:
            done = set(done) | set(existing.done)
            started = min(started, existing.started_at)
        obj, _ = PlanProgress.objects.update_or_create(
            profile=profile,
            plan_slug=slug,
            defaults={"started_at": started, "done": sorted(done)},
        )
    return obj


def _ms_to_dt(ms) -> datetime | None:
    """Interpret a client `updated_at` (epoch milliseconds) as an aware datetime."""
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _kind_or_none(value) -> str | None:
    """A valid WorkKind, defaulting to book when absent; None when invalid.

    Absent means an older client that predates sermons in the reading layer —
    its rows are book rows. An *unknown* value is a newer client than this
    server; misfiling that data under "book" would corrupt it, so callers
    reject (PUT) or skip (merge) instead.
    """
    if value in (None, ""):
        return WorkKind.BOOK
    return value if value in WorkKind.values else None


def _marks_from_payload(data) -> list[dict]:
    """Marks from a client payload — range shape, or converted legacy h/n."""
    if isinstance(data.get("marks"), list):
        return clean_mark_list(data["marks"])
    return from_legacy(data.get("highlights"), data.get("notes"))


class StateView(APIView):
    """The reader's entire synced state — every progress row and chapter's marks.

    Used to hydrate the client on sign-in and to power the "Continue reading"
    lists. Small by construction (a handful of books per reader).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _profile(request)
        return Response(_serialize_state(profile))


class ProgressView(APIView):
    """Upsert the reader's position in one book."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, slug):
        profile = _profile(request)
        data = _dict_body(request)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        kind = _kind_or_none(request.query_params.get("kind") or data.get("kind"))
        if kind is None:
            return Response({"detail": "Unknown kind."}, status=400)
        obj, _ = ReadingProgress.objects.update_or_create(
            profile=profile,
            kind=kind,
            book_slug=slug,
            defaults={
                "language": (data.get("language") or "en")[:10],
                "chapter_order": _clamp_int(data.get("chapter_order"), default=1, low=1),
                "paragraph_index": _clamp_int(data.get("paragraph_index"), default=0),
            },
        )
        return Response(ReadingProgressSerializer(obj).data)


class MarksView(APIView):
    """Replace the reader's marks for one chapter (empty payload deletes them)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, slug, order):
        profile = _profile(request)
        data = _dict_body(request)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        if _valid_order(order) is None:
            return Response({"detail": "Invalid chapter order."}, status=400)
        kind = _kind_or_none(request.query_params.get("kind") or data.get("kind"))
        if kind is None:
            return Response({"detail": "Unknown kind."}, status=400)
        marks = _marks_from_payload(data)

        if not marks:
            ChapterMarks.objects.filter(
                profile=profile, kind=kind, book_slug=slug, chapter_order=order
            ).delete()
            return Response({"marks": []})

        obj, _ = ChapterMarks.objects.update_or_create(
            profile=profile,
            kind=kind,
            book_slug=slug,
            chapter_order=order,
            defaults={
                "language": (data.get("language") or "en")[:10],
                "marks": marks,
                "highlights": [],
                "notes": {},
            },
        )
        return Response(ChapterMarksSerializer(obj).data)


class SermonMarksView(APIView):
    """COMPAT SHIM for pre-unification clients (PR #293's deployed bundle).

    Sermon marks now live in ChapterMarks(kind="sermon", chapter_order=1);
    this keeps the old URL and payload shape working for stale PWA bundles so
    their pushes keep syncing until they pick up the new build. Retire once
    old bundles have aged out.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, slug):
        profile = _profile(request)
        data = _dict_body(request)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        marks = _marks_from_payload(data)

        if not marks:
            ChapterMarks.objects.filter(
                profile=profile, kind=WorkKind.SERMON, book_slug=slug, chapter_order=1
            ).delete()
            return Response({"marks": []})

        obj, _ = ChapterMarks.objects.update_or_create(
            profile=profile,
            kind=WorkKind.SERMON,
            book_slug=slug,
            chapter_order=1,
            defaults={
                "language": (data.get("language") or "en")[:10],
                "marks": marks,
                "highlights": [],
                "notes": {},
            },
        )
        return Response(_legacy_sermon_shape(obj))


class FavoriteView(APIView):
    """Save / unsave one favorite (an author, book, plan or sermon)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        profile = _profile(request)
        obj, _ = Favorite.objects.get_or_create(
            profile=profile, kind=kind, slug=slug
        )
        return Response(FavoriteSerializer(obj).data)

    def delete(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        profile = _profile(request)
        Favorite.objects.filter(profile=profile, kind=kind, slug=slug).delete()
        return Response(status=204)


class PlanProgressView(APIView):
    """Upsert the reader's progress in one reading plan.

    Completed days UNION with the server's set and the earliest start wins (see
    ``_upsert_plan_progress``), so a day finished on any device is never lost —
    even when two devices are signed in at once and neither has re-synced. The
    cost is that un-marking a day is device-local; that's the right tradeoff for
    a progress log.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, slug):
        profile = _profile(request)
        data = _dict_body(request)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        started = _ms_to_dt(data.get("started_at")) or datetime.now(timezone.utc)
        obj = _upsert_plan_progress(
            profile, slug, _clean_done(data.get("done")), started
        )
        return Response(PlanProgressSerializer(obj).data)


class ActivityView(APIView):
    """Record one day the reader read (the streak's activity log)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, day):
        parsed = _parse_day(day)
        if parsed is None:
            return Response({"detail": "Bad date."}, status=400)
        profile = _profile(request)
        ReadingDay.objects.get_or_create(profile=profile, day=parsed)
        return Response({"day": parsed.isoformat()})


class MergeView(APIView):
    """First-sign-in reconciliation of local (offline) state with the server.

    Progress conflicts resolve by recency (the client sends `updated_at` in epoch
    ms); marks are *unioned* so no highlight or note is ever dropped — on a note
    collision the longer text wins. Returns the merged whole for the client to
    write back over its localStorage cache.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def post(self, request):
        profile = _profile(request)
        # A JSON array/scalar body (a stale client shape) must not 500 the whole
        # sign-in reconciliation; each helper also guards its own section.
        data = _as_dict(request.data)
        # All six phases are one transaction: a failure in a later phase (or a
        # DB error mid-write) must not leave the account half-reconciled — the
        # client writes the returned state back over localStorage, so a partial
        # merge would silently diverge local and server.
        with transaction.atomic():
            self._merge_progress(profile, data.get("progress") or [])
            self._merge_marks(profile, data.get("marks") or [])
            self._merge_sermon_marks(profile, data.get("sermon_marks") or [])
            self._merge_favorites(profile, data.get("favorites") or [])
            self._merge_activity(profile, data.get("activity") or [])
            self._merge_plan_progress(profile, data.get("plan_progress") or [])
        return Response(_serialize_state(profile))

    def _merge_plan_progress(self, profile, incoming):
        """Union done days + earliest start (same rule as a live PUT — see
        ``_upsert_plan_progress``). A non-list is ignored, matching the activity
        merge, so a malformed bundle can't 500 the whole sign-in reconciliation."""
        if not isinstance(incoming, list):
            return
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("plan_slug")
            if not _valid_slug(slug):
                continue
            started = _ms_to_dt(row.get("started_at")) or datetime.now(timezone.utc)
            _upsert_plan_progress(profile, slug, _clean_done(row.get("done")), started)

    def _merge_activity(self, profile, incoming):
        """Union: a day read on either side counts (a streak is the union of
        active days across all the reader's devices). Malformed dates skipped;
        a non-list is ignored, and the batch is capped so a malformed or
        oversized bundle can't fan out into an unbounded number of writes
        (MAX_ACTIVITY_MERGE ≈ years of daily reading — no honest client hits it)."""
        if not isinstance(incoming, list):
            return
        days = {
            parsed
            for value in incoming[:MAX_ACTIVITY_MERGE]
            if (parsed := _parse_day(value)) is not None
        }
        # One INSERT ... ON CONFLICT DO NOTHING instead of a get_or_create per
        # day: the unique (profile, day) constraint skips days already recorded.
        ReadingDay.objects.bulk_create(
            [ReadingDay(profile=profile, day=d) for d in days],
            ignore_conflicts=True,
        )

    def _merge_favorites(self, profile, incoming):
        """Union: a heart set on either side survives (like marks, nothing a
        reader saved offline is ever dropped). Unknown kinds are skipped; a
        non-list is ignored and non-dict rows skipped, so a malformed bundle
        can't 500 the sign-in reconciliation."""
        if not isinstance(incoming, list):
            return
        favorites = {}
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            kind = row.get("kind")
            slug = row.get("slug")
            if not _valid_slug(slug) or kind not in FavoriteKind.values:
                continue
            favorites[(kind, slug)] = Favorite(profile=profile, kind=kind, slug=slug)
        # One INSERT ... ON CONFLICT DO NOTHING: the unique (profile, kind, slug)
        # constraint skips hearts already saved.
        Favorite.objects.bulk_create(list(favorites.values()), ignore_conflicts=True)

    def _merge_progress(self, profile, incoming):
        if not isinstance(incoming, list):
            return
        existing = {(p.kind, p.book_slug): p for p in profile.progress.all()}
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            if not _valid_slug(slug) or kind is None:
                continue
            local_dt = _ms_to_dt(row.get("updated_at"))
            server = existing.get((kind, slug))
            # Keep the server row unless the local one is strictly newer.
            if server and local_dt and server.updated_at >= local_dt:
                continue
            ReadingProgress.objects.update_or_create(
                profile=profile,
                kind=kind,
                book_slug=slug,
                defaults={
                    "language": (row.get("language") or "en")[:10],
                    "chapter_order": _clamp_int(row.get("chapter_order"), default=1, low=1),
                    "paragraph_index": _clamp_int(row.get("paragraph_index"), default=0),
                },
            )

    def _merge_marks(self, profile, incoming):
        if not isinstance(incoming, list):
            return
        existing = {
            (m.kind, m.book_slug, m.chapter_order): m for m in profile.marks.all()
        }
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            order = _valid_order(row.get("chapter_order"))
            # A parseable negative (e.g. -5) used to clamp to 0 and get stored as
            # a junk chapter-0 row; require a real 1-based order instead.
            if not _valid_slug(slug) or kind is None or order is None:
                continue
            marks = _marks_from_payload(row)
            server = existing.get((kind, slug, order))
            if server:
                # A pre-conversion server row folds its legacy fields in too.
                server_marks = server.marks or from_legacy(
                    server.highlights, server.notes
                )
                marks = merge_mark_lists(server_marks, marks)
            if not marks:
                continue
            ChapterMarks.objects.update_or_create(
                profile=profile,
                kind=kind,
                book_slug=slug,
                chapter_order=order,
                defaults={
                    "language": (row.get("language") or "en")[:10],
                    "marks": marks,
                    "highlights": [],
                    "notes": {},
                },
            )

    def _merge_sermon_marks(self, profile, incoming):
        """COMPAT: old bundles send sermon marks in their own payload field —
        fold them into ChapterMarks(kind="sermon") so nothing is dropped. A
        non-list is ignored and non-dict rows skipped."""
        if not isinstance(incoming, list):
            return
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("sermon_slug")
            if not _valid_slug(slug):
                continue
            marks = _marks_from_payload(row)
            server = ChapterMarks.objects.filter(
                profile=profile, kind=WorkKind.SERMON, book_slug=slug, chapter_order=1
            ).first()
            if server:
                marks = merge_mark_lists(server.marks or [], marks)
            if not marks:
                continue
            ChapterMarks.objects.update_or_create(
                profile=profile,
                kind=WorkKind.SERMON,
                book_slug=slug,
                chapter_order=1,
                defaults={
                    "language": (row.get("language") or "en")[:10],
                    "marks": marks,
                    "highlights": [],
                    "notes": {},
                },
            )


def _legacy_sermon_shape(m) -> dict:
    """A ChapterMarks sermon row in the old SermonMarks response shape."""
    return {
        "sermon_slug": m.book_slug,
        "language": m.language,
        "marks": m.marks,
        "updated_at": m.updated_at,
    }


def _serialize_state(profile) -> dict:
    return {
        "progress": ReadingProgressSerializer(
            profile.progress.all(), many=True
        ).data,
        "marks": ChapterMarksSerializer(profile.marks.all(), many=True).data,
        "favorites": FavoriteSerializer(profile.favorites.all(), many=True).data,
        "plan_progress": PlanProgressSerializer(
            profile.plan_progress.all(), many=True
        ).data,
        # Activity log (the streak): just the set of days, newest first.
        "activity": [d.day.isoformat() for d in profile.reading_days.all()],
        # COMPAT: old bundles rehydrate their sermon store from this field.
        "sermon_marks": [
            _legacy_sermon_shape(m)
            for m in profile.marks.filter(kind=WorkKind.SERMON)
        ],
    }
