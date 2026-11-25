"""Unit tests for deploy_train.py: the "never overlap a running deploy" rule
and the "go red when the last web deploy failed or the site lags" check.

Run from .github/scripts:  python3 -m unittest test_deploy_train
No network: Render's HTTP layer (render_get / deploy / wait_for) and the git
and GitHub lookups are mocked.
"""

from __future__ import annotations

import os
import tempfile
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

    def run_main(
        self, *, busy, reason="3 file(s) for ochorus-web", env=None, health=None
    ):
        deploy = mock.Mock(return_value="dep-new")
        self.health = mock.Mock(return_value=health or ([], []))
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
            mock.patch.object(dt, "web_health", self.health),
            mock.patch.object(dt, "deploy", deploy),
            mock.patch.object(dt, "wait_for", return_value="live"),
            mock.patch("builtins.print") as self.printed,
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

    def test_unhealthy_web_goes_red_but_still_deploys(self):
        problem = "last ochorus-web deploy `dep-x` of `cccccccc` ended **build_failed**"
        with tempfile.NamedTemporaryFile("r", suffix=".md") as f:
            code, deploy, _ = self.run_main(
                busy=None,
                health=([problem], []),
                env={"GITHUB_STEP_SUMMARY": f.name},
            )
            written = f.read()
        self.assertEqual(code, 1)
        self.assertEqual(
            [c.args[0] for c in deploy.call_args_list], ["srv-api", "srv-web"]
        )
        self.assertIn(f"**RED: {problem}.**", written)
        self.assertTrue(
            any("::error" in str(c.args[0]) for c in self.printed.call_args_list)
        )

    def test_unhealthy_web_while_busy_is_red_and_deploys_nothing(self):
        code, deploy, _ = self.run_main(
            busy="ochorus-web deploy `dep-w` is still build_in_progress",
            health=(["lags"], []),
        )
        self.assertEqual(code, 1)
        deploy.assert_not_called()

    def test_health_runs_with_nothing_to_deploy(self):
        code, deploy, _ = self.run_main(busy=None, reason=None, health=(["lags"], []))
        self.assertEqual(code, 1)
        self.health.assert_called_once_with("a" * 40, "b" * 40, "srv-web", "k")
        deploy.assert_not_called()

    def test_health_notes_do_not_turn_red(self):
        code, _, _ = self.run_main(
            busy=None, reason=None, health=([], ["Could not check (down)."])
        )
        self.assertEqual(code, 0)


def full(dep_id, status, sha="c" * 40, when="2026-11-17T06:40:00Z"):
    return {
        "deploy": {
            "id": dep_id,
            "status": status,
            "commit": {"id": sha},
            "finishedAt": when,
        },
        "cursor": "c",
    }


class FailedWebDeployTest(unittest.TestCase):
    def check(self, answer):
        with mock.patch.object(dt, "render_get", return_value=answer) as get:
            note = dt.failed_web_deploy("srv-web", "k")
        get.assert_called_once_with("/services/srv-web/deploys?limit=20", "k")
        return note

    def test_failed_statuses_are_named(self):
        for status in (
            "build_failed",
            "update_failed",
            "canceled",
            "pre_deploy_failed",
        ):
            with self.subTest(status=status):
                note = self.check([full("dep-x", status)])
                self.assertIn("dep-x", note)
                self.assertIn("cccccccc", note)
                self.assertIn(status, note)
                self.assertIn("2026-11-17T06:40:00Z", note)

    def test_live_or_deactivated_is_fine(self):
        self.assertIsNone(self.check([full("dep-1", "live")]))
        self.assertIsNone(self.check([full("dep-1", "deactivated")]))

    def test_running_deploy_is_skipped_for_the_finished_one_before_it(self):
        answer = [
            full("dep-run", "build_in_progress"),
            full("dep-bad", "build_failed"),
            full("dep-ok", "live"),
        ]
        self.assertIn("dep-bad", self.check(answer))
        answer = [full("dep-run", "queued"), full("dep-ok", "live")]
        self.assertIsNone(self.check(answer))

    def test_a_failure_before_a_live_deploy_is_history(self):
        answer = [full("dep-ok", "live"), full("dep-bad", "build_failed")]
        self.assertIsNone(self.check(answer))

    def test_empty_and_junk_are_fine(self):
        self.assertIsNone(self.check([]))
        self.assertIsNone(self.check(["x", None, {"deploy": None}]))

    def test_non_list_answer_raises(self):
        with self.assertRaises(TypeError):
            self.check({"message": "unauthorized"})


class SpendCapHintTest(unittest.TestCase):
    def deploy(self, status, created, finished):
        return {"status": status, "createdAt": created, "finishedAt": finished}

    def test_a_build_that_fails_at_once_names_the_spend_limit(self):
        d = self.deploy("build_failed", "2026-11-20T22:11:05Z", "2026-11-20T22:11:31Z")
        hint = dt.spend_cap_hint(d)
        self.assertIn("26s", hint)
        self.assertIn("spend limit", hint)

    def test_a_build_that_ran_and_failed_is_an_ordinary_failure(self):
        d = self.deploy("build_failed", "2026-11-20T22:11:05Z", "2026-11-20T22:31:05Z")
        self.assertIsNone(dt.spend_cap_hint(d))

    def test_other_statuses_and_missing_times_give_no_hint(self):
        quick = ("2026-11-20T22:11:05Z", "2026-11-20T22:11:06Z")
        self.assertIsNone(dt.spend_cap_hint(self.deploy("update_failed", *quick)))
        self.assertIsNone(dt.spend_cap_hint(self.deploy("build_failed", None, None)))
        self.assertIsNone(dt.spend_cap_hint({}))

    def test_the_failed_web_note_carries_it(self):
        d = {
            "id": "dep-cap",
            "status": "build_failed",
            "commit": {"id": "c" * 40},
            "createdAt": "2026-11-20T22:11:05Z",
            "finishedAt": "2026-11-20T22:11:20Z",
        }
        with mock.patch.object(dt, "render_get", return_value=[{"deploy": d}]):
            note = dt.failed_web_deploy("srv-web", "k")
        self.assertIn("spend limit", note)


