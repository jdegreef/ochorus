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
def tmts(top, mid, low, far, near, emblem, scene, extra_defs=""):
    d = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
         f'<stop offset=".6" stop-color="{mid}"/><stop offset=".8" stop-color="{low}"/><stop offset="1" stop-color="{low}"/></linearGradient>')
    b = '<rect width="600" height="800" fill="url(#sky)"/>'
    readers = f'''<path d="M-10 800 L-10 720 C80 690 170 682 260 700 C330 714 420 712 520 696 C560 690 590 692 610 696 L610 800 Z" fill="{near}"/>
<g fill="{near}"><circle cx="118" cy="652" r="11"/><path d="M104 664 C100 680 98 694 96 706 L142 706 C140 690 136 676 130 664 Z"/>
<circle cx="150" cy="670" r="8"/><path d="M140 679 C138 690 137 698 136 706 L162 706 C161 696 159 688 157 679 Z"/></g>
<path d="M126 684 L148 690 L148 698 L126 692 Z" fill="#f4e7c6"/>'''
    return page(b + emblem + f'<path d="M0 640 C120 610 220 620 330 632 C430 642 520 618 600 610 L600 800 L0 800 Z" fill="{far}"/>' + scene + readers, d + extra_defs)

S["tell-me-the-story-1"] = tmts("#173462", "#2f5688", "#d9a86a", "#3a5a3a", "#1d2a1c",
  '<circle cx="300" cy="212" r="42" fill="#ffe7a8"/><circle cx="300" cy="212" r="58" fill="#ffe7a8" opacity=".18"/>' + stars(61, 30, 260, .8) +
  '<circle cx="452" cy="178" r="15" fill="#f3efdc"/><circle cx="459" cy="173" r="13" fill="#1f3c6a"/>',
  '<g><rect x="372" y="560" width="10" height="66" fill="#4a3624"/><circle cx="377" cy="548" r="36" fill="#3f7a3a"/><circle cx="356" cy="566" r="22" fill="#4a8a40"/><circle cx="398" cy="566" r="22" fill="#4a8a40"/>'
  '<g fill="#e8463a"><circle cx="362" cy="546" r="4"/><circle cx="390" cy="556" r="4"/><circle cx="376" cy="530" r="4"/></g></g>'
  '<path d="M440 640 C470 620 520 618 560 628" stroke="#6fb0d8" stroke-width="5" fill="none" opacity=".8"/>')

S["tell-me-the-story-2"] = tmts("#251f48", "#5e3a5a", "#c97a4e", "#6a4a3a", "#2a1c18",
  '<rect x="287" y="164" width="26" height="102" rx="13" fill="#ffb24a"/><path d="M300 152 C316 170 316 188 300 202 C284 188 284 170 300 152 Z" fill="#ffe08a"/><rect x="281" y="164" width="38" height="102" rx="19" fill="#ffb24a" opacity=".25"/>',
  '<path d="M150 640 L150 600 C200 590 236 560 262 520 C276 560 284 600 288 640 Z" fill="#3a7ab0"/><path d="M450 640 L450 600 C400 590 364 560 338 520 C324 560 316 600 312 640 Z" fill="#3a7ab0"/>'
  '<path d="M262 520 C270 540 282 546 290 542" stroke="#cfe8f6" stroke-width="4" fill="none"/><path d="M338 520 C330 540 318 546 310 542" stroke="#cfe8f6" stroke-width="4" fill="none"/>'
  '<path d="M288 640 L312 640 L304 560 L296 560 Z" fill="#c9a26a"/>')

S["tell-me-the-story-3"] = tmts("#21163a", "#44285a", "#a85a5e", "#4a3a4a", "#1f1622",
  '<path d="M252 220 L252 168 L274 190 L300 150 L326 190 L348 168 L348 220 Z" fill="#f2c24a"/><rect x="252" y="214" width="96" height="14" fill="#d9a83a"/><g fill="#e8463a"><circle cx="274" cy="221" r="3.5"/><circle cx="300" cy="221" r="3.5"/><circle cx="326" cy="221" r="3.5"/></g>',
  '<g fill="#b98a6a"><rect x="300" y="574" width="190" height="64"/><rect x="300" y="562" width="14" height="14"/><rect x="330" y="562" width="14" height="14"/><rect x="360" y="562" width="14" height="14"/><rect x="390" y="562" width="14" height="14"/><rect x="420" y="562" width="14" height="14"/><rect x="450" y="562" width="14" height="14"/><rect x="476" y="562" width="14" height="14"/>'
  '<rect x="360" y="530" width="70" height="44"/><path d="M352 532 L395 506 L438 532 Z"/></g><rect x="388" y="600" width="18" height="38" rx="9" fill="#5a3a2e"/>')

