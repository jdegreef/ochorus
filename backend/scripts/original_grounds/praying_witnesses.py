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

Vol. 4: Faithful unto Death. Full morning over the Egyptian desert, where the
monks of the fourth century went out to pray: the sun just clear of the far
dunes, a flat-topped mountain in silhouette like Antony's, and on the near
ground, low left, a domed mud-brick cell with a small cross and a lit doorway,
a palm beside it (Hosea 2:14).

Vol. 5: Seven Times a Day. A clear morning over the hills: the sun risen low
on the left, and on the near ridge, low right, a monastery church with its bell
tower and cross, a cloister wall and two cypresses, its windows lit for the
morning office (Psalm 119:164).

Vol. 6: A Mighty Fortress. Full morning, the sun clear of the far ridge on the
right; on the near hill, low left, a walled castle with its keep and a corner
tower, one window lit in the keep where a man sits up translating and praying
(Psalm 46:1). No particular castle.

Vol. 7: The Fire on the Altar. A bright morning, the sun clear of the far hills
on the left; on the near ridge, right, a village: a plain meeting hall with a
small bell turret and a row of houses, windows lit; on the hill to the far left
a small fire that is kept burning (Leviticus 6:13).

Vol. 8: Open Your Mouth Wide. Late morning over the sea, the sun well up on the
right and its light on the water; a sailing ship putting out to sea under its
sails, and on the shore, low left, a small chapel with a cross and a lit window:
the century when the church sent its missionaries out (Psalm 81:10).
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

VOL4 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#0b1730"/><stop offset=".34" stop-color="#18294e"/>
  <stop offset=".50" stop-color="#3a3f62"/><stop offset=".57" stop-color="#8a6258"/>
  <stop offset=".62" stop-color="#d0925a"/><stop offset="1" stop-color="#d0925a"/>
 </linearGradient>
 <radialGradient id="sun" cx="430" cy="486" r="190" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ffe2a8" stop-opacity=".95"/>
  <stop offset=".22" stop-color="#f2a865" stop-opacity=".5"/>
  <stop offset="1" stop-color="#d0925a" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
<circle cx="430" cy="486" r="17" fill="#fff1cf" opacity=".95"/>
{ridge([(0, 494), (110, 490), (210, 493), (330, 489), (450, 492), (600, 488)], "#7a5048")}
{ridge([(0, 470), (40, 470), (52, 482), (96, 482), (104, 474), (150, 474), (166, 492), (250, 497), (340, 499),
        (470, 499), (530, 490), (546, 478), (600, 478)], "#2c1c22")}
<g fill="#0c090c">
 <path d="M0 800 L0 506 L60 503 L130 506 L220 509 L330 511 L430 508 L520 505 L600 507 L600 800 Z"/>
 <path d="M84 506 L84 494 C84 486 90 481 98 481 C106 481 112 486 112 494 L112 506 Z"/>
 <rect x="97" y="473" width="2" height="9"/><rect x="94.5" y="476" width="7" height="2"/>
 <path d="M152 507 C153 496 154 486 152 476 L155 476 C157 486 157 496 156 507 Z"/>
 <path d="M153 476 C146 470 138 470 132 474 C140 472 147 473 153 477 Z"/>
 <path d="M154 476 C160 469 169 468 175 472 C167 471 160 473 155 477 Z"/>
 <path d="M153 475 C150 467 144 462 138 461 C144 465 149 470 152 476 Z"/>
 <path d="M155 475 C159 467 165 463 171 463 C165 466 160 470 156 476 Z"/>
</g>
<path d="M95 506 L95 498 C95 496 96.5 495 98 495 C99.5 495 101 496 101 498 L101 506 Z" fill="#f2b66a" opacity=".7"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

VOL5 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#10203f"/><stop offset=".32" stop-color="#1f3561"/>
  <stop offset=".48" stop-color="#4a5a82"/><stop offset=".56" stop-color="#a08470"/>
  <stop offset=".61" stop-color="#dcae6e"/><stop offset="1" stop-color="#dcae6e"/>
 </linearGradient>
 <radialGradient id="sun" cx="150" cy="478" r="210" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fff0c4" stop-opacity=".95"/>
  <stop offset=".2" stop-color="#f4bd72" stop-opacity=".5"/>
  <stop offset="1" stop-color="#dcae6e" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
