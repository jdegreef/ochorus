"""The Originals series grounds of 2026-10-13: Real Questions 2-3, They Were Young
3-4, Tell Me the Story 1-7 and The Big Story.

Kept so a later volume can match its series exactly (Book 1 of Real Questions and
They Were Young had no committed source and had to be re-measured from pixels).
Each ground is an inline SVG rendered by headless Chrome at 2x and downscaled;
the committed jpg is FROZEN by digest in curated_art.ORIGINAL_GROUND, so a redraw
here only ships with a deliberate new digest.

    python3 backend/scripts/original_grounds/originals_series.py OUTDIR [slug ...]

Then copy OUTDIR/<slug>.jpg to frontend/static/covers/art/ and follow the
ORIGINAL_GROUND ship steps in .claude/skills/level-up-cover.
"""
import pathlib
import random
import subprocess
import sys

from PIL import Image

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def page(body, defs=""):
    return f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs><pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.04"/><circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.08"/></pattern>{defs}</defs>
{body}
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

def sky(top, mid, bot, id="sky"):
    return (f'<linearGradient id="{id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
            f'<stop offset=".5" stop-color="{mid}"/><stop offset="1" stop-color="{bot}"/></linearGradient>',
            f'<rect width="600" height="800" fill="url(#{id})"/>')

def stars(seed, n=70, ymax=640, op=.7):
    r = random.Random(seed)
    return "".join(f'<circle cx="{r.uniform(5,595):.0f}" cy="{r.uniform(5,ymax):.0f}" r="{r.choice([0.8,1,1.2,1.5]):.1f}" fill="#fff" opacity="{r.uniform(.3,op):.2f}"/>' for _ in range(n))

# ── series marks, at Book 1's geometry ──────────────────────────────────────
def lantern(c):
    return f'''<path d="M252 216 A48 48 0 0 1 348 216" stroke="{c}" stroke-width="14" fill="none"/>
<path d="M230 232 L370 232 L361 268 L239 268 Z" fill="{c}"/>
<rect x="236" y="268" width="15" height="244" fill="{c}"/><rect x="296" y="268" width="8" height="244" fill="{c}"/><rect x="348" y="268" width="15" height="244" fill="{c}"/>
<path d="M229 512 L371 512 L363 548 L237 548 Z" fill="{c}"/>'''

def small_lantern(cx=300, cy=628):
    return f'''<circle cx="{cx}" cy="{cy}" r="45" fill="#f5c862" opacity=".16"/><circle cx="{cx}" cy="{cy}" r="30" fill="#f5c862" opacity=".12"/>
<rect x="{cx-12}" y="{cy-18}" width="24" height="36" rx="2" fill="none" stroke="#f0c25e" stroke-width="3"/>
<line x1="{cx-12}" y1="{cy-18}" x2="{cx+12}" y2="{cy-18}" stroke="#f0c25e" stroke-width="5"/><line x1="{cx-12}" y1="{cy+18}" x2="{cx+12}" y2="{cy+18}" stroke="#f0c25e" stroke-width="5"/>
<path d="M{cx} {cy-11} C{cx+6} {cy-3} {cx+5} {cy+6} {cx} {cy+11} C{cx-5} {cy+6} {cx-6} {cy-3} {cx} {cy-11} Z" fill="#ffd877"/>'''

def hill(c):
    return f'<path d="M0 690 C150 668 300 664 450 670 C520 673 570 668 600 664 L600 800 L0 800 Z" fill="{c}"/>'

def qmark(c):
    return f'<path d="M187 335 A113 113 0 1 1 398 384 C352 430 300 452 300 505 L300 545" stroke="{c}" stroke-width="54" fill="none" stroke-linecap="round"/>'

def qdot(fig="#1c1030"):
    return f'''<circle cx="300" cy="620" r="53" fill="#f0c25e" opacity=".14"/><circle cx="300" cy="620" r="40" fill="#f0c25e" opacity=".12"/>
<circle cx="300" cy="620" r="26" fill="#e8bd61"/><circle cx="300" cy="612" r="4.2" fill="{fig}"/><path d="M296 618 L304 618 L305 632 L295 632 Z" fill="{fig}"/>'''

S = {}

