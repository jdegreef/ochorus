"""The grounds for the catenas: A Catena on John, and (SCENES) its siblings.

A catena is a chain of voices, and this ground draws one: eleven small clay
lamps along a dark ridge, one for each commentator in the book, joined by a
fine gold chain that hangs between them, under a deep night sky going to dawn.
"The light shines in the darkness, and the darkness has not overcome it"
(John 1:5). The lamps sit in the lower third, below the title band (their
flames below y=560), the ridge top stays above the subtitle band (y=519), and
the mark zone (y664-747) is over the dark foreground. The upper two-thirds
stay night-dark for the white title; the dawn is a low haze behind the far
hills. Wordless, so every edition's title can be set over it.

    python3 backend/scripts/original_grounds/catena.py OUTDIR [SLUG ...]

writes OUTDIR/<slug>.html; render it at 2x with headless Chromium (600x800
window) and downscale with Pillow to the committed jpg, which is FROZEN by
digest in curated_art.ORIGINAL_GROUND.
"""
import itertools
import math
import pathlib
import random
import sys

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()


def stars(seed, n=110, ymax=430):
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


#: Eleven lamps, back-left to front-right along a gentle rise and fall: (x, y) of
#: each lamp's base, and its scale (the nearer, the larger).
LAMPS = [
    (38, 596, .84), (90, 603, .88), (142, 609, .92), (194, 613, .96), (246, 615, .99),
    (298, 616, 1.02), (350, 615, 1.04), (402, 612, 1.06), (454, 607, 1.08), (506, 601, 1.1),
    (556, 594, 1.12),
]


def lamp(x, y, s):
    """A small clay oil lamp seen from the side, nozzle to the right, flame lit."""
    w, h = 36 * s, 11 * s
    body = (
        f'<path d="M{x - w / 2:.1f} {y:.1f} C{x - w / 2:.1f} {y - h:.1f} {x + w / 4:.1f} {y - h * 1.15:.1f} '
        f'{x + w / 2:.1f} {y - h * .55:.1f} L{x + w / 2 + 5 * s:.1f} {y - h * .7:.1f} '
        f'L{x + w / 2 + 4 * s:.1f} {y - h * .25:.1f} C{x + w / 4:.1f} {y + 1.5 * s:.1f} '
        f'{x - w / 3:.1f} {y + 1.5 * s:.1f} {x - w / 2:.1f} {y:.1f} Z" fill="url(#clay)"/>'
        f'<path d="M{x - w / 2 + 2 * s:.1f} {y - h * .55:.1f} C{x - w / 4:.1f} {y - h * 1.02:.1f} {x + w / 4:.1f} {y - h * 1.05:.1f} '
        f'{x + w / 2:.1f} {y - h * .55:.1f}" fill="none" stroke="#c98a4e" stroke-width="{1.1 * s:.1f}" opacity=".8"/>'
        f'<ellipse cx="{x - 2 * s:.1f}" cy="{y - h * .9:.1f}" rx="{5 * s:.1f}" ry="{1.4 * s:.1f}" fill="#1c120c"/>'
    )
    fx, fy = x + w / 2 + 4.5 * s, y - h * .75
    flame = (
        f'<circle cx="{fx:.1f}" cy="{fy - 5 * s:.1f}" r="{20 * s:.1f}" fill="url(#halo)"/>'
        f'<path d="M{fx:.1f} {fy - 13 * s:.1f} C{fx + 3.4 * s:.1f} {fy - 7 * s:.1f} {fx + 3 * s:.1f} {fy - 1 * s:.1f} '
        f'{fx:.1f} {fy:.1f} C{fx - 3 * s:.1f} {fy - 1 * s:.1f} {fx - 3.4 * s:.1f} {fy - 7 * s:.1f} {fx:.1f} {fy - 13 * s:.1f} Z" '
        f'fill="#f6c46a"/>'
        f'<path d="M{fx:.1f} {fy - 7 * s:.1f} C{fx + 1.4 * s:.1f} {fy - 4 * s:.1f} {fx + 1.2 * s:.1f} {fy - 1 * s:.1f} '
        f'{fx:.1f} {fy - .3 * s:.1f} C{fx - 1.2 * s:.1f} {fy - 1 * s:.1f} {fx - 1.4 * s:.1f} {fy - 4 * s:.1f} {fx:.1f} {fy - 7 * s:.1f} Z" '
        f'fill="#fff4d6"/>'
    )
    return body + flame


