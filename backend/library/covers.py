"""The generated plate GROUND — a book cover with no words on it.

A book without artwork gets a plate built from its own colour and the emblem of
the topic it belongs to. The TYPE that goes over it is not drawn here: it is
drawn in the browser by ``BookCover.svelte``, per author and per language. This
module owns the drawing of the ground; the ``generate_covers`` command owns
writing the files and updating rows.

WHY THE WORDS LEFT
They used to be here — the byline, the title, the rule, the subtitle and the
brand lockup, composited into the file. An SVG is served through ``<img>``,
which renders it in an isolated document that cannot reach the page's webfonts,
so this could only ever name fonts the DEVICE already had. Every generated
cover in the library therefore came out in Georgia, and no per-author or
per-century typography was expressible at all. The type moved to HTML to get
its hands on the real faces (see ``frontend/src/lib/coverStyles.ts``), and the
rest followed: the browser wraps where the words are rather than at a character
count, shapes Arabic, picks a Devanagari face, and sets a translated title
without this file knowing anything about scripts.

So what is left here is exactly what is NOT words, and there is now one drawing
of each thing rather than two: the ground in this file, the type in the
component. The proportions the two share — the frame inset, the byline's
height, the emblem's band — are copied deliberately and named on both sides
(STYLE_GUIDE §5); the algorithms never are.

STILL PER LANGUAGE, AND NO LONGER NEEDING TO BE
``cover_path`` still gives every ``(slug, language)`` its own file, which is
what it took to fix a real bug: the first generator wrote one ``<slug>.svg``
while looping over every language row, so the last row processed silently
overwrote the rest and a Spanish reader saw "All of Grace" over a card reading
"Todo por Gracia". A ground has no words in it, so those files are now
identical across languages and every edition could share one, as the paintings
already do. Consolidating them means repointing every translated row's
``cover_url`` — a fixture change, and its own PR.

WHY THE CONTRAST MODEL STAYED
The type is white wherever it is drawn, and a plate colour is data that nothing
between choosing it and drawing on it ever checked. ``ink_safe`` and the
arithmetic under it model the byline sitting at ``_AUTHOR_Y`` on this gradient
and floor the colour until white clears AA there. That the byline is now an
HTML element rather than a ``<text>`` node changes nothing about the colour
underneath it.
"""

from __future__ import annotations

import json
import math
import re
from functools import cache, lru_cache
from itertools import pairwise
from pathlib import Path

# The three cover-tier registries, for the two predicates below. Both are plain
# tables with no Django import between them and this, which is what lets the
# predicates live beside `art_url` rather than in a command.
from library.curated_art import CURATED, CURATED_GROUND, ORIGINAL_GROUND
from library.designed_covers import DERIVED_GROUND
from library.localization import is_english_edition

# A plain module, imported for exactly that reason — see its docstring.
from library.topic_seed import TOPICS

# The canvas. 3:4, matching BookCover's reserved box so nothing shifts.
W, H = 600, 800

# The hairline frame's inset, and the height the author line sits at. Neither is
# DRAWN here any more — the frame is `.type::before` and the byline is a div, both
# in `BookCover.svelte`, which state them as 4.3cqw and 17cqw of a plate whose
# container width is W. They stay because the contrast model below is a claim
# about the colour under that byline, and it has to be told where the byline is.
_FRAME_INSET = 26
_AUTHOR_Y = 112

#: Cover files a reader downloads as pixels, and the widths they are built at.
#: `scripts/build_cover_assets.py` writes the variants, `BookCover` asks for
#: them by name, and a fixture gate proves they exist — three readers of one
#: rule, so the rule lives here.
RASTER_SUFFIXES = (".jpg", ".jpeg", ".png")
COVER_WIDTHS = (320, 640)


def art_url(slug: str) -> tuple[str, str]:
    """(url, path under the covers dir) for a work's shared painting.

    One file per work, not per edition: a painting carries no words, so every
    language points at it and ``BookCover`` draws that edition's title over it.
    """
    return f"/covers/art/{slug}.jpg", f"art/{slug}.jpg"


def shares_a_ground(slug: str) -> bool:
    """Does this work's artwork live in ONE wordless file under ``covers/art/``?

    True for all three shared-ground tiers, which differ in where that file
    comes from and in nothing a caller of this cares about:

    * ``CURATED`` — a museum painting, fetched by ``build_curated_covers``.
    * ``DERIVED_GROUND`` — a crop of the work's own designed English cover,
      drawn by ``scripts/build_derived_grounds.py``.
    * ``CURATED_GROUND`` — a museum painting for a work that HAS a designed
      English cover but no croppable picture inside it.
    * ``ORIGINAL_GROUND`` — an illustration drawn for the work itself (an
      Ochorus Original), frozen by digest because no recipe can redraw it.

    Three call sites spelled the membership out as an ``or`` over two tables —
    ``generate_covers``, ``scripts/localize_covers.py`` and
    ``scripts/build_cover_assets.py``. A third tier is what turns that
    repetition into a hazard: miss one site and a work is half in the tier,
    which does not fail loudly — it draws a plate over a book that already has
    a cover, or ships a painting with no webp variants. A fourth only sharpens
    it, which is why membership stays behind this one predicate.
    """
    return (
        slug in CURATED
        or slug in DERIVED_GROUND
        or slug in CURATED_GROUND
        or slug in ORIGINAL_GROUND
    )


def keeps_english_designed(slug: str) -> bool:
    """Does English wear a hand-made cover while the translations wear a ground?

    The exception inside ``shares_a_ground``. A ground exists so a translated
    edition is not stuck with English words baked into a raster; the English
    edition has no such problem and goes on wearing the cover someone drew for
    it. Repointing it at the ground is the precise loss both designed-cover
    tiers exist to prevent.

    ``CURATED`` and ``ORIGINAL_GROUND`` are the tiers this is false for: those
    works have no designed cover, so every one of their languages — English
    included — takes the shared picture.
    """
    return slug in DERIVED_GROUND or slug in CURATED_GROUND


def variant_url(cover_url: str, width: int) -> str:
    """The webp variant of a raster cover at `width`."""
    return f"{cover_url.rsplit('.', 1)[0]}-{width}.webp"