d, b = sky("#0e2830", "#163c46", "#123540")
S["real-questions-2"] = page(b + stars(21, 60) + '''
<circle cx="468" cy="168" r="20" fill="#e9e4cf" opacity=".85"/><circle cx="478" cy="161" r="18" fill="#0f2a33"/>
<g fill="#1d4a55" opacity=".55"><ellipse cx="150" cy="210" rx="120" ry="10"/><ellipse cx="430" cy="250" rx="140" ry="9"/><ellipse cx="260" cy="470" rx="160" ry="8"/></g>''' + qmark("#1c4752") + qdot("#0f2a33"), d)

d, b = sky("#28101f", "#401c35", "#381830")
r = random.Random(33)
snow = "".join(f'<circle cx="{r.uniform(0,600):.0f}" cy="{r.uniform(0,800):.0f}" r="{r.choice([1.2,1.6,2,2.4]):.1f}" fill="#fff" opacity="{r.uniform(.25,.6):.2f}"/>' for _ in range(140))
S["real-questions-3"] = page(b + stars(31, 25, 400, .5) + qmark("#4c2541") + snow + qdot("#28101f"), d)

d, b = sky("#141d2a", "#1f2c3d", "#1b2738")
fog = '<g filter="url(#fogblur)">' + "".join(f'<rect x="-40" y="{y}" width="680" height="{h}" rx="{h//2}" fill="#9fb2c8" opacity="{o}"/>' for y, h, o in [(300,60,.07),(380,40,.08),(450,70,.07),(560,50,.09),(620,40,.07)]) + '</g>'
fogdef = '<filter id="fogblur" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>'
S["they-were-young-3"] = page(b + stars(41, 30, 260, .5) + lantern("#2e4058") + fog + hill("#0b1119") + small_lantern(), d + fogdef)

d, b = sky("#101a3a", "#1c2a55", "#3a3150")
dawn = '<radialGradient id="dawn" cx="300" cy="700" r="330" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#f2a65a" stop-opacity=".55"/><stop offset=".45" stop-color="#c76a5a" stop-opacity=".22"/><stop offset="1" stop-color="#c76a5a" stop-opacity="0"/></radialGradient>'
S["they-were-young-4"] = page(b + '<rect width="600" height="800" fill="url(#dawn)"/>' + stars(51, 45, 360, .6) + lantern("#2d3c6a") + hill("#0c1022") +
    '<path d="M300 800 C310 760 330 730 352 700 C366 684 380 676 396 670" stroke="#3a3350" stroke-width="10" fill="none" stroke-linecap="round"/>' + small_lantern(), d + dawn)

# ── Tell Me the Story: one frame, a sky emblem and a scene per volume ───────
# Revised 2026-10-14: a hue family per section (Old Testament warm dawns, the Life
# of Jesus blue into gold, New Testament teal-green), a lighter horizon and greener
# ground, a legible Red Sea (Book 2) and dove and flames (Book 7), and the reading
# pair moved left of the Ochorus mark. The title band (y284-463) stays deep: the
# type is always white, and tune_art_scrim measures it.
def tmts(top, mid, low, glow, far, near, emblem, scene, extra_defs=""):
    d = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
         f'<stop offset=".58" stop-color="{mid}"/><stop offset=".78" stop-color="{low}"/><stop offset="1" stop-color="{low}"/></linearGradient>'
         f'<radialGradient id="horizon" cx="300" cy="640" r="340" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{glow}" stop-opacity=".55"/>'
         f'<stop offset=".5" stop-color="{glow}" stop-opacity=".18"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>')
    b = '<rect width="600" height="800" fill="url(#sky)"/><rect width="600" height="800" fill="url(#horizon)"/>'
    readers = f'''<path d="M-10 800 L-10 720 C80 690 170 682 260 700 C330 714 420 712 520 696 C560 690 590 692 610 696 L610 800 Z" fill="{near}"/>
<g transform="translate(-58 0)"><g fill="#15140f" opacity=".92"><circle cx="118" cy="652" r="11"/><path d="M104 664 C100 680 98 694 96 706 L142 706 C140 690 136 676 130 664 Z"/>
<circle cx="150" cy="670" r="8"/><path d="M140 679 C138 690 137 698 136 706 L162 706 C161 696 159 688 157 679 Z"/></g>
<path d="M126 684 L148 690 L148 698 L126 692 Z" fill="#f4e7c6"/></g>'''
    return page(b + emblem + f'<path d="M0 640 C120 610 220 620 330 632 C430 642 520 618 600 610 L600 800 L0 800 Z" fill="{far}"/>' + scene + readers, d + extra_defs)

