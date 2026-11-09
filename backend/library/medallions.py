"""Biography covers that wear their subject's portrait in a medallion.

A biography's cover is a painting like any other, and nothing on it said
whose life it was until the reader reached the title. So a biography wears a
round, sepia-toned portrait of its subject above the title (design review,
2026-11), cut from the subject's photo under `static/portraits/` and drawn by
both renderers through `cover-type.css`'s `.medallion`.

Each entry is cut BY HAND, because the source photos differ: a seated
full-length Livingstone, Amy Carmichael beside a child, a studio head-and-
shoulders. ``(cx, cy)`` is the face's centre as a fraction of the photo's width
and height; ``side`` is the square's side as a fraction of the photo's HEIGHT.
`scripts/build_medallions.py` cuts, tones and writes each to
`static/covers/medallions/<work>.webp`, and writes `coverMedallions.ts`.

LEFT OUT ON PURPOSE (founder decision, 2026-11): `c-s-lewis-a-life` and
`corrie-ten-boom-a-life`, whose only photos are likely still under copyright
and have no recorded licence; a cover travels further than the author page —
every shared link and the downloadable PDF and EPUB. `elisabeth-elliot-a-life`
has an illustration, not a likeness. Add one only with a photo that is public
domain or freely licensed, credited on its author row.
"""

from __future__ import annotations

from typing import NamedTuple


class Medallion(NamedTuple):
    portrait: str  # an author slug: static/portraits/<portrait>.jpg
    cx: float
    cy: float
    side: float


MEDALLIONS: dict[str, Medallion] = {
    "amy-carmichael-a-life": Medallion("amy-carmichael", 0.60, 0.46, 0.38),
    "c-t-studd-a-life": Medallion("c-t-studd", 0.48, 0.13, 0.22),
    "david-livingstone-a-life": Medallion("david-livingstone", 0.61, 0.25, 0.30),
    "george-muller-of-bristol": Medallion("george-muller", 0.55, 0.43, 0.48),
    "john-hyde-a-life": Medallion("john-hyde", 0.50, 0.47, 0.86),
    "mary-slessor-a-life": Medallion("mary-slessor", 0.50, 0.27, 0.44),
    "pandita-ramabai-a-life": Medallion("pandita-ramabai", 0.47, 0.34, 0.48),
    "samuel-ajayi-crowther-a-life": Medallion("samuel-ajayi-crowther", 0.52, 0.47, 0.58),
    "watchman-nee-a-life": Medallion("watchman-nee", 0.50, 0.42, 0.76),
}

#: The medallion's pixels: twice the largest it is drawn (30cqw of a 600px twin).
SIZE = 360
