"""The teen object grounds of 2026-10-13 (the fourteen retold classics for teens):
one true thing from the book, low on a deep ground. Same contract as
originals_series.py:

    python3 backend/scripts/original_grounds/teen_objects.py OUTDIR [slug ...]
"""
import pathlib
import subprocess
import sys

from PIL import Image

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def frame(top, bottom, body, glow=None):
    g = ""
    if glow:
        cx, cy, r, col, op = glow
        g = f'<radialGradient id="glow" cx="{cx}" cy="{cy}" r="{r}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/><stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
    return f'''<!doctype html><html><body style="margin:0;background:#000">
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>
<radialGradient id="vig" cx="300" cy="380" r="560" gradientUnits="userSpaceOnUse"><stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.35"/></radialGradient>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#fff" fill-opacity="0.05"/><circle cx="3" cy="3" r="0.6" fill="#000" fill-opacity="0.10"/></pattern>
{g}
</defs>
<rect width="600" height="800" fill="url(#bg)"/>
{'<rect width="600" height="800" fill="url(#glow)"/>' if glow else ''}
{body}
<rect width="600" height="800" fill="url(#vig)"/>
<rect width="600" height="800" fill="url(#grain)"/>
</svg></body></html>'''

def key(angle):
    # bow centre on the ring's rim, shaft hanging outward
    return f'''<g transform="rotate({angle} 300 540)">
<circle cx="300" cy="566" r="12" fill="none" stroke="#d2ab52" stroke-width="7"/>
<rect x="296" y="577" width="8" height="68" rx="2" fill="#d2ab52"/>
<rect x="303" y="624" width="15" height="7" fill="#d2ab52"/><rect x="303" y="636" width="11" height="7" fill="#d2ab52"/>
<rect x="297" y="576" width="2" height="66" fill="#8a6a2a" opacity=".6"/></g>'''

def reed(x, h, lean=0, col="#a8946a"):
    return f'<path d="M{x} 645 Q{x+lean/2} {645-h/2} {x+lean} {645-h}" stroke="{col}" stroke-width="4" fill="none" stroke-linecap="round"/>' \
           f'<ellipse cx="{x+lean}" cy="{645-h+8}" rx="4" ry="12" fill="#7a5a3a" transform="rotate({lean/3} {x+lean} {645-h+8})"/>'

S = {}

S["absolute-surrender-teens"] = frame("#15403f", "#0a2425", f'''
<circle cx="300" cy="540" r="24" fill="none" stroke="#d8b25a" stroke-width="7"/>
{key(-40)}{key(-14)}{key(14)}{key(40)}''')

S["foxes-book-of-martyrs-teens"] = frame("#221b1c", "#120d0e", '''
<path d="M300 528 C312 548 316 562 300 584 C284 562 288 548 300 528 Z" fill="#f4c35a"/>
<path d="M300 546 C306 558 307 566 300 580 C293 566 294 558 300 546 Z" fill="#fff1c8"/>
<line x1="300" y1="582" x2="300" y2="592" stroke="#2a1a10" stroke-width="2.5"/>
<rect x="286" y="590" width="28" height="66" rx="3" fill="#e9dcc0"/>
<rect x="286" y="590" width="8" height="66" fill="#c9b994" opacity=".7"/>
<path d="M286 594 q4 8 0 16" stroke="#f5ecd8" stroke-width="3" fill="none"/>
<ellipse cx="300" cy="658" rx="46" ry="9" fill="#5a3b24"/><ellipse cx="300" cy="655" rx="36" ry="5" fill="#7a5233"/>''',
glow=(300, 560, 110, "#f4a83a", 0.28))

