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

from datetime import datetime, timedelta, timezone

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
    now = datetime.now(timezone.utc)
    payload = {
        "sub": SUB,
        "aud": AUD,
        "iat": now,
        "exp": now + exp_delta,
    }
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


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
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            SECRET,
            algorithm="HS256",
        )
        self.assertIsNone(self.auth.authenticate(_request(token)))

    def test_missing_sub_is_anonymous(self):
        now = datetime.now(timezone.utc)
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