# Old Testament Stories: warm dawns
S["tell-me-the-story-1"] = tmts("#2a2456", "#7a3f6a", "#f0b878", "#ffd49a", "#5f9a4a", "#2f5a2a",
  '<circle cx="300" cy="212" r="42" fill="#ffe7a8"/><circle cx="300" cy="212" r="58" fill="#ffe7a8" opacity=".18"/>' + stars(61, 30, 260, .8) +
  '<circle cx="452" cy="178" r="15" fill="#f3efdc"/><circle cx="459" cy="173" r="13" fill="#2c2a5c"/>',
  '<g><rect x="372" y="560" width="10" height="66" fill="#5a4028"/><circle cx="377" cy="548" r="36" fill="#3f8a3a"/><circle cx="356" cy="566" r="22" fill="#4f9a44"/><circle cx="398" cy="566" r="22" fill="#4f9a44"/>'
  '<g fill="#e8463a"><circle cx="362" cy="546" r="4"/><circle cx="390" cy="556" r="4"/><circle cx="376" cy="530" r="4"/></g></g>'
  '<path d="M440 640 C470 620 520 618 560 628" stroke="#7fc4ea" stroke-width="6" fill="none" opacity=".9"/>')

S["tell-me-the-story-2"] = tmts("#3a1f2a", "#8a4428", "#f2a24e", "#ffc070", "#c8945a", "#5a4a2a",
  '<rect x="287" y="164" width="26" height="102" rx="13" fill="#ffb24a"/><path d="M300 152 C316 170 316 188 300 202 C284 188 284 170 300 152 Z" fill="#ffe08a"/><rect x="281" y="164" width="38" height="102" rx="19" fill="#ffb24a" opacity=".25"/>',
  # the sea low on both sides and, in the middle, two walls of water standing up
  # with a dry path and a family crossing between them. Everything stays below the
  # subtitle band (y519-543), so the white subtitle never sits on the water.
  '<path d="M0 640 L0 616 C60 608 120 612 196 606 L196 640 Z" fill="#2577b8"/><path d="M600 640 L600 616 C540 608 480 612 404 606 L404 640 Z" fill="#2577b8"/>'
  '<path d="M0 616 C60 608 120 612 196 606 M600 616 C540 608 480 612 404 606" stroke="#bfe6fb" stroke-width="3" fill="none"/>'
  '<path d="M262 640 L272 600 L328 600 L338 640 Z" fill="#e8c68a"/>'
  '<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5ab4ea"/><stop offset="1" stop-color="#1c5f9a"/></linearGradient>'
  '<path d="M190 640 L190 572 C204 556 222 566 236 554 C248 546 258 554 266 560 L266 640 Z" fill="url(#wall)"/>'
  '<path d="M410 640 L410 572 C396 556 378 566 364 554 C352 546 342 554 334 560 L334 640 Z" fill="url(#wall)"/>'
  '<path d="M190 572 C204 556 222 566 236 554 C248 546 258 554 266 560 C262 550 252 548 246 554" stroke="#f2fbff" stroke-width="5" fill="none" stroke-linecap="round"/>'
  '<path d="M410 572 C396 556 378 566 364 554 C352 546 342 554 334 560 C338 550 348 548 354 554" stroke="#f2fbff" stroke-width="5" fill="none" stroke-linecap="round"/>'
  '<path d="M266 560 L266 640 M334 560 L334 640" stroke="#bfe6fb" stroke-width="4"/>'
  '<g stroke="#9fd6f4" stroke-width="2.5" fill="none" opacity=".6"><path d="M198 590 C220 584 240 590 260 586"/><path d="M198 616 C220 610 240 616 260 612"/><path d="M402 590 C380 584 360 590 340 586"/><path d="M402 616 C380 610 360 616 340 612"/></g>'
  '<g fill="#3a2a1c"><circle cx="284" cy="604" r="5"/><path d="M279 610 L289 610 L291 632 L277 632 Z"/><circle cx="300" cy="612" r="4"/><path d="M296 617 L304 617 L305 632 L295 632 Z"/>'
  '<circle cx="317" cy="603" r="5"/><path d="M312 609 L322 609 L324 632 L310 632 Z"/></g>')