S["how-to-succeed-in-the-christian-life-teens"] = frame("#12302a", "#081a16", '''
<g fill="#0c211c"><ellipse cx="300" cy="700" rx="62" ry="13"/><ellipse cx="262" cy="664" rx="40" ry="9"/><ellipse cx="318" cy="636" rx="30" ry="7"/><ellipse cx="282" cy="614" rx="22" ry="5"/><ellipse cx="306" cy="598" rx="15" ry="3.5"/></g>
<ellipse cx="300" cy="700" rx="62" ry="13" fill="#3e4a3e"/><ellipse cx="262" cy="664" rx="40" ry="9" fill="#9a9478"/><ellipse cx="318" cy="636" rx="30" ry="7" fill="#727560"/><ellipse cx="282" cy="614" rx="22" ry="5" fill="#4c5848"/><ellipse cx="306" cy="598" rx="15" ry="3.5" fill="#34423a"/>
<rect x="250" y="612" width="24" height="44" rx="3" fill="#2a2620"/>
<rect x="254" y="618" width="16" height="32" rx="2" fill="#ffd77a"/>
<path d="M256 640 C258 630 262 628 262 622 C264 628 268 632 268 640 Z" fill="#fff3c8"/>
<path d="M248 612 L276 612 L270 602 L254 602 Z" fill="#2a2620"/><path d="M254 602 Q262 584 270 602" stroke="#2a2620" stroke-width="3" fill="none"/>
<rect x="246" y="654" width="32" height="5" rx="2" fill="#2a2620"/>''',
glow=(262, 636, 95, "#ffd77a", 0.26))

S["life-and-diary-of-david-brainerd-teens"] = frame("#132232", "#0a131d", '''
<path d="M300 596 L196 582 L190 646 L300 656 Z" fill="#e7dcc4"/>
<path d="M300 596 L404 582 L410 646 L300 656 Z" fill="#f1e8d4"/>
<path d="M300 596 L300 656" stroke="#b9a986" stroke-width="2"/>
<g stroke="#9c8c6c" stroke-width="1.4" opacity=".7">
<line x1="208" y1="600" x2="290" y2="609"/><line x1="207" y1="612" x2="290" y2="620"/><line x1="206" y1="624" x2="290" y2="632"/><line x1="205" y1="636" x2="270" y2="642"/>
<line x1="310" y1="609" x2="392" y2="600"/><line x1="310" y1="620" x2="393" y2="612"/></g>
<path d="M352 626 L436 534" stroke="#d6cdb8" stroke-width="2.5"/>
<path d="M436 534 C424 548 404 574 386 590 C392 568 410 548 436 534 Z" fill="#cfc6b2"/>
<path d="M436 534 C440 552 424 576 398 594 L386 590 C404 574 424 548 436 534 Z" fill="#a9a08c"/>
<ellipse cx="300" cy="664" rx="120" ry="6" fill="#000" opacity=".35"/>''')

S["life-of-antony-teens"] = frame("#3a1e13", "#1f0f09", '''
<path d="M0 604 C140 592 240 598 300 600 C380 596 480 590 600 600 L600 800 L0 800 Z" fill="#2c160d"/>
<path d="M290 600 L310 600 L430 800 L170 800 Z" fill="#6b4128"/>
<g fill="#2a1209"><ellipse cx="286" cy="628" rx="3" ry="5.5" transform="rotate(-6 286 628)"/><ellipse cx="276" cy="648" rx="3.6" ry="6.5" transform="rotate(-6 276 648)"/><ellipse cx="270" cy="674" rx="4.4" ry="8" transform="rotate(-5 270 674)"/><ellipse cx="256" cy="706" rx="5.4" ry="10" transform="rotate(-5 256 706)"/><ellipse cx="248" cy="748" rx="6.5" ry="12" transform="rotate(-4 248 748)"/><ellipse cx="292" cy="614" rx="2.4" ry="4"/></g>
<g fill="#f0c04e"><ellipse cx="316" cy="622" rx="6" ry="2.6"/><ellipse cx="330" cy="634" rx="7" ry="3"/><ellipse cx="314" cy="642" rx="8" ry="3.4"/><ellipse cx="338" cy="654" rx="8" ry="3.4"/><ellipse cx="322" cy="662" rx="7" ry="3"/><ellipse cx="348" cy="672" rx="9" ry="3.8"/><ellipse cx="332" cy="684" rx="8" ry="3.4"/></g>
<g fill="#fff3c0"><circle cx="312" cy="641" r="1.8"/><circle cx="346" cy="671" r="2"/><circle cx="328" cy="633" r="1.6"/></g>''',
glow=(330, 652, 80, "#f0c04e", 0.16))