def cover_path(slug: str, language: str) -> tuple[str, str]:
    """(url, path under the covers dir) for one edition's generated cover.

    English keeps the historic root path so the covers already live don't 404;
    every other language sits under its own directory. Lives here rather than in
    ``generate_covers`` because four callers assert this layout — the command,
    ``build_curated_covers``, ``scripts/localize_covers.py`` and the fixture gate
    that fails a row wearing another language's cover — and a rule spelled out
    four times is a rule that will be changed in three places.
    """
    if language == "en":
        return f"/covers/{slug}.svg", f"{slug}.svg"
    return f"/covers/{language}/{slug}.svg", f"{language}/{slug}.svg"


# ── The scrim over a painting ──────────────────────────────────────────────
# `cover-type.css`'s `.cover-plate.over-art`, as a curve, so Python can composite
# what a reader sees. Two callers need it: `build_derived_grounds --preview`,
# and the fixture gate that checks every committed painting still carries white
# type. It was a hand-copy inside the first of those; a second copy would be one
# too many.
#
# STATED AS THE CURVE, not as the CSS's 41 sampled stops. The stylesheet has no
# cosine so it samples this; sampling it again here would be reproducing an
# approximation rather than the thing approximated. `coverArtContrast.test.ts`
# is what holds the CSS to this shape from the other side.
_SCRIM_BANDS = ((0.13, 0.20, 0.60), (0.91, 0.20, 0.60))
_SCRIM_FLOOR = 0.10
_SCRIM_STRENGTH = 1.1
_SCRIM_CEILING = 0.88


def scrim_alpha(f: float, strength: float = 1.0) -> float:
    """How black the PLATE's scrim layer is a fraction ``f`` down it, 0-1.

    Two cosine bands — the byline and the mark, which sit at the same height on
    every cover — over a floor that is never zero. The title and subtitle are
    NOT here any more: they move with the words (`middle_band_alpha`), because a
    translated title wraps longer and lands lower, and a band fixed at the
    English rows left 20 of Brave for God's 26 editions setting white type on
    pale art.

    ``strength`` scales the whole scrim for ONE painting (``ART_SCRIM``): the
    shape follows the type, how much of it a picture needs is the picture's.
    """
    a = _SCRIM_FLOOR
    for centre, half, peak in _SCRIM_BANDS:
        d = abs(f - centre) / half
        if d < 1.0:
            a = max(a, _SCRIM_FLOOR + (peak - _SCRIM_FLOOR) * (0.5 + 0.5 * math.cos(math.pi * d)))
    return min(_SCRIM_CEILING, strength * _SCRIM_STRENGTH * a)


# ── The band that follows the type ─────────────────────────────────────────
#
# `.middle` holds the volume numeral, the title, the rule and the subtitle, and
# is centred between the byline and the mark by auto margins (or set from the
# top, on a TYPE_TOP cover). So wherever a translation's longer title pushes the
# words, `.middle` is exactly where they are, and a band hung off it
# (`.middle::after` in `cover-type.css`) goes with them.
#
# The band is a plateau across the block with cosine shoulders beyond it, wide
# enough to merge into the plate's layer rather than read as a stripe; on a
# cover that draws a subtitle its foot is darker, because the subtitle is small
# type at a lower ink opacity and always the last thing in the block.
#
# STATED AS STOPS, not as a curve, because it is anchored to a box whose height
# varies: the stylesheet writes these same stops (in `cqw`, from the band's top
# or its bottom), and `middle_band_alpha` evaluates them the way a browser
# evaluates a gradient — linear between stops, a stop that would fall before
# the previous one clamped to it. `tests_covers.MiddleBandCssTests` holds the
# CSS to `middle_band_stops`.

#: The shoulder beyond the block, above and below (cqw; 6px each on the plate).
#: Wide enough that the band's edge melts into the plate's floor; narrower
#: darkens more of the picture than the words need.
_BAND_FEATHER = 12
#: A subtitle-carrying block's darker foot: its depth (two subtitle lines, in
#: the tallest script) and the ramp into it.
_BAND_FOOT, _BAND_RAMP = 11.5, 4
#: Peak alpha over the title and over the subtitle, at full strength. CHOSEN BY
#: SWEEPING, since every painting's strength is re-tuned against whatever shape
#: this is: the shape that leaves the library brightest while carrying every
#: edition. At 16cqw / 0.59 / 0.74 (the old bands' peaks) readers saw 69.5% of
#: the paintings' brightness; here 73.1%, against 69.0% under the fixed bands.
_BAND_TITLE, _BAND_SUBTITLE = 0.40, 0.65
_CQW = W / 100


def _rise(t: float) -> float:
    """0 -> 1 along a cosine, for t in 0-1."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


@cache
def middle_band_stops(subtitle: bool) -> tuple[tuple[str, float, float], ...]:
    """The band's gradient as (anchor, cqw, alpha): ``anchor`` is "top" for an
    offset from the band's top edge, "bottom" for one up from its bottom edge.
    The band's box is `.middle` grown by `_BAND_FEATHER` above and below.
    """
    f, n = _BAND_FEATHER, 8
    peak = _BAND_SUBTITLE if subtitle else _BAND_TITLE
    stops = [("top", round(f * k / n, 2), round(_BAND_TITLE * _rise(k / n), 3)) for k in range(n + 1)]
    if subtitle:
        foot = f + _BAND_FOOT
        stops += [
            (
                "bottom",
                round(foot + _BAND_RAMP * (1 - j / 4), 2),
                round(_BAND_TITLE + (_BAND_SUBTITLE - _BAND_TITLE) * _rise(j / 4), 3),
            )
            for j in range(5)
        ]
    stops += [
        ("bottom", round(f * (n - k) / n, 2), round(peak * _rise((n - k) / n), 3))
        for k in range(n + 1)
    ]
    return tuple(stops)


@cache
def _band_points(middle: tuple[int, int], subtitle: bool) -> tuple[float, tuple[tuple[float, float], ...]]:
    """The band's top on the plate, and its stops as (offset from it, alpha) —
    placed the way a browser places them: a stop that would fall before the
    previous one is clamped to it rather than reordered."""
    top = middle[0] - _BAND_FEATHER * _CQW
    height = middle[1] - middle[0] + 2 * _BAND_FEATHER * _CQW
    points, last = [], -math.inf
    for anchor, cqw, alpha in middle_band_stops(subtitle):
        last = max(last, cqw * _CQW if anchor == "top" else height - cqw * _CQW)
        points.append((last, alpha))
    return top, tuple(points)


def middle_band_alpha(y: float, middle: tuple[int, int], subtitle: bool) -> float:
    """How black the band over `.middle` (top, bottom) is at plate row ``y``, at
    full strength — the stops above, evaluated as the browser does: linear
    between them, and at a clamped jump, the later one."""
    top, points = _band_points(tuple(middle), subtitle)
    offset = y - top
    for (p0, a0), (p1, a1) in pairwise(points):
        if p0 <= offset <= p1 and p1 > p0:
            return a0 + (a1 - a0) * (offset - p0) / (p1 - p0)
    return 0.0


@cache
def _band_column(middle: tuple[int, int], subtitle: bool) -> tuple[float, ...]:
    """The band's alpha down every row of the plate, at full strength (sampled
    at pixel centres). Strength does not move it, so the tuner's walk reuses it."""
    return tuple(middle_band_alpha(y + 0.5, middle, subtitle) for y in range(H))


