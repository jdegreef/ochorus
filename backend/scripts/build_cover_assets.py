#!/usr/bin/env python3
"""Build the cover files a reader actually downloads.

    uv run python scripts/build_cover_assets.py --dry-run
    uv run python scripts/build_cover_assets.py

WHAT THIS IS FOR
Nothing resized a cover. `jesus-himself-2.png` is 397 KB at 600x800 and appears
on a shelf card 180px wide, and in a topic fan at 40px. The 27 raster covers a
reader can fetch weighed 1.5 MB; at the width they are painted they weigh
346 KB. So every cover gets webp variants, and `BookCover` and the three cover
fans ask for them through `srcset`.

The variants are named by convention — `<cover>-320.webp` — and derived on the
frontend from `cover_url` rather than looked up in a manifest. That is the right
coupling for this repo (the alternative is a generated file to build, commit and
keep in sync, and a missing key degrades silently instead of loudly), but it
means a `srcset` candidate that 404s renders a BROKEN image rather than falling
back. `CoverAssetTests.test_raster_covers_ship_their_responsive_variants` is
what makes that promise keepable; the widths live in `library.covers` so the
writer, the reader and the gate cannot drift apart.

A NOTE ON THE PAINTINGS
`covers/art/<slug>.jpg` is one painting per work, written by
`build_curated_covers`, with the type drawn over it in HTML by `BookCover`. It
used to be composited into an SVG per (slug, language) — six copies of one
painting for `waiting-on-god`, 430 KB, re-downloaded on every locale switch —
because an SVG served through <img> cannot fetch a sibling file. This script
only gives those paintings their variants; it does not produce them.

RE-CROPPED A COVER? RE-RUN THIS. Variants are built from whatever the source
was at the time, and nothing recomputes them on deploy: the committed files are
what production serves. A `--dry-run` says whether anything is stale.

Pillow is a dev-group dependency; this is a by-hand curation step like
`localize_covers` and `build_curated_covers`.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.content_fixtures import book_editions, persist_field  # noqa: E402
from library.covers import (  # noqa: E402
    COVER_WIDTHS,
    RASTER_SUFFIXES,
    art_url,
    keeps_english_designed,
    shares_a_ground,
    variant_url,
)
from library.designed_covers import DESIGNED_BY_SLUG  # noqa: E402

COVERS = BACKEND.parent / "frontend" / "static" / "covers"

#: 82 is where these covers stop losing anything visible — checked against the
#: photographic ones (the-inner-chamber, jesus-himself-2), which are hardest.
#: `method=6` is the slowest encoder setting and the right one: the CPU is paid
#: once, by hand, and the bytes ship to every reader forever.
WEBP_QUALITY = 82


def write_variants(source: Path, dry_run: bool) -> list[str]:
    """Write `<source>-<width>.webp` for each width, and say what changed."""
    from PIL import Image

    written = []
    # RGBA, not RGB: `baptism-with-the-holy-spirit.png` is 85-91% opaque on every
    # pixel and `prayer-the-pulse-of-life.png` carries fully transparent ones, so
    # flattening makes the variant the browser picks look darker than the `src`
    # it stands in for. webp carries alpha.
    im = Image.open(source)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    for width in COVER_WIDTHS:
        # NEVER upscale. Every committed cover is 600px wide or less, so a
        # literal 640 would invent pixels — measured at 18% more bytes and a
        # third more encode time for no detail. The FILENAME keeps the nominal
        # width, because the frontend derives both names unconditionally and a
        # missing one is a broken image, not a smaller one.
        scaled_to = min(width, im.width)
        scaled = im.resize((scaled_to, round(scaled_to * im.height / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
        dest = source.with_name(Path(variant_url(source.name, width)).name)
        if dest.exists() and dest.read_bytes() == buf.getvalue():
            continue
        if not dry_run:
            dest.write_bytes(buf.getvalue())
        written.append(str(dest.relative_to(COVERS)))
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    args = ap.parse_args()

    wrote: list[str] = []
    repointed = 0
    sources: set[Path] = set()

    for path, slug, language, fields in book_editions():
        # A work with a SHARED GROUND — a curated painting, or a ground cropped
        # from its own designed cover — has one wordless file under `covers/art/`
        # that its editions point at. Written here as well as by the script that
        # draws it because the DB is not the vehicle: `seed_books` re-asserts
        # cover_url from the fixture every deploy.
        if shares_a_ground(slug):
            url, rel = art_url(slug)
            # THE ENGLISH ROW IS THE EXCEPTION, and the reason the two tiers are
            # not simply merged here. A derived ground was cut FROM the English
            # edition's hand-made cover, which that edition goes on wearing
            # (library/designed_covers.py); repointing it at the ground is
            # precisely the loss this tier exists to prevent. A curated work has
            # no such cover, and every one of its languages takes the painting.
            wants = (
                DESIGNED_BY_SLUG[slug]
                if keeps_english_designed(slug) and language == "en"
                else url
            )
            if fields.get("cover_url") != wants:
                if not args.dry_run:
                    persist_field(path, "cover_url", wants)
                repointed += 1
            painting = COVERS / rel
            if not painting.exists():
                raise SystemExit(
                    f"{slug} wears a shared ground but has none at {rel} — run "
                    "`manage.py build_curated_covers` (curated) or "
                    "`scripts/build_derived_grounds.py` (derived) first"
                )
            # And the plate it replaced must be GONE. The mirror of the check
            # above, and it belongs here for the same reason: this is the one
            # place that knows every curated slug and owns the covers dir.
            #
            # Deleting them was a manual step for two batches running, and a
            # missed one is invisible — `cover_url` has moved to the painting,
            # so nothing renders the plate, no test reads it, and the plate
            # contrast gate skips any file whose stem is curated. It is not
            # merely dead weight: `render.yaml` redirects retired WordPress
            # image URLs at `/covers/<slug>.svg`, and `renderRoutes.test.ts`
            # only checks that the destination EXISTS. Leave the plate behind
            # and that check passes while the redirect quietly sends a legacy
            # URL to a design that is no longer the book's cover, forever.
            stale = sorted(
                p for p in COVERS.rglob(f"{slug}.svg") if p.is_file()
            )
            if stale:
                listed = ", ".join(str(p.relative_to(COVERS)) for p in stale)
                raise SystemExit(
                    f"{slug} wears a shared ground but still has its generated "
                    f"plate: {listed}. Delete it — a leftover plate is what a "
                    "retired render.yaml redirect will keep pointing at."
                )
            sources.add(painting)
            # The English designed cover is a raster a reader downloads too, and
            # this branch `continue`s past the tier below that would have
            # collected it — so it would have shipped without its variants.
            if keeps_english_designed(slug) and language == "en":
                sources.add(COVERS / wants.removeprefix("/covers/"))
            continue
        cover = fields.get("cover_url") or ""
        if cover.endswith(RASTER_SUFFIXES):
            source = COVERS / cover.removeprefix("/covers/")
            if not source.exists():
                raise SystemExit(f"cover_url points at a missing file: {cover}")
            sources.add(source)

    for source in sorted(sources):
        wrote += write_variants(source, args.dry_run)

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {len(wrote)} variants for {len(sources)} covers · repointed {repointed} rows")
    for name in wrote[:8]:
        print(f"    {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
