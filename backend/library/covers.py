"""The house-style generated book cover.

A book without artwork gets a typographic cover built from its own title,
author and accent colour. This module owns the drawing; the
``generate_covers`` command owns writing the files and updating rows.

WHY IT LOOKS LIKE THIS
Ochorus's designed covers (the-inner-chamber, godliness) already establish a
house style: a hairline frame, the AUTHOR at the top, the title centred in a
serif, and the Ochorus mark at the foot. The first generator inverted that —
"OCHORUS" at the top and the author at the foot — so a generated cover read as
a different species next to a designed one, on the same shelf. Matching the
layout is most of what makes the two tiers cohere, and it costs nothing.

PER LANGUAGE
Covers are generated per ``(slug, language)`` row, from THAT row's translated
title. The old generator wrote one ``<slug>.svg`` while looping over every
language row, so the last row processed silently overwrote the rest and every
locale ended up showing whichever language won — in practice English. A Spanish
reader saw "All of Grace" over a card reading "Todo por Gracia".

FONTS
The SVG is served through ``<img>``, which does NOT inherit the page's
webfonts, so this can only name fonts the device already has. Georgia is the
closest widely-installed serif to Fraunces' warmth, and the per-script stacks
below give Arabic and Devanagari a serif rather than whatever the fallback
would pick. Real Fraunces would mean embedding a subset per cover; not worth
the bytes for a fallback surface.
"""

from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path

# A plain module, imported for exactly that reason — see its docstring.
from library.topic_seed import TOPICS

# The canvas. 3:4, matching BookCover's reserved box so nothing shifts.
W, H = 600, 800

# The hairline frame's inset, and the baseline the author line sits on. Both are
# drawn from here, and both are read by the contrast model below.
_FRAME_INSET = 26
_AUTHOR_Y = 112

# Per-script serif stacks. Georgia leads the Latin one because it is the
# nearest ubiquitous face to the brand serif; the others name the common
# system serifs for their script so Arabic and Hindi covers aren't rendered in
# a default sans (or, worse, in tofu).
FONTS: dict[str, str] = {
    "ar": "'Amiri', 'Scheherazade New', 'Traditional Arabic', 'Geeza Pro', 'Noto Naskh Arabic', serif",
    "hi": "'Noto Serif Devanagari', 'Kohinoor Devanagari', 'Nirmala UI', 'Mangal', serif",
}
FONT_DEFAULT = "Georgia, 'Times New Roman', serif"

# Scripts that read right-to-left need it declared on each text run, or the
# punctuation lands on the wrong end.
RTL = {"ar"}

# Arabic and Devanagari carry more detail per glyph than Latin and read small
# at the same point size, so they get a nudge. Checked against the Latin covers
# at thumbnail width, which is where most of these are actually seen.
SCRIPT_SCALE: dict[str, float] = {"ar": 1.12, "hi": 1.10}


def font_for(language: str) -> str:
    return FONTS.get(language, FONT_DEFAULT)


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


# The ink is white at these opacities (see build_svg). The author line is set at
# 23px, which is NOT "large text" under WCAG 1.4.3, so AA asks 4.5:1 of it; the
# title runs 34-60px and asks 3:1, which every colour that satisfies the author
# line clears with room to spare (the worst measured is 5.08 against a 3.0 bar).
# So the author line is the binding constraint, and the only one checked.
AUTHOR_INK_OPACITY = 0.86
AUTHOR_MIN_CONTRAST = 4.5

# The plate gradient's far stop, as a fraction of the base colour. `build_svg`
# paints from this same constant, so the contrast model cannot drift from the
# artwork it measures.
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
    the artwork that ships. `build_svg` still calls this, but on floored data it
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