<circle cx="150" cy="474" r="19" fill="#fff6dc" opacity=".95"/>
{ridge([(0, 490), (90, 486), (180, 491), (270, 484), (360, 488), (470, 482), (600, 487)], "#6e5a64")}
{ridge([(0, 500), (80, 497), (170, 500), (260, 496), (330, 490), (400, 484), (470, 482), (540, 488), (600, 492)], "#2e2633")}
<g fill="#0b0a10">
 <path d="M0 800 L0 508 L90 505 L200 508 L300 507 L360 504 L420 502 L520 502 L600 504 L600 800 Z"/>
 <rect x="404" y="490" width="84" height="13"/>
 <path d="M400 492 L446 476 L492 492 Z"/>
 <rect x="468" y="472" width="14" height="22"/>
 <path d="M466 474 L475 465 L484 474 Z"/>
 <rect x="474" y="456" width="2" height="10"/><rect x="471" y="459" width="8" height="2"/>
 <rect x="378" y="494" width="28" height="9"/><rect x="486" y="494" width="32" height="9"/>
 <path d="M352 505 C349 494 350 482 354 471 C358 482 359 494 356 505 Z"/>
 <path d="M532 503 C529 492 530 480 534 470 C538 480 539 492 536 503 Z"/>
</g>
<rect x="473" y="478" width="4" height="6" fill="#f2b66a" opacity=".8"/>
<rect x="422" y="494" width="4" height="5" fill="#f2b66a" opacity=".6"/>
<rect x="440" y="494" width="4" height="5" fill="#f2b66a" opacity=".6"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

VOL6 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#12254a"/><stop offset=".30" stop-color="#22406e"/>
  <stop offset=".46" stop-color="#4f6b92"/><stop offset=".55" stop-color="#a49a8a"/>
  <stop offset=".61" stop-color="#e2bf82"/><stop offset="1" stop-color="#e2bf82"/>
 </linearGradient>
 <radialGradient id="sun" cx="430" cy="470" r="220" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fff4d2" stop-opacity=".95"/>
  <stop offset=".2" stop-color="#f6c97e" stop-opacity=".5"/>
  <stop offset="1" stop-color="#e2bf82" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
<circle cx="430" cy="466" r="20" fill="#fffbe8" opacity=".95"/>
{ridge([(0, 489), (110, 484), (210, 489), (320, 483), (430, 488), (520, 484), (600, 488)], "#6d6470")}
{ridge([(0, 497), (60, 492), (110, 486), (170, 484), (220, 490), (300, 498), (400, 499), (500, 495), (600, 498)], "#2c2836")}
<g fill="#0b0a10">
 <path d="M0 800 L0 504 L40 500 L80 494 L120 490 L170 489 L210 493 L250 500 L330 506 L450 507 L600 505 L600 800 Z"/>
 <rect x="96" y="478" width="90" height="14"/>
 <rect x="96" y="474" width="8" height="5"/><rect x="110" y="474" width="8" height="5"/><rect x="124" y="474" width="8" height="5"/>
 <rect x="150" y="474" width="8" height="5"/><rect x="164" y="474" width="8" height="5"/><rect x="178" y="474" width="8" height="5"/>
 <rect x="134" y="462" width="18" height="18"/>
 <rect x="132" y="458" width="5" height="5"/><rect x="140.5" y="458" width="5" height="5"/><rect x="149" y="458" width="5" height="5"/>
 <rect x="84" y="468" width="14" height="24"/><path d="M82 470 L91 458 L100 470 Z"/>
</g>
<rect x="141" y="467" width="4" height="6" fill="#f2b66a" opacity=".85"/>
<rect x="114" y="482" width="3" height="5" fill="#f2b66a" opacity=".6"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

VOL7 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#142a52"/><stop offset=".30" stop-color="#26497a"/>
  <stop offset=".45" stop-color="#5677a0"/><stop offset=".54" stop-color="#a9a594"/>
  <stop offset=".60" stop-color="#e6c78c"/><stop offset="1" stop-color="#e6c78c"/>
 </linearGradient>
 <radialGradient id="sun" cx="190" cy="462" r="230" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fff6da" stop-opacity=".95"/>
  <stop offset=".2" stop-color="#f7cf88" stop-opacity=".5"/>
  <stop offset="1" stop-color="#e6c78c" stop-opacity="0"/>
 </radialGradient>
 <radialGradient id="fire" cx="62" cy="478" r="16" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ffb060" stop-opacity=".9"/>
  <stop offset="1" stop-color="#ffb060" stop-opacity="0"/>
 </radialGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
