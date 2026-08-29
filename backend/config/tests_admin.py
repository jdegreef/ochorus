"""Django's admin is mounted only in local DEBUG.

In production the admin surface is the SPA dashboard behind IsAdminEmail; Django's
own password login on the public API origin is an unthrottled brute-force target
(see config/urls.py). This guards against it silently coming back unconditionally.
"""

import importlib

from django.test import SimpleTestCase, override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse

import config.urls


def _reload_urlconf():
    importlib.reload(config.urls)
    clear_url_caches()


class AdminSurfaceTests(SimpleTestCase):
    def tearDown(self):
        # The test runner forces DEBUG=False, so reloading restores the ambient
        # (production-like, admin-unmounted) urlconf for any later test.
        _reload_urlconf()

    def test_admin_is_not_mounted_in_production(self):
        with override_settings(DEBUG=False):
            _reload_urlconf()
            with self.assertRaises(NoReverseMatch):
                reverse("admin:index")

    def test_admin_is_mounted_in_local_debug(self):
        with override_settings(DEBUG=True):
            _reload_urlconf()
            self.assertTrue(reverse("admin:index").startswith("/admin/"))
