"""The Coram Deo ground (2026-11-16): a doorway of light standing alone under a
night sky. James chose it from twenty variations on an open-door concept
("A door in the open"): God's presence is not tied to a building, and the
reader is invited to walk toward it every day.

    python3 backend/scripts/original_grounds/coram_deo.py OUTDIR

`BookCover` sets the type over this ground, so the composition keeps clear of
where the words fall on the framed English cover (og-manifest rows): byline
y102-131, title y337-439, subtitle y457-485, mark y664-746 (x232-368). The sky
above y495 is dark and starless behind every text row; the door stands in the
gap between the subtitle and the mark, and its path bends away to the lower
left so the mark sits over dark ground.

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
SLUG = "coram-deo"

# Text rows on the framed cover, padded, where no star may fall (the byline
# band is measured edge to edge, so it is kept clear across the full width).
KEEP_CLEAR = [(0, 88, 600, 145), (40, 322, 560, 452), (60, 444, 540, 498)]


def stars(seed=16, n=150):
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        x, y = rnd.uniform(6, 594), rnd.uniform(6, 500)
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in KEEP_CLEAR):
            continue
        r = rnd.choice([0.6, 0.8, 1.0, 1.0, 1.3, 1.6])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" fill-opacity="{rnd.uniform(.3, .85):.2f}"/>')
    return "".join(out)


def figure(x, feet, h, color):
    s = h / 57
    return (f'<g transform="translate({x} {feet}) scale({s:.3f})" fill="{color}">'
            '<circle cx="0" cy="-50" r="7"/><path d="M-9 -40 Q0 -46 9 -40 L12 0 L4 0 L1 -22 L-1 -22 L-4 0 L-12 0Z"/></g>')


DOOR = "M272 640 V545 A28 28 0 0 1 328 545 V640Z"

HTML = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#070a1d"/><stop offset=".5" stop-color="#121634"/>
  <stop offset=".72" stop-color="#2c2748"/><stop offset=".8" stop-color="#3f3255"/></linearGradient>
<linearGradient id="light" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffbef"/><stop offset="1" stop-color="#f3c066"/></linearGradient>
<radialGradient id="halo" cx="300" cy="598" r="110" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#f6c66e" stop-opacity=".55"/><stop offset="1" stop-color="#f6c66e" stop-opacity="0"/></radialGradient>
<linearGradient id="path" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9bf6e" stop-opacity=".62"/><stop offset="1" stop-color="#e9bf6e" stop-opacity=".1"/></linearGradient>
<filter id="soft" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="14"/></filter>
<radialGradient id="vig" cx="300" cy="400" r="560" gradientUnits="userSpaceOnUse"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="#fff" fill-opacity=".04"/><circle cx="3" cy="3" r=".6" fill="#000" fill-opacity=".1"/></pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
{stars()}
<path d="M0 640 C90 628 200 646 300 640 C420 632 520 644 600 636 V800H0Z" fill="#141226"/>
<path d="M0 700 C160 688 330 712 600 694 V800H0Z" fill="#0d0c1a"/>
<circle cx="300" cy="598" r="110" fill="url(#halo)"/>
<path d="M276 640 L324 640 C290 668 200 690 170 800 L30 800 C90 700 240 676 276 640Z" fill="url(#path)"/>
<path d="{DOOR}" fill="#f6c66e" filter="url(#soft)" opacity=".85"/>
<path d="{DOOR}" fill="url(#light)"/>
{figure(268, 664, 28, "#0b0a14")}
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
