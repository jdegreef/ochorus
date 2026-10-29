"""The ground of Faithful with Little (2026-10-29): the widow's two small coins
(Mark 12:42, told in the book's introduction), low in a pool of warm light on
the deep green the book's plate wore. Same contract as originals_series.py:

    python3 backend/scripts/original_grounds/faithful_with_little.py OUTDIR

The type on this cover is set from the top (the `originals` layout), so the
coins sit below the subtitle and above the mark, and everything from the
byline down to the subtitle stays a deep, even green. Set CHROME to a Chrome
or Chromium binary when it is not the macOS default.
"""
import os
import pathlib
import subprocess
import sys

from PIL import Image

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SLUG = "faithful-with-little"


def coin(cx, cy, rx, ry, tilt):
    """One small worn copper coin, seen at a low angle: rim, face, a struck mark."""
    return f'''<g transform="rotate({tilt} {cx} {cy})">
<ellipse cx="{cx}" cy="{cy + 4}" rx="{rx}" ry="{ry}" fill="#5a3418"/>
<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#copper)"/>
<ellipse cx="{cx}" cy="{cy}" rx="{rx - 4}" ry="{ry - 1.6}" fill="none" stroke="#7a4a22" stroke-width="1.6" opacity=".7"/>
<path d="M{cx - rx * .35} {cy - ry * .1} q{rx * .35} {-ry * .55} {rx * .7} 0" stroke="#6a3d1c" stroke-width="2" fill="none" opacity=".75"/>
<ellipse cx="{cx - rx * .3}" cy="{cy - ry * .35}" rx="{rx * .35}" ry="{ry * .22}" fill="#ffd9a0" opacity=".35"/>
</g>'''


HTML = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#173d2c"/><stop offset=".55" stop-color="#11301f"/><stop offset="1" stop-color="#0a1f14"/></linearGradient>
<radialGradient id="pool" cx="300" cy="598" r="170" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#e8b86a" stop-opacity=".42"/><stop offset=".45" stop-color="#b07a3a" stop-opacity=".16"/><stop offset="1" stop-color="#b07a3a" stop-opacity="0"/></radialGradient>
<radialGradient id="copper" cx=".38" cy=".3" r=".9">
<stop offset="0" stop-color="#f0b878"/><stop offset=".5" stop-color="#c27a3c"/><stop offset="1" stop-color="#8a4f24"/></radialGradient>
<linearGradient id="ledge" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#2a2016" stop-opacity="0"/><stop offset="1" stop-color="#1a130c" stop-opacity=".55"/></linearGradient>
<radialGradient id="vig" cx="300" cy="420" r="560" gradientUnits="userSpaceOnUse">
<stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></radialGradient>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
<circle cx="1" cy="1" r=".7" fill="#fff" fill-opacity=".04"/><circle cx="3" cy="3" r=".6" fill="#000" fill-opacity=".1"/></pattern>
</defs>
<rect width="600" height="800" fill="url(#bg)"/>
<rect y="560" width="600" height="240" fill="url(#ledge)"/>
<rect width="600" height="800" fill="url(#pool)"/>
<ellipse cx="300" cy="622" rx="78" ry="9" fill="#000" opacity=".35"/>
{coin(272, 604, 26, 10, -4)}
{coin(326, 610, 23, 9, 6)}
<rect width="600" height="800" fill="url(#vig)"/>
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
