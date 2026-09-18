#!/usr/bin/env python3
"""Paint covers: take works you have added to `CURATED` all the way to shippable.

    uv run python scripts/paint_covers.py <slug> [<slug> ...]
    uv run python scripts/paint_covers.py <slug> --dry-run     # say what would run
    uv run python scripts/paint_covers.py <slug> --no-check    # skip the gates

THE ONE HUMAN STEP COMES FIRST: choose the painting and add each work's entry to
`library/curated_art.py` (`.claude/skills/level-up-cover` is how to choose one).
Everything after that is mechanical, and was eight hand-run commands in an order
that mattered, each with a gotcha that had bitten a run. This runs them, in
that order, and stops at the first failure:

  1. clear stale `__pycache__`   — a stale .pyc hides a new CURATED entry
  2. migrate                     — a worktree's copied DB can predate main
  3. build_curated_covers        — the painting, PD re-verified at fetch
  4. delete the retired plates   — every `<slug>.svg`, in every language dir
  5. build_cover_assets          — webp variants; repoints EVERY edition row
  6. tune_art_scrim              — measured scrim, BEFORE the twins are drawn
  7. npm run og:covers           — the per-edition share twins
  8. keep only these works' twins — the generator can redraw others' bytes
  9. the cover gates             — Python fixture gates and the JS twin gates

Each stage is the existing tool that owns that job; this file only decides the
order and does the two chores no tool owned (4 and 8). So a fix to how a stage
works belongs in that stage's tool, not here.

Run from `backend/`. Needs the frontend's `node_modules` (for step 7) and Node
22 on PATH — see `frontend/.nvmrc`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend"
COVERS = FRONTEND / "static" / "covers"
sys.path.insert(0, str(BACKEND))

# Django-free, like the scripts it drives.
from library.curated_art import CURATED  # noqa: E402

PY = ["uv", "run", "python"]


def step(n: int, title: str) -> None:
    print(f"\n── {n}. {title}", flush=True)


def run(cmd: list[str], cwd: Path, dry: bool) -> None:
    print("   $ " + " ".join(cmd), flush=True)
    if not dry:
        subprocess.run(cmd, cwd=cwd, check=True)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def is_theirs(path: str, slugs: set[str]) -> bool:
    """Is a changed twin PNG (`frontend/static/covers/[<lang>/]<slug>.png`) one
    of the works being painted? A twin's filename IS its slug."""
    return Path(path).stem in slugs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="+", help="Works already added to CURATED.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; change nothing.")
    ap.add_argument("--no-check", action="store_true", help="Skip the gates at the end.")
    args = ap.parse_args()
    slugs = set(args.slugs)
    dry = args.dry_run

    # Refuse before anything runs: a slug missing from CURATED would sail
    # through every stage as a no-op and "succeed" having painted nothing.
    missing = sorted(slugs - set(CURATED))
    if missing:
        raise SystemExit(
            f"Not in library/curated_art.py CURATED: {', '.join(missing)}. "
            "Choose the painting and add its entry first — that is the one step "
            "this cannot do (see .claude/skills/level-up-cover)."
        )
    if not (FRONTEND / "node_modules").is_dir():
        raise SystemExit("frontend/node_modules is missing — run `npm ci` in frontend/ first.")
    # Step 8 reverts files this run did not mean to change, so it must be able to
    # tell them from changes that were already here. Start from a clean tree.
    if not dry and git("status", "--porcelain", "--", "frontend/static/covers").strip():
        raise SystemExit(
            "frontend/static/covers has uncommitted changes. Commit or stash them "
            "first: step 8 restores any twin this run redraws outside your works, "
            "and would not be able to tell those from yours."
        )

    step(1, "clear stale __pycache__")
    caches = [c for c in BACKEND.rglob("__pycache__") if ".venv" not in c.parts]
    print(f"   {len(caches)} __pycache__ dir(s)")
    if not dry:
        for cache in caches:
            shutil.rmtree(cache)

    step(2, "migrate")
    run([*PY, "manage.py", "migrate", "--noinput"], BACKEND, dry)

    step(3, "fetch and crop the paintings")
    run([*PY, "manage.py", "build_curated_covers", *sorted(slugs)], BACKEND, dry)

    step(4, "delete the retired plates")
    for slug in sorted(slugs):
        for plate in sorted(COVERS.rglob(f"{slug}.svg")):
            print(f"   rm {plate.relative_to(ROOT)}")
            if not dry:
                plate.unlink()

    step(5, "variants, and repoint every edition")
    run([*PY, "scripts/build_cover_assets.py"], BACKEND, dry)

    step(6, "measure the scrim (before the twins, which are drawn with it)")
    run([*PY, "scripts/tune_art_scrim.py"], BACKEND, dry)

    step(7, "draw the share twins")
    run(["npm", "run", "og:covers"], FRONTEND, dry)

    step(8, "keep only these works' twins")
    if not dry:
        changed = [
            line[3:]
            for line in git("status", "--porcelain", "--", "frontend/static/covers").splitlines()
            if line.endswith(".png") and line[:2].strip() == "M"
        ]
        # The generator redraws any twin its skip cannot vouch for, and a redraw
        # on a different Chromium build moves bytes without moving the design.
        # Those are someone else's twins; the manifest gate reads INPUT digests,
        # not PNG bytes, so putting their bytes back leaves every gate green.
        others = [p for p in changed if not is_theirs(p, slugs)]
        if others:
            git("checkout", "HEAD", "--", *others)
        print(f"   kept {len(changed) - len(others)} twin(s); restored {len(others)} redrawn elsewhere")

    if args.no_check:
        print("\nDone — gates skipped (--no-check).")
        return 0
    step(9, "the cover gates")
    run(
        [*PY, "manage.py", "test", "library.tests_fixture", "library.tests_covers", "--noinput"],
        BACKEND,
        dry,
    )
    run(
        [
            "npx", "vitest", "run",
            "src/lib/coverOgManifest.test.ts", "src/lib/coverArt.test.ts",
            "src/lib/coverStyles.test.ts", "src/lib/coverScrim.test.ts",
        ],
        FRONTEND,
        dry,
    )
    print("\nDone. Review `git status`, then commit — the diff should be these works only.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"\nStopped: `{' '.join(map(str, e.cmd))}` exited {e.returncode}.")
