"""Build *Journal of an Expedition up the Niger* — Samuel Crowther's 1854 journal.

This is an Internet Archive OCR text (`journalofexpedit00crow`, printed 1855, US
public domain) that the general `import_archive` cannot chapter cleanly:

  * the body's **Chapter I marker is lost** inside a garbled map-scan page, so a
    marker-driven split starts one chapter short;
  * the printing sets a long ALL-CAPS **précis** under each "CHAP. N" heading
    (identical to the Contents), which `contents_titles` scrambles into the wrong
    bodies; and
  * the running header and its page number sit on **separate lines**
    ("ARRIVAL AT FERNANDO PO." then "5"), so `import_archive._is_header` — which
    needs the digit on the same line — leaves the bare ALL-CAPS header to leak
    into the prose.

So this command splits the five chapters at explicit, verified anchors and reuses
`import_archive`'s OCR reflow, extended to drop a bare ALL-CAPS line as furniture.
It drops the front matter, the Society's preface, and the appended official
letters of Laird and Baikie, keeping only Crowther's own journal.

Fixture-driven like every other book: `seed_books` creates it (with its chapters
and author) on the next deploy from
`fixtures/content/books/journal-of-an-expedition-up-the-niger.en.json`. This
command GENERATES that fixture reproducibly — run it, then serialize the row (see
the book-import skill). It is idempotent: re-running replaces the book's chapters.

    DJANGO_DEBUG=true uv run python manage.py build_niger_journal
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import (
    _BARE_NUM,
    _HYPHEN_EOL,
    _HYPHEN_SPACE,
    _NON_LETTER,
    _WS,
    _is_header,
    fetch_text,
)
from library.models import Author, Book, Chapter

SLUG = "journal-of-an-expedition-up-the-niger"
TITLE = "Journal of an Expedition up the Niger"
SUBTITLE = "Up the Niger and Tshadda Rivers, 1854"
AUTHOR_SLUG = "samuel-ajayi-crowther"
ARCHIVE_ID = "journalofexpedit00crow"
COVER_COLOR = "#1b5e57"  # deep river teal — house-style cover ground
SOURCE_URL = f"https://archive.org/details/{ARCHIVE_ID}"

DESCRIPTION = (
    "In 1854 Samuel Crowther — a Yoruba boy once carried down this same coast in "
    "a slave ship, now an ordained missionary — steamed up the Niger and Tshadda "
    "rivers aboard the <em>Pleiad</em>, on the first such expedition to come home "
    "without losing a man to fever. This is his own day-by-day journal of the "
    "voyage: the towns and chiefs he met, the trade and the slavery he witnessed, "
    "the Scriptures he read to kings, and his longing to see the gospel and the "
    "freed people of Sierra Leone return to the interior of Africa."
)

ATTRIBUTION = (
    "Public domain — first published London, 1855. Samuel Crowther's journal of "
    "the 1854 Niger and Tshadda expedition; the volume's official preface and the "
    "appended letters of Macgregor Laird and Dr. Baikie are omitted."
)

# The five chapters, in reading order. Titles are the lead clause of each
# chapter's Contents précis (the printed "titles" are paragraph-long summaries),
# lightly cleaned. Order is a public contract (PlanDay, saved positions,
# prerendered URLs).
TITLES = [
    "Departure from Abbeokuta",
    "Entrance of the Tshadda",
    "Interview with the Chief of Zhibu",
    "Return of the Expedition",
    "Sickness at the Confluence",
]


def _is_allcaps(line: str) -> bool:
    """A bare running header / précis line: its letters are (almost) all capitals.

    Diary prose is mixed-case, so a mostly-uppercase LINE is page furniture — the
    running header ("ARRIVAL AT FERNANDO PO.") or the chapter précis restated
    under the marker. `import_archive._is_header` misses these because the page
    number sits on its own line here, not beside the caps.

    The threshold is a ratio, not a strict `.isupper()`, because the OCR lowercases
    the odd letter inside a caps line ("lYANPE" for IYANPE, "ZURl's" for ZURI's) —
    which a strict test lets leak in glued to the next paragraph. Real prose lines
    are dominated by lowercase, so 0.75 separates them with wide margin.
    """
    letters = _NON_LETTER.sub("", line)
    if len(letters) < 3:
        return False
    upper = sum(c.isupper() for c in letters)
    return upper / len(letters) >= 0.75


def _furniture(line: str) -> bool:
    if not line:
        return True
    if not re.search(r"[A-Za-z0-9]", line):  # OCR speck (punctuation only)
        return True
    return bool(_BARE_NUM.match(line)) or _is_header(line) or _is_allcaps(line)


def _reflow(lines: list[str]) -> str:
    """`import_archive._reflow`, with a bare ALL-CAPS line treated as furniture."""
    paras: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        text = _HYPHEN_SPACE.sub(r"\1-\2", _WS.sub(" ", buf).strip())
        if text:
            paras.append(text)
        buf = ""

    for raw in lines:
        line = raw.strip()
        if _furniture(line):
            # End the paragraph only if it reads complete; otherwise a page break
            # fell mid-paragraph (header + number between "…Baptist" and
            # "missionary…") — keep accumulating so the sentence rejoins.
            if buf.rstrip().endswith((".", "!", "?", "”", '"', ":", ";")):
                flush()
            continue
        if buf and _HYPHEN_EOL.search(buf.rstrip()):
            buf = _HYPHEN_EOL.sub(r"\1", buf.rstrip()) + line
        else:
            buf = f"{buf} {line}" if buf else line
    flush()
    return "".join(f"<p>{p}</p>" for p in paras)


# --- OCR repair -------------------------------------------------------------
# This 1855 DjVu scan is the cleaner of the two on Archive (the Google copy has
# 9× the caret noise), but it still mangles text systematically: it drops a
# spurious caret into words, turns an 'r' into an apostrophe, and fuses or swaps
# the odd letter. Each fix below is anchored to ONE garbled spelling and was
# resolved from its context — none guesses at a word the scan doesn't otherwise
# make plain. The apostrophe RULES use the class ['’] so one rule matches
# whichever quote glyph the scanner happened to use for that word.

_APOS_RULES: list[tuple[str, str]] = [
    # apostrophe standing in for a dropped 'r' (the dominant pattern)
    (r"\bFi['’]om\b", "From"), (r"\bfi['’]om\b", "from"), (r"\bfi['’]o\b", "fro"),
    (r"\bfi['’]equent\b", "frequent"), (r"\bfi['’]iendship\b", "friendship"),
    (r"\bfi['’]iend\b", "friend"), (r"\bfii['’]e\b", "fire"), (r"\bfii['’]st\b", "first"),
    (r"\bmai['’]ket\b", "market"), (r"\bwei['’]e\b", "were"), (r"\bwhei['’]e\b", "where"),
    (r"\banchoi['’]ed\b", "anchored"), (r"\bci['’]eek\b", "creek"),
    (r"\bdi['’]essed\b", "dressed"), (r"\bdi['’]ink\b", "drink"),
    (r"\bpi['’]esents\b", "presents"), (r"\bcui['’]rent\b", "current"),
    (r"\bcai['’]e\b", "care"), (r"\bdishonoui['’]ed\b", "dishonoured"),
    (r"\bconsidei['’]able\b", "considerable"), (r"\bgi['’]ound\b", "ground"),
    (r"\bsevei['’]al\b", "several"), (r"\bcompi['’]ises\b", "comprises"),
    (r"\binciu['’]ring\b", "incurring"), (r"\bti['’]ees\b", "trees"),
    (r"\bgi['’]eater\b", "greater"), (r"\bgi['’]eat\b", "great"),
    (r"\bcb['’]ead\b", "dread"), (r"\bmox['’]e\b", "more"),
    (r"\bimpoi['’]tance\b", "importance"), (r"\bbi['’]oad\b", "broad"),
    (r"\bbi['’]ing\b", "bring"), (r"\bcashmei['’]e\b", "cashmere"),
    (r"\beffoi['’]ts\b", "efforts"), (r"\bhei['’]e\b", "here"),
    (r"\bevei['’]ything\b", "everything"), (r"\bcowi['’]ies\b", "cowries"),
    (r"\btln['’]ee\b", "three"), (r"\bwi['’]apped\b", "wrapped"),
    (r"\bfoi['’]bid\b", "forbid"), (r"\bentei['’]tained\b", "entertained"),
    (r"\bdiffei['’]ent\b", "different"), (r"\bpiu['’]chase\b", "purchase"),
    (r"\bdesu['’]e\b", "desire"), (r"\bdistm['’]bed\b", "disturbed"),
    (r"\bofi['’]ered\b", "offered"), (r"\bpai['’]ts\b", "parts"),
    (r"\bmanufactm['’]e\b", "manufacture"), (r"\bnatm['’]ally\b", "naturally"),
    (r"\bsecm['’]ed\b", "secured"), (r"\bretm['’]ii\b", "return"),
    (r"\bam['’]ouud\b", "about"),
    # proper nouns the same 'r' → apostrophe damage hit
    (r"\bAfi['’]ica\b", "Africa"), (r"\bEui['’]opean\b", "European"),
    (r"\bI['’]iver\b", "River"), (r"\bI['’]ocks\b", "rocks"),
    (r"\bI['’]ospccting\b", "respecting"), (r"\bIgai['’]a\b", "Igara"),
    (r"\bIgbix['’]a\b", "Igbira"), (r"\bIkei['’]eku\b", "Ikereku"),
    (r"\bKoi['’]orofa\b", "Kororofa"), (r"\bOgai['’]a\b", "Ogara"),
    (r"\bOssamai['’]e\b", "Ossamare"), (r"\bQuoi['’]ra\b", "Quorra"),
    (r"\bRichai['’]ds\b", "Richards"), (r"\bSai['’]iki\b", "Sariki"),
    (r"\bSiei['’]ra\b", "Sierra"), (r"\bTi['’]otter\b", "Trotter"),
    (r"\bZui['’]i\b", "Zuri"), (r"\bAi['’]afro\b", "Arafro"),
    (r"\brelatiA['’]es\b", "relatives"),
    # a spurious apostrophe after 'w' (an 'r' was NOT dropped here — the letter
    # simply reads with a stray mark); only before a vowel/'h', so a possessive
    # like "cow's" is never touched
    (r"\bw['’]e\b", "we"), (r"\bW['’]as\b", "Was"), (r"\bw['’]as\b", "was"),
    (r"\bw['’]ater\b", "water"), (r"\bw['’]hite\b", "white"), (r"\bw['’]ho\b", "who"),
    (r"\bw['’]hich\b", "which"), (r"\bw['’]ord\b", "word"), (r"\bw['’]orship\b", "worship"),
    (r"\bw['’]ould\b", "would"), (r"\bw['’]eigh\b", "weigh"),
    (r"\bw['’]eapons\b", "weapons"), (r"\bw['’]ar\b", "war"), (r"\bw['’]ere\b", "were"),
    (r"\bAA['’]hat\b", "What"), (r"\bAA['’]hy\b", "Why"),
    (r"\bAvhei['’]cupon\b", "whereupon"),
    # spans where an apostrophe garble sits amid other damage
    (r"\bk['’]li['’]\.", "Mr."),
    (r"j:\)m['’]chase", "purchase"),
    (r"Tliei['’]cn\]\)on Igara", "Thereupon Igara"),
    (r"\baa['’]c anchored", "we anchored"),
    (r"gave ['’]i['’]shukuma", "gave Shukuma"),
    (r"\bA['’]illage\b", "village"),
    (r"['’]\^bhose", "Those"), (r"\^Ii['’]\. Richards", "Mr. Richards"),
]

_LITERAL: list[tuple[str, str]] = [
    # two running headers flushed into the prose (their OCR lowercased a letter,
    # so they slipped under the caps-furniture ratio)
    ("<p>THE ATTA’S daughters.</p>", ""),
    ("towns PUT IN AMA’S keeping.</p><p>and villages", "towns and villages"),
    # the stray caret, sprinkled through the text ~24×: spurious inside a word
    # ("w^as"), or standing in for a capital M ("^londay", "^Ir.")
    ("j^et", "yet"), ("July^4t:", "July 4:"), ("w^as", "was"), ("w^e", "we"),
    ("^Ir.", "Mr."), ("^Mahamma", "Mahamma"), ("Al^pama", "Alpama"),
    ("^londay", "Monday"), ("Batw^ Anasara", "Batwa Anasara"), ("W^hen", "When"),
    ("w^aited", "waited"), ("*^vhich", "which"), ("did n^h like", "did not like"),
    ("the deng^ and", "the denge and"), ("down the^ river", "down the river"),
    ("the shij^,", "the ship,"), ("^lany of", "Many of"),
    ("on the ri^ht side", "on the right side"), ("feet, ar^d the", "feet, and the"),
    ("his ai^pearance.", "his appearance."), ("Salvation of ^lan,", "Salvation of Man,"),
    # mixed-case fusions and letter swaps
    ("AkraAtani", "Akra Atani"), ("AmaAbokko", "Ama-Abokko"), ("DiboU", "Diboll"),
    ("LandeFs", "Lander's"), ("MitshL I asked", "Mitshi. I asked"), ("aU", "all"),
    ("accomjDany", "accompany"), ("chfF", "chief"), ("cliiePs house", "chief's house"),
    ("coiTect", "correct"), ("couTies", "cowries"), ("gToup", "group"),
    ("jDointed", "pointed"), ("knoAV", "know"), ("knoAvledge", "knowledge"),
    ("noAV", "now"), ("noAv", "now"), ("occuiDying", "occupying"), ("olF", "off"),
    ("purK chase", "purchase"), ("reHved", "revived"), ("tOAvn", "town"),
    ("visitsAnother", "visits. Another"), ("wiU", "will"),
    # plain letter-substitution slips (incl. the author's own signature)
    ("INIr.", "Mr."), ("aneliored", "anchored"), ("wRo can", "who can"),
    ("Samuel Crowthee.", "Samuel Crowther."), ("helow the Aboh", "below the Aboh"),
    ("lanowao-e", "language"), ("measuriiur", "measuring"),
    # OCR scanned an opening double-quote on the ship's name as two open-singles,
    # and a possessive apostrophe as a closing double-quote.
    ("‘‘Pleiad", "“Pleiad"), ("two days” sail", "two days’ sail"),
]


# Words the scanner broke across a line/page and rejoined WITH the hyphen (or
# other furniture) still inside, plus a few phrase-level slips. Applied first and
# in order, since they span what the word rules would otherwise see as fragments.
_SPAN_FIXES: list[tuple[str, str]] = [
    ("jom-ney", "journey"), ("intei-ior", "interior"), ("intei-preter", "interpreter"),
    ("thi-ough", "through"), ("bro-wn", "brown"), ("retiu-n", "return"),
    ("fi-inge", "fringe"), ("eng-ao-ed", "engaged"), ("re-inha bited", "reinhabited"),
    ("peo])le", "people"), ("))oor man", "poor man"), ("Ac(;ording", "According"),
    ("))roduce", "produce"), ("j>ain", "pain"), ("neai'", "near"),
    ("May, hir. Richards", "May, Mr. Richards"),
    ("year, \\iz.", "year, viz."), ("iq)on", "upon"), ("wish to confes.s", "wish to confess"),
    ("e.xisting", "existing"), ("T.shuku", "Tshuku"), ("Sv/nday", "Sunday"),
    ("es])ccially", "especially"), ("Baikie hav ing", "Baikie having"),
    ("I bad taken", "I had taken"), ("Indian com", "Indian corn"),
    ("was cnt out", "was cut out"), ("lumps of leadore", "lumps of lead ore"),
    ("fifty slaves, d hese", "fifty slaves, these"), ("the danqi which", "the damp which"),
    ("nice mixture of fiira", "nice mixture of fura"), ("Wulcari halhi", "Wulcari harbi"),
    ("Yauri and liabba", "Yauri and Rabba"), ("of the IModel", "of the Model"),
    ("his ffettinff more", "his getting more"), ("half-past four oniock", "half-past four o'clock"),
    ("F orerunner", "Forerunner"), ("de])arture", "departure"), ("did not apj)ear", "did not appear"),
    ("my exj)lanation", "my explanation"), ("W ukaid", "Wukari"), ("W ukari", "Wukari"),
    ("green alg£B", "green algae"), ("the rio;ht channel", "the right channel"),
    ("Sariki n dolci", "Sariki n doki"), ("came to anchoi'", "came to anchor"),
    ("flooded com fields", "flooded corn fields"), ("fetch com from", "fetch corn from"),
    ("the T.shadda", "the Tshadda"), ("bj' the llcv.", "by the Rev."),
    ("seven p.bi.", "seven p.m."), ("his com]: anions", "his companions"),
    ("gi-eat", "great"), ("ax-e", "axe"), ("Juhj", "July"), ("Septemher", "September"),
    ("Kovemhev", "November"), ("Swnday", "Sunday"), ("Eumour", "Rumour"),
    ("Eogan-Koto", "Rogan-Koto"), ("Eogankoto", "Rogankoto"), ("NVIien", "When"),
    ("INIonday", "Monday"),
]

# Whole-word OCR mis-scans (the scanner read 'h' as 'li', 'm' as 'rn', 'wh' as
# 'wdi'/'wli', and so on). Applied case-insensitively, preserving a leading
# capital, so "witli"/"Witli" both land right. Keys are garbled non-words, so a
# \b-anchored match can only hit the error. Hausa grain names (gero, dawuro) and
# period spellings (surprize, favour) are NOT here — they are correct as printed.
_WORDMAP: dict[str, str] = {
    "aboiit": "about", "abotit": "about", "ahont": "about", "absonce": "absence",
    "accorchngly": "accordingly", "adliered": "adhered", "alrearly": "already",
    "amve": "arrive", "amved": "arrived", "anival": "arrival", "arcliers": "archers",
    "aseend": "ascend", "beacb": "beach", "bemnning": "beginning", "biunt": "blunt",
    "birilt": "built", "brilhant": "brilliant", "brotlier": "brother", "btit": "but",
    "calcidating": "calculating", "cntcrtahicd": "entertained", "coimtry": "country",
    "conntry": "country", "coidd": "could", "countiy": "country", "covuies": "cowries",
    "cpme": "come", "damjj": "damp", "desfrous": "desirous", "destiaictiou": "destruction",
    "discouree": "discourse", "dming": "during", "eaidy": "early", "earthern": "earthen",
    "eighed": "weighed", "embarkiug": "embarking", "eould": "could", "eople": "people",
    "erceive": "perceive", "estabhshment": "establishment", "evenirig": "evening",
    "exjilain": "explain", "fhe": "the", "fiiel": "fuel", "fiom": "from", "flelds": "fields",
    "foimer": "former", "fonned": "formed", "gloiy": "glory", "groiind": "ground",
    "hav": "have", "heavil": "heavily", "heen": "been", "hese": "these", "higli": "high",
    "hmidred": "hundred", "hoiase": "house", "hoius": "hours", "httle": "little",
    "iinjnwed": "uninjured", "imder": "under", "imderstood": "understood",
    "imjjossible": "impossible", "industiy": "industry", "industriou": "industrious",
    "influeirce": "influence", "infonnant": "informant", "inqiihe": "inquire",
    "inquhed": "inquired", "inuiiediately": "immediately", "iuhabitants": "inhabitants",
    "iuncture": "juncture", "jierformed": "performed", "joimney": "journey",
    "jouniey": "journey", "klere": "where", "liave": "have", "liimself": "himself",
    "liis": "his", "liim": "him", "liow": "how", "liowever": "however",
    "mieht": "might", "miglit": "might", "moniing": "morning", "mth": "with",
    "mucli": "much", "munber": "number", "naore": "more", "ninning": "running",
    "occujiy": "occupy", "occujjied": "occupied", "ofif": "off", "oidy": "only",
    "oiir": "our", "oirr": "our", "ojien": "open", "ojiponents": "opponents",
    "ojiposite": "opposite", "opjiortuuity": "opportunity", "opmion": "opinion",
    "otlier": "other", "partieulars": "particulars", "peciiliarity": "peculiarity",
    "peojde": "people", "perfonned": "performed", "ractlsed": "practised",
    "recejitiou": "reception", "retimn": "return", "retiumed": "returned",
    "retixrn": "return", "retmned": "returned", "retnm": "return", "retum": "return",
    "risit": "visit", "rnmour": "rumour", "roceedings": "proceedings",
    "ropensities": "propensities", "salubriousncss": "salubriousness", "sailoi": "sailor",
    "shij": "ship", "shoidd": "should", "sistei": "sister", "slie": "she",
    "snltan": "sultan", "stnick": "struck", "sufiered": "suffered", "svithout": "without",
    "tauglit": "taught", "tfiere": "there", "theti": "then", "tliat": "that",
    "tliem": "them", "tlieni": "them", "tlierefore": "therefore", "tliey": "they",
    "tliough": "though", "tliree": "three", "tomi": "town", "toolc": "took",
    "uffien": "when", "undei": "under", "understanditm": "understanding",
    "unfortimately": "unfortunately", "unfortunatelv": "unfortunately", "vdth": "with",
    "veiy": "very", "verj": "very", "vve": "we", "vvould": "would", "wbicli": "which",
    "wdiere": "where", "wdiether": "whether", "wdiich": "which", "wdiite": "white",
    "wdio": "who", "wdiom": "whom", "wdth": "with", "wdthout": "without",
    "weigli": "weigh", "weirt": "went", "whicli": "which", "witli": "with",
    "wliat": "what", "wliich": "which", "wlio": "who", "wltliin": "within",
    "wmmen": "women", "woidd": "would", "woiild": "would", "worshij": "worship",
    "wth": "with", "enquiiy": "enquiry", "bidlock": "bullock", "opeix": "open", "wns": "was", "iier": "her", "laige": "large",
    "sancl": "sand", "neighbovu": "neighbour", "accomjianied": "accompanied",
    "messencrers": "messengers", "mifinished": "unfinished", "xmder": "under",
    "lakfe": "lake", "rantly": "instantly", "anchoi": "anchor", "tlie": "the",
    "tliis": "this", "sked": "asked",
}

# Proper-noun mis-scans — always capitalised, never case-derived from the match.
# Several are fixed to the spelling that DOMINATES the same text (Richards,
# Hamaruwa, Baikie, Tshukuma), which is how they're known to be mis-scans.
_NAMEMAP: dict[str, str] = {
    "iviohamma": "Mohamma", "iviitshi": "Mitshi", "iviitshis": "Mitshis",
    "imitshi": "Mitshi", "imitshis": "Mitshis", "klitshi": "Mitshi",
    "hlitshis": "Mitshis", "iliehards": "Richards", "llichards": "Richards",
    "jvloorish": "Moorish", "vvukari": "Wukari", "llogan": "Rogan",
    "imodel": "Model", "imr": "Mr", "klr": "Mr", "lyanpe": "Iyanpe",
    "ignoama": "Ignoama", "ilaussa": "Haussa", "ilaussas": "Haussas",
    "ilamaruwa": "Hamaruwa", "jlamaruwa": "Hamaruwa", "eichards": "Richards",
    "kichards": "Richards", "ptichards": "Richards", "eabba": "Rabba",
    "eobertson": "Robertson", "bailde": "Baikie", "avillicrforce": "Wilberforce",
    "tshukiima": "Tshukuma", "tsbukiima": "Tshukuma", "tsliukuma": "Tshukuma",
    "tshuknma": "Tshukuma",
}

# Fused compounds the printing set with a hyphen.
_HYPHENATE: dict[str, str] = {
    "halfpast": "half-past", "palmoil": "palm-oil", "marketday": "market-day",
    "landingplace": "landing-place", "canoevoyage": "canoe-voyage",
    "roughmade": "rough-made", "safetyvalve": "safety-valve",
    "selfimportance": "self-importance", "newlybuilt": "newly-built",
    "allsufficient": "all-sufficient",
}


_PATTERN_CACHE: dict[int, re.Pattern] = {}


def _apply_map(html: str, mapping: dict[str, str], *, force_cap: bool = False) -> str:
    if not mapping:
        return html
    pat = _PATTERN_CACHE.get(id(mapping))
    if pat is None:
        keys = sorted(map(re.escape, mapping), key=len, reverse=True)
        pat = _PATTERN_CACHE[id(mapping)] = re.compile(r"\b(" + "|".join(keys) + r")\b", re.I)

    def repl(m: re.Match) -> str:
        fix = mapping[m.group(0).lower()]
        if force_cap or m.group(0)[:1].isupper():
            return fix[:1].upper() + fix[1:]
        return fix

    return pat.sub(repl, html)


# The scanner also read a word-initial 'w' as 'Av' (and once 'AY'/'OAv'), which
# wears a spurious capital A — so the fix must NOT take its case from the match.
# Capitalise only when the word actually opens a sentence.
_AV_WORDS: dict[str, str] = {
    "avas": "was", "avhen": "when", "avhich": "which", "avould": "would",
    "avere": "were", "avent": "went", "avords": "words", "avho": "who",
    "avell": "well", "avhom": "whom", "avomen": "women", "avith": "with",
    "avorthy": "worthy", "aveigh": "weigh", "ayith": "with", "oavn": "own",
}


def _fix_av(html: str) -> str:
    pat = re.compile(r"\b(?:A[vVY]\w+|OAvn)\b")

    def repl(m: re.Match) -> str:
        fix = _AV_WORDS.get(m.group(0).lower())
        if fix is None:  # a real word (Available, Ayrshire …) — leave it
            return m.group(0)
        prev = html[: m.start()].rstrip()
        return fix.capitalize() if (not prev or prev[-1] in '.!?”"') else fix

    return pat.sub(repl, html)


def _repair(html: str) -> str:
    """Undo the scan's systematic OCR damage. Idempotent: every rule is anchored
    to a garbled spelling that no longer exists once the rule has run."""
    for old, new in _SPAN_FIXES:
        html = html.replace(old, new)
    for pat, rep in _APOS_RULES:
        html = re.sub(pat, rep, html)
    for old, new in _LITERAL:
        html = html.replace(old, new)
    html = _fix_av(html)
    html = _apply_map(html, _WORDMAP)
    html = _apply_map(html, _HYPHENATE)
    html = _apply_map(html, _NAMEMAP, force_cap=True)
    return html


def _chapter_bounds(lines: list[str]) -> list[int]:
    """The six line indices bounding the five chapters, at verified anchors.

    Chapter I has no usable marker (lost in a map-scan page), so it starts at its
    first diary entry; II–V start at their "CHAP./CHAPTER N" markers (the printing
    switches from "CHAP." to "CHAPTER" partway through); the fifth ends at the
    appendix. Anchors are searched, not hard-coded to line numbers, so a re-OCR
    that shifts the pagination still resolves.
    """

    def norm(s: str) -> str:
        return _WS.sub(" ", s).strip().upper()

    start = next((i for i, ln in enumerate(lines) if norm(ln).startswith("JUNE 17")), None)
    if start is None:
        raise CommandError("Chapter I anchor ('June 17') not found in the OCR text.")

    bounds = [start]
    prev = start
    for roman in ["II", "III", "IV", "V"]:
        # The whole stripped line must BE the marker ("CHAP. II", "CHAPTER IV.") —
        # trailing punctuation only — so a body sentence that opens "Chapter IV of
        # …" can't be mistaken for the boundary.
        pat = re.compile(r"^CHAP(?:TER)?\b[^A-Za-z0-9]*" + roman + r"\b[.,)\s]*$", re.I)
        idx = next((i for i in range(prev + 1, len(lines)) if pat.match(lines[i].strip())), None)
        if idx is None:
            raise CommandError(f"Chapter {roman} marker not found after line {prev}.")
        bounds.append(idx)
        prev = idx

    end = next(
        (i for i in range(prev + 1, len(lines)) if norm(lines[i]).startswith("APPENDIX")),
        None,
    )
    if end is None:
        raise CommandError("Appendix anchor (end of Chapter V) not found.")
    bounds.append(end)
    return bounds


class Command(BaseCommand):
    help = "Build Crowther's Niger journal from Archive OCR (dev DB); then serialize the fixture."

    @transaction.atomic  # a mid-run abort rolls back, never a partial book
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"Author {AUTHOR_SLUG!r} is not in this database — run "
                "`manage.py seed_if_empty` first."
            ) from None

        lines = fetch_text(ARCHIVE_ID).split("\n")
        bounds = _chapter_bounds(lines)

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        for order, title in enumerate(TITLES, start=1):
            block = lines[bounds[order - 1] : bounds[order]]
            body = settled_chapter_body(SLUG, order, clean_fragment(_repair(_reflow(block))))
            wc = word_count(body)
            if wc < 1000:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:40]:40} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
