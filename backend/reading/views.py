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

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile

from .marks import clean_mark_list, from_legacy, merge_mark_lists
from .models import (
    ChapterMarks,
    Favorite,
    FavoriteKind,
    ReadingDay,
    ReadingProgress,
    WorkKind,
)
from .serializers import (
    ChapterMarksSerializer,
    FavoriteSerializer,
    ReadingProgressSerializer,
)


def _profile(request) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"supabase_uid": request.user.username, "email": request.user.email},
    )
    return profile


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

    def put(self, request, slug):
        profile = _profile(request)
        data = request.data
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

    def put(self, request, slug, order):
        profile = _profile(request)
        data = request.data
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

    def put(self, request, slug):
        profile = _profile(request)
        data = request.data
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

    def put(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        profile = _profile(request)
        obj, _ = Favorite.objects.get_or_create(
            profile=profile, kind=kind, slug=slug
        )
        return Response(FavoriteSerializer(obj).data)

    def delete(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        profile = _profile(request)
        Favorite.objects.filter(profile=profile, kind=kind, slug=slug).delete()
        return Response(status=204)


class ActivityView(APIView):
    """Record one day the reader read (the streak's activity log)."""

    permission_classes = [IsAuthenticated]

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

    def post(self, request):
        profile = _profile(request)
        self._merge_progress(profile, request.data.get("progress") or [])
        self._merge_marks(profile, request.data.get("marks") or [])
        self._merge_sermon_marks(profile, request.data.get("sermon_marks") or [])
        self._merge_favorites(profile, request.data.get("favorites") or [])
        self._merge_activity(profile, request.data.get("activity") or [])
        return Response(_serialize_state(profile))

    def _merge_activity(self, profile, incoming):
        """Union: a day read on either side counts (a streak is the union of
        active days across all the reader's devices). Malformed dates skipped."""
        for value in incoming:
            parsed = _parse_day(value)
            if parsed is not None:
                ReadingDay.objects.get_or_create(profile=profile, day=parsed)

    def _merge_favorites(self, profile, incoming):
        """Union: a heart set on either side survives (like marks, nothing a
        reader saved offline is ever dropped). Unknown kinds are skipped."""
        for row in incoming:
            kind = row.get("kind")
            slug = row.get("slug")
            if not slug or kind not in FavoriteKind.values:
                continue
            Favorite.objects.get_or_create(profile=profile, kind=kind, slug=slug)

    def _merge_progress(self, profile, incoming):
        existing = {(p.kind, p.book_slug): p for p in profile.progress.all()}
        for row in incoming:
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            if not slug or kind is None:
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
        existing = {
            (m.kind, m.book_slug, m.chapter_order): m for m in profile.marks.all()
        }
        for row in incoming:
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            order = _clamp_int(row.get("chapter_order"), default=-1, low=0)
            if not slug or kind is None or order < 0:
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
        fold them into ChapterMarks(kind="sermon") so nothing is dropped."""
        for row in incoming:
            slug = row.get("sermon_slug")
            if not slug:
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
        # Activity log (the streak): just the set of days, newest first.
        "activity": [d.day.isoformat() for d in profile.reading_days.all()],
        # COMPAT: old bundles rehydrate their sermon store from this field.
        "sermon_marks": [
            _legacy_sermon_shape(m)
            for m in profile.marks.filter(kind=WorkKind.SERMON)
        ],
    }
