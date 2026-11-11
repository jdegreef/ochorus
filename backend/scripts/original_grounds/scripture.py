"""The grounds for the Open Word Bible books: a leaf of parchment with the
book's name in the language it was written in.

Each book of the Bible had a name before it had an English one, and the Hebrew
names are its first words: Genesis is Bereshit, "In the beginning"; the Psalms
are Tehillim, "Praises". The Greek names are the titles the manuscripts carry:
Kata Iōannēn, "According to John"; Pros Rhōmaious, "To the Romans". The ground
sets that name large in ink on a pale leaf, low on the cover. `BookCover` sets
the rest over it live, in dark ink from the top (`INK_DARK` and `TYPE_TOP` in
`covers.py` and `coverLayouts.ts`): the byline, the English title, and the
subtitle, which spells the name out and says what it means ("Bereshit, 'In the
beginning'") in the edition's own language.

WORDS ON A GROUND. A ground carries no words because words serve one language
(CLAUDE.md, Covers), and these are the exception that rule allows: the Hebrew or
Greek name is the same for every edition, in no reader's language and in every
one of them, as an inscription in a painting is. Everything a reader needs to
read is drawn live; this is the picture.

Layout, 600x800: the upper half stays a plain, light leaf for the type, which is
set from the top and ends near y=400 even under a long title. The name sits in
the band y=470..650, between two hairline rules with a lozenge, and the foot
under y=690 is clear for the Ochorus mark.

    python3 backend/scripts/original_grounds/scripture.py FONTS OUTDIR [SLUG ...]

FONTS is a folder holding the two @fontsource packages the name is set in:

    npm pack @fontsource/noto-serif-hebrew@5.1.1 @fontsource/eb-garamond@5.1.1
    (untar each into FONTS/<package-name>/)

writes OUTDIR/<slug>.html for each slug (every book with none). Render each at
2x with headless Chromium (600x800 window) and downscale with Pillow to the
committed `frontend/static/covers/art/<slug>.jpg`, which is FROZEN by digest in
`curated_art.ORIGINAL_GROUND`.
"""
import base64
import pathlib
import sys
import unicodedata
from typing import NamedTuple


class Name(NamedTuple):
    #: The name as the cover sets it, top to bottom. Hebrew: the name, and for
    #: the halves of Samuel, Kings and Chronicles its number (א, ב). Greek: a
    #: small first word ("ΚΑΤΑ", "ΠΡΟΣ", or "" for none), the large name, and an
    #: optional small last line (a letter's number, "Α"; Revelation's "ΙΩΑΝΝΟΥ").
    lines: tuple[str, ...]
    #: "he" (Noto Serif Hebrew, right to left) or "grc" (EB Garamond capitals).
    script: str
    #: The ink the name is written in: a deep tint of the book's own colour.
    ink: str


