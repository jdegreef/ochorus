#!/usr/bin/env python3
"""Measure how much scrim each painting actually needs.

    uv run python scripts/tune_art_scrim.py --dry-run
    uv run python scripts/tune_art_scrim.py
    uv run python scripts/tune_art_scrim.py <slug> ...   # re-measure only these

With slugs, the other entries are carried over from the committed table rather
than re-measured. That changes nothing in the output — each value depends only
on its own painting, whether its work has a subtitle, and where its editions'
lines fall (read from `og-manifest.json`, so run `npm run og:covers` first after
a new or retitled translation) — and it is the whole
cost of painting one cover otherwise: every painting in the library, ~2 s each.
Run it bare to re-measure everything (a crop change touching many works, or to
drop entries for paintings that are gone).

WHAT THIS IS FOR
`.cover-plate.over-art` darkens a painting so white type can sit on it, and its
SHAPE is shared — three bands following the byline, the title and the mark,
which are in the same place on every cover. How much of that a picture needs is
not shared at all: measured across the library the span is more than threefold.

One strength for all of them therefore has to be the maximum, and that is what
shipped first — every painting carried the weight the palest one needed, and the
library read at 53.2 per cent of its own brightness where it could read at 70.0.

The numbers in the generated tables are computed from the measurement rather
than typed here, because a hand-written span in a docstring is exactly the thing
that goes stale the first time a painting is recropped.

So this searches, per painting, for the LEAST strength that still clears AA
where the type falls, and writes `library/art_scrim.py`. The search is a walk
rather than a bisection: the predicate is contrast after an 8-bit composite, so
it is very slightly non-monotone, and a bisection that "agreed on every sample"
is not a guarantee. It costs seconds, offline.

RE-RUN THIS WHEN ARTWORK CHANGES — or when an edition's words do. A recropped
or replaced painting is a different picture and may need a different scrim; a
new translation, or a retitled one, puts its lines somewhere else. The lines are
read from `og-manifest.json`, so run `cd frontend && npm run og:covers` first,
this, then `og:covers` again to redraw the cards whose scrim moved.
`CoverAssetTests.test_every_painting_still_carries_white_type` fails the build
until the table matches what is on disk, and names the file.

Pillow is a dev-group dependency, like the rest of the cover tooling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.content_fixtures import book_editions  # noqa: E402
from library.covers import (  # noqa: E402
    INK_DARK,
    SCRIM_MAX,
    THIN_AT_FULL_SCRIM,
    H,
    W,
    ink_contrast,
    painting_ink_rows,
    scrimmed,
    subtitled_works,
)

ART = BACKEND.parent / "frontend" / "static" / "covers" / "art"
TABLE = BACKEND / "library" / "art_scrim.py"
TS_TABLE = BACKEND.parent / "frontend" / "src" / "lib" / "coverScrim.ts"

# The title runs 7.6-10.45cqw, which is large text: AA asks 3:1 of it, where the
# byline at 3.9cqw is small and asks 4.5. Both are held a little above their bar
# so a re-encode or a resampling difference cannot drop a painting under it.
MARGIN = 0.1


def needed(image, subtitle: bool, slug: str, rows: dict | None = None) -> float | None:
    """The least strength that clears every bar, or None if none does.

    ``subtitle`` says whether this work's covers draw one. It decides both
    whether the subtitle strip is measured AND whether the fourth scrim band is
    there to be measured against — the two go together, which is why one flag
    carries both.

    ``rows`` is where each edition's ink actually landed (`painting_ink_rows`):
    a translation whose subtitle wraps below the English strip is measured
    there, not at the English rows.

    The walk stops at `SCRIM_MAX`, the most the stylesheet can draw; it used to
    run to 2.00x, answering with strengths no page renders. At the ceiling the
    bar itself is enough — MARGIN is headroom to spend, and there is none left.
    """

    def worst_over_bar(strength: float) -> float:
        got = ink_contrast(scrimmed(image, strength, subtitle), slug, subtitle, rows)
        return min(worst - bar for worst, bar in got.values())

    for step in range(30, round(SCRIM_MAX * 100) + 1, 5):
        over = worst_over_bar(step / 100)
        if over >= MARGIN:
            return step / 100
    # The last step WAS the ceiling: its measurement answers the bar-only test.
    return SCRIM_MAX if over >= 0 else None


def main() -> int:
    from PIL import Image

    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*", help="Re-measure only these (default: all).")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()

    books = [fields for _path, _slug, _lang, fields in book_editions()]
    subtitled = subtitled_works(books)
    # Where every edition's type landed, from the og twin generator — run
    # `npm run og:covers` first if a title or subtitle changed.
    rows = painting_ink_rows(books)
    table, unusable = {}, []
    paths = sorted(ART.glob("*.jpg"))
    if opts.slugs:
        from library.art_scrim import ART_SCRIM

        table = dict(ART_SCRIM)
        missing = [s for s in opts.slugs if not (ART / f"{s}.jpg").exists()]
        if missing:
            print(f"no painting at covers/art/ for: {', '.join(missing)}", file=sys.stderr)
            return 1
        paths = [ART / f"{s}.jpg" for s in sorted(set(opts.slugs))]
    for path in paths:
        # A dark-ink ground carries no white type and no scrim; the fixture gate
        # measures its ink instead (`covers.INK_DARK`).
        if path.stem in INK_DARK:
            continue
        image = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
        strength = needed(image, path.stem in subtitled, path.stem, rows.get(path.stem))
        if strength is None:
            if path.stem not in THIN_AT_FULL_SCRIM:
                unusable.append(path.stem)
                continue
            # Known, and the founder's call — see `covers.THIN_AT_FULL_SCRIM`.
            thin = "; ".join(f"{k} {v}" for k, v in THIN_AT_FULL_SCRIM[path.stem].items())
            print(f"  {path.stem:44} {SCRIM_MAX:.2f}x  (thin: {thin})")
            table[path.stem] = SCRIM_MAX
            continue
        table[path.stem] = strength
        mark = " +subtitle" if path.stem in subtitled else ""
        print(f"  {path.stem:44} {strength:.2f}x{mark}")

    if unusable:
        print(
            f"\nno strength up to {SCRIM_MAX:.2f}x carries white type over: {', '.join(unusable)}\n"
            "That is a painting too pale for this composition, not a tuning problem "
            "— recrop it, or give the work a darker artwork.",
            file=sys.stderr,
        )
        return 1

    # A re-run for named slugs starts from the old table; drop any dark-ink
    # ground it still carries, so the table holds only works with a scrim.
    for slug in INK_DARK:
        table.pop(slug, None)

    # The SVG Originals are measured outside this script (it reads rasters) and
    # carried in on every run, bare or not, so re-tuning never drops them. See
    # `curated_art.ORIGINAL_SVG_SCRIM`.
    from library.curated_art import ORIGINAL_SVG_SCRIM

    table.update(ORIGINAL_SVG_SCRIM)

    span = sorted(table.values())
    print(f"\n{len(table)} paintings, {span[0]:.2f}x .. {span[-1]:.2f}x")
    if opts.dry_run:
        return 0

    body = "\n".join(f'    "{slug}": {k:.2f},' for slug, k in sorted(table.items()))
    TABLE.write_text(
        '"""How much scrim each painting needs — GENERATED by '
        "scripts/tune_art_scrim.py.\n\n"
        "The scrim's SHAPE is shared and lives in `covers.scrim_alpha`: three bands\n"
        "following the byline, the title and the mark, which sit in the same place on\n"
        "every cover. How much of it a picture needs is a property of the picture, and\n"
        f"the span here is {span[0]:.2f}x to {span[-1]:.2f}x — so one strength for all of\n"
        "them has to be the maximum, and every other painting pays for the palest.\n\n"
        "Measured, not chosen: each value is the least strength at which white type\n"
        "still clears AA where it falls, found by walking upward.\n"
        "`CoverAssetTests.test_every_painting_still_carries_white_type` re-measures\n"
        "every entry against the artwork on disk, so a recropped painting fails the\n"
        "build by name rather than shipping illegible.\n\n"
        "`frontend/src/lib/coverScrim.ts` is the same table for the two renderers\n"
        'that draw a cover; `coverScrim.test.ts` fails if the two drift.\n"""\n\n'
        "ART_SCRIM: dict[str, float] = {\n" + body + "\n}\n"
    )
    # THE SAME TABLE FOR THE TWO RENDERERS. `BookCover` and the share-card
    # script both draw a painting and both need its strength, and neither can
    # read Python. Written from here rather than hand-kept, and
    # `coverScrim.test.ts` fails if the two files disagree.
    ts_body = "\n".join(f"\t{slug!r}: {k:.2f}," for slug, k in sorted(table.items()))
    TS_TABLE.write_text(
        "// GENERATED by backend/scripts/tune_art_scrim.py — do not edit by hand.\n"
        "//\n"
        "// How much scrim each painting needs. The scrim's SHAPE lives in\n"
        "// `cover-type.css` and in `covers.scrim_alpha`; this is how far it is\n"
        "// scaled for one picture, measured as the least that still carries white\n"
        "// type over it. A painting with no entry takes 1, which is the strength\n"
        "// every painting carried before this table existed.\n"
        "//\n"
        "// `coverScrim.test.ts` holds this against `library/art_scrim.py`, and\n"
        "// `CoverAssetTests` re-measures that against the artwork on disk.\n\n"
        "export const COVER_SCRIM: Record<string, number> = {\n" + ts_body + "\n};\n\n"
        "/** How far to scale the scrim over one work's painting. */\n"
        "export function scrimStrength(slug: string): number {\n"
        "\treturn COVER_SCRIM[slug] ?? 1;\n"
        "}\n"
    )
    print(f"wrote {TABLE.relative_to(BACKEND)} and {TS_TABLE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
