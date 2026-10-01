"""Admin dashboard API — the record of what has been done here.

Reads ``AdminAction``. Its own module rather than a section of the content
audit: that page answers "is the library in good shape", and this one answers
"who changed it". Filing them together would put an administrator's name in a
report about chapter quality.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import is_admin_user, requires

from ..models import AdminAction
from .analytics import mask_email

#: Team-grant rows target the grantee as ``user:<email>`` (see ``team.py``).
USER_TARGET = "user:"

#: The filter chips' families, keyed by the part of an action before the dot.
#: The server twin of ``actionMeta`` in ``frontend/src/lib/adminActivity.ts``:
#: the chips filter here now, so the two must file an action the same way. A
#: prefix not listed (audit, broadcast, feedback) lands in ``content`` there too.
CATEGORIES = ("language", "content", "review", "translation", "author", "access")
_PREFIX_CATEGORY = {c: c for c in CATEGORIES} | {"role": "access"}

#: The actions that change what a reader sees — ``loud`` in ``actionMeta``.
READER_FACING = frozenset(
    {
        AdminAction.Action.LANGUAGE_GO_LIVE,
        AdminAction.Action.CONTENT_PUBLISH,
        AdminAction.Action.CONTENT_UNPUBLISH,
        AdminAction.Action.ROLE_GRANT,
        AdminAction.Action.ROLE_REVOKE,
    }
)


def category_of(action: str) -> str:
    return _PREFIX_CATEGORY.get(action.split(".", 1)[0], "content")


def actions_in(category: str) -> list[str]:
    return [a for a in AdminAction.Action.values if category_of(a) == category]


def _serialize(row: AdminAction, *, reveal: bool) -> dict:
    """One log row. ``reveal`` is whether the caller is a super admin; for anyone
    else the actor and any ``user:<email>`` target are masked — every role holds
    ``reporting:view``, and an unmasked log would hand the lowest of them the
    email and role of every admin on the team (the ``mask_email`` bar)."""
    actor, target = row.actor, row.target
    if not reveal:
        actor = mask_email(actor) if actor else actor
        if target.startswith(USER_TARGET):
            target = USER_TARGET + mask_email(target[len(USER_TARGET):])
    return {
        "action": row.action,
        # The human phrasing lives with the choices, so the label a reader sees
        # and the value stored cannot drift.
        "label": AdminAction.Action(row.action).label,
        "actor": actor,
        "target": target,
        "detail": row.detail,
        "at": row.at.isoformat(),
    }


def _parse_cursor(raw: str | None) -> int | None:
    """A ``before`` cursor as a positive int, or None for anything off-shape.

    A bad cursor returns the newest page rather than a 400: it can only come
    from a stale link or a hand-edited URL, and the useful answer to both is the
    top of the log, not an error.
    """
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _day_start(raw: str | None, now):
    """The caller's local midnight, so "today" means the admin's day, not UTC's.

    Anything unparseable, naive, or not within the last day and a half (a
    stale tab, a hand-edited URL) falls back to the server's own midnight.
    """
    parsed = parse_datetime(raw) if raw else None
    if parsed and timezone.is_aware(parsed) and now - timedelta(hours=36) <= parsed <= now:
        return parsed
    return timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminActivityView(APIView):
    """Admin actions, newest first — a page at a time, optionally one target.

    Still a "what happened lately" screen by default: no cursor returns the most
    recent ``LIMIT``. But an append-only log is exactly the thing that grows
    without anyone noticing, so two ways to reach past that window:

    * ``?before=<id>`` returns the page of rows older than that id — the "load
      older" cursor. Keyset on the primary key rather than an offset: the table
      only ever grows at the head, so an id both orders the rows (it rises with
      ``at``) and is a stable boundary that a new insert cannot shift, which an
      OFFSET would.
    * ``?target=<target>`` narrows to one object's whole history — "everything
      that happened to ``language:sw``" — and paginates the same way.

    ``next_cursor`` is the id to pass as ``before`` for the next older page, or
    null when this was the last. It is set by fetching one row beyond the page
    and keeping it only as the "there is more" signal, so the client never has
    to make a trailing request that comes back empty.

    Filters run here, over the whole log, not over the page the client holds —
    a search that only saw the newest hundred rows answered "never happened"
    for anything older:

    * ``?q=`` matches target, actor, detail, or the action's label.
    * ``?category=`` one of ``CATEGORIES``; ``?actor=`` one admin, by the
      (possibly masked) value the rows carry.
    * ``?export=1`` returns every match up to ``EXPORT_LIMIT``, unpaged, for
      the CSV — an export of the loaded page alone silently dropped the rest.

    The first page also carries ``summary``: the header cards and chip counts,
    counted in SQL over the whole (target-scoped) log. ``?day_start=`` is the
    caller's local midnight, for "today".
    """

    #: Enough to cover a working session and a couple before it.
    LIMIT = 100
    #: An export is a file, not a page — but still bounded.
    EXPORT_LIMIT = 20_000

    def get(self, request):
        params = request.query_params
        target = (params.get("target") or "").strip()
        before = _parse_cursor(params.get("before"))
        q = (params.get("q") or "").strip()
        category = (params.get("category") or "").strip()
        actor = (params.get("actor") or "").strip()
        export = params.get("export") == "1"

        reveal = is_admin_user(request.user, request)
        scope = AdminAction.objects.all()
        if target:
            # A person's history is keyed by their email; letting a non-super
            # caller filter on it would confirm addresses the rows mask.
            if not reveal and target.startswith(USER_TARGET):
                scope = scope.none()
            scope = scope.filter(target=target)

        # The chips count over search + actor but not category, so each chip
        # says what clicking it would show.
        searched = self._search(scope, q, reveal=reveal)
        if actor:
            searched = searched.filter(actor__in=self._actors_matching(scope, actor, reveal=reveal))
        base = searched.filter(action__in=actions_in(category)) if category in CATEGORIES else searched

        if export:
            rows = list(base.order_by("-id")[: self.EXPORT_LIMIT + 1])
            return Response(
                {
                    "truncated": len(rows) > self.EXPORT_LIMIT,
                    "actions": [_serialize(r, reveal=reveal) for r in rows[: self.EXPORT_LIMIT]],
                }
            )

        page = base.filter(id__lt=before) if before is not None else base
        # Keyset on the primary key, newest first. `id` is the true insertion
        # order of an append-only table, so `-id` is a tie-free stand-in for the
        # model's `-at` default (which two rows can share) and pairs with the
        # `id__lt` cursor above. One extra row is the "is there more" sentinel:
        # kept out of the payload, it makes "did the page fill" a real has-more
        # without a count query.
        rows = list(page.order_by("-id")[: self.LIMIT + 1])
        has_more = len(rows) > self.LIMIT
        rows = rows[: self.LIMIT]

        first = before is None
        return Response(
            {
                # First-page figures only. A "load older" request (one with a
                # cursor) already has them and discards ours, so don't pay for
                # the counts on every page of a table built to grow.
                "total": base.count() if first else None,
                "summary": self._summary(scope, searched, params, reveal=reveal) if first else None,
                "limit": self.LIMIT,
                "next_cursor": rows[-1].id if has_more else None,
                "actions": [_serialize(r, reveal=reveal) for r in rows],
            }
        )

    @staticmethod
    def _search(qs, q: str, *, reveal: bool):
        if not q:
            return qs
        labels = [a for a, label in AdminAction.Action.choices if q.lower() in label.lower()]
        match = Q(detail__icontains=q) | Q(action__in=labels) | Q(action__icontains=q)
        if reveal:
            match |= Q(target__icontains=q) | Q(actor__icontains=q)
        else:
            # The rows mask actors and user targets for this caller; a substring
            # search over the raw values would let them probe the addresses.
            match |= Q(target__icontains=q) & ~Q(target__startswith=USER_TARGET)
        return qs.filter(match)

    @staticmethod
    def _actors_matching(scope, actor: str, *, reveal: bool) -> list[str]:
        """The raw actor values an ``?actor=`` names. A non-super caller only
        ever saw masked actors, so theirs is matched against the mask — the
        filter works without the raw address reaching (or being probed by) them."""
        if reveal:
            return [actor]
        known = scope.values_list("actor", flat=True).distinct()
        return [a for a in known if a and mask_email(a) == actor]

    def _summary(self, scope, searched, params, *, reveal: bool) -> dict:
        now = timezone.now()
        day_start = _day_start(params.get("day_start"), now)

        by_category = dict.fromkeys(CATEGORIES, 0)
        for row in searched.values("action").annotate(n=Count("id")).order_by():
            by_category[category_of(row["action"])] += row["n"]

        today = scope.filter(at__gte=day_start).aggregate(
            n=Count("id"), loud=Count("id", filter=Q(action__in=READER_FACING))
        )

        actors: dict[str, int] = {}
        for row in scope.values("actor").annotate(n=Count("id")).order_by():
            if not row["actor"]:
                continue  # a DEBUG tokenless request: nobody to filter on
            key = row["actor"] if reveal else mask_email(row["actor"])
            actors[key] = actors.get(key, 0) + row["n"]

        def latest(action):
            row = scope.filter(action=action).order_by("-id").first()
            return _serialize(row, reveal=reveal) if row else None

        return {
            "all": scope.count(),
            "by_category": by_category,
            "today": today["n"],
            "today_reader_facing": today["loud"],
            "week": scope.filter(at__gte=day_start - timedelta(days=6)).count(),
            "actors": [
                {"actor": a, "count": n}
                for a, n in sorted(actors.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            "last_go_live": latest(AdminAction.Action.LANGUAGE_GO_LIVE),
            "last_publish": latest(AdminAction.Action.CONTENT_PUBLISH),
        }
