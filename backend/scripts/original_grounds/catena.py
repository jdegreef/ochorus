"""The grounds for the catena series: A Catena on John, on Romans, on Matthew.

A catena is a chain of voices, and each ground draws one: small clay lamps
along a dark ridge, one for each commentator in the book, joined by a fine
gold chain that hangs between them, under a night sky going to dawn. The
frame is the series' (`scene`); each book has its own sky and landscape:

* John: eleven lamps under a deep blue night, low hills, a morning star.
  "The light shines in the darkness, and the darkness has not overcome it"
  (John 1:5).
* Romans: seven lamps under a wine-dark sky, the morning star (Romans 13:12),
  a Roman aqueduct on the far hills.
* Matthew: four lamps on a lakeshore, a lit town on a hill across the water
  (Matthew 5:14–15), under a deep green night.

The house rules for white type hold for all of them. The lamps sit in the
lower third, below the title band (their flames below y=560); nothing but sky
rises into the title band (it ends at y=463); the foreground ridge top stays
above the subtitle band (y=519); the mark zone (y664-747) is over the dark
foreground; the dawn is a low haze behind the far hills. Wordless, so every
edition's title can be set over it.

    python3 backend/scripts/original_grounds/catena.py OUTDIR [SLUG ...]

writes OUTDIR/<slug>.html; render it at 2x with headless Chromium (600x800
window) and downscale with Pillow to the committed jpg, which is FROZEN by
digest in curated_art.ORIGINAL_GROUND. A change to `scene` must leave every
shipped ground's HTML byte-identical, or its jpg (and digest) moves.
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


def chain(lamps=LAMPS, sag=SAG, links=LINKS):
    """The gold chain: a catenary hung between each lamp's handle and the next's,
    drawn as small links, alternately face-on and edge-on. The cosh term is
    normalised to run from 0 at either end to 1 at the middle."""
    out = []
    for (x1, y1, s1), (x2, y2, s2) in itertools.pairwise(lamps):
        ax, ay = x1 - 15 * s1, y1 - 5 * s1
        bx, by = x2 - 15 * s2, y2 - 5 * s2
        angle = math.degrees(math.atan2(by - ay, bx - ax))
        for i in range(links + 1):
            t = i / links
            px = ax + (bx - ax) * t
            py = ay + (by - ay) * t + sag * (math.cosh(2 * t - 1) - _COSH1) / (1 - _COSH1)
            ry = 1.3 if i % 2 == 0 else .7
            out.append(
                f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="2.6" ry="{ry}" fill="none" '
                f'stroke="#c9a14e" stroke-width=".9" opacity=".85" transform="rotate({angle:.0f} {px:.1f} {py:.1f})"/>'
            )
    return "".join(out)


def scene(sky, dawn, seed, star, landscape, lamps=LAMPS, sag=SAG, links=LINKS, n_stars=110):
    """A catena ground: a night sky going to dawn, stars, one bright star, the
    book's own `landscape` (SVG, all of it below the title band), a warm pool
    on the ground, and the chain of `lamps` along the dark foreground.

    `sky` is the gradient's four colours, top to horizon; `dawn` is the low
    glow: (centre y, radius, (colour, opacity) at its heart, (colour, opacity)
    halfway out); it fades into the horizon colour. `star` is (x, y, r)."""
    top, high, low, horizon = sky
    dawn_y, dawn_r, (heart, heart_o), (mid, mid_o) = dawn
    return f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{top}"/><stop offset=".40" stop-color="{high}"/>
  <stop offset=".56" stop-color="{low}"/><stop offset=".62" stop-color="{horizon}"/>
  <stop offset="1" stop-color="{horizon}"/>
 </linearGradient>
 <radialGradient id="dawn" cx="300" cy="{dawn_y}" r="{dawn_r}" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="{heart}" stop-opacity="{heart_o}"/>
  <stop offset=".45" stop-color="{mid}" stop-opacity="{mid_o}"/>
  <stop offset="1" stop-color="{horizon}" stop-opacity="0"/>
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
{stars(seed, n_stars)}
<circle cx="{star[0]}" cy="{star[1]}" r="{star[2]}" fill="#fff" opacity=".95"/>
{landscape}
<rect x="0" y="560" width="600" height="90" fill="url(#pool)"/>
{chain(lamps, sag, links)}
{"".join(lamp(*p) for p in lamps)}
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''


#: A Catena on John: eleven lamps under a deep blue night (John 1:5).
JOHN = scene(
    sky=("#050812", "#0b1428", "#14203a", "#22283f"),
    dawn=(530, 230, ("#b8875a", ".55"), ("#6a4e52", ".30")),
    seed=43, star=(476, 58, 2.1),
    landscape="\n".join((
        ridge([(0, 478), (80, 470), (160, 476), (240, 466), (310, 472), (380, 480), (450, 470), (530, 476), (600, 468)],
              "#2a2a3d"),
        ridge([(0, 494), (70, 489), (150, 486), (220, 492), (300, 496), (380, 492), (460, 487), (540, 491), (600, 488)],
              "#161624"),
        ridge([(0, 508), (100, 503), (200, 506), (300, 510), (400, 505), (500, 502), (600, 506)], "#0a0a10"),
    )),
)


def aqueduct(x0, x1, top, span, pier, fill):
    """A Roman aqueduct's single tier of round arches, 40px tall from `top`:
    one path, each opening cut out (even-odd), so the sky and the hills behind
    show through it."""
    d = [f"M{x0} {top} L{x1} {top} L{x1} {top + 40} L{x0} {top + 40} Z"]
    x, r = x0 + pier, span / 2
    while x + span <= x1:
        d.append(f"M{x} {top + 40} L{x} {top + 10 + r:.1f} A{r:.1f} {r:.1f} 0 0 1 {x + span} {top + 10 + r:.1f} "
                 f"L{x + span} {top + 40} Z")
        x += span + pier
    return f'<path d="{" ".join(d)}" fill="{fill}" fill-rule="evenodd"/>'


#: A Catena on Romans: seven lamps, one for each voice, under a wine-dark sky
#: before dawn, with the morning star high on the right — "The night is almost
#: over; the day is close" (Romans 13:12) — and, on the far hills, a Roman
#: aqueduct: the road the letter took to the city it was written to.
ROMANS = scene(
    sky=("#0a0508", "#1a0b12", "#2a121a", "#3a1c22"),
    dawn=(520, 250, ("#c98e5c", ".55"), ("#7a4048", ".30")),
    seed=13, n_stars=80, star=(468, 74, 2.3),
    landscape=(
        ridge([(0, 482), (90, 474), (170, 480), (260, 472), (350, 478), (430, 484), (520, 476), (600, 480)], "#3a2230")
        + aqueduct(250, 590, 466, 22, 6, "#2a1824")
        + ridge([(0, 496), (80, 492), (160, 489), (250, 494), (330, 499), (410, 494), (490, 490), (600, 493)], "#1c1018")
        + ridge([(0, 508), (100, 504), (200, 507), (300, 511), (400, 506), (500, 503), (600, 507)], "#0c070a")
    ),
    lamps=[(52, 600, .92), (134, 607, .98), (216, 612, 1.02), (298, 614, 1.06),
           (380, 612, 1.08), (462, 607, 1.11), (544, 600, 1.14)],
    sag=22, links=13,
)


def town(cx, base, fill, lit):
    """A small town on a hilltop, seen far off: blocks of houses, a taller one
    in the middle, and a few lit windows."""
    r = random.Random(5)
    out, x = [], cx - 46
    while x < cx + 46:
        w = r.choice([8, 10, 12])
        h = r.choice([6, 8, 10]) if abs(x - cx) > 10 else 14
        out.append(f'<rect x="{x}" y="{base - h}" width="{w}" height="{h + 2}" fill="{fill}"/>')
        if r.random() < .35:
            out.append(f'<rect x="{x + w / 2 - 1:.1f}" y="{base - h + 3}" width="1.6" height="1.6" fill="{lit}"/>')
        x += w
    return "".join(out)


#: A Catena on Matthew: four lamps, one for each voice, lit on the shore of a
#: still lake before dawn, and across the water a town on a hill, its windows
#: lit — "A town built on a hilltop cannot be hidden. No one lights a lamp and
#: hides it under a basket" (Matthew 5:14–15), under a deep green night.
MATTHEW = scene(
    sky=("#040a0a", "#0a1a1a", "#11282a", "#1b3433"),
    dawn=(500, 240, ("#c9a464", ".50"), ("#4f5a48", ".28")),
    seed=40, n_stars=100, star=(120, 66, 2.3),
    landscape=(
        ridge([(0, 484), (90, 480), (180, 486), (250, 478), (300, 470), (350, 478), (420, 486), (510, 480), (600, 484)],
              "#20302f")
        + town(300, 473, "#20302f", "#f6c46a")
        # The lake: a band of still water holding the dawn, with a few glints.
        + '<rect x="0" y="486" width="600" height="20" fill="#2b3f3a" opacity=".55"/>'
        + "".join(
            f'<rect x="{x}" y="{y}" width="{w}" height="1" fill="#e6c27a" opacity=".35"/>'
            for x, y, w in ((262, 490, 30), (286, 494, 22), (310, 497, 34), (278, 500, 18), (330, 502, 14))
        )
        + ridge([(0, 506), (100, 503), (200, 507), (300, 510), (400, 506), (500, 502), (600, 505)], "#081010")
    ),
    lamps=[(84, 602, 1.12), (228, 610, 1.2), (372, 610, 1.24), (516, 602, 1.28)],
    sag=30, links=21,
)

SCENES = {"catena-on-john": JOHN, "catena-on-romans": ROMANS, "catena-on-matthew": MATTHEW}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[2:] or SCENES:
        (OUT / f"{slug}.html").write_text(SCENES[slug])
        print(OUT / f"{slug}.html")
