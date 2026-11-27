"""Admin dashboard API — the "Start here" steps for someone new to the console.

A new admin (Maika, the first Content admin, was the reason) lands on a
dashboard of counts with no sense of where to begin. The dashboard shows them
a short checklist of first steps — one per area their grants open — and each
step ticks itself when the append-only ``AdminAction`` log shows they have
done it. Nothing new is stored: the log already says who did what.

Read-only, open to anyone with admin access (``HasAnyAdminAccess``). A super
admin gets no steps: they built the place.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability as C
from accounts.models import AdminVerb as V
from accounts.permissions import HasAnyAdminAccess, has_capability, is_admin_user

from ..audit import actor_email
from ..models import AdminAction

A = AdminAction.Action

#: (key, capability, verb, title, why, href, the log actions that complete it).
#: In the order a newcomer should take them.
STEPS: list[tuple[str, str, str, str, str, str, tuple[str, ...]]] = [
    (
        "review",
        C.REVIEW,
        V.ACT,
        "Record your first review decision",
        "Open the review queue, read a translation against its source, and approve it or mark what needs work.",
        "/admin/review",
        (A.REVIEW_DECIDE,),
    ),
    (
        "feedback",
        C.FEEDBACK,
        V.ACT,
        "Triage one piece of reader feedback",
        "Give it a status, take it, or turn a chapter suggestion into a fix job.",
        "/admin/feedback",
        (A.FEEDBACK_TRIAGE,),
    ),
    (
        "fix",
        C.CONTENT_EDIT,
        V.SUGGEST,
        "File a fix from a book page",
        "On any book's admin page, use Fix title or Flag text on a chapter. A worker turns it into a reviewed change.",
        "/admin/books",
        (A.CONTENT_EDIT_JOB,),
    ),
    (
        "email",
        C.EMAIL,
        V.APPROVE,
        "Send yourself a test email",
        "Open a draft in Compose and use Send test to me, so you know how an email looks before anyone else gets it.",
        "/admin/emails/compose",
        (A.BROADCAST_TEST,),
    ),
    (
        "audit",
        C.AUDIT,
        V.ACT,
        "Settle one content-audit finding",
        "Fix it, send it to the fix queue, or accept it as known.",
        "/admin/audit",
        (A.AUDIT_DISMISS, A.CONTENT_EDIT_JOB),
    ),
]


class AdminOnboardingView(APIView):
    permission_classes = [HasAnyAdminAccess]

    def get(self, request):
        if is_admin_user(request.user, request):
            return Response({"steps": []})
        me = actor_email(request)
        done = (
            set(
                AdminAction.objects.filter(actor__iexact=me)
                .values_list("action", flat=True)
                .distinct()
            )
            if me
            else set()
        )
        steps = [
            {
                "key": key,
                "title": title,
                "why": why,
                "href": href,
                "done": any(a in done for a in actions),
            }
            for key, cap, verb, title, why, href, actions in STEPS
            if has_capability(request, cap, verb)
        ]
        return Response({"steps": steps})
