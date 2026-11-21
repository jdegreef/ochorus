"""The After His Heart ground (2026-11-20): a shepherd leading his flock home
over a ridge at dusk, the last light low behind the far hills (Jeremiah 3:15,
"shepherds who are after my own heart"; John 10:3-4, "he goes ahead of them").

    python3 backend/scripts/original_grounds/after_his_heart.py OUTDIR

`BookCover` sets the type over this ground, so the scene keeps clear of where
the words fall (level-up-cover's ink bands): byline y102-131, title y284-463,
subtitle y457-543, mark y664-747 (x232-368). The sky stays deep and starless
behind every text row; the glow sits low (below y570) behind the far hills,
the shepherd and his flock stand on the ridge between the subtitle and the
mark, and the mark sits over the dark near slope.

CHROME defaults to macOS Chrome; set CHROME to any Chromium binary elsewhere.
"""
import os
import pathlib
import random
import subprocess
import sys

from PIL import Image

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SLUG = "after-his-heart"

# Text rows, padded, where no star may fall.
KEEP_CLEAR = [(0, 88, 600, 145), (30, 270, 570, 560)]


def stars(seed=315, n=120):
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        x, y = rnd.uniform(6, 594), rnd.uniform(6, 300)
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in KEEP_CLEAR):
            continue
        r = rnd.choice([0.6, 0.8, 1.0, 1.0, 1.3, 1.6])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" fill-opacity="{rnd.uniform(.3, .8):.2f}"/>')
    return "".join(out)


INK = "#0b0a16"


def shepherd(x, feet, h):
    """A robed, hooded figure walking right, a crook in the forward hand."""
    s = h / 60
    st = f'stroke="{INK}" stroke-width="2.4" fill="none" stroke-linecap="round"'
    return (f'<g transform="translate({x} {feet}) scale({s:.3f})" fill="{INK}">'
            '<circle cx="1.5" cy="-52" r="6"/>'
            '<path d="M-6.5 -50 Q-6 -61 2 -61 Q9 -61 9 -53 L10 -46 L-8 -44Z"/>'  # hood
            '<path d="M-9 -45 Q1 -49 10 -45 L12 -30 L15 0 L-15 0 L-11 -28Z"/>'  # robe
            '<path d="M9 -43 L21 -33 L19.5 -30.5 L8 -38Z"/>'  # forward arm
            f'<path d="M21 -33 L22.5 0" {st}/>'
            f'<path d="M21 -33 L19.5 -60 Q19.5 -67 25.5 -67 Q31 -67 31 -61" {st}/>'
            '</g>')


def sheep(x, feet, w, flip=False):
    s = w / 30
    sx = -s if flip else s
    return (f'<g transform="translate({x} {feet}) scale({sx:.3f} {s:.3f})" fill="{INK}">'
            '<ellipse cx="0" cy="-11" rx="13" ry="8"/>'
            '<ellipse cx="13" cy="-15" rx="5" ry="4"/>'
            '<rect x="-9" y="-6" width="2.4" height="6"/><rect x="-3" y="-6" width="2.4" height="6"/>'
            '<rect x="4" y="-6" width="2.4" height="6"/><rect x="8.5" y="-6" width="2.4" height="6"/>'
            '</g>')


# The ridge the shepherd walks: its crest line, sampled where each figure stands.
RIDGE = "M0 650 C80 640 150 628 230 626 C320 624 420 634 600 648 V800H0Z"


def crest(x):
    # Close enough to RIDGE's top edge for placing feet (piecewise linear).
    pts = [(0, 650), (80, 637), (150, 629), (230, 626), (320, 626), (420, 632), (520, 640), (600, 648)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def flock():
    rnd = random.Random(7)
    out = []
    xs = [138, 112, 88, 64, 44, 22, 4, 122, 76, 34]
    for i, x in enumerate(xs):
        w = rnd.uniform(22, 27) if i < 7 else rnd.uniform(15, 17)  # the last three are lambs
        out.append(sheep(x, crest(x) + rnd.uniform(1, 4), w))
    return "".join(out)


HTML = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#080b1e"/><stop offset=".45" stop-color="#141a3a"/>
  <stop offset=".68" stop-color="#2a2a4d"/><stop offset=".74" stop-color="#5b3f57"/>
  <stop offset=".785" stop-color="#b8735a"/><stop offset=".81" stop-color="#e7a865"/></linearGradient>
<radialGradient id="glow" cx="300" cy="640" r="300" gradientUnits="userSpaceOnUse" gradientTransform="translate(0 640) scale(1 .3) translate(0 -640)">
  <stop offset="0" stop-color="#f7c879" stop-opacity=".55"/><stop offset="1" stop-color="#f7c879" stop-opacity="0"/></radialGradient>
<linearGradient id="far" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a2c44"/><stop offset="1" stop-color="#241d33"/></linearGradient>
<radialGradient id="vig" cx="300" cy="400" r="560" gradientUnits="userSpaceOnUse"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="#fff" fill-opacity=".04"/><circle cx="3" cy="3" r=".6" fill="#000" fill-opacity=".1"/></pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
{stars()}
<rect width="600" height="800" fill="url(#glow)"/>
<path d="M0 622 C70 606 130 612 190 618 C260 625 320 604 390 608 C460 612 530 622 600 614 V800H0Z" fill="url(#far)"/>
<path d="{RIDGE}" fill="#120f1f"/>
<path d="M0 706 C150 692 380 716 600 698 V800H0Z" fill="#0c0a16"/>
{flock()}
{shepherd(186, crest(186) + 1, 66)}
<rect width="600" height="800" fill="url(#vig)"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    h = OUT / f"{SLUG}.html"
    h.write_text(HTML)
    png = OUT / f"{SLUG}@2x.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                    "--force-device-scale-factor=2", "--window-size=600,800", f"--screenshot={png}", f"file://{h}"],
                   capture_output=True)
    Image.open(png).convert("RGB").resize((600, 800), Image.LANCZOS).save(OUT / f"{SLUG}.jpg", quality=90)
    print("drew", SLUG)
