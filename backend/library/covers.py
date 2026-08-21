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
import re
from pathlib import Path

# The canvas. 3:4, matching BookCover's reserved box so nothing shifts.
W, H = 600, 800

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

# The plate gradient's far stop, as a fraction of the base colour, and how far
# along that gradient the author line sits. Both are read back by
# `author_plate_color`; keep them in step with the `<linearGradient id="bg">`
# and the y=112 byline in `build_svg`.
_GRADIENT_END = 0.55
_AUTHOR_GRADIENT_T = 0.28


def _channels(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or "#3b5bdb").lstrip("#")
    if len(h) != 6:
        h = "3b5bdb"
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.x relative luminance of a colour."""
    channels = []
    for value in _channels(hex_color):
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def author_plate_color(hex_color: str) -> str:
    """The colour actually under the author line, not the plate's top stop.

    The byline sits at y=112 on a 600x800 plate painted with a gradient running
    to ``(0.35, 1)``, so the point projects 28% of the way along it and the
    colour there is already a little darker than the stop. The vignette is fully
    transparent that high (it starts at 0.55 of a 0.78 radius centred at 0.42),
    so the gradient is the whole story. Modelling it matters: taking the top stop
    instead reads ~0.6 of a ratio point low, which would darken plates that are
    in fact legible.
    """
    return _darken(hex_color, 1 - (1 - _GRADIENT_END) * _AUTHOR_GRADIENT_T)


def author_ink_contrast(hex_color: str) -> float:
    """Contrast of the author line against the plate it sits on.

    The ink is white at ``AUTHOR_INK_OPACITY``, so what the reader sees is white
    composited over the plate, not white — a third of a ratio point, and the
    difference between passing and failing on the paler plates.
    """
    behind = author_plate_color(hex_color)
    plate = _channels(behind)
    ink = "#" + "".join(
        f"{round(AUTHOR_INK_OPACITY * 255 + (1 - AUTHOR_INK_OPACITY) * c):02x}" for c in plate
    )
    light, dark = relative_luminance(ink), relative_luminance(behind)
    return (light + 0.05) / (dark + 0.05)


def ink_safe(hex_color: str) -> str:
    """The plate colour, darkened just enough to carry white ink at AA.

    Ochorus' covers are white type on a coloured plate, always — the frame, the
    rules, the byline and the lockup are all white, and a per-cover decision to
    flip to dark ink would break the one thing the generated and designed tiers
    have in common. So the colour yields, not the ink.

    16 committed covers failed AA on the author line — `the-unselfishness-of-god`
    worst at 3.16:1 — because a plate colour is DATA (a hand-picked hex, or one
    sampled from the English artwork) and nothing between the two ever asked
    whether white could sit on it. Colours that already pass are returned
    untouched, so this darkens 5 of the library's 46 plate colours and leaves the
    committed artwork of the rest byte-identical.

    Scaling channels rather than moving through HLS keeps the hue and the
    saturation exactly where the curator put them: a green plate comes back a
    deeper green, never a grey or a different green.
    """
    # Normalised first, so a blank or malformed value comes back as the default
    # rather than as itself with a "#" bolted on.
    hex_color = "#" + "".join(f"{c:02x}" for c in _channels(hex_color))
    if author_ink_contrast(hex_color) >= AUTHOR_MIN_CONTRAST:
        return hex_color
    # Integer steps, not a float accumulator: the TypeScript mirror walks the
    # same ladder, and two languages drifting a step apart would hand one book
    # two plates.
    for step in range(99, 0, -1):
        candidate = _darken(hex_color, step / 100)
        if author_ink_contrast(candidate) >= AUTHOR_MIN_CONTRAST:
            return candidate
    return "#000000"  # unreachable: black passes at 21:1


def _darken(hex_color: str, factor: float = 0.55) -> str:
    h = (hex_color or "#3b5bdb").lstrip("#")
    if len(h) != 6:
        h = "3b5bdb"
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{max(0, int(c * factor)):02x}" for c in (r, g, b))


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


def _read_lockup() -> tuple[str, float, float]:
    """The lockup's inner markup and its viewBox size.

    The committed artwork is normalised to a `0 0 w h` viewBox with the
    transform baked into the path data, so placing it needs nothing but a
    translate and a uniform scale — and the aspect ratio is read from the file
    rather than hard-coded beside it, which is what keeps a re-trace from
    silently mis-placing the logo.
    """
    src = (_BRAND_DIR / "ochorus-lockup.svg").read_text()
    vw, vh = (float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src).groups())
    return re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1), vw, vh


_LOCKUP, _LOCKUP_VW, _LOCKUP_VH = _read_lockup()

# Centred at the foot, matching where the printed covers put it. Positioned off
# the FRAME, not the canvas: placed by canvas coordinates the logo crossed the
# hairline.
_FRAME_INSET = 26
_LOGO_W = 136
_LOGO_H = _LOGO_W * _LOCKUP_VH / _LOCKUP_VW
_MARK = (
    f'<g transform="translate({(W - _LOGO_W) // 2} '
    f'{round(H - _FRAME_INSET - 16 - _LOGO_H)}) scale({_LOGO_W / _LOCKUP_VW:.5f})" '
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
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def build_svg(
    title: str,
    subtitle: str,
    author: str,
    color: str,
    language: str = "en",
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
    if subtitle:
        sub_lines = _wrap(subtitle, 34)[:2]
        sub = "".join(
            f'<text x="{W / 2:.0f}" y="{rule_y + 42 + i * 30:.0f}" text-anchor="middle" '
            f'fill="#ffffff" fill-opacity="0.82" font-family="{family}" font-style="italic" '
            f'font-size="24"{dir_attr}>{html.escape(ln)}</text>'
            for i, ln in enumerate(sub_lines)
        )

    # Author sits at the TOP, letterspaced caps — the house style. Long bylines
    # ("Ochorus Originals") stay on one line at this size.
    author_txt = html.escape(author.upper())

    return f"""<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{color}"/>
      <stop offset="1" stop-color="{_darken(color)}"/>
    </linearGradient>
    <radialGradient id="vig" cx="0.5" cy="0.42" r="0.78">
      <stop offset="0.55" stop-color="#000000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.34"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  <rect x="{_FRAME_INSET}" y="{_FRAME_INSET}" width="{W - 2 * _FRAME_INSET}" height="{H - 2 * _FRAME_INSET}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="1.5"/>
  <text x="{W / 2:.0f}" y="112" text-anchor="middle" fill="#ffffff" fill-opacity="0.86" font-family="{family}" font-size="{round(23 * scale)}" letter-spacing="4"{dir_attr}>{author_txt}</text>
  <text text-anchor="middle" fill="#ffffff" font-family="{family}" font-weight="600" font-size="{size}"{dir_attr}>{tspans}</text>
  <line x1="{W / 2 - 38:.0f}" y1="{rule_y:.0f}" x2="{W / 2 + 38:.0f}" y2="{rule_y:.0f}" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5"/>
  {sub}
{_MARK}
</svg>
"""


# ── Curated art covers ─────────────────────────────────────────────────────
# Same type treatment as the generated plate, over a photograph or painting
# instead of a gradient. The art layer is language-neutral and the type is
# drawn on top, so one image serves every locale with its own title.
#
# The image is embedded as a data URI because an SVG loaded through <img> runs
# in secure static mode and cannot fetch an external file — a <image href> to a
# sibling path renders blank. Costs ~33% over the raw JPEG; at 600x800/q72
# that lands near the existing designed covers (godliness.jpg is 19 KB,
# baptism.png 281 KB), so it is not the heavy option on this shelf.

def build_art_svg(
    title: str,
    subtitle: str,
    author: str,
    jpeg_b64: str,
    language: str = "en",
    credit: str = "",
) -> str:
    """A cover whose background is real artwork. `jpeg_b64` is a bare base64
    JPEG (no data: prefix), already cropped to 3:4."""
    family = font_for(language)
    dir_attr = ' direction="rtl"' if language in RTL else ""
    scale = SCRIPT_SCALE.get(language, 1.0)

    size, budget = _title_metrics(title)
    size = round(size * scale)
    line_h = size + 10
    lines = _wrap(title, budget)
    block_mid = 410
    top = block_mid - (len(lines) - 1) * line_h / 2
    tspans = "".join(
        f'<tspan x="{W / 2:.0f}" y="{top + i * line_h:.0f}">{html.escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    rule_y = top + (len(lines) - 1) * line_h + 52

    sub = ""
    if subtitle:
        sub = "".join(
            f'<text x="{W / 2:.0f}" y="{rule_y + 42 + i * 30:.0f}" text-anchor="middle" '
            f'fill="#ffffff" fill-opacity="0.86" font-family="{family}" font-style="italic" '
            f'font-size="24"{dir_attr}>{html.escape(ln)}</text>'
            for i, ln in enumerate(_wrap(subtitle, 34)[:2])
        )

    desc = f"<desc>{html.escape(credit)}</desc>" if credit else ""

    # Two scrims, not one flat wash: a global darkener so white type holds
    # anywhere, plus top/bottom gradients under the author line and the mark,
    # which is where the art is most likely to be pale.
    return f"""<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(title)}">
  {desc}
  <defs>
    <linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000000" stop-opacity="0.62"/>
      <stop offset="0.30" stop-color="#000000" stop-opacity="0.34"/>
      <stop offset="0.70" stop-color="#000000" stop-opacity="0.40"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.70"/>
    </linearGradient>
  </defs>
  <image href="data:image/jpeg;base64,{jpeg_b64}" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>
  <rect width="{W}" height="{H}" fill="#1a1410" fill-opacity="0.26"/>
  <rect width="{W}" height="{H}" fill="url(#scrim)"/>
  <rect x="{_FRAME_INSET}" y="{_FRAME_INSET}" width="{W - 2 * _FRAME_INSET}" height="{H - 2 * _FRAME_INSET}" fill="none" stroke="#ffffff" stroke-opacity="0.30" stroke-width="1.5"/>
  <text x="{W / 2:.0f}" y="112" text-anchor="middle" fill="#ffffff" fill-opacity="0.92" font-family="{family}" font-size="{round(23 * scale)}" letter-spacing="4"{dir_attr}>{html.escape(author.upper())}</text>
  <text text-anchor="middle" fill="#ffffff" font-family="{family}" font-weight="600" font-size="{size}"{dir_attr}>{tspans}</text>
  <line x1="{W / 2 - 38:.0f}" y1="{rule_y:.0f}" x2="{W / 2 + 38:.0f}" y2="{rule_y:.0f}" stroke="#ffffff" stroke-opacity="0.7" stroke-width="1.5"/>
  {sub}
{_MARK}
</svg>
"""
