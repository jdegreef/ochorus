"""Fetch a Bible from the ebible mirror and build ONE cleaned verse index.

Worker sessions often cannot reach Take Root (egress policy), but they can reach
the ebible collection mirrored on GitHub (gracious-tech/fetch_collection). This
script downloads a collection's USFM, parses it into `BOOK C:V -> text`, applies
the collection's known repairs, and writes the index every translator in a job
should quote from:

    uv run python scripts/bible_mirror.py vie_kt /tmp/vie
    # -> /tmp/vie/verses.json, verses.tsv, book_names.json, damaged.json

Repairs are TYPOGRAPHY ONLY — they restore the letters and spacing the mirror
damaged and never change a word. A verse damaged beyond that (text missing, or
another language interleaved) is WITHHELD: it is left out of verses.json and
listed in damaged.json as `key -> {reason, mirror_text}`, so a translator
self-renders it instead of quoting the wrong words. A collection without an
entry in CLEANERS is written as parsed (damaged.json is then `{}`).

Collections with cleaners (fra_lsg's damage is markup, fixed by `parse` itself):

- `fra_lsg` (Louis Segond 1910): every word is `\\w mot|strong="G…"\\w*`, elisions
  are set `qu\\+w*’\\+w il`, and cross-references sit between words with no space
  of their own. `parse` drops the attributes, lets each opening marker own the
  one space after it (USFM's rule), and turns a cross-reference before a word into
  a space — `qu’il`, `Fils unique, afin`.
- `kor_old` (개역): a comma glued to the next word (149 verses); backtick and
  apostrophe quote marks, dropped (the shipped ko books quote 개역 without them);
  a space before `!` / `?`. WITHHELD: Isa 57:15, truncated by an eye-skip between
  its two 겸손한 자, and Deu 22:30, whose text is the English `missing verse`.
  NOT repaired: 17 verses (Pss 3, 10, 15, Deu 2, Ezk 1, ...)
  carry the next verse inline as `[ (Psalms 3:9) … ]` where the mirror's
  versification differs, and some books are a few verses short.
- `por_bpm` (Bíblia Livre = porbrbsl): a footnote closing a `\\wj` span left a space
  before the comma (JHN 3:16, LUK 12:6, LUK 15:8) — fixed by `parse`. WITHHELD:
  all of Jeremiah 49, interleaved line by line with English glosses.
- `amh_amh` (Amharic 1962, UBS; ebible id `amh`; NT only — the OT 404s): 254
  bridged verses (`\\v 1-3` in HEB 12) hold ONLY the last verse's text. All
  WITHHELD, with the range in the reason; they are not split.

`vie_kt` (Cadman's Kinh Thánh, 1925, the `vi` Bible) carries five kinds of damage,
measured over all 31,102 verses on 2026-10-19:

1. VNI leftovers on a word-initial CAPITAL vowel (~2,000 verses): the tone or
   vowel mark arrives as a separate Latin-1 letter — `Aùp-ra-ham` for Áp-ra-ham,
   `Aáy` for Ấy, `Oâng` for Ông, `Aên` for Ăn, `Aét` for Ắt.
2. The vocative `Ớ` lost its O (31 verses): `rằng: ù Sa-tan` is `Ớ Sa-tan`.
3. `ỳ` after k/K/hu arrives as a closing quote: `k”` (≈180), `hu”nh`.
4. Four verses are cp1258 mojibake (Gen 40:12, 40:18, Isa 55:8, Matt 6:10), and
   Matt 6:10 and the Genesis pair also lost a leading `Ý`; they are restored
   whole from Cadman.
5. Psalm 2:8 ends with a stray word (` vãi`).
   The mojibake pass must leave a genuine capital `Ò` alone: decoding `CÒN` (the
   divine title of Rev 1:4, 1:8 and 4:8) as cp1258 yields `C` + a stray combining
   hook, so a "repair" that leaves a combining mark unattached is refused.

The book-name headings (`\\toc1`) in this mirror are modernised (La-mã, Khải thị);
the verse text is classic Cadman (Rô-ma, Khải Huyền in the text itself), so cite
with the traditional names, not these.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MIRROR = (
    "https://raw.githubusercontent.com/gracious-tech/fetch_collection/master/bibles"
)

# USFM book codes, in canonical order. The mirror's file names are LOWERCASE
# (`usfm/jhn.usfm`); `JHN.usfm` 404s.
BOOKS = [
    "GEN",
    "EXO",
    "LEV",
    "NUM",
    "DEU",
    "JOS",
    "JDG",
    "RUT",
    "1SA",
    "2SA",
    "1KI",
    "2KI",
    "1CH",
    "2CH",
    "EZR",
    "NEH",
    "EST",
    "JOB",
    "PSA",
    "PRO",
    "ECC",
    "SNG",
    "ISA",
    "JER",
    "LAM",
    "EZK",
    "DAN",
    "HOS",
    "JOL",
    "AMO",
    "OBA",
    "JON",
    "MIC",
    "NAM",
    "HAB",
    "ZEP",
    "HAG",
    "ZEC",
    "MAL",
    "MAT",
    "MRK",
    "LUK",
    "JHN",
    "ACT",
    "ROM",
    "1CO",
    "2CO",
    "GAL",
    "EPH",
    "PHP",
    "COL",
    "1TH",
    "2TH",
    "1TI",
    "2TI",
    "TIT",
    "PHM",
    "HEB",
    "JAS",
    "1PE",
    "2PE",
    "1JN",
    "2JN",
    "3JN",
    "JUD",
    "REV",
]


# --------------------------------------------------------------------------- #
# vie_kt
# --------------------------------------------------------------------------- #

_TONE = {"ù": "́", "ø": "̀", "û": "̉", "õ": "̃", "ï": "̣"}
_CIRC_TONE = {"á": "́", "à": "̀", "å": "̉", "ã": "̃", "ä": "̣"}
_BREVE_TONE = {"é": "́", "è": "̀", "ú": "̉", "ü": "̃", "ë": "̣"}

# A capital vowel at the start of a word, followed by a VNI mark letter.
_VNI_CAPITAL = re.compile(r"(?<!\w)([AEIOU])([ùøûõïâêáàåãäéèúüë])")
# A standalone ù is the vocative Ớ with its O dropped.
_VOCATIVE = re.compile(r"(?<!\w)ù(?=[\s,])")
_KY = re.compile(r"(?<!\w)([Kk])”")
# Tokens carrying cp1258 mojibake (Latin-1 letters that never occur in Vietnamese).
_MOJIBAKE = re.compile(r"\S*[ðÞÌÒÐ]\S*|\S*ý[õò]\S*|\S*õ[ÌÒòì]\S*")

_VIE_WHOLE = {
    "MAT 6:10": "Nước Cha được đến; Ý Cha được nên, ở đất như trời!",
    "GEN 40:12": "Giô-sép nói: Ý-nghĩa chiêm bao đó là thể nầy: Ba nhành nho tức là ba ngày.",
    "GEN 40:18": "Giô-sép đáp rằng: Ý-nghĩa chiêm bao nầy là, ba giỏ, tức là ba ngày.",
    "ISA 55:8": (
        "Đức Giê-hô-va phán: Ý tưởng ta chẳng phải ý tưởng các ngươi, "
        "đường lối các ngươi chẳng phải đường lối ta."
    ),
    "PSA 2:8": (
        "Hãy cầu ta, ta sẽ ban cho Con các ngoại bang làm cơ nghiệp, "
        "Và các đầu cùng đất làm của cải."
    ),
}


def _vni_capital(m: re.Match) -> str:
    base, mark = m.group(1), m.group(2)
    if mark in _TONE:
        marks = _TONE[mark]
    elif mark == "â":
        marks = "̂"  # Oâ -> Ô, Eâ -> Ê, Aâ -> Â
    elif mark == "ê":
        marks = "̆" if base == "A" else "̂"  # Aê -> Ă
    elif mark in _CIRC_TONE:
        marks = "̂" + _CIRC_TONE[mark]  # Aá -> Ấ
    elif mark in _BREVE_TONE and base == "A":
        marks = "̆" + _BREVE_TONE[mark]  # Aé -> Ắ
    else:
        return m.group(0)
    return unicodedata.normalize("NFC", base + marks)


def _mojibake(m: re.Match) -> str:
    word = m.group(0)
    try:
        fixed = unicodedata.normalize("NFC", word.encode("cp1252").decode("cp1258"))
    except (UnicodeEncodeError, UnicodeDecodeError):
        return word
    # A genuine capital Ò (CÒN) decodes to C + U+0309, which no letter absorbs.
    if any(unicodedata.combining(ch) for ch in fixed):
        return word
    return fixed


def clean_vie(text: str) -> str:
    """Repair one vie_kt verse's encoding damage. Idempotent; no word changes."""
    text = _VNI_CAPITAL.sub(_vni_capital, text)
    text = _VOCATIVE.sub("Ớ", text)
    text = _KY.sub(lambda m: m.group(1) + "ỳ", text)
    text = text.replace("hu”nh", "huỳnh")
    return _MOJIBAKE.sub(_mojibake, text)


