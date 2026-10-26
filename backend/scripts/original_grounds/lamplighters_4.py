#!/usr/bin/env python3
"""Wordless cover ground for *The Hill of Cinders* (Lamplighters of Gloamhaven, Book 4).

The darkest moment just before morning.  Wren kneels low on the left on a ridge of
ash, the lamp burning small and low "like a coal under ash"; a line of worn
memorial stones leads across the Burned Country to Cinder Hill, black and round,
with the broken outline of the Lampwright's Workshop on top.  Behind the hill, at
the very horizon, the first thin gold-rose line of dawn, warming the rim of the hill.

Emits cinders_cover.html (600x800 SVG), renders it at 2x with headless Chrome,
downsamples with Pillow to the-hill-of-cinders.jpg, and writes mock.jpg with the
cover pipeline's white-type bands outlined (red) and the subtitle's real
one-line-title row (blue).  Rerun:  python lamplighters_4.py OUTDIR
"""
import os
import random
import subprocess
import sys

# Output folder: the first argument, else beside this script.
HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 600, 800
HORIZON = 566
RAISE = 48  # lift of the Wren group above where its shapes are drawn

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

rnd = random.Random(4)
INK = "#0b0a0b"


def stars():
    out = []
    for _ in range(26):
        x, y = rnd.uniform(8, 592), rnd.uniform(10, 280)
        if 92 < y < 140:
            continue
        r = rnd.choice([0.5, 0.6, 0.7, 0.9])
        o = rnd.uniform(0.16, 0.42)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#dfe4ea" opacity="{o:.2f}"/>')
    return "\n".join(out)


def ash_drift(y0, y1):
    """Soft low swells of grey ash across the plain, not straight lines (not water)."""
    out = []
    y = y0
    while y < y1:
        d = (y - HORIZON) / 300
        x0 = rnd.uniform(-60, 520)
        w = rnd.uniform(40, 180) * (0.6 + d)
        sag = rnd.uniform(1.5, 4) * (0.5 + d)
        o = 0.05 + 0.05 * rnd.random()
        out.append(
            f'<path d="M{x0:.0f},{y + sag:.1f} Q{x0 + w / 2:.0f},{y - sag:.1f} {x0 + w:.0f},{y + sag:.1f}" '
            f'stroke="#8d8a86" stroke-width="{0.6 + d * 0.7:.1f}" fill="none" opacity="{o:.2f}"/>'
        )
        y += 6 + d * 16
    return "\n".join(out)


def hill():
    """Cinder Hill: one black round dome rising out of the plain, right of centre,
    its crown low, well below the subtitle, with the long low ruined Workshop on top."""
    crown = 552  # top of the dome
    # its left foot meets the plain near the stones; its base sinks into the ash
    top = (f'M262,642 C292,638 312,626 328,604 C340,586 352,{crown + 8} 380,{crown + 4} '
           f'C410,{crown - 2} 470,{crown - 3} 505,{crown + 3} '
           f'C545,{crown + 8} 582,{crown + 22} 606,{crown + 40}')
    # the Workshop: a long low stone range, its roof fallen in, the wall-tops broken,
    # a broken gable end and a stub of forge-chimney still standing.  Nothing above y535.
    c = crown
    ws = (f'M396,{c + 3} V{c - 9} L400,{c - 13} L404,{c - 9} V{c - 10} H412 L414,{c - 7} '
          f'L418,{c - 11} H426 L428,{c - 6} H432 L433,{c - 10} H446 L448,{c - 13} H452 '
          f'V{c - 10} H462 L465,{c - 5} H470 L472,{c - 9} H482 V{c - 17} H487 V{c - 9} '
          f'H496 L500,{c - 12} L504,{c - 8} L508,{c - 4} L512,{c - 2} V{c + 3} Z')
    # empty window holes: only the dim sky shows through, no light within
    gaps = "".join(
        f'<rect x="{x}" y="{c - 7}" width="1.8" height="3.5" fill="#26262b"/>'
        for x in (408, 422, 440, 456, 477)
    )
    rim = (f'M380,{crown + 4} '
           f'C410,{crown - 2} 470,{crown - 3} 505,{crown + 3} '
           f'C545,{crown + 8} 582,{crown + 22} 606,{crown + 40}')
    dome = top + ' L610,664 C520,668 380,664 262,642 Z'
    return f'''
<g filter="url(#ink)" fill="{INK}">
  <path d="{dome}" fill="url(#hillfoot)"/>
  <path d="{ws}"/>
</g>
{gaps}
<!-- a faint warm rim where the dawn behind touches the hill's crown and the ruin -->
<path d="{rim}" stroke="#e6a77e" stroke-width="1" fill="none" opacity="0.5" filter="url(#ink)"/>
<path d="{ws}" stroke="#e6a77e" stroke-width="0.7" fill="none" opacity="0.35" filter="url(#ink)"/>
'''


