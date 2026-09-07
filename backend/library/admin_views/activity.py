"""Admin dashboard API — the record of what has been done here.

Reads ``AdminAction``. Its own module rather than a section of the content
audit: that page answers "is the library in good shape", and this one answers
"who changed it". Filing them together would put an administrator's name in a
report about chapter quality.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import AdminAction


def _serialize(row: AdminAction) -> dict:
    return {
        "action": row.action,
        # The human phrasing lives with the choices, so the label a reader sees
        # and the value stored cannot drift.
        "label": AdminAction.Action(row.action).label,
        "actor": row.actor,
        "target": row.target,
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
    """

    permission_classes = [IsAdminEmail]

    #: Enough to cover a working session and a couple before it.
    LIMIT = 100

    def get(self, request):
        target = (request.query_params.get("target") or "").strip()
        before = _parse_cursor(request.query_params.get("before"))

        base = AdminAction.objects.all()
        if target:
            base = base.filter(target=target)

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

        return Response(
            {
                # A first-page figure only. A "load older" request (one with a
                # cursor) already has the total and discards ours, so don't pay
                # for a full count on every page of a table built to grow.
                "total": None if before is not None else base.count(),
                "limit": self.LIMIT,
                "next_cursor": rows[-1].id if has_more else None,
                "actions": [_serialize(r) for r in rows],
            }
        )
