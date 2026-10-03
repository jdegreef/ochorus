"""The reader-facing feedback endpoint: one signed-in POST that files a
:class:`~feedback.models.Feedback` row.

Signed-in only. ``SupabaseJWTAuthentication`` resolves a missing or bad token to
an anonymous request (never a 500), so ``IsAuthenticated`` is what actually
requires a real account here. Throttled per account so a script can't flood the
queue.
"""

from __future__ import annotations

import re
from urllib.parse import unquote_plus, urlsplit, urlunsplit

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminGrant, UserProfile
from accounts.permissions import _verified_email, is_admin_user
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


def submitter_role(request) -> str:
    """A snapshot label of the submitter's standing, for the queue's trust badge.

    Super admin wins; otherwise the strongest role they hold (``language_admin``
    preferred), or a bare ``"admin"`` for a raw-capability grant, or ``""`` for an
    ordinary reader.
    """
    if is_admin_user(request.user, request):
        return "super_admin"
    # Only a VERIFIED address earns a grant's badge — the bar every grant check
    # holds (``_verified_email``); an unverified claim of a granted address is
    # just a reader.
    verified = _verified_email(request.user, request)
    if not verified:
        return ""
    grants = list(AdminGrant.objects.filter(email=verified))
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


#: Query keys that carry a credential, matched whole (so ``error_code`` or
#: ``author`` survive). Supabase's implicit flow puts the session in the
#: fragment (``#access_token=…&refresh_token=…``) and its PKCE / OTP flows put
#: ``code`` / ``token_hash`` in the query; a reader who opens feedback straight
#: after a magic-link sign-in would otherwise file their live session with it.
_SECRET_KEY = re.compile(
    r"(\w+_)?token(_hash|_type)?|code|otp|password|secret|api_?key", re.IGNORECASE
)


def _scrub_url(url: str) -> str:
    """Drop credential-shaped query parameters and any ``key=value`` fragment,
    keeping every other parameter exactly as spelled. A plain ``#section``
    anchor stays: the reader app sets those itself (author pages, /biographies)
    and they say where the reader was. Returns "" for a URL that won't parse.
    Only ever shortens its input."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    kept = [
        seg
        for seg in parts.query.split("&")
        if not _SECRET_KEY.fullmatch(unquote_plus(seg.split("=", 1)[0]))
    ]
    fragment = "" if "=" in parts.fragment else parts.fragment
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(kept), fragment))


def _clip_url(value, limit: int) -> str:
    """Like _clip, but only keep an http(s) URL — the admin queue renders this as
    a clickable link, so a ``javascript:``/``data:`` scheme would be stored XSS —
    and scrub any credential out of it first (see :func:`_scrub_url`)."""
    url = _scrub_url(_clip(value, limit))
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
            submitter_role=submitter_role(request),
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
