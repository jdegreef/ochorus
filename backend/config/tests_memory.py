from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from config import memory


class MemoryLogMiddlewareTests(SimpleTestCase):
    def run_with(self, readings):
        with mock.patch.object(memory, "rss_mb", side_effect=readings):
            mw = memory.MemoryLogMiddleware(lambda request: HttpResponse("ok"))
            request = RequestFactory().get("/api/library/books/?language=en")
            with self.assertLogs("ochorus.memory", "WARNING") as logs:
                memory.logger.warning("sentinel")  # assertLogs needs one line
                response = mw(request)
        return response, [line for line in logs.output if "sentinel" not in line]

    def test_a_request_that_grows_memory_is_logged_with_its_url(self):
        response, lines = self.run_with([100, 100, 140])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(lines), 1)
        self.assertIn("+40 MB", lines[0])
        self.assertIn("/api/library/books/?language=en", lines[0])

    def test_a_request_near_the_limit_is_logged_even_without_growth(self):
        _response, lines = self.run_with([100, 450, 452])
        self.assertEqual(len(lines), 1)

    def test_an_ordinary_request_is_not_logged(self):
        _response, lines = self.run_with([100, 150, 152])
        self.assertEqual(lines, [])

    def test_off_linux_it_steps_aside(self):
        with mock.patch.object(memory, "rss_mb", return_value=None):
            mw = memory.MemoryLogMiddleware(lambda request: HttpResponse("ok"))
        self.assertFalse(mw.enabled)
        self.assertEqual(mw(RequestFactory().get("/")).status_code, 200)
