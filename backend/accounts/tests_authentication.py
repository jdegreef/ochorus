"""Tests for the security boundary: SupabaseJWTAuthentication.

This class authenticates every request in the app. Its contract:

* a validly-signed, current token authenticates and maps to a Django User +
  UserProfile;
* an expired, malformed, wrong-secret, or sub-less token resolves to *anonymous*
  (returns ``None``) — never a raised 401/500 — so public endpoints keep working
  for a signed-in reader whose token has lapsed;
* the token's ``email_verified`` claim gates admin (see ``permissions``).

We exercise the HS256 (shared-secret) path: it runs the same
``_decode`` → ``_get_or_create_user`` → ``authenticate`` flow as the production
asymmetric path but needs no network/JWKS or ``cryptography`` keypair.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from unittest import mock

import jwt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from accounts.authentication import (
    SupabaseJWTAuthentication,
    token_email_is_verified,
)
from accounts.models import UserProfile
from accounts.permissions import is_admin_user

User = get_user_model()

SECRET = "test-jwt-secret"
AUD = "authenticated"
SUB = "11111111-1111-1111-1111-111111111111"


def _token(secret=SECRET, *, exp_delta=timedelta(hours=1), **claims) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": SUB,
        "aud": AUD,
        "iat": now,
        "exp": now + exp_delta,
    }
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


def _b64url(raw: bytes) -> str:
    """base64url without padding — the JWT wire encoding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _fake_jwks(key):
    """A stubbed PyJWKClient that hands back `key` for any token.

    Lets the asymmetric branch be exercised without a network call — and makes
    a rejection provably the decoder's doing rather than a failed fetch.
    """
    client = mock.Mock()
    client.get_signing_key_from_jwt.return_value = mock.Mock(key=key)
    return client


def _request(token: str | None):
    extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token is not None else {}
    return APIRequestFactory().get("/api/auth/me/", **extra)


