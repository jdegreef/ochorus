from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserProfile
from accounts.permissions import is_admin_user
from common.env import origin_url
from reading.models import ChapterMarks, Favorite, ReadingDay, ReadingProgress

User = get_user_model()


class MeViewTests(TestCase):
    """The authenticated profile endpoint — profile mutation and, critically,
    account deletion (a destructive, hard-to-undo action)."""

    def setUp(self):
        self.user = User.objects.create(username="11111111-1111-1111-1111-111111111111")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="me@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_patch_sets_trims_and_clears_display_name(self):
        res = self.client.patch("/api/auth/me/", {"display_name": "  James  "}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["display_name"], "James")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "James")
        # Empty string clears it back to the email.
        self.client.patch("/api/auth/me/", {"display_name": ""}, format="json")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name, "")

    def test_delete_removes_profile_and_cascades_all_reading_data(self):
        ReadingProgress.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            language="en", chapter_order=1, paragraph_index=0,
        )
        Favorite.objects.create(profile=self.profile, kind="book", slug="humility")
        ChapterMarks.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            chapter_order=1, marks=[],
        )
        ReadingDay.objects.create(profile=self.profile, day="2026-07-20")
        pid = self.profile.id

        res = self.client.delete("/api/auth/me/")
        self.assertEqual(res.status_code, 204)

        self.assertFalse(UserProfile.objects.filter(id=pid).exists())
        for model in (ReadingProgress, Favorite, ChapterMarks, ReadingDay):
            self.assertEqual(model.objects.filter(profile_id=pid).count(), 0)

    def test_delete_only_touches_the_requesters_own_data(self):
        other_user = User.objects.create(username="22222222-2222-2222-2222-222222222222")
        other = UserProfile.objects.create(
            user=other_user, supabase_uid=other_user.username, email="other@example.com"
        )
        Favorite.objects.create(profile=other, kind="book", slug="humility")

        self.client.delete("/api/auth/me/")

        self.assertTrue(UserProfile.objects.filter(id=other.id).exists())
        self.assertEqual(Favorite.objects.filter(profile=other).count(), 1)

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/auth/me/").status_code, 401)
        self.assertEqual(anon.delete("/api/auth/me/").status_code, 401)


class OriginUrlTests(TestCase):
    def test_strips_rest_path(self):
        # The exact misconfiguration that broke prod JWT validation.
        self.assertEqual(
            origin_url("https://abc.supabase.co/rest/v1/"),
            "https://abc.supabase.co",
        )

    def test_strips_auth_path_and_query(self):
        self.assertEqual(
            origin_url("https://abc.supabase.co/auth/v1?x=1"),
            "https://abc.supabase.co",
        )

    def test_plain_origin_unchanged(self):
        self.assertEqual(
            origin_url("https://abc.supabase.co"), "https://abc.supabase.co"
        )

    def test_trailing_slash_trimmed(self):
        self.assertEqual(
            origin_url("https://abc.supabase.co/"), "https://abc.supabase.co"
        )

    def test_preserves_port(self):
        self.assertEqual(
            origin_url("http://localhost:54321/rest/v1"), "http://localhost:54321"
        )

    def test_missing_scheme_keeps_host(self):
        self.assertEqual(origin_url("abc.supabase.co/rest/v1"), "abc.supabase.co")

    def test_blank(self):
        self.assertEqual(origin_url(""), "")
        self.assertEqual(origin_url("  "), "")


def _request(remote_addr: str, *, verified: bool | None = None):
    from django.test import RequestFactory

    req = RequestFactory().get("/api/admin/stats/", REMOTE_ADDR=remote_addr)
    if verified is not None:
        # DRF puts the decoded JWT on request.auth; mimic a token that does (or
        # does not) assert the email is verified.
        req.auth = {"email_verified": verified}
    return req


class IsAdminUserTests(TestCase):
    @override_settings(DEBUG=True, ADMIN_EMAILS=set())
    def test_debug_bypasses_check_for_loopback_requests(self):
        self.assertTrue(is_admin_user(User(email=""), _request("127.0.0.1")))
        self.assertTrue(is_admin_user(User(email=""), _request("::1")))

    @override_settings(DEBUG=True, ADMIN_EMAILS={"admin@example.com"})
    def test_debug_does_not_bypass_for_remote_requests(self):
        # A misconfigured DJANGO_DEBUG=true on a real host must not open the
        # admin surface to the internet — remote clients still need the list.
        self.assertFalse(is_admin_user(User(email=""), _request("203.0.113.9")))
        self.assertFalse(
            is_admin_user(User(email="someone@example.com"), _request("203.0.113.9"))
        )
        self.assertTrue(
            is_admin_user(
                User(email="admin@example.com"), _request("203.0.113.9", verified=True)
            )
        )

    @override_settings(DEBUG=True, ADMIN_EMAILS=set())
    def test_debug_does_not_bypass_without_a_request(self):
        self.assertFalse(is_admin_user(User(email="")))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_allowlisted_verified_email_allowed(self):
        self.assertTrue(
            is_admin_user(
                User(email="admin@example.com"), _request("203.0.113.9", verified=True)
            )
        )

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_case_insensitive(self):
        self.assertTrue(
            is_admin_user(
                User(email="Admin@Example.com"), _request("203.0.113.9", verified=True)
            )
        )

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_allowlisted_but_unverified_email_denied(self):
        # The core fix: an allowlisted address whose token does NOT assert the
        # email is verified must not be treated as admin (email-confirmation-off
        # takeover). Verify=False models exactly that token.
        self.assertFalse(
            is_admin_user(
                User(email="admin@example.com"), _request("203.0.113.9", verified=False)
            )
        )

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_allowlisted_without_a_token_denied(self):
        # No request/token at all (e.g. an internal call) never counts as admin.
        self.assertFalse(is_admin_user(User(email="admin@example.com")))
        self.assertFalse(
            is_admin_user(User(email="admin@example.com"), _request("203.0.113.9"))
        )

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_other_email_denied(self):
        self.assertFalse(
            is_admin_user(
                User(email="someone@example.com"), _request("203.0.113.9", verified=True)
            )
        )

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_blank_email_denied(self):
        self.assertFalse(is_admin_user(User(email="")))