BOOKS: dict[str, Name] = {
    # Bereshit, "In the beginning": the book's first word (Genesis 1:1).
    "genesis": Name(("בְּרֵאשִׁית",), "he", "#6b2f1c"),
    # Tehillim, "Praises": the name the Hebrew Bible gives the book.
    "psalms": Name(("תְּהִלִּים",), "he", "#5a2448"),
    # Kata Iōannēn, "According to John": the title the manuscripts carry.
    "gospel-of-john": Name(("ΚΑΤΑ", "ΙΩΑΝΝΗΝ"), "grc", "#24425a"),
    # Pros Rhōmaious, "To the Romans".
    "romans": Name(("ΠΡΟΣ", "ΡΩΜΑΙΟΥΣ"), "grc", "#1f3a5c"),
    # The rest of the Old Testament: each book's Hebrew name, the halves of
    # Samuel, Kings and Chronicles numbered as the Hebrew numbers them (א, ב).
    "exodus": Name(('שְׁמוֹת',), "he", "#6b3a26"),
    "leviticus": Name(('וַיִּקְרָא',), "he", "#7a4a22"),
    "numbers": Name(('בְּמִדְבַּר',), "he", "#5c4a2a"),
    "deuteronomy": Name(('דְּבָרִים',), "he", "#6a2f2a"),
    "joshua": Name(('יְהוֹשֻׁעַ',), "he", "#4f5a2e"),
    "judges": Name(('שֹׁפְטִים',), "he", "#5a4a2e"),
    "ruth": Name(('רוּת',), "he", "#6b5a2e"),
    "1-samuel": Name(('שְׁמוּאֵל', 'א'), "he", "#3f4a2e"),
    "2-samuel": Name(('שְׁמוּאֵל', 'ב'), "he", "#2e4a3f"),
    "1-kings": Name(('מְלָכִים', 'א'), "he", "#4a3a2e"),
    "2-kings": Name(('מְלָכִים', 'ב'), "he", "#3a2e2e"),
    "1-chronicles": Name(('דִּבְרֵי הַיָּמִים', 'א'), "he", "#2e3a4a"),
    "2-chronicles": Name(('דִּבְרֵי הַיָּמִים', 'ב'), "he", "#2e4a4a"),
    "ezra": Name(('עֶזְרָא',), "he", "#4a3a24"),
    "nehemiah": Name(('נְחֶמְיָה',), "he", "#3a4a24"),
    "esther": Name(('אֶסְתֵּר',), "he", "#5a2a3a"),
    "job": Name(('אִיּוֹב',), "he", "#3a2a1e"),
    "proverbs": Name(('מִשְׁלֵי',), "he", "#5a2f4f"),
    "ecclesiastes": Name(('קֹהֶלֶת',), "he", "#4a2f5a"),
    "song-of-songs": Name(('שִׁיר הַשִּׁירִים',), "he", "#6a2a44"),
    "isaiah": Name(('יְשַׁעְיָהוּ',), "he", "#2c3563"),
    "jeremiah": Name(('יִרְמְיָהוּ',), "he", "#2c3f63"),
    "lamentations": Name(('אֵיכָה',), "he", "#3a2f4a"),
    "ezekiel": Name(('יְחֶזְקֵאל',), "he", "#2c4a63"),
    "daniel": Name(('דָּנִיֵּאל',), "he", "#3a2c63"),
    "hosea": Name(('הוֹשֵׁעַ',), "he", "#2f5559"),
    "joel": Name(('יוֹאֵל',), "he", "#2f4f59"),
    "amos": Name(('עָמוֹס',), "he", "#3f5530"),
    "obadiah": Name(('עֹבַדְיָה',), "he", "#55402f"),
    "jonah": Name(('יוֹנָה',), "he", "#2f4a55"),
    "micah": Name(('מִיכָה',), "he", "#4a2f55"),
    "nahum": Name(('נַחוּם',), "he", "#55302f"),
    "habakkuk": Name(('חֲבַקּוּק',), "he", "#2f5540"),
    "zephaniah": Name(('צְפַנְיָה',), "he", "#40302f"),
    "haggai": Name(('חַגַּי',), "he", "#5a4a2a"),
    "zechariah": Name(('זְכַרְיָה',), "he", "#2a4a5a"),
    "malachi": Name(('מַלְאָכִי',), "he", "#4a2a5a"),
    # The rest of the New Testament: each book's title in the manuscripts, the
    # letters numbered as they number them (Α, Β, Γ).
    "gospel-of-matthew": Name(("ΚΑΤΑ", "ΜΑΘΘΑΙΟΝ"), "grc", "#6b2a2f"),
    "gospel-of-mark": Name(("ΚΑΤΑ", "ΜΑΡΚΟΝ"), "grc", "#7a3b22"),
    "gospel-of-luke": Name(("ΚΑΤΑ", "ΛΟΥΚΑΝ"), "grc", "#5c3b1e"),
    "acts-of-the-apostles": Name(("ΠΡΑΞΕΙΣ", "ΑΠΟΣΤΟΛΩΝ"), "grc", "#6e5420"),
    "1-corinthians": Name(("ΠΡΟΣ", "ΚΟΡΙΝΘΙΟΥΣ", "Α"), "grc", "#3b2f5c"),
    "2-corinthians": Name(("ΠΡΟΣ", "ΚΟΡΙΝΘΙΟΥΣ", "Β"), "grc", "#2f3b5c"),
    "galatians": Name(("ΠΡΟΣ", "ΓΑΛΑΤΑΣ"), "grc", "#1f4a4a"),
    "ephesians": Name(("ΠΡΟΣ", "ΕΦΕΣΙΟΥΣ"), "grc", "#22405e"),
    "philippians": Name(("ΠΡΟΣ", "ΦΙΛΙΠΠΗΣΙΟΥΣ"), "grc", "#5a3a1c"),
    "colossians": Name(("ΠΡΟΣ", "ΚΟΛΟΣΣΑΕΙΣ"), "grc", "#2b4a35"),
    "1-thessalonians": Name(("ΠΡΟΣ", "ΘΕΣΣΑΛΟΝΙΚΕΙΣ", "Α"), "grc", "#2e4a5c"),
    "2-thessalonians": Name(("ΠΡΟΣ", "ΘΕΣΣΑΛΟΝΙΚΕΙΣ", "Β"), "grc", "#3a4a2e"),
    "1-timothy": Name(("ΠΡΟΣ", "ΤΙΜΟΘΕΟΝ", "Α"), "grc", "#4a2e3a"),
    "2-timothy": Name(("ΠΡΟΣ", "ΤΙΜΟΘΕΟΝ", "Β"), "grc", "#3a2e4a"),
    "titus": Name(("ΠΡΟΣ", "ΤΙΤΟΝ"), "grc", "#2e3a4a"),
    "philemon": Name(("ΠΡΟΣ", "ΦΙΛΗΜΟΝΑ"), "grc", "#5b3240"),
    "hebrews": Name(("ΠΡΟΣ", "ΕΒΡΑΙΟΥΣ"), "grc", "#4a2a1e"),
    "james": Name(("", "ΙΑΚΩΒΟΥ"), "grc", "#34502c"),
    "1-peter": Name(("", "ΠΕΤΡΟΥ", "Α"), "grc", "#2c3f5a"),
    "2-peter": Name(("", "ΠΕΤΡΟΥ", "Β"), "grc", "#3f2c5a"),
    "1-john": Name(("", "ΙΩΑΝΝΟΥ", "Α"), "grc", "#24425a"),
    "2-john": Name(("", "ΙΩΑΝΝΟΥ", "Β"), "grc", "#2a4f4a"),
    "3-john": Name(("", "ΙΩΑΝΝΟΥ", "Γ"), "grc", "#4a3a24"),
    "jude": Name(("", "ΙΟΥΔΑ"), "grc", "#4f2a2a"),
    "revelation": Name(("", "ΑΠΟΚΑΛΥΨΙΣ", "ΙΩΑΝΝΟΥ"), "grc", "#2a1f3a"),
}