S["mortification-of-sin-teens"] = frame("#252a1a", "#13160d", '''
<path d="M300 598 C298 580 300 566 300 552" stroke="#6f8a3a" stroke-width="4" fill="none"/>
<path d="M300 566 C276 562 262 546 260 532 C282 536 296 548 300 566 Z" fill="#7a9440"/>
<path d="M300 556 C322 552 336 538 340 526 C318 528 304 540 300 556 Z" fill="#8aa64a"/>
<path d="M300 580 C320 580 334 570 342 560 C322 558 308 566 300 580 Z" fill="#6c843a"/>
<ellipse cx="300" cy="604" rx="18" ry="10" fill="#4a3a26"/>
<g stroke="#c2a77a" stroke-width="2" fill="none" stroke-linecap="round">
<path d="M292 610 C284 624 276 636 272 652"/><path d="M298 612 C296 628 292 640 294 658"/><path d="M304 612 C308 626 312 640 310 656"/>
<path d="M310 608 C320 620 330 630 334 646"/><path d="M286 606 C272 614 262 626 256 640"/><path d="M296 630 C302 636 304 644 302 650"/></g>''')

petals = "".join(f'<ellipse cx="300" cy="557" rx="8.5" ry="25" fill="#f3efe4" transform="rotate({a} 300 584)"/>' for a in range(0, 360, 24))
S["orthodoxy-teens"] = frame("#1c1d44", "#0e0f26", f'''
<path d="M300 660 C298 640 302 620 300 600" stroke="#5f9b4e" stroke-width="4" fill="none"/>
<path d="M300 646 C280 644 266 632 262 616 C284 618 296 630 300 646 Z" fill="#5f9b4e"/>
{petals}<circle cx="300" cy="584" r="14" fill="#e9b93a"/><circle cx="296" cy="580" r="5" fill="#f6d36b"/>
<g fill="#fff" opacity=".55"><circle cx="120" cy="520" r="1.4"/><circle cx="468" cy="560" r="1.2"/><circle cx="420" cy="640" r="1"/><circle cx="170" cy="630" r="1.1"/></g>''')

S["pensees-teens"] = frame("#1b2636", "#0d141e", '''
<path d="M222 650 C232 590 262 556 292 566" stroke="#c9a24a" stroke-width="1.6" fill="none" stroke-dasharray="3 6" opacity=".6"/>
<g transform="rotate(-24 304 566) translate(304 566) scale(1.5) translate(-304 -566)"><ellipse cx="304" cy="570" rx="34" ry="12" fill="#8a6a2a"/><ellipse cx="304" cy="566" rx="34" ry="12" fill="#d6af55"/><ellipse cx="304" cy="566" rx="25" ry="8" fill="none" stroke="#a9853a" stroke-width="2"/></g>
<g stroke="#e8c870" stroke-width="2" stroke-linecap="round" opacity=".7"><line x1="350" y1="540" x2="360" y2="532"/><line x1="356" y1="556" x2="368" y2="552"/><line x1="342" y1="528" x2="346" y2="518"/></g>
<line x1="170" y1="652" x2="430" y2="652" stroke="#2c3a50" stroke-width="2"/>
<ellipse cx="304" cy="654" rx="26" ry="4" fill="#000" opacity=".4"/>''')

