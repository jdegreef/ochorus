"""Authenticated API for a reader's own progress, highlights and notes.

Every endpoint requires a signed-in user and operates only on that user's rows
(scoped by their :class:`accounts.UserProfile`). The frontend mirrors the same
data in localStorage; these views are the synced source of truth. On first
sign-in the client POSTs its local state to :class:`MergeView`, which unions it
with anything already on the server (so nothing a reader did offline is lost) and
returns the merged whole.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile

from .models import ChapterMarks, ReadingProgress
from .serializers import ChapterMarksSerializer, ReadingProgressSerializer


def _profile(request) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"supabase_uid": request.user.username, "email": request.user.email},
    )
    return profile


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


def _clean_marks(highlights, notes) -> tuple[list[int], dict[str, str]]:
    """Coerce arbitrary client input into a safe (highlights, notes) pair."""
    clean_h = sorted(
        {i for i in (_clamp_int(x, default=-1, low=0) for x in highlights or []) if i >= 0}
    )
    clean_n: dict[str, str] = {}
    if isinstance(notes, dict):
        for k, v in notes.items():
            idx = _clamp_int(k, default=-1, low=0)
            if idx >= 0 and isinstance(v, str) and v.strip():
                clean_n[str(idx)] = v.strip()
    return clean_h, clean_n


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
        obj, _ = ReadingProgress.objects.update_or_create(
            profile=profile,
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
        highlights, notes = _clean_marks(data.get("highlights"), data.get("notes"))

        if not highlights and not notes:
            ChapterMarks.objects.filter(
                profile=profile, book_slug=slug, chapter_order=order
            ).delete()
            return Response({"highlights": [], "notes": {}})

        obj, _ = ChapterMarks.objects.update_or_create(
            profile=profile,
            book_slug=slug,
            chapter_order=order,
            defaults={
                "language": (data.get("language") or "en")[:10],
                "highlights": highlights,
                "notes": notes,
            },
        )
        return Response(ChapterMarksSerializer(obj).data)


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
        return Response(_serialize_state(profile))

    def _merge_progress(self, profile, incoming):
        existing = {p.book_slug: p for p in profile.progress.all()}
        for row in incoming:
            slug = row.get("book_slug")
            if not slug:
                continue
            local_dt = _ms_to_dt(row.get("updated_at"))
            server = existing.get(slug)
            # Keep the server row unless the local one is strictly newer.
            if server and local_dt and server.updated_at >= local_dt:
                continue
            ReadingProgress.objects.update_or_create(
                profile=profile,
                book_slug=slug,
                defaults={
                    "language": (row.get("language") or "en")[:10],
                    "chapter_order": _clamp_int(row.get("chapter_order"), default=1, low=1),
                    "paragraph_index": _clamp_int(row.get("paragraph_index"), default=0),
                },
            )

    def _merge_marks(self, profile, incoming):
        existing = {
            (m.book_slug, m.chapter_order): m for m in profile.marks.all()
        }
        for row in incoming:
            slug = row.get("book_slug")
            order = _clamp_int(row.get("chapter_order"), default=-1, low=0)
            if not slug or order < 0:
                continue
            highlights, notes = _clean_marks(row.get("highlights"), row.get("notes"))
            server = existing.get((slug, order))
            if server:
                highlights = sorted(set(server.highlights) | set(highlights))
                merged_notes = {str(k): v for k, v in server.notes.items()}
                for k, v in notes.items():
                    # On collision keep the longer text; never silently drop one.
                    if len(v) >= len(merged_notes.get(k, "")):
                        merged_notes[k] = v
                notes = merged_notes
            if not highlights and not notes:
                continue
            ChapterMarks.objects.update_or_create(
                profile=profile,
                book_slug=slug,
                chapter_order=order,
                defaults={
                    "language": (row.get("language") or "en")[:10],
                    "highlights": highlights,
                    "notes": notes,
                },
            )


def _serialize_state(profile) -> dict:
    return {
        "progress": ReadingProgressSerializer(
            profile.progress.all(), many=True
        ).data,
        "marks": ChapterMarksSerializer(profile.marks.all(), many=True).data,
    }
