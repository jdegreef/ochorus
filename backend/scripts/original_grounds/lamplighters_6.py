#!/usr/bin/env python3
"""Wordless cover ground for *Morning Comes* (Lamplighters of Gloamhaven, Book 6).

The first golden morning.  The Bright Mountain rises low on the cover, its snow
catching the gold; a line of lit waystones zigzags up its dark face to a small
fire on the summit, where one small figure holds the lamp up as the sun breaks the
horizon behind.  The last of the night stays deep blue above for the white title,
and warms to gold only below the subtitle row: this is the one cover of the six
where the sky is gold, and the only one with the sun in it.

Emits morning_cover.html (600x800 SVG), renders it at 2x with headless Chrome,
downsamples with Pillow to morning-comes.jpg, and writes mock.jpg with the cover
pipeline's white-type bands outlined (red) and the subtitle's real one-line-title
row (blue).  Rerun:  CHROME=/path/to/chrome python lamplighters_6.py OUTDIR
"""
import os
import random
import subprocess
import sys

# Output folder: the first argument, else beside this script.
HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H = 600, 800
HORIZON = 640
PEAK = (318, 566)  # the summit, just under the subtitle row

# Type bands the cover pipeline overlays (x0, y0, x1, y1).
BANDS = {
    "byline": (0, 102, 600, 130),
    "title": (70, 284, 530, 463),
    "subtitle": (70, 519, 530, 543),
    "mark": (232, 664, 368, 747),
}
# Where the subtitle really falls when the title sets on ONE line (as it does here).
REAL_ROWS = {
    "subtitle@1-line": (70, 493, 530, 517),
}

rnd = random.Random(6)
INK = "#0d0b10"


def stars():
    """The last stars, only high up, going out."""
    out = []
    for _ in range(18):
        x, y = rnd.uniform(8, 592), rnd.uniform(10, 220)
        if 92 < y < 140:
            continue
        r = rnd.choice([0.5, 0.6, 0.7])
        o = rnd.uniform(0.10, 0.30) * (1 - y / 280)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#eef0f4" opacity="{o:.2f}"/>')
    return "\n".join(out)


def mountain():
    """The Bright Mountain: one broad peak, its sunward (right) snow edge lit gold."""
    px, py = PEAK
    body = (f'M-10,{HORIZON + 6} C40,{HORIZON - 4} 110,{HORIZON - 22} 170,{py + 46} '
            f'C210,{py + 30} 250,{py + 22} 280,{py + 10} L300,{py + 3} L{px},{py} L336,{py + 5} '
            f'C360,{py + 14} 392,{py + 30} 430,{py + 46} C490,{py + 66} 550,{HORIZON - 14} 610,{HORIZON - 4} '
            f'L610,810 L-10,810 Z')
    # snow fields catching the first light along the right-hand shoulder
    snow = (f'M{px},{py} L336,{py + 5} C360,{py + 14} 392,{py + 30} 430,{py + 46} '
            f'C410,{py + 44} 388,{py + 38} 372,{py + 36} C360,{py + 30} 346,{py + 22} 334,{py + 20} '
            f'C328,{py + 14} 322,{py + 8} {px},{py} Z')
    rim = (f'M280,{py + 10} L300,{py + 3} L{px},{py} L336,{py + 5} C360,{py + 14} 392,{py + 30} 430,{py + 46} '
           f'C490,{py + 66} 550,{HORIZON - 14} 610,{HORIZON - 4}')
    return f'''
<g filter="url(#ink)">
  <path d="{body}" fill="url(#rock)"/>
  <path d="{snow}" fill="url(#snow)" opacity="0.9"/>
</g>
<path d="{rim}" stroke="#ffd98a" stroke-width="1.3" fill="none" opacity="0.75" filter="url(#ink)"/>
'''


def waystones():
    """The road up the face in zigzags, a lit waystone at every turn: a line of gold."""
    px, py = PEAK
    # turns of the road, from the foot (low left) to just under the summit
    # (the lowest turns swing wide round the Ochorus mark, x232-368 y664-747)
    turns = [(120, 716), (212, 698), (392, 680), (250, 658), (340, 640), (262, 622),
             (332, 606), (278, 592), (320, 581), (302, 574)]
    road = "M" + " L".join(f"{x},{y}" for x, y in turns) + f" L{px - 4},{py + 4}"
    out = [f'<path d="{road}" stroke="#d8a85e" stroke-width="0.7" fill="none" opacity="0.28" stroke-dasharray="2 3"/>']
    for i, (x, y) in enumerate(turns):
        s = 1.0 - i * 0.06
        out.append(f'<circle cx="{x}" cy="{y}" r="{9 * s:.1f}" fill="url(#halo)"/>')
        out.append(f'<rect x="{x - 1.6 * s:.1f}" y="{y - 6 * s:.1f}" width="{3.2 * s:.1f}" height="{7 * s:.1f}" fill="{INK}"/>')
        out.append(f'<circle cx="{x}" cy="{y - 4.2 * s:.1f}" r="{1.3 * s:.1f}" fill="#ffe3a0"/>')
    return "\n".join(out)


