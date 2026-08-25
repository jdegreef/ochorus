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

from PIL import Image, ImageFilter, ImageOps  # noqa: E402

# `H`/`W` are the plate's canvas — imported rather than restated, because every
# other cover tool derives its geometry from that pair and a private copy here
# would go on drawing 600x800 after the module moved.
from library.covers import H, W, art_url, write_og_twin  # noqa: E402
from library.designed_covers import (  # noqa: E402
    DERIVED_GROUND,
    DESIGNED_BY_SLUG,
    Ground,
    is_designed,
)

ROOT = BACKEND.parent
STATIC = ROOT / "frontend" / "static"

def derived_ground(source: Path, cut: Ground):
    """The wordless ground for one work, as a 600x800 image.

    NOT `covers.build_ground`, which takes a colour and returns the SVG plate.
    Different input, different output, same subsystem — hence the name.
    """
    im = Image.open(source).convert("RGB")
    w, h = im.size
    band = im.crop((
        int(w * cut.inset),
        int(h * cut.top),
        int(w * (1 - cut.inset)),
        int(h * cut.bottom),
    ))
    bh = round(band.height * W / band.width)
    band = band.resize((W, bh), Image.LANCZOS)

    if cut.lift != 1.0:
        # Gamma rather than a brightness multiply: the scrim takes 36-64% back
        # out, and a multiply that lifted these shadows far enough would flatten
        # the highlights the photographs were chosen for.
        lut = [min(255, round(255 * (v / 255) ** (1 / cut.lift))) for v in range(256)]
        band = band.point(lut * 3)

    if bh >= H:
        y = (bh - H) // 2
        return band.crop((0, y, W, y + H))

    seam = H - bh
    slice_h = max(8, int(bh * cut.sky))
    ground = ImageOps.fit(
        band.crop((0, 0, W, slice_h)), (W, H), Image.LANCZOS
    ).filter(ImageFilter.GaussianBlur(radius=46))
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
    stops = [(0.00, 0.64), (0.30, 0.36), (0.60, 0.50), (1.00, 0.74)]

    def alpha(f: float) -> int:
        """The scrim's opacity a fraction `f` down the plate, 0-255."""
        for (p0, a0), (p1, a1) in zip(stops, stops[1:], strict=True):
            if f <= p1:
                return round(255 * (a0 + (a1 - a0) * (f - p0) / (p1 - p0)))
        return round(255 * stops[-1][1])

    out = Image.blend(ground.convert("RGB"), Image.new("RGB", (W, H), (26, 20, 16)), 0.26)
    # One pixel wide, then stretched: the ramp is vertical, so 800 values rather
    # than 480,000.
    column = Image.new("L", (1, H))
    column.putdata([alpha(y / (H - 1)) for y in range(H)])
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), out, column.resize((W, H)))


def _ensure_twin(slug: str, designed) -> bool:
    """Guarantee `/covers/<slug>.png` exists once this work wears a ground.

    Handing the translations a `covers/art/` cover ARMS the og:image fallback —
    `books/[slug]/+page.svelte` sends any art or `.svg` cover to
    `/covers/<slug>.png` — and `test_covers_that_cannot_be_shared_have_a_raster
    _twin` fails without one. `localize_covers.ensure_og_twin` used to be what
    wrote it, and no longer can: a derived work now `continue`s out of that
    script before its artwork branch, so the seventeenth of these would have
    arrived at a red build with no command that produces the missing file —
    the trap `tests_fixture` names elsewhere as "a red build no re-run fixes".

    The twin is a crop of the DESIGNED cover, not of the ground: it is the one
    image of this work that still has a title on it, which is the whole job of
    a share card.

    Two of the sixteen are the case that makes this delicate — for
    `baptism-with-the-holy-spirit` and `prayer-the-pulse-of-life` the twin's
    path IS the designed cover. Writing there would destroy a hand-made cover,
    so the registry is asked, not the extension.
    """
    dest = STATIC / "covers" / f"{slug}.png"
    if dest.exists():
        return False
    if is_designed(f"/covers/{slug}.png"):
        # Cannot happen while the file is committed; if it ever does, the file
        # is missing and regenerating it is precisely the wrong repair.
        raise SystemExit(
            f"{slug}'s og twin path is its designed cover and that file is "
            "gone — restore it from git rather than redrawing it"
        )
    write_og_twin(designed, dest)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slugs", nargs="*", help="Limit to these works.")
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    ap.add_argument("--force", action="store_true",
                    help="Redraw grounds that already exist (discards hand-edits).")
    ap.add_argument("--preview", metavar="DIR",
                    help="Also write each ground under the art scrim, for tuning.")
    args = ap.parse_args()

    wanted = set(args.slugs)
    drawn = skipped = twins = 0
    preview = Path(args.preview) if args.preview else None
    if preview and not args.dry_run:
        preview.mkdir(parents=True, exist_ok=True)

    for slug, cut in sorted(DERIVED_GROUND.items()):
        if wanted and slug not in wanted:
            continue
        designed = DESIGNED_BY_SLUG[slug]
        source = STATIC / designed.lstrip("/")
        if not source.is_file():
            raise SystemExit(f"missing designed cover for {slug}: {source}")
        url, rel = art_url(slug)
        dest = STATIC / "covers" / rel
        if dest.exists() and not args.force:
            skipped += 1
            print(f"  · {url:44} already drawn")
            continue

        ground = derived_ground(source, cut)
        drawn += 1
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Quality 88 and 4:2:0 off: these grounds carry soft gradients that
            # 4:2:0 bands, and they are the only thing behind the title.
            ground.save(dest, "JPEG", quality=88, subsampling=0, optimize=True)
            if preview:
                scrimmed(ground).save(preview / f"{slug}.png")
            if _ensure_twin(slug, source):
                twins += 1
        print(f"  ✓ {url:44} from {designed}")

    verb = "would draw" if args.dry_run else "drew"
    print(f"\n{verb} {drawn} grounds · {twins} og:image twins · {skipped} already on disk")
    if drawn and not args.dry_run:
        print("next: uv run python scripts/build_cover_assets.py  (webp variants)")
        print("      uv run python scripts/localize_covers.py     (repoint rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
