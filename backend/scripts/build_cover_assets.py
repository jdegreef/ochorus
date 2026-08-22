#!/usr/bin/env python3
"""Build what the reader actually downloads: the art layer, and small variants.

    uv run python scripts/build_cover_assets.py --dry-run
    uv run python scripts/build_cover_assets.py
    uv run python scripts/build_cover_assets.py --check   # CI-style, writes nothing

TWO PROBLEMS, ONE PIPELINE

**The painting was embedded once per language.** A curated cover is an SVG with
its artwork as a base64 data URI, because an SVG loaded through ``<img>`` runs
in secure static mode and cannot fetch a sibling file. Covers are per
``(slug, language)``, so `waiting-on-god` shipped SIX copies of one painting —
430 KB for one book — and a reader who switches locale downloads it again,
because it is a different URL every time. Base64 adds a third on top of that.

**Nothing was ever resized.** `jesus-himself-2.png` is 397 KB at 600x800 and
appears on a shelf card 180px wide, and in a topic fan at 40px. The 27 raster
covers a reader can fetch weigh 1.5 MB; at the width they are actually painted
they weigh 346 KB.

Both are the same fix: stop shipping one big file that serves every purpose.
The painting becomes ONE file per work under ``covers/art/``, the type moves to
HTML over it (BookCover already draws that type for the generated plate), and
every raster gets 320w/640w webp variants that ``<img srcset>`` picks between.

WHY THE TYPE MOVES TO HTML
Because it is better type. The SVG is served through ``<img>``, so it can only
name fonts the device already has — Georgia, in practice — and it pre-wraps the
title at a character count that means nothing in Arabic or Devanagari. Rendered
as HTML the browser shapes the script, honours ``dir``, wraps at real word
boundaries and uses the brand serif. That is the same argument that retired the
SVG replica in the fallback plate, applied to the tier that has artwork.

WHAT THIS DOES NOT TOUCH
The og:image twins under ``covers/*.png``. They are a raster of the OLD cover
design (wordmark at the top, author at the foot) and want re-rasterising with
the brand fonts installed — a different job, on a machine that has them.

Pillow is a dev-group dependency; the committed output is what production
serves, so this is a by-hand curation step like ``localize_covers``.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.content_fixtures import BOOKS_DIR, persist_field  # noqa: E402
from library.curated_art import CURATED  # noqa: E402

ROOT = BACKEND.parent
COVERS = ROOT / "frontend" / "static" / "covers"
ART_DIR = COVERS / "art"

#: The widths a cover is actually painted at. 320 covers the shelf card (180px)
#: and the book page's 128px box on a 2x screen; 640 covers both at 3x and any
#: future wider card. A third size buys nothing measurable and triples the
#: file count.
VARIANT_WIDTHS = (320, 640)
RASTER = (".jpg", ".jpeg", ".png")
#: 82 is where these covers stop losing anything visible — checked against the
#: photographic ones (the-inner-chamber, jesus-himself-2), which are the hardest.
WEBP_QUALITY = 82


def art_url(slug: str) -> str:
    """Where a work's painting lives — one file, every language."""
    return f"/covers/art/{slug}.jpg"


def variant_url(cover_url: str, width: int) -> str:
    """The webp variant of a raster cover at `width`."""
    return f"{cover_url.rsplit('.', 1)[0]}-{width}.webp"


def book_rows() -> list[tuple[Path, str, str, dict]]:
    """(path, slug, language, fields) for every committed book edition."""
    rows = []
    for path in sorted(BOOKS_DIR.glob("*.json")):
        slug, language = path.stem.rsplit(".", 1)
        for row in json.loads(path.read_text(encoding="utf-8")):
            if row["model"] == "library.book":
                rows.append((path, slug, language, row["fields"]))
                break
    return rows


def extract_art(slug: str) -> bytes | None:
    """The painting behind a curated cover, from whichever edition still has it.

    Every language embedded the same cropped JPEG — byte-identical, asserted
    here rather than assumed, because if two locales ever diverged the choice of
    which one becomes the shared file would be silent and arbitrary.
    """
    digests, art = set(), None
    for svg in sorted(COVERS.rglob(f"{slug}.svg")):
        match = re.search(r"base64,([A-Za-z0-9+/=]+)", svg.read_text(encoding="utf-8"))
        if match:
            art = base64.b64decode(match.group(1))
            digests.add(art)
    if len(digests) > 1:
        raise SystemExit(f"{slug}: locales carry different artwork — resolve by hand")
    return art


def write_variants(source: Path, dest_base: Path, dry_run: bool) -> list[str]:
    """Write `<dest_base>-<width>.webp` for each variant width."""
    from PIL import Image

    written = []
    im = Image.open(source).convert("RGB")
    for width in VARIANT_WIDTHS:
        dest = dest_base.with_name(f"{dest_base.stem}-{width}.webp")
        if width >= im.width and source.suffix == ".webp":
            continue
        scaled = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
        if dest.exists() and dest.read_bytes() == buf.getvalue():
            continue
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(buf.getvalue())
        written.append(str(dest.relative_to(COVERS)))
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if anything is missing or stale. Writes nothing.",
    )
    args = ap.parse_args()
    dry = args.dry_run or args.check
    rows = book_rows()
    wrote: list[str] = []
    repointed = 0

    # ── The paintings: one file per work, type no longer baked in ────────────
    for slug in sorted(CURATED):
        art = extract_art(slug)
        dest = ART_DIR / f"{slug}.jpg"
        if art is None and not dest.exists():
            print(f"  – {slug}: no artwork committed yet, skipping")
            continue
        if art is not None and (not dest.exists() or dest.read_bytes() != art):
            if not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(art)
            wrote.append(str(dest.relative_to(COVERS)))
        source = dest if dest.exists() else None
        if source:
            wrote += write_variants(source, dest, dry)

    # ── Every edition points at the shared painting, and the per-language
    #    composites go away ────────────────────────────────────────────────
    for path, slug, _language, fields in rows:
        if slug not in CURATED:
            continue
        if fields.get("cover_url") != art_url(slug):
            if not dry:
                persist_field(path, "cover_url", art_url(slug))
            repointed += 1

    stale_composites = [
        p for slug in CURATED for p in sorted(COVERS.rglob(f"{slug}.svg"))
    ]
    if stale_composites and not dry:
        for p in stale_composites:
            p.unlink()

    # ── Responsive variants for the designed artwork ─────────────────────────
    for _path, _slug, _language, fields in rows:
        cover = fields.get("cover_url") or ""
        if not cover.endswith(RASTER) or cover.startswith("/covers/art/"):
            continue
        source = COVERS / cover.removeprefix("/covers/")
        if not source.exists():
            raise SystemExit(f"cover_url points at a missing file: {cover}")
        wrote += write_variants(source, source, dry)

    verb = "would write" if dry else "wrote"
    print(f"{verb} {len(set(wrote))} files · repointed {repointed} curated rows")
    if stale_composites:
        print(f"{'would remove' if dry else 'removed'} {len(stale_composites)} per-language composites")
    for name in sorted(set(wrote))[:8]:
        print(f"    {name}")
    if args.check and (wrote or repointed or stale_composites):
        print("\nCover assets are stale — run scripts/build_cover_assets.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
