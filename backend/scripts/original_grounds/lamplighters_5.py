#!/usr/bin/env python3
"""Wordless cover ground for *The Midsummer Flame* (Lamplighters of Gloamhaven, Book 5).

Midsummer morning on the moor above Harrowgate.  A small company stands along a
heather ridge low on the cover, ink against a sky just beginning to warm, and a
small flame rests above the head of each one; at the left end Wren holds the lamp
out in front of her.  Long faint streaks of warm wind run in off the hills behind.
The sky above stays deep and cool for the white title; the subject sits wholly
below the subtitle row.

Emits midsummer_cover.html (600x800 SVG), renders it at 2x with headless Chrome,
downsamples with Pillow to the-midsummer-flame.jpg, and writes mock.jpg with the
cover pipeline's white-type bands outlined (red) and the subtitle's real
one-line-title row (blue).  Rerun:  CHROME=/path/to/chrome python lamplighters_5.py OUTDIR
"""
import os
import random
import subprocess
import sys

# Output folder: the first argument, else beside this script.
HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H = 600, 800
HORIZON = 600

# Type bands the cover pipeline overlays (x0, y0, x1, y1).
BANDS = {
    "byline": (0, 102, 600, 130),
    "title": (70, 284, 530, 463),
    "subtitle": (70, 519, 530, 543),
    "mark": (232, 664, 368, 747),
}
# Where the subtitle really falls when the title sets on ONE line.
REAL_ROWS = {
    "subtitle@1-line": (70, 493, 530, 517),
}

rnd = random.Random(5)
INK = "#0b0a0b"


def stars():
    """A few last stars, fading out toward the warming horizon."""
    out = []
    for _ in range(22):
        x, y = rnd.uniform(8, 592), rnd.uniform(10, 250)
        if 92 < y < 140:
            continue
        r = rnd.choice([0.5, 0.6, 0.7])
        o = rnd.uniform(0.12, 0.34) * (1 - y / 320)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#e3e8ee" opacity="{o:.2f}"/>')
    return "\n".join(out)


def wind():
    """Long, soft, warm streaks of wind coming in low off the hills, right to left."""
    out = []
    for i in range(9):
        y = rnd.uniform(552, 596)
        x0 = rnd.uniform(140, 420)
        w = rnd.uniform(120, 260)
        bow = rnd.uniform(3, 8)
        o = rnd.uniform(0.10, 0.22)
        out.append(
            f'<path d="M{x0 + w:.0f},{y:.1f} C{x0 + w * 0.6:.0f},{y - bow:.1f} {x0 + w * 0.3:.0f},{y + bow:.1f} {x0:.0f},{y - 1:.1f}" '
            f'stroke="#f3c98a" stroke-width="{rnd.uniform(0.6, 1.2):.1f}" fill="none" opacity="{o:.2f}" stroke-linecap="round"/>'
        )
    return "\n".join(out)


def hills():
    """Far moors: two soft bands of hill under the warm horizon."""
    return f'''
<path d="M0,{HORIZON - 12} C80,{HORIZON - 26} 150,{HORIZON - 30} 230,{HORIZON - 18} C300,{HORIZON - 8} 360,{HORIZON - 30} 440,{HORIZON - 34} C510,{HORIZON - 36} 560,{HORIZON - 22} 600,{HORIZON - 18} L600,700 L0,700 Z" fill="#2a2a33"/>
<path d="M0,{HORIZON + 2} C90,{HORIZON - 8} 170,{HORIZON - 2} 250,{HORIZON + 6} C340,{HORIZON + 14} 430,{HORIZON - 4} 600,{HORIZON + 2} L600,700 L0,700 Z" fill="#1d1c23"/>
'''


def ridge():
    """The near heather ridge the company stands on, rising gently to the left."""
    return f'''
<g filter="url(#ink)" fill="{INK}">
  <path d="M-10,646 C60,640 130,640 210,648 C300,656 380,652 460,646 C520,642 570,644 610,650 L610,810 L-10,810 Z"/>
</g>
<!-- heather tufts along the crest -->
<g filter="url(#ink)" fill="{INK}">{''.join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{5 + x % 4:.0f}" ry="{2.5 + x % 3 * 0.6:.1f}"/>' for x, y in tuft_points())}</g>
'''


def tuft_points():
    pts = []
    x = 6
    while x < 600:
        t = x / 600
        y = 646 - 6 * (1 - t) + 6 * t + (2 if 200 < x < 300 else 0)
        pts.append((x, y))
        x += rnd.uniform(14, 34)
    return pts


