"""The admin side of reader feedback: a queue to read submissions and a triage
endpoint to move one along.

Both gate on the ``feedback`` capability (``RequireCapability`` via ``@requires``).
The triage write is audited like every admin mutation — a new
``AdminAction.Action.FEEDBACK_TRIAGE`` value, recorded by the ``AdminAudited``
mixin.

The queue is **language-scoped**, the same per-row way the review queue is: a
super admin (or a ``*`` grant) sees everything; a language admin sees only
feedback in their languages, and language-less feedback (a general idea from the
floating button, with no ``content_language``) stays with the super admins. The
triage write refuses a row outside the caller's languages.
"""

from __future__ import annotations

from collections import Counter

from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import allowed_languages, requires
from library.audit import AdminAudited
from library.models import AdminAction

from .models import (
    TRIAGE_STATUSES,
    Feedback,
    FeedbackCategory,
    FeedbackSource,
    FeedbackStatus,
)

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
        "selected_text": item.selected_text,
        "suggested_text": item.suggested_text,
        "anchor_block": item.anchor_block,
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
        source = q.get("source") or ""

        # Scope: super/`*` → everything; a language admin → their languages only,
        # which also drops language-less items (their content_language is "" and
        # never in the set), leaving those to the super admins.
        allowed = allowed_languages(request, AdminCapability.FEEDBACK, AdminVerb.VIEW)
        scoped = Feedback.objects.all()
        if allowed is not None:
            scoped = scoped.filter(content_language__in=allowed)

        qs = scoped
        if status in FeedbackStatus.values:
            qs = qs.filter(status=status)
        if category in FeedbackCategory.values:
            qs = qs.filter(category=category)
        if source in FeedbackSource.values:
            qs = qs.filter(source=source)

        items = [_serialize(f) for f in qs[:PAGE_SIZE]]
        # A dedup nudge: how many other shown items flag the same passage, so ten
        # reports of one broken paragraph read as a cluster rather than ten rows.
        clusters = Counter(
            (i["content_kind"], i["content_slug"], i["chapter_ref"])
            for i in items
            if i["content_slug"]
        )
        for i in items:
            key = (i["content_kind"], i["content_slug"], i["chapter_ref"])
            i["similar"] = clusters[key] - 1 if i["content_slug"] else 0

        # Counts (for the status chips) reflect the caller's scope, not the whole
        # table — a grouped query over the scoped set.
        counts = dict.fromkeys(FeedbackStatus.values, 0)
        for row in scoped.values("status").annotate(n=Count("id")):
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

        # Refuse a row outside the caller's languages (a language admin can't
        # triage another language's — or a language-less — item).
        allowed = allowed_languages(request, AdminCapability.FEEDBACK, AdminVerb.ACT)
        if allowed is not None and item.content_language not in allowed:
            return Response({"detail": "Not in your languages."}, status=403)

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