def clean_vie_index(verses: dict[str, str]) -> dict[str, str]:
    out = {key: clean_vie(text) for key, text in verses.items()}
    out.update({k: v for k, v in _VIE_WHOLE.items() if k in out})
    return out


# --------------------------------------------------------------------------- #
# kor_old
# --------------------------------------------------------------------------- #

# A comma glued to the next word (`하나님,나의`, 149 verses).
_KOR_COMMA = re.compile(r",(?=[^\s\d])")
# The mirror's quote marks are a backtick (open) and an apostrophe (close), used
# loosely both ways; the shipped ko books quote 개역 without them. A mark glued
# between two words is a word space before the verb 하다 (`하라'하고` = `하라 하고`)
# and nothing before a particle or copula (`말하라'고`, `롬'이라`).
_KOR_QUOTE_BEFORE_HA = re.compile(r"(?<=\S)[`'](?=[하한함])")
_KOR_QUOTE = re.compile(r"[`']")
# The mirror spaces off its marks (`하느냐 ?`, ~2,800 verses). A spaced `?` is a
# real question and is glued to its word; a spaced `!` is the mirror's own
# addition — the shipped ko books quote 개역 without it (`범사에 그를 인정하라
# 그리하면` x11, never `인정하라!`) — so it is dropped with its space.
_KOR_SPACED_QUESTION = re.compile(r"\s+(?=\?)")
_KOR_SPACED_BANG = re.compile(r"\s+!")

