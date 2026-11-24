"""The API gzips its responses, except the admin's (config/compression.py)."""

from __future__ import annotations

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from config.compression import ApiGZipMiddleware

BODY = b'{"body_html": "' + b"<p>Grace and peace.</p>" * 200 + b'"}'


def respond(path: str, encoding: str = "gzip, br") -> HttpResponse:
    request = RequestFactory().get(path, HTTP_ACCEPT_ENCODING=encoding)
    middleware = ApiGZipMiddleware(
        lambda r: HttpResponse(BODY, content_type="application/json")
    )
    return middleware(request)


class ApiCompressionTests(SimpleTestCase):
    def test_reader_api_json_is_gzipped(self):
        response = respond("/api/books/the-pilgrims-progress/1/")
        self.assertEqual(response["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", response["Vary"])
        self.assertLess(len(response.content), len(BODY) / 4)

    def test_a_client_that_asks_for_none_gets_plain_bytes(self):
        response = respond("/api/books/", encoding="")
        self.assertFalse(response.has_header("Content-Encoding"))
        self.assertEqual(response.content, BODY)

    def test_the_admin_is_never_compressed(self):
        # BREACH: a CSRF token (Django admin) or readers' emails (admin API)
        # next to caller-chosen text.
        for path in ("/admin/library/book/", "/api/admin/stats/"):
            with self.subTest(path=path):
                self.assertFalse(respond(path).has_header("Content-Encoding"))

    def test_it_is_installed(self):
        from django.conf import settings

        self.assertIn("config.compression.ApiGZipMiddleware", settings.MIDDLEWARE)
