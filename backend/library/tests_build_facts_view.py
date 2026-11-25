"""GET /api/build-facts/ — token-gated, invisible without the token."""

from django.test import TestCase, override_settings

from .build_facts import FORMAT
from .models import Language

URL = "/api/build-facts/"


class BuildFactsViewTests(TestCase):
    def setUp(self):
        Language.objects.get_or_create(code="en", defaults={"name": "English"})

    def get(self, auth=None, **extra):
        if auth is not None:
            extra["HTTP_AUTHORIZATION"] = auth
        return self.client.get(URL, **extra)

    @override_settings(BUILD_FACTS_TOKEN="")
    def test_off_until_a_token_is_configured(self):
        self.assertEqual(self.get().status_code, 404)
        self.assertEqual(self.get("Bearer ").status_code, 404)
        self.assertEqual(self.get("Bearer anything").status_code, 404)

    @override_settings(BUILD_FACTS_TOKEN="s3cret-build-token")
    def test_a_wrong_or_missing_token_looks_like_no_route(self):
        for auth in (
            None,
            "",
            "Bearer wrong",
            "Basic s3cret-build-token",
            "s3cret-build-token",
        ):
            with self.subTest(auth=auth):
                self.assertEqual(self.get(auth).status_code, 404)

    @override_settings(BUILD_FACTS_TOKEN="s3cret-build-token")
    def test_the_token_gets_the_export(self):
        response = self.get("Bearer s3cret-build-token")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["format"], FORMAT)
        self.assertIn("en", [lang["code"] for lang in body["languages"]])
        self.assertIn("no-store", response["Cache-Control"])

    @override_settings(BUILD_FACTS_TOKEN="s3cret-build-token")
    def test_read_only(self):
        self.assertEqual(
            self.client.post(
                URL, HTTP_AUTHORIZATION="Bearer s3cret-build-token"
            ).status_code,
            405,
        )

    @override_settings(BUILD_FACTS_TOKEN="s3cret-build-token", API_GUARD_MODE="enforce")
    def test_the_api_guard_lets_the_build_through(self):
        # The build is a server: no Origin, no Referer, no service key.
        self.assertEqual(self.get("Bearer s3cret-build-token").status_code, 200)
