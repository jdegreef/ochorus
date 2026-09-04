"""Authenticated API for a reader's own progress, highlights and notes.

Every endpoint requires a signed-in user and operates only on that user's rows
(scoped by their :class:`accounts.UserProfile`). The frontend mirrors the same
data in localStorage; these views are the synced source of truth. On first
sign-in the client POSTs its local state to :class:`MergeView`, which unions it
with anything already on the server (so nothing a reader did offline is lost) and
returns the merged whole.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from common.throttling import ScopedCacheThrottle

from .marks import (
    clean_mark_list,
    clean_tombstones,
    from_legacy,
    reconcile_marks,
)
from .models import (
    Bookmark,
    ChapterMarks,
    Favorite,
    FavoriteKind,
    PlanProgress,
    ReadingDay,
    ReadingProgress,
    WorkKind,
)
from .serializers import (
    BookmarkSerializer,
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


class _ReadingWriteThrottle(ScopedCacheThrottle):
    """Bounds how fast one signed-in account can mutate its reading state.

    These endpoints are ``IsAuthenticated``, so this caps a single account
    (keyed by user id); combined with the per-list merge caps it stops a scripted
    or compromised account from amplifying sync into unbounded DB writes.
    Generous enough that real highlight/scroll bursts never hit it — a bound, not
    access control (per-worker local-memory cache, like the search-click one)."""

    scope = "reading"


class _ReadingReadThrottle(ScopedCacheThrottle):
    """The same bound for READS of reading state (one per chapter open), on its
    own budget so they never eat into the write one — but still a ceiling:
    `_profile()` is a get_or_create, and an unbounded read path is a free loop."""

    scope = "reading-read"


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


def _clamp_int(value, default=0, low=0, high=None) -> int:
    try:
        n = max(low, int(value))
    except (TypeError, ValueError):
        return default
    return min(high, n) if high is not None else n


def _lang(value) -> str:
    """A language code coerced to a short string. A truthy non-string value (a
    number or list from a buggy client) would crash ``(x or "en")[:10]`` with a
    TypeError → 500, so anything but a non-empty string falls back to ``"en"``."""
    return value[:10] if isinstance(value, str) and value else "en"


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

    The read-union-write runs inside a transaction with the row locked
    (``select_for_update``): without it, two devices PUTting at once can both read
    the same old ``done`` and the second write clobbers the first's union — losing
    a completed day, the exact thing this function promises never happens. On
    SQLite the lock is a no-op (single-writer already); on Postgres it serializes
    the two writers. Nested inside MergeView's atomic block it's just a savepoint.

    The row is CREATED first, unlocked, and only then locked and merged. Locking
    before creating was the bug: ``SELECT … FOR UPDATE`` on a row that does not
    exist yet locks nothing — there is no tuple to lock, and a plain
    ``FOR UPDATE`` takes no gap lock in Postgres. So for a plan's FIRST write
    both devices saw ``existing = None``, both skipped the union, and both tried
    to create; the loser caught the ``IntegrityError`` inside
    ``update_or_create``, re-fetched, and then applied its own ``defaults``
    verbatim — overwriting the winner's day instead of unioning it. The guarantee
    held only from the second write onward, which is precisely when nobody is
    racing.
    """
    with transaction.atomic():
        # get_or_create so there is always a tuple to lock. Its defaults are the
        # incoming values, which is correct for a genuine first write and
        # harmless for the loser of a race — the merge below runs either way.
        obj, created = PlanProgress.objects.get_or_create(
            profile=profile,
            plan_slug=slug,
            defaults={"started_at": started, "done": sorted(set(done))},
        )
        # Re-read under the lock even when we just created the row: between the
        # create and here, the device that lost the race may already have merged
        # into it.
        locked = PlanProgress.objects.select_for_update().get(pk=obj.pk)
        merged_done = set(done) | set(locked.done)
        merged_started = min(started, locked.started_at)
        if created and merged_done == set(locked.done) and merged_started == locked.started_at:
            return locked  # nothing to add — the create already said it
        locked.done = sorted(merged_done)
        locked.started_at = merged_started
        locked.save(update_fields=["done", "started_at", "updated_at"])
    return locked


