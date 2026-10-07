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
4. Fire EVERY service's deploy hook with `ref=TARGET`. All three services move
   to the same commit together. That keeps two promises: the web build's
   prebuild gate finds the API serving exactly the content it checks out, and
   the API's own commit (RENDER_GIT_COMMIT) is a safe `ref` for the rebuilds
   the admin fires between trains (library/golive.trigger_web_deploy).

Until both the API and web hook secrets are set the train deploys nothing
(it reports what it would have done), so it is harmless before it is set up.
A failed hook fails the run, so it shows red in Actions. DRY_RUN=1 prints the decision and fires
nothing.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import yaml

REPO = os.environ.get("GITHUB_REPOSITORY", "jdegreef/ochorus")
GATE = "test-and-build"
# The service whose last deploy tells us where production is. The web build
# is the expensive one, and the train always moves every service together.
ANCHOR = "ochorus-web"
HOOK_SECRETS = {
    "ochorus-api": "RENDER_DEPLOY_HOOK_API",
    "ochorus-web": "RENDER_DEPLOY_HOOK_WEB",
    "ochorus-lifecycle-email": "RENDER_DEPLOY_HOOK_CRON",
}
# The two the content gate couples: one without the other fails the web build.
# The cron only shares the API's image, so a train can ship without it.
REQUIRED = ("ochorus-api", "ochorus-web")
LOOKBACK = 60  # commits to search for a green one


def sh(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def gh_api(path: str):
    return json.loads(sh("gh", "api", path))


def is_green(sha: str) -> bool:
    runs = gh_api(f"repos/{REPO}/commits/{sha}/check-runs?check_name={GATE}")["check_runs"]
    return any(r["conclusion"] == "success" for r in runs)


def green_target() -> str | None:
    for sha in sh("git", "rev-list", "--first-parent", f"-n{LOOKBACK}", "HEAD").split():
        if is_green(sha):
            return sha
    return None


def last_deployed(service: str) -> str | None:
    env = urllib.parse.quote(f"main - {service}")
    for d in gh_api(f"repos/{REPO}/deployments?environment={env}&per_page=30"):
        states = {s["state"] for s in gh_api(f"repos/{REPO}/deployments/{d['id']}/statuses")}
        if "success" in states:
            return d["sha"]
    return None


def is_ancestor(a: str, b: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], check=False).returncode == 0


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


def fire(hook: str, sha: str) -> int:
    url = urllib.parse.urlsplit(hook)
    query = urllib.parse.urlencode(urllib.parse.parse_qsl(url.query) + [("ref", sha)])
    req = urllib.request.Request(url._replace(query=query).geturl(), method="POST")
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.status


def why_deploy(target: str, last: str | None) -> tuple[str | None, str]:
    """(reason to deploy or None, a note for the summary)."""
    if last is None:
        return "no recorded deploy to compare against", ""
    if subprocess.run(
        ["git", "cat-file", "-e", f"{last}^{{commit}}"], check=False, capture_output=True
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
        print(f"No commit in the last {LOOKBACK} has a passing {GATE}; nothing to deploy.")
        return 0
    last = last_deployed(ANCHOR)
    summary = [f"target `{target[:8]}` · last {ANCHOR} deploy `{(last or 'unknown')[:8]}`"]

    reason, note = why_deploy(target, last)
    # Force redeploys the target, but never moves production BACK: an older
    # API would run old code against a schema its newer deploy migrated.
    rollback = last is not None and target != last and is_ancestor(target, last)
    if reason is None and os.environ.get("FORCE", "").lower() == "true" and not rollback:
        reason = "forced"
    if note:
        summary.append(note)

    hooks = {svc: os.environ.get(secret, "").strip() for svc, secret in HOOK_SECRETS.items()}
    failed = False
    if reason and not all(hooks[svc] for svc in REQUIRED):
        # All or nothing: a web build without its API deploy waits on content
        # the API never serves and fails 15 minutes later. And the run goes RED:
        # a green run here hid two days of undeployed main (2026-10-05 → 07)
        # while every web auto-deploy timed out waiting on a stale API.
        failed = True
        missing = ", ".join(HOOK_SECRETS[svc] for svc in REQUIRED if not hooks[svc])
        summary.append(f"Would deploy ({reason}), but **not configured**: {missing}.")
    elif reason:
        summary.append(f"Deploying all services to `{target[:8]}`: {reason}.")
        for service, hook in hooks.items():
            if not hook:
                summary.append(f"- {service}: skipped, secret {HOOK_SECRETS[service]} is not set")
            elif os.environ.get("DRY_RUN"):
                summary.append(f"- {service}: would deploy (dry run)")
            else:
                # Each hook on its own: one failing must not strand the others.
                try:
                    summary.append(f"- {service}: hook returned {fire(hook, target)}")
                except OSError as e:  # URLError / HTTPError / timeout
                    failed = True
                    summary.append(f"- {service}: **hook failed** ({e})")

    text = "\n".join(summary)
    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as f:
            f.write("## Deploy train\n\n" + text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
