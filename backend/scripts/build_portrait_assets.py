"""Responsive WebP variants for the author portraits.

Nothing resized a portrait. `frederick-brotherton-meyer.jpg` is ~110 KB at
361×600 and appears as a 44px avatar on the home shelf and the author tiles, and
at 96px on the biographies cards — Lighthouse measured 547 KiB of wasted image
bytes on the home page alone, most of it portraits shipped at ~8× their painted
size. So every portrait gets small WebP variants, and the portrait `<img>`s ask
for them through `srcset` + `sizes` (see `$lib/portraits.portraitSrcset`).

The variants are named by convention — `<portrait>-96.webp` — and derived on the
committed source here, exactly like the covers (`build_cover_assets.py`); the
widths live in `PORTRAIT_WIDTHS` and are mirrored in `$lib/portraits`. A test
(`CoverAssetTests` sibling in `tests_fixture`) makes the promise keepable: every
portrait must ship its variants, or an `<img>` would point `srcset` at a 404.

    uv run python scripts/build_portrait_assets.py            # write missing/changed
    uv run python scripts/build_portrait_assets.py --dry-run  # report only
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
PORTRAITS = BACKEND.parent / "frontend" / "static" / "portraits"

#: The painted sizes are 44px (home/tile/person/article avatars), 32px (sermon
#: guests) and 96–112px (biography cards, author-page header). 96 covers every
#: avatar at 2× DPR; 224 covers the 112px card at 2×. The sources are ~361px, so
#: neither upscales. Mirrored in `frontend/src/lib/portraits.ts`.
PORTRAIT_WIDTHS = (96, 224)

#: 82 is the same floor the covers use — where these stop losing anything
#: visible. method=6 is the slowest encoder, paid once here, shipped forever.
WEBP_QUALITY = 82


def variant_name(source_name: str, width: int) -> str:
    """`andrew-murray.jpg` + 96 -> `andrew-murray-96.webp`."""
    return f"{Path(source_name).stem}-{width}.webp"


def write_variants(source: Path, dry_run: bool) -> list[str]:
    """Write `<source>-<width>.webp` for each width; return what changed."""
    from PIL import Image

    written: list[str] = []
    im = Image.open(source).convert("RGB")  # portraits are opaque JPEGs
    for width in PORTRAIT_WIDTHS:
        # NEVER upscale — a portrait narrower than the width keeps its own size,
        # under its nominal filename (the frontend derives both names blindly, so
        # a missing one is a broken image, not a smaller one).
        scaled_to = min(width, im.width)
        scaled = im.resize(
            (scaled_to, round(scaled_to * im.height / im.width)), Image.LANCZOS
        )
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
        dest = source.with_name(variant_name(source.name, width))
        if dest.exists() and dest.read_bytes() == buf.getvalue():
            continue
        if not dry_run:
            dest.write_bytes(buf.getvalue())
        written.append(dest.name)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    args = ap.parse_args()

    wrote: list[str] = []
    for source in sorted(PORTRAITS.glob("*.jpg")):
        wrote += write_variants(source, args.dry_run)

    if wrote:
        verb = "Would write" if args.dry_run else "Wrote"
        print(f"{verb} {len(wrote)} portrait variant(s):")
        for name in wrote:
            print(f"  {name}")
    else:
        print("Portrait variants already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