@cache
def _plate_column(strength: float) -> tuple[float, ...]:
    """The plate layer's alpha down every row, at one strength."""
    return tuple(scrim_alpha(y / (H - 1), strength) for y in range(H))


def scrimmed(ground, strength: float, middle: tuple[int, int], subtitle: bool):
    """A painting as a reader sees one edition of it: the artwork under both
    scrim layers — the plate's, and the band over that edition's `.middle`
    (top, bottom). ``subtitle`` is whether THIS edition draws one; the band's
    foot is darker when it does.

    The layers are separate elements, so they composite rather than taking the
    max, and each is scaled by the painting's strength — clamped at `SCRIM_MAX`,
    as the page's `opacity` is.
    """
    from PIL import Image

    strength = min(strength, SCRIM_MAX)
    alphas = []
    for plate, band in zip(_plate_column(strength), _band_column(tuple(middle), subtitle), strict=True):
        alphas.append(round(255 * (1 - (1 - plate) * (1 - strength * band))))
    column = Image.new("L", (1, H))
    column.putdata(alphas)
    return Image.composite(
        Image.new("RGB", (W, H), (0, 0, 0)),
        ground.convert("RGB"),
        column.resize((W, H)),
    )


def twin_path(slug: str, language: str) -> tuple[str, str]:
    """(url, path under the covers dir) for one edition's og:image twin.

    A twin is the cover PHOTOGRAPHED — the ground with the title drawn over it,
    flattened to a raster, because every social platform refuses an SVG and a
    painting carries no words of its own. So it is per EDITION, not per work:
    the title is in the pixels.

    That is what this function exists to stop anyone forgetting again. og:image
    resolved to ``/covers/<slug>.png``, keyed by slug alone, so sharing the
    Arabic page of a book posted a card with the ENGLISH title on it — for every
    translated edition in the library, in prerendered HTML the runtime never got
    to correct. Both fixture gates read the same wrong path and agreed it was
    fine.

    Same layout as ``cover_path`` above and for the same reason: English keeps
    the historic root path so cards already shared do not 404, everything else
    sits under its language. ``frontend/src/lib/coverArt.ts``'s ``twinUrl`` is
    the JS side of this one rule — the generator and the page both read it from
    there, and ``CoverAssetTests`` reads it from here.
    """
    if is_english_edition(language):  # the Modern English edition shares English's
        return f"/covers/{slug}.png", f"{slug}.png"
    return f"/covers/{language}/{slug}.png", f"{language}/{slug}.png"


def twin_key(slug: str, language: str) -> str:
    """How `og-manifest.json` names one edition's twin: its path, no extension."""
    return twin_path(slug, language)[1].removesuffix(".png")


# The ink is white at these opacities. The byline is set at 3.9cqw — 23px on the
# 600-wide plate this module's geometry describes — which is NOT "large text"
# under WCAG 1.4.3, so AA asks 4.5:1 of it. The title runs 7.6-10.45cqw and asks
# 3:1, which every colour that satisfies the byline clears with room to spare
# (the worst measured is 5.08 against a 3.0 bar). So the byline is the binding
# constraint, and the only one checked.
#
# Both sizes are `BookCover`'s now, not this module's — the type moved to HTML —
# but the QUESTION is still this module's: what colour is under white ink at
# that height. See `cover-type.css` for where the numbers are set.
AUTHOR_INK_OPACITY = 0.86
AUTHOR_MIN_CONTRAST = 4.5

TITLE_MIN = 3.0

#: What each inked thing asks of the ground under it: (ink opacity, bar).
#:
#: The bars are WCAG: 4.5:1 for the byline and subtitle, which are small text,
#: 3:1 for the title (7.6-10.45cqw is large text) and for the brandmark, which
#: is a graphic rather than words. The opacities are what `cover-type.css`
#: actually sets over artwork.
INK = {
    "byline": (AUTHOR_INK_OPACITY, AUTHOR_MIN_CONTRAST),
    "title": (1.0, TITLE_MIN),
    "subtitle": (0.90, AUTHOR_MIN_CONTRAST),
    "mark": (0.95, 3.0),
}

#: The rows the byline and the brandmark occupy — the two things that sit at
#: the same height on every cover, measured in the browser at 600x800: the
#: byline at 102-129, the brandmark at 664-746. They are measured here as well
#: as at each edition's own lines, because they are also where the plate's own
#: scrim peaks. (The title and subtitle move, so they are measured only where
#: an edition sets them.) The byline strip was once 8px short of the real
#: byline, and five paintings failed in the rows it did not look at.
_FIXED_ROWS = {"byline": (102, 130), "mark": (664, 747)}

#: The most scrim the stylesheet can draw. `--scrim-strength` is the scrim
#: layer's CSS `opacity`, which clamps at 1 — so a table value above this is a
#: scrim no reader ever sees, and a model that scales past it (``scrim_alpha``
#: does) would pass a painting the page leaves pale.
SCRIM_MAX = 1.0