# Verses the mirror damaged beyond typography. Withheld from the index (a
# translator self-renders them) and written to damaged.json with the reason.
_KOR_DAMAGED = {
    "ISA 57:15": (
        "truncated by an eye-skip between the two 겸손한 자: the mirror reads "
        "'마음이 겸손한 자의 영을 소성케 하려 함이라', dropping the clause between "
        "them. Not restored (no word is supplied from memory)."
    ),
    "DEU 22:30": "the mirror's text is the English placeholder 'missing verse'",
}


def clean_kor(text: str) -> str:
    """Repair one kor_old verse's punctuation. Idempotent; no word changes."""
    text = _KOR_COMMA.sub(", ", text)
    text = _KOR_QUOTE.sub("", _KOR_QUOTE_BEFORE_HA.sub(" ", text))
    text = _KOR_SPACED_BANG.sub("", _KOR_SPACED_QUESTION.sub("", text))
    return re.sub(r"\s+", " ", text).strip()


# Single-letter typos in the mirror that change the word. HEB 12:14 prints 좆으라
# (a vulgarity) for 개역's 좇으라 ("follow"); three shipped ko books had quoted it.
# Each fix names its verse and must match exactly once.
_KOR_TYPOS = {
    "HEB 12:14": ("좆으라", "좇으라"),
}


def clean_kor_index(verses, ranges):
    out = {key: clean_kor(text) for key, text in verses.items()}
    for key, (bad, good) in _KOR_TYPOS.items():
        if key in out and out[key].count(bad) == 1:
            out[key] = out[key].replace(bad, good)
    return _withhold(out, _KOR_DAMAGED)


# --------------------------------------------------------------------------- #
# por_bpm (Bíblia Livre = porbrbsl)
# --------------------------------------------------------------------------- #

# Jeremiah 49 is interleaved line by line with the World English Bible
# (`Leave your fatherless children. “Deixe os seus órfãos.”`) in all 39 verses,
# and the quote marks wrapping the Portuguese cannot be told from the text's own,
# so the Portuguese cannot be recovered mechanically. JER 49 is the only English
# in the collection (scanned for English function words, 2026-11-12).
_POR_DAMAGED_CHAPTERS = {"JER 49": "interleaved with English (WEB) glosses"}


def clean_por_index(verses, ranges):
    damaged = {
        key: reason
        for key in verses
        for chapter, reason in _POR_DAMAGED_CHAPTERS.items()
        if key.startswith(chapter + ":")
    }
    return _withhold(dict(verses), damaged)