def figure(x, base, h, kind):
    """One of the company, ink against the sky: head, shoulders, coat to the ridge."""
    head_r = h * 0.095
    top = base - h
    hy = top + head_r
    sh = hy + head_r * 1.45
    w = h * 0.34
    # a neck, sloping shoulders, arms hanging close, the coat falling a little wider
    n, sy = w * 0.11, sh + h * 0.07
    coat = (f'M{x - n:.1f},{sh - 4:.1f} C{x - n:.1f},{sh:.1f} {x - w * 0.36:.1f},{sh - 1:.1f} {x - w * 0.44:.1f},{sy:.1f} '
            f'C{x - w * 0.52:.1f},{sy + h * 0.12:.1f} {x - w * 0.5:.1f},{base - h * 0.3:.1f} {x - w * 0.46:.1f},{base - h * 0.26:.1f} '
            f'L{x - w * 0.52:.1f},{base} L{x + w * 0.52:.1f},{base} L{x + w * 0.46:.1f},{base - h * 0.26:.1f} '
            f'C{x + w * 0.5:.1f},{base - h * 0.3:.1f} {x + w * 0.52:.1f},{sy + h * 0.12:.1f} {x + w * 0.44:.1f},{sy:.1f} '
            f'C{x + w * 0.36:.1f},{sh - 1:.1f} {x + n:.1f},{sh:.1f} {x + n:.1f},{sh - 4:.1f} Z')
    extra = ""
    if kind == "pole":  # Tobin with Ash's pole, its hook at the top
        extra = (f'<path d="M{x + w * 0.7:.1f},{base} L{x + w * 0.78:.1f},{top - 18:.1f}" stroke="{INK}" stroke-width="2.2" fill="none"/>'
                 f'<path d="M{x + w * 0.78:.1f},{top - 18:.1f} c4,-2 6,2 3,5" stroke="{INK}" stroke-width="1.6" fill="none"/>')
    elif kind == "plaid":  # a Highlander's plaid over one shoulder
        extra = f'<path d="M{x - w * 0.3:.1f},{sh} L{x + w * 0.62:.1f},{base - h * 0.35:.1f} L{x + w * 0.66:.1f},{base - h * 0.25:.1f} Z"/>'
    elif kind == "skirt":
        coat = (f'M{x - w * 0.8:.1f},{base} C{x - w * 0.6:.1f},{sh + h * 0.4:.1f} {x - w * 0.45:.1f},{sh + 3:.1f} '
                f'{x - w * 0.18:.1f},{sh - 1:.1f} L{x + w * 0.18:.1f},{sh - 1:.1f} '
                f'C{x + w * 0.45:.1f},{sh + 3:.1f} {x + w * 0.6:.1f},{sh + h * 0.4:.1f} {x + w * 0.8:.1f},{base} Z')
    return (f'<g filter="url(#ink)" fill="{INK}"><circle cx="{x:.1f}" cy="{hy:.1f}" r="{head_r:.1f}"/>'
            f'<path d="{coat}"/>{extra}</g>'), (x, top)


def flame(x, y, s=1.0):
    """The small flame that rests above each head, with its warm halo."""
    return (f'<circle cx="{x:.1f}" cy="{y - 3 * s:.1f}" r="{16 * s:.1f}" fill="url(#halo)"/>'
            f'<path d="M{x:.1f},{y:.1f} C{x - 3.4 * s:.1f},{y - 2 * s:.1f} {x - 3 * s:.1f},{y - 6.5 * s:.1f} {x:.1f},{y - 11 * s:.1f} '
            f'C{x + 3 * s:.1f},{y - 6.5 * s:.1f} {x + 3.4 * s:.1f},{y - 2 * s:.1f} {x:.1f},{y:.1f} Z" fill="url(#flame)"/>'
            f'<path d="M{x:.1f},{y - 1.2 * s:.1f} C{x - 1.3 * s:.1f},{y - 2.5 * s:.1f} {x - 1 * s:.1f},{y - 4.6 * s:.1f} {x:.1f},{y - 6.4 * s:.1f} '
            f'C{x + 1 * s:.1f},{y - 4.6 * s:.1f} {x + 1.3 * s:.1f},{y - 2.5 * s:.1f} {x:.1f},{y - 1.2 * s:.1f} Z" fill="#fff6d6"/>')


def wren():
    """Wren at the left end of the line, small, holding the lamp out in front of her."""
    x, base = 92, 650
    return f'''
<g filter="url(#ink)" fill="{INK}" stroke="{INK}">
  <path d="M{x - 13},{base} C{x - 15},{base - 20} {x - 12},{base - 38} {x - 4},{base - 44} L{x + 6},{base - 44} C{x + 13},{base - 38} {x + 15},{base - 20} {x + 13},{base} Z" stroke="none"/>
  <circle cx="{x + 1}" cy="{base - 52}" r="8.5" stroke="none"/>
  <path d="M{x - 8},{base - 54} L{x - 13},{base - 58} L{x - 6},{base - 59} L{x - 8},{base - 65} L{x - 1},{base - 62} L{x + 1},{base - 68} L{x + 4},{base - 62} L{x + 9},{base - 66} L{x + 8},{base - 59} L{x + 13},{base - 57} L{x + 9},{base - 53} Z" stroke="none"/>
  <path d="M{x + 8},{base - 38} C{x + 16},{base - 34} {x + 22},{base - 32} {x + 28},{base - 33}" stroke-width="4.5" stroke-linecap="round" fill="none"/>
  <path d="M{x - 6},{base - 44} C{x - 16},{base - 46} {x - 26},{base - 40} {x - 36},{base - 42}" stroke-width="3" stroke-linecap="round" fill="none"/>
</g>
<path d="M{x + 25},{base - 35} L{x + 27},{base - 32}" stroke="#c0222c" stroke-width="2" stroke-linecap="round"/>
<circle cx="{x + 34}" cy="{base - 30}" r="26" fill="url(#halo)"/>
<g>
  <circle cx="{x + 34}" cy="{base - 41}" r="2" fill="none" stroke="#3a2a14" stroke-width="1"/>
  <path d="M{x + 29},{base - 38} H{x + 39} L{x + 37.5},{base - 35.5} H{x + 30.5} Z" fill="#2a1d0e"/>
  <rect x="{x + 30}" y="{base - 35.5}" width="8" height="9" rx="2.4" fill="url(#chimney)"/>
  <path d="M{x + 28.5},{base - 26.5} H{x + 39.5} L{x + 38},{base - 22} H{x + 30} Z" fill="#7a5320"/>
</g>
'''