#: The painted works whose type is set from the TOP of the cover rather than
#: centred: `coverLayouts.TYPE_TOP`, mirrored here because the scrim is measured
#: in Python. A fixture gate holds the two sets equal.
TYPE_TOP = frozenset({
    "key-teachings-of-a-b-simpson",
    "key-teachings-of-jonathan-edwards",
    "key-teachings-of-richard-baxter",
    "key-teachings-of-watchman-nee",
    "key-teachings-of-charles-h-spurgeon",
    "key-teachings-of-andrew-murray",
    "key-teachings-of-hannah-whitall-smith",
    "key-teachings-of-catherine-booth",
    "key-teachings-of-augustine-of-hippo",
    "key-teachings-of-amanda-berry-smith",
    "key-teachings-of-hudson-taylor",
    "key-teachings-of-athanasius-of-alexandria",
    "key-teachings-of-julia-foote",
    "key-teachings-of-jeanne-guyon",
    "key-teachings-of-r-a-torrey",
    "key-teachings-of-dwight-l-moody",
    "key-teachings-of-john-bunyan",
    "key-teachings-of-john-wesley",
    "key-teachings-of-charles-finney",
    "key-teachings-of-john-owen",
    "key-teachings-of-e-m-bounds",
    "key-teachings-of-frederick-brotherton-meyer",
    "key-teachings-of-george-whitefield",
    "key-teachings-of-ignatius-of-antioch",
    "key-teachings-of-john-calvin",
    "key-teachings-of-martin-luther",
    "key-teachings-of-a-w-tozer",
    "key-teachings-of-martyn-lloyd-jones",
    "key-teachings-of-corrie-ten-boom",
    "key-teachings-of-derek-prince",
    "key-teachings-of-dietrich-bonhoeffer",
    "key-teachings-of-gareth-evans",
    "key-teachings-of-c-s-lewis",
    "key-teachings-of-g-k-chesterton",
})

#: The brandmark's own columns (`BookCover`'s centred lockup). Only a TYPE_TOP
#: cover is measured there rather than across the frame: its picture sits
#: behind the mark, and the lit objects either side of it carry no ink.
_MARK_X = (232, 368)


#: How far a measured line may overhang a fixed strip and still BE that strip.
#: The strips were measured in the browser to the pixel; the lines in the og
#: manifest are rounded to the nearest one, and every byline's comes back
#: ending at 131 against the strip's 130 — a row of line leading no glyph
#: reaches, measured twice.
_ROW_SLACK = 1


def _inside(box, outer, slack: int = 0) -> bool:
    """Whether crop box ``box`` lies within ``outer``, give or take ``slack`` rows."""
    return (
        box[0] >= outer[0]
        and box[2] <= outer[2]
        and box[1] >= outer[1] - slack
        and box[3] <= outer[3] + slack
    )


def ink_boxes(slug: str, rows: dict):
    """Each inked strip of one edition of `slug`'s cover as (name, box, ink
    opacity, bar). ``box`` is a PIL crop box on the 600x800 plate. One answer
    for the scrim tuner and the fixture gate, so the rows one tunes to are the
    rows the other holds.

    ``rows`` is where THIS edition's lines were measured (`painting_editions`):
    region -> the box of every line. The title and subtitle are measured at
    those lines alone — the band over them moves with the words, so there is no
    fixed place for them — and the byline and mark at their fixed strips
    plus any line outside one.
    """
    for name, (opacity, bar) in INK.items():
        lines = {
            (max(0, a), max(0, b), min(W, c), min(H, d))
            for a, b, c, d in rows.get(name, ())
        }
        if name in _FIXED_ROWS:
            x0, x1 = _MARK_X if slug in TYPE_TOP and name == "mark" else (_FRAME_INSET, W - _FRAME_INSET)
            y0, y1 = _FIXED_ROWS[name]
            strip = (x0, y0, x1, y1)
            yield name, strip, opacity, bar
            lines = {box for box in lines if not _inside(box, strip, _ROW_SLACK)}
        for box in sorted(lines):
            # One inside another is the same pixels asked twice.
            if not any(other != box and _inside(box, other) for other in lines):
                yield name, box, opacity, bar


#: Where `npm run og:covers` records, per edition, where its type landed.
OG_MANIFEST = (
    Path(__file__).resolve().parents[2] / "frontend" / "static" / "covers" / "og-manifest.json"
)


def painting_editions(books, manifest: dict | None = None) -> dict[str, list[dict]]:
    """Painting stem -> every FRAMED edition wearing it, as it was laid out.

    Each is ``{"key", "rows", "middle", "subtitle"}``: the lines its ink sits in,
    the `.middle` block the scrim's band hangs off (top, bottom), and whether it
    draws a subtitle — read from the lines the browser actually set, the same
    fact `BookCover`'s `has-subtitle` is drawn from. The og twin generator lays
    out every edition anyway, so it records these (`generate-cover-og.mjs`'s
    ``measureInk``).

    WHY PER EDITION. A translated title wraps longer and the words land lower:
    on Brave for God the Luganda and Swahili subtitles reached y595, and 20 of
    26 editions set white type on pale art while a gate measuring the English
    rows passed. Each edition is its own plate — its own band position — and is
    measured at its own lines; the painting's one strength must carry them all.

    ``books`` is an iterable of Book fixture ``fields``. A laid-out edition sets
    dark ink on paper with no scrim, so it records nothing and is absent here —
    and a painting worn ONLY by laid-out editions is absent altogether: no
    reader sees it under a scrim, so there is nothing to tune or to hold.
    (`coverOgManifest.test.ts` fails a framed edition with nothing recorded.)
    """
    if manifest is None:
        manifest = json.loads(OG_MANIFEST.read_text())
    twins = manifest["twins"]
    out: dict[str, list[dict]] = {}
    for fields in books:
        cover = fields.get("cover_url") or ""
        if not cover.startswith("/covers/art/"):
            continue
        key = twin_key(fields["slug"], fields["language"])
        entry = twins.get(key, {})
        if "rows" not in entry or "middle" not in entry:
            continue
        rows = {name: [tuple(b) for b in lines] for name, lines in entry["rows"].items()}
        out.setdefault(Path(cover).stem, []).append(
            {"key": key, "rows": rows, "middle": tuple(entry["middle"]), "subtitle": "subtitle" in rows}
        )
    return out


def painting_contrast(image, strength: float, slug: str, editions) -> dict:
    """Region -> (worst contrast, its bar, the edition it is worst on) for one
    painting at one strength, over every framed edition wearing it
    (its entry in `painting_editions`)."""
    out: dict[str, tuple[float, float, str]] = {}
    for ed in editions:
        plate = scrimmed(image, strength, ed["middle"], ed["subtitle"])
        for name, (got, bar) in ink_contrast(plate, slug, ed["rows"]).items():
            if name not in out or got < out[name][0]:
                out[name] = (got, bar, ed["key"])
    return out