def _ms_to_dt(ms) -> datetime | None:
    """Interpret a client `updated_at` (epoch milliseconds) as an aware datetime."""
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=UTC)
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


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _upsert_progress(
    profile, kind, slug, *, language, chapter_order, paragraph_index, client_dt, keep_server_when_unknown
):
    """Upsert one reading-position row, keeping the server's when it is newer.

    The recency rule is SHARED by the live PUT and the sign-in merge so both
    resolve a conflict identically: a stale device — a backgrounded tab flushing
    a debounced push, an old localStorage bundle — can't rewind a position a
    newer device already recorded. It compares the incoming ``client_dt`` against
    the row's stored ``client_updated_at`` (both client-clock) rather than the
    server's ``updated_at`` (auto_now); comparing to the server clock would freeze
    any device whose clock lags the server, since after each save the server time
    is ~now and the lagging device's next timestamp is behind it.

    Progress is last-write-wins, not a union, so no row lock is needed: a race
    just picks a momentary winner and self-heals on the next read (contrast marks
    / plan progress, which union and so must lock — see ``_upsert_marks_locked``).

    ``keep_server_when_unknown`` differs by caller. The live PUT passes False: a
    PUT is an ACTIVE write, and an old client that sends no timestamp must still
    be able to save. The merge passes True: an untimestamped bundle is stale local
    state, so it must not overwrite a newer server position it can't out-date.
    """
    existing = ReadingProgress.objects.filter(
        profile=profile, kind=kind, book_slug=slug
    ).first()
    if existing:
        stored = existing.client_updated_at
        if client_dt is not None and stored is not None and stored >= client_dt:
            return existing
        if client_dt is None and keep_server_when_unknown:
            return existing
    obj, _ = ReadingProgress.objects.update_or_create(
        profile=profile,
        kind=kind,
        book_slug=slug,
        defaults={
            "language": language,
            "chapter_order": chapter_order,
            "paragraph_index": paragraph_index,
            "client_updated_at": client_dt,
        },
    )
    return obj


