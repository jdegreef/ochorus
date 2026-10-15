"""Replace ochorus-web's redirect/rewrite rules with the list in render.yaml.

A Blueprint sync only ADDS and UPDATES routing rules; it never deletes one.
Rules dropped from render.yaml therefore pile up on the service, and once
they reach Render's 200-rule cap for a static site every sync fails at
"Update web service ochorus-web routes" (taking the headers with it). That is
what happened from the Vietnamese locale (#5673) on; #6064 cut render.yaml to
59 rules, but the leftovers on the service still have to go.

Render's REST API has the one call that deletes: PUT /services/{id}/routes
replaces the service's whole list, in order (first rule = highest priority).
This script sends render.yaml's `routes:` for ochorus-web through it. Run it
once, then click Manual sync on the Blueprint; from then on the sync has
headroom again. Run it again any time rules were REMOVED from render.yaml.

    RENDER_API_KEY=rnd_… python3 .github/scripts/render_replace_routes.py --dry-run
    RENDER_API_KEY=rnd_… python3 .github/scripts/render_replace_routes.py

RENDER_SERVICE_ID_WEB overrides the service id (default: ochorus-web's).
--dry-run prints current vs desired and the diff, and changes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

RENDER_API = "https://api.render.com/v1"
SERVICE = "ochorus-web"
DEFAULT_SERVICE_ID = "srv-d948c44vikkc73brci5g"
RENDER_YAML = Path(__file__).resolve().parents[2] / "render.yaml"
PAGE = 100  # the list endpoint's maximum


def desired_routes() -> list[dict]:
    services = yaml.safe_load(RENDER_YAML.read_text())["services"]
    (web,) = [s for s in services if s["name"] == SERVICE]
    return [{k: r[k] for k in ("type", "source", "destination")} for r in web["routes"]]


def call(method: str, path: str, api_key: str, body=None):
    req = urllib.request.Request(
        f"{RENDER_API}{path}",
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read() or b"null")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} → HTTP {e.code}: {e.read().decode(errors='replace')}")


def current_routes(service_id: str, api_key: str) -> list[dict]:
    """The service's rules in priority order (first = highest)."""
    out, cursor = [], None
    while True:
        query = {"limit": PAGE, **({"cursor": cursor} if cursor else {})}
        page = call("GET", f"/services/{service_id}/routes?{urllib.parse.urlencode(query)}", api_key)
        out += [item["route"] for item in page]
        if len(page) < PAGE:
            break
        cursor = page[-1]["cursor"]
    out.sort(key=lambda r: r["priority"])
    return [{k: r[k] for k in ("type", "source", "destination")} for r in out]


def fmt(r: dict) -> str:
    return f"{r['type']:8} {r['source']} -> {r['destination']}"


def report(current: list[dict], desired: list[dict]) -> None:
    cur, want = {fmt(r) for r in current}, {fmt(r) for r in desired}
    print(f"current rules on {SERVICE}: {len(current)}")
    print(f"desired rules (render.yaml): {len(desired)}")
    removed = [fmt(r) for r in current if fmt(r) not in want]
    added = [fmt(r) for r in desired if fmt(r) not in cur]
    print(f"\n- {len(removed)} to remove")
    for line in removed:
        print(f"  - {line}")
    print(f"\n+ {len(added)} to add")
    for line in added:
        print(f"  + {line}")
    kept_order = [fmt(r) for r in current if fmt(r) in want]
    if kept_order != [fmt(r) for r in desired if fmt(r) in cur]:
        print("\n~ the kept rules also change priority order")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="show the diff; change nothing")
    args = parser.parse_args()

    api_key = os.environ.get("RENDER_API_KEY")
    if not api_key:
        sys.exit("Set RENDER_API_KEY (Render → Account Settings → API Keys).")
    service_id = os.environ.get("RENDER_SERVICE_ID_WEB", DEFAULT_SERVICE_ID)

    desired = desired_routes()
    current = current_routes(service_id, api_key)
    report(current, desired)

    if current == desired:
        print("\nAlready in sync; nothing to do.")
        return
    if args.dry_run:
        print("\nDry run: nothing changed.")
        return

    call("PUT", f"/services/{service_id}/routes", api_key, desired)
    after = current_routes(service_id, api_key)
    if after != desired:
        sys.exit(f"\nPUT returned, but the service now holds {len(after)} rules that differ from render.yaml.")
    print(f"\nReplaced: {SERVICE} now holds exactly render.yaml's {len(after)} rules.")
    print("Next: Render → Blueprints → Ochorus → Manual sync, and check the Syncs tab goes green.")


if __name__ == "__main__":
    main()