def stones():
    """Memorial waystones along the Lampwright's last road, from Wren toward the hill."""
    out = []
    # (x, base y, height, width) — nearer = lower and bigger
    for x, y, h, w in (
        (318, 644, 5, 3),
        (292, 650, 7, 4),
        (266, 658, 9, 5),
    ):
        out.append(
            f'<path d="M{x - w / 2:.1f},{y} V{y - h + w / 2:.1f} '
            f'A{w / 2:.1f},{w / 2:.1f} 0 0 1 {x + w / 2:.1f},{y - h + w / 2:.1f} V{y} Z"/>'
        )
    # one tilted, chipped stone off the road
    out.append('<path d="M346,642 L347,638 L349.5,636.5 L351,639 L350.5,642 Z"/>')
    return f'<g filter="url(#ink)" fill="{INK}">{"".join(out)}</g>'


def near_stone():
    """The nearest waystone, just right of Wren, with a carved flame catching the lamp."""
    return f'''
<g filter="url(#ink)" fill="{INK}">
  <path d="M226,652 V622 C226,612 246,612 246,622 V652 Z"/>
</g>
<!-- warm rim on its lamp-side edge -->
<path d="M226.6,650 V623 C227,617 231,614.5 235,614.2" stroke="#f2b24e" stroke-width="0.9" fill="none" opacity="0.6"/>
<!-- the carved flame, worn shallow; its left edge catches the light -->
<path d="M236,640 C232,637 232,632 234.5,628.5 C234.6,631 235.6,632 236.4,632.4 C236,629 237.2,626 239,624.5 C238.6,628 241,631 240.6,635 C240.4,638 238.6,640 236,640 Z"
      fill="#2a1d10" stroke="#f2b24e" stroke-width="0.7" opacity="0.95"/>
'''


def wren():
    """Wren kneeling on the ash ridge, facing right toward the hill, the lamp set low
    on the ash in front of her and cupped in her LEFT hand (the near hand here); red
    ribbon at that wrist; her long knitted scarf trailing behind on the wind."""
    return f'''
<g filter="url(#ink)" fill="{INK}" stroke="{INK}">
  <!-- scarf: long, knitted, lifted on the dawn wind, rippling out behind her -->
  <path d="M116,616 C104,612 94,620 82,626 C70,632 62,624 50,628 C42,631 36,636 30,640 L33,647 C40,643 46,639 53,637 C64,634 72,642 86,635 C98,629 106,624 118,626 Z" stroke="none"/>
  <path d="M30,640 L23,637 M31,643 L23,644 M32,646 L25,650 M33,647 L28,653" stroke-width="1.4" stroke-linecap="round" fill="none"/>
  <!-- second, shorter tail hanging down her back -->
  <path d="M112,622 C106,636 104,650 100,662 L107,664 C110,652 114,638 118,626 Z" stroke="none"/>
  <!-- kneeling body: back bowed toward the lamp -->
  <path d="M100,690 C94,668 98,642 110,626 C118,616 134,614 142,622 C150,632 150,652 146,668 L150,690 Z" stroke="none"/>
  <!-- heel and folded leg on the ash -->
  <path d="M86,690 C88,682 96,678 104,678 L106,690 Z" stroke="none"/>
  <path d="M130,682 L164,688" stroke-width="12" stroke-linecap="round" fill="none"/>
  <!-- scarf wrap at the neck -->
  <path d="M114,618 C122,624 136,624 144,616 L142,610 C134,616 122,616 116,612 Z" stroke="none"/>
  <!-- neck + head, bowed a little toward the lamp -->
  <path d="M128,612 L131,602" stroke-width="9" stroke-linecap="round" fill="none"/>
  <circle cx="132" cy="592" r="15" stroke="none"/>
  <!-- spiky knife-cut tufts -->
  <path d="M118,594 L109,588 L118,585 L113,576 L123,580 L124,571 L130,579 L136,569 L138,579 L146,575 L143,584 L150,587 L145,592 Z" stroke="none"/>
  <!-- arm reaching down and forward to the lamp on the ash -->
  <path d="M138,630 C150,646 158,660 166,668" stroke-width="7.5" stroke-linecap="round" fill="none"/>
</g>
<!-- red ribbon at her left wrist -->
<path d="M160.5,660.5 L163.5,663.5" stroke="#c0222c" stroke-width="2.4" stroke-linecap="round"/>
<path d="M162,664 L158,670" stroke="#d0242f" stroke-width="1.2" stroke-linecap="round"/>
<!-- the lamp, set low on the ash: ring, cap, chimney (dimmed: a coal under ash), brass base -->
<g>
  <circle cx="176" cy="664" r="3" fill="none" stroke="#3a2a14" stroke-width="1.4"/>
  <path d="M170,668 H182 L180,672 H172 Z" fill="#2a1d0e"/>
  <rect x="171" y="672" width="10" height="12" rx="3" fill="url(#chimney)"/>
  <path d="M169,684 H183 L181,690 H171 Z" fill="#7a5320"/>
  <path d="M170,684 H182" stroke="#c99540" stroke-width="0.8"/>
</g>
'''