# --------------------------------------------------------------------------- #
# amh_amh (Amharic 1962, UBS; NT only — the OT books 404)
# --------------------------------------------------------------------------- #


def clean_amh_index(verses, ranges):
    """Withhold every bridged verse: the mirror holds only its LAST verse's text.

    `\\v 1-3` in HEB 12 is Heb 12:3 alone (`በነፍሳችሁ ዝላችሁ እንዳትደክሙ…`), so keyed
    `HEB 12:1` it would hand a translator the wrong verse. 254 ranges; they are
    not split (which verse the text is would be a guess), only flagged.
    """
    damaged = {
        key: f"bridged {label} in the mirror; its text is only the last verse's"
        for key, label in ranges.items()
    }
    return _withhold(dict(verses), damaged)


def _withhold(verses, reasons):
    """Move the damaged verses out of the index, keeping their text beside the reason."""
    damaged = {
        key: {"reason": reason, "mirror_text": verses.pop(key)}
        for key, reason in reasons.items()
        if key in verses
    }
    return verses, damaged


# collection -> cleaner(verses, ranges) -> (verses, damaged). `ranges` maps a
# bridged verse's key (`HEB 12:1`) to its label (`HEB 12:1-3`); `damaged` maps a
# withheld key to {reason, mirror_text}. fra_lsg needs no entry: its damage
# (Strong's attributes, cross-references, split elisions) is USFM markup, which
# `parse` now strips correctly for every collection.
CLEANERS = {
    "vie_kt": lambda verses, ranges: (clean_vie_index(verses), {}),
    "kor_old": clean_kor_index,
    "por_bpm": clean_por_index,
    "amh_amh": clean_amh_index,
}


# --------------------------------------------------------------------------- #
# Fetch and parse
# --------------------------------------------------------------------------- #


def fetch(collection: str, dest: Path) -> None:
    """Download the collection's USFM files into dest/usfm/ (skips ones present).

    A book the mirror lacks (amh_amh is NT only) 404s and is skipped, not fatal.
    """
    usfm = dest / "usfm"
    usfm.mkdir(parents=True, exist_ok=True)

    def one(code: str) -> None:
        path = usfm / f"{code.lower()}.usfm"
        if path.exists() and path.stat().st_size:
            return
        url = f"{MIRROR}/{collection}/usfm/{code.lower()}.usfm"
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                path.write_bytes(resp.read())
        except urllib.error.HTTPError as err:
            if err.code != 404:
                raise

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, BOOKS))


# Headings and metadata: skipped wherever they fall. Every other line marker
# (`\p`, `\q1`, `\m`, `\li`, `\pi`, `\nb`, `\cls`, ...) starts a paragraph or
# poetry line whose text belongs to the verse it continues —
# `\q1 Phép tắc nhân từ ở nơi lưỡi nàng.` is the second half of Prov 31:26.
_HEADING = re.compile(
    r"\\(?:id|ide|usfm|h|toca?[0-9]*|rem|sts|mte?[0-9]*|ms[0-9]*|mr|s[0-9]*|sr|sd[0-9]*"
    r"|sp|r|d|b|cl|cd|cp|qa|fp|periph"
    r"|i(?:b|e|ex|li|m|mi|mq|mt|mte|o|or|ot|p|pi|pq|pr|q|s)[0-9]*)(?:\s|$)"
)
# The paragraph marker opening a line (not `\v`, which may follow it).
_PARAGRAPH = re.compile(r"\\(?!v\s)[a-z]+[0-9]*(?:\s+|$)")
# Footnotes are dropped whole. A cross-reference before a word becomes a SPACE:
# fra_lsg sets one between two words with no space of its own
# (`unique,\x …\x*afin`), so dropping it welds them (`unique,afin`). One before
# punctuation (por_bpm: `louvor\x …\x*, ou seja`) is dropped like a footnote.
# The choice is made once the markers around it are gone (a sentinel stands in),
# and collapsing whitespace removes the space wherever one stood already.
_XREF = re.compile(r"\\x\s(?:(?!\\x\*).)*\\x\*")  # never runs past its own \x*
_XREF_MARK = "\x00"
_XREF_BEFORE_PUNCT = re.compile(_XREF_MARK + r"+(?=[,.;:!?)\]’”»]|$)")
_FOOTNOTE = re.compile(r"\\(f|fe)\s.*?\\\1\*")
# Character markers keep their text (`\tl Ma-ra-na-tha.\tl*`, `\qs (Sê-la)\qs*`)
# but lose their attributes: fra_lsg tags every word `\w mot|strong="G…"\w*`.
_ATTRIBUTES = re.compile(r"\|[^\\|]*(?=\\\+?[a-z]+[0-9]*\*)")
_CLOSE_MARKER = re.compile(r"\\\+?[a-z]+[0-9]*\*")
# An opening marker owns the ONE space after it (USFM: the space ends the marker
# name; it is not text). Leaving it splits fra_lsg's elisions, which are set
# `qu\+w*’\+w il` (-> `qu’ il`), and leaves por_bpm a space before the comma
# where a footnote closed a `\wj` span (`unigênito\wj*\f …\f*\wj , para`).
_OPEN_MARKER = re.compile(r"\\\+?[a-z]+[0-9]*\s?")


