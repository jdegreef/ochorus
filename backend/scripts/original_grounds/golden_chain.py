"""The grounds for The Golden Chain, Aquinas's Catena Aurea in four volumes.

One family, four nights: a heavy gold chain hangs in a catenary across a dark
foreground, its links catching a low golden light, under a deep sky of stars.
The Catena Aurea is a chain of the Fathers' words; each volume wears the same
chain under its own sky (Matthew violet, Mark sea-green, Luke oxblood, John
night-blue), so the series reads as one on a shelf. The chain hangs wholly
below the subtitle band (its top at y>=556) and above the mark zone (its
lowest link above y=652); the dark foreground's top edge stays above y=519;
the upper two-thirds stay dark for the white title. Wordless, so every
edition's title can be set over it.

    python3 backend/scripts/original_grounds/golden_chain.py OUTDIR [SLUG ...]

writes OUTDIR/<slug>.html; render it at 2x with headless Chromium (600x800
window) and downscale with Pillow to the committed jpg, which is FROZEN by
digest in curated_art.ORIGINAL_GROUND.
"""
import math
import pathlib
import random
import sys

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()

#: slug -> (sky top, sky middle, sky at the horizon, far hills, star seed)
SKIES = {
    "catena-aurea-matthew": ("#07050f", "#1a1230", "#3a2a4a", "#231a33", 11),
    "catena-aurea-mark": ("#030a0c", "#0e2228", "#24403f", "#142a2c", 23),
    "catena-aurea-luke": ("#0d0505", "#2a1210", "#4a2a22", "#2c1714", 37),
    "catena-aurea-john": ("#04060f", "#0f1a33", "#26304c", "#161d33", 53),
}


def stars(seed, n=120, ymax=440):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = r.uniform(6, 594), r.uniform(6, ymax)
        out.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.choice([0.6, 0.8, 1.0, 1.3]):.1f}" '
            f'fill="#fff" opacity="{r.uniform(.25, .7) * (1 - y / (ymax * 1.5)):.2f}"/>'
        )
    return "".join(out)


def ridge(points, fill):
    d = "M0 800 L" + " L".join(f"{x} {y}" for x, y in points) + " L600 800 Z"
    return f'<path d="{d}" fill="{fill}"/>'


#: The chain: hung from just outside either edge, sagging to its lowest point
#: mid-frame. Link pitch along the curve, and the link's outer half-sizes.
LEFT, RIGHT, TOP, SAG = (-20, 568), (620, 568), 568, 66
PITCH, LONG, SHORT = 17.0, 12.0, 6.6
_COSH1 = math.cosh(1)


def curve(t):
    """A point on the catenary at t in [0, 1], and its slope angle in degrees."""
    x = LEFT[0] + (RIGHT[0] - LEFT[0]) * t
    y = TOP + SAG * (math.cosh(2 * t - 1) - _COSH1) / (1 - _COSH1)
    dy = SAG * 2 * math.sinh(2 * t - 1) / (1 - _COSH1)
    return x, y, math.degrees(math.atan2(dy, RIGHT[0] - LEFT[0]))


def chain():
    """Links along the catenary at an even pitch, alternately face-on (an open
    oval) and edge-on (a narrow bar), each with a highlight on its upper rim."""
    samples = [curve(i / 2000) for i in range(2001)]
    points, walked, last = [samples[0]], 0.0, samples[0]
    for p in samples[1:]:
        walked += math.dist(p[:2], last[:2])
        last = p
        if walked >= PITCH:
            points.append(p)
            walked = 0.0
    out = []
    for i, (x, y, a) in enumerate(points):
        if i % 2 == 0:
            out.append(
                f'<g transform="rotate({a:.1f} {x:.1f} {y:.1f})">'
                f'<ellipse cx="{x:.1f}" cy="{y + 1.2:.1f}" rx="{LONG:.1f}" ry="{SHORT:.1f}" fill="none" '
                f'stroke="#000" stroke-width="4.2" opacity=".45"/>'
                f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{LONG:.1f}" ry="{SHORT:.1f}" fill="none" '
                f'stroke="url(#gold)" stroke-width="3.6"/>'
                f'<path d="M{x - LONG * .7:.1f} {y - SHORT * .72:.1f} Q{x:.1f} {y - SHORT * 1.08:.1f} '
                f'{x + LONG * .7:.1f} {y - SHORT * .72:.1f}" fill="none" stroke="#fff2c4" '
                f'stroke-width="1.1" opacity=".75"/></g>'
            )
        else:
            out.append(
                f'<g transform="rotate({a:.1f} {x:.1f} {y:.1f})">'
                f'<rect x="{x - LONG - 1:.1f}" y="{y - 1.6:.1f}" width="{2 * LONG + 2:.1f}" height="4.4" rx="2.2" '
                f'fill="#000" opacity=".45"/>'
                f'<rect x="{x - LONG - 1:.1f}" y="{y - 2.6:.1f}" width="{2 * LONG + 2:.1f}" height="4.6" rx="2.3" '
                f'fill="url(#goldbar)"/></g>'
            )
    # Draw the edge-on links first, so each face-on link passes over its neighbours.
    return "".join(out[1::2] + out[0::2])


def ground(slug):
    top, mid, low, hills, seed = SKIES[slug]
    return f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{top}"/><stop offset=".42" stop-color="{mid}"/>
  <stop offset=".62" stop-color="{low}"/><stop offset="1" stop-color="{low}"/>
 </linearGradient>
 <radialGradient id="glow" cx="300" cy="512" r="250" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#c99a52" stop-opacity=".50"/>
  <stop offset=".45" stop-color="#7a5a3e" stop-opacity=".22"/>
  <stop offset="1" stop-color="{low}" stop-opacity="0"/>
 </radialGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#f7dc8e"/><stop offset=".5" stop-color="#d4a443"/><stop offset="1" stop-color="#8a5f1c"/>
 </linearGradient>
 <linearGradient id="goldbar" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fbe7a6"/><stop offset=".55" stop-color="#c8963a"/><stop offset="1" stop-color="#7a5218"/>
 </linearGradient>
 <radialGradient id="pool" cx="300" cy="610" r="300" gradientUnits="userSpaceOnUse"
   gradientTransform="translate(0 610) scale(1 .16) translate(0 -610)">
  <stop offset="0" stop-color="#f3c76a" stop-opacity=".16"/><stop offset="1" stop-color="#f3c76a" stop-opacity="0"/>
 </radialGradient>
 <pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.035"/>
  <circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.08"/>
 </pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#glow)"/>
{stars(seed)}
{ridge([(0, 482), (90, 474), (170, 480), (250, 470), (330, 477), (410, 484), (490, 473), (600, 480)], hills)}
{ridge([(0, 500), (120, 494), (240, 499), (360, 503), (480, 496), (600, 500)], "#0b0a0e")}
{ridge([(0, 512), (150, 508), (300, 511), (450, 507), (600, 510)], "#050507")}
<rect x="0" y="540" width="600" height="130" fill="url(#pool)"/>
{chain()}
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''


SCENES = {slug: ground(slug) for slug in SKIES}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[2:] or SCENES:
        (OUT / f"{slug}.html").write_text(SCENES[slug])
        print(OUT / f"{slug}.html")
