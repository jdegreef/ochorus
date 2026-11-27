"""Admin dashboard API — "My work": what is waiting on the person looking.

With one admin, the queues were the to-do list. With two or more, the useful
question is "what is mine?": feedback assigned to me, review decisions waiting
for my confirmation, my own proposals waiting for someone else's, and the
emails I started and haven't sent. This gathers those from the tables that
already hold them — nothing new is stored, and every item links to the page
where it is worked.

Read-only, and open to anyone with any admin access (``HasAnyAdminAccess``):
each section is filtered to what the viewer's grants open, so a contributor
simply sees fewer sections.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import HasAnyAdminAccess, allowed_languages, has_capability

from ..audit import actor_email
from ..models import AdminAction, ReviewOutcome

#: Feedback still being worked: not done, declined or a duplicate.
OPEN_FEEDBACK = ("new", "triaging", "planned", "in_progress")
#: Per section — "My work" is a shortlist, the queue pages hold the rest.
LIMIT = 25


class AdminMyWorkView(APIView):
    permission_classes = [HasAnyAdminAccess]

    def get(self, request):
        me = actor_email(request)
        sections = [
            self._feedback(request, me),
            self._to_confirm(request, me),
            self._my_proposals(request, me),
            self._my_emails(request, me),
        ]
        sections = [s for s in sections if s is not None]
        return Response(
            {
                "me": me,
                "sections": sections,
                "total": sum(len(s["items"]) for s in sections),
            }
        )

    @staticmethod
    def _feedback(request, me):
        if not me or not has_capability(
            request, AdminCapability.FEEDBACK, AdminVerb.VIEW
        ):
            return None
        from feedback.models import Feedback

        rows = Feedback.objects.filter(
            assignee_email__iexact=me, status__in=OPEN_FEEDBACK
        ).order_by("created_at")[:LIMIT]
        return {
            "key": "feedback",
            "title": "Feedback assigned to you",
            "empty": "No feedback is assigned to you.",
            "href": "/admin/feedback",
            "items": [
                {
                    "id": f"feedback:{f.pk}",
                    "label": (f.body or f.selected_text or "Feedback")[:140],
                    "meta": " · ".join(
                        x
                        for x in (
                            f.get_category_display(),
                            f.content_language,
                            f.get_status_display(),
                        )
                        if x
                    ),
                    "at": f.created_at,
                    "href": "/admin/feedback",
                }
                for f in rows
            ],
        }

    @staticmethod
    def _to_confirm(request, me):
        """Provisional review decisions someone ELSE proposed, in languages the
        viewer may approve: the maker-checker's second half."""
        if not has_capability(request, AdminCapability.REVIEW, AdminVerb.APPROVE):
            return None
        langs = allowed_languages(request, AdminCapability.REVIEW, AdminVerb.APPROVE)
        qs = ReviewOutcome.objects.filter(confirmed_at__isnull=True)
        if langs is not None:
            qs = qs.filter(language__in=langs)
        if me:
            qs = qs.exclude(reviewer__iexact=me)
        rows = qs.order_by("decided_at")[:LIMIT]
        return {
            "key": "confirm",
            "title": "Review decisions waiting for your confirmation",
            "empty": "Nothing is waiting for you to confirm.",
            "href": "/admin/review",
            "items": [
                {
                    "id": f"review:{r.kind}:{r.slug}:{r.language}",
                    "label": f"{r.slug} ({r.language}): {r.get_outcome_display().lower()}",
                    "meta": f"proposed by {r.reviewer or 'a reviewer'}",
                    "at": r.decided_at,
                    "href": "/admin/review",
                }
                for r in rows
            ],
        }

    @staticmethod
    def _my_proposals(request, me):
        """The viewer's own provisional decisions, still waiting on an approver."""
        if not me or not has_capability(request, AdminCapability.REVIEW, AdminVerb.ACT):
            return None
        rows = ReviewOutcome.objects.filter(
            confirmed_at__isnull=True, reviewer__iexact=me
        ).order_by("decided_at")[:LIMIT]
        if not rows:
            return None
        return {
            "key": "proposed",
            "title": "Your review decisions waiting on an approver",
            "empty": "",
            "href": "/admin/review",
            "items": [
                {
                    "id": f"proposed:{r.kind}:{r.slug}:{r.language}",
                    "label": f"{r.slug} ({r.language}): {r.get_outcome_display().lower()}",
                    "meta": "waiting for confirmation",
                    "at": r.decided_at,
                    "href": "/admin/review",
                }
                for r in rows
            ],
        }

    @staticmethod
    def _my_emails(request, me):
        """Broadcasts the viewer created that haven't finished going out."""
        if not me or not has_capability(request, AdminCapability.EMAIL, AdminVerb.VIEW):
            return None
        from emails.models import Broadcast, BroadcastStatus

        mine = {
            t.removeprefix("broadcast:")
            for t in AdminAction.objects.filter(
                action=AdminAction.Action.BROADCAST_CREATE, actor__iexact=me
            ).values_list("target", flat=True)
        }
        ids = [int(x) for x in mine if x.isdigit()]
        rows = Broadcast.objects.filter(
            pk__in=ids,
            status__in=[
                BroadcastStatus.DRAFT,
                BroadcastStatus.SCHEDULED,
                BroadcastStatus.PAUSED,
            ],
        ).order_by("-updated_at")[:LIMIT]
        return {
            "key": "emails",
            "title": "Your emails not sent yet",
            "empty": "You have no unsent emails.",
            "href": "/admin/emails/compose",
            "items": [
                {
                    "id": f"broadcast:{b.pk}",
                    "label": b.name or "Untitled email",
                    "meta": b.get_status_display()
                    + (
                        f" for {b.scheduled_at:%d %b %H:%M} UTC"
                        if b.scheduled_at and b.status == BroadcastStatus.SCHEDULED
                        else ""
                    ),
                    "at": b.updated_at,
                    "href": f"/admin/emails/compose?id={b.pk}",
                }
                for b in rows
            ],
        }
