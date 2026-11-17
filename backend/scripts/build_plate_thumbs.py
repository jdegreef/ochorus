#!/usr/bin/env python3
"""Draw the small twins of the books' full-page plates, for the series page.

The series page's "From the pages" row shows each illustrated chapter's plate
at about 150px wide (``library/series_page.py`` picks them). The plates
themselves are 900px JPEGs of ~100 KB, so a row of fifteen would fetch about
1.5 MB to show postage stamps. Each plate under ``frontend/static/illustrations``
named ``*plate-*.jpg`` gets a ``-320.webp`` beside it (~10 KB), which the row
asks for first (``SeriesPlates.svelte``); ``plateThumbs.test.ts`` fails the
build on a plate without one.

Output, not source: run it again after adding plates, and commit the files.

    cd backend && uv run python scripts/build_plate_thumbs.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "static" / "illustrations"
WIDTH = 320


def main() -> None:
    wrote = 0
    for plate in sorted(ROOT.rglob("*plate-*.jpg")):
        out = plate.with_name(f"{plate.stem}-{WIDTH}.webp")
        if out.exists() and out.stat().st_mtime >= plate.stat().st_mtime:
            continue
        im = Image.open(plate).convert("RGB")
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(out, "WEBP", quality=70, method=6)
        wrote += 1
    print(f"{wrote} plate thumbnails written under {ROOT}")


if __name__ == "__main__":
    main()