<circle cx="190" cy="458" r="21" fill="#fffbea" opacity=".95"/>
{ridge([(0, 488), (100, 483), (200, 487), (300, 481), (410, 486), (510, 482), (600, 486)], "#6f6a76")}
{ridge([(0, 484), (40, 481), (80, 483), (130, 492), (220, 498), (320, 497), (420, 493), (520, 496), (600, 494)], "#2d2a38")}
<rect width="600" height="800" fill="url(#fire)"/>
<g fill="#0b0a10">
 <path d="M0 800 L0 507 L120 507 L230 509 L330 506 L420 503 L520 504 L600 506 L600 800 Z"/>
 <rect x="360" y="486" width="62" height="18"/><path d="M356 488 L391 474 L426 488 Z"/>
 <rect x="386" y="462" width="10" height="14"/><path d="M384 464 L391 455 L398 464 Z"/>
 <rect x="432" y="490" width="22" height="14"/><path d="M430 491 L443 482 L456 491 Z"/>
 <rect x="462" y="492" width="22" height="12"/><path d="M460 493 L473 484 L486 493 Z"/>
 <rect x="330" y="492" width="22" height="12"/><path d="M328 493 L341 484 L354 493 Z"/>
 <rect x="494" y="494" width="20" height="10"/><path d="M492 495 L504 487 L516 495 Z"/>
</g>
<path d="M58 482 L62 472 L66 482 Z" fill="#ffcf7a" opacity=".95"/>
<path d="M60 482 L62 476 L64 482 Z" fill="#fff0c0"/>
<rect x="372" y="492" width="4" height="6" fill="#f2b66a" opacity=".75"/>
<rect x="388" y="492" width="4" height="6" fill="#f2b66a" opacity=".75"/>
<rect x="404" y="492" width="4" height="6" fill="#f2b66a" opacity=".75"/>
<rect x="441" y="495" width="3" height="5" fill="#f2b66a" opacity=".6"/>
<rect x="471" y="496" width="3" height="4" fill="#f2b66a" opacity=".6"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

VOL8 = f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#16305a"/><stop offset=".30" stop-color="#2a5386"/>
  <stop offset=".45" stop-color="#5c82ad"/><stop offset=".54" stop-color="#b0b2a6"/>
  <stop offset=".60" stop-color="#e9d09a"/><stop offset="1" stop-color="#e9d09a"/>
 </linearGradient>
 <radialGradient id="sun" cx="400" cy="440" r="240" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fff8e2" stop-opacity=".95"/>
  <stop offset=".2" stop-color="#f8d898" stop-opacity=".5"/>
  <stop offset="1" stop-color="#e9d09a" stop-opacity="0"/>
 </radialGradient>
 <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#8f8f98"/><stop offset=".25" stop-color="#4a4d60"/>
  <stop offset="1" stop-color="#1d1f2c"/>
 </linearGradient>
 {GRAIN}
</defs>
<rect width="600" height="800" fill="url(#sky)"/>
<rect width="600" height="800" fill="url(#sun)"/>
<circle cx="400" cy="440" r="22" fill="#fffcee" opacity=".95"/>
<rect x="0" y="493" width="600" height="20" fill="url(#sea)"/>
<ellipse cx="400" cy="499" rx="70" ry="5" fill="#f6e6b8" opacity=".35"/>
<ellipse cx="400" cy="505" rx="38" ry="3" fill="#f6e6b8" opacity=".25"/>
<g fill="#0b0a10">
 <path d="M408 494 L452 494 L446 501 L414 501 Z"/>
 <rect x="429" y="458" width="2" height="36"/><rect x="416" y="466" width="2" height="28"/>
 <path d="M431 460 L431 490 L446 490 Z"/><path d="M429 462 L429 490 L420 490 Z"/>
 <path d="M418 468 L418 490 L410 490 Z"/>
 <path d="M0 800 L0 500 L60 497 L120 498 L170 503 L210 512 L600 512 L600 800 Z"/>
 <rect x="62" y="486" width="30" height="12"/><path d="M58 488 L77 477 L96 488 Z"/>
 <rect x="76" y="466" width="2" height="12"/><rect x="73" y="469" width="8" height="2"/>
</g>
<rect x="71" y="490" width="4" height="5" fill="#f2b66a" opacity=".7"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

SCENES = {
    "the-prayers-jesus-learned": VOL1,
    "jesus-teacher-of-prayer": VOL2,
    "devoted-to-prayer": VOL3,
    "faithful-unto-death": VOL4,
    "seven-times-a-day": VOL5,
    "a-mighty-fortress": VOL6,
    "the-fire-on-the-altar": VOL7,
    "open-your-mouth-wide": VOL8,
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[2:] or SCENES:
        (OUT / f"{slug}.html").write_text(SCENES[slug])
        print(OUT / f"{slug}.html")
