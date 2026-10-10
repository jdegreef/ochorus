"""The native app's origins stay in CORS whatever the environment says.

Every installed copy of the iOS / Android app calls the API from a fixed origin
(``NATIVE_APP_ORIGINS``). Production sets ``CORS_ALLOWED_ORIGINS`` from the
environment, which replaces the dev defaults wholesale — so if the app's origins
lived in that default, the first production deploy would block every phone.
"""

from __future__ import annotations

import importlib
import os
from unittest import mock

from django.test import SimpleTestCase

import config.settings as settings_module


def allowed_origins(env: dict[str, str]) -> list[str]:
    """Re-run the settings module under `env` and return its CORS allow-list."""
    with mock.patch.dict(os.environ, env, clear=False), mock.patch("sentry_sdk.init"):
        importlib.reload(settings_module)
    return settings_module.CORS_ALLOWED_ORIGINS


class NativeAppOriginTests(SimpleTestCase):
    def tearDown(self):
        # Leave the module as the rest of the suite expects to find it.
        with mock.patch("sentry_sdk.init"):
            importlib.reload(settings_module)

    def test_a_production_override_keeps_the_app_origins(self):
        origins = allowed_origins({"CORS_ALLOWED_ORIGINS": "https://ochorus.com"})
        self.assertEqual(
            origins, ["https://ochorus.com", "capacitor://localhost", "https://localhost"]
        )

    def test_an_override_that_already_lists_them_does_not_repeat_them(self):
        origins = allowed_origins(
            {"CORS_ALLOWED_ORIGINS": "https://ochorus.com,capacitor://localhost"}
        )
        self.assertEqual(origins.count("capacitor://localhost"), 1)
        self.assertIn("https://localhost", origins)
