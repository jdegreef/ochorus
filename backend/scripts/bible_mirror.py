"""Fetch a Bible from the ebible mirror and build ONE cleaned verse index.

Worker sessions often cannot reach Take Root (egress policy), but they can reach
the ebible collection mirrored on GitHub (gracious-tech/fetch_collection). This
script downloads a collection's USFM, parses it into `BOOK C:V -> text`, applies
the collection's known repairs, and writes the index every translator in a job
should quote from:

    uv run python scripts/bible_mirror.py vie_kt /tmp/vie
    # -> /tmp/vie/verses.json, /tmp/vie/verses.tsv, /tmp/vie/book_names.json

Repairs are TYPOGRAPHY ONLY — they restore the letters the mirror's encoding
damaged and never change a word. A collection without an entry in CLEANERS is
written as parsed.

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

The book-name headings (`\\toc1`) in this mirror are modernised (La-mã, Khải thị);
the verse text is classic Cadman (Rô-ma, Khải Huyền in the text itself), so cite
with the traditional names, not these.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
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
        return unicodedata.normalize("NFC", word.encode("cp1252").decode("cp1258"))
    except (UnicodeEncodeError, UnicodeDecodeError):
        return word


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


CLEANERS = {"vie_kt": clean_vie_index}


# --------------------------------------------------------------------------- #
# Fetch and parse
# --------------------------------------------------------------------------- #


def fetch(collection: str, dest: Path) -> None:
    """Download the collection's USFM files into dest/usfm/ (skips ones present)."""
    usfm = dest / "usfm"
    usfm.mkdir(parents=True, exist_ok=True)

    def one(code: str) -> None:
        path = usfm / f"{code.lower()}.usfm"
        if path.exists() and path.stat().st_size:
            return
        url = f"{MIRROR}/{collection}/usfm/{code.lower()}.usfm"
        with urllib.request.urlopen(url, timeout=60) as resp:
            path.write_bytes(resp.read())

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
# Footnotes and cross-references are dropped whole; character markers
# (`\tl Ma-ra-na-tha.\tl*`, `\qs (Sê-la)\qs*`) keep their text.
_NOTE = re.compile(r"\\(f|fe|x)\s.*?\\\1\*")
_CHAR_MARKER = re.compile(r"\\\+?[a-z]+[0-9]*\*?")


def _strip_inline(text: str) -> str:
    return _CHAR_MARKER.sub("", _NOTE.sub("", text))


def parse(usfm_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """`BOOK C:V -> text` and `BOOK -> \\toc1 name` from the mirror's USFM.

    A verse's text is its `\\v` line plus any paragraph or poetry lines (`\\q1`,
    `\\p`, `\\m`, ...) that follow it, up to the next `\\v` or `\\c`. Headings
    in between are skipped. A verse range (`\\v 15-16`) is keyed by its first verse.
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
                if m := re.match(r"\\v (\d+)(?:-\d+)?\s*(.*)", line):
                    key = f"{book} {chapter}:{m.group(1)}"
                    verses[key] = m.group(2)
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
    verses, names = parse(dest / "usfm")
    cleaner = CLEANERS.get(collection)
    if cleaner:
        cleaned = cleaner(verses)
        changed = sum(cleaned[k] != verses[k] for k in verses)
        verses = cleaned
        print(f"{collection}: repaired {changed} verses")
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