def _upsert_marks_locked(profile, kind, slug, order, *, language, marks, tombs, now_ms):
    """Reconcile one chapter's marks into the reader's row under a row lock.

    Same create-then-lock-then-reconcile shape (and reasoning) as
    ``_upsert_plan_progress``: without the lock two devices merging at once both
    read the same server marks and the second write clobbers the first's union,
    dropping a highlight the merge promises never to drop. The row is created
    first (so there is a tuple to lock — ``SELECT … FOR UPDATE`` on a not-yet-
    existing row locks nothing), then locked and reconciled. Returns the row, or
    None when nothing remains to store.

    An empty incoming (no marks, no tombstones) is a no-op — it neither adds nor
    deletes — so the existing row is returned untouched without taking the lock.
    """
    if not marks and not tombs:
        return ChapterMarks.objects.filter(
            profile=profile, kind=kind, book_slug=slug, chapter_order=order
        ).first()
    with transaction.atomic():
        obj, _ = ChapterMarks.objects.get_or_create(
            profile=profile,
            kind=kind,
            book_slug=slug,
            chapter_order=order,
            defaults={"language": language, "marks": [], "deleted": {}},
        )
        locked = ChapterMarks.objects.select_for_update().get(pk=obj.pk)
        server_marks = locked.marks or from_legacy(locked.highlights, locked.notes)
        merged, merged_tombs = reconcile_marks(
            server_marks, locked.deleted or {}, marks, tombs, now_ms
        )
        # Keep an empty row alive while it still carries tombstones — dropping it
        # would let a stale device re-push the deleted marks and win.
        if not merged and not merged_tombs:
            locked.delete()
            return None
        locked.language = language
        locked.marks = merged
        locked.deleted = merged_tombs
        locked.highlights = []
        locked.notes = {}
        locked.save(
            update_fields=["language", "marks", "deleted", "highlights", "notes", "updated_at"]
        )
    return locked


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
    """Read or upsert the reader's position in one book."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def get_throttles(self):
        # A read happens on every chapter open: its own budget, not the writes'.
        if self.request.method == "GET":
            return [_ReadingReadThrottle()]
        return super().get_throttles()

    def get(self, request, slug):
        """The account's synced position in one work — what another device last
        pushed. The reader asks on chapter open to offer "continue where you
        left off"; before this the only pull was the whole-state merge at
        sign-in, so a second device never learned the first had moved on."""
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        kind = _kind_or_none(request.query_params.get("kind"))
        if kind is None:
            return Response({"detail": "Unknown kind."}, status=400)
        profile = _profile(request)
        obj = ReadingProgress.objects.filter(profile=profile, kind=kind, book_slug=slug).first()
        if obj is None:
            return Response({"detail": "No position."}, status=404)
        return Response(ReadingProgressSerializer(obj).data)

    def put(self, request, slug):
        profile = _profile(request)
        data = _dict_body(request)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        kind = _kind_or_none(request.query_params.get("kind") or data.get("kind"))
        if kind is None:
            return Response({"detail": "Unknown kind."}, status=400)
        obj = _upsert_progress(
            profile,
            kind,
            slug,
            language=_lang(data.get("language")),
            chapter_order=_clamp_int(data.get("chapter_order"), default=1, low=1, high=MAX_CHAPTER_ORDER),
            paragraph_index=_clamp_int(data.get("paragraph_index"), default=0, high=MAX_CHAPTER_ORDER),
            client_dt=_ms_to_dt(data.get("updated_at")),
            # An active write: an old client without a timestamp must still save.
            keep_server_when_unknown=False,
        )
        return Response(ReadingProgressSerializer(obj).data)


class MarksView(APIView):
    """Sync the reader's marks for one chapter.

    A client that speaks the tombstone protocol (it sends a ``deleted`` list, even
    an empty one) is UNIONED with the server row, so a highlight another device
    added since this one last synced is never clobbered by a full-list push; that
    client's own deletions ride in ``deleted``. A client that sends no ``deleted``
    key is an older bundle that relies on replace-for-delete — it keeps the
    previous blind-replace behaviour so its deletions still land. The compat
    branch ages out with those bundles.
    """

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

        # Legacy client (no `deleted` key): blind replace, exactly as before — an
        # empty list still means "delete this chapter's marks".
        if not isinstance(data.get("deleted"), (list, dict)):
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
                    "language": _lang(data.get("language")),
                    "marks": marks,
                    "highlights": [],
                    "notes": {},
                },
            )
            return Response(ChapterMarksSerializer(obj).data)

        # Tombstone protocol: reconcile under a row lock (the shared helper) so two
        # devices' concurrent merges can't lose one another's marks. None back means
        # the chapter has neither marks nor tombstones left.
        row = _upsert_marks_locked(
            profile,
            kind,
            slug,
            order,
            language=_lang(data.get("language")),
            marks=marks,
            tombs=clean_tombstones(data.get("deleted")),
            now_ms=_now_ms(),
        )
        if row is None:
            return Response({"marks": []})
        return Response(ChapterMarksSerializer(row).data)


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
                "language": _lang(data.get("language")),
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


def _bookmark_fields(data) -> dict:
    """The cached display fields from a bookmark payload, bounded to the columns."""
    return {
        "bm_id": str(data.get("bm_id") or "")[:80],
        "snippet": str(data.get("snippet") or "")[:300],
        "title": str(data.get("title") or "")[:300],
    }


class BookmarksView(APIView):
    """Save / unsave one bookmark — a paragraph the reader saved on purpose.

    Add/remove like :class:`FavoriteView`: PUT the position to save it (with its
    cached snippet/title), DELETE to remove it. Identity is the position, so
    saving the same paragraph twice keeps one row (its display text refreshed).
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def _locate(self, kind, slug, order, p):
        """Validate the path parts → (kind, order, p) or None.

        `p` is bounded like the other integer columns (see MAX_CHAPTER_ORDER):
        `<int:p>` matches an arbitrarily long run of digits, and an out-of-range
        value would reach the DB as an integer-overflow DataError (a 500). A
        paragraph index far beyond any real chapter is junk regardless.
        """
        k = _kind_or_none(kind)
        o = _valid_order(order)
        if k is None or not _valid_slug(slug) or o is None or not 0 <= p <= MAX_CHAPTER_ORDER:
            return None
        return k, o, p

    def put(self, request, kind, slug, order, p):
        loc = self._locate(kind, slug, order, p)
        if loc is None:
            return Response({"detail": "Invalid bookmark."}, status=400)
        k, o, pi = loc
        profile = _profile(request)
        obj, _ = Bookmark.objects.update_or_create(
            profile=profile,
            kind=k,
            book_slug=slug,
            chapter_order=o,
            paragraph_index=pi,
            defaults=_bookmark_fields(_dict_body(request)),
        )
        return Response(BookmarkSerializer(obj).data)

    def delete(self, request, kind, slug, order, p):
        loc = self._locate(kind, slug, order, p)
        if loc is None:
            return Response({"detail": "Invalid bookmark."}, status=400)
        k, o, pi = loc
        profile = _profile(request)
        Bookmark.objects.filter(
            profile=profile, kind=k, book_slug=slug, chapter_order=o, paragraph_index=pi
        ).delete()
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
        started = _ms_to_dt(data.get("started_at")) or datetime.now(UTC)
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
    ms); marks are *unioned* — on a note collision the longer text wins — so no
    highlight or note a real reader made is dropped (the union is bounded only by
    a large per-chapter anti-abuse cap; see marks.MAX_MARKS_PER_CHAPTER). Returns
    the merged whole for the client to write back over its localStorage cache.
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
            self._merge_bookmarks(profile, data.get("bookmarks") or [])
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
            started = _ms_to_dt(row.get("started_at")) or datetime.now(UTC)
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
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            if not _valid_slug(slug) or kind is None:
                continue
            _upsert_progress(
                profile,
                kind,
                slug,
                language=_lang(row.get("language")),
                chapter_order=_clamp_int(row.get("chapter_order"), default=1, low=1, high=MAX_CHAPTER_ORDER),
                paragraph_index=_clamp_int(row.get("paragraph_index"), default=0, high=MAX_CHAPTER_ORDER),
                client_dt=_ms_to_dt(row.get("updated_at")),
                # Stale local state must not overwrite a newer server position it
                # can't out-date; an untimestamped row keeps the server's.
                keep_server_when_unknown=True,
            )

    def _merge_bookmarks(self, profile, incoming):
        """Union offline bookmarks into the account in one INSERT … ON CONFLICT
        DO NOTHING — a bookmark made on either side survives and re-runs are
        idempotent (the unique position constraint skips ones already saved),
        like ``_merge_favorites``. A non-list is ignored and non-dict / malformed
        rows are skipped so a bad bundle can't 500 the reconcile; ``p`` is bounded
        like the other integer columns to keep an out-of-range value off the DB."""
        if not isinstance(incoming, list):
            return
        rows = {}
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("book_slug")
            kind = _kind_or_none(row.get("kind"))
            order = _valid_order(row.get("chapter_order"))
            p = row.get("paragraph_index")
            if (
                not _valid_slug(slug)
                or kind is None
                or order is None
                or not isinstance(p, int)
                or not 0 <= p <= MAX_CHAPTER_ORDER
            ):
                continue
            rows[(kind, slug, order, p)] = Bookmark(
                profile=profile,
                kind=kind,
                book_slug=slug,
                chapter_order=order,
                paragraph_index=p,
                **_bookmark_fields(row),
            )
        Bookmark.objects.bulk_create(list(rows.values()), ignore_conflicts=True)

    def _merge_marks(self, profile, incoming):
        if not isinstance(incoming, list):
            return
        now_ms = _now_ms()
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
            # The locked reconcile unions marks and applies tombstones (so a
            # highlight deleted offline stays deleted) under a row lock — two
            # devices merging at once can't lose each other's marks.
            _upsert_marks_locked(
                profile,
                kind,
                slug,
                order,
                language=_lang(row.get("language")),
                marks=_marks_from_payload(row),
                tombs=clean_tombstones(row.get("deleted")),
                now_ms=now_ms,
            )

    def _merge_sermon_marks(self, profile, incoming):
        """COMPAT: old bundles send sermon marks in their own payload field —
        fold them into ChapterMarks(kind="sermon") so nothing is dropped. A
        non-list is ignored and non-dict rows skipped."""
        if not isinstance(incoming, list):
            return
        now_ms = _now_ms()
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            slug = row.get("sermon_slug")
            if not _valid_slug(slug):
                continue
            # Old bundles carry no tombstones here, so this is a plain union —
            # but routed through the same locked reconcile as every other mark
            # write, so a concurrent merge can't drop a sermon highlight either.
            _upsert_marks_locked(
                profile,
                WorkKind.SERMON,
                slug,
                1,
                language=_lang(row.get("language")),
                marks=_marks_from_payload(row),
                tombs={},
                now_ms=now_ms,
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
        "bookmarks": BookmarkSerializer(profile.bookmarks.all(), many=True).data,
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