S["the-bruised-reed-teens"] = frame("#2f2338", "#181220", f'''
<rect x="0" y="645" width="600" height="155" fill="#120d18" opacity=".7"/>
<g stroke="#5c4a6c" stroke-width="2" opacity=".7"><line x1="190" y1="660" x2="250" y2="660"/><line x1="320" y1="672" x2="400" y2="672"/><line x1="230" y1="686" x2="270" y2="686"/></g>
{reed(232, 96, -6)}{reed(256, 112, 4)}{reed(344, 104, 8)}{reed(368, 88, -4)}
<path d="M300 645 L301 588 Q302 576 314 566 Q328 560 334 574" stroke="#a8946a" stroke-width="4" fill="none" stroke-linecap="round"/>
<ellipse cx="336" cy="588" rx="4" ry="12" fill="#7a5a3a" transform="rotate(-10 336 588)"/>''')

S["the-imitation-of-christ-teens"] = frame("#2b1b26", "#160c13", '''
<rect x="0" y="652" width="600" height="148" fill="#120a10"/>
<rect x="236" y="528" width="128" height="128" fill="#3a2731"/>
<path d="M252 656 L252 560 A48 34 0 0 1 348 560 L348 656 Z" fill="#5a3b2a"/>
<g stroke="#3e2819" stroke-width="2.5"><line x1="276" y1="540" x2="276" y2="656"/><line x1="300" y1="532" x2="300" y2="656"/><line x1="324" y1="540" x2="324" y2="656"/></g>
<rect x="252" y="574" width="96" height="6" fill="#3a2a22"/><rect x="252" y="626" width="96" height="6" fill="#3a2a22"/>
<circle cx="334" cy="604" r="4" fill="#c9a24a"/>
<rect x="254" y="653" width="92" height="3" fill="#ffd27a"/>
<path d="M254 656 L346 656 L380 690 L220 690 Z" fill="#ffd27a" opacity=".16"/>''')

S["the-practice-of-the-presence-of-god-teens"] = frame("#2b2927", "#151413", '''
<path d="M300 586 C290 572 310 562 300 548 C292 538 306 530 300 520" stroke="#cfc8bc" stroke-width="2.4" fill="none" opacity=".6" stroke-linecap="round"/>
<path d="M314 586 C306 574 322 566 314 554" stroke="#cfc8bc" stroke-width="2" fill="none" opacity=".4" stroke-linecap="round"/>
<path d="M254 596 L346 596 L340 634 Q300 650 260 634 Z" fill="#4c4844"/>
<path d="M254 596 L346 596 L344 608 L256 608 Z" fill="#5f5a55"/>
<rect x="248" y="590" width="104" height="8" rx="3" fill="#6d6863"/>
<path d="M248 600 q-12 2 -10 12" stroke="#6d6863" stroke-width="4" fill="none"/><path d="M352 600 q12 2 10 12" stroke="#6d6863" stroke-width="4" fill="none"/>
<path d="M270 662 C272 648 280 646 282 640 C286 648 288 652 292 642 C296 650 300 654 304 640 C308 652 312 650 316 642 C320 648 326 652 330 662 Z" fill="#e8873a"/>
<path d="M286 662 C288 654 292 652 294 648 C298 654 302 656 306 648 C308 654 312 656 314 662 Z" fill="#f6c45a"/>''',
glow=(300, 660, 90, "#e8873a", 0.22))

