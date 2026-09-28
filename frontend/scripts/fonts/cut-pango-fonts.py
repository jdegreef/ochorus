"""Cut the static TTFs the build-time share cards set their text in with Pango.

    cd frontend && python3 scripts/fonts/cut-pango-fonts.py   # needs fontTools + brotli

Pango (inside sharp) reads fonts through fontconfig, which cannot use the app's
woff2 files, and cannot pick an instance out of a variable font. So each face a
card needs is decompressed from the SAME @fontsource package the app loads and,
where it is variable, pinned at the one instance the card uses. One file per
script subset: fontconfig falls through them per glyph, so a Luganda title's
"ŋ" (latin-ext) and its Latin letters come from the one family.

Committed, not run at build: the build machine need not have Python.
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).parent
MODULES = HERE.parent.parent / 'node_modules'
OUT = HERE / 'pango'

# (package, woff2 name pattern, subsets, variable-axis instance or None, output stem)
FACES = [
    ('@fontsource-variable/fraunces', 'fraunces-{s}-full-normal', ['latin', 'latin-ext'],
     {'wght': 600, 'opsz': 72, 'SOFT': 0, 'WONK': 0}, 'Fraunces-SemiBold'),
    ('@fontsource-variable/fraunces', 'fraunces-{s}-full-normal', ['latin', 'latin-ext'],
     {'wght': 400, 'opsz': 72, 'SOFT': 0, 'WONK': 0}, 'Fraunces-Regular'),
    ('@fontsource-variable/fraunces', 'fraunces-{s}-full-italic', ['latin', 'latin-ext'],
     {'wght': 400, 'opsz': 72, 'SOFT': 0, 'WONK': 1}, 'Fraunces-Italic'),
    ('@fontsource-variable/hanken-grotesk', 'hanken-grotesk-{s}-wght-normal', ['latin', 'latin-ext'],
     {'wght': 500}, 'HankenGrotesk-Medium'),
    ('@fontsource/pt-serif', 'pt-serif-{s}-700-normal', ['cyrillic', 'cyrillic-ext'], None, 'PTSerif-Bold'),
    ('@fontsource/pt-serif', 'pt-serif-{s}-400-normal', ['cyrillic', 'cyrillic-ext'], None, 'PTSerif-Regular'),
    ('@fontsource/pt-serif', 'pt-serif-{s}-400-italic', ['cyrillic', 'cyrillic-ext'], None, 'PTSerif-Italic'),
    ('@fontsource/pt-sans', 'pt-sans-{s}-400-normal', ['cyrillic', 'cyrillic-ext'], None, 'PTSans-Regular'),
    ('@fontsource/amiri', 'amiri-{s}-700-normal', ['arabic'], None, 'Amiri-Bold'),
    ('@fontsource/amiri', 'amiri-{s}-400-normal', ['arabic'], None, 'Amiri-Regular'),
    ('@fontsource/noto-sans-arabic', 'noto-sans-arabic-{s}-400-normal', ['arabic'], None, 'NotoSansArabic-Regular'),
    ('@fontsource/tiro-devanagari-hindi', 'tiro-devanagari-hindi-{s}-400-normal', ['devanagari'], None, 'TiroDevanagariHindi-Regular'),
    ('@fontsource/noto-sans-devanagari', 'noto-sans-devanagari-{s}-400-normal', ['devanagari'], None, 'NotoSansDevanagari-Regular'),
    ('@fontsource/noto-serif-ethiopic', 'noto-serif-ethiopic-{s}-700-normal', ['ethiopic'], None, 'NotoSerifEthiopic-Bold'),
    ('@fontsource/noto-serif-ethiopic', 'noto-serif-ethiopic-{s}-400-normal', ['ethiopic'], None, 'NotoSerifEthiopic-Regular'),
    ('@fontsource/noto-sans-ethiopic', 'noto-sans-ethiopic-{s}-400-normal', ['ethiopic'], None, 'NotoSansEthiopic-Regular'),
]

OUT.mkdir(exist_ok=True)
for package, pattern, subsets, instance, stem in FACES:
    for subset in subsets:
        font = TTFont(MODULES / package / 'files' / f'{pattern.format(s=subset)}.woff2')
        font.flavor = None
        if instance:
            axes = {a.axisTag for a in font['fvar'].axes}
            font = instancer.instantiateVariableFont(
                font, {k: v for k, v in instance.items() if k in axes}
            )
        out = OUT / f'{stem}-{subset}.ttf'
        font.save(out)
        print(f'{out.name}  {out.stat().st_size // 1024} KB')
