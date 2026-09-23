"""The admin side of reader feedback: a queue to read submissions and a triage
endpoint to move one along.

Both gate on the ``feedback`` capability (``RequireCapability`` via ``@requires``).
The triage write is audited like every admin mutation — a new
``AdminAction.Action.FEEDBACK_TRIAGE`` value, recorded by the ``AdminAudited``
mixin. Feedback is not language-scoped yet: a later phase filters the queue to a
language admin's languages; today ``feedback`` is a flat capability the founder
(and anyone explicitly granted it) holds.
"""

from __future__ import annotations

from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires
from library.audit import AdminAudited
from library.models import AdminAction

from .models import TRIAGE_STATUSES, Feedback, FeedbackCategory, FeedbackStatus

#: Cap a single queue read. The founder works the backlog down; a page far above
#: this would be a table dump, not a worklist.
PAGE_SIZE = 200


def _serialize(item: Feedback) -> dict:
    return {
        "id": item.id,
        "category": item.category,
        "body": item.body,
        "source": item.source,
        "status": item.status,
        "submitter_email": item.submitter_email,
        "submitter_role": item.submitter_role,
        "page_url": item.page_url,
        "content_kind": item.content_kind,
        "content_slug": item.content_slug,
        "content_language": item.content_language,
        "chapter_ref": item.chapter_ref,
        "ui_locale": item.ui_locale,
        "assignee_email": item.assignee_email,
        "admin_note": item.admin_note,
        "duplicate_of": item.duplicate_of_id,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


@requires(AdminCapability.FEEDBACK, verb=AdminVerb.VIEW)
class AdminFeedbackListView(APIView):
    """GET the feedback queue — newest first, filterable by status and category,
    with per-status counts for the filter chips."""

    def get(self, request):
        q = request.query_params
        status = q.get("status") or ""
        category = q.get("category") or ""

        qs = Feedback.objects.all()
        if status in FeedbackStatus.values:
            qs = qs.filter(status=status)
        if category in FeedbackCategory.values:
            qs = qs.filter(category=category)

        items = [_serialize(f) for f in qs[:PAGE_SIZE]]
        # Counts are global (the chips show the whole backlog per status), so a
        # single grouped query rather than the filtered `qs`.
        counts = dict.fromkeys(FeedbackStatus.values, 0)
        for row in Feedback.objects.values("status").annotate(n=Count("id")):
            if row["status"] in counts:
                counts[row["status"]] = row["n"]
        return Response({"items": items, "counts": counts, "total": sum(counts.values())})


@requires(AdminCapability.FEEDBACK, verbs={"POST": AdminVerb.ACT})
class AdminFeedbackDetailView(AdminAudited, APIView):
    """POST a triage decision for one item: change its status, assign it, note
    it, or mark it a duplicate. Only the fields present in the body change."""

    audit_action = AdminAction.Action.FEEDBACK_TRIAGE

    def audit_entry(self, request, response):
        data = response.data
        return f"feedback:{data['id']}", {"status": data["status"]}

    def post(self, request, pk: int):
        try:
            item = Feedback.objects.get(pk=pk)
        except Feedback.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        data = request.data if isinstance(request.data, dict) else {}

        if "status" in data:
            status = str(data.get("status") or "").strip()
            if status not in TRIAGE_STATUSES:
                return Response({"detail": "Unknown status."}, status=400)
            item.status = status

        if "assignee_email" in data:
            item.assignee_email = str(data.get("assignee_email") or "").strip().lower()[:254]

        if "admin_note" in data:
            item.admin_note = str(data.get("admin_note") or "").strip()

        if "duplicate_of" in data:
            dup = data.get("duplicate_of")
            if dup in (None, "", 0):
                item.duplicate_of = None
            elif (
                isinstance(dup, int)
                and not isinstance(dup, bool)  # bool is an int subclass; reject `true`
                and dup != item.pk
                and Feedback.objects.filter(pk=dup).exists()
            ):
                item.duplicate_of_id = dup
            else:
                return Response({"detail": "Invalid duplicate_of."}, status=400)

        item.save()
        return Response(_serialize(item))
