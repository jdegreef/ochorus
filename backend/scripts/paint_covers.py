#!/usr/bin/env python3
"""Paint covers: take works you have added to `CURATED` all the way to shippable.

    uv run python scripts/paint_covers.py <slug> [<slug> ...]
    uv run python scripts/paint_covers.py <slug> --dry-run     # print the plan
    uv run python scripts/paint_covers.py <slug> --no-check    # skip the gates
    uv run python scripts/paint_covers.py <slug> --recrop      # redraw a painting
                                                               # after changing its focus

THE ONE HUMAN STEP COMES FIRST: choose the painting and add each work's entry to
`library/curated_art.py` (`.claude/skills/level-up-cover` is how to choose one).
Everything after that is mechanical — it used to be a list of hand-run
commands whose order mattered — and runs here, stopping at the first failure:

  1. migrate, seed_if_empty   — a fresh worktree's DB is empty or behind main
  2. build_curated_covers     — fetch, re-verify the licence, crop the painting
                                (kept if cut from this entry; --recrop redraws)
  3. delete the retired plates — every `<slug>.svg`, in every language dir
  4. build_cover_assets       — webp variants; repoints EVERY edition row
  5. tune_art_scrim <slugs>   — measure these paintings' scrim
  6. npm run og:covers        — the per-edition share twins
  7. the cover gates          — Python fixture gates and the JS twin gates

THE ORDER IS LOAD-BEARING. The plates must be gone before 4, which refuses to
run past a leftover one; the scrim must be measured before 6, because a twin is
drawn with it and records the strength it used.

Each stage is the tool that owns that job, and this file only orders them — so
a fix to how a stage works belongs in that stage's tool. Step 3 is the one job
no tool owned.

A TWIN REDRAWN OUTSIDE YOUR WORKS IS REPORTED, NOT UNDONE. The generator only
redraws a twin whose recorded inputs moved, so another work's redraw means
something about it really changed; restoring its old bytes would leave the
manifest vouching for a picture it no longer describes.

Run from `backend/`. Needs the frontend's `node_modules` (for step 6) and Node
22 on PATH — see `frontend/.nvmrc`. The whole cover system: `docs/covers.md`.
"""

from __future__ import annotations

import argparse
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


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("slugs", nargs="+", help="Works already added to CURATED.")
    ap.add_argument(
        "--dry-run", action="store_true", help="Print the plan; change nothing."
    )
    ap.add_argument(
        "--no-check", action="store_true", help="Skip the gates at the end."
    )
    ap.add_argument(
        "--recrop",
        action="store_true",
        help="Redraw committed paintings even when their entry is unchanged.",
    )
    args = ap.parse_args()
    slugs = sorted(set(args.slugs))

    def step(n: int, title: str) -> None:
        print(f"\n── {n}. {title}", flush=True)

    def run(cmd: list[str], cwd: Path = BACKEND) -> None:
        print("   $ " + " ".join(cmd), flush=True)
        if not args.dry_run:
            subprocess.run(cmd, cwd=cwd, check=True)

    # Refuse before anything runs: a slug missing from CURATED would sail
    # through every stage as a no-op and "succeed" having painted nothing.
    missing = [s for s in slugs if s not in CURATED]
    if missing:
        raise SystemExit(
            f"Not in library/curated_art.py CURATED: {', '.join(missing)}. "
            "Choose the painting and add its entry first — that is the one step "
            "this cannot do (see .claude/skills/level-up-cover)."
        )
    if not (FRONTEND / "node_modules").is_dir():
        raise SystemExit(
            "frontend/node_modules is missing — run `npm ci` in frontend/ first."
        )

    step(1, "migrate, and seed an empty database")
    run([*PY, "manage.py", "migrate", "--noinput"])
    # A fresh worktree — the repo's working agreement — starts with an empty
    # DB, and build_curated_covers skips any work with no Book rows. Without
    # this, a new painting is silently never drawn and step 4 fails pointing
    # back at the step that just "succeeded". A no-op once seeded.
    run([*PY, "manage.py", "seed_if_empty"])

    step(2, "fetch and crop the paintings")
    run(
        [
            *PY,
            "manage.py",
            "build_curated_covers",
            *slugs,
            *(["--force"] if args.recrop else []),
        ]
    )

    step(3, "delete the retired plates")
    for slug in slugs:
        for plate in sorted(p for p in COVERS.rglob(f"{slug}.svg") if p.is_file()):
            print(f"   rm {plate.relative_to(ROOT)}")
            if not args.dry_run:
                plate.unlink()

    step(4, "variants, and repoint every edition")
    run([*PY, "scripts/build_cover_assets.py"])

    step(5, "measure the scrim (before the twins, which are drawn with it)")
    run([*PY, "scripts/tune_art_scrim.py", *slugs])

    step(6, "draw the share twins")
    run(["npm", "run", "og:covers"], FRONTEND)
    if not args.dry_run:
        redrawn = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=M",
                "--",
                "frontend/static/covers/*.png",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()
        elsewhere = [p for p in redrawn if Path(p).stem not in slugs]
        if elsewhere:
            print(
                f"   note: {len(elsewhere)} twin(s) outside these works were redrawn because "
                "their inputs changed — check them before committing:\n"
                + "\n".join(f"     {p}" for p in elsewhere)
            )

    if args.no_check:
        print("\nDone — gates skipped (--no-check).")
        return 0
    step(7, "the cover gates")
    run(
        [
            *PY,
            "manage.py",
            "test",
            "library.tests_fixture",
            "library.tests_covers",
            "--noinput",
        ]
    )
    run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/coverOgManifest.test.ts",
            "src/lib/coverArt.test.ts",
            "src/lib/coverStyles.test.ts",
            "src/lib/coverScrim.test.ts",
        ],
        FRONTEND,
    )
    print(
        "\nDone. Review `git status`, then commit — the diff should be these works only."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"\nStopped: `{' '.join(map(str, e.cmd))}` exited {e.returncode}."
        ) from None
