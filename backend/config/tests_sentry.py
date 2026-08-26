"""What Sentry is told about a deploy.

The release is the difference between "something is broken in production" and
"the deploy at 14:32 broke it". Without it every report from every build is
attributed to one undifferentiated environment, and the first question anyone
asks of an error — which release introduced this — has no answer.

Exercised by re-executing the settings module with the environment set and
`sentry_sdk.init` patched, rather than by asserting on the source text: the
value has to survive the `or None`, and a test that only greps for `release=`
would pass on a line that sends the wrong thing.
"""

from __future__ import annotations

import importlib
import os
from unittest import mock

from django.test import SimpleTestCase

import config.settings as settings_module

#: Well-formed but pointed at nothing. Its presence is what makes the settings
#: module reach the init at all — without a DSN the whole block is skipped.
FAKE_DSN = "https://fake@o0.ingest.sentry.io/0"


def sentry_kwargs(env: dict[str, str]) -> dict | None:
    """Re-run the settings module under `env` and report what init was given.

    Reloaded rather than imported fresh because the module has already been
    executed by the time any test runs; the reload is confined to this call and
    the module is restored afterwards.
    """
    with (
        mock.patch.dict(os.environ, env, clear=False),
        mock.patch("sentry_sdk.init") as init,
    ):
        importlib.reload(settings_module)
    return init.call_args.kwargs if init.call_args else None


class SentryReleaseTests(SimpleTestCase):
    def tearDown(self):
        # Leave the module as the rest of the suite expects to find it.
        with mock.patch("sentry_sdk.init"):
            importlib.reload(settings_module)

    def test_the_deploy_commit_is_reported_as_the_release(self):
        kwargs = sentry_kwargs({"SENTRY_DSN": FAKE_DSN, "RENDER_GIT_COMMIT": "deadbeef"})
        self.assertIsNotNone(kwargs, "settings did not initialise Sentry")
        self.assertEqual(kwargs["release"], "deadbeef")

    def test_no_commit_sends_no_release_rather_than_an_empty_one(self):
        """Local and CI have no commit to report.

        An empty string is worse than nothing: Sentry would accept it and group
        every unreleased error under a release named "".
        """
        kwargs = sentry_kwargs({"SENTRY_DSN": FAKE_DSN, "RENDER_GIT_COMMIT": ""})
        self.assertIsNone(kwargs["release"])

    def test_nothing_is_initialised_without_a_dsn(self):
        """Monitoring stays opt-in — an unconfigured deploy sends nothing."""
        self.assertIsNone(sentry_kwargs({"SENTRY_DSN": "", "RENDER_GIT_COMMIT": "deadbeef"}))

    def test_the_environment_is_still_reported(self):
        """Release and environment answer different questions; adding one must
        not have displaced the other."""
        kwargs = sentry_kwargs(
            {
                "SENTRY_DSN": FAKE_DSN,
                "RENDER_GIT_COMMIT": "deadbeef",
                "SENTRY_ENVIRONMENT": "staging",
            }
        )
        self.assertEqual(kwargs["environment"], "staging")
        # Personal data stays off; a reader's email is not ours to ship to a
        # third party because an error happened near them.
        self.assertFalse(kwargs["send_default_pii"])