S["tell-me-the-story-3"] = tmts("#2e1838", "#86364a", "#f0a466", "#ffc488", "#7a9a5a", "#3a4a2a",
  '<path d="M252 220 L252 168 L274 190 L300 150 L326 190 L348 168 L348 220 Z" fill="#f2c24a"/><rect x="252" y="214" width="96" height="14" fill="#d9a83a"/><g fill="#e8463a"><circle cx="274" cy="221" r="3.5"/><circle cx="300" cy="221" r="3.5"/><circle cx="326" cy="221" r="3.5"/></g>',
  '<g fill="#d8b08a"><rect x="300" y="574" width="190" height="64"/><rect x="300" y="562" width="14" height="14"/><rect x="330" y="562" width="14" height="14"/><rect x="360" y="562" width="14" height="14"/><rect x="390" y="562" width="14" height="14"/><rect x="420" y="562" width="14" height="14"/><rect x="450" y="562" width="14" height="14"/><rect x="476" y="562" width="14" height="14"/>'
  '<rect x="360" y="530" width="70" height="44"/><path d="M352 532 L395 506 L438 532 Z"/></g><rect x="388" y="600" width="18" height="38" rx="9" fill="#6a4434"/>')

# The Life of Jesus: deep blue into gold
S["tell-me-the-story-4"] = tmts("#0e1a44", "#24407a", "#e8b860", "#ffd98a", "#3a5a7a", "#1e3248",
  '<g fill="#fff3c4"><path d="M300 154 L309 198 L352 208 L309 218 L300 262 L291 218 L248 208 L291 198 Z"/></g><circle cx="300" cy="208" r="54" fill="#fff3c4" opacity=".18"/>' + stars(71, 60, 440, .75) +
  '<path d="M300 262 L300 520" stroke="#fff3c4" stroke-width="2.5" opacity=".28"/>',
  '<circle cx="300" cy="592" r="78" fill="#ffd27a" opacity=".14"/>'
  '<path d="M250 640 L250 584 L300 546 L350 584 L350 640 Z" fill="#7a5a38"/><path d="M240 588 L300 540 L360 588" stroke="#4a3622" stroke-width="8" fill="none"/>'
  '<rect x="282" y="600" width="36" height="40" fill="#ffd27a"/><path d="M290 626 Q300 616 310 626 L308 634 L292 634 Z" fill="#c98a3a"/>')

S["tell-me-the-story-5"] = tmts("#0e2c52", "#1f6a8e", "#f2cc7a", "#ffe2a0", "#3a8a9a", "#24584a",
  '<circle cx="300" cy="212" r="40" fill="#fff0c0"/><circle cx="300" cy="212" r="56" fill="#fff0c0" opacity=".18"/>'
  '<g fill="#fff" opacity=".9"><path d="M150 196 q10 -8 20 0 q10 -8 20 0" stroke="#fff" stroke-width="2.5" fill="none"/><path d="M420 176 q8 -6 16 0 q8 -6 16 0" stroke="#fff" stroke-width="2.5" fill="none"/></g>',
  '<path d="M300 612 C340 600 400 600 460 606" stroke="#e6f6fa" stroke-width="3" fill="none" opacity=".8"/>'
  '<path d="M330 600 L470 600 L452 626 L346 626 Z" fill="#8a5432"/><line x1="398" y1="600" x2="398" y2="520" stroke="#5a3a20" stroke-width="5"/><path d="M402 526 L452 594 L402 594 Z" fill="#fff6e0"/>')

S["tell-me-the-story-6"] = tmts("#1a2456", "#4a4a8a", "#ffc870", "#ffe6a0", "#7a9a5a", "#3a5a2e",
  '<circle cx="300" cy="222" r="42" fill="#ffe7a8"/><circle cx="300" cy="222" r="62" fill="#ffe7a8" opacity=".2"/>' + "".join(f'<rect x="297" y="150" width="6" height="18" rx="3" fill="#ffe7a8" opacity=".65" transform="rotate({a} 300 222)"/>' for a in range(-80, 81, 20)),
  '<path d="M280 640 C280 560 330 530 400 530 C470 530 520 560 520 640 Z" fill="#a8977a"/><path d="M370 640 L370 594 A30 30 0 0 1 430 594 L430 640 Z" fill="#2a2418"/>'
  '<circle cx="470" cy="610" r="30" fill="#c2b090"/><circle cx="470" cy="610" r="30" fill="none" stroke="#8a7a5a" stroke-width="3"/><path d="M372 640 L428 640" stroke="#fff3c4" stroke-width="3"/>'
  '<path d="M370 594 A30 30 0 0 1 430 594" stroke="#ffe7a8" stroke-width="2" fill="none" opacity=".6"/>')