@override_settings(
    DEBUG=False,
    SUPABASE_JWT_SECRET=SECRET,
    SUPABASE_JWT_AUDIENCE=AUD,
    ADMIN_EMAILS={"admin@example.com"},
)
class SupabaseJWTAuthenticationTests(TestCase):
    def setUp(self):
        self.auth = SupabaseJWTAuthentication()

    # -- happy path -----------------------------------------------------------

    def test_valid_token_authenticates_and_provisions_user(self):
        token = _token(email="reader@example.com", email_verified=True)
        result = self.auth.authenticate(_request(token))
        self.assertIsNotNone(result)
        user, payload = result
        self.assertEqual(user.username, SUB)
        self.assertEqual(user.email, "reader@example.com")
        self.assertEqual(payload["sub"], SUB)
        # A UserProfile is created for the sub.
        self.assertTrue(UserProfile.objects.filter(user=user, supabase_uid=SUB).exists())

    def test_second_call_reuses_the_same_user(self):
        self.auth.authenticate(_request(_token(email="reader@example.com")))
        self.auth.authenticate(_request(_token(email="reader@example.com")))
        self.assertEqual(User.objects.filter(username=SUB).count(), 1)
        self.assertEqual(UserProfile.objects.filter(supabase_uid=SUB).count(), 1)

    def test_records_providers_and_last_seen_from_token(self):
        token = _token(
            email="reader@example.com",
            app_metadata={"provider": "google", "providers": ["email", "google"]},
        )
        user, _ = self.auth.authenticate(_request(token))
        profile = UserProfile.objects.get(user=user)
        # Stored sorted + de-duplicated across provider/providers.
        self.assertEqual(profile.providers, "email,google")
        self.assertIsNotNone(profile.last_seen_at)

    def test_last_seen_refreshes_only_past_the_throttle(self):
        from datetime import timedelta

        from django.utils import timezone

        from accounts.authentication import LAST_SEEN_THROTTLE

        self.auth.authenticate(_request(_token()))
        # A second sign-in within the throttle window leaves last_seen_at alone.
        UserProfile.objects.filter(supabase_uid=SUB).update(
            last_seen_at=timezone.now() - LAST_SEEN_THROTTLE / 2
        )
        recent = UserProfile.objects.get(supabase_uid=SUB).last_seen_at
        self.auth.authenticate(_request(_token()))
        self.assertEqual(UserProfile.objects.get(supabase_uid=SUB).last_seen_at, recent)
        # Once it's stale beyond the window, the next sign-in refreshes it.
        UserProfile.objects.filter(supabase_uid=SUB).update(
            last_seen_at=timezone.now() - LAST_SEEN_THROTTLE - timedelta(minutes=1)
        )
        stale = UserProfile.objects.get(supabase_uid=SUB).last_seen_at
        self.auth.authenticate(_request(_token()))
        self.assertGreater(UserProfile.objects.get(supabase_uid=SUB).last_seen_at, stale)

    def test_newly_linked_provider_is_picked_up(self):
        self.auth.authenticate(
            _request(_token(app_metadata={"providers": ["email"]}))
        )
        self.auth.authenticate(
            _request(_token(app_metadata={"providers": ["email", "google"]}))
        )
        self.assertEqual(UserProfile.objects.get(supabase_uid=SUB).providers, "email,google")

    def test_token_without_providers_does_not_clear_them(self):
        self.auth.authenticate(
            _request(_token(app_metadata={"providers": ["google"]}))
        )
        self.auth.authenticate(_request(_token()))  # no app_metadata at all
        self.assertEqual(UserProfile.objects.get(supabase_uid=SUB).providers, "google")

    def test_authenticate_header_is_bearer(self):
        self.assertEqual(self.auth.authenticate_header(_request(None)), "Bearer")

    # -- bad tokens resolve to anonymous, never raise -------------------------

    def test_no_authorization_header_is_anonymous(self):
        self.assertIsNone(self.auth.authenticate(_request(None)))

    def test_expired_token_is_anonymous(self):
        token = _token(email="reader@example.com", exp_delta=timedelta(hours=-1))
        self.assertIsNone(self.auth.authenticate(_request(token)))

    def test_malformed_token_is_anonymous(self):
        self.assertIsNone(self.auth.authenticate(_request("not-a-jwt")))

    def test_wrong_secret_is_anonymous(self):
        token = _token(secret="a-different-secret", email="reader@example.com")
        self.assertIsNone(self.auth.authenticate(_request(token)))

    def test_wrong_audience_is_anonymous(self):
        token = _token(email="reader@example.com")
        token = jwt.encode(
            {
                "sub": SUB,
                "aud": "some-other-audience",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            SECRET,
            algorithm="HS256",
        )
        self.assertIsNone(self.auth.authenticate(_request(token)))

    def test_missing_sub_is_anonymous(self):
        now = datetime.now(UTC)
        token = jwt.encode(
            {"aud": AUD, "iat": now, "exp": now + timedelta(hours=1)},
            SECRET,
            algorithm="HS256",
        )
        self.assertIsNone(self.auth.authenticate(_request(token)))

    # -- email verification gates admin (#01) ---------------------------------

    def test_verified_admin_email_is_admin(self):
        token = _token(email="admin@example.com", email_verified=True)
        request = _request(token)
        user, payload = self.auth.authenticate(request)
        request.user, request.auth = user, payload
        self.assertTrue(is_admin_user(user, request))

    def test_unverified_admin_email_authenticates_but_is_not_admin(self):
        # The takeover scenario: someone signs up with the admin's address while
        # Supabase email confirmation is off. They authenticate as a normal user
        # but must NOT be granted admin.
        token = _token(email="admin@example.com")  # no email_verified claim
        request = _request(token)
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)  # still a valid (non-admin) session
        user, payload = result
        request.user, request.auth = user, payload
        self.assertFalse(is_admin_user(user, request))


