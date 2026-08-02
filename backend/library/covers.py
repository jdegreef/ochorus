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


# The Ochorus mark — the same open-book-and-quill as BrandMark.svelte, inlined
# because an <img>-loaded SVG cannot reference another file.
_MARK = (
    '<g transform="translate(263 690) scale(1.6)" fill="none" stroke="#ffffff" '
    'stroke-opacity="0.75" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12.4 13.6C11 8.9 8.2 5.5 4 3.4c4.7-.5 8.2 1.3 10.4 5.6"/>'
    '<path d="M12.4 13.6l-.4 2.6"/>'
    '<path d="M3 19.6c3-.8 6-.6 9 .8 3-1.4 6-1.6 9-.8"/>'
    '<path d="M3 19.6v-5c2-.5 4-.5 6-.1"/>'
    '<path d="M21 19.6v-5c-2-.5-4-.5-6 0"/>'
    '<path d="M12 16.2v4.2"/>'
    "</g>"
)


def build_svg(
    title: str,
    subtitle: str,
    author: str,
    color: str,
    language: str = "en",
) -> str:
    """The cover for one (book, language). Returns SVG source."""
    color = color or "#3b5bdb"
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
  <rect x="26" y="26" width="{W - 52}" height="{H - 52}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="1.5"/>
  <text x="{W / 2:.0f}" y="112" text-anchor="middle" fill="#ffffff" fill-opacity="0.86" font-family="{family}" font-size="{round(23 * scale)}" letter-spacing="4"{dir_attr}>{author_txt}</text>
  <text text-anchor="middle" fill="#ffffff" font-family="{family}" font-weight="600" font-size="{size}"{dir_attr}>{tspans}</text>
  <line x1="{W / 2 - 38:.0f}" y1="{rule_y:.0f}" x2="{W / 2 + 38:.0f}" y2="{rule_y:.0f}" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5"/>
  {sub}
{_MARK}
  <text x="{W / 2:.0f}" y="754" text-anchor="middle" fill="#ffffff" fill-opacity="0.7" font-family="{FONT_DEFAULT}" font-size="19" letter-spacing="6">OCHORUS</text>
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
  <rect x="26" y="26" width="{W - 52}" height="{H - 52}" fill="none" stroke="#ffffff" stroke-opacity="0.30" stroke-width="1.5"/>
  <text x="{W / 2:.0f}" y="112" text-anchor="middle" fill="#ffffff" fill-opacity="0.92" font-family="{family}" font-size="{round(23 * scale)}" letter-spacing="4"{dir_attr}>{html.escape(author.upper())}</text>
  <text text-anchor="middle" fill="#ffffff" font-family="{family}" font-weight="600" font-size="{size}"{dir_attr}>{tspans}</text>
  <line x1="{W / 2 - 38:.0f}" y1="{rule_y:.0f}" x2="{W / 2 + 38:.0f}" y2="{rule_y:.0f}" stroke="#ffffff" stroke-opacity="0.7" stroke-width="1.5"/>
  {sub}
{_MARK}
  <text x="{W / 2:.0f}" y="754" text-anchor="middle" fill="#ffffff" fill-opacity="0.78" font-family="{FONT_DEFAULT}" font-size="19" letter-spacing="6">OCHORUS</text>
</svg>
"""
