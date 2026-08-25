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
import re
from functools import lru_cache
from pathlib import Path

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
    channels = []
    for value in _channels(hex_color):
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


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
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
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