def svg():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#14171f"/>
    <stop offset="0.45" stop-color="#1a1d24"/>
    <stop offset="0.75" stop-color="#262830"/>
    <stop offset="1" stop-color="#2f2e30"/>
  </linearGradient>
  <linearGradient id="plain" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2a292b"/>
    <stop offset="0.06" stop-color="#232225"/>
    <stop offset="0.3" stop-color="#1c1b1e"/>
    <stop offset="1" stop-color="#121215"/>
  </linearGradient>
  <!-- the hill is ink down to its shoulders, then sinks into the ash at its foot -->
  <linearGradient id="hillfoot" gradientUnits="userSpaceOnUse" x1="0" y1="600" x2="0" y2="662">
    <stop offset="0" stop-color="#0b0a0b"/>
    <stop offset="1" stop-color="#19181b"/>
  </linearGradient>
  <linearGradient id="dawn" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#d98e72" stop-opacity="0"/>
    <stop offset="0.35" stop-color="#e09a74" stop-opacity="0.55"/>
    <stop offset="0.68" stop-color="#f4c47e" stop-opacity="0.9"/>
    <stop offset="1" stop-color="#e09a74" stop-opacity="0.45"/>
  </linearGradient>
  <linearGradient id="dawnrise" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#d99a72" stop-opacity="0.3"/>
    <stop offset="0.4" stop-color="#b98070" stop-opacity="0.12"/>
    <stop offset="1" stop-color="#b98070" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="fadex" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset="0.45" stop-color="#fff" stop-opacity="0.8"/>
    <stop offset="0.75" stop-color="#fff" stop-opacity="1"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0.6"/>
  </linearGradient>
  <mask id="dawnfade" maskUnits="userSpaceOnUse" x="150" y="{HORIZON - 26}" width="450" height="26">
    <rect x="150" y="{HORIZON - 26}" width="450" height="26" fill="url(#fadex)"/>
  </mask>
  <radialGradient id="dawnhaze" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#d0906a" stop-opacity="0.32"/>
    <stop offset="0.5" stop-color="#a06a5a" stop-opacity="0.08"/>
    <stop offset="1" stop-color="#a06a5a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="warm" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff3c4" stop-opacity="0.95"/>
    <stop offset="0.1" stop-color="#ffd476" stop-opacity="0.6"/>
    <stop offset="0.35" stop-color="#e08a2a" stop-opacity="0.26"/>
    <stop offset="0.7" stop-color="#e08a2a" stop-opacity="0.07"/>
    <stop offset="1" stop-color="#d9802a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="chimney" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe7a6"/>
    <stop offset="1" stop-color="#f2a948"/>
  </linearGradient>
  <filter id="ink" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.35" numOctaves="2" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="1.6"/>
  </filter>
  <!-- keeps the halo out of the Ochorus mark (x232-368, y664-747) and the type above: it falls to
       near-black by x~225 at those heights, but still lights the waystone above -->
  <filter id="blur16" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="16"/></filter>
  <mask id="markshade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect width="{W}" height="{H}" fill="#fff"/>
    <ellipse cx="318" cy="722" rx="140" ry="112" fill="#000" filter="url(#blur16)"/>
    <!-- and off the subtitle row and title above her head -->
    <rect x="-40" y="-40" width="680" height="576" fill="#000" filter="url(#blur16)"/>
  </mask>
  <filter id="blur2"><feGaussianBlur stdDeviation="1.6"/></filter>