def _strip_inline(text: str) -> str:
    text = _FOOTNOTE.sub("", _XREF.sub(_XREF_MARK, text))
    text = _CLOSE_MARKER.sub("", _ATTRIBUTES.sub("", text))
    text = _OPEN_MARKER.sub("", text)
    return _XREF_BEFORE_PUNCT.sub("", text).replace(_XREF_MARK, " ")


def parse(
    usfm_dir: Path, ranges: dict[str, str] | None = None
) -> tuple[dict[str, str], dict[str, str]]:
    """`BOOK C:V -> text` and `BOOK -> \\toc1 name` from the mirror's USFM.

    A verse's text is its `\\v` line plus any paragraph or poetry lines (`\\q1`,
    `\\p`, `\\m`, ...) that follow it, up to the next `\\v` or `\\c`. Headings
    in between are skipped. A verse range (`\\v 15-16`) is keyed by its first verse;
    pass `ranges` to collect `key -> "BOOK C:15-16"` for each one.
    """
    verses: dict[str, str] = {}
    names: dict[str, str] = {}
    for path in sorted(usfm_dir.glob("*.usfm")):
        book = chapter = key = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if m := re.match(r"\\id (\w+)", line):
                book = m.group(1).upper()
            elif m := re.match(r"\\toc1 (.+)", line):
                names[book] = m.group(1).strip()
            elif m := re.match(r"\\c (\d+)", line):
                chapter, key = m.group(1), None
            elif not _HEADING.match(line):
                if m := _PARAGRAPH.match(line):
                    line = line[m.end() :]
                if m := re.match(r"\\v (\d+)(?:-(\d+))?\s*(.*)", line):
                    key = f"{book} {chapter}:{m.group(1)}"
                    verses[key] = m.group(3)
                    if m.group(2) and ranges is not None:
                        ranges[key] = f"{key}-{m.group(2)}"
                elif key and line:
                    verses[key] += " " + line
    for key, text in verses.items():
        # Some mirrors set the capital Đ as U+00D0 (Ð); Vietnamese needs U+0110.
        text = _strip_inline(text).replace("Ð", "Đ")
        verses[key] = re.sub(r"\s+", " ", text).strip()
    return verses, names


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    collection, dest = argv[1], Path(argv[2])
    fetch(collection, dest)
    ranges: dict[str, str] = {}
    verses, names = parse(dest / "usfm", ranges)
    damaged: dict[str, dict] = {}
    cleaner = CLEANERS.get(collection)
    if cleaner:
        cleaned, damaged = cleaner(dict(verses), ranges)
        changed = sum(cleaned[k] != verses[k] for k in cleaned)
        verses = cleaned
        print(f"{collection}: repaired {changed} verses, withheld {len(damaged)}")
    # Always written (empty when nothing was withheld) so a crib builder can
    # rely on it: a key listed here is NOT in verses.json and must be self-rendered.
    (dest / "damaged.json").write_text(
        json.dumps(damaged, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (dest / "verses.json").write_text(
        json.dumps(verses, ensure_ascii=False), encoding="utf-8"
    )
    (dest / "verses.tsv").write_text(
        "".join(f"{k}\t{v}\n" for k, v in verses.items()), encoding="utf-8"
    )
    (dest / "book_names.json").write_text(
        json.dumps(names, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{collection}: {len(verses)} verses, {len(names)} books -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
