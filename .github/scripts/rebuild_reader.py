"""Rebuild ochorus-web alone at one commit (.github/workflows/rebuild-reader.yml).

The API dispatches this when content changes in its database and the
prerendered reader has to catch up: a language launch, an import publish, a
review approval (library/golive.trigger_web_deploy). It passes the commit the
API runs. Under the deploy train that is also the reader's commit, so the build
finds the API serving exactly the content it checks out and its prebuild gate
passes at once. A build of main's tip could hold content the API hasn't
released yet, and would wait at that gate and then fail.

This doesn't use the web deploy hook, because Render 500s on a hook carrying
`ref=<sha>` (deploy_train.py has the story). It deploys through Render's REST
API with `commitId`, the way the train does.

Refuses, and fails the run, rather than deploy:
- a commit that isn't on main: a leaked dispatch token must not be able to
  ship an arbitrary branch to readers;
- a commit OLDER than the reader's last deploy: that would roll the reader back.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.error

from deploy_train import deploy, is_ancestor, last_deployed

SERVICE = "ochorus-web"


def check(commit: str, last: str | None) -> str | None:
    """Why `commit` must not be deployed, or None when it may."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return f"`{commit}` is not a full commit SHA"
    if not is_ancestor(commit, "HEAD"):
        return f"`{commit[:8]}` is not on main"
    if last and commit != last and is_ancestor(commit, last):
        return f"`{commit[:8]}` is older than the reader's `{last[:8]}`; that would roll it back"
    return None


def main() -> int:
    commit = os.environ.get("COMMIT", "").strip().lower()
    api_key = os.environ.get("RENDER_API_KEY", "").strip()
    service_id = os.environ.get("RENDER_SERVICE_ID_WEB", "").strip()
    last = last_deployed(SERVICE)

    failed = True
    if not (api_key and service_id):
        text = "Not configured: RENDER_API_KEY and RENDER_SERVICE_ID_WEB are both needed."
    elif why := check(commit, last):
        text = f"Not rebuilding {SERVICE}: {why}."
    elif os.environ.get("DRY_RUN"):
        failed = False
        text = f"Would rebuild {SERVICE} at `{commit[:8]}` (dry run)."
    else:
        try:
            text = f"Rebuilding {SERVICE} at `{commit[:8]}`: deploy `{deploy(service_id, commit, api_key)}` started."
            failed = False
        except OSError as e:  # URLError / HTTPError / timeout
            body = ""
            if isinstance(e, urllib.error.HTTPError):
                body = e.read(300).decode("utf-8", "replace").strip()
            text = f"**Deploy failed** ({e})" + (f": `{body}`" if body else "")

    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as f:
            f.write("## Rebuild reader\n\n" + text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
