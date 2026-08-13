"""DRF authentication that trusts Supabase-issued JWTs.

The frontend logs users in via Supabase and sends the resulting access token as
``Authorization: Bearer <jwt>``. We validate the signature against either:

* the project's JWKS endpoint (asymmetric ES256/RS256 keys — the modern default), or
* a shared HS256 secret (the legacy "JWT Secret"),

whichever matches the token's ``alg`` header and is configured. On success we map
the Supabase user (``sub`` claim, a UUID) to a Django User + UserProfile.
"""

from __future__ import annotations

import logging

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

logger = logging.getLogger(__name__)


def _claim_true(value) -> bool:
    """A JWT boolean claim, tolerant of the string form some providers emit."""
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def token_email_is_verified(payload) -> bool:
    """True only if the Supabase token positively asserts the email is verified.

    Supabase carries this in ``user_metadata.email_verified`` (and, on newer
    projects, a top-level ``email_verified``). Absent or false → not verified, so
    the address must NOT be trusted for authorization: with email confirmation
    disabled anyone could sign up claiming the admin's address, and the admin
    allowlist keys on the address alone (see ``accounts.permissions``).
    """
    if not isinstance(payload, dict):
        return False
    if _claim_true(payload.get("email_verified")):
        return True
    meta = payload.get("user_metadata")
    return isinstance(meta, dict) and _claim_true(meta.get("email_verified"))


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"
    _jwks_client: jwt.PyJWKClient | None = None

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None  # let other authenticators (or AnonymousUser) handle it
        if len(header) != 2:
            return None  # malformed header — treat as anonymous, not a hard 401

        token = header[1].decode()
        try:
            payload = self._decode(token)
            user = self._get_or_create_user(payload)
        except exceptions.AuthenticationFailed as exc:
            # An expired or invalid token must NOT break public (AllowAny)
            # endpoints. DRF runs authentication before the permission check, so
            # raising here 401s the whole request — meaning a signed-in user whose
            # Supabase token has expired gets a 500 on every book/author/chapter
            # page (the frontend load throws the 401). Treat a bad token as
            # anonymous instead; protected endpoints still return 401 via
            # IsAuthenticated on the resulting AnonymousUser.
            #
            # Log the reason (never the token) so a misconfiguration — a wrong
            # SUPABASE_URL, an unreachable JWKS, an audience mismatch — is visible
            # instead of silently 401ing every authenticated request. Routine
            # expiry is noise, so it's logged quietly.
            msg = str(exc)
            if "expired" in msg.lower():
                logger.info("Ignoring expired Supabase token")
            else:
                logger.warning("Rejected Supabase token: %s", msg)
            return None
        return (user, payload)

    def authenticate_header(self, request):
        return self.keyword

    # -- internals -------------------------------------------------------------

    def _decode(self, token: str) -> dict:
        try:
            alg = jwt.get_unverified_header(token).get("alg", "")
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f"Malformed token: {exc}") from exc

        audience = settings.SUPABASE_JWT_AUDIENCE or None
        try:
            if alg.startswith("HS"):
                if not settings.SUPABASE_JWT_SECRET:
                    raise exceptions.AuthenticationFailed(
                        "Received an HS-signed token but SUPABASE_JWT_SECRET is not set."
                    )
                key = settings.SUPABASE_JWT_SECRET
            else:
                key = self._jwks().get_signing_key_from_jwt(token).key
            return jwt.decode(token, key, algorithms=[alg], audience=audience)
        except exceptions.AuthenticationFailed:
            raise
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired") from None
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}") from exc

    def _jwks(self) -> jwt.PyJWKClient:
        if not settings.SUPABASE_URL:
            raise exceptions.AuthenticationFailed(
                "SUPABASE_URL is not configured; cannot validate asymmetric tokens."
            )
        if SupabaseJWTAuthentication._jwks_client is None:
            url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            SupabaseJWTAuthentication._jwks_client = jwt.PyJWKClient(url, cache_keys=True)
        return SupabaseJWTAuthentication._jwks_client

    def _get_or_create_user(self, payload: dict):
        sub = payload.get("sub")
        if not sub:
            raise exceptions.AuthenticationFailed("Token is missing the 'sub' claim.")

        email = payload.get("email") or ""
        user, _ = User.objects.get_or_create(username=sub, defaults={"email": email})
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])

        # Lazy import to avoid app-loading order issues.
        from .models import UserProfile

        UserProfile.objects.get_or_create(
            user=user,
            defaults={"supabase_uid": sub, "email": email},
        )
        return user