class TokenEmailVerifiedHelperTests(TestCase):
    def test_top_level_boolean(self):
        self.assertTrue(token_email_is_verified({"email_verified": True}))
        self.assertFalse(token_email_is_verified({"email_verified": False}))

    def test_user_metadata_form(self):
        self.assertTrue(
            token_email_is_verified({"user_metadata": {"email_verified": True}})
        )

    def test_string_true_is_accepted(self):
        self.assertTrue(token_email_is_verified({"email_verified": "true"}))
        self.assertFalse(token_email_is_verified({"email_verified": "false"}))

    def test_absent_or_non_dict_is_false(self):
        self.assertFalse(token_email_is_verified({}))
        self.assertFalse(token_email_is_verified(None))
        self.assertFalse(token_email_is_verified("nope"))


ISSUER_URL = "https://project-ref.supabase.co"
ISSUER = f"{ISSUER_URL}/auth/v1"


@override_settings(
    DEBUG=False,
    SUPABASE_JWT_SECRET=SECRET,
    SUPABASE_JWT_AUDIENCE=AUD,
    SUPABASE_URL=ISSUER_URL,
    SUPABASE_JWT_ISSUER="",
)
class TokenValidationHardeningTests(TestCase):
    """The four decode weaknesses from the 2026-08 security audit.

    Each was latent rather than exploitable — which is exactly why they needed
    tests: nothing failed while they were wrong, so nothing would notice a
    refactor making them exploitable.
    """

    def setUp(self):
        self.auth = SupabaseJWTAuthentication()

    def _auth(self, token):
        return self.auth.authenticate(_request(token))

    # -- issuer ---------------------------------------------------------------

    def test_token_from_another_issuer_is_rejected(self):
        token = _token(iss="https://attacker.supabase.co/auth/v1")
        self.assertIsNone(self._auth(token))

    def test_token_with_the_expected_issuer_authenticates(self):
        result = self._auth(_token(iss=ISSUER))
        self.assertIsNotNone(result)
        self.assertEqual(result[1]["iss"], ISSUER)

    def test_issuer_is_derived_without_a_double_slash(self):
        """A trailing slash in SUPABASE_URL must not break every login.

        origin_url normalises the setting, so this asserts the contract the
        derivation depends on rather than the derivation alone.
        """
        self.assertEqual(self.auth._issuer(), ISSUER)

    @override_settings(SUPABASE_JWT_ISSUER="https://self-hosted.example/auth/v1")
    def test_explicit_issuer_setting_overrides_the_derived_one(self):
        self.assertEqual(
            self.auth._issuer(), "https://self-hosted.example/auth/v1"
        )
        self.assertIsNotNone(
            self._auth(_token(iss="https://self-hosted.example/auth/v1"))
        )

    @override_settings(SUPABASE_URL="", SUPABASE_JWT_ISSUER="")
    def test_issuer_check_is_skipped_when_unconfigured(self):
        """A dev box on the shared secret keeps working, issuer or not."""
        self.assertIsNone(self.auth._issuer())
        self.assertIsNotNone(self._auth(_token()))

    # -- required claims ------------------------------------------------------

    def test_token_without_exp_never_expires_and_is_rejected(self):
        now = datetime.now(UTC)
        token = jwt.encode(
            {"sub": SUB, "aud": AUD, "iss": ISSUER, "iat": now},
            SECRET,
            algorithm="HS256",
        )
        self.assertNotIn("exp", jwt.decode(token, options={"verify_signature": False}))
        self.assertIsNone(self._auth(token))

    def test_token_without_aud_is_rejected_while_audience_is_configured(self):
        now = datetime.now(UTC)
        token = jwt.encode(
            {"sub": SUB, "iss": ISSUER, "iat": now, "exp": now + timedelta(hours=1)},
            SECRET,
            algorithm="HS256",
        )
        self.assertIsNone(self._auth(token))

    def test_token_without_iss_is_rejected_while_issuer_is_configured(self):
        self.assertIsNone(self._auth(_token()))

    # -- algorithm pinning ----------------------------------------------------

    def test_alg_none_is_rejected(self):
        """Rejected by the pinned algorithm list, not by a failed key fetch.

        The JWKS client is stubbed deliberately: without it this test passes
        because the network call fails, which would keep passing even if the
        algorithm list were unpinned — and it would make CI reach the internet.
        """
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": SUB, "aud": AUD, "iss": ISSUER,
                "iat": now, "exp": now + timedelta(hours=1),
            },
            key="",
            algorithm="none",
        )
        with mock.patch.object(
            SupabaseJWTAuthentication, "_jwks", return_value=_fake_jwks(SECRET)
        ):
            self.assertIsNone(self._auth(token))

    def test_asymmetric_alg_token_cannot_be_verified_with_the_shared_secret(self):
        """The HS/RS confusion forgery, built the way an attacker builds it.

        PyJWT will not *encode* this shape (it honours the header and demands a
        real RSA key), so the token is assembled by hand: an RS256 header over an
        HMAC-SHA256 signature. The stubbed JWKS then hands back the very key the
        forgery was signed with — the most favourable case for the attacker — and
        it is still rejected, because an RS256 header is only ever verified as
        RS256.
        """
        now = int(datetime.now(UTC).timestamp())
        claims = {
            "sub": SUB, "aud": AUD, "iss": ISSUER,
            "iat": now, "exp": now + 3600,
        }
        header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        payload = _b64url(json.dumps(claims).encode())
        signing_input = f"{header}.{payload}".encode()
        signature = _b64url(
            hmac.new(SECRET.encode(), signing_input, hashlib.sha256).digest()
        )
        forged = f"{header}.{payload}.{signature}"

        # Sanity: the forgery really does advertise an asymmetric algorithm.
        self.assertEqual(jwt.get_unverified_header(forged)["alg"], "RS256")

        with mock.patch.object(
            SupabaseJWTAuthentication, "_jwks", return_value=_fake_jwks(SECRET)
        ):
            self.assertIsNone(self._auth(forged))

    def test_accepted_algorithms_are_constants_not_the_token_header(self):
        """The HS branch must never accept an asymmetric alg, and vice versa.

        The disjointness is the property that blocks HS/RS confusion: a token
        whose header names an asymmetric alg can never be verified against the
        shared secret, whatever the header claims.
        """
        from accounts.authentication import ASYMMETRIC_ALGORITHMS, HS_ALGORITHMS

        self.assertEqual(set(HS_ALGORITHMS) & set(ASYMMETRIC_ALGORITHMS), set())
        self.assertTrue(all(a.startswith("HS") for a in HS_ALGORITHMS))
        self.assertFalse(any(a.startswith("HS") for a in ASYMMETRIC_ALGORITHMS))

    def test_hs_token_signed_with_an_unaccepted_family_is_rejected(self):
        """An HS-header token still has to be a real HS signature."""
        header, _, rest = _token(iss=ISSUER).partition(".")
        self.assertTrue(rest)  # sanity: the token really is three parts
        tampered = header + "." + rest.split(".")[0] + ".not-a-signature"
        self.assertIsNone(self._auth(tampered))


class JwksCacheTests(TestCase):
    """Key rotation must actually take effect.

    PyJWT's per-`kid` cache (`cache_keys=True`, which this code used to pass)
    has, in its own words, "no time-based expiration" — so a revoked signing key
    stayed trusted for the life of the worker. The JWK *Set* cache does expire,
    so turning the per-key tier off costs no extra network traffic.
    """

    @override_settings(SUPABASE_URL=ISSUER_URL)
    def test_per_key_cache_is_off_and_the_jwk_set_cache_expires(self):
        SupabaseJWTAuthentication._jwks_client = None
        try:
            client = SupabaseJWTAuthentication()._jwks()
            # No unbounded per-kid memo: PyJWT only builds one when cache_keys
            # is on, so its absence is the assertion.
            self.assertFalse(
                hasattr(client.get_signing_key, "cache_info"),
                "per-kid signing-key LRU is enabled; a revoked key would stay "
                "trusted for the life of the worker",
            )
            self.assertIsNotNone(client.jwk_set_cache)
            self.assertEqual(client.jwk_set_cache.lifespan, 300)
        finally:
            SupabaseJWTAuthentication._jwks_client = None