S["tell-me-the-story-4"] = tmts("#0c1636", "#1c2a5a", "#3a3a6a", "#25304a", "#10141f",
  '<g fill="#fff3c4"><path d="M300 154 L309 198 L352 208 L309 218 L300 262 L291 218 L248 208 L291 198 Z"/></g><circle cx="300" cy="208" r="54" fill="#fff3c4" opacity=".15"/>' + stars(71, 60, 480, .7) +
  '<path d="M300 262 L300 520" stroke="#fff3c4" stroke-width="2" opacity=".2"/>',
  '<path d="M250 640 L250 584 L300 546 L350 584 L350 640 Z" fill="#5a4630"/><path d="M240 588 L300 540 L360 588" stroke="#3a2c1c" stroke-width="8" fill="none"/>'
  '<rect x="282" y="600" width="36" height="40" fill="#f4c56a"/><path d="M290 626 Q300 616 310 626 L308 634 L292 634 Z" fill="#c98a3a"/>')

S["tell-me-the-story-5"] = tmts("#0d3442", "#1f5f6e", "#c9a46a", "#2a6a7a", "#16262a",
  '<circle cx="300" cy="212" r="40" fill="#fff0c0"/><circle cx="300" cy="212" r="56" fill="#fff0c0" opacity=".16"/>'
  '<g fill="#fff" opacity=".85"><path d="M150 196 q10 -8 20 0 q10 -8 20 0" stroke="#fff" stroke-width="2.5" fill="none"/><path d="M420 176 q8 -6 16 0 q8 -6 16 0" stroke="#fff" stroke-width="2.5" fill="none"/></g>',
  '<path d="M300 612 C340 600 400 600 460 606" stroke="#cfe8ee" stroke-width="2.5" fill="none" opacity=".7"/>'
  '<path d="M330 600 L470 600 L452 626 L346 626 Z" fill="#7a4a2a"/><line x1="398" y1="600" x2="398" y2="520" stroke="#5a3a20" stroke-width="5"/><path d="M402 526 L452 594 L402 594 Z" fill="#f3ead2"/>')

S["tell-me-the-story-6"] = tmts("#262248", "#7a4664", "#d9a26a", "#5a5a4a", "#1f1f18",
  '<circle cx="300" cy="222" r="40" fill="#ffe7a8"/>' + "".join(f'<rect x="297" y="156" width="6" height="16" rx="3" fill="#ffe7a8" opacity=".5" transform="rotate({a} 300 222)"/>' for a in range(-80, 81, 20)),
  '<path d="M280 640 C280 560 330 530 400 530 C470 530 520 560 520 640 Z" fill="#8a7a62"/><path d="M370 640 L370 594 A30 30 0 0 1 430 594 L430 640 Z" fill="#1a1712"/>'
  '<circle cx="470" cy="610" r="30" fill="#a8977a"/><circle cx="470" cy="610" r="30" fill="none" stroke="#7a6a52" stroke-width="3"/><path d="M380 640 L420 640" stroke="#f6e3b0" stroke-width="2"/>')

S["tell-me-the-story-7"] = tmts("#331329", "#7e3434", "#cf8846", "#6a3a3a", "#22140f",
  '<g fill="#ffd25a">' + "".join(f'<path d="M{x} 262 C{x+11} 244 {x+9} 226 {x} 208 C{x-9} 226 {x-11} 244 {x} 262 Z"/>' for x in (240, 300, 360)) + '</g>'
  '<path d="M300 170 C312 162 330 162 340 170 C330 172 320 178 312 186 L300 184 L288 186 C280 178 270 172 260 170 C270 162 288 162 300 170 Z" fill="#fff6e0"/>',
  '<g fill="#7a4a3a"><rect x="300" y="576" width="40" height="62"/><rect x="344" y="560" width="44" height="78"/><rect x="392" y="584" width="36" height="54"/><rect x="432" y="568" width="48" height="70"/><path d="M344 560 L366 540 L388 560 Z"/></g>'
  '<g fill="#f5c862"><rect x="352" y="580" width="8" height="10"/><rect x="372" y="580" width="8" height="10"/><rect x="444" y="584" width="8" height="10"/><rect x="310" y="592" width="8" height="10"/></g>'
  '<path d="M300 640 C260 660 230 690 210 720" stroke="#b98a5a" stroke-width="8" fill="none" opacity=".6"/>')

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
