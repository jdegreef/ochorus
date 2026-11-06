"""The grounds for A Cloud of Praying Witnesses, one per volume.

The series shares one scene, the hills under a night sky with the light coming
up a little further in each volume: Vol. 1 under the stars, Vol. 2 at first
light, Vol. 3 at sunrise. Every ground keeps the upper two-thirds dark for the
white title, its subject below y=470 and its ridge tops above y=519 (the
subtitle band), and the mark zone over dark foreground. No likeness.

    python3 backend/scripts/original_grounds/praying_witnesses.py OUTDIR [SLUG ...]

writes OUTDIR/<slug>.html for each slug (all three with none); render each at 2x
with headless Chromium (600x800 window) and downscale with Pillow to the
committed jpg, which is FROZEN by digest in curated_art.ORIGINAL_GROUND.

Vol. 2: Jesus, Teacher of Prayer.

Drawn 2026-11-04 because the session could reach no collection host (the museum
APIs, Commons and Wikidata were all blocked), so the volume wears an Original
ground rather than a CURATED painting. "Rising up a great while before day, He
went out, and departed into a solitary place, and there prayed" (Mark 1:35): the
Galilean hills before dawn under a deep sky, the first light low behind the far
ridge, and on the near ridge, low left, one figure kneeling in prayer. The upper
two-thirds stay night-dark for the white title; the glow sits under the subtitle
band, behind a ridge whose top edge never drops below y=500, and the mark zone is
over the dark foreground. No likeness.

    python3 backend/scripts/original_grounds/praying_witnesses.py OUTDIR

Vol. 1: The Prayers Jesus Learned. "Look up into the sky and try counting the
stars, if you can" (Genesis 15:5): a night thick with stars over low desert
hills, no dawn yet, only a violet haze on the far horizon; on the near ridge,
low left, a tent with a lamp at its door and Abram standing beside it, face
lifted to the sky.

Vol. 3: Devoted to Prayer. The morning of Pentecost over Jerusalem: the sun's
glow broad on the horizon behind the city, the sky still deep blue above, and
on the near ridge the flat roofs, walls and towers of the city in silhouette,
one upper room's window lit (Acts 1:13-14, 2:1).
"""
import pathlib
import random
import sys

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()


def stars(seed, n=90, ymax=420):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = r.uniform(6, 594), r.uniform(6, ymax)
        out.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.choice([0.7, 0.9, 1.1, 1.4]):.1f}" '
            f'fill="#fff" opacity="{r.uniform(.25, .75) * (1 - y / (ymax * 1.6)):.2f}"/>'
        )
    return "".join(out)


def ridge(points, fill):
    d = "M0 800 L" + " L".join(f"{x} {y}" for x, y in points) + " L600 800 Z"
    return f'<path d="{d}" fill="{fill}"/>'


VOL2 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#070b18"/><stop offset=".38" stop-color="#0e1730"/>
  <stop offset=".55" stop-color="#1b2645"/><stop offset=".62" stop-color="#3a3550"/>
  <stop offset=".66" stop-color="#6b4a4e"/><stop offset="1" stop-color="#6b4a4e"/>
 </linearGradient>
 <radialGradient id="dawn" cx="400" cy="520" r="150" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#f0b46a" stop-opacity=".85"/>
  <stop offset=".35" stop-color="#c97a4e" stop-opacity=".45"/>
  <stop offset="1" stop-color="#6b4a4e" stop-opacity="0"/>
 </radialGradient>
 <pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.035"/>
  <circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.08"/>
 </pattern>
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#dawn)"/>
{stars(7)}
<circle cx="118" cy="96" r="1.9" fill="#fff" opacity=".9"/>
{ridge([(0, 486), (70, 478), (150, 482), (230, 470), (300, 476), (360, 484), (430, 474), (520, 480), (600, 472)], "#2a2639")}
{ridge([(0, 500), (60, 496), (130, 492), (190, 498), (260, 503), (340, 500), (420, 494), (500, 499), (600, 495)], "#151522")}
{ridge([(0, 512), (90, 506), (170, 503), (240, 509), (330, 514), (430, 510), (520, 504), (600, 508)], "#07080e")}
<g fill="#07080e">
 <path d="M133 505 C134 495 138 487 145 482 C149 479 155 478 158 481 C161 484 162 489 161 494 L171 499 C174 501 173 505 169 505 Z"/>
 <circle cx="156.5" cy="477" r="5.6"/>
 <path d="M156 486 C160 484 164 483 166 484 C167 486 166 488 163 489 C160 490 157 490 156 489 Z"/>
