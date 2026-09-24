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

A REPAINT ONLY WHERE A CROP CANNOT REACH. Some pictures share their band with
thin lettering — a subtitle across a river, a ministry URL, the designed
cover's own hairline frame — or, on `soar-like-the-eagle-3`, have their subject
flying between the lines of the title. `Ground.erase` names those boxes, and the
ink in them (pixels darker or lighter than their neighbourhood) is filled from
the picture around it before the crop. It is an eraser for thin type over a
quiet ground, not for a title set over a subject.

A FOOT, WHEN THE SUBJECT SITS LOW. `BookCover` puts the Ochorus mark at the foot
of every cover, so a band ending on its subject puts the mark on top of it.
`Ground.foot` continues the band's bottom out of focus below it, the sky
extension pointed the other way, and the subject rises into the clear space.

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

from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageOps  # noqa: E402

# `H`/`W` are the plate's canvas — imported rather than restated, because every
# other cover tool derives its geometry from that pair and a private copy here
# would go on drawing 600x800 after the module moved.
from library.covers import H, W, art_url, scrimmed, write_og_twin  # noqa: E402
from library.designed_covers import (  # noqa: E402
    DERIVED_GROUND,
    DESIGNED_BY_SLUG,
    Ground,
    is_designed,
)

ROOT = BACKEND.parent
STATIC = ROOT / "frontend" / "static"

def _ink_mask(im, boxes):
    """Where the lettering in `boxes` is, as an L mask (255 = paint out).

    Ink is measured against a median of its neighbourhood rather than a fixed
    threshold: a median of 21px ignores a stroke a few pixels wide and keeps
    the gradient the stroke was set on, so the same box finds dark type on a
    sunset and on a pale sleeve alike.
    """
    w, h = im.size
    lum = im.convert("L")
    mask = Image.new("L", im.size, 0)
    for box in boxes:
        x0, y0 = int(w * box.x0), int(h * box.y0)
        x1, y1 = int(w * box.x1), int(h * box.y1)
        m = 12  # a margin, so the median sees ground on every side of the box
        area = (max(0, x0 - m), max(0, y0 - m), min(w, x1 + m), min(h, y1 + m))
        patch = lum.crop(area)
        ground = patch.filter(ImageFilter.MedianFilter(21))
        diff = (ImageChops.subtract(ground, patch) if box.ink == "dark"
                else ImageChops.subtract(patch, ground))
        found = diff.point(lambda v: 255 if v > 14 else 0)
        # Strokes only. The bright side of a real edge — a page, a branch —
        # also clears the median test, but it is BROAD, and an opening (erode,
        # then grow back) keeps exactly the broad parts; what it removes is
        # type-thin. So the mask is what the opening took away.
        if box.thin:
            broad = found.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(7))
            found = ImageChops.subtract(found, broad)
        # Then grown by a few pixels: a stroke's antialiased edge is ink too,
        # and a halo of it left behind reads as a ghost of the word.
        found = found.filter(ImageFilter.MaxFilter(5))
        keep = Image.new("L", patch.size, 0)
        keep.paste(255, (x0 - area[0], y0 - area[1], x1 - area[0], y1 - area[1]))
        mask.paste(ImageChops.multiply(found, keep), area[:2], ImageChops.multiply(found, keep))
    return mask


def _repaint(im, hole):
    """`im` with `hole` filled from the pixels around it.

    Normalised convolution at widening radii: each pass fills whatever a blur
    of that radius can see known pixels from, so a thin stroke is filled from
    its immediate neighbours and only a wide one reaches further. No numpy —
    Pillow is this script's only dependency, and a dev-group one at that.
    """
    known = ImageOps.invert(hole)
    src = Image.composite(Image.new("RGB", im.size), im, hole)
    out = im.copy()
    todo = hole
    for radius in (2, 4, 8, 16, 32, 64):
        weight = known.filter(ImageFilter.GaussianBlur(radius))
        denom = weight.point(lambda v: max(v, 1))
        blurred = src.filter(ImageFilter.GaussianBlur(radius))
        est = Image.merge("RGB", [
            ImageMath.lambda_eval(
                lambda a: a["n"] * 255 / a["d"], n=band, d=denom
            ).convert("L")
            for band in blurred.split()
        ])
        take = ImageChops.multiply(todo, weight.point(lambda v: 255 if v >= 40 else 0))
        out.paste(est, (0, 0), take)
        todo = ImageChops.subtract(todo, take)
    if todo.getbbox():
        # A box whose ink is too wide for the widest pass to reach across —
        # which is lettering this eraser was not made for. Shipping the ground
        # with the word half in it would be silent; saying so is not.
        raise SystemExit(f"erase left ink it could not repaint at {todo.getbbox()}")
    # Softened across the repaint only, so the join does not show as a seam.
    edge = hole.filter(ImageFilter.GaussianBlur(2))
    return Image.composite(out.filter(ImageFilter.GaussianBlur(1)), out, edge)


