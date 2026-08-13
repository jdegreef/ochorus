#!/usr/bin/env python3
"""Give every translated edition a cover in its own language.

    uv run python scripts/localize_artwork_covers.py --dry-run
    uv run python scripts/localize_artwork_covers.py
    uv run python scripts/localize_artwork_covers.py the-inner-chamber

THE PROBLEM
A book's editions are separate rows sharing a slug, but they shared a
``cover_url`` too — the English one. So the Swahili edition of "The Way to God"
sat on the shelf under a cover reading *The Way to God*, and 58 editions across
15 works did the same. For a library whose whole point is reading in your own
language, that is the wrong thing to show.

``generate_covers`` already writes per-language covers and would have fixed
this, except it refuses to touch a row whose ``cover_url`` is a raster — those
are the designed covers and a generated plate would be a downgrade. Right rule;
it just happens to cover nearly every affected row.

WHY NOT COMPOSITE NEW TYPE OVER THE ARTWORK
That was the first attempt, reusing ``build_art_svg`` — the artwork as the
background layer, the house scrim over it, the translated title on top. It does
not work, and the reason is not subtle: the English title is *baked into the
pixels* of these covers, and the scrim is a 26–70% wash, not an eraser. The
prototypes came out with "CLOTHED WITH STRENGTH AND DIGNITY" legible above
"Amevaa Nguvu na Heshima", two hairline frames, two author lines, and — on the
covers inherited from another ministry — a second wordmark and a
garethevansministries.org URL showing through the foot. Unusable, and no scrim
opacity fixes it without turning the artwork into a black rectangle.

Compositing only becomes possible with the *untyped* artwork, which we do not
have for these. So:

WHAT THIS DOES INSTEAD
Each translated edition gets the house typographic cover in its own language —
the same tier 27 other covers already ship in, so it is a sibling of an existing
style, not a foreign one — coloured from the ENGLISH edition's artwork. The
Spanish "Él sostiene mis mañanas" comes out in the desert blue of the English
photograph; the Arabic "المخدع" in the warm brown of the Inner Chamber doorway.
The editions read as the same book without inheriting a word of the wrong
language. English keeps its designed cover untouched.

This is a trade: the translated editions lose the photograph. It is worth it
because the title is the one thing a cover must get right, and it is not
permanent — a curated-art cover (``build_curated_covers``) is per-language by
construction, so any work that gets one later supersedes this for every locale
at once.

WHY IT EDITS THE FIXTURE
``seed_books`` lists ``cover_url`` and ``cover_color`` in UPDATE_FIELDS, so both
are re-asserted from the fixture on every deploy. Writing them to the DB — which
is what ``generate_covers`` does — would be walked back by the next release.
The fixture is the source of truth, and it is one file per work-language, so
patching 58 of them collides with nobody. ``regen_fixture`` cannot carry this:
its pinned recipe is loaddata → dumpdata with nothing in between, so it
reproduces the fixture from the fixture.

Committed output is what production serves; this is a by-hand curation step,
like ``build_curated_covers``. Pillow is a dev-group dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.covers import build_svg, palette_from_artwork  # noqa: E402

ROOT = BACKEND.parent
BOOKS = BACKEND / "library" / "fixtures" / "content" / "books"
STATIC = ROOT / "frontend" / "static"
COVERS = STATIC / "covers"
AUTHORS = BACKEND / "library" / "fixtures" / "content" / "authors.json"
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


def book_row(path: Path) -> dict | None:
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row["model"] == "library.book":
            return row["fields"]
    return None


def author_names() -> dict[str, str]:
    rows = json.loads(AUTHORS.read_text(encoding="utf-8"))
    return {r["fields"]["slug"]: r["fields"].get("name", "") for r in rows}


def patch(path: Path, cover_url: str, cover_color: str) -> None:
    """Replace the two values in place, touching nothing else.

    Deliberately textual rather than load-modify-dump. The committed files are
    NOT uniformly formatted — most match regen_fixture (records at column 0,
    indent=1) but a handful, the-inner-chamber.pt among them, are indent=2 with
    the records indented. Re-serialising normalises those, which rewrites all
    526 lines of a file whose actual change is two, and makes a cover edit look
    like a content edit in review. Reformatting the fixture may be worth doing;
    it is not this change's business.

    Safe as a whole-file substitution: only ``library.book`` rows carry these
    keys, and a fixture file holds exactly one book row. Both are asserted."""
    text = path.read_text(encoding="utf-8")
    for key, value in (("cover_url", cover_url), ("cover_color", cover_color)):
        pattern = rf'("{key}"\s*:\s*)"(?:[^"\\]|\\.)*"'
        text, n = re.subn(pattern, lambda m, value=value: m.group(1) + json.dumps(value), text)
        if n != 1:
            raise SystemExit(f"{path.name}: expected 1 {key}, found {n}")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slugs", nargs="*", help="Limit to these slugs.")
    ap.add_argument("--dry-run", action="store_true", help="Report; write nothing.")
    args = ap.parse_args()

    names = author_names()
    english: dict[str, dict] = {}
    editions: list[tuple[Path, str, str, dict]] = []
    for path in sorted(BOOKS.glob("*.json")):
        slug, language = path.stem.rsplit(".", 1)
        fields = book_row(path)
        if fields is None:
            continue
        if language == "en":
            english[slug] = fields
        else:
            editions.append((path, slug, language, fields))

    wrote = skipped = 0
    palettes: dict[str, str] = {}
    twins: list[str] = []
    for path, slug, language, fields in editions:
        if args.slugs and slug not in args.slugs:
            continue
        source = english.get(slug)
        # No English edition, or English isn't carrying inherited artwork:
        # generate_covers already handles those rows correctly.
        if not source or not (source.get("cover_url") or "").endswith(RASTER):
            skipped += 1
            continue

        if slug not in palettes:
            art = STATIC / source["cover_url"].lstrip("/")
            if not art.exists():
                raise SystemExit(f"missing artwork for {slug}: {art}")
            palettes[slug] = palette_from_artwork(art)
            # Before the SVG lands, not after: an SVG cover arms the og:image
            # fallback, and the twin has to be there when it does.
            if not args.dry_run and ensure_og_twin(slug, art):
                twins.append(slug)
        color = palettes[slug]

        # The author's name is the ENGLISH one by design: these are names, not
        # prose, and the shipped author rows carry a single canonical spelling.
        author = names.get(fields["author"][0], fields["author"][0])
        svg = build_svg(
            title=fields["title"],
            subtitle=fields.get("subtitle") or "",
            author=author,
            color=color,
            language=language,
        )
        rel = f"{language}/{slug}.svg"
        url = f"/covers/{rel}"
        if not args.dry_run:
            dest = COVERS / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(svg, encoding="utf-8")
            patch(path, url, color)
        wrote += 1
        print(f"  ✓ {rel:52} {color}  {fields['title']}")

    verb = "would write" if args.dry_run else "wrote"
    print(f"\n{verb} {wrote} localized covers across {len(palettes)} works "
          f"· {len(twins)} og:image twins · left {skipped} editions alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