S["the-pursuit-of-god-teens"] = frame("#3b1018", "#200810", '''
<defs><linearGradient id="fold" x1="0" y1="0" x2="1" y2="0" spreadMethod="repeat"><stop offset="0" stop-color="#7a1e2a"/><stop offset=".5" stop-color="#9a2c38"/><stop offset="1" stop-color="#7a1e2a"/></linearGradient>
<linearGradient id="light" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f6d27a" stop-opacity="0"/><stop offset=".5" stop-color="#fff2c4"/><stop offset="1" stop-color="#f6d27a" stop-opacity="0"/></linearGradient></defs>
<rect x="196" y="524" width="208" height="8" fill="#c9a24a"/>
<path d="M204 532 L294 532 L298 556 L290 578 L297 602 L288 628 L294 660 L204 660 Z" fill="#8a2532"/>
<path d="M306 532 L396 532 L396 660 L312 660 L304 634 L313 606 L303 582 L311 558 Z" fill="#8a2532"/>
<g stroke="#5e1420" stroke-width="3" opacity=".7"><line x1="222" y1="532" x2="222" y2="660"/><line x1="246" y1="532" x2="246" y2="660"/><line x1="270" y1="532" x2="268" y2="660"/><line x1="332" y1="532" x2="334" y2="660"/><line x1="356" y1="532" x2="356" y2="660"/><line x1="380" y1="532" x2="380" y2="660"/></g>
<path d="M294 532 L306 532 L311 558 L303 582 L313 606 L304 634 L312 660 L294 660 L288 628 L297 602 L290 578 L298 556 Z" fill="url(#light)"/>''',
glow=(300, 600, 120, "#f6c45a", 0.18))

S["the-secret-of-guidance-teens"] = frame("#0f1d2e", "#08101a", '''
<rect x="0" y="600" width="600" height="200" fill="#060d16"/>
<g stroke="#2c3c52" stroke-width="3"><line x1="296" y1="602" x2="196" y2="800"/><line x1="304" y1="602" x2="404" y2="800"/></g>
<g stroke="#1e2b3d" stroke-width="3"><line x1="288" y1="620" x2="312" y2="620"/><line x1="282" y1="642" x2="318" y2="642"/><line x1="272" y1="672" x2="328" y2="672"/><line x1="258" y1="712" x2="342" y2="712"/><line x1="238" y1="764" x2="362" y2="764"/></g>
<g fill="#ffd27a"><circle cx="300" cy="592" r="3.2"/><circle cx="284" cy="594" r="2.6"/><circle cx="318" cy="593" r="2.8"/><circle cx="268" cy="596" r="2.2"/><circle cx="334" cy="595" r="2.4"/><circle cx="292" cy="584" r="2.2"/><circle cx="310" cy="582" r="2.4"/><circle cx="250" cy="597" r="1.8"/><circle cx="352" cy="597" r="1.9"/><circle cx="300" cy="574" r="2"/><circle cx="234" cy="598" r="1.4"/><circle cx="368" cy="598" r="1.5"/></g>
<path d="M0 600 C120 594 200 598 260 600 L340 600 C400 598 480 592 600 598 L600 604 L0 604 Z" fill="#060d16"/>''',
glow=(300, 592, 110, "#ffd27a", 0.2))

S["the-way-to-god-teens"] = frame("#11242b", "#081418", '''
<path d="M0 620 C120 590 220 600 300 606 C390 596 480 586 600 610 L600 800 L0 800 Z" fill="#0a171c"/>
<path d="M286 612 L314 612 L372 800 L228 800 Z" fill="#1e3238"/>
<path d="M264 612 L264 574 L300 548 L336 574 L336 612 Z" fill="#06100f"/>
<rect x="276" y="584" width="14" height="14" fill="#f4c35a"/><rect x="306" y="588" width="12" height="24" fill="#e8a347"/>
<rect x="326" y="552" width="6" height="16" fill="#06100f"/>
<circle cx="292" cy="680" r="5" fill="#06100f"/><path d="M286 688 L298 688 L300 712 L284 712 Z" fill="#06100f"/>''',
glow=(300, 592, 80, "#f4c35a", 0.18))

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
        print("drew", slug)
    fs = list(S)
    if only:
        raise SystemExit(0)  # a partial run has no full set to montage
    m = Image.new("RGB", (7*240, 2*320), "white")
    for i, s in enumerate(fs):
        m.paste(Image.open(OUT / f"{s}.jpg").resize((240, 320)), ((i % 7)*240, (i//7)*320))
    m.save(OUT / "montage.jpg")