def _feathered(bh, feather, at_top):
    """A band's paste mask: opaque, fading out over `feather` px at one edge."""
    mask = Image.new("L", (W, bh), 255)
    ramp = Image.linear_gradient("L").resize((W, feather))
    if at_top:
        mask.paste(ramp, (0, 0))
    else:
        mask.paste(ImageOps.flip(ramp), (0, bh - feather))
    return mask


def derived_ground(source: Path, cut: Ground):
    """The wordless ground for one work, as a 600x800 image.

    NOT `covers.build_ground`, which takes a colour and returns the SVG plate.
    Different input, different output, same subsystem — hence the name.
    """
    im = Image.open(source).convert("RGB")
    if cut.erase:
        im = _repaint(im, _ink_mask(im, cut.erase))
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
    if cut.peak != 255:
        band = band.point(lambda v: v * cut.peak // 255)

    if cut.foot:
        # The band's own bottom, continued out of focus below it — the same
        # move as the sky extension, pointed the other way.
        foot = round(H * cut.foot)
        slice_h = max(8, int(bh * 0.12))
        below = ImageOps.fit(
            band.crop((0, bh - slice_h, W, bh)), (W, bh + foot), Image.LANCZOS
        ).filter(ImageFilter.GaussianBlur(radius=30))
        below.paste(band, (0, 0), _feathered(bh, min(90, bh // 3), at_top=False))
        band, bh = below, bh + foot

    if bh >= H:
        y = (bh - H) // 2
        return band.crop((0, y, W, y + H))

    seam = H - bh
    slice_h = max(8, int(bh * cut.sky))
    ground = ImageOps.fit(
        band.crop((0, 0, W, slice_h)), (W, H), Image.LANCZOS
    ).filter(ImageFilter.GaussianBlur(radius=46))
    # Feathered in rather than pasted: the join has to read as depth of field.
    ground.paste(band, (0, seam), _feathered(bh, min(120, bh // 2), at_top=True))
    return ground


# `scrimmed` moved to `library.covers`: the fixture gate that measures every
# committed painting needs the same curve, and this was already described here
# as "a hand-copy of four alpha stops, and the third copy of that gradient in
# the repo". Two callers of one function beats two copies of one gradient.
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
        redraw = args.force or not dest.exists()
        ground = None
        if redraw:
            ground = derived_ground(source, cut)
            drawn += 1
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Quality 88 and 4:2:0 off: these grounds carry soft gradients
                # that 4:2:0 bands, and they are the only thing behind the
                # title.
                ground.save(dest, "JPEG", quality=88, subsampling=0, optimize=True)
        else:
            skipped += 1

        # THE TWIN AND THE PREVIEW ARE OF THE WORK, NOT OF THIS RUN'S DRAWING,
        # so they sit outside the fills-gaps skip above. A twin inside it was
        # unrecoverable: delete `/covers/<slug>.png` and the fixture gate goes
        # red, while re-running this restored nothing because the ground was
        # already on disk — leaving `--force`, which discards hand-edits, as
        # the only repair. That is the trap `_ensure_twin` exists to close, and
        # it had reproduced it one level up.
        if not args.dry_run:
            if preview:
                scrimmed(ground or Image.open(dest)).save(preview / f"{slug}.png")
            if _ensure_twin(slug, source):
                twins += 1
        print(
            f"  {'✓' if redraw else '·'} {url:44} "
            f"{'from ' + designed if redraw else 'already drawn'}"
        )

    verb = "would draw" if args.dry_run else "drew"
    print(f"\n{verb} {drawn} grounds · {twins} og:image twins · {skipped} already on disk")
    if drawn and not args.dry_run:
        print("next: uv run python scripts/build_cover_assets.py  (webp variants)")
        print("      uv run python scripts/localize_covers.py     (repoint rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
