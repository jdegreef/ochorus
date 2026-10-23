#!/usr/bin/env python3
"""Wordless cover ground for *The Glowstone Bargain* (Lamplighters of Gloamhaven, Book 3).

One small WARM gold light (Wren's lamp, low left, on the end of the harbour wall)
against one huge COLD white one (Vaelport, low right on the horizon).

Emits glowstone_cover.html (600x800 SVG), renders it at 2x with headless Chrome,
downsamples with Pillow to the-glowstone-bargain.jpg, and writes mock.jpg with the
cover pipeline's white-type bands outlined.  Rerun:  python lamplighters_3.py OUTDIR
"""
import os
import random
import subprocess
import sys

# Output folder: the first argument, else beside this script.
HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 600, 800
HORIZON = 508

# Type bands the cover pipeline overlays (x0, y0, x1, y1).
BANDS = {
    "byline": (0, 102, 600, 130),
    "title": (70, 284, 530, 463),
    "subtitle": (70, 519, 530, 543),
    "mark": (232, 664, 368, 747),
}

rnd = random.Random(3)


def stars():
    out = []
    for _ in range(26):
        x, y = rnd.uniform(8, 592), rnd.uniform(10, 270)
        if 92 < y < 140:
            continue
        r = rnd.choice([0.5, 0.6, 0.7, 0.9])
        o = rnd.uniform(0.18, 0.45)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#dfe4ea" opacity="{o:.2f}"/>')
    return "\n".join(out)


def city():
    """Tiered towers of Vaelport, x 392..600, base on the horizon."""
    rows = []
    # (x0, x1, base height above horizon, jitter, tower width range)
    tiers = [
        (398, 610, 8, 3, (5, 11), "#c3ced6"),
        (420, 610, 15, 3, (5, 10), "#d3dce3"),
        (448, 610, 22, 3, (4, 9), "#e0e7ec"),
        (480, 606, 30, 3, (4, 8), "#ebf0f3"),
        (508, 600, 38, 2, (4, 7), "#f5f8fa"),
        (532, 588, 46, 2, (3, 6), "#ffffff"),
    ]
    for x0, x1, h, jit, (wmin, wmax), col in tiers:
        x = x0
        parts = []
        while x < x1:
            w = rnd.randint(wmin, wmax)
            th = h + rnd.uniform(-jit, jit)
            top = HORIZON - th
            # nothing in the title band (x<532 must stay below y466)
            cap = 466 if x + w < 534 else 446
            top = max(top, cap)
            kind = rnd.random()
            spire = top - w * 1.4
            if kind < 0.18:  # dome
                parts.append(f'M{x},{HORIZON} V{top+w/2:.1f} A{w/2:.1f},{w/2:.1f} 0 0 1 {x+w},{top+w/2:.1f} V{HORIZON} Z')
            elif kind < 0.40 and spire >= cap:
                parts.append(f'M{x},{HORIZON} V{top:.1f} L{x+w/2:.1f},{spire:.1f} L{x+w},{top:.1f} V{HORIZON} Z')
            else:
                parts.append(f'M{x},{HORIZON} V{top:.1f} H{x+w} V{HORIZON} Z')
            x += w + rnd.choice([0, 0, 1])
        rows.append(f'<path d="{" ".join(parts)}" fill="{col}"/>')
    # the Glass Palace's high spire and two flanking towers, all right of the title band
    rows.append(f'<path d="M550,{HORIZON-40} V{HORIZON-52} L554,{HORIZON-58} L558,{HORIZON-52} V{HORIZON-40} Z" fill="#ffffff"/>')
    rows.append(f'<path d="M551.5,{HORIZON-54} L554,{HORIZON-64} L556.5,{HORIZON-54} Z" fill="#ffffff"/>')
    for tx, tt in ((536, 40), (586, 36)):
        rows.append(f'<path d="M{tx-2.5},{HORIZON-28} V{HORIZON-tt} L{tx},{HORIZON-tt-6} L{tx+2.5},{HORIZON-tt} V{HORIZON-28} Z" fill="#ffffff"/>')
    # thin cold "windows": darker seams between tiers so it reads as tiers, not a blob
    shapes = "\n".join(rows)
    seams = [f'<clipPath id="cityclip">{shapes}</clipPath><g clip-path="url(#cityclip)">']
    for y in (HORIZON - 9, HORIZON - 16, HORIZON - 24, HORIZON - 31, HORIZON - 38):
        seams.append(f'<line x1="398" y1="{y}" x2="600" y2="{y}" stroke="#9fb0bc" stroke-width="0.6" opacity="0.55"/>')
    for _ in range(60):  # faint vertical wall-seams
        x = rnd.uniform(400, 600)
        seams.append(f'<rect x="{x:.1f}" y="{HORIZON-48}" width="0.5" height="48" fill="#aebcc6" opacity="0.35"/>')
    seams.append("</g>")
    return shapes + "\n" + "\n".join(seams)