#: sRGB channel -> linear light, for every 8-bit value. The contrast sweep
#: reads hundreds of thousands of pixels per painting; `_relative_luminance`
#: reads it too, so the plate check and the painting check share one curve.
_LINEAR = tuple(
    c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    for c in (v / 255 for v in range(256))
)


def _ink_luminance(channels) -> float:
    """WCAG 2.x relative luminance of an 8-bit RGB triple."""
    r, g, b = channels
    return 0.2126 * _LINEAR[r] + 0.7152 * _LINEAR[g] + 0.0722 * _LINEAR[b]


@cache
def _inked(opacity: float) -> tuple[float, ...]:
    """Channel value -> linear light once white ink at ``opacity`` is laid over it."""
    return tuple(_LINEAR[round(255 * opacity + c * (1 - opacity))] for c in range(256))


def worst_ink_contrast(band, opacity: float) -> float:
    """Least white-on-artwork contrast anywhere in a band of pixels.

    Over the band's distinct colours: the answer is a minimum over pixels, so a
    colour repeated a thousand times is the same question asked a thousand times.
    White ink only ever lightens what is under it, so the ink is the lighter of
    the two and the ratio needs no max/min.
    """
    ink, lin = _inked(opacity), _LINEAR
    out = 1e9
    for _count, (r, g, b) in band.getcolors(band.width * band.height):
        ratio = (0.2126 * ink[r] + 0.7152 * ink[g] + 0.0722 * ink[b] + 0.05) / (
            0.2126 * lin[r] + 0.7152 * lin[g] + 0.0722 * lin[b] + 0.05
        )
        if ratio < out:
            out = ratio
    return out


def ink_contrast(plate, slug: str, rows: dict) -> dict:
    """Region -> (worst white-ink contrast, its bar) on one edition's scrimmed
    plate, at `ink_boxes`; `painting_contrast` runs this over each edition."""
    out: dict[str, tuple[float, float]] = {}
    for name, box, opacity, bar in ink_boxes(slug, rows):
        got = worst_ink_contrast(plate.crop(box), opacity)
        if name in out:
            got = min(got, out[name][0])
        out[name] = (got, bar)
    return out


#: Framed works whose PALE ground takes DARK ink and no scrim:
#: `coverLayouts.INK_DARK`, mirrored here so the gate measures the right ink.
#: The scrim tuner skips them (there is no white type to carry), and the
#: fixture gate holds their dark ink to the same bars instead.
INK_DARK = frozenset({
    "daughters-of-the-king-1",
    "daughters-of-the-king-2",
    "daughters-of-the-king-3",
    "sons-of-the-king-1",
    "sons-of-the-king-2",
    "sons-of-the-king-3",
})

#: `--cover-ink-dark` in `cover-type.css`.
DARK_INK = (0x23, 0x1A, 0x24)

#: Where the dark ink sits on an INK_DARK cover, as (name, box, ink opacity,
#: bar): the text column (the widest line any edition sets) by the union of
#: every edition's rows, measured on the composed covers. The flowers that
#: frame these grounds live in the side margins, outside the column.
DARK_INK_BOXES = (
    # Glyphs span x85-515 (the English "Growing Up" subtitle); the column holds
    # 25px either side. Rows are the union over Daughters (en, am) and Sons
    # (en), measured 2026-09-30, with a few px of margin. A new dark-ink work,
    # or a translation whose title wraps longer, must be re-measured on its
    # composed twin before it is trusted to this table.
    ("byline", (60, 100, 540, 133), AUTHOR_INK_OPACITY, AUTHOR_MIN_CONTRAST),
    # The ring and its numeral; the ring line is the faintest ink (0.72).
    ("volume", (266, 228, 334, 332), 0.72, 3.0),
    ("title", (60, 316, 540, 456), 1.0, TITLE_MIN),
    ("subtitle", (60, 474, 540, 566), 0.90, AUTHOR_MIN_CONTRAST),
    ("mark", (232, 662, 368, 748), 0.95, 3.0),
)
# The plate gradient's far stop, as a fraction of the base colour.
# `build_ground` paints from this same constant, so the contrast model cannot
# drift from the artwork it measures.
_GRADIENT_END = 0.55

# The gradient runs to (0.35, 1) in object-bounding-box units, so a point's
# colour depends on how far it projects along that vector.
_GRADIENT_VECTOR = (0.35, 1.0)


def _gradient_t(x: float, y: float) -> float:
    """How far along the plate gradient the point (x, y) sits, 0-1."""
    vx, vy = _GRADIENT_VECTOR
    return (vx * (x / W) + vy * (y / H)) / (vx * vx + vy * vy)


# Measured at the LEFTMOST point the byline can reach, not at its centre. The
# line is centred and letter-spaced and runs 250-400px wide, and the gradient
# darkens toward the right — so its left end sits on a lighter plate than its
# middle, and a floor set from the middle leaves the first few words below AA
# (measured: a plate floored to 4.53:1 at x=300 gives 4.05:1 at the frame).
# How wide the line actually is depends on the author's name and on a font the
# device supplies, neither known here, so the bound is the frame: type cannot
# start left of it.
_AUTHOR_GRADIENT_T = _gradient_t(_FRAME_INSET, _AUTHOR_Y)


def _channels(hex_color: str) -> tuple[int, int, int]:
    # Validated, not just measured: `cover_color` is an unvalidated CharField and
    # the fixtures are hand-edited, so a 6-character value that isn't hex
    # ("orange") is reachable — and `int(h[i:i+2], 16)` raises on it, which would
    # replace a named assertion failure with a stack trace.
    h = (hex_color or "").lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        h = "3b5bdb"
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(channels) -> str:
    return "#" + "".join(f"{c:02x}" for c in channels)