FONT_FILES = {
    "he": "noto-serif-hebrew/package/files/noto-serif-hebrew-hebrew-600-normal.woff2",
    "grc": "eb-garamond/package/files/eb-garamond-greek-500-normal.woff2",
}


def font_face(fonts: pathlib.Path, script: str) -> str:
    data = base64.b64encode((fonts / FONT_FILES[script]).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'Name {script}';"
        f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
    )


def name_markup(name: Name) -> str:
    """The name, centred in its band: a Hebrew name on one line, or a Greek one
    as an optional small first word (ΚΑΤΑ, ΠΡΟΣ), the large name, and an
    optional small last line (a letter's number, Revelation's ΙΩΑΝΝΟΥ)."""
    if name.script == "he":
        if not 1 <= len(name.lines) <= 2:
            raise ValueError(f"a Hebrew name is 1 or 2 lines, not {name.lines}")
        word, *after = name.lines
        # Letters only: the vowel points are combining marks and take no width.
        letters = sum(unicodedata.category(c) not in ("Mn", "Zs") for c in word)
        # Bereshit and Tehillim keep the size they were drawn at; a longer name
        # (Divrei HaYamim, Shir HaShirim) steps down to stay inside the leaf.
        size = 104 if letters <= 8 and not after else min(88, int(470 / (letters * 0.58)))
        last = f'<div class="small after">{after[0]}</div>' if after else ""
        return (
            f'<div class="he" dir="rtl" lang="he" style="font-size:{size}px">'
            f"{word}</div>{last}"
        )
    if not 2 <= len(name.lines) <= 3:
        raise ValueError(f"a Greek name is 2 or 3 lines, not {name.lines}")
    small, large, *after = name.lines
    # A long name steps down to keep inside the leaf (a capital is ~0.68em wide
    # at this tracking); Pros Rhōmaious and Kata Iōannēn keep the two sizes
    # they were drawn at.
    size = 72 if len(large) <= 7 else min(62, int(500 / (len(large) * 0.68)))
    first = f'<div class="small">{small}</div>' if small else ""
    last = f'<div class="small after">{after[0]}</div>' if after else ""
    return (
        f'<div class="grc" lang="grc">{first}'
        f'<div style="font-size:{size}px">{large}</div>{last}</div>'
    )


