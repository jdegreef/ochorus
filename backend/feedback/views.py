"""The reader-facing feedback endpoint: one signed-in POST that files a
:class:`~feedback.models.Feedback` row.

Signed-in only. ``SupabaseJWTAuthentication`` resolves a missing or bad token to
an anonymous request (never a 500), so ``IsAuthenticated`` is what actually
requires a real account here. Throttled per account so a script can't flood the
queue.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminGrant, UserProfile
from accounts.permissions import is_admin_user
from common.throttling import ScopedCacheThrottle

from .models import Feedback, FeedbackCategory, FeedbackSource

#: Lower/upper bounds on the body. A blank or one-word "feedback" is noise; the
#: cap stops a single row from being used as unbounded storage.
MIN_BODY = 10
MAX_BODY = 5000


class _FeedbackThrottle(ScopedCacheThrottle):
    """Bounds the one write on this module. Feedback is occasional — a reader
    files a handful a day at most — so this sits far above real use and only
    catches a script hammering the queue. ``UserRateThrottle`` keys on the
    account (every submitter is signed in), so it is a genuine per-person cap.
    """

    scope = "feedback"


def _profile(request) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"supabase_uid": request.user.username, "email": request.user.email},
    )
    return profile


def submitter_role(request, email: str) -> str:
    """A snapshot label of the submitter's standing, for the queue's trust badge.

    Super admin wins; otherwise the strongest role they hold (``language_admin``
    preferred), or a bare ``"admin"`` for a raw-capability grant, or ``""`` for an
    ordinary reader.
    """
    if is_admin_user(request.user, request):
        return "super_admin"
    grants = list(AdminGrant.objects.filter(email=email))
    labels = {g.role_label for g in grants if g.role_label}
    if "language_admin" in labels:
        return "language_admin"
    if labels:
        return sorted(labels)[0]
    if grants:
        return "admin"
    return ""


def _clip(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _anchor_block(value) -> int | None:
    """A non-negative block index, or None. Rejects bools (an int subclass) and
    anything non-integral or negative."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _clip_url(value, limit: int) -> str:
    """Like _clip, but only keep an http(s) URL — the admin queue renders this as
    a clickable link, so a ``javascript:``/``data:`` scheme would be stored XSS."""
    url = _clip(value, limit)
    return url if urlsplit(url).scheme in ("http", "https") else ""


class FeedbackView(APIView):
    """POST a suggestion. The client sends the body + category and whatever page
    context it can resolve; the server stamps the submitter and their role."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [_FeedbackThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        body = str(data.get("body") or "").strip()
        if len(body) < MIN_BODY:
            return Response(
                {"detail": f"Please describe your feedback (at least {MIN_BODY} characters)."},
                status=400,
            )
        body = body[:MAX_BODY]

        category = str(data.get("category") or "").strip()
        if category not in FeedbackCategory.values:
            category = FeedbackCategory.OTHER

        source = str(data.get("source") or "").strip()
        if source not in FeedbackSource.values:
            source = FeedbackSource.MENU

        profile = _profile(request)
        email = (profile.email or request.user.email or "").strip().lower()

        feedback = Feedback.objects.create(
            submitter=profile,
            submitter_email=email,
            submitter_role=submitter_role(request, email),
            category=category,
            body=body,
            source=source,
            page_url=_clip_url(data.get("page_url"), 2000),
            content_kind=_clip(data.get("content_kind"), 20),
            content_slug=_clip(data.get("content_slug"), 200),
            content_language=_clip(data.get("content_language"), 20),
            chapter_ref=_clip(data.get("chapter_ref"), 100),
            ui_locale=_clip(data.get("ui_locale"), 20),
            selected_text=_clip(data.get("selected_text"), 2000),
            suggested_text=_clip(data.get("suggested_text"), 2000),
            anchor_block=_anchor_block(data.get("anchor_block")),
        )
        return Response({"id": feedback.id, "ok": True}, status=201)