# New Testament Stories: teal into green
S["tell-me-the-story-7"] = tmts("#0c2e3a", "#1f6a6a", "#d8d084", "#fff0a8", "#4a9a6a", "#2a5a3a",
  # three larger two-tone flames, and a dove descending with wings raised
  '<g>' + "".join(f'<path d="M{x} 294 C{x+18} 274 {x+16} 252 {x} 226 C{x-16} 252 {x-18} 274 {x} 294 Z" fill="#ff9a3a"/><path d="M{x} 292 C{x+9} 278 {x+8} 264 {x} 250 C{x-8} 264 {x-9} 278 {x} 292 Z" fill="#ffe27a"/>' for x in (226, 300, 374)) + '</g>'
  '<g fill="#fffaf0" transform="translate(66 50) scale(.78)"><path d="M300 176 C292 150 268 132 236 128 C252 142 262 158 268 176 C276 182 290 184 300 176 Z"/>'
  '<path d="M300 176 C308 150 332 132 364 128 C348 142 338 158 332 176 C324 182 310 184 300 176 Z"/>'
  '<ellipse cx="300" cy="182" rx="12" ry="18"/><circle cx="300" cy="200" r="9"/><path d="M296 206 L300 214 L304 206 Z" fill="#f2b24a"/>'
  '<path d="M292 164 L300 150 L308 164 Z"/></g>',
  '<g fill="#d8a878"><rect x="300" y="576" width="40" height="62"/><rect x="344" y="560" width="44" height="78"/><rect x="392" y="584" width="36" height="54"/><rect x="432" y="568" width="48" height="70"/><path d="M344 560 L366 540 L388 560 Z"/></g>'
  '<g fill="#ffe08a"><rect x="352" y="580" width="8" height="10"/><rect x="372" y="580" width="8" height="10"/><rect x="444" y="584" width="8" height="10"/><rect x="310" y="592" width="8" height="10"/></g>'
  '<path d="M300 640 C270 660 250 690 236 720" stroke="#e2c08a" stroke-width="9" fill="none" opacity=".75"/>')

S["tell-me-the-story-8"] = tmts("#0c2c3e", "#1c6476", "#e2d88c", "#fff2b0", "#3f9a76", "#25583e",
  # the tree of life, golden, in the sky
  '<circle cx="300" cy="214" r="62" fill="#fff2b0" opacity=".16"/><rect x="295" y="226" width="10" height="30" rx="3" fill="#c99a4a"/>'
  '<circle cx="300" cy="206" r="32" fill="#f2c24a"/><circle cx="276" cy="222" r="20" fill="#f2c24a"/><circle cx="324" cy="222" r="20" fill="#f2c24a"/>'
  '<g fill="#e8563a"><circle cx="290" cy="198" r="4"/><circle cx="312" cy="208" r="4"/><circle cx="282" cy="224" r="4"/><circle cx="322" cy="226" r="4"/><circle cx="300" cy="186" r="4"/></g>',
  # the sea, Paul's ship under sail, and a far city on the shore
  '<path d="M0 640 L0 606 C120 598 240 604 360 600 C460 597 540 600 600 598 L600 640 Z" fill="#2a8aa0"/>'
  '<path d="M0 606 C120 598 240 604 360 600 C460 597 540 600 600 598" stroke="#dff4f6" stroke-width="2.5" fill="none" opacity=".8"/>'
  '<g fill="#d8a878"><rect x="470" y="570" width="22" height="30"/><rect x="496" y="560" width="26" height="40"/><rect x="526" y="574" width="20" height="26"/><path d="M496 560 L509 546 L522 560 Z"/></g>'
  '<path d="M280 596 L392 596 L378 618 L294 618 Z" fill="#8a5432"/><line x1="336" y1="596" x2="336" y2="540" stroke="#5a3a20" stroke-width="4"/>'
  '<path d="M314 548 L358 548 L362 590 L310 590 Z" fill="#fff6e0"/><path d="M336 548 L336 590" stroke="#e8dcc0" stroke-width="2"/>')
