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


class AdminActivityView(APIView):
    """Recent admin actions, newest first.

    A window rather than the whole table, and a hard cap rather than a
    caller-chosen page size: this is a "what happened lately" screen, and an
    append-only log is exactly the thing that grows without anyone noticing.
    """

    permission_classes = [IsAdminEmail]

    #: Enough to cover a working session and a couple before it.
    LIMIT = 100

    def get(self, request):
        rows = AdminAction.objects.all()[: self.LIMIT]
        return Response(
            {
                "total": AdminAction.objects.count(),
                "limit": self.LIMIT,
                "actions": [
                    {
                        "action": r.action,
                        # The human phrasing lives with the choices, so the label
                        # a reader sees and the value stored cannot drift.
                        "label": AdminAction.Action(r.action).label,
                        "actor": r.actor,
                        "target": r.target,
                        "detail": r.detail,
                        "at": r.at.isoformat(),
                    }
                    for r in rows
                ],
            }
        )
