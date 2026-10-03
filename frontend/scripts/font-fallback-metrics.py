#!/usr/bin/env python3
"""Regenerate the metric overrides for the house fonts' CLS fallbacks.

Fraunces and Hanken Grotesk ship `font-display: swap`, so the browser paints
Latin text in a local device font (Georgia / Arial) until the web file arrives,
then swaps — and if the device font's metrics differ, the line reflows. That is
the mobile CLS the `'Fraunces Fallback'` / `'Hanken Grotesk Fallback'` faces in
`src/app.css` exist to kill: a local-aliased stand-in whose box matches the web
font's, so there is nothing to reflow on swap.

This prints the four @capsizecss-formula overrides for each stand-in, computed
from the ACTUAL shipped woff2 against the macOS Georgia/Arial. Paste the numbers
into the two @font-face blocks in src/app.css if a font package is ever bumped.

    python3 scripts/font-fallback-metrics.py

Needs `fonttools` (pip install fonttools) and runs from the frontend/ dir.
"""
from fontTools.ttLib import TTFont

# English letter frequencies — @capsizecss/unpack's weights for `xWidthAvg`,
# the average advance width `size-adjust` matches.
WEIGHTS = {
    'a': 0.0668, 'b': 0.0122, 'c': 0.0228, 'd': 0.0348, 'e': 0.1039, 'f': 0.0182,
    'g': 0.0165, 'h': 0.0499, 'i': 0.0570, 'j': 0.0010, 'k': 0.0063, 'l': 0.0329,
    'm': 0.0197, 'n': 0.0552, 'o': 0.0614, 'p': 0.0158, 'q': 0.0008, 'r': 0.0490,
    's': 0.0518, 't': 0.0741, 'u': 0.0226, 'v': 0.0080, 'w': 0.0193, 'x': 0.0012,
    'y': 0.0162, 'z': 0.0006, ' ': 0.1818,
}

# Web face → the local device font its fallback aliases.
PAIRS = [
    ('Fraunces Fallback',
     'node_modules/@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2',
     '/System/Library/Fonts/Supplemental/Georgia.ttf'),
    ('Hanken Grotesk Fallback',
     'node_modules/@fontsource-variable/hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2',
     '/System/Library/Fonts/Supplemental/Arial.ttf'),
]


def metrics(path):
    f = TTFont(path)
    upm = f['head'].unitsPerEm
    hhea = f['hhea']
    cmap = f.getBestCmap()
    hmtx = f['hmtx']
    adv = total = 0.0
    for ch, w in WEIGHTS.items():
        gid = cmap.get(ord(ch))
        if gid is None:
            continue
        adv += hmtx[gid][0] * w
        total += w
    return dict(upm=upm, ascent=hhea.ascent, descent=hhea.descent,
                lineGap=hhea.lineGap, xavg=adv / total)


def pct(x):
    return f"{round(x * 100, 4)}%"


def overrides(web, fb):
    size_adjust = (web['xavg'] / web['upm']) / (fb['xavg'] / fb['upm'])
    denom = web['upm'] * size_adjust
    return dict(
        size_adjust=pct(size_adjust),
        ascent_override=pct(web['ascent'] / denom),
        descent_override=pct(abs(web['descent']) / denom),
        line_gap_override=pct(web['lineGap'] / denom),
    )


if __name__ == '__main__':
    for family, web_path, fb_path in PAIRS:
        o = overrides(metrics(web_path), metrics(fb_path))
        print(f"@font-face {{  /* {family} */")
        print(f"  size-adjust: {o['size_adjust']};")
        print(f"  ascent-override: {o['ascent_override']};")
        print(f"  descent-override: {o['descent_override']};")
        print(f"  line-gap-override: {o['line_gap_override']};")
        print("}")
