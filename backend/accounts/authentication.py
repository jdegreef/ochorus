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
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

logger = logging.getLogger(__name__)

# Accepted signature algorithms, per key source. These are CONSTANTS on purpose.
# Passing the token's own `alg` header back to `jwt.decode` lets the caller
# choose how their signature is checked, which is the setup for an
# HS/RS confusion attack: sign with the JWKS *public* key as an HMAC secret and
# a "verified" token falls out. The branch below happens to block that today —
# an HS header routes to the shared secret, never to a JWKS key — but that is an
# accident of control flow, not a decision, and one refactor away from being
# untrue. Pinning the set per branch makes it a decision.
HS_ALGORITHMS = ("HS256", "HS384", "HS512")
ASYMMETRIC_ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512")

# How long a fetched JWK Set is trusted before it is re-fetched. This bounds how
# long a rotated-out or revoked Supabase signing key stays accepted.
JWKS_CACHE_SECONDS = 300

# Don't move ``last_seen_at`` (a write) on every authenticated request — only
# once the recorded value is this stale. The admin's "seen" column is a
# day-grained signal, so a coarse throttle costs nothing it needs.
LAST_SEEN_THROTTLE = timedelta(minutes=15)


def token_providers(payload) -> list[str]:
    """The Supabase auth providers a verified token reports, normalised.

    Supabase carries the linked identities in ``app_metadata.providers`` (a
    list) and the one just used in ``app_metadata.provider`` (a string). We
    keep the full set — an account that signed up with email and later linked
    Google should count under both — lower-cased, de-duplicated and sorted so
    the stored form is stable. Returns ``[]`` when the token says nothing.
    """
    meta = payload.get("app_metadata") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        return []
    found: set[str] = set()
    provs = meta.get("providers")
    if isinstance(provs, list):
        found.update(p.strip().lower() for p in provs if isinstance(p, str) and p.strip())
    prov = meta.get("provider")
    if isinstance(prov, str) and prov.strip():
        found.add(prov.strip().lower())
    return sorted(found)


def token_signup_variant(payload) -> str:
    """The logged-out sign-up band arm a token reports, or ``""``.

    Supabase carries custom sign-up metadata in ``user_metadata`` — set by the
    client at ``signUp({ options: { data } })``, so it is present only for a
    genuine sign-up (a plain login sends none) and it survives the email
    confirmation round-trip (it lives on the auth user, not the JS session).
    We read it only when the profile is first created (see
    ``_get_or_create_user``), which makes the field naturally create-only.
    Unknown values are dropped so a stray client can't write junk into the
    analytics vocabulary.
    """
    from .models import SIGNUP_VARIANTS

    meta = payload.get("user_metadata") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        return ""
    value = meta.get("signup_variant")
    return value if isinstance(value, str) and value in SIGNUP_VARIANTS else ""


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
        issuer = self._issuer()

        # Claims that must be PRESENT, not merely valid if present. PyJWT
        # verifies `exp` only when the token carries one, so without this a
        # token minted with no `exp` never expires. `aud`/`iss` are required
        # only when we are actually checking them — demanding a claim we then
        # ignore would reject valid tokens for no security gain.
        required = ["exp", "sub"]
        if audience:
            required.append("aud")
        if issuer:
            required.append("iss")

        try:
            if alg.startswith("HS"):
                if not settings.SUPABASE_JWT_SECRET:
                    raise exceptions.AuthenticationFailed(
                        "Received an HS-signed token but SUPABASE_JWT_SECRET is not set."
                    )
                key = settings.SUPABASE_JWT_SECRET
                algorithms = list(HS_ALGORITHMS)
            else:
                key = self._jwks().get_signing_key_from_jwt(token).key
                algorithms = list(ASYMMETRIC_ALGORITHMS)
            return jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience=audience,
                issuer=issuer,
                options={"require": required},
            )
        except exceptions.AuthenticationFailed:
            raise
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired") from None
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}") from exc

    def _issuer(self) -> str | None:
        """The issuer these tokens must carry, or ``None`` to skip the check.

        Supabase stamps ``iss`` as ``<project-url>/auth/v1``. Without checking
        it, *any* token signed by a key the JWKS endpoint serves is accepted
        regardless of who issued it.

        ``SUPABASE_URL`` is normalised to a bare origin by ``origin_url`` (no
        trailing slash, no path), so deriving the issuer from it is safe.
        ``SUPABASE_JWT_ISSUER`` overrides it for a self-hosted GoTrue whose
        issuer is not the project origin — an escape hatch that avoids a code
        change if the derived value is ever wrong, since a mismatch resolves
        every request to anonymous.

        Returns ``None`` when neither is configured (a dev box on the shared
        HS256 secret), leaving behaviour unchanged there.
        """
        override = getattr(settings, "SUPABASE_JWT_ISSUER", "")
        if override:
            return override
        if settings.SUPABASE_URL:
            return f"{settings.SUPABASE_URL}/auth/v1"
        return None

    def _jwks(self) -> jwt.PyJWKClient:
        if not settings.SUPABASE_URL:
            raise exceptions.AuthenticationFailed(
                "SUPABASE_URL is not configured; cannot validate asymmetric tokens."
            )
        if SupabaseJWTAuthentication._jwks_client is None:
            url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            SupabaseJWTAuthentication._jwks_client = jwt.PyJWKClient(
                url,
                # Tier 1 — the JWK Set response — is cached and re-fetched every
                # `lifespan` seconds, so a key rotation takes effect within five
                # minutes without a request paying for a fetch.
                cache_jwk_set=True,
                lifespan=JWKS_CACHE_SECONDS,
                # Tier 2 — PyJWT's per-`kid` signing-key LRU — is deliberately
                # OFF (it was on). Its own docs: "no time-based expiration …
                # evicted only when the cache reaches its maximum size". With it
                # on, a signing key Supabase had ROTATED OUT or REVOKED stayed
                # trusted for the life of the worker, because the kid sat in the
                # 16-entry LRU and was never re-checked — even while Tier 1 was
                # refreshing correctly. Tier 1 already removes the per-request
                # network cost, so this tier bought nothing and cost revocation.
                cache_keys=False,
            )
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
        from django.utils import timezone

        from .models import UserProfile

        providers = ",".join(token_providers(payload))
        now = timezone.now()
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "supabase_uid": sub,
                "email": email,
                "providers": providers,
                # Create-only: recorded once, from the sign-up token's metadata,
                # and never revisited by a later login (see token_signup_variant).
                "signup_variant": token_signup_variant(payload),
                "last_seen_at": now,
            },
        )
        if not created:
            self._touch_profile(profile, providers, now)
        return user

    def _touch_profile(self, profile, providers: str, now) -> None:
        """Keep ``providers`` current and ``last_seen_at`` fresh, cheaply.

        Runs on every authenticated request, so it writes only when something
        actually changed: a newly linked provider, or a ``last_seen_at`` older
        than ``LAST_SEEN_THROTTLE``. A token that reports no providers never
        clears a value we already learned.
        """
        fields = []
        if providers and providers != profile.providers:
            profile.providers = providers
            fields.append("providers")
        if profile.last_seen_at is None or now - profile.last_seen_at >= LAST_SEEN_THROTTLE:
            profile.last_seen_at = now
            fields.append("last_seen_at")
        if fields:
            profile.save(update_fields=fields)