#: How far the chain sags between two lamps, and how many links hang there.
SAG, LINKS = 16, 9
_COSH1 = math.cosh(1)


def chain(lamps=LAMPS, link_every=None):
    """The gold chain: a catenary hung between each lamp's handle and the next's,
    drawn as small links, alternately face-on and edge-on. The cosh term is
    normalised to run from 0 at either end to 1 at the middle."""
    out = []
    for (x1, y1, s1), (x2, y2, s2) in itertools.pairwise(lamps):
        ax, ay = x1 - 15 * s1, y1 - 5 * s1
        bx, by = x2 - 15 * s2, y2 - 5 * s2
        angle = math.degrees(math.atan2(by - ay, bx - ax))
        links = round(math.dist((ax, ay), (bx, by)) / link_every) if link_every else LINKS
        for i in range(links + 1):
            t = i / links
            px = ax + (bx - ax) * t
            py = ay + (by - ay) * t + SAG * (math.cosh(2 * t - 1) - _COSH1) / (1 - _COSH1)
            ry = 1.3 if i % 2 == 0 else .7
            out.append(
                f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="2.6" ry="{ry}" fill="none" '
                f'stroke="#c9a14e" stroke-width=".9" opacity=".85" transform="rotate({angle:.0f} {px:.1f} {py:.1f})"/>'
            )
    return "".join(out)


def ground(lamps, figure="", link_every=None):
    """The family's night: sky going to dawn, three ridges, a pool of lamplight,
    the chain and its lamps, and a book's own figure (drawn under the chain)."""
    return f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#050812"/><stop offset=".40" stop-color="#0b1428"/>
  <stop offset=".56" stop-color="#14203a"/><stop offset=".62" stop-color="#22283f"/>
  <stop offset="1" stop-color="#22283f"/>
 </linearGradient>
 <radialGradient id="dawn" cx="300" cy="530" r="230" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#b8875a" stop-opacity=".55"/>
  <stop offset=".45" stop-color="#6a4e52" stop-opacity=".30"/>
  <stop offset="1" stop-color="#22283f" stop-opacity="0"/>
 </radialGradient>
 <radialGradient id="halo">
  <stop offset="0" stop-color="#f6c46a" stop-opacity=".42"/>
  <stop offset=".5" stop-color="#e09a4a" stop-opacity=".12"/>
  <stop offset="1" stop-color="#e09a4a" stop-opacity="0"/>
 </radialGradient>
 <linearGradient id="clay" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#8a5a34"/><stop offset=".55" stop-color="#5e3b22"/><stop offset="1" stop-color="#2e1d12"/>
 </linearGradient>
 <radialGradient id="pool" cx="300" cy="605" r="320" gradientUnits="userSpaceOnUse" gradientTransform="translate(0 605) scale(1 .12) translate(0 -605)">
  <stop offset="0" stop-color="#f6c46a" stop-opacity=".10"/><stop offset="1" stop-color="#f6c46a" stop-opacity="0"/>
 </radialGradient>
 <pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.035"/>
  <circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.08"/>
 </pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#dawn)"/>
{stars(43)}
<circle cx="476" cy="58" r="2.1" fill="#fff" opacity=".95"/>
{ridge([(0, 478), (80, 470), (160, 476), (240, 466), (310, 472), (380, 480), (450, 470), (530, 476), (600, 468)], "#2a2a3d")}
{ridge([(0, 494), (70, 489), (150, 486), (220, 492), (300, 496), (380, 492), (460, 487), (540, 491), (600, 488)], "#161624")}
{ridge([(0, 508), (100, 503), (200, 506), (300, 510), (400, 505), (500, 502), (600, 506)], "#0a0a10")}
<rect x="0" y="560" width="600" height="90" fill="url(#pool)"/>
{figure}{chain(lamps, link_every)}
{"".join(lamp(*p) for p in lamps)}
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

