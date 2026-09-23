"""Authenticated API for a reader's own progress, highlights and notes.

Every endpoint requires a signed-in user and operates only on that user's rows
(scoped by their :class:`accounts.UserProfile`). The frontend mirrors the same
data in localStorage; these views are the synced source of truth. On first
sign-in the client POSTs its local state to :class:`MergeView`, which unions it
with anything already on the server (so nothing a reader did offline is lost) and
returns the merged whole.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

from django.db import IntegrityError, transaction
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
    JournalEntry,
    JournalKind,
    PlanProgress,
    PrayerGroup,
    ReadingDay,
    ReadingProgress,
    ReadingSession,
    Removal,
    WorkKind,
)
from .serializers import (
    BookmarkSerializer,
    ChapterMarksSerializer,
    FavoriteSerializer,
    JournalEntrySerializer,
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


def _passage(kind, slug, order, p) -> tuple[str, int, int] | None:
    """A place in a text — (kind, order, p) — validated, or None.

    `p` is bounded like the other integer columns (see MAX_CHAPTER_ORDER): an
    arbitrarily long run of digits would reach the DB as an integer-overflow
    DataError (a 500), and a paragraph index far beyond any real chapter is
    junk regardless. Shared by bookmarks and a journal entry's source.
    """
    k = _kind_or_none(kind)
    o = _valid_order(order)
    if k is None or not _valid_slug(slug) or o is None:
        return None
    if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p <= MAX_CHAPTER_ORDER:
        return None
    return k, o, p


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


def _is_stale_against(tomb: Removal | None, client_dt: datetime | None) -> bool:
    """Is an incoming position / heart NOT newer than the reader's removal of it?

    An untimestamped write is stale by definition: it can't show it came after
    the removal, and the stale device re-uploading what it still holds — the
    case the tombstone exists for — is exactly the write that carries no newer
    clock.
    """
    return tomb is not None and (client_dt is None or client_dt <= tomb.removed_at)


def _tombstone(profile, domain, kind, slug) -> Removal | None:
    return Removal.objects.filter(profile=profile, domain=domain, kind=kind, slug=slug).first()


def _record_removal(profile, domain, kind, slug, removed_at: datetime, *, live: bool) -> bool:
    """Take a position or heart off the reader's account, and leave a tombstone
    so a device that still holds it can't merge it back (see ``Removal``).

    A LIVE removal (the DELETE, made now by the reader's own tap) always
    applies. Its tombstone is stamped no earlier than the row's own client
    clock, so every stale copy of that row is covered even when the removing
    device's clock lags the one that last wrote it — otherwise a slow clock
    would leave the tombstone older than the very position it removed.

    A removal carried up LATE by the merge (made offline) is itself stale if
    the thing it removes is newer — a position read after it, or a heart saved
    after it — and is then not applied (False). A heart has no client clock of
    its own, so its server ``created_at`` stands in there.

    The tombstone keeps the LATEST removal time, so an older removal arriving
    late can't narrow what a newer one covers.
    """
    with transaction.atomic():
        if domain == Removal.Domain.PROGRESS:
            rows = ReadingProgress.objects.filter(profile=profile, kind=kind, book_slug=slug)
            row = rows.first()
            row_at = row.client_updated_at if row else None
        else:
            rows = Favorite.objects.filter(profile=profile, kind=kind, slug=slug)
            row = rows.first()
            row_at = row.created_at if row else None
        if row_at is not None and row_at > removed_at:
            if not live:
                return False
            removed_at = row_at
        rows.delete()
        tomb, created = Removal.objects.get_or_create(
            profile=profile,
            domain=domain,
            kind=kind,
            slug=slug,
            defaults={"removed_at": removed_at},
        )
        if not created and tomb.removed_at < removed_at:
            tomb.removed_at = removed_at
            tomb.save(update_fields=["removed_at"])
    return True


def _removed_at(value) -> datetime:
    """The removing device's clock (epoch ms) for a live DELETE, else now."""
    return _ms_to_dt(value) or datetime.now(UTC)


def _upsert_progress(
    profile,
    kind,
    slug,
    *,
    language,
    chapter_order,
    paragraph_index,
    client_dt,
    keep_server_when_unknown,
    finished_at=None,
    clear_finished=False,
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

    ``finished_at`` is resolved SEPARATELY from the position, and it UNIONS: the
    earliest non-null wins and a write that omits it never clears it, so a
    completion earned on any device survives (the same lossless rule as plan days
    and favorites). Keeping it independent of the recency rule matters — a device
    that reaches the end has, by definition, the furthest position, but a stale
    late push finishing an already-advanced work must still land its finish
    without rewinding the position, and an explicit un-finish must clear even
    when its position is stale. ``clear_finished`` (an explicit un-finish) is the
    one thing that clears it; like un-favoriting it is a live-only signal the
    merge never carries.

    A position the reader REMOVED from their shelf (a ``Removal`` tombstone) is
    only re-created by a write newer than the removal — they read it again.
    Anything older is a stale device re-uploading what it still holds: it is
    dropped and None comes back. A newer write clears the tombstone.
    """
    tomb = _tombstone(profile, Removal.Domain.PROGRESS, kind, slug)
    if tomb is not None:
        if _is_stale_against(tomb, client_dt):
            return None
        tomb.delete()

    existing = ReadingProgress.objects.filter(
        profile=profile, kind=kind, book_slug=slug
    ).first()

    # Resolve the finished state first, independently of the position below.
    server_finished = existing.finished_at if existing else None
    if clear_finished:
        resolved_finished = None
    elif server_finished and finished_at:
        resolved_finished = min(server_finished, finished_at)
    else:
        resolved_finished = server_finished or finished_at

    # Is the incoming POSITION stale (the stored one is at least as new)? Either
    # the stored client-clock is at or ahead of the incoming one, or the incoming
    # carries no clock and the caller keeps the server's in that case (the merge).
    position_stale = False
    if existing:
        stored = existing.client_updated_at
        position_stale = (stored is not None and client_dt is not None and stored >= client_dt) or (
            client_dt is None and keep_server_when_unknown
        )

    if position_stale:
        # Keep the server's newer position, but still apply a finished change —
        # finishing/un-finishing is resolved apart from the position for exactly
        # this case (a stale position must not rewind, yet the finish must land).
        # `position_stale` is only ever set inside `if existing:`, so it's here.
        if resolved_finished != server_finished:
            existing.finished_at = resolved_finished
            existing.save(update_fields=["finished_at"])
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
            "finished_at": resolved_finished,
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
            # `finished_at` (epoch ms) marks the work finished; `unfinish` clears
            # it. A plain position save carries neither and leaves it untouched.
            finished_at=_ms_to_dt(data.get("finished_at")),
            clear_finished=bool(data.get("unfinish")),
        )
        if obj is None:
            # Removed from the shelf after this position was taken: a stale
            # push. Not an error — the client's next merge drops it locally.
            return Response({"removed": True})
        return Response(ReadingProgressSerializer(obj).data)

    def delete(self, request, slug):
        """Remove this work from the reader's shelf (the Bookshelf's "Remove"):
        drop the position and leave a tombstone so it stays removed across
        devices. ``?at=`` is the removing device's clock (epoch ms). 204 either
        way."""
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        kind = _kind_or_none(request.query_params.get("kind"))
        if kind is None:
            return Response({"detail": "Unknown kind."}, status=400)
        _record_removal(
            _profile(request),
            Removal.Domain.PROGRESS,
            kind,
            slug,
            _removed_at(request.query_params.get("at")),
            live=True,
        )
        return Response(status=204)


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
    """Save / unsave one favorite (an author, book, plan, sermon, topic,
    article or quote — see FavoriteKind)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        profile = _profile(request)
        # A live heart is always a new act: it lifts any earlier removal.
        Removal.objects.filter(
            profile=profile, domain=Removal.Domain.FAVORITE, kind=kind, slug=slug
        ).delete()
        obj, _ = Favorite.objects.get_or_create(
            profile=profile, kind=kind, slug=slug
        )
        return Response(FavoriteSerializer(obj).data)

    def delete(self, request, kind, slug):
        if kind not in FavoriteKind.values:
            return Response({"detail": "Unknown kind."}, status=400)
        if not _valid_slug(slug):
            return Response({"detail": "Invalid slug."}, status=400)
        # Delete AND tombstone, so another device still holding the heart can't
        # merge it back (see Removal). `?at=` is the device's clock (epoch ms).
        _record_removal(
            _profile(request),
            Removal.Domain.FAVORITE,
            kind,
            slug,
            _removed_at(request.query_params.get("at")),
            live=True,
        )
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

    def put(self, request, kind, slug, order, p):
        loc = _passage(kind, slug, order, p)
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
        loc = _passage(kind, slug, order, p)
        if loc is None:
            return Response({"detail": "Invalid bookmark."}, status=400)
        k, o, pi = loc
        profile = _profile(request)
        Bookmark.objects.filter(
            profile=profile, kind=k, book_slug=slug, chapter_order=o, paragraph_index=pi
        ).delete()
        return Response(status=204)


# --- Journal (the Notebook's own notes and prayers) ---------------------------

# A client id: the frontend mints `<base36 time>-<random>`; anything URL-safe
# up to the column width is accepted, anything else is junk.
_JOURNAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Column / anti-abuse bounds. Generous for real writing (a long prayer journal
# entry is a few thousand characters), finite so one account can't store MBs.
JOURNAL_BODY_MAX = 20_000
JOURNAL_ANSWER_MAX = 10_000
MAX_JOURNAL_ENTRIES = 5_000
# How far ahead of the server a client clock may stamp a write. Last-write-wins
# trusts the device's clock; one set years ahead would otherwise make its entry
# immune to every later edit from a correct device.
JOURNAL_CLOCK_SKEW = timedelta(days=1)
_JOURNAL_REMIND = re.compile(r"^(daily|weekly-[0-6])@([01]\d|2[0-3]):[0-5]\d$")
MAX_JOURNAL_UPDATES = 50
JOURNAL_UPDATE_MAX = 2_000


def _journal_updates(value) -> list:
    """A prayer's follow-ups → a bounded list of {at, text}; junk dropped."""
    if not isinstance(value, list):
        return []
    out = []
    for u in value[:MAX_JOURNAL_UPDATES]:
        if not isinstance(u, dict) or not isinstance(u.get("text"), str) or not u["text"].strip():
            continue
        at = _ms_to_dt(u.get("at"))
        if at is None:
            continue
        out.append({"at": int(at.timestamp() * 1000), "text": u["text"][:JOURNAL_UPDATE_MAX]})
    return out


def _journal_source(value) -> dict | None:
    """The passage an entry was written from, validated field by field, or None.

    Only positions and display text are kept — never a URL — so nothing a
    client sends can become a link the Notebook renders."""
    # The kind is required here: _kind_or_none's absent-means-book default is
    # for old progress clients, and would file a sermon's passage as a book's.
    if not isinstance(value, dict) or value.get("kind") not in WorkKind.values:
        return None
    slug = value.get("slug")
    place = _passage(value.get("kind"), slug, value.get("order"), value.get("p"))
    edition = value.get("edition")
    if place is None or not isinstance(edition, str) or not 0 < len(edition) <= 16:
        return None
    kind, order, p = place
    return {
        "kind": kind,
        "slug": slug,
        "order": order,
        "p": p,
        "edition": edition,
        "title": str(value.get("title") or "")[:200],
        "quote": str(value.get("quote") or "")[:600],
    }


_JOURNAL_BLANK = {
    "title": "",
    "body": "",
    "answer": "",
    "answered_at": None,
    "ref": "",
    "person": "",
    "group": "",
    "remind": "",
    "updates": [],
    "source": None,
}


# Every column a later write may change — all but identity and first-write time.
_JOURNAL_WRITABLE = [*_JOURNAL_BLANK, "kind", "deleted", "client_updated_at", "updated_at"]


def _journal_fields(data) -> dict | None:
    """A journal payload → cleaned column values, or None when it is unusable.

    Text is bounded to the columns rather than rejected, like a bookmark's
    snippet. An unknown kind is None (a newer client than this server —
    misfiling a prayer as a note would lose what makes it one). Only a prayer
    can be answered.
    """
    if not isinstance(data, dict):
        return None
    kind = data.get("kind") or JournalKind.NOTE
    if kind not in JournalKind.values:
        return None
    now = datetime.now(UTC)
    updated = min(_ms_to_dt(data.get("client_updated_at")) or now, now + JOURNAL_CLOCK_SKEW)
    created = min(_ms_to_dt(data.get("client_created_at")) or updated, updated)

    def text(key, n):
        return str(data.get(key) or "")[:n]

    deleted = data.get("deleted") is True
    if deleted:
        # A tombstone keeps its identity and clock, never the reader's words —
        # the one place that rule lives.
        return {
            **_JOURNAL_BLANK,
            "kind": kind,
            "deleted": True,
            "client_created_at": created,
            "client_updated_at": updated,
        }
    prayer = kind == JournalKind.PRAYER
    answered = _ms_to_dt(data.get("answered_at")) if prayer else None
    group = data.get("group")
    remind = data.get("remind")
    return {
        "kind": kind,
        "title": text("title", 200),
        "body": text("body", JOURNAL_BODY_MAX),
        "answer": text("answer", JOURNAL_ANSWER_MAX) if answered else "",
        "answered_at": answered,
        "ref": text("ref", 200),
        # Who a prayer is for, its group, reminder and follow-ups are prayer
        # things; a note carries none of them.
        "person": text("person", 80) if prayer else "",
        "group": group if prayer and group in PrayerGroup.values else "",
        "remind": remind if prayer and isinstance(remind, str) and _JOURNAL_REMIND.match(remind) else "",
        "updates": _journal_updates(data.get("updates")) if prayer else [],
        "source": _journal_source(data.get("source")),
        "deleted": False,
        "client_created_at": created,
        "client_updated_at": updated,
    }


def _live_journal_count(profile) -> int:
    """Entries toward the cap — tombstones are never pruned, and counting them
    would one day lock a reader who deletes a lot out of writing anything."""
    return profile.journal_entries.filter(deleted=False).count()


def _journal_wins(obj: JournalEntry, fields: dict) -> bool:
    """Whether an incoming write replaces the stored entry.

    Last-write-wins on the writing device's clock; an equal clock is the same
    write arriving again (every sign-in merge re-sends the whole journal), so
    it is skipped rather than rewritten. A delete is STICKY once stored — an
    offline device's stale edit of a prayer the reader deleted must not bring
    it back — and always lands, whatever the clocks say, so a device whose
    clock runs fast can't make its entry undeletable.
    """
    if obj.deleted:
        return False
    return fields["deleted"] or fields["client_updated_at"] > obj.client_updated_at


def _apply_journal(obj: JournalEntry, fields: dict) -> None:
    for k, v in fields.items():
        if k != "client_created_at":
            setattr(obj, k, v)


def _upsert_journal(profile, entry_id: str, fields: dict) -> JournalEntry | None:
    """One entry, under a row lock (see ``_journal_wins``). Returns None only
    when a NEW entry would pass the per-account cap."""
    for _ in range(2):
        with transaction.atomic():
            obj = (
                JournalEntry.objects.select_for_update()
                .filter(profile=profile, entry_id=entry_id)
                .first()
            )
            if obj is not None:
                if _journal_wins(obj, fields):
                    _apply_journal(obj, fields)
                    obj.save()
                return obj
            if not fields["deleted"] and _live_journal_count(profile) >= MAX_JOURNAL_ENTRIES:
                return None
            try:
                with transaction.atomic():
                    return JournalEntry.objects.create(
                        profile=profile, entry_id=entry_id, **fields
                    )
            except IntegrityError:
                # A concurrent first write of the same entry won the insert;
                # loop once to take the locked update path against its row.
                continue
    return JournalEntry.objects.get(profile=profile, entry_id=entry_id)


class JournalView(APIView):
    """Save one Notebook entry (a note or a prayer), or tombstone it.

    PUT carries the whole entry — edits are last-write-wins by the client's
    `client_updated_at` — and a delete is a PUT with `deleted: true`, so it
    propagates to every device instead of being resurrected by one that was
    offline. See :class:`JournalEntry`.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request, entry_id):
        if not _JOURNAL_ID.match(entry_id):
            return Response({"detail": "Invalid entry id."}, status=400)
        fields = _journal_fields(_dict_body(request))
        if fields is None:
            return Response({"detail": "Invalid entry."}, status=400)
        obj = _upsert_journal(_profile(request), entry_id, fields)
        if obj is None:
            return Response({"detail": "Notebook is full."}, status=400)
        return Response(JournalEntrySerializer(obj).data)


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


# A single sitting can't sanely exceed a day of ACTIVE reading; clamp so a buggy
# or hostile client can't store a wild total that would skew every average.
MAX_SESSION_SECONDS = 24 * 60 * 60


def _session_kind(value) -> str:
    """A WorkKind for the session's context, or "" — blank is allowed here
    (unlike progress, which must file a row under *some* kind). An unknown value
    is dropped to blank rather than stored."""
    return value if value in WorkKind.values else ""


def _sessions_from_body(request) -> list[dict]:
    """The session dicts from the PUT body's ``sessions`` list — same envelope
    convention as MergeView's sections (``_as_dict(...).get(...)``)."""
    rows = _as_dict(request.data).get("sessions", [])
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


class SessionsView(APIView):
    """Sync reading sittings — the signal behind "time on site".

    The client owns each sitting's id and accumulates its ACTIVE reading time
    (see :class:`reading.models.ReadingSession`); this upserts by
    (profile, client_id) with the same union rule as the rest of the layer —
    seconds only grow, the earliest start and latest last-seen win — so a retry
    or a second device never double-counts or loses time. Context
    (kind/slug/language) is filled once, from the first sync that carries it.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [_ReadingWriteThrottle]

    def put(self, request):
        profile = _profile(request)
        rows = _sessions_from_body(request)[:MAX_MERGE_ROWS]
        saved = 0
        with transaction.atomic():
            for r in rows:
                cid = r.get("client_id")
                if not isinstance(cid, str) or not cid:
                    continue
                start = _ms_to_dt(r.get("started_at"))
                seen = _ms_to_dt(r.get("last_seen_at"))
                if start is None or seen is None:
                    continue
                if seen < start:
                    seen = start
                secs = _clamp_int(r.get("seconds"), 0, 0, MAX_SESSION_SECONDS)
                slug = r.get("book_slug")
                book_slug = slug if _valid_slug(slug) else ""
                obj, created = ReadingSession.objects.get_or_create(
                    profile=profile,
                    client_id=cid[:80],
                    defaults={
                        "started_at": start,
                        "last_seen_at": seen,
                        "seconds": secs,
                        "kind": _session_kind(r.get("kind")),
                        "book_slug": book_slug,
                        "language": _lang(r.get("language")) if r.get("language") else "",
                    },
                )
                if not created:
                    # Re-read under a row lock before the union, exactly as
                    # _upsert_plan_progress does: without it two concurrent PUTs
                    # for the same (profile, client_id) — two tabs share the
                    # localStorage client id — can both read the old row and the
                    # later write wins with a *smaller* max. SQLite no-ops the
                    # lock; Postgres serializes the two writers.
                    obj = ReadingSession.objects.select_for_update().get(pk=obj.pk)
                    obj.started_at = min(obj.started_at, start)
                    obj.last_seen_at = max(obj.last_seen_at, seen)
                    obj.seconds = max(obj.seconds, secs)
                    # Context is write-once: fill it only if a prior sync hadn't.
                    if not obj.kind:
                        obj.kind = _session_kind(r.get("kind"))
                    if not obj.book_slug and book_slug:
                        obj.book_slug = book_slug
                    if not obj.language and r.get("language"):
                        obj.language = _lang(r.get("language"))
                    obj.save()
                saved += 1
        return Response({"ok": True, "count": saved})


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
        # All the phases are one transaction: a failure in a later phase (or a
        # DB error mid-write) must not leave the account half-reconciled — the
        # client writes the returned state back over localStorage, so a partial
        # merge would silently diverge local and server.
        with transaction.atomic():
            # Removals first: they may be this device's own offline removals,
            # and the unions below must see their tombstones.
            self._merge_removals(profile, data.get("removed") or [])
            self._merge_progress(profile, data.get("progress") or [])
            self._merge_marks(profile, data.get("marks") or [])
            self._merge_sermon_marks(profile, data.get("sermon_marks") or [])
            self._merge_favorites(profile, data.get("favorites") or [])
            self._merge_bookmarks(profile, data.get("bookmarks") or [])
            self._merge_activity(profile, data.get("activity") or [])
            self._merge_plan_progress(profile, data.get("plan_progress") or [])
            self._merge_journal(profile, data.get("journal") or [])
        # `removed_applied` tells the client this API honours `removed`, so it
        # may drop its pending list. An API from before tombstones ignores the
        # field — without this, the client would clear removals nobody applied.
        return Response({**_serialize_state(profile), "removed_applied": True})

    def _merge_removals(self, profile, incoming):
        """Apply removals the device made while its live DELETE couldn't land
        (offline, or the request failed) — ``[{domain, kind, slug, at}]``. Each
        goes through the same rule as a live DELETE, so one outdated by newer
        activity elsewhere is not applied. Malformed rows are skipped; a row
        with no ``at`` is skipped too (a removal must say when it happened)."""
        if not isinstance(incoming, list):
            return
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            domain, kind, slug = row.get("domain"), row.get("kind"), row.get("slug")
            removed_at = _ms_to_dt(row.get("at"))
            if removed_at is None or not _valid_slug(slug):
                continue
            if domain == Removal.Domain.PROGRESS:
                kind = _kind_or_none(kind)
                if kind is None:
                    continue
            elif domain == Removal.Domain.FAVORITE:
                if kind not in FavoriteKind.values:
                    continue
            else:
                continue
            _record_removal(profile, domain, kind, slug, removed_at, live=False)

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

    def _merge_journal(self, profile, incoming):
        """The same last-write-wins rule as a live PUT (``_journal_wins``),
        batched: this runs on every sign-in and session restore with the whole
        journal, so it is one locked read, one bulk update of the entries that
        changed, and one bulk insert of the new ones — not a round-trip per
        entry. A non-list is ignored and malformed rows skipped, like every
        other section; new entries stop at the per-account cap."""
        if not isinstance(incoming, list):
            return
        rows = {}
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            entry_id = row.get("entry_id")
            fields = _journal_fields(row)
            if isinstance(entry_id, str) and _JOURNAL_ID.match(entry_id) and fields is not None:
                rows[entry_id] = fields
        if not rows:
            return
        existing = {
            e.entry_id: e
            for e in JournalEntry.objects.select_for_update().filter(
                profile=profile, entry_id__in=list(rows)
            )
        }
        changed = []
        for entry_id, fields in rows.items():
            obj = existing.get(entry_id)
            if obj is not None and _journal_wins(obj, fields):
                _apply_journal(obj, fields)
                changed.append(obj)
        if changed:
            # bulk_update skips auto_now, so the server-side stamp is set here.
            now = datetime.now(UTC)
            for obj in changed:
                obj.updated_at = now
            JournalEntry.objects.bulk_update(changed, _JOURNAL_WRITABLE)
        room = MAX_JOURNAL_ENTRIES - _live_journal_count(profile)
        new = []
        for entry_id, fields in rows.items():
            if entry_id in existing:
                continue
            # A tombstone is always accepted (it holds no words, and a delete
            # must sync); only live entries spend the cap.
            if not fields["deleted"]:
                if room <= 0:
                    continue
                room -= 1
            new.append(JournalEntry(profile=profile, entry_id=entry_id, **fields))
        # ON CONFLICT DO NOTHING: an entry a concurrent write created since the
        # read above keeps that write, like the other merge sections' unions.
        JournalEntry.objects.bulk_create(new, ignore_conflicts=True)

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
        can't 500 the sign-in reconciliation.

        Except a heart the reader REMOVED elsewhere: one not saved after the
        removal (``saved_at``, epoch ms; absent on older clients, so stale) is a
        device re-uploading what it still holds, and is dropped. One saved after
        it is a real re-heart made offline: it lands and lifts the tombstone."""
        if not isinstance(incoming, list):
            return
        tombs = {
            (t.kind, t.slug): t
            for t in Removal.objects.filter(profile=profile, domain=Removal.Domain.FAVORITE)
        }
        favorites = {}
        for row in incoming[:MAX_MERGE_ROWS]:
            if not isinstance(row, dict):
                continue
            kind = row.get("kind")
            slug = row.get("slug")
            if not _valid_slug(slug) or kind not in FavoriteKind.values:
                continue
            tomb = tombs.get((kind, slug))
            if tomb is not None:
                if _is_stale_against(tomb, _ms_to_dt(row.get("saved_at"))):
                    continue
                tomb.delete()
                del tombs[(kind, slug)]
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
                # Finishing unions in (earliest non-null wins); the merge never
                # CLEARS — un-finish is a live-only signal, like un-favoriting.
                finished_at=_ms_to_dt(row.get("finished_at")),
                clear_finished=False,
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
        # Tombstones included: a device holding a since-deleted entry learns
        # the delete from them instead of pushing the entry back.
        "journal": JournalEntrySerializer(profile.journal_entries.all(), many=True).data,
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
