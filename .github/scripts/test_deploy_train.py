"""Unit tests for deploy_train.py's "never overlap a running deploy" rule.

Run from .github/scripts:  python3 -m unittest test_deploy_train
No network: Render's HTTP layer (render_get / deploy / wait_for) and the git
and GitHub lookups are mocked.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

import deploy_train as dt

IDS = {"ochorus-api": "srv-api", "ochorus-web": "srv-web"}
ENV = {
    "RENDER_API_KEY": "k",
    "RENDER_SERVICE_ID_API": "srv-api",
    "RENDER_SERVICE_ID_WEB": "srv-web",
}


def wrapped(dep_id: str, status: str) -> dict:
    return {"deploy": {"id": dep_id, "status": status}, "cursor": "c"}


class RunningDeployTest(unittest.TestCase):
    def check(self, answer):
        with mock.patch.object(dt, "render_get", return_value=answer):
            return dt.running_deploy("srv-web", "k")

    def test_in_progress_statuses_are_running(self):
        for status in (
            "created",
            "queued",
            "build_in_progress",
            "update_in_progress",
            "pre_deploy_in_progress",
            "some_new_status",
        ):
            with self.subTest(status=status):
                self.assertEqual(
                    self.check([wrapped("dep-1", status)]), ("dep-1", status)
                )

    def test_terminal_statuses_are_not(self):
        answer = [wrapped(f"dep-{i}", s) for i, s in enumerate(sorted(dt.DONE))]
        self.assertIsNone(self.check(answer))

    def test_unwrapped_shape(self):
        answer = [{"id": "dep-2", "status": "build_in_progress"}]
        self.assertEqual(self.check(answer), ("dep-2", "build_in_progress"))

    def test_running_behind_a_finished_one_is_found(self):
        answer = [wrapped("dep-new", "live"), wrapped("dep-old", "update_in_progress")]
        self.assertEqual(self.check(answer), ("dep-old", "update_in_progress"))

    def test_empty_list_and_junk_items_are_idle(self):
        self.assertIsNone(self.check([]))
        self.assertIsNone(self.check(["x", None, {"deploy": None}, {"foo": 1}]))

    def test_non_list_answer_raises(self):
        for answer in (None, {"message": "unauthorized"}, "oops"):
            with self.subTest(answer=answer), self.assertRaises(TypeError):
                self.check(answer)


class BusyDeployTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(dt.time, "sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_names_the_running_deploy(self):
        answers = {
            "/services/srv-api/deploys?limit=10": [wrapped("dep-a", "live")],
            "/services/srv-web/deploys?limit=10": [
                wrapped("dep-w", "build_in_progress")
            ],
        }
        with mock.patch.object(dt, "render_get", side_effect=lambda p, k: answers[p]):
            note = dt.busy_deploy(IDS, "k")
        self.assertIn("ochorus-web", note)
        self.assertIn("dep-w", note)
        self.assertIn("build_in_progress", note)

    def test_idle(self):
        with mock.patch.object(dt, "render_get", return_value=[wrapped("d", "live")]):
            self.assertIsNone(dt.busy_deploy(IDS, "k"))

    def test_transient_failure_is_retried(self):
        calls = iter([OSError("reset"), [], []])

        def answer(path, key):
            r = next(calls)
            if isinstance(r, Exception):
                raise r
            return r

        with mock.patch.object(dt, "render_get", side_effect=answer):
            self.assertIsNone(dt.busy_deploy(IDS, "k"))
        self.assertEqual(self.sleep.call_count, 1)

    def test_persistent_failure_raises(self):
        with (
            mock.patch.object(dt, "render_get", side_effect=OSError("down")),
            self.assertRaises(RuntimeError) as cm,
        ):
            dt.busy_deploy(IDS, "k")
        self.assertIn("down", str(cm.exception))
        self.assertEqual(self.sleep.call_count, dt.BUSY_CHECK_ATTEMPTS - 1)


class MainTest(unittest.TestCase):
    """main()'s decision with everything outside the busy check mocked."""

    def run_main(self, *, busy, reason="3 file(s) for ochorus-web", env=None):
        deploy = mock.Mock(return_value="dep-new")
        busy_mock = (
            mock.Mock(side_effect=busy)
            if isinstance(busy, Exception)
            else mock.Mock(return_value=busy)
        )
        with (
            mock.patch.dict(os.environ, {**ENV, **(env or {})}, clear=True),
            mock.patch.object(dt, "green_target", return_value="a" * 40),
            mock.patch.object(dt, "last_deployed", return_value="b" * 40),
            mock.patch.object(dt, "why_deploy", return_value=(reason, "")),
            mock.patch.object(dt, "is_ancestor", return_value=False),
            mock.patch.object(dt, "busy_deploy", busy_mock),
            mock.patch.object(dt, "deploy", deploy),
            mock.patch.object(dt, "wait_for", return_value="live"),
            mock.patch("builtins.print"),
        ):
            code = dt.main()
        return code, deploy, busy_mock

    def test_busy_deploys_nothing_and_stays_green(self):
        code, deploy, _ = self.run_main(
            busy="ochorus-web deploy `dep-w` is still build_in_progress"
        )
        self.assertEqual(code, 0)
        deploy.assert_not_called()

    def test_force_does_not_override_busy(self):
        code, deploy, _ = self.run_main(
            busy="ochorus-web deploy `dep-w` is still build_in_progress",
            reason=None,
            env={"FORCE": "true"},
        )
        self.assertEqual(code, 0)
        deploy.assert_not_called()

    def test_render_unreachable_deploys_nothing_and_goes_red(self):
        code, deploy, _ = self.run_main(busy=RuntimeError("5 attempts failed"))
        self.assertEqual(code, 1)
        deploy.assert_not_called()

    def test_idle_deploys_both_api_first(self):
        code, deploy, _ = self.run_main(busy=None)
        self.assertEqual(code, 0)
        self.assertEqual(
            [c.args[0] for c in deploy.call_args_list], ["srv-api", "srv-web"]
        )

    def test_dry_run_still_checks_and_deploys_nothing(self):
        code, deploy, busy_mock = self.run_main(busy=None, env={"DRY_RUN": "1"})
        self.assertEqual(code, 0)
        busy_mock.assert_called_once()
        deploy.assert_not_called()

    def test_nothing_to_deploy_skips_the_check(self):
        code, deploy, busy_mock = self.run_main(busy=None, reason=None)
        self.assertEqual(code, 0)
        busy_mock.assert_not_called()
        deploy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