def _wrap(text: str, max_chars: int) -> list[str]:
    """Greedy word wrap. A single word longer than the budget keeps its own
    line rather than being broken — a hyphenated split reads worse than a
    slightly wide line, and the font size step below usually absorbs it."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def _title_metrics(title: str) -> tuple[int, int]:
    """Font size and wrap budget, stepped by title length so long titles still
    fit the plate without spilling into the author line or the mark."""
    n = len(title)
    if n <= 20:
        return 60, 12
    if n <= 34:
        return 50, 15
    if n <= 52:
        return 42, 18
    return 34, 22


# The Ochorus logo at the foot, read from the real artwork rather than redrawn.
#
# This used to be a hand-drawn open-book-and-quill copied from BrandMark.svelte
# — and it had the quill pointing the wrong way. Three independent hand-copies
# of a logo is how that happens, so every one of them now reads these files.
# This is the canonical location: the api's Docker image has rootDir `backend/`,
# so covers.py cannot read anything under `frontend/`; the frontend mirrors it
# and `brandAssets.test.ts` fails if the copies drift.
#
# Inlined (not <img href>) because an <img>-loaded SVG cannot reference another
# file. The lockup already contains the "Ochorus" wordmark, which is why the
# letter-spaced OCHORUS that used to sit under the mark is gone — the printed
# ministry covers carry the lockup alone.
_BRAND_DIR = Path(__file__).resolve().parent / "data" / "brand"
_EMBLEM_DIR = Path(__file__).resolve().parent / "data" / "emblems"

#: The emblem sits in the band between the last line of type and the mark, at
#: most 20% of the plate's width. Checked at 300px and at thumbnail size, which
#: is where covers are mostly seen: smaller and it is a smudge, larger and it
#: crowds the lockup into looking like a second device.
#:
#: FITTED, not placed at a fixed offset. A plate's type runs to a different
#: depth on every book — a four-line title pushes the rule 52 units lower than a
#: one-line title, and a two-line subtitle another 30 below that — so a constant
#: offset put the emblem 16px into the lockup on the long titles and straight
#: through the subtitle on `a-plain-account-christian-perfection`. Below
#: `_EMBLEM_MIN` there is no room worth taking, and the plate goes without.
_EMBLEM_W = 120
_EMBLEM_MIN = 64
_EMBLEM_GAP = 22


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


def _read_lockup() -> tuple[str, float, float]:
    """The lockup's inner markup and its viewBox size.

    Loud where `emblem_art` is quiet: the mark is on every generated cover, so a
    lockup this module cannot read is a broken build, not a cover without one.
    """
    art = _read_art(_BRAND_DIR / "ochorus-lockup.svg")
    if art is None:
        raise RuntimeError("the brand lockup is missing or not a 0 0 w h viewBox SVG")
    return art


_LOCKUP, _LOCKUP_VW, _LOCKUP_VH = _read_lockup()

# Centred at the foot, matching where the printed covers put it. Positioned off
# the FRAME, not the canvas: placed by canvas coordinates the logo crossed the
# hairline.
# Also echoed, as proportions, by the client-side plate in BookCover.svelte —
# the frame inset, this width and the divider, over W. That is the whole of the
# coupling: the plate copies proportions deliberately and algorithms never
# (STYLE_GUIDE §5), so moving one of these is a look-there-too, not a break.
_LOGO_W = 136
_LOGO_H = _LOGO_W * _LOCKUP_VH / _LOCKUP_VW
#: The top edge of the lockup — where the plate's type has to stop.
_MARK_TOP = H - _FRAME_INSET - 16 - _LOGO_H

_MARK = (
    f'<g transform="translate({(W - _LOGO_W) // 2} {round(_MARK_TOP)}) scale({_LOGO_W / _LOCKUP_VW:.5f})" '
    f'fill="#ffffff" fill-opacity="0.82">{_LOCKUP}</g>'
)


def palette_from_artwork(path) -> str:
    """The plate colour for a translated edition, taken from the ENGLISH
    edition's artwork.

    A book whose designed cover is a dark magnolia photograph should not have
    its Swahili edition come out in the default indigo — the two are the same
    book, and the shelf should say so. This picks one colour out of the artwork
    and hands it to ``build_svg``.

    Quantised, not averaged: the mean of a sunset and a silhouette is mud. Of
    the eight quantised buckets it prefers one that is both common and actually
    coloured, ignoring near-black and near-white, which carry no hue to inherit.

    The clamps are not cosmetic. ``build_svg`` darkens the colour to 55% down a
    diagonal gradient AND lays a vignette over that, so a colour sampled at the
    artwork's own lightness lands as near-black on the finished plate — the
    first pass returned five visibly different hex values that all rendered as
    the same dark slab. The floors are what let the hue survive the treatment.

    Pillow is a dev-group dependency: this runs on a developer's machine as a
    curation step, and the committed SVGs are what production serves. Imported
    inside the function so the API image, which has no Pillow, can still import
    this module for ``build_svg``.
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


def _emblem_mark(emblem: str | None, content_bottom: float) -> str:
    """The emblem, fitted into the band between the type and the lockup.

    Centred in that band, and only as large as the band leaves room for. The
    gap is a margin on the SIZE, not on the position: it keeps the drawing off
    the last line of type and off the mark, and what is left over is shared
    equally above and below.
    """
    art = emblem_art(emblem) if emblem else None
    if art is None:
        return ""
    inner, vw, vh = art
    # NOT `size`: that is the title's font size in the caller. Shadowing it
    # there set every regenerated title to the emblem's width in points —
    # 97.87px on `a-call-to-the-unconverted` — and the geometry checks all
    # passed, because the emblem itself was placed correctly.
    band = _MARK_TOP - content_bottom - 2 * _EMBLEM_GAP
    emblem_w = min(_EMBLEM_W, band * vw / vh)
    if emblem_w < _EMBLEM_MIN:
        return ""
    y = (content_bottom + _MARK_TOP - emblem_w * vh / vw) / 2
    return (
        f'<g transform="translate({(W - emblem_w) / 2:.0f} {y:.0f}) '
        f'scale({emblem_w / vw:.5f})">{inner}</g>'
    )


