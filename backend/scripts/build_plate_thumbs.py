#!/usr/bin/env python3
"""Draw the small twins of the books' full-page plates, for the series page.

The series page's "From the pages" row shows each illustrated chapter's plate
at about 150px wide (``library/series_page.py`` picks them). The plates are
900px JPEGs of ~100 KB, so a row of fifteen would fetch about 1.5 MB to show
postage stamps. Each plate under ``frontend/static/illustrations`` named
``*plate-*.jpg`` gets the covers' webp variants beside it (``-320.webp`` and
``-640.webp``, the covers' own ``write_variants``), which the row offers at 1x
and 2x (``plateSrcset`` in ``frontend/src/lib/plates.ts``); ``plates.test.ts``
fails the build on a plate without them.

Output, not source: run it again after adding plates, and commit the files.

    cd backend && uv run python scripts/build_plate_thumbs.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_cover_assets import write_variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "static" / "illustrations"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    written = [f for plate in sorted(ROOT.rglob("*plate-*.jpg")) for f in write_variants(plate, args.dry_run, ROOT)]
    for f in written:
        print(f"  {'would write' if args.dry_run else 'wrote'} {f}")
    print(f"{len(written)} plate variants {'to write' if args.dry_run else 'written'} under {ROOT}")


if __name__ == "__main__":
    main()
