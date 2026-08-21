#!/usr/bin/env python3
"""Give every translated edition a cover in its own language.

    uv run python scripts/localize_covers.py --dry-run
    uv run python scripts/localize_covers.py
    uv run python scripts/localize_covers.py the-inner-chamber

THE PROBLEM
A book's editions are separate rows sharing a slug, but they shared a
``cover_url`` too — the English one. So the Swahili edition of "The Way to God"
sat on the shelf under a cover reading *The Way to God*, and 58 editions across
15 works did the same. For a library whose whole point is reading in your own
language, that is the wrong thing to show.

``generate_covers`` already writes per-language covers and would have fixed
this, except (a) it refuses to touch a row whose ``cover_url`` is a raster —
those are the designed covers and a generated plate would be a downgrade, a
right rule that happens to cover nearly every affected row — and (b) it writes
``cover_url`` to the DATABASE, which ``seed_books`` overwrites from the fixture
on the next deploy. This script is the fixture-side half.

WHAT IT DOES — one localized cover per (work, language), by tier
The tier is decided by the ENGLISH edition's cover, so every locale of a work
gets the same treatment:

* **Designed artwork** (``.jpg`` / ``.png``) → a house typographic plate in the
  edition's own language, coloured from the English artwork by
  ``palette_from_artwork``. The Spanish "Él sostiene mis mañanas" comes out in
  the desert blue of the English photograph.

  Not a composite over the artwork — that was tried first, and the reason it
  fails is not subtle: the English title is *baked into the pixels* of these
  covers, and the scrim is a 26–70% wash, not an eraser. The prototypes came
  out with "CLOTHED WITH STRENGTH AND DIGNITY" legible above "Amevaa Nguvu na
  Heshima", two hairline frames, two author lines, and — on the covers
  inherited from another ministry — a second wordmark and a
  garethevansministries.org URL showing through the foot. Compositing only
  works with *untyped* artwork, which we do not have for these. The trade: the
  translated editions lose the photograph, and keep the one thing a cover must
  get right.

* **Curated art** (``curated_art.CURATED``) → the real thing:
  ``build_art_svg``, the same painting under the edition's own title. The art
  layer is read back out of the ENGLISH SVG rather than re-fetched from the
  Met, which makes this reproducible offline and on any OS —
  ``build_curated_covers`` needs the network and macOS ``sips``. The bytes are
  the same cropped JPEG either way, so the output is identical to what a full
  rebuild would write (asserted for three shipped covers when this was added).

* **Generated plate** (everything else) → ``build_svg`` from the edition's own
  title and ``cover_color``, i.e. what ``generate_covers`` writes, but recorded
  in the fixture where the deploy will read it.

FILLS GAPS; ``--force`` REDRAWS
A cover file that already exists is left alone (its fixture row is still
corrected), because the drawing is not always the generator's: ``uk/baptism-
with-the-holy-spirit.svg`` carries a hand-balanced line break — "Хрещення /
Святим Духом" where the greedy wrap gives "Хрещення Святим / Духом" — and a
reconciler that rewrote every file would silently revert that kind of work. The
summary counts the divergent ones so they stay visible, and ``--force`` redraws
them, the same split ``generate_covers`` draws between filling gaps and
redrawing.

WHY IT EDITS THE FIXTURE
``seed_books`` lists ``cover_url`` and ``cover_color`` in UPDATE_FIELDS, so both
are re-asserted from the fixture on every deploy. Writing them to the DB — which
is what ``generate_covers`` does — would be walked back by the next release.
The fixture is the source of truth, and it is one file per work-language, so
patching 58 of them collides with nobody. ``regen_fixture`` cannot carry this:
its pinned recipe is loaddata → dumpdata with nothing in between, so it
reproduces the fixture from the fixture.

WHAT KEEPS IT DONE
``CoverAssetTests.test_translated_editions_wear_their_own_cover`` fails any row
whose cover lives outside its language's directory. That gate is the point: the
first run of this script fixed 58 rows, and 21 more had drifted back within the
month, because a new translation copies ``cover_url`` from the English file.

Committed output is what production serves; this is a by-hand curation step,
like ``build_curated_covers``. Pillow is a dev-group dependency.
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Both modules are deliberately Django-free, so this runs as a plain script.
from library.content_fixtures import (  # noqa: E402
    BOOKS_DIR,
    authors_by_slug,
    persist_field,
)
from library.covers import (  # noqa: E402
    build_art_svg,
    build_svg,
    cover_path,
    palette_from_artwork,
)
from library.curated_art import CURATED, credit  # noqa: E402

ROOT = BACKEND.parent
STATIC = ROOT / "frontend" / "static"
COVERS = STATIC / "covers"
RASTER = (".jpg", ".jpeg", ".png")


def ensure_og_twin(slug: str, artwork: Path) -> bool:
    """Guarantee ``/covers/<slug>.png`` exists beside an SVG cover.

    og:image must be raster — WhatsApp, Facebook and X all refuse an SVG
    preview — so ``books/[slug]/+page.svelte`` falls back to
    ``/covers/<slug>.png`` whenever cover_url ends in .svg. Handing a row a
    localized SVG therefore silently arms that fallback, and these 15 works had
    a .jpg twin, not a .png: 49 rows would have shipped pointing og:image at a
    404. ``CoverAssetTests.test_svg_covers_have_a_raster_twin_for_og_image``
    catches it, which is how this was found.

    One twin per WORK, not per language: the fallback path is keyed by slug
    alone, so a translated page's card shows the English designed cover. That is
    already true of the 27 works whose English cover is a generated SVG, so it
    is the existing behaviour rather than a new inconsistency — and fixing it
    properly means teaching the page the English row's cover_url, which is a
    different change.

    Palettised deliberately. A truecolour PNG of these frames runs 250-400 KB
    each; at feed size 256 colours is indistinguishable and costs a third of
    that. Rasterising the localized SVGs instead — 58 files rather than 15 —
    measured ~15 MB, which is not worth a preview card.
    """
    dest = COVERS / f"{slug}.png"
    if dest.exists():
        return False

    from PIL import Image

    im = Image.open(artwork).convert("RGB")
    w, h = im.size
    tw, th = (w, w * 4 // 3) if w * 4 // 3 <= h else (h * 3 // 4, h)
    im = im.crop(
        ((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th)
    ).resize((600, 800), Image.LANCZOS)
    im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(
        dest, "PNG", optimize=True
    )
    return True


@functools.cache
def art_layer(slug: str) -> str:
    """The bare base64 JPEG behind a curated cover, read from the English SVG.

    ``build_curated_covers`` embeds the cropped artwork as a data URI, so the
    shipped English cover already holds the exact bytes a translated edition
    needs — no Met fetch, no ``sips``, and no chance of a re-crop drifting from
    the locale that shipped first. Cached per work, like ``palettes`` below:
    these SVGs run 100-150 KB and a work has up to five translated editions."""
    src = (COVERS / cover_path(slug, "en")[1]).read_text(encoding="utf-8")
    match = re.search(r'data:image/jpeg;base64,([A-Za-z0-9+/=]+)"', src)
    if not match:
        raise SystemExit(f"{slug}: curated cover has no embedded artwork to reuse")
    return match.group(1)


def book_row(path: Path) -> dict | None:
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row["model"] == "library.book":
            return row["fields"]
    return None


def author_names() -> dict[str, str]:
    return {slug: fields.get("name", "") for slug, fields in authors_by_slug().items()}


def patch(path: Path, cover_url: str, cover_color: str | None = None) -> None:
    """Point one edition's fixture row at its own cover.

    ``cover_color`` is only rewritten for the artwork tier, where the colour is
    derived here; the other tiers keep whatever the edition already carries."""
    persist_field(path, "cover_url", cover_url)
    if cover_color is not None:
        persist_field(path, "cover_color", cover_color)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slugs", nargs="*", help="Limit to these slugs.")
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Redraw covers that already exist (discards hand-edited drawings).",
    )
    args = ap.parse_args()

    names = author_names()
    english: dict[str, dict] = {}
    editions: list[tuple[Path, str, str, dict]] = []
    # Narrowed by slug rather than filtered after the fact: a book fixture
    # carries its whole text, so parsing all 153 to keep three costs 74 MB and
    # most of the runtime — and the SKILL now puts a single-slug run on every
    # translation job's path.
    globs = [f"{slug}.*.json" for slug in args.slugs] or ["*.json"]
    for path in sorted(p for g in globs for p in BOOKS_DIR.glob(g)):
        slug, language = path.stem.rsplit(".", 1)
        fields = book_row(path)
        if fields is None:
            continue
        if language == "en":
            english[slug] = fields
        else:
            editions.append((path, slug, language, fields))

    drawn = patched = unchanged = 0
    diverged: list[str] = []
    palettes: dict[str, str] = {}
    twins: list[str] = []
    for path, slug, language, fields in editions:
        if args.slugs and slug not in args.slugs:
            continue
        source = english.get(slug) or {}
        source_cover = source.get("cover_url") or ""
        author = names.get(fields["author"][0], fields["author"][0])
        title = fields["title"]
        subtitle = fields.get("subtitle") or ""
        color: str | None = None

        if source_cover.endswith(RASTER):
            # Designed artwork: a plate in this language, in the artwork's hue.
            if slug not in palettes:
                art = STATIC / source_cover.lstrip("/")
                if not art.exists():
                    raise SystemExit(f"missing artwork for {slug}: {art}")
                palettes[slug] = palette_from_artwork(art)
                # Before the SVG lands, not after: an SVG cover arms the
                # og:image fallback, and the twin has to be there when it does.
                if not args.dry_run and ensure_og_twin(slug, art):
                    twins.append(slug)
            color = palettes[slug]
            svg = build_svg(title, subtitle, author, color, language)
            tier = "artwork"
        elif slug in CURATED:
            # The real painting, under this language's title.
            svg = build_art_svg(
                title, subtitle, author, art_layer(slug), language, credit(slug) or ""
            )
            tier = "curated"
        else:
            # The house plate, from this edition's own colour.
            svg = build_svg(title, subtitle, author, fields.get("cover_color") or "", language)
            tier = "generated"

        url, rel = cover_path(slug, language)
        dest = COVERS / rel
        # The author's name is the ENGLISH one by design: these are names, not
        # prose, and the shipped author rows carry a single canonical spelling.
        on_disk = dest.read_text(encoding="utf-8") if dest.exists() else None
        hand_drawn = on_disk is not None and on_disk != svg  # exists, but not ours
        needs_draw = on_disk is None or (hand_drawn and args.force)
        needs_patch = fields.get("cover_url") != url or (
            color is not None and fields.get("cover_color") != color
        )
        if hand_drawn and not args.force:
            diverged.append(rel)
        if not (needs_draw or needs_patch):
            unchanged += 1
            continue

        if needs_draw:
            drawn += 1
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(svg, encoding="utf-8")
        if needs_patch:
            patched += 1
            if not args.dry_run:
                patch(path, url, color)
        marks = "+".join(m for m, on in (("draw", needs_draw), ("row", needs_patch)) if on)
        print(f"  ✓ {rel:52} {tier:9} {marks:9} {color or '':8} {title}")

    verb = "would write" if args.dry_run else "wrote"
    print(
        f"\n{verb} {drawn} covers · repointed {patched} fixture rows"
        f" · {len(twins)} og:image twins · {unchanged} editions already correct"
    )
    if diverged:
        # Not an error: see FILLS GAPS above. Printed so a hand-edit is a known
        # divergence rather than a surprise the next --force run erases.
        print(f"{len(diverged)} drawn by hand, left as they are: {', '.join(diverged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
