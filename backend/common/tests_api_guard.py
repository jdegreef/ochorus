"""The API guard lets Ochorus's own clients through and turns the rest away."""

from __future__ import annotations

from django.test import SimpleTestCase, override_settings

ORIGINS = ["https://ochorus.com", "capacitor://localhost", "https://localhost"]
KEY = "k" * 64

# /api/library/languages/ is a cheap public read that needs no fixture rows
# beyond what the guard decides: a refusal is a 403, anything else got through.
LIBRARY = "/api/library/languages/"


@override_settings(
    API_GUARD_MODE="enforce",
    API_SERVICE_KEYS=[KEY, "rotated-" + "x" * 56],
    CORS_ALLOWED_ORIGINS=ORIGINS,
    ALLOWED_HOSTS=["api.ochorus.com", "testserver"],
)
class EnforceTests(SimpleTestCase):
    databases = "__all__"

    def get(self, path=LIBRARY, **headers):
        return self.client.get(path, headers=headers)

    def assertRefused(self, res):
        self.assertEqual(res.status_code, 403, res.content[:200])
        self.assertIn("Ochorus", res.json()["detail"])

    def assertPassed(self, res):
        self.assertNotEqual(res.status_code, 403, res.content[:200])

    def test_a_bare_script_is_refused(self):
        self.assertRefused(self.get())

    def test_the_reader_and_the_apps_pass_by_origin(self):
        for origin in ORIGINS:
            with self.subTest(origin=origin):
                self.assertPassed(self.get(origin=origin))

    def test_origin_matching_ignores_case_and_a_trailing_slash(self):
        self.assertPassed(self.get(origin="HTTPS://Ochorus.com/"))

    def test_another_site_is_refused(self):
        self.assertRefused(self.get(origin="https://scraper.example"))
        # A lookalike is not a prefix match.
        self.assertRefused(self.get(origin="https://ochorus.com.evil.example"))

    def test_a_referer_from_the_reader_passes_without_origin(self):
        self.assertPassed(self.get(referer="https://ochorus.com/books/pilgrims-progress/"))
        self.assertRefused(self.get(referer="https://scraper.example/page"))

    def test_the_build_passes_by_service_key_and_any_listed_key_works(self):
        self.assertPassed(self.get(**{"x-ochorus-key": KEY}))
        self.assertPassed(self.get(**{"x-ochorus-key": "rotated-" + "x" * 56}))
        self.assertRefused(self.get(**{"x-ochorus-key": "guess"}))

    def test_an_empty_key_list_accepts_no_key(self):
        with override_settings(API_SERVICE_KEYS=[]):
            self.assertRefused(self.get(**{"x-ochorus-key": ""}))

    def test_exempt_paths_pass_without_anything(self):
        for path in (
            "/api/health/",
            "/api/emails/unsubscribe/not-a-token/",
            "/api/library/books/some-book/download.epub",
            "/robots.txt",
        ):
            with self.subTest(path=path):
                self.assertPassed(self.get(path))

    def test_the_exemptions_are_anchored(self):
        # "download.epub" must be the END of a book path, not a substring.
        self.assertRefused(self.get("/api/library/books/x/download.epub/../../authors/"))
        self.assertRefused(self.get("/api/library/books/download.epub-not/chapters/"))

    def test_a_preflight_is_not_refused(self):
        res = self.client.options(
            LIBRARY,
            headers={"origin": "https://ochorus.com", "access-control-request-method": "GET"},
        )
        self.assertPassed(res)

    def test_private_routes_are_guarded_too(self):
        # Admin and reading routes are guarded too, not only the library.
        self.assertRefused(self.get("/api/reading/state/"))
        self.assertRefused(self.get("/api/auth/me/"))


@override_settings(API_GUARD_MODE="report", API_SERVICE_KEYS=[KEY], CORS_ALLOWED_ORIGINS=ORIGINS)
class ReportTests(SimpleTestCase):
    databases = "__all__"

    def test_report_mode_logs_but_lets_everything_through(self):
        with self.assertLogs("ochorus.api_guard", level="WARNING") as logs:
            res = self.client.get(LIBRARY, headers={"user-agent": "python-requests/2.31"})
        self.assertNotEqual(res.status_code, 403)
        self.assertIn("would refuse GET /api/library/languages/", logs.output[0])
        self.assertIn("python-requests", logs.output[0])

    def test_report_mode_is_quiet_for_our_own_clients(self):
        with self.assertNoLogs("ochorus.api_guard", level="WARNING"):
            self.client.get(LIBRARY, headers={"origin": "https://ochorus.com"})


@override_settings(API_GUARD_MODE="off", CORS_ALLOWED_ORIGINS=ORIGINS)
class OffTests(SimpleTestCase):
    databases = "__all__"

    def test_off_does_nothing(self):
        with self.assertNoLogs("ochorus.api_guard", level="WARNING"):
            res = self.client.get(LIBRARY)
        self.assertNotEqual(res.status_code, 403)