</g>
<g fill="#07080e">
 <path d="M468 506 L470 490 L472 506 Z"/>
 <ellipse cx="470" cy="486" rx="15" ry="8"/><ellipse cx="461" cy="490" rx="9" ry="5"/><ellipse cx="480" cy="489" rx="10" ry="5"/>
</g>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

GRAIN = '''<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.035"/>
  <circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.08"/>
 </pattern>'''

VOL1 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#04060f"/><stop offset=".40" stop-color="#0a1126"/>
  <stop offset=".56" stop-color="#151c38"/><stop offset=".62" stop-color="#262244"/>
  <stop offset="1" stop-color="#262244"/>
 </linearGradient>
 <radialGradient id="haze" cx="300" cy="520" r="260" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#4a3a63" stop-opacity=".55"/>
  <stop offset="1" stop-color="#262244" stop-opacity="0"/>
 </radialGradient>
 <radialGradient id="lamp" cx="95" cy="503" r="12" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#f3b866" stop-opacity=".6"/>
  <stop offset="1" stop-color="#f3b866" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#haze)"/>
{stars(15, n=230, ymax=470)}
{stars(16, n=40, ymax=300)}
<circle cx="452" cy="88" r="2.0" fill="#fff" opacity=".95"/>
<circle cx="214" cy="152" r="1.8" fill="#fff" opacity=".9"/>
<circle cx="347" cy="236" r="1.7" fill="#fff" opacity=".85"/>
{ridge([(0, 488), (90, 482), (170, 486), (260, 476), (340, 482), (420, 478), (510, 484), (600, 479)], "#1c1a2e")}
{ridge([(0, 500), (80, 497), (150, 494), (230, 499), (310, 503), (390, 499), (470, 495), (540, 500), (600, 497)], "#100f1c")}
{ridge([(0, 511), (100, 506), (190, 505), (270, 510), (360, 513), (450, 509), (530, 505), (600, 508)], "#06070d")}
<rect width="600" height="800" fill="url(#lamp)"/>
<g fill="#06070d">
 <path d="M58 507 L82 474 L106 507 Z"/>
 <path d="M82 474 L88 470 L84 476 Z"/>
 <path d="M124 507 L125 489 C125 485 127 483 130 483 C133 483 135 485 135 489 L136 507 Z"/>
 <circle cx="130.5" cy="477.5" r="5"/>
 <path d="M128 474 C130 471 134 471 136 473 L134 476 Z"/>
</g>
<path d="M92 507 L96 494 L100 507 Z" fill="#f3b866" opacity=".55"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

VOL3 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#08102a"/><stop offset=".36" stop-color="#132046"/>
  <stop offset=".52" stop-color="#2a3160"/><stop offset=".58" stop-color="#5a4566"/>
  <stop offset=".63" stop-color="#9a6458"/><stop offset="1" stop-color="#9a6458"/>
 </linearGradient>
 <radialGradient id="sun" cx="300" cy="512" r="165" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ffd08a" stop-opacity=".9"/>
  <stop offset=".3" stop-color="#e8955c" stop-opacity=".45"/>
  <stop offset="1" stop-color="#9a6458" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
{stars(23, n=45, ymax=260)}
{ridge([(0, 492), (120, 486), (220, 490), (300, 484), (390, 489), (480, 485), (600, 490)], "#4a3346")}
<g fill="#0a0910">
 <path d="M0 800 L0 506 L40 506 L40 496 L58 496 L58 506 L96 506 L96 490 L112 490 L112 482 L120 482 L120 490 L136 490
  L136 500 L170 500 L170 494 L204 494 L204 502 L232 502 L232 488 L262 488 L262 497 L300 497 L300 491 L336 491 L336 499
  L362 499 L362 476 L372 476 L372 470 L382 470 L382 476 L392 476 L392 499 L428 499 L428 492 L470 492 L470 501 L502 501
  L502 495 L536 495 L536 504 L566 504 L566 498 L600 498 L600 800 Z"/>
</g>
<rect x="241" y="493" width="5" height="5" fill="#f6c06e" opacity=".95"/>
<rect x="0" y="512" width="600" height="288" fill="#0a0910"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

SCENES = {
    "the-prayers-jesus-learned": VOL1,
    "jesus-teacher-of-prayer": VOL2,
    "devoted-to-prayer": VOL3,
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[2:] or SCENES:
        (OUT / f"{slug}.html").write_text(SCENES[slug])
        print(OUT / f"{slug}.html")
