"""Deploy main to Render in batches: the deploy train (.github/workflows/deploy-train.yml).

Every merge used to deploy at once, and with ~50 merges a day the ~21-minute
web prerender ran nearly back to back while the API rebuilt its Docker image
for each backend commit. The train runs on a schedule instead, and deploys
only when something deployable changed since the last train.

What it does, in order:

1. TARGET: the newest first-parent commit on main whose `test-and-build`
   check passed (the same gate branch protection requires). A commit still in
   CI, or red, is passed over for an older green one.
2. LAST: the commit ochorus-web last deployed successfully, read from the
   GitHub deployments Render reports ("main - ochorus-web").
3. Deploy if a file in LAST..TARGET matches any service's render.yaml
   buildFilter (or rootDir), or if FORCE is set.
4. Unless a deploy is still RUNNING on ochorus-api or ochorus-web: then
   deploy nothing, say which deploy (id + status) in one line, and exit green;
   the next train picks the work up. FORCE does not override this.
5. Ask Render's REST API to deploy TARGET (`commitId`) on the API, WAIT for
   that deploy to finish, then deploy the web service at the same commit, so
   both move together and the web build's prebuild gate finds the API serving
   exactly the content it checks out.
   The email cron is not on the train: Render's API cannot pin a cron job to
   a commit, so it auto-deploys on its own (render.yaml).

WHY THE REST API, NOT DEPLOY HOOKS. Render documents `?ref=<sha>` on a deploy
hook, but on 2026-10-14 every hook call carrying it answered 500 while the
same hook without it deployed fine. Without a ref a hook builds the branch
tip, which may be red or newer than what the API holds. The REST endpoint
takes `commitId` and does not touch the service's auto-deploy setting.

WHY THE WEB WAITS FOR THE API. The two used to start at the same moment. The
prebuild gate only waits for the API's CONTENT, so when a train carried
backend code but no content change, the gate passed at once and the web
prerendered ~an hour of pages against an API that was meanwhile building,
running its `release` (seeds, citation index, search vectors) against the
live database and cutting over. On 2026-11-13 (train at 5a294ec) a request
landed in that window, got a 500 that outlasted apiFetch's ~15s of retries,
and failed the web build 39 minutes in (/scripture/matthew/7/29/). The same
page rendered fine before and after. Starting the web build only once the
API deploy is over closes the window. If the API deploy fails, the web still
deploys (it may well be a frontend-only change) and the run goes red.

WHY A RUNNING DEPLOY STOPS THE TRAIN. The train waits for the API deploy
but only STARTS the web one and exits; the web build then runs 20-70 minutes,
crawling the live API. On 2026-11-19 a manual run at 05:57 UTC started a web
build at 06:05; the scheduled run at 06:22 redeployed ochorus-api (the
cutover restarts it) under that crawl and started a second web deploy at
06:31. The first web build failed; the second took 68 minutes. So before
deploying anything the train asks Render for each service's recent deploys,
and any status outside DONE (created, queued, build_in_progress,
update_in_progress, pre_deploy_in_progress, ...) means "busy": deploy
nothing, exit 0. That is green on purpose: production is not frozen, it is
mid-deploy, and the next scheduled run deploys whatever is still pending.
FORCE means "deploy even if nothing changed", not "interrupt a build", so it
waits too; to really cut a build short, cancel it in Render's dashboard and
re-run. If Render cannot be asked (after BUSY_CHECK_ATTEMPTS tries), the run
deploys nothing and goes RED: deploying blind could restart the API under a
running crawl, and a run that silently skipped would hide a broken key.
DRY_RUN still asks (it is read-only) and reports what it found.

Needs the RENDER_API_KEY secret and the two service IDs (plain env in the
workflow). Until the key is set the train deploys nothing and fails the run,
so a half-configured train shows red instead of silently doing nothing.
DRY_RUN=1 prints the decision and deploys nothing.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

REPO = os.environ.get("GITHUB_REPOSITORY", "jdegreef/ochorus")
GATE = "test-and-build"
# The service whose last deploy tells us where production is. The web build
# is the expensive one, and the train always moves every service together.
ANCHOR = "ochorus-web"
# The two services the train moves, and the env var holding each one's Render
# service ID (srv-…, shown at the top of the service's page; not a secret).
# Both are required: the content gate couples them, so one without the other
# fails the web build. ochorus-lifecycle-email is deliberately absent (see top).
SERVICE_ID_VARS = {
    "ochorus-api": "RENDER_SERVICE_ID_API",
    "ochorus-web": "RENDER_SERVICE_ID_WEB",
}
RENDER_API = "https://api.render.com/v1"
LOOKBACK = 60  # commits to search for a green one
# How long to wait for the API deploy before starting the web one anyway. An
# API deploy (Docker build + `release`) is well under this; the workflow's
# timeout-minutes leaves room for it plus the rest of the run.
API_WAIT_SECONDS = 40 * 60
POLL_SECONDS = 30
# Render deploy statuses that mean "over". `live` is the only good one.
DONE = {
    "live",
    "deactivated",
    "build_failed",
    "update_failed",
    "canceled",
    "pre_deploy_failed",
}
# Any other status (created, queued, build_in_progress, update_in_progress,
# pre_deploy_in_progress, or one Render adds later) counts as RUNNING, and a
# running deploy on either service stops the train (see "WHY A RUNNING
# DEPLOY STOPS THE TRAIN"). Asking Render is retried this many times,
# POLL_SECONDS apart, before the run gives up and goes red.
BUSY_CHECK_ATTEMPTS = 5


def sh(*args: str) -> str:
    return subprocess.run(
        args, check=True, capture_output=True, text=True
    ).stdout.strip()


def gh_api(path: str):
    return json.loads(sh("gh", "api", path))


def is_green(sha: str) -> bool:
    runs = gh_api(f"repos/{REPO}/commits/{sha}/check-runs?check_name={GATE}")[
        "check_runs"
    ]
    return any(r["conclusion"] == "success" for r in runs)


def green_target() -> str | None:
    for sha in sh("git", "rev-list", "--first-parent", f"-n{LOOKBACK}", "HEAD").split():
        if is_green(sha):
            return sha
    return None


def last_deployed(service: str) -> str | None:
    env = urllib.parse.quote(f"main - {service}")
    for d in gh_api(f"repos/{REPO}/deployments?environment={env}&per_page=30"):
        states = {
            s["state"] for s in gh_api(f"repos/{REPO}/deployments/{d['id']}/statuses")
        }
        if "success" in states:
            return d["sha"]
    return None


def is_ancestor(a: str, b: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", a, b], check=False
        ).returncode
        == 0
    )


def service_globs(render_yaml: str) -> dict[str, tuple[list[str], list[str]]]:
    """service name → (paths, ignoredPaths), as Render decides auto-deploys."""
    out = {}
    for svc in yaml.safe_load(render_yaml)["services"]:
        bf = svc.get("buildFilter") or {}
        paths = bf.get("paths") or [f"{svc.get('rootDir', '').strip('/')}/**"]
        out[svc["name"]] = (paths, bf.get("ignoredPaths") or [])
    return out


def deployable(path: str, paths: list[str], ignored: list[str]) -> bool:
    # fnmatch's `*` crosses `/`, so `backend/**` and `backend/**/tests*.py`
    # match the way Render's globs do for the patterns render.yaml uses.
    hit = any(fnmatch.fnmatchcase(path, g) for g in paths)
    return hit and not any(fnmatch.fnmatchcase(path, g) for g in ignored)


def deploy(service_id: str, sha: str, api_key: str) -> str:
    """Start a deploy of `sha` on one Render service; returns its deploy id."""
    req = urllib.request.Request(
        f"{RENDER_API}/services/{service_id}/deploys",
        data=json.dumps({"commitId": sha}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        # 201 carries the new deploy; a deploy QUEUED behind a running one comes
        # back 202 with an empty body (2026-10-14), which is a success too.
        try:
            body = json.loads(res.read() or b"{}")
        except ValueError:
            body = None
        return (isinstance(body, dict) and body.get("id")) or f"HTTP {res.status}"


def render_get(path: str, api_key: str):
    req = urllib.request.Request(
        f"{RENDER_API}{path}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read() or b"null")


def find_deploy(service_id: str, sha: str, api_key: str) -> str | None:
    """The id of the newest deploy of `sha` on a service (a queued deploy's
    POST returns no id, so it is looked up), or None."""
    for item in render_get(f"/services/{service_id}/deploys?limit=10", api_key) or []:
        d = item.get("deploy", item) if isinstance(item, dict) else {}
        if (d.get("commit") or {}).get("id") == sha:
            return d.get("id")
    return None


def running_deploy(service_id: str, api_key: str) -> tuple[str, str] | None:
    """(id, status) of a deploy on a service that is not over yet, or None.

    Render lists deploys newest first, each as {"deploy": {...}, "cursor": ...};
    a bare {...} is accepted too. Anything that is not a list raises, so a
    garbled answer is never read as "nothing running".
    """
    items = render_get(f"/services/{service_id}/deploys?limit=10", api_key)
    if not isinstance(items, list):
        raise TypeError(f"unexpected deploy list from Render: {str(items)[:200]}")
    for item in items:
        d = item.get("deploy", item) if isinstance(item, dict) else None
        status = d.get("status") if isinstance(d, dict) else None
        if status and status not in DONE:
            return str(d.get("id") or "?"), status
    return None


def busy_deploy(ids: dict[str, str], api_key: str) -> str | None:
    """A note naming a deploy still running on a train service, or None.

    Retried BUSY_CHECK_ATTEMPTS times; if Render never answers, raises
    RuntimeError, because "could not tell" must not be treated as "idle".
    """
    error: Exception | None = None
    for attempt in range(1, BUSY_CHECK_ATTEMPTS + 1):
        try:
            for service, service_id in ids.items():
                if hit := running_deploy(service_id, api_key):
                    return f"{service} deploy `{hit[0]}` is still {hit[1]}"
            return None
        except Exception as e:  # noqa: BLE001 — HTTPError / URLError / timeout / bad JSON
            error = e
            print(
                f"  (checking for a running deploy failed,"
                f" attempt {attempt}/{BUSY_CHECK_ATTEMPTS}: {e})",
                flush=True,
            )
            if attempt < BUSY_CHECK_ATTEMPTS:
                time.sleep(POLL_SECONDS)
    raise RuntimeError(f"{BUSY_CHECK_ATTEMPTS} attempts failed, last: {error}")


def wait_for(service_id: str, deploy_id: str, sha: str, api_key: str) -> str:
    """Poll a deploy until it is over; returns its final status, or 'timeout'.

    A failed poll is retried, not fatal: losing track of the API deploy must
    not keep the web from deploying, only delay it to the timeout.
    """
    deadline = time.monotonic() + API_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            if not deploy_id.startswith("dep-"):
                deploy_id = find_deploy(service_id, sha, api_key) or deploy_id
            if deploy_id.startswith("dep-"):
                status = (
                    render_get(f"/services/{service_id}/deploys/{deploy_id}", api_key)
                    or {}
                ).get("status")
                if status in DONE:
                    return status
        except Exception as e:  # HTTPError / URLError / timeout / bad JSON
            print(f"  (poll failed, retrying: {e})", flush=True)
        time.sleep(POLL_SECONDS)
    return "timeout"


def why_deploy(target: str, last: str | None) -> tuple[str | None, str]:
    """(reason to deploy or None, a note for the summary)."""
    if last is None:
        return "no recorded deploy to compare against", ""
    if subprocess.run(
        ["git", "cat-file", "-e", f"{last}^{{commit}}"],
        check=False,
        capture_output=True,
    ).returncode:
        return f"last deploy {last[:8]} is not on main any more", ""
    if is_ancestor(target, last):
        return None, "Production already holds the target."
    changed = sh("git", "diff", "--name-only", last, target).splitlines()
    globs = service_globs(sh("git", "show", f"{target}:render.yaml"))
    counts = {
        name: n
        for name, (paths, ignored) in globs.items()
        if (n := sum(deployable(p, paths, ignored) for p in changed))
    }
    if not counts:
        return None, f"{len(changed)} file(s) changed, none deployable."
    return ", ".join(f"{n} file(s) for {name}" for name, n in counts.items()), ""


def main() -> int:
    target = green_target()
    if target is None:
        print(
            f"No commit in the last {LOOKBACK} has a passing {GATE}; nothing to deploy."
        )
        return 0
    last = last_deployed(ANCHOR)
    summary = [
        f"target `{target[:8]}` · last {ANCHOR} deploy `{(last or 'unknown')[:8]}`"
    ]

    reason, note = why_deploy(target, last)
    # Force redeploys the target, but never moves production BACK: an older
    # API would run old code against a schema its newer deploy migrated.
    rollback = last is not None and target != last and is_ancestor(target, last)
    if (
        reason is None
        and os.environ.get("FORCE", "").lower() == "true"
        and not rollback
    ):
        reason = "forced"
    if note:
        summary.append(note)

    api_key = os.environ.get("RENDER_API_KEY", "").strip()
    ids = {svc: os.environ.get(var, "").strip() for svc, var in SERVICE_ID_VARS.items()}
    missing = [var for svc, var in SERVICE_ID_VARS.items() if not ids[svc]]
    if not api_key:
        missing.insert(0, "RENDER_API_KEY")
    failed = False
    busy = None
    if reason and not missing:
        # Never overlap a deploy that is still running (see "WHY A RUNNING
        # DEPLOY STOPS THE TRAIN"). FORCE does not override this.
        try:
            busy = busy_deploy(ids, api_key)
        except RuntimeError as e:
            # Unknown is not "idle": deploying blind could restart the API under
            # a web build that is crawling it. Go red instead.
            failed = True
            busy = f"**could not ask Render whether a deploy is running** ({e})"
    if reason and missing:
        # All or nothing: a web build without its API deploy waits on content
        # the API never serves and fails 15 minutes later. And the run goes RED:
        # a green run here hid two days of undeployed main (2026-10-05 → 07)
        # while every web auto-deploy timed out waiting on a stale API.
        failed = True
        summary.append(
            f"Would deploy ({reason}), but **not configured**: {', '.join(missing)}."
        )
    elif reason and busy:
        summary.append(
            f"Would deploy ({reason}), but {busy}. Deployed nothing;"
            " the next train picks this up."
        )
    elif reason:
        summary.append(f"Deploying {' and '.join(ids)} to `{target[:8]}`: {reason}.")
        # The API first, waited on; then the web (see "WHY THE WEB WAITS").
        for service, service_id in ids.items():
            if os.environ.get("DRY_RUN"):
                summary.append(f"- {service}: would deploy (dry run)")
                continue
            # Each service on its own: one failing must not strand the other.
            try:
                deploy_id = deploy(service_id, target, api_key)
                summary.append(f"- {service}: deploy `{deploy_id}` started")
            except Exception as e:  # HTTPError / URLError / timeout / anything
                # Never let one service's failure skip the other's deploy.
                failed = True
                # Render's error body says why (a bad commit, a bad key...);
                # the status line alone does not.
                body = ""
                if isinstance(e, urllib.error.HTTPError):
                    body = e.read(300).decode("utf-8", "replace").strip()
                summary.append(
                    f"- {service}: **deploy failed** ({e})"
                    + (f": `{body}`" if body else "")
                )
                continue
            if service == "ochorus-api":
                print(
                    f"Waiting for {service} `{deploy_id}` before starting the web build…",
                    flush=True,
                )
                status = wait_for(service_id, deploy_id, target, api_key)
                if status != "live":
                    failed = True
                summary.append(
                    f"  - {service}: {status}"
                    + (
                        ""
                        if status == "live"
                        else " (**not live**; deploying the web anyway)"
                    )
                )

    text = "\n".join(summary)
    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as f:
            f.write("## Deploy train\n\n" + text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