class RobotsTxtTests(TestCase):
    """/robots.txt on the API host tells crawlers to stay off — the corpus is on
    the prerendered reader, and every bot request here is Supabase egress."""

    def test_it_disallows_everything(self):
        res = APIClient().get("/robots.txt")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/plain")
        body = res.content.decode()
        self.assertIn("User-agent: *", body)
        self.assertIn("Disallow: /", body)


class HealthEndpointTests(TestCase):
    """/api/health/ is Render's liveness probe AND the content fingerprint the
    static web build waits on before prerendering (see
    frontend/scripts/await-api-release.mjs)."""

    @override_settings(RELEASE_COMMIT="abc123def456")
    def test_reports_the_commit_it_is_serving(self):
        res = APIClient().get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "ok")
        self.assertEqual(res.data["commit"], "abc123def456")

    @override_settings(RELEASE_COMMIT="")
    def test_commit_is_present_but_empty_when_unset(self):
        res = APIClient().get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("commit", res.data)
        self.assertEqual(res.data["commit"], "")

    def test_publishes_the_content_digest_the_web_build_compares(self):
        from library.content_fixtures import content_digest

        res = APIClient().get("/api/health/")
        self.assertEqual(res.data["content_version"], content_digest())

    def test_the_digest_matches_what_the_web_build_computes(self):
        """The gate is a Python digest compared against a JavaScript one, and if
        the two rules ever drift the build either hangs for its whole timeout or
        stops checking anything.

        Recomputed here by the DOCUMENTED rule — every file under every root in
        content_sources.json, keyed by "<root>/<path within root>", roots sorted
        and paths sorted within a root — written out independently of the
        implementation. That is what makes it a contract test rather than a
        restatement: changing how content_digest() works has to be a deliberate
        change here too, and this is the only place that notices the JavaScript
        side has been left behind.
        """
        import hashlib

        from library.content_fixtures import (
            compute_content_digest,
            content_roots,
        )

        h = hashlib.sha256()
        seen = 0
        for label, root in sorted(content_roots()):
            if not root.exists():
                continue
            if root.is_file():
                # A file root is keyed by its own name, with no relative part —
                # the seed modules, named individually because a `/**` over a
                # Python package would sweep in __pycache__ and the API image
                # and the web build would digest the same content differently.
                seen += 1
                h.update(label.encode())
                h.update(b"\0")
                h.update(hashlib.sha256(root.read_bytes()).hexdigest().encode())
                h.update(b"\0")
                continue
            rels = sorted(
                p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
            )
            for rel in rels:
                seen += 1
                h.update(f"{label}/{rel}".encode())
                h.update(b"\0")
                h.update(hashlib.sha256((root / rel).read_bytes()).hexdigest().encode())
                h.update(b"\0")
        self.assertTrue(seen, "no reader content to digest")
        # compute_content_digest, not content_digest: the latter prefers the
        # value baked into the image, which is the right thing at runtime and
        # would make this test assert nothing.
        self.assertEqual(compute_content_digest(), h.hexdigest()[:16])

    def test_a_baked_digest_is_served_in_preference_to_walking_the_disk(self):
        """/api/health/ is Render's LIVENESS probe. Computing the digest reads
        ~90 MB — 8s cold — so the image build bakes it and the endpoint serves
        that file. If this ever stopped being preferred, the first request a
        fresh container answered would be the slow one."""
        import tempfile
        from pathlib import Path
        from unittest import mock

        from library.content_fixtures import content_digest

        with tempfile.TemporaryDirectory() as tmp:
            baked = Path(tmp) / ".content-version"
            baked.write_text("deadbeefdeadbeef\n")
            with mock.patch("library.content_fixtures.BAKED_DIGEST_FILE", baked):
                content_digest.cache_clear()
                self.assertEqual(content_digest(), "deadbeefdeadbeef")
        content_digest.cache_clear()