# Book 9 is a companion (songs and wisdom), so it takes its own family: plum into amber
S["tell-me-the-story-9"] = tmts("#2a1638", "#6a3266", "#f2b46a", "#ffd890", "#5f9a4a", "#2f5a2a",
  # David's lyre in the sky: a sound box, two curving horns, a crossbar, strings
  '<circle cx="300" cy="214" r="60" fill="#ffd890" opacity=".14"/>'
  '<path d="M272 254 C252 232 248 200 262 176 C268 166 262 158 254 156 M328 254 C348 232 352 200 338 176 C332 166 338 158 346 156" stroke="#f2c24a" stroke-width="9" fill="none" stroke-linecap="round"/>'
  '<path d="M262 180 L338 180" stroke="#f2c24a" stroke-width="7" stroke-linecap="round"/>'
  '<path d="M266 248 L334 248 L328 268 L272 268 Z" fill="#d9a83a"/>'
  '<g stroke="#fff2c8" stroke-width="2"><line x1="282" y1="181" x2="284" y2="250"/><line x1="294" y1="181" x2="295" y2="250"/><line x1="306" y1="181" x2="305" y2="250"/><line x1="318" y1="181" x2="316" y2="250"/></g>',
  # still waters and two sheep in a green pasture (Psalm 23)
  '<path d="M330 640 C360 622 420 616 470 622 C520 628 560 622 600 616 L600 640 Z" fill="#5fb4dc"/>'
  '<path d="M340 632 C380 620 430 618 470 624" stroke="#e6f6ff" stroke-width="2.5" fill="none" opacity=".8"/>'
  '<g fill="#f4efe2"><ellipse cx="410" cy="600" rx="22" ry="14"/><circle cx="430" cy="592" r="8" fill="#3a2a22"/>'
  '<ellipse cx="474" cy="604" rx="18" ry="12"/><circle cx="458" cy="598" r="7" fill="#3a2a22"/></g>'
  '<g stroke="#3a2a22" stroke-width="3"><line x1="400" y1="612" x2="400" y2="622"/><line x1="418" y1="612" x2="418" y2="622"/><line x1="468" y1="614" x2="468" y2="622"/><line x1="482" y1="614" x2="482" y2="622"/></g>')

# ── The Big Story: from the garden to the city ──────────────────────────────
d, b = sky("#0d1230", "#2a2a55", "#8a5a5a")
glow = '<radialGradient id="city" cx="470" cy="600" r="220" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffd98a" stop-opacity=".7"/><stop offset=".4" stop-color="#e89a5a" stop-opacity=".25"/><stop offset="1" stop-color="#e89a5a" stop-opacity="0"/></radialGradient>'
S["the-big-story"] = page(b + stars(81, 90, 520, .8) + '<rect width="600" height="800" fill="url(#city)"/>' +
  '<path d="M0 610 C120 590 240 600 360 604 C440 606 520 596 600 592 L600 800 L0 800 Z" fill="#2a2440"/>'
  '<g fill="#ffe3a0"><rect x="430" y="568" width="16" height="34"/><rect x="450" y="556" width="22" height="46"/><rect x="476" y="562" width="14" height="40"/><rect x="494" y="572" width="18" height="30"/><path d="M450 556 L461 540 L472 556 Z"/></g>'
  '<path d="M0 700 C140 670 260 660 380 664 C480 668 550 660 600 650 L600 800 L0 800 Z" fill="#141226"/>'
  '<path d="M160 800 C220 740 300 700 380 672 C420 658 440 640 456 612" stroke="#3a3250" stroke-width="7" fill="none" stroke-linecap="round"/>'
  '<g><rect x="96" y="626" width="9" height="62" fill="#141226"/><circle cx="100" cy="612" r="30" fill="#141226"/><circle cx="80" cy="630" r="18" fill="#141226"/><circle cx="120" cy="630" r="18" fill="#141226"/>'
  '<g fill="#e8463a" opacity=".85"><circle cx="90" cy="610" r="3"/><circle cx="112" cy="622" r="3"/></g></g>', d + glow)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[2:]
    for slug, html in S.items():
        if only and slug not in only:
            continue
        h = OUT / f"{slug}.html"
        h.write_text(html)
        png = OUT / f"{slug}@2x.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        "--window-size=600,800", f"--screenshot={png}", f"file://{h}"], capture_output=True)
        Image.open(png).convert("RGB").resize((600, 800), Image.LANCZOS).save(OUT / f"{slug}.jpg", quality=90)
        print("drew", slug, flush=True)
    if only:
        raise SystemExit(0)  # a partial run has no full set to montage
    m = Image.new("RGB", (6*240, 2*320), "white")
    for i, s in enumerate(S):
        m.paste(Image.open(OUT / f"{s}.jpg").resize((240, 320)), ((i % 6)*240, (i//6)*320))
    m.save(OUT / "montage.jpg")
