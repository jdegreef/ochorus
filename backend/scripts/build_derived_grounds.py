#!/usr/bin/env python3
"""Give a translated edition the artwork its English edition has.

    uv run python scripts/build_derived_grounds.py --dry-run
    uv run python scripts/build_derived_grounds.py
    uv run python scripts/build_derived_grounds.py godliness

THE PROBLEM
Sixteen works wear a designed cover in English — a photograph with the title set
into it — and a flat coloured plate in every other language. `localize_covers`
explains why it could not do better: the English title is IN THE PIXELS, and a
scrim is not an eraser, so the prototypes that composited a translated title
over the English one came out with both legible. The result was a library whose
shelf said, in the one place a reader looks first, that the translations were
the lesser edition.

WHAT THIS DOES
It does NOT touch the designed cover. That file is registered in
`library.designed_covers` and frozen (see that module for the rule). This reads
it, and writes a SECOND, WORDLESS file beside the paintings:

    /covers/<slug>.jpg          the designed English cover — untouched
    /covers/art/<slug>.jpg      the ground this writes, for every other language

`covers/art/` is the tier `BookCover` already draws a per-language title over,
so a Swahili edition pointing there gets the work's own photography with its own
title on it, in its own script, in the author's house face. The English row goes
on pointing at the designed file and renders exactly as it always has.

HOW A GROUND IS MADE — a crop, not a repaint
Each designed cover has a band that carries photography and no words: below the
title, above the ministry mark, inside the hairline frame. `BAND` records that
band per work, because no rule finds it — the mark sits at 78% on one cover and
overlaps the subject on the next, and `jesus-himself-2` has a hairline rule at
0.594 that a crop starting at 0.56 quietly included. That table is the curation,
and it is the reason this is a by-hand step rather than a deploy-time one.

The band is rarely 3:4, so the picture is continued behind itself: its own top
slice, scaled to fill and thrown out of focus, with the sharp band feathered in
over it. Built from the TOP slice rather than the whole band on purpose — that
is what the photograph was doing where the extension begins, so sky stays sky
and `the-unselfishness-of-god`'s hill does not bloom into a dark dome over its
own sunset.

WHY A LIFT, AND WHY PER WORK
`cover-type.css`'s `.cover-plate.over-art` lays 36-64% black over an art cover.
The curated tier survives it because a museum landscape is daylight; these are
ministry photographs chosen to be moody, and three of them (`the-inner-chamber`
is a doorway into a dark room) came out of the scrim as black rectangles. The
lift is a gamma on the band — shadows open, highlights stay — tuned per work
against the scrim, which `--preview` composites so the tuning is done against
what ships rather than against the file.

FILLS GAPS; `--force` REDRAWS, exactly like `localize_covers`. A ground already
on disk is left alone, so a hand-adjusted one survives a re-run.

Pillow is a dev-group dependency; this is a by-hand curation step like
`localize_covers` and `build_curated_covers`. The committed output is what
production serves. After running this, run `build_cover_assets.py` — a raster
cover without its webp variants is a broken image, not a soft failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.covers import art_url  # noqa: E402
from library.designed_covers import DERIVED_GROUND  # noqa: E402

ROOT = BACKEND.parent
STATIC = ROOT / "frontend" / "static"

#: The plate's canvas, matching `covers.W/H` and BookCover's reserved 3:4 box.
W, H = 600, 800

#: Per work: the band of the designed cover to take, as fractions of its size,
#: and how far to open its shadows.
#:
#: * ``top`` / ``bottom`` — the words-free band, as fractions of the height.
#:   Read off the artwork; every one of these excludes the byline, the title,
#:   any rule, and the Ochorus or garethevansministries.org mark at the foot.
#: * ``inset`` — how far in from each side, to clear the designed cover's own
#:   hairline frame. `BookCover` draws a frame of its own, and two of them a few
#:   pixels apart is worse than either. A cover with no frame (the four
#:   full-bleed photographs) takes the 0.02 that just trims the edge.
#: * ``lift`` — gamma on the band, against the art scrim. 1.0 leaves it alone.
#: * ``sky`` — how much of the band's top the out-of-focus extension is built
#:   from. The default suits a photograph whose top is already background; a
#:   silhouette against a sunset wants less, or its subject blurs upward into
#:   the sky it was cut out of.
BAND: dict[str, tuple[float, float, float, float, float]] = {
    #                                       top   bottom inset  lift  sky
    "baptism-with-the-holy-spirit":        (0.42, 0.83, 0.11, 1.15, 0.35),
    "clothed-with-strength-and-dignity":   (0.40, 0.78, 0.10, 1.45, 0.35),
    "godliness":                           (0.44, 0.75, 0.09, 1.85, 0.35),
    "he-holds-my-tomorrows":               (0.46, 0.88, 0.02, 1.10, 0.20),
    "humility-2":                          (0.38, 0.80, 0.11, 1.20, 0.35),
    # The rule under the title sits at 0.594 — measured, not guessed, after a
    # crop from 0.56 shipped a hairline across the ground. What is left below it
    # is 18% of the cover, which at the usual inset came out as five parts blur
    # to one part picture; the wide inset crops IN to the cross's stem instead,
    # so the sharp band lands at a third of the plate.
    "jesus-himself-2":                     (0.62, 0.78, 0.22, 1.80, 0.35),
    # A true silhouette: nearly black before the scrim, so the heaviest lift
    # in the table and it is still the darkest ground here.
    "lord-teach-us-to-pray-2":             (0.44, 0.84, 0.03, 2.50, 0.35),
    "prayer-the-pulse-of-life":            (0.56, 0.84, 0.11, 1.50, 0.35),
    "purity-of-heart":                     (0.55, 0.79, 0.12, 2.00, 0.35),
    "stepping-stones-2":                   (0.26, 0.64, 0.02, 1.15, 0.35),
    "talks-to-the-farmer":                 (0.46, 0.78, 0.09, 1.45, 0.35),
    "the-god-of-all-comfort":              (0.50, 0.78, 0.11, 1.10, 0.35),
    # The doorway itself is an unlit room — a black rectangle at any lift the
    # highlights survive — so this takes the lintel and sandstone ABOVE it,
    # under the byline. The one work here whose ground is not its cover's
    # subject, because its subject is an absence of light.
    "the-inner-chamber":                   (0.13, 0.33, 0.10, 1.60, 0.35),
    "the-key-in-my-hand":                  (0.26, 0.60, 0.02, 1.05, 0.35),
    "the-person-and-work-of-the-holy-spirit": (0.41, 0.82, 0.10, 1.00, 0.35),
    "the-unselfishness-of-god":            (0.44, 0.80, 0.09, 1.15, 0.15),
}


def _fill(im, w: int, h: int):
    """Scale to cover (w, h), centre-cropping the overflow."""
    from PIL import Image

    scale = max(w / im.width, h / im.height)
    im = im.resize(
        (max(w, round(im.width * scale)), max(h, round(im.height * scale))),
        Image.LANCZOS,
    )
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def build_ground(source: Path, top: float, bottom: float, inset: float,
                 lift: float, sky: float):
    """The wordless ground for one work, as a 600x800 image."""
    from PIL import Image, ImageFilter

    im = Image.open(source).convert("RGB")
    w, h = im.size
    band = im.crop((int(w * inset), int(h * top), int(w * (1 - inset)), int(h * bottom)))
    bh = round(band.height * W / band.width)
    band = band.resize((W, bh), Image.LANCZOS)

    if lift != 1.0:
        # Gamma rather than a brightness multiply: the scrim takes 36-64% back
        # out, and a multiply that lifted these shadows far enough would flatten
        # the highlights the photographs were chosen for.
        lut = [min(255, round(255 * (v / 255) ** (1 / lift))) for v in range(256)]
        band = band.point(lut * 3)

    if bh >= H:
        y = (bh - H) // 2
        return band.crop((0, y, W, y + H))

    seam = H - bh
    slice_h = max(8, int(bh * sky))
    ground = _fill(band.crop((0, 0, W, slice_h)), W, H).filter(
        ImageFilter.GaussianBlur(radius=46)
    )
    # Feathered in rather than pasted: the join has to read as depth of field.
    mask = Image.new("L", (W, bh), 255)
    mask.paste(Image.linear_gradient("L").resize((W, min(120, bh // 2))), (0, 0))
    ground.paste(band, (0, seam), mask)
    return ground


def scrimmed(ground):
    """`cover-type.css`'s `.cover-plate.over-art`, composited — what a reader
    actually sees. Only `--preview` uses this; nothing is written through it.

    A hand-copy of four alpha stops, and the third copy of that gradient in the
    repo. Deliberate, and thin enough to stay honest: this is a curation aid on
    a developer's machine, and the alternative — teaching a Python script to
    read a CSS custom property — is more machinery than the tuning is worth.
    """
    from PIL import Image

    out = Image.blend(ground.convert("RGB"), Image.new("RGB", (W, H), (26, 20, 16)), 0.26)
    stops = [(0.00, 0.64), (0.30, 0.36), (0.60, 0.50), (1.00, 0.74)]
    column = Image.new("L", (1, H))
    px = column.load()
    for y in range(H):
        f = y / (H - 1)
        for (p0, a0), (p1, a1) in zip(stops, stops[1:], strict=False):
            if p0 <= f <= p1:
                px[0, y] = int(255 * (a0 + (a1 - a0) * (f - p0) / (p1 - p0)))
                break
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), out, column.resize((W, H)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slugs", nargs="*", help="Limit to these works.")
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    ap.add_argument("--force", action="store_true",
                    help="Redraw grounds that already exist (discards hand-edits).")
    ap.add_argument("--preview", metavar="DIR",
                    help="Also write each ground under the art scrim, for tuning.")
    args = ap.parse_args()

    missing = sorted(set(DERIVED_GROUND) - set(BAND))
    if missing:
        raise SystemExit(f"no band recorded for: {', '.join(missing)}")

    wanted = set(args.slugs)
    drawn = skipped = 0
    preview = Path(args.preview) if args.preview else None
    if preview and not args.dry_run:
        preview.mkdir(parents=True, exist_ok=True)

    for slug, designed in sorted(DERIVED_GROUND.items()):
        if wanted and slug not in wanted:
            continue
        source = STATIC / designed.lstrip("/")
        if not source.is_file():
            raise SystemExit(f"missing designed cover for {slug}: {source}")
        url, rel = art_url(slug)
        dest = STATIC / "covers" / rel
        if dest.exists() and not args.force:
            skipped += 1
            print(f"  · {url:44} already drawn")
            continue

        ground = build_ground(source, *BAND[slug])
        drawn += 1
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Quality 88 and 4:2:0 off: these grounds carry soft gradients that
            # 4:2:0 bands, and they are the only thing behind the title.
            ground.save(dest, "JPEG", quality=88, subsampling=0, optimize=True)
            if preview:
                scrimmed(ground).save(preview / f"{slug}.png")
        print(f"  ✓ {url:44} from {designed}")

    verb = "would draw" if args.dry_run else "drew"
    print(f"\n{verb} {drawn} grounds · {skipped} already on disk")
    if drawn and not args.dry_run:
        print("next: uv run python scripts/build_cover_assets.py  (webp variants)")
        print("      uv run python scripts/localize_covers.py     (repoint rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