def reflection():
    out = []
    y = HORIZON + 2
    i = 0
    while y < 640:
        depth = (y - HORIZON) / (640 - HORIZON)
        n = rnd.randint(2, 4)
        for _ in range(n):
            cx = rnd.uniform(440, 590)
            # keep the subtitle band (x<530) quiet: shove streaks right there
            if 515 < y < 547:
                cx = rnd.uniform(520, 595)
            w = rnd.uniform(6, 30) * (1 - 0.5 * depth)
            o = (0.75 - 0.7 * depth) * rnd.uniform(0.5, 1.0)
            if 515 < y < 547:
                o *= 0.45
            out.append(f'<rect x="{cx-w/2:.1f}" y="{y:.1f}" width="{w:.1f}" height="1.3" fill="#e8eef2" opacity="{o:.2f}"/>')
        y += 2.2 + depth * 6
        i += 1
    return "\n".join(out)


def water_lines():
    out = []
    y = HORIZON + 6
    while y < 800:
        d = (y - HORIZON) / 300
        x0 = rnd.uniform(-40, 300)
        w = rnd.uniform(60, 260)
        out.append(f'<rect x="{x0:.0f}" y="{y:.1f}" width="{w:.0f}" height="0.8" fill="#8a96a3" opacity="{0.07:.2f}"/>')
        y += 5 + d * 14
    return "\n".join(out)


def wren():
    """Wren seated on the end of the wall, facing right toward the city, knees up,
    lamp held out in her LEFT hand (the near hand here), red ribbon at that wrist."""
    ink = "#0b0a0b"
    return f'''
<g filter="url(#ink)" fill="{ink}" stroke="{ink}">
  <!-- back / coat, seated -->
  <path d="M96,690 C88,668 90,640 100,624 C108,612 124,610 134,618 C142,626 144,646 142,664 L150,690 Z" stroke="none"/>
  <!-- coat tail on the stone -->
  <path d="M84,690 C88,680 94,676 102,676 L104,690 Z" stroke="none"/>
  <!-- thigh + shin, knees up -->
  <path d="M120,676 L166,656" stroke-width="15" stroke-linecap="round" fill="none"/>
  <path d="M166,656 L176,690" stroke-width="11" stroke-linecap="round" fill="none"/>
  <path d="M170,690 L188,690" stroke-width="7" stroke-linecap="round" fill="none"/>
  <!-- neck + head -->
  <path d="M118,614 L121,602" stroke-width="9" stroke-linecap="round" fill="none"/>
  <circle cx="121" cy="590" r="15" stroke="none"/>
  <!-- spiky knife-cut tufts -->
  <path d="M107,590 L99,583 L108,582 L104,573 L113,578 L114,569 L120,577 L126,567 L127,577 L135,573 L132,582 L139,585 L134,590 Z" stroke="none"/>
  <!-- arm reaching forward to the lamp -->
  <path d="M128,628 C140,640 150,640 160,634" stroke-width="7.5" stroke-linecap="round" fill="none"/>
</g>
<!-- red ribbon at her left wrist -->
<path d="M153,634.5 L157,639.5" stroke="#d0242f" stroke-width="3" stroke-linecap="round"/>
<path d="M155,638 L152,644" stroke="#d0242f" stroke-width="1.2" stroke-linecap="round"/>
<!-- the lamp: ring, cap, chimney, brass base -->
<g>
  <circle cx="170" cy="616" r="3" fill="none" stroke="#3a2a14" stroke-width="1.4"/>
  <path d="M164,620 H176 L174,624 H166 Z" fill="#2a1d0e"/>
  <rect x="165" y="624" width="10" height="14" rx="3" fill="url(#chimney)"/>
  <path d="M163,638 H177 L175,644 H165 Z" fill="#7a5320"/>
  <path d="M164,638 H176" stroke="#c99540" stroke-width="0.8"/>
</g>
'''


def svg():
    global CITY
    CITY = city()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#14171f"/>
    <stop offset="0.45" stop-color="#1a1d24"/>
    <stop offset="0.75" stop-color="#262830"/>
    <stop offset="1" stop-color="#2f2e30"/>
  </linearGradient>
  <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#22252c"/>
    <stop offset="0.35" stop-color="#181a20"/>
    <stop offset="1" stop-color="#0e0f13"/>
  </linearGradient>
  <radialGradient id="coldglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>
    <stop offset="0.35" stop-color="#e8eef2" stop-opacity="0.22"/>
    <stop offset="0.7" stop-color="#b9c6cf" stop-opacity="0.07"/>
    <stop offset="1" stop-color="#b9c6cf" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="warm" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff3c4" stop-opacity="0.95"/>
    <stop offset="0.1" stop-color="#ffd476" stop-opacity="0.6"/>
    <stop offset="0.35" stop-color="#e08a2a" stop-opacity="0.24"/>
    <stop offset="0.7" stop-color="#e08a2a" stop-opacity="0.06"/>
    <stop offset="1" stop-color="#e08a2a" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="chimney" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff3c4"/>
    <stop offset="1" stop-color="#ffd476"/>
  </linearGradient>
  <linearGradient id="beam" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0" stop-color="#e8eef2" stop-opacity="0.32"/>
    <stop offset="1" stop-color="#e8eef2" stop-opacity="0"/>
  </linearGradient>
  <filter id="ink" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.35" numOctaves="2" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="1.6"/>
  </filter>
  <filter id="blur6"><feGaussianBlur stdDeviation="6"/></filter>
  <filter id="blur2"><feGaussianBlur stdDeviation="1.6"/></filter>
