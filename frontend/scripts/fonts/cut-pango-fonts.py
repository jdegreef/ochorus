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

# ── Hangul ─────────────────────────────────────────────────────────────────
# Korean's faces ship as ~120 NUMBERED unicode-range slices, not a named
# subset, so there is no one woff2 to decompress. Merge the slices back into
# one font, then keep only the 2,350 syllables of KS X 1001 (every Hangul
# syllable EUC-KR can encode, which covers ordinary modern Korean) plus ASCII
# and the punctuation the cards set: ~1.4 MB a face, where all 11,172
# syllables would be several times that, committed. A rarer syllable falls
# through fontconfig like any missing glyph.
#
# The slices carry a wrong family name ("Noto Serif KR ExtraLight" on the 700
# slices, in fontsource 5.3.0), and fontconfig matches by family + weight, so
# the name table is rewritten to what card-kit's stacks ask for.
from fontTools.merge import Merger
from fontTools import subset as _subset

KS_X_1001 = ''.join(
    chr(c) for c in range(0xAC00, 0xD7A4) if len(chr(c).encode('euc_kr', 'ignore')) == 2
)
HANGUL_TEXT = KS_X_1001 + ''.join(map(chr, range(0x20, 0x7F))) + '·…—–“”‘’『』「」〈〉《》'

# (package, weight, family, style, output stem)
HANGUL = [
    ('@fontsource/noto-serif-kr', 700, 'Noto Serif KR', 'Bold', 'NotoSerifKR-Bold'),
    ('@fontsource/noto-serif-kr', 400, 'Noto Serif KR', 'Regular', 'NotoSerifKR-Regular'),
    ('@fontsource/noto-sans-kr', 400, 'Noto Sans KR', 'Regular', 'NotoSansKR-Regular'),
]

for package, weight, family, style, stem in HANGUL:
    slug = package.split('/')[1]
    slices = sorted((MODULES / package / 'files').glob(f'{slug}-[0-9]*-{weight}-normal.woff2'))
    ttfs = []
    for i, woff2 in enumerate(slices):
        font = TTFont(woff2)
        font.flavor = None
        path = OUT / f'.{stem}-slice-{i}.ttf'
        font.save(path)
        ttfs.append(str(path))
    font = Merger().merge(ttfs)
    for path in ttfs:
        Path(path).unlink()
    options = _subset.Options()
    options.layout_features = ['*']
    options.name_IDs = ['*']
    subsetter = _subset.Subsetter(options)
    subsetter.populate(text=HANGUL_TEXT)
    subsetter.subset(font)
    names = font['name']
    for record in list(names.names):
        if record.nameID in (1, 2, 4, 6, 16, 17):
            names.removeNames(nameID=record.nameID)
    names.setName(family, 1, 3, 1, 0x409)
    names.setName(style, 2, 3, 1, 0x409)
    names.setName(f'{family} {style}', 4, 3, 1, 0x409)
    names.setName(f'{family.replace(" ", "")}-{style}', 6, 3, 1, 0x409)
    font['OS/2'].usWeightClass = weight
    out = OUT / f'{stem}-hangul.ttf'
    font.save(out)
    print(f'{out.name}  {out.stat().st_size // 1024} KB')