def build_svg(
    title: str,
    subtitle: str,
    author: str,
    color: str,
    language: str = "en",
    emblem: str | None = None,
) -> str:
    """The cover for one (book, language). Returns SVG source."""
    # The plate yields to the ink, not the other way round: `ink_safe` returns
    # the book's own colour untouched unless white type could not sit on it.
    color = ink_safe(color)
    family = font_for(language)
    dir_attr = ' direction="rtl"' if language in RTL else ""

    size, budget = _title_metrics(title)
    scale = SCRIPT_SCALE.get(language, 1.0)
    size = round(size * scale)
    line_h = size + 10
    lines = _wrap(title, budget)

    # Optical centre of the space BETWEEN the author line and the mark, not of
    # the whole plate. A designed cover has a photograph filling that region; a
    # typographic one has nothing, so pinning the title as high as the designed
    # covers do left roughly a third of the cover visibly empty.
    block_mid = 410
    top = block_mid - (len(lines) - 1) * line_h / 2
    tspans = "".join(
        f'<tspan x="{W / 2:.0f}" y="{top + i * line_h:.0f}">{html.escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    rule_y = top + (len(lines) - 1) * line_h + 52

    sub = ""
    # Where the type stops — the rule, or the last line of subtitle under it.
    content_bottom = rule_y
    if subtitle:
        sub_lines = _wrap(subtitle, 34)[:2]
        content_bottom = rule_y + 42 + (len(sub_lines) - 1) * 30
        sub = "".join(
            f'<text x="{W / 2:.0f}" y="{rule_y + 42 + i * 30:.0f}" text-anchor="middle" '
            f'fill="#ffffff" fill-opacity="0.82" font-family="{family}" font-style="italic" '
            f'font-size="24"{dir_attr}>{html.escape(ln)}</text>'
            for i, ln in enumerate(sub_lines)
        )

    # Author sits at the TOP, letterspaced caps — the house style. Long bylines
    # ("Ochorus Originals") stay on one line at this size.
    author_txt = html.escape(author.upper())

    # The emblem of the topic this book belongs to, between the rule and the
    # mark. 105 of the library's 153 editions wear a generated plate, and with
    # nothing on it but a title a grid of them reads as coloured slabs — the
    # colour varies per book but the COMPOSITION doesn't, so nothing tells one
    # from another at a glance. The emblem is a second variable, and it is the
    # book's own: the drawing its topic already wears on the topics shelf.
    emblem_mark = _emblem_mark(emblem, content_bottom)

    return f"""<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(title)}">
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
  <rect x="{_FRAME_INSET}" y="{_FRAME_INSET}" width="{W - 2 * _FRAME_INSET}" height="{H - 2 * _FRAME_INSET}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="1.5"/>
  <text x="{W / 2:.0f}" y="{_AUTHOR_Y}" text-anchor="middle" fill="#ffffff" fill-opacity="{AUTHOR_INK_OPACITY}" font-family="{family}" font-size="{round(23 * scale)}" letter-spacing="4"{dir_attr}>{author_txt}</text>
  <text text-anchor="middle" fill="#ffffff" font-family="{family}" font-weight="600" font-size="{size}"{dir_attr}>{tspans}</text>
  <line x1="{W / 2 - 38:.0f}" y1="{rule_y:.0f}" x2="{W / 2 + 38:.0f}" y2="{rule_y:.0f}" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5"/>
  {sub}
  {emblem_mark}
{_MARK}
</svg>
"""


# ── Curated art covers ─────────────────────────────────────────────────────
# There is no builder here any more. A curated cover used to be this module's
# `build_art_svg`: the painting as a base64 background, the house scrim over it,
# and the type composited on top — one SVG per (work, language), because an SVG
# served through <img> cannot fetch a sibling file, so the artwork had to be
# embedded in every one. `waiting-on-god` shipped six copies of one painting.
#
# The painting is now a plain image (`covers/art/<slug>.jpg`, built by
# `scripts/build_cover_assets.py`) and `BookCover` draws the type over it in
# HTML — which also means the title is set in the brand serif and shaped for its
# own script, neither of which an <img>-served SVG can do. One file, one
# download, every language.
