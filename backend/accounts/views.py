import logging
from datetime import timedelta

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _database_ok() -> bool:
    """Can this instance actually reach its database?

    A cheap ``SELECT 1`` — no table, no row, no ORM. It exists because the rest
    of this endpoint answers "ok" from files alone (``content_version`` walks the
    baked digest, ``commit`` is an env var), so without it a container whose
    Postgres is down, whose connection pool is exhausted, or whose persistent
    ``conn_max_age`` connections have gone stale reports perfectly healthy while
    every real endpoint 500s — and Render, seeing green, keeps routing to it and
    never restarts it. This is the one dependency worth probing on the path
    Render's health check hits.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:  # noqa: BLE001 — a probe converts ANY db error into 503, never a 500.
        logger.warning("Health check database probe failed", exc_info=True)
        return False


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe used by Render's health check.

    Returns 200 only when this instance can reach its database (a shallow
    ``SELECT 1``, see ``_database_ok``); a database it cannot reach is a 503, so
    Render and any uptime monitor see the outage instead of a green file-walk.

    Also publishes what this instance is serving, for the web build's benefit.
    The reader is a static site prerendered against this API, and a content
    commit deploys both services at once — so the build needs a way to tell "the
    API already has my content" from "the API is still on the previous release",
    rather than baking the old content into pages meant to show the new. These
    fields are file/env-derived, so they stay in the body even on a 503 (the web
    build's poller treats any non-200 as "not ready yet" and simply waits —
    exactly the right thing against an API whose database is down).

    ``content_version`` is the field that question is answered with; ``commit``
    is informational (which release is live, for a human looking at the
    endpoint). It deliberately isn't the comparison: only the API's rootDir is
    backend/, so a frontend-only commit deploys the web service alone and this
    instance legitimately keeps reporting an older SHA — a build waiting on THAT
    would wait for a deploy that is never coming.
    """
    from library.content_fixtures import content_digest

    db_ok = _database_ok()
    return Response(
        {
            "status": "ok" if db_ok else "error",
            "service": "ochorus",
            "commit": settings.RELEASE_COMMIT,
            "content_version": content_digest(),
            "database": "ok" if db_ok else "error",
        },
        status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class MeView(APIView):
    """Read/update the authenticated user's profile (reading preferences)."""

    permission_classes = [IsAuthenticated]

    def _profile(self, request):
        from .models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"supabase_uid": request.user.username, "email": request.user.email},
        )
        return profile

    def _serialize(self, profile) -> dict:
        return {
            "email": profile.email,
            "display_name": profile.display_name,
            "locale": profile.locale,
            "theme": profile.theme,
            "font_scale": profile.font_scale,
            "tts_rate": profile.tts_rate,
            "tts_voice_uri": profile.tts_voice_uri,
            "timezone": profile.timezone,
        }

    def get(self, request):
        from .models import AdminGrant
        from .permissions import _verified_email, is_admin_user

        data = self._serialize(self._profile(request))
        is_super = is_admin_user(request.user, request)
        data["is_admin"] = is_super
        data["is_super_admin"] = is_super
        # Scoped grants drive the frontend's capability-aware nav. A super admin
        # holds no grant rows (their power is the allowlist), so report the full
        # set so their UI shows everything; everyone else gets exactly their grants.
        if is_super:
            data["roles"] = ["super_admin"]
            data["scopes"] = "all"
        else:
            email = _verified_email(request.user, request)
            scopes = AdminGrant.scopes_for(email) if email else []
            data["scopes"] = scopes
            data["roles"] = sorted({s["role"] for s in scopes if s["role"]})
        return Response(data)

    def patch(self, request):
        profile = self._profile(request)
        data = request.data
        updated = []

        if isinstance(data.get("display_name"), str):
            # Trimmed; empty string is allowed (clears the name back to the email).
            profile.display_name = data["display_name"].strip()[:120]
            updated.append("display_name")
        if isinstance(data.get("locale"), str) and data["locale"]:
            profile.locale = data["locale"][:10]
            updated.append("locale")
        if data.get("theme") in ("paper", "light", "dark", "sepia", "system"):
            profile.theme = data["theme"]
            updated.append("theme")
        try:
            if data.get("font_scale") is not None:
                profile.font_scale = max(0.8, min(1.6, float(data["font_scale"])))
                updated.append("font_scale")
        except (TypeError, ValueError):
            pass
        try:
            if data.get("tts_rate") is not None:
                profile.tts_rate = max(0.5, min(3.0, float(data["tts_rate"])))
                updated.append("tts_rate")
        except (TypeError, ValueError):
            pass
        if isinstance(data.get("tts_voice_uri"), str):
            profile.tts_voice_uri = data["tts_voice_uri"][:255]
            updated.append("tts_voice_uri")
        # An IANA timezone string (e.g. "Europe/London"). Stored verbatim,
        # length-capped; the admin analytics derive an approximate country from
        # it. Empty string is allowed (clears it). Not validated against the tz
        # database here — an unrecognised zone simply won't map to a country.
        if isinstance(data.get("timezone"), str):
            profile.timezone = data["timezone"].strip()[:40]
            updated.append("timezone")

        if updated:
            profile.save(update_fields=[*updated, "updated_at"])
        return Response(self._serialize(profile))

    def delete(self, request):
        """Delete the reader's account data: the profile and, via CASCADE, all
        their reading progress, highlights/notes and favorites. The Supabase
        auth identity itself is managed by Supabase; a later sign-in simply
        starts a fresh, empty profile."""
        self._profile(request).delete()
        return Response(status=204)


class SignupSourceView(APIView):
    """Attribute an account to the logged-out sign-up band that drove it, for
    sign-ups that can't carry the arm in the JWT.

    Email/magic-link ride ``user_metadata.signup_variant`` (set at ``signUp``,
    recorded create-only in ``authentication.token_signup_variant``) — that
    survives the email-confirmation round-trip, even on another device. But
    Supabase ``signInWithOAuth`` takes no ``user_metadata``, so a Google sign-up
    reaches Django untagged. The client posts the stored arm here right after a
    NEW user's first sign-in.

    Create-only AND fresh-only: it writes the arm only when the profile has none
    yet *and* was created within the last hour, so a returning reader carrying a
    stale stored arm from a past visit can never be mislabelled (the client
    applies the same new-account gate; this is the backstop). It is a harmless
    no-op for an email/magic-link account whose tag the JWT path already set.
    """

    permission_classes = [IsAuthenticated]

    #: A profile older than this at POST time is treated as a returning reader,
    #: never a fresh sign-up — so its blank arm is left blank.
    FRESH = timedelta(hours=1)

    def post(self, request):
        from django.utils import timezone

        from .models import SIGNUP_VARIANTS, UserProfile

        variant = request.data.get("signup_variant")
        if variant not in SIGNUP_VARIANTS:
            # Unknown/missing arm — accept the request but record nothing, so a
            # stray client can't write junk into the analytics vocabulary.
            return Response(status=204)

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"supabase_uid": request.user.username, "email": request.user.email},
        )
        if profile.signup_variant == "" and timezone.now() - profile.created_at <= self.FRESH:
            profile.signup_variant = variant
            profile.save(update_fields=["signup_variant", "updated_at"])
        return Response(status=204)