</defs>

<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars()}
<!-- cold haze low on the horizon, right; capped so nothing climbs past ~y440 -->
<ellipse cx="510" cy="{HORIZON}" rx="190" ry="62" fill="url(#coldglow)"/>

<!-- far headland, left -->
<path d="M0,{HORIZON-12} C60,{HORIZON-20} 120,{HORIZON-16} 190,{HORIZON-8} C250,{HORIZON-3} 320,{HORIZON-2} 380,{HORIZON} L0,{HORIZON} Z" fill="#1b1d22"/>

<!-- far quay: glowstone dots marching toward the city -->
{"".join(f'<circle cx="{x}" cy="{HORIZON-2}" r="1.1" fill="#e8eef2" opacity="0.7"/>' for x in range(300, 372, 12))}
<!-- sea -->
<rect x="0" y="{HORIZON}" width="{W}" height="{H-HORIZON}" fill="url(#sea)"/>
{water_lines()}
<g filter="url(#blur2)">{reflection()}</g>
{reflection()}

<!-- lighthouse on its rock, left end of the city, short low cold beam -->
<path d="M368,{HORIZON+2} C374,{HORIZON-6} 392,{HORIZON-6} 398,{HORIZON+2} Z" fill="#0b0a0b"/>
<polygon points="376,{HORIZON-28} 360,{HORIZON-24} 290,{HORIZON-14} 290,{HORIZON-4} 360,{HORIZON-20}" fill="url(#beam)"/>
<path d="M379,{HORIZON-3} L381,{HORIZON-26} H387 L389,{HORIZON-3} Z" fill="#d6dee4"/>
<rect x="380" y="{HORIZON-32}" width="8" height="6" fill="#ffffff"/>
<path d="M379,{HORIZON-32} L384,{HORIZON-37} L389,{HORIZON-32} Z" fill="#c9d3da"/>
<circle cx="384" cy="{HORIZON-29}" r="7" fill="#ffffff" opacity="0.35" filter="url(#blur2)"/>

<!-- Vaelport -->
<g filter="url(#blur6)" opacity="0.8">{CITY.split("<clipPath")[0]}</g>
{CITY}

<!-- harbour wall from the left, ending under Wren -->
<g filter="url(#ink)">
  <path d="M-10,692 L196,688 C204,688 208,692 208,698 L212,800 L-10,800 Z" fill="#0b0a0b"/>
</g>

<!-- stone courses on the wall face, caught by the lamp -->
<g stroke="#3a2a18" stroke-width="0.7" opacity="0.32" fill="none">
  <path d="M0,712 L209,710"/><path d="M0,736 L210,734"/><path d="M0,760 L211,758"/>
  <path d="M60,692 V712 M140,690 V710 M30,712 V736 M100,712 V736 M180,711 V735 M70,736 V760 M150,735 V759"/>
</g>
<!-- end face of the wall: warm rim where the lamp reaches it -->
<path d="M207,694 L211,780" stroke="#f2b24e" stroke-width="1" opacity="0.35"/>
<!-- warm lamp glow -->
<circle cx="168" cy="634" r="175" fill="url(#warm)"/>
<!-- warm rim along the wall top and a little warm on the water at its foot -->
<path d="M40,690.5 L196,688" stroke="#f2b24e" stroke-width="1.2" opacity="0.55"/>
<g opacity="0.5">
  <rect x="214" y="706" width="16" height="1.2" fill="#ffd476" opacity="0.5"/>
  <rect x="212" y="716" width="10" height="1.2" fill="#e08a2a" opacity="0.4"/>
</g>

{wren()}
</svg>'''


def page():
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#14171f}} svg{{display:block}}
</style></head><body>{svg()}</body></html>'''


def render():
    from PIL import Image, ImageDraw
    html = os.path.join(HERE, "glowstone_cover.html")
    png = os.path.join(HERE, "glowstone_cover@2x.png")
    jpg = os.path.join(HERE, "the-glowstone-bargain.jpg")
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
    mock.save(os.path.join(HERE, "mock.jpg"), quality=90)
    print(jpg)


if __name__ == "__main__":
    render()
