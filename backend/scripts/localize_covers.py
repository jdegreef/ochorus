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

* **Curated art** (``curated_art.CURATED``) → nothing to do here. A painting
  has no language: it is one shared file under ``covers/art/`` and BookCover
  draws each edition's title over it, so there is no per-language artefact to
  localize. ``build_cover_assets.py`` owns that tier. (It was composited per
  language once, which meant six copies of one painting for ``waiting-on-god``
  and a fresh download on every locale switch.)

* **Generated plate** (everything else) → ``build_ground`` from the edition's
  ``cover_color``, i.e. what ``generate_covers`` writes, but recorded in the
  fixture where the deploy will read it. A ground has no words in it, so what
  this draws no longer varies by language at all — the per-language FILE is
  what the fixture rows still point at, and consolidating that is its own PR
  (see ``library/covers.py``).

FILLS GAPS; ``--force`` REDRAWS
A cover file that already exists is left alone (its fixture row is still
corrected), because the drawing has not always been the generator's: a
hand-balanced line break used to be a thing a translator could put in one of
these files, and a reconciler that rewrote every file would silently revert
that kind of work. There are no line breaks left to balance — the words are
drawn by the browser now — but a hand-adjusted GROUND is the same kind of
work, so the split stands. The summary counts the divergent ones so they stay
visible, and ``--force`` redraws them, the same split ``generate_covers`` draws
between filling gaps and redrawing.

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
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Both modules are deliberately Django-free, so this runs as a plain script.
from library.content_fixtures import book_editions, persist_fields  # noqa: E402
from library.covers import (  # noqa: E402
    RASTER_SUFFIXES,
    art_url,
    build_ground,
    cover_path,
    emblem_for_book,
    palette_from_artwork,
    write_og_twin,
)
from library.curated_art import CURATED  # noqa: E402
from library.designed_covers import DERIVED_GROUND, is_designed  # noqa: E402

ROOT = BACKEND.parent
STATIC = ROOT / "frontend" / "static"
COVERS = STATIC / "covers"


def ensure_og_twin(slug: str, artwork: Path) -> bool:
    """Guarantee ``/covers/<slug>.png`` exists beside an SVG cover.

    og:image must be raster — WhatsApp, Facebook and X all refuse an SVG
    preview — so ``books/[slug]/+page.svelte`` falls back to
    ``/covers/<slug>.png`` whenever cover_url ends in .svg. Handing a row a
    localized SVG therefore silently arms that fallback, and these 15 works had
    a .jpg twin, not a .png: 49 rows would have shipped pointing og:image at a
    404. ``CoverAssetTests.test_covers_that_cannot_be_shared_have_a_raster_twin``
    catches it, which is how this was found.

    ONE TWIN PER WORK, AND THAT IS NO LONGER THE WHOLE STORY. This wrote
    `<slug>.png` because og:image was keyed by slug alone, so a translated
    page's card showed the English one — this docstring used to call fixing
    that "a different change". It has since been made: `covers.twin_path` and
    `coverArt.twinUrl` key a card by edition, and `frontend/npm run og:covers`
    draws one per row.

    What is left here is a STOPGAP, and it is worth knowing which. This writes
    the artwork rasterised, with no type on it; the card a reader actually sees
    has the book's title in its pixels and only the JS generator draws that. So
    this guarantees the English path is not a 404 the moment a localized SVG
    arms the fallback, and `npm run og:covers` supersedes it — which the
    translation-worker skill now names as a step, because `CoverAssetTests`
    asks for the per-language card that only that script produces.

    The DRAWING moved to ``covers.write_og_twin`` when
    ``build_derived_grounds`` needed the same twin for the same reason; what is
    left here is the decision to write one. Rasterising the localized SVGs
    instead — 58 files rather than 15 — measured ~15 MB, which is not worth a
    preview card.
    """
    name = f"{slug}.png"
    dest = COVERS / name
    if dest.exists():
        return False
    # `/covers/<slug>.png` is a generated twin for thirty works and a HAND-MADE
    # COVER for two — `baptism-with-the-holy-spirit` and
    # `prayer-the-pulse-of-life` are designed `.png`s at exactly this path. The
    # `exists()` above is what has been keeping them safe, which is to say
    # nothing has: delete one and re-run this, and a designed cover is silently
    # replaced by a machine crop of itself. Ask the registry, not the extension.
    if is_designed(f"/covers/{name}"):
        raise SystemExit(
            f"refusing to write {dest}: that path is {slug}'s designed cover "
            "(library.designed_covers.DESIGNED), not a twin to regenerate"
        )

    write_og_twin(artwork, dest)
    return True