def company():
    """The rest of the company along the ridge, each with a flame above the head."""
    people = (
        (156, 650, 58, "plain"),   # Mira
        (206, 652, 70, "pole"),    # Tobin, with Ash's pole
        (268, 653, 84, "plain"),   # Aren, tall
        (330, 652, 66, "skirt"),   # Sister Hale
        (392, 650, 76, "plaid"),   # a Highlander
        (448, 648, 62, "skirt"),
        (498, 647, 72, "plain"),
        (548, 647, 56, "plain"),   # a child
    )
    shapes, flames = [], []
    for x, base, h, kind in people:
        s, (fx, top) = figure(x, base, h, kind)
        shapes.append(s)
        flames.append(flame(fx, top - 6, 0.85 + h / 400))
    # Wren's own flame, above her head
    flames.append(flame(93, 576, 1.0))
    return "\n".join(shapes), "\n".join(flames)


def svg():
    shapes, flames = company()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#121722"/>
    <stop offset="0.45" stop-color="#182030"/>
    <stop offset="0.64" stop-color="#262a38"/>
    <stop offset="0.71" stop-color="#4a3e42"/>
    <stop offset="0.75" stop-color="#8a6648"/>
  </linearGradient>
  <linearGradient id="glow" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#e7a868" stop-opacity="0"/>
    <stop offset="0.6" stop-color="#e7a868" stop-opacity="0.35"/>
    <stop offset="1" stop-color="#f6cf8a" stop-opacity="0.75"/>
  </linearGradient>
  <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff0c8" stop-opacity="0.9"/>
    <stop offset="0.25" stop-color="#f7cf8a" stop-opacity="0.45"/>
    <stop offset="1" stop-color="#e0965a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe7a0" stop-opacity="0.7"/>
    <stop offset="0.35" stop-color="#f2a948" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#e08a2a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#f6a63c"/>
    <stop offset="0.6" stop-color="#ffd36e"/>
    <stop offset="1" stop-color="#ffe9a8"/>
  </linearGradient>
  <linearGradient id="chimney" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff1c2"/>
    <stop offset="1" stop-color="#f2a948"/>
  </linearGradient>
  <filter id="ink" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.35" numOctaves="2" seed="5" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="1.4"/>
  </filter>
  <filter id="blur3"><feGaussianBlur stdDeviation="3"/></filter>
</defs>

<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars()}

<!-- the warming horizon: a band of amber under the hills, and the pale sun just under them, right of centre -->
<rect x="0" y="{HORIZON - 70}" width="{W}" height="70" fill="url(#glow)"/>
<ellipse cx="430" cy="{HORIZON - 26}" rx="120" ry="40" fill="url(#sun)"/>
<g filter="url(#blur3)" opacity="0.9">{wind()}</g>
{hills()}
{ridge()}
{shapes}
{wren()}
{flames}
</svg>'''


def page():
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#121722}} svg{{display:block}}
</style></head><body>{svg()}</body></html>'''


def render():
    from PIL import Image, ImageDraw
    os.makedirs(HERE, exist_ok=True)
    html = os.path.join(HERE, "midsummer_cover.html")
    png = os.path.join(HERE, "midsummer_cover@2x.png")
    jpg = os.path.join(HERE, "the-midsummer-flame.jpg")
    with open(html, "w") as f:
        f.write(page())
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={W},{H}",
                    f"--screenshot={png}", "file://" + html],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(png):
        sys.exit("chrome did not write the screenshot")
    im = Image.open(png).convert("RGB").resize((W, H), Image.LANCZOS)
    im.save(jpg, quality=90)
    mock = im.copy()
    d = ImageDraw.Draw(mock)
    g = im.convert("L")
    for rows, colour in ((BANDS, (255, 60, 60)), (REAL_ROWS, (60, 200, 255))):
        for name, (x0, y0, x1, y1) in rows.items():
            d.rectangle((x0, y0, x1 - 1, y1), outline=colour)
            px = list(g.crop((x0, y0, x1, y1)).getdata())
            print(f"{name:9s} mean={sum(px)/len(px):5.1f} max={max(px)}")
    mock.save(os.path.join(HERE, "mock.jpg"), quality=90)
    print(jpg)


if __name__ == "__main__":
    render()
