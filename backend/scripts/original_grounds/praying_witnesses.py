"""The ground for A Cloud of Praying Witnesses, Vol. 2: Jesus, Teacher of Prayer.

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

writes OUTDIR/jesus-teacher-of-prayer.html; render it at 2x with headless
Chromium (600x800 window) and downscale with Pillow to the committed jpg, which
is FROZEN by digest in curated_art.ORIGINAL_GROUND.
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


SVG = f'''<!doctype html><html><body style="margin:0;background:#000">
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

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jesus-teacher-of-prayer.html").write_text(SVG)
    print(OUT / "jesus-teacher-of-prayer.html")
