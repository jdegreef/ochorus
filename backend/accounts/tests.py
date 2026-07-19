from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.permissions import is_admin_user
from common.env import origin_url

User = get_user_model()


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


def _request(remote_addr: str):
    from django.test import RequestFactory

    return RequestFactory().get("/api/admin/stats/", REMOTE_ADDR=remote_addr)


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
            is_admin_user(User(email="admin@example.com"), _request("203.0.113.9"))
        )

    @override_settings(DEBUG=True, ADMIN_EMAILS=set())
    def test_debug_does_not_bypass_without_a_request(self):
        self.assertFalse(is_admin_user(User(email="")))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_allowlisted_email_allowed(self):
        self.assertTrue(is_admin_user(User(email="admin@example.com")))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_case_insensitive(self):
        self.assertTrue(is_admin_user(User(email="Admin@Example.com")))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_other_email_denied(self):
        self.assertFalse(is_admin_user(User(email="someone@example.com")))

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_blank_email_denied(self):
        self.assertFalse(is_admin_user(User(email="")))