def stacked(name: Name) -> bool:
    """Three lines of Greek (ΠΡΟΣ / ΚΟΡΙΝΘΙΟΥΣ / Α), or a Hebrew name with its
    number under it (שְׁמוּאֵל / א): set tighter to hold to the band."""
    if name.script == "he":
        return len(name.lines) == 2
    return len(name.lines) == 3 and all(name.lines)


def page(fonts: pathlib.Path, name: Name) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_face(fonts, name.script)}
html,body{{margin:0;background:#000}}
.leaf{{position:relative;width:600px;height:800px;overflow:hidden;
  background:radial-gradient(120% 90% at 50% 38%,#f4ecda 0,#ece1c8 55%,#dccdae 100%)}}
.leaf svg{{position:absolute;inset:0}}
.band{{position:absolute;left:0;right:0;top:470px;height:180px;display:flex;
  flex-direction:column;align-items:center;justify-content:center;color:{name.ink}}}
.he{{font-family:'Name he',serif;font-weight:600;line-height:1;opacity:.92}}
.grc{{font-family:'Name grc',serif;font-weight:500;line-height:1.05;text-align:center;
  letter-spacing:.06em;opacity:.92}}
.grc .small{{font-size:30px;letter-spacing:.32em;margin-bottom:10px;opacity:.8}}
.grc .small.after{{margin:12px 0 0}}
/* A Hebrew number line is always stacked (`stacked`), so set at its size here. */
.band.three .he + .small.after{{font-family:'Name he',serif;font-size:28px;margin-top:4px;opacity:.8;text-align:center}}
.name{{margin:22px 0}}
/* Three lines (ΠΡΟΣ / ΚΟΡΙΝΘΙΟΥΣ / Α) hold to the same band, y=470..650, with
   tighter margins and a smaller first and last line. */
.band.three .name{{margin:8px 0}}
.band.three .grc .small{{font-size:24px;margin-bottom:6px}}
.band.three .grc .small.after{{margin:6px 0 0}}
.rule{{display:flex;align-items:center;gap:12px;width:220px;opacity:.55}}
.rule i{{flex:1;height:1px;background:{name.ink}}}
.rule b{{width:7px;height:7px;transform:rotate(45deg);border:1px solid {name.ink}}}
</style></head><body><div class="leaf">
<svg width="600" height="800" viewBox="0 0 600 800" aria-hidden="true">
 <defs>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
   <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/>
   <feColorMatrix values="0 0 0 0 .42  0 0 0 0 .33  0 0 0 0 .2  0 0 0 .07 0"/>
  </filter>
  <filter id="fibre" x="0" y="0" width="100%" height="100%">
   <feTurbulence type="fractalNoise" baseFrequency=".012 .09" numOctaves="3" seed="3"/>
   <feColorMatrix values="0 0 0 0 .45  0 0 0 0 .35  0 0 0 0 .2  0 0 0 .06 0"/>
  </filter>
  <radialGradient id="edge" cx="50%" cy="45%" r="75%">
   <stop offset=".62" stop-color="#6b4a22" stop-opacity="0"/>
   <stop offset="1" stop-color="#6b4a22" stop-opacity=".28"/>
  </radialGradient>
 </defs>
 <rect width="600" height="800" filter="url(#fibre)"/>
 <rect width="600" height="800" filter="url(#grain)"/>
 <rect width="600" height="800" fill="url(#edge)"/>
</svg>
<div class="band{' three' if stacked(name) else ''}"><div class="rule"><i></i><b></b><i></i></div>
<div class="name">{name_markup(name)}</div>
<div class="rule"><i></i><b></b><i></i></div></div>
</div></body></html>"""


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    fonts, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for slug in sys.argv[3:] or BOOKS:
        (out / f"{slug}.html").write_text(page(fonts, BOOKS[slug]), "utf-8")
        print(out / f"{slug}.html")


if __name__ == "__main__":
    main()