GROUND = ground(LAMPS)

#: A Catena on the Psalms: seven lamps, one for each of its commentators, three
#: either side of David's lyre and the seventh at its foot, with the first light
#: behind it: "Come awake, harp and lyre! I will wake up the dawn" (Psalm 57:8).
#: Lyre and lamps keep below the subtitle band (their tops under y=550).
PSALM_LAMPS = [
    (46, 600, .9), (130, 608, .95), (214, 614, 1.0), (300, 640, 1.08),
    (386, 614, 1.0), (470, 608, .95), (554, 600, .9),
]


def lyre(cx=300, top=553, foot=626):
    """A kinnor: a wooden sound box, two arms curving up and apart, a slanting
    yoke across their tips, and seven strings catching the lamplight."""
    box_top = foot - 26
    left_tip, right_tip = (cx - 40, top + 9), (cx + 42, top)
    frame = (
        f'<path d="M{cx - 30} {foot} Q{cx - 34} {box_top} {cx - 24} {box_top} L{cx + 24} {box_top} '
        f'Q{cx + 34} {box_top} {cx + 30} {foot} Z" fill="url(#clay)"/>'
        f'<path d="M{cx - 20} {box_top + 1} C{cx - 30} {box_top - 18} {cx - 44} {top + 34} {left_tip[0]} {left_tip[1]}" '
        f'fill="none" stroke="#5e3b22" stroke-width="5" stroke-linecap="round"/>'
        f'<path d="M{cx + 20} {box_top + 1} C{cx + 30} {box_top - 18} {cx + 46} {top + 28} {right_tip[0]} {right_tip[1]}" '
        f'fill="none" stroke="#5e3b22" stroke-width="5" stroke-linecap="round"/>'
        f'<path d="M{left_tip[0] - 5} {left_tip[1] + 1} L{right_tip[0] + 5} {right_tip[1] - 1}" '
        f'stroke="#6e4728" stroke-width="4.5" stroke-linecap="round"/>'
        f'<path d="M{cx - 20} {box_top + 1} C{cx - 30} {box_top - 18} {cx - 44} {top + 34} {left_tip[0]} {left_tip[1]}" '
        f'fill="none" stroke="#c98a4e" stroke-width="1" opacity=".55"/>'
        f'<path d="M{cx + 20} {box_top + 1} C{cx + 30} {box_top - 18} {cx + 46} {top + 28} {right_tip[0]} {right_tip[1]}" '
        f'fill="none" stroke="#c98a4e" stroke-width="1" opacity=".55"/>'
        f'<ellipse cx="{cx}" cy="{box_top + 12}" rx="7" ry="4" fill="#1c120c"/>'
    )
    strings = []
    for i in range(7):
        t = (i + 1) / 8
        x_top = left_tip[0] + (right_tip[0] - left_tip[0]) * t
        y_top = left_tip[1] + (right_tip[1] - left_tip[1]) * t + 2
        x_foot = cx - 16 + 32 * t
        strings.append(
            f'<line x1="{x_top:.1f}" y1="{y_top:.1f}" x2="{x_foot:.1f}" y2="{box_top + 4}" '
            f'stroke="#f2d9a0" stroke-width=".7" opacity=".8"/>'
        )
    return frame + "".join(strings)


PSALMS = ground(PSALM_LAMPS, figure=lyre(), link_every=6)

SCENES = {"catena-on-john": GROUND, "catena-on-the-psalms": PSALMS}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[2:] or SCENES:
        (OUT / f"{slug}.html").write_text(SCENES[slug])
        print(OUT / f"{slug}.html")