</defs>

<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars()}

<!-- first hint of dawn: a faint rose haze hugging the horizon, then one thin warm line -->
<ellipse cx="450" cy="{HORIZON}" rx="250" ry="28" fill="url(#dawnhaze)"/>
<rect x="150" y="{HORIZON - 26}" width="450" height="26" fill="url(#dawnrise)" mask="url(#dawnfade)"/>
<rect x="150" y="{HORIZON - 5}" width="450" height="6" fill="url(#dawn)" opacity="0.75" filter="url(#blur2)"/>
<rect x="150" y="{HORIZON - 3.5}" width="450" height="3.5" fill="url(#dawn)" opacity="0.9"/>

<!-- the Burned Country: plain of grey ash -->
<rect x="0" y="{HORIZON}" width="{W}" height="{H - HORIZON}" fill="url(#plain)"/>
<!-- ash drifts stay out of the mark too -->
<g mask="url(#markshade)">{ash_drift(HORIZON + 6, 800)}</g>
<!-- a very low far rise on the left, so the plain has an edge -->
<path d="M0,{HORIZON - 5} C60,{HORIZON - 8} 120,{HORIZON - 4} 200,{HORIZON} L0,{HORIZON} Z" fill="#1c1c20"/>

{hill()}
{stones()}

<!-- the Wren group (ridge, waystone, rim, Wren and her lamp) is drawn about y690 and
     lifted by RAISE, so the flame sits above the mark's full-width strip (y664-747) -->
<g transform="translate(0,-{RAISE})">
<!-- the ash ridge Wren kneels on, from the left, falling away past the stone -->
<g filter="url(#ink)">
  <path d="M-10,694 C60,688 140,686 200,690 C236,694 258,704 278,720 C296,736 306,766 312,800 C316,820 318,840 320,860 L-10,860 Z" fill="{INK}"/>
</g>
{near_stone()}
</g>

<!-- the lamp glow round Wren's hand and lap; its mask keeps it off the mark -->
<circle cx="170" cy="{668 - RAISE}" r="180" fill="url(#warm)" mask="url(#markshade)"/>

<g transform="translate(0,-{RAISE})">
<!-- warm rim along the ridge-top near the lamp -->
<path d="M110,688 C140,686.5 172,686.5 200,690 C208,691 214,692 220,693.5" stroke="#f2b24e" stroke-width="1.1" fill="none" opacity="0.45"/>
{wren()}
</g>
</svg>'''


def page():
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#14171f}} svg{{display:block}}
</style></head><body>{svg()}</body></html>'''


def render():
    from PIL import Image, ImageDraw
    os.makedirs(HERE, exist_ok=True)
    html = os.path.join(HERE, "cinders_cover.html")
    png = os.path.join(HERE, "cinders_cover@2x.png")
    jpg = os.path.join(HERE, "the-hill-of-cinders.jpg")
    with open(html, "w") as f:
        f.write(page())
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={W},{H}",
                    f"--screenshot={png}", "file://" + html],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(png):
        sys.exit("chrome did not write the screenshot")
    im = Image.open(png).convert("RGB").resize((W, H), Image.LANCZOS)
    im.save(jpg, quality=90)
    # mock with bands outlined + per-band brightness report
    mock = im.copy()
    d = ImageDraw.Draw(mock)
    g = im.convert("L")
    for name, (x0, y0, x1, y1) in BANDS.items():
        d.rectangle((x0, y0, x1 - 1, y1), outline=(255, 60, 60))
        px = list(g.crop((x0, y0, x1, y1)).get_flattened_data())
        print(f"{name:9s} mean={sum(px)/len(px):5.1f} max={max(px)}")
    for name, (x0, y0, x1, y1) in REAL_ROWS.items():
        d.rectangle((x0, y0, x1 - 1, y1), outline=(60, 200, 255))
        px = list(g.crop((x0, y0, x1, y1)).get_flattened_data())
        print(f"{name:9s} mean={sum(px)/len(px):5.1f} max={max(px)}")
    mock.save(os.path.join(HERE, "mock.jpg"), quality=90)
    print(jpg)


if __name__ == "__main__":
    render()