def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.x relative luminance of a colour."""
    return _ink_luminance(_channels(hex_color))


def _author_plate_color(hex_color: str) -> str:
    """The colour actually under the author line, not the plate's top stop.

    The byline sits at y=112 on a 600x800 plate painted with a gradient running
    to ``(0.35, 1)``, so its colour is already a little darker than the top stop
    — by how much depends on where along the line you stand, which is what
    ``_AUTHOR_GRADIENT_T`` above settles. The vignette is fully transparent that
    high (it starts at 0.55 of a 0.78 radius centred at 0.42), so the gradient is
    the whole story. Modelling it matters: taking the top stop instead reads ~0.6
    of a ratio point low, which would darken plates that are in fact legible.
    """
    return _darken(hex_color, 1 - (1 - _GRADIENT_END) * _AUTHOR_GRADIENT_T)


def author_ink_contrast(hex_color: str) -> float:
    """Contrast of the author line against the plate it sits on.

    The ink is white at ``AUTHOR_INK_OPACITY``, so what the reader sees is white
    composited over the plate, not white — a third of a ratio point, and the
    difference between passing and failing on the paler plates.
    """
    behind = _author_plate_color(hex_color)
    plate = _channels(behind)
    ink = _hex(round(AUTHOR_INK_OPACITY * 255 + (1 - AUTHOR_INK_OPACITY) * c) for c in plate)
    light, dark = _relative_luminance(ink), _relative_luminance(behind)
    return (light + 0.05) / (dark + 0.05)


def ink_safe(hex_color: str) -> str:
    """The plate colour, darkened just enough to carry white ink at AA.

    Ochorus' covers are white type on a coloured plate, always — the frame, the
    rules, the byline and the lockup are all white, and a per-cover decision to
    flip to dark ink would break the one thing the generated and designed tiers
    have in common. So the colour yields, not the ink.

    8 of the library's 45 plate colours could not carry it, across 25 book rows
    — `the-unselfishness-of-god` worst at 2.81:1 — because a plate colour is DATA
    (a hand-picked hex, or one sampled from the English artwork) and nothing
    between choosing it and drawing on it ever asked whether white could sit on
    it. Colours that already pass are returned untouched, so the other 37 and
    every cover drawn from them are left byte-identical.

    Applied where a colour is MINTED — `palette_from_artwork`, the admin import,
    and the hand-picked hexes in `catalog.py`, all of which land in the fixture
    already floored — rather than only where one is drawn. A floor at the drawer
    has to be copied into every other drawer (the client fallback was a second
    copy of this arithmetic, and two surfaces that paint the raw colour were
    still missed), and it leaves the stored data permanently disagreeing with
    the artwork that ships. `build_ground` still calls this, but on floored data it
    is a no-op standing guard over a row that reached the DB some other way.

    Scaling channels rather than moving through HLS keeps the hue and the
    saturation exactly where the curator put them: a green plate comes back a
    deeper green, never a grey or a different green.
    """
    # Normalised first, so a blank or malformed value comes back as the default
    # rather than as itself with a "#" bolted on.
    hex_color = _hex(_channels(hex_color))
    if author_ink_contrast(hex_color) >= AUTHOR_MIN_CONTRAST:
        return hex_color
    # A search, not a formula: sRGB gamma is applied per channel AFTER the
    # truncation in `_darken`, and the ink is composited over the plate, so both
    # sides of the ratio move with the factor. Integer steps rather than a float
    # accumulator, and linear rather than binary, because that truncation makes
    # the predicate very slightly non-monotone — a bisection agreed on every
    # colour sampled, but "agreed on the sample" is not a guarantee, and the walk
    # costs microseconds in an offline command.
    for step in range(99, 0, -1):
        candidate = _darken(hex_color, step / 100)
        if author_ink_contrast(candidate) >= AUTHOR_MIN_CONTRAST:
            return candidate
    return "#000000"  # unreachable: black passes at 21:1


def _darken(hex_color: str, factor: float = 0.55) -> str:
    return _hex(max(0, int(c * factor)) for c in _channels(hex_color))


# The topic emblem is the only thing drawn on a ground besides the colour.
#
# The brand lockup used to be read here too and composited at the foot of every
# plate. It is drawn by `BrandMark.svelte` now, over the ground rather than in
# it, like the rest of the cover's furniture — so this module reads only the
# emblems. `backend/library/data/brand/` stays the canonical copy of the
# artwork (`brandAssets.test.ts` mirrors it into the frontend and fails on
# drift); nothing in the API image draws from it any more.
_EMBLEM_DIR = Path(__file__).resolve().parent / "data" / "emblems"

#: The emblem's band, in plate units.
#:
#: FIXED, where it used to be fitted. The old placement measured the band
#: between the last line of type and the lockup and sized the drawing to what
#: was left, because a four-line title pushed the type 52 units further down
#: than a one-line one. Nothing here knows where the type ends any more — the
#: browser wraps it — so the band is reserved instead, and `BookCover`'s
#: `.emblem-band` holds the type off it from the other side.
#:
#: Read off that component, whose foot is 9cqw of padding under a 13.7cqw mark,
#: with a 4cqw gap above it. `W` is the container those `cqw` are of, so a cqw
#: is six plate units. 20cqw of drawing was chosen at 300px and at thumbnail
#: size, which is where covers are mostly seen: smaller and it is a smudge,
#: larger and it crowds the lockup into looking like a second device.
_EMBLEM_W = 120
_EMBLEM_GAP = 24
_MARK_H = 82
_FOOT_PAD = 54
_EMBLEM_BOTTOM = H - _FOOT_PAD - _MARK_H - _EMBLEM_GAP
_EMBLEM_TOP = _EMBLEM_BOTTOM - _EMBLEM_W


@lru_cache(maxsize=1)
def _book_emblems() -> dict[str, str]:
    """Book slug → the emblem it wears, through the topic it belongs to.

    Built from the topic seed rather than the database, so a cover can be drawn
    without one — the covers are committed files built by hand, and requiring a
    seeded DB to know a book's topic would make the artwork depend on the state
    of whatever machine ran the command. `topic_seed` is a plain module for
    exactly this reason: `seed_topics` pulls in `django.core.management`, and
    this one is imported by scripts that never call `django.setup()`.

    A book in more than one topic takes the first that has an emblem, in seed
    order: the shelves are ordered by how central the topic is, so the first is
    the one a reader is likeliest to have met the book under.
    """
    assignments = json.loads((_EMBLEM_DIR / "topics.json").read_text())["topics"]
    emblems: dict[str, str] = {}
    for topic_slug, _title, _description, book_slugs in TOPICS:
        if topic_slug not in assignments:
            continue
        for slug in book_slugs:
            emblems.setdefault(slug, assignments[topic_slug])
    return emblems


def emblem_for_book(slug: str) -> str | None:
    """The emblem a book wears, or None if no topic holds it."""
    return _book_emblems().get(slug)


@lru_cache(maxsize=16)
def _read_art(path: Path) -> tuple[str, float, float] | None:
    """A committed SVG's inner markup and its viewBox size, or None if unusable.

    The artwork on both sides of this module — the brand lockup and the topic
    emblems — is normalised to a `0 0 w h` viewBox with any transform baked into
    the path data, so placing it needs nothing but a translate and a uniform
    scale. The aspect ratio is read from the file rather than hard-coded beside
    it, which is what keeps a re-trace from silently mis-placing the drawing.
    """
    if not path.is_file():
        return None
    src = path.read_text()
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src)
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S)
    if not box or not inner:
        return None
    return inner.group(1), float(box.group(1)), float(box.group(2))


def emblem_art(name: str) -> tuple[str, float, float] | None:
    """One emblem's markup and viewBox size, or None if we don't have it.

    Generated from `frontend/src/lib/emblems.ts` by `npm run emblem:art` — the
    drawings are curated there, and the API image cannot read anything under
    `frontend/`. `emblemArt.test.ts` fails if the committed copies drift.

    Missing is not fatal here, unlike the lockup below: a plate without its
    emblem is the plate we shipped until now.
    """
    return _read_art(_EMBLEM_DIR / f"{name}.svg")


def write_og_twin(artwork, dest) -> None:
    """Rasterise ``artwork`` into the 600x800 og:image twin at ``dest``.

    og:image must be raster — WhatsApp, Facebook and X all refuse an SVG
    preview — so ``books/[slug]/+page.svelte`` falls back to
    ``/covers/<slug>.png`` whenever a book's cover cannot stand in for itself.
    Both tiers that wear a wordless ground arm that fallback, so both need a
    twin, and the two scripts that hand a row such a ground
    (``localize_covers``, ``build_derived_grounds``) call this rather than each
    growing a copy. Neither decides WHETHER to write — that is the caller's, and
    on the derived tier one of those paths is a hand-made cover.

    Palettised deliberately. A truecolour PNG of these frames runs 250-400 KB
    each; at feed size 256 colours is indistinguishable and costs a third of
    that.

    Pillow is imported here, not at module scope, for the reason
    ``palette_from_artwork`` is: the API image ships without it and must still
    be able to import this module for ``build_ground``.
    """
    from PIL import Image

    im = Image.open(artwork).convert("RGB")
    w, h = im.size
    tw, th = (w, w * 4 // 3) if w * 4 // 3 <= h else (h * 3 // 4, h)
    im = im.crop(
        ((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th)
    ).resize((W, H), Image.LANCZOS)
    im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(
        dest, "PNG", optimize=True
    )


def palette_from_artwork(path) -> str:
    """The plate colour for a translated edition, taken from the ENGLISH
    edition's artwork.

    A book whose designed cover is a dark magnolia photograph should not have
    its Swahili edition come out in the default indigo — the two are the same
    book, and the shelf should say so. This picks one colour out of the artwork
    and hands it to ``build_ground``.

    Quantised, not averaged: the mean of a sunset and a silhouette is mud. Of
    the eight quantised buckets it prefers one that is both common and actually
    coloured, ignoring near-black and near-white, which carry no hue to inherit.

    The clamps are not cosmetic. ``build_ground`` darkens the colour to 55% down a
    diagonal gradient AND lays a vignette over that, so a colour sampled at the
    artwork's own lightness lands as near-black on the finished plate — the
    first pass returned five visibly different hex values that all rendered as
    the same dark slab. The floors are what let the hue survive the treatment.

    Pillow is a dev-group dependency: this runs on a developer's machine as a
    curation step, and the committed SVGs are what production serves. Imported
    inside the function so the API image, which has no Pillow, can still import
    this module for ``build_ground``.
    """
    import colorsys

    from PIL import Image

    im = Image.open(path).convert("RGB").resize((80, 107), Image.LANCZOS)
    quantised = im.quantize(colors=8, method=Image.MEDIANCUT)
    palette = quantised.getpalette()
    best, best_score = (59, 91, 219), -1.0
    for count, index in sorted(quantised.getcolors(), reverse=True):
        rgb = tuple(palette[index * 3 : index * 3 + 3])
        _, lightness, saturation = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
        usable = 0.12 < lightness < 0.62
        score = count * (0.35 + saturation) * (1.0 if usable else 0.35)
        if score > best_score:
            best, best_score = rgb, score

    hue, lightness, saturation = colorsys.rgb_to_hls(*[c / 255 for c in best])
    lightness = min(max(lightness, 0.30), 0.46)
    saturation = min(max(saturation, 0.30), 0.72)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    # Floored on the way out, not left for the drawer. The lightness ceiling
    # above cannot do this job: what a plate needs to carry white type depends on
    # its HUE — a yellow has to sit at L<=0.29 to clear 4.5:1 where a blue clears
    # it at 0.66 — so a single ceiling tight enough for the yellows would crush
    # every blue far darker than it needs. Four of the six colours that failed AA
    # in the library were minted right here.
    return ink_safe(_hex(round(c * 255) for c in (r, g, b)))


def _emblem_mark(emblem: str | None) -> str:
    """The emblem, drawn into its reserved band.

    Centred in that band both ways, and scaled to fit whichever of the band's
    two dimensions binds — the emblems are all square today, but the aspect is
    read from the file rather than assumed, which is what keeps a re-trace from
    silently mis-placing the drawing.

    Missing is not fatal: a book in no topic, or an emblem the API image does
    not carry, gets a plate without one. `BookCover` reserves the band either
    way, so the two grounds still line up on a shelf.
    """
    art = emblem_art(emblem) if emblem else None
    if art is None:
        return ""
    inner, vw, vh = art
    emblem_w = min(_EMBLEM_W, _EMBLEM_W * vw / vh)
    emblem_h = emblem_w * vh / vw
    y = (_EMBLEM_TOP + _EMBLEM_BOTTOM - emblem_h) / 2
    return (
        f'<g transform="translate({(W - emblem_w) / 2:.0f} {y:.0f}) '
        f'scale({emblem_w / vw:.5f})">{inner}</g>'
    )


# ── The material ───────────────────────────────────────────────────────────
# A plate used to be a flat gradient, and read like one: a coloured rectangle
# where the other two tiers are a photograph and a painting. These give it a
# surface — the ribbing of a bound cloth — so a generated cover looks like a
# made object rather than a fallback.
#
# DARKENING ONLY, AND THAT IS A CONSTRAINT RATHER THAN A TASTE. `ink_safe`
# promises white type at `_AUTHOR_Y` clears `AUTHOR_MIN_CONTRAST` against this
# ground, and it computes that from the flat colour, which is the only thing it
# can see. A material that LIGHTENS any pixel breaks the promise for that pixel,
# and breaks it exactly where there is no headroom — on a plate `ink_safe` has
# already floored to 4.5:1. Measured on the library's floored colours, with a
# symmetric `mix-blend-mode: overlay` grain:
#
#     flat                  worst pixel 4.58   AA pass
#     overlay, faintest     worst pixel 4.12   AA FAIL
#     overlay, mid          worst pixel 3.85   AA FAIL
#
# Overlay is not luminance-neutral on a dark backdrop — it lightens net — so
# every symmetric grain failed at every strength tried. Black at a low alpha
# cannot fail that way: white ink on a darker ground is higher contrast, never
# lower. So the material is black, and the contrast model stays a conservative
# bound on what actually ships.
#
# A PATTERN RATHER THAN `feTurbulence`, which is where this landed after
# measuring the noise version that came first. Laid ribbing is periodic in
# life, and periodic is worth a great deal here:
#
#   * SIZE. Noise is close to incompressible, and `generate-cover-og.mjs`
#     PALETTISES every share card — a step whose own comment assumes a plate is
#     mostly one colour. Measured on a rendered plate, palettised: turbulence
#     2.00x the flat card, this pattern 1.16x. Across the fifteen twins that is
#     the difference between +1.4 MB and +0.25 MB of shared-link weight.
#   * AGREEMENT BETWEEN RENDERERS. `feTurbulence`'s PRNG is specified, but the
#     filter resolution and colour-space round trip are not: Chromium and resvg
#     came out a little apart on the same plate. A pattern of rectangles has
#     nothing to disagree about, so the committed twins stop being a noise field
#     that re-diffs wholesale on a browser bump.
#   * SMALL SIZES. Noise is point-sampled rather than area-averaged, so it stays
#     speckle at a 48px fan instead of resolving into anything.
#
# What it gives up is a per-book weave, and that is the right trade: one house
# binding across the generated tier reads as a series, and a book is already
# told apart by its colour, its emblem and its era's ornament.
#
# `PlateMaterialTests` is this argument as a gate.
_GRAIN_ALPHA = 0.11
# One line every four units, a unit and a half wide. Checked at 300, 180, 90
# and 48px for the moire a regular pattern can throw when it is scaled: none at
# this period, where a finer one (every two units) averaged away into a flat
# darkening and stopped being a texture at all.
_GRAIN_PERIOD = 4
_GRAIN_RIB = 1.5


def _grain() -> tuple[str, str]:
    """The material layer for every plate: `(defs, rect)`.

    Takes nothing, and that is the point twice over. `build_ground`'s signature
    stays `(colour, emblem)` — a ground is not allowed to know its slug — and
    with no seed there is nothing per-book to drift, so a regenerated plate is
    byte-identical, which a committed file needs.
    """
    defs = (
        f'<pattern id="grain" width="{_GRAIN_PERIOD}" height="{_GRAIN_PERIOD}"'
        f' patternUnits="userSpaceOnUse">'
        # Black, and nothing but black: the tile's remaining area is left
        # transparent rather than painted, so the material can only ever
        # subtract light. This is the whole of the argument above.
        f'<rect width="{_GRAIN_RIB}" height="{_GRAIN_PERIOD}"'
        f' fill="black" opacity="{_GRAIN_ALPHA}"/>'
        f"</pattern>"
    )
    # THIS RECT MUST NEVER BE ABLE TO PAINT ITSELF. SVG's initial fill is
    # BLACK and it covers the whole plate, so a refactor that drops the `fill`
    # here ships every generated cover in the library as a solid black
    # rectangle — measured, not feared: (0, 0, 0) against the plate's
    # (100, 32, 52). And it would ship GREEN, because the contrast gate reads
    # the gradient stop and the no-words gate greps for <text>; neither looks
    # at this element. `PlateMaterialTests` is what actually catches that, by
    # requiring the reference to be here at all.
    # The `none` fallback covers the milder case: a reference that survives but
    # stops resolving. Chromium already degrades that to the flat plate on its
    # own (measured — identical with and without the fallback), so this is
    # belt-and-braces for renderers that do not, and it is free.
    return defs, f'<rect width="{W}" height="{H}" fill="url(#grain) none"/>'


def build_ground(color: str, emblem: str | None = None) -> str:
    """The plate ground for one book. Returns SVG source.

    Takes a colour and an emblem and nothing else — no title, no author, no
    language. That short signature IS the change: a ground carries no words, so
    there is nothing in it to translate and nothing for a font stack to set.
    `BookCover.svelte` draws the type over this.
    """
    # The plate yields to the ink, not the other way round: `ink_safe` returns
    # the book's own colour untouched unless white type could not sit on it.
    color = ink_safe(color)
    grain_defs, grain_rect = _grain()
    return f"""<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="presentation">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{color}"/>
      <stop offset="1" stop-color="{_darken(color, _GRADIENT_END)}"/>
    </linearGradient>
    <radialGradient id="vig" cx="0.5" cy="0.42" r="0.78">
      <stop offset="0.55" stop-color="#000000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.34"/>
    </radialGradient>
    {grain_defs}
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  {grain_rect}
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  {_emblem_mark(emblem)}
</svg>
"""


# ── Curated art covers ─────────────────────────────────────────────────────
# There is no builder here for those either, and for the same reason there is
# no type in `build_ground` above: a curated cover is a painting
# (`covers/art/<slug>.jpg`, built by `scripts/build_curated_covers`), and
# `BookCover` draws the type over it in HTML.
#
# It used to be this module's `build_art_svg`: the painting as a base64
# background, the house scrim over it, and the type composited on top — one SVG
# per (work, language), because an SVG served through <img> cannot fetch a
# sibling file, so the artwork had to be embedded in every one.
# `waiting-on-god` shipped six copies of one painting.
#
# The two tiers are now one shape — a wordless ground, plus the type the
# browser sets over it — which is what let the plate stop carrying words too.
