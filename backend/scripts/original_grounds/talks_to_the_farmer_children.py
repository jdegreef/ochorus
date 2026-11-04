"""The ground of Talks to the Farmer (For Children) (2026-10-30): a child sowing
seed across a ploughed field at dawn ("The Sower", "The Grain That Grows" in
the children's retelling). Before this the children's and teens' editions wore
the same photograph and could not be told apart on a shelf; the teens keep it.
Young Readers "Storybook" system (one child, lower third, deep sky for the white
title, the glow low at the horizon). Same contract as originals_series.py:

    python3 backend/scripts/original_grounds/talks_to_the_farmer_children.py OUTDIR

Set CHROME to a Chrome or Chromium binary when it is not the macOS default.
"""
import os
import pathlib
import subprocess
import sys

from PIL import Image

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SLUG = "talks-to-the-farmer-children"

# Furrows: curves from the near edge converging on a point on the horizon.
VX, VY = 300, 566
FURROWS = "".join(
    f'<path d="M{x} 800 Q{(x + VX) / 2 + (x - VX) * 0.1} 660 {VX + (x - VX) * 0.04} {VY + 6}" '
    f'stroke="#2c1d14" stroke-width="{3 + abs(x - VX) / 120:.1f}" fill="none" opacity=".55"/>'
    for x in range(-500, 1101, 80)
)
# Seed in flight, an arc from the child's hand.
SEEDS = "".join(
    f'<circle cx="{232 + i * 15}" cy="{596 - 20 * (i / 6) + (i / 6) ** 2 * 34:.1f}" r="{2.6 - i * 0.12:.1f}" fill="#f6d98c" opacity="{0.95 - i * 0.05:.2f}"/>'
    for i in range(12)
)
STARS = "".join(
    f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" opacity="{o}"/>'
    for x, y, r, o in [(70, 60, 1.6, .8), (520, 90, 1.3, .7), (140, 180, 1.1, .5), (470, 230, 1.4, .55),
                       (40, 300, 1, .4), (560, 330, 1.2, .45), (330, 40, 1.1, .6), (250, 150, 0.9, .4)]
)

HTML = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#161f47"/><stop offset=".5" stop-color="#2b2f63"/>
<stop offset=".64" stop-color="#5b4472"/><stop offset=".71" stop-color="#c7774d"/></linearGradient>
<radialGradient id="glow" cx="420" cy="566" r="230" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#ffcf7a" stop-opacity=".75"/><stop offset=".4" stop-color="#e98d55" stop-opacity=".3"/>
<stop offset="1" stop-color="#e98d55" stop-opacity="0"/></radialGradient>
<linearGradient id="field" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#6b4a33"/><stop offset=".35" stop-color="#4b3222"/><stop offset="1" stop-color="#2a1b12"/></linearGradient>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
<circle cx="1" cy="1" r=".7" fill="#fff" fill-opacity=".04"/><circle cx="3" cy="3" r=".6" fill="#000" fill-opacity=".1"/></pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
{STARS}
<rect width="600" height="800" fill="url(#glow)"/>
<circle cx="420" cy="566" r="30" fill="#ffd98a"/>
<path d="M0 560 Q90 538 180 552 T360 548 T600 556 V575 H0 Z" fill="#2b2140"/>
<rect y="566" width="600" height="234" fill="url(#field)"/>
<path d="M0 566 H600" stroke="#8a5a3a" stroke-width="2" opacity=".5"/>
{FURROWS}
<!-- the child: feet on a furrow, left of the mark, sowing toward the light -->
<g transform="translate(168 0)">
<ellipse cx="22" cy="664" rx="34" ry="6" fill="#000" opacity=".35"/>
<path d="M8 660 L13 622 H24 L28 660 Z" fill="#3b2a24"/>
<path d="M-2 584 Q22 572 42 584 L46 630 H-6 Z" fill="#c4553b"/>
<path d="M-6 628 H46 L44 636 H-4 Z" fill="#9c3f2c"/>
<path d="M30 590 Q50 588 62 598" stroke="#c4553b" stroke-width="9" stroke-linecap="round" fill="none"/>
<circle cx="64" cy="598" r="5" fill="#e3a57a"/>
<path d="M4 598 Q-10 614 -2 626" stroke="#c4553b" stroke-width="8" stroke-linecap="round" fill="none"/>
<ellipse cx="-4" cy="628" rx="11" ry="9" fill="#d9b77c"/>
<path d="M-12 622 Q-4 616 4 622" stroke="#a8844d" stroke-width="2" fill="none"/>
<circle cx="20" cy="566" r="15" fill="#e3a57a"/>
<path d="M4 562 Q8 546 22 548 Q36 548 36 564 Q30 556 20 556 Q10 556 4 562 Z" fill="#3a2418"/>
</g>
{SEEDS}
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    h, png = OUT / f"{SLUG}.html", OUT / f"{SLUG}@2x.png"
    h.write_text(HTML)
    # Headless Chrome can exit non-zero after writing the screenshot ("Teardown
    # watchdog expired"), so the file, not the return code, says it worked.
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--window-size=600,800", f"--screenshot={png}", f"file://{h}"], capture_output=True)
    Image.open(png).convert("RGB").resize((600, 800), Image.LANCZOS).save(OUT / f"{SLUG}.jpg", quality=90)
    h.unlink()
    png.unlink()
    print("drew", SLUG)