def patch(path: Path, cover_url: str, cover_color: str | None = None) -> None:
    """Point one edition's fixture row at its own cover, in one write.

    ``cover_color`` is passed for the tiers that derive one here; the curated
    tier draws on a painting and leaves whatever the edition carries."""
    values = {"cover_url": cover_url}
    if cover_color is not None:
        values["cover_color"] = cover_color
    persist_fields(path, values)


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

    english: dict[str, dict] = {}
    editions: list[tuple[Path, str, str, dict]] = []
    # A slug filter, applied after the read. `book_editions()` parses every work
    # file (0.34s, 74 MB transient) whichever slugs are asked for — the shared
    # reader is worth more than the narrowing was, and a curation script run by
    # hand can afford it.
    wanted = set(args.slugs)
    for path, slug, language, fields in book_editions():
        if wanted and slug not in wanted:
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
        own_cover = fields.get("cover_url") or ""
        if own_cover.startswith(f"/covers/{language}/") and own_cover.endswith(RASTER_SUFFIXES):
            # This edition has designed artwork of its OWN — the one case where a
            # generated plate is a downgrade, and the same line generate_covers
            # draws with is_generated. Nothing in the library is here yet; the
            # fixture gate permits it, so the drawing tool must too.
            unchanged += 1
            continue
        title = fields["title"]
        color: str | None = None

        if slug in CURATED or slug in DERIVED_GROUND:
            # A wordless ground has no language. It is one shared file under
            # `covers/art/`, and BookCover draws this edition's title over it —
            # so there is nothing to DRAW here. Tested BEFORE the raster branch,
            # not after: the shared file IS a .jpg, so extension alone would
            # file it as designed artwork and draw a plate over a book that
            # already has a cover.
            #
            # TWO TIERS TAKE THIS PATH and they differ only in where the file
            # came from — `CURATED` is a public-domain painting fetched by
            # `build_curated_covers`, `DERIVED_GROUND` is a crop of this work's
            # OWN designed English cover, drawn by `build_derived_grounds`. What
            # happens to the fixture row is identical, so the branch is shared;
            # the registries stay separate because one carries a museum's
            # licence receipt and the other must never be mistaken for it.
            #
            # The English row is NOT here — this loop only sees translations —
            # which is exactly the point for the derived tier: English goes on
            # wearing the hand-made cover, untouched (library.designed_covers).
            #
            # The ROW still gets pointed at the painting. `translate_book` writes
            # `/covers/<lang>/<slug>.svg` for a new translation and those
            # per-language files no longer exist, so a freshly translated curated
            # edition arrives with a dangling cover_url — and reporting it
            # "unchanged" is how it would stay that way until `tests_fixture`
            # went red. Same URL `build_cover_assets.py` writes.
            url, _rel = art_url(slug)
            if fields.get("cover_url") != url:
                patched += 1
                if not args.dry_run:
                    patch(path, url)
                tier = "curated" if slug in CURATED else "derived"
                print(f"  ✓ {url:52} {tier:9} {'row':9} {'':8} {title}")
            else:
                unchanged += 1
            continue
        if source_cover.endswith(RASTER_SUFFIXES):
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
            tier = "artwork"
        else:
            # The house plate. A freshly translated row often carries no colour
            # of its own, and letting that fall to the default indigo would put
            # one edition of a work in a colour its siblings don't share — so
            # the work's English colour is inherited, and recorded.
            color = fields.get("cover_color") or source.get("cover_color") or ""
            tier = "generated"

        # One call for both tiers: they differ in where `color` comes from, not
        # in what is drawn from it.
        svg = build_ground(color, emblem=emblem_for_book(slug))

        url, rel = cover_path(slug, language)
        dest = COVERS / rel
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