HOUR = 3600
NOW = 1_800_000_000


class WebLagTest(unittest.TestCase):
    def lag(self, *, pending, last="b" * 40, ancestor=False, exists=True, hours=6.0):
        with (
            mock.patch.object(dt, "commit_exists", return_value=exists),
            mock.patch.object(dt, "is_ancestor", return_value=ancestor),
            mock.patch.object(dt, "pending_since", return_value=pending) as ps,
        ):
            note = dt.web_lag("a" * 40, last, hours, NOW)
        return note, ps

    def test_old_pending_change_is_red(self):
        note, _ = self.lag(pending=("d" * 40, NOW - 7 * HOUR))
        self.assertIn("bbbbbbbb", note)
        self.assertIn("aaaaaaaa", note)
        self.assertIn("dddddddd", note)
        self.assertIn("7.0h", note)

    def test_recent_pending_change_is_fine(self):
        note, _ = self.lag(pending=("d" * 40, NOW - 5 * HOUR))
        self.assertIsNone(note)

    def test_limit_is_configurable(self):
        note, _ = self.lag(pending=("d" * 40, NOW - 5 * HOUR), hours=4)
        self.assertIn("limit 4h", note)

    def test_nothing_deployable_pending_is_fine(self):
        self.assertIsNone(self.lag(pending=None)[0])

    def test_up_to_date_or_unknown_is_not_measured(self):
        for kwargs in ({"ancestor": True}, {"last": None}, {"exists": False}):
            with self.subTest(**kwargs):
                note, ps = self.lag(pending=("d" * 40, 0), **kwargs)
                self.assertIsNone(note)
                ps.assert_not_called()

    def test_env_limit(self):
        for raw, want in (("", 6.0), ("2.5", 2.5), ("junk", 6.0), ("0", 6.0)):
            with (
                self.subTest(raw=raw),
                mock.patch.dict(os.environ, {"MAX_WEB_LAG_HOURS": raw}),
            ):
                self.assertEqual(dt.max_web_lag_hours(), want)


RENDER_YAML = """
services:
  - name: ochorus-api
    rootDir: backend
  - name: ochorus-web
    buildFilter:
      paths: ["frontend/**"]
      ignoredPaths: ["frontend/**/*.test.ts"]
"""


class PendingSinceTest(unittest.TestCase):
    def test_oldest_deployable_commit_wins(self):
        diffs = {
            "c1": "docs/readme.md\nfrontend/src/x.test.ts",
            "c2": "frontend/src/app.ts",
            "c3": "backend/x.py",
        }

        def fake_sh(*args):
            if args[:2] == ("git", "show"):
                return RENDER_YAML
            if args[:2] == ("git", "log"):
                self.assertEqual(args[-1], "last..target")
                return "c1 100\nc2 200\nc3 300"
            if args[:2] == ("git", "diff"):
                return diffs[args[-1]]
            raise AssertionError(args)

        with mock.patch.object(dt, "sh", side_effect=fake_sh):
            self.assertEqual(dt.pending_since("last", "target"), ("c2", 200))

    def test_nothing_deployable(self):
        def fake_sh(*args):
            if args[:2] == ("git", "show"):
                return RENDER_YAML
            if args[:2] == ("git", "log"):
                return "c1 100"
            return "docs/readme.md"

        with mock.patch.object(dt, "sh", side_effect=fake_sh):
            self.assertIsNone(dt.pending_since("last", "target"))


class WebHealthTest(unittest.TestCase):
    def test_collects_both_problems(self):
        with (
            mock.patch.object(dt, "failed_web_deploy", return_value="failed"),
            mock.patch.object(dt, "web_lag", return_value="lags"),
        ):
            self.assertEqual(
                dt.web_health("a", "b", "srv-web", "k"), (["failed", "lags"], [])
            )

    def test_render_error_is_a_note_and_lag_still_runs(self):
        with (
            mock.patch.object(dt, "failed_web_deploy", side_effect=OSError("down")),
            mock.patch.object(dt, "web_lag", return_value="lags"),
        ):
            problems, notes = dt.web_health("a", "b", "srv-web", "k")
        self.assertEqual(problems, ["lags"])
        self.assertIn("down", notes[0])

    def test_lag_error_is_a_note(self):
        with (
            mock.patch.object(dt, "failed_web_deploy", return_value=None),
            mock.patch.object(dt, "web_lag", side_effect=ValueError("bad log")),
        ):
            problems, notes = dt.web_health("a", "b", "srv-web", "k")
        self.assertEqual(problems, [])
        self.assertIn("bad log", notes[0])

    def test_without_a_key_only_the_lag_is_checked(self):
        with (
            mock.patch.object(dt, "failed_web_deploy") as failed,
            mock.patch.object(dt, "web_lag", return_value=None),
        ):
            self.assertEqual(dt.web_health("a", "b", "srv-web", ""), ([], []))
        failed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