def summit():
    """The fire on the summit, and Wren beside it holding the lamp up to the sun."""
    px, py = PEAK
    fx, fy = px + 10, py + 1
    wx, wy = px - 8, py + 2  # Wren's feet
    return f'''
<circle cx="{fx}" cy="{fy - 4}" r="22" fill="url(#halo)"/>
<path d="M{fx},{fy} C{fx - 4},{fy - 2} {fx - 3},{fy - 8} {fx},{fy - 12} C{fx + 3},{fy - 8} {fx + 4},{fy - 2} {fx},{fy} Z" fill="url(#flame)"/>
<g filter="url(#ink)" fill="{INK}" stroke="{INK}">
  <path d="M{wx - 4},{wy} C{wx - 5},{wy - 6} {wx - 4},{wy - 12} {wx - 1.5},{wy - 14} L{wx + 1.5},{wy - 14} C{wx + 4},{wy - 12} {wx + 5},{wy - 6} {wx + 4},{wy} Z" stroke="none"/>
  <circle cx="{wx}" cy="{wy - 17}" r="3" stroke="none"/>
  <path d="M{wx - 3},{wy - 18} l-2,-2 l2.4,-0.4 l-0.4,-2.4 l2,1.4 l1,-2.6 l1,2.6 l2,-1.4 l-0.4,2.4 l2.4,0.4 l-2,2 Z" stroke="none"/>
  <path d="M{wx + 2},{wy - 12} L{wx + 5},{wy - 22}" stroke-width="1.6" stroke-linecap="round" fill="none"/>
</g>
<circle cx="{wx + 5.5}" cy="{wy - 25}" r="10" fill="url(#halo)"/>
<rect x="{wx + 4}" y="{wy - 27}" width="3" height="3.6" rx="1" fill="#fff1c2"/>
'''


def svg():
    px, py = PEAK
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{HORIZON}">
    <stop offset="0" stop-color="#0f1730"/>
    <stop offset="0.4" stop-color="#16244a"/>
    <stop offset="0.66" stop-color="#22325a"/>
    <stop offset="0.80" stop-color="#2c3558"/>
    <stop offset="0.85" stop-color="#5e4e60"/>
    <stop offset="0.90" stop-color="#c58a5a"/>
    <stop offset="0.96" stop-color="#f2b860"/>
    <stop offset="1" stop-color="#ffd98a"/>
  </linearGradient>
  <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fffbe8" stop-opacity="1"/>
    <stop offset="0.18" stop-color="#ffe9a8" stop-opacity="0.9"/>
    <stop offset="0.45" stop-color="#ffc766" stop-opacity="0.4"/>
    <stop offset="1" stop-color="#f29a40" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="rock" gradientUnits="userSpaceOnUse" x1="0" y1="{py}" x2="0" y2="760">
    <stop offset="0" stop-color="#2a2430"/>
    <stop offset="0.25" stop-color="#1b1720"/>
    <stop offset="1" stop-color="{INK}"/>
  </linearGradient>
  <linearGradient id="snow" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff1cf"/>
    <stop offset="1" stop-color="#e6b36c"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffe7a0" stop-opacity="0.75"/>
    <stop offset="0.35" stop-color="#f2a948" stop-opacity="0.25"/>
    <stop offset="1" stop-color="#e08a2a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#f6a63c"/>
    <stop offset="0.6" stop-color="#ffd36e"/>
    <stop offset="1" stop-color="#ffe9a8"/>
  </linearGradient>
  <filter id="ink" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.35" numOctaves="2" seed="6" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="1.4"/>
  </filter>
  <filter id="blur6"><feGaussianBlur stdDeviation="6"/></filter>
</defs>

<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars()}

<!-- the sun breaking the horizon right of the peak, with long soft rays up into the gold -->
<g filter="url(#blur6)" opacity="0.35">
  {''.join(f'<path d="M476,{HORIZON - 30} L{476 + dx},{HORIZON - 92} L{476 + dx + 10},{HORIZON - 92} Z" fill="#ffe3a0"/>' for dx in (-110, -60, -10, 40, 90))}
</g>
<circle cx="476" cy="{HORIZON - 30}" r="96" fill="url(#sun)"/>
<circle cx="476" cy="{HORIZON - 30}" r="15" fill="#fffbe8"/>

<!-- far ranges, lit along their tops -->
<path d="M0,{HORIZON - 18} C70,{HORIZON - 34} 130,{HORIZON - 30} 190,{HORIZON - 22} L190,700 L0,700 Z" fill="#3a2f3a" opacity="0.9"/>
<path d="M420,{HORIZON - 26} C480,{HORIZON - 40} 540,{HORIZON - 36} 610,{HORIZON - 24} L610,700 L420,700 Z" fill="#433440" opacity="0.85"/>
{mountain()}
{waystones()}
{summit()}
</svg>'''


def page():
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#0f1730}} svg{{display:block}}
</style></head><body>{svg()}</body></html>'''


def render():
    from PIL import Image, ImageDraw
    os.makedirs(HERE, exist_ok=True)
    html = os.path.join(HERE, "morning_cover.html")
    png = os.path.join(HERE, "morning_cover@2x.png")
    jpg = os.path.join(HERE, "morning-comes.jpg")
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
