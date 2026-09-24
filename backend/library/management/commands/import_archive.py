"""Ingest a public-domain book from an Internet Archive OCR text layer.

For titles with no CCEL/Gutenberg/Wikisource edition (e.g. Eliza Clarke's 1886
biography of Susanna Wesley — Wikisource has only 5 of its 16 chapters). Each
``source="archive"`` book's ``source_ref`` is the Archive item id; we read its
``<id>_djvu.txt`` and reflow the OCR into chapters.

Reflow is the whole job. A DjVu text layer is hard-wrapped, double-spaced, and
sprinkled with page furniture (bare page numbers and a running header that
interrupt paragraphs) and end-of-line hyphenation. We drop the furniture,
de-hyphenate, and rejoin wrapped lines into paragraphs — a blank line only ends
a paragraph when the text so far ends on terminal punctuation, so a page break
mid-paragraph doesn't split it.

    python manage.py import_archive                        # all archive books
    python manage.py import_archive susanna-wesley-clarke  # one book by slug
"""

from __future__ import annotations

import re

import requests
from django.core.management.base import BaseCommand, CommandError

from library import english_audit
from library.catalog import BOOKS, BookEntry
from library.ingest import clean_title, is_front_matter, upsert_book, word_count

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
METADATA_URL = "https://archive.org/metadata/{item_id}"

#: Below this the scan is pre-modern type — long s, ligatures — and the OCR is
#: noise, not prose. Measured on one book in two printings: the 1651 first
#: edition of Burroughs' *Rare Jewel* gives "Thai through Gods mercy in my
#: afflidion, I find the Graces of Gods Spirit workirtg as ftrongly in me",
#: while the 1878 reprint of Sibbes reads cleanly. The PRINTING decides this,
#: not the work, and archive.org usually holds several.
MIN_PRINTING_YEAR = 1800
#: US public domain is 95 years from publication. A literal rather than a
#: computed date so an import is reproducible and a bump is a reviewed change.
PD_THROUGH_YEAR = 1929
_PD_STATUS = "NOT_IN_COPYRIGHT"
_PD_LICENCE = re.compile(r"creativecommons\.org/publicdomain|/mark/1\.0|/zero/1\.0")

# The header pattern below is still tuned to a house style rather than settled
# infrastructure. The chapter marker is no longer: it accepts "CHAPTER IV." on
# its own line (Clarke's Susanna Wesley) and "Chap. IV. — Signs of one truly
# bruised" with the title on the same line after a dash (Sibbes' Bruised Reed).
# A book that numbers chapters in words or digits will still need this revisited.
_CHAPTER = re.compile(
    # Tolerant in two places, because both halves of a marker get mis-scanned:
    #   the WORD  — "CHAPTEE" (Clarke), "CHAPTEB" (Grosart), plain "Chap."
    #   the NUMERAL — "YI" for VI, where the scanner read V as Y
    # The bracket is Grosart's: a collected-works volume marks its editorial
    # divisions "[CHAPTER XXIV. — All should side with Christ.]". Both halves
    # are still validated below — `_roman` rejects anything that is not a
    # well-formed numeral once the known confusions are undone.
    #   the SEPARATOR — "CHAP, II." / "CHAP... XXV." (Pickering's 1838 Sibbes):
    #     a comma read for the abbreviation's period, or the period smeared into
    #     several. Same confusion class as the numeral ones below.
    #   the LEADING JUNK — "\ CHAP. XXVI.", a stray rule-mark the scanner kept.
    #     Capped at two characters so it cannot reach into prose; the numeral is
    #     still validated by `_roman`.
    #   the FIRST LETTER — "OHAPTEE XXXIV." (Finney's 1876 Memoirs): a display
    #     face's C read as O. No English word opens "ohap".
    #   STACKED I's — "Vm." / "Xn." / "Xin." for VIII / XII / XIII (Finney):
    #     two or three I's fused into one lowercase letter; `_STACKED_I` undoes
    #     it. A capital N or M is not a numeral, and `_roman` still rejects it.
    r"^\s*[\\/|]{0,2}\s*\[?\s*[co]hap\w*[.,]*\s+([IVXLCYilnm|]+)[\s.,:;]*"
    r"(?:[\u2014\u2013-]\s*(.*?))?\s*\]?$", re.I
)
#: A bracketed marker whose OPENING was eaten by the scanner. Grosart's chapter
#: VIII survives only as "B VIII. — Tenderness required in ministers toward
#: young beginners.]" — the tail of "[CHAPTEB". Losing it merges two chapters
#: silently, so the closing bracket plus a dash plus a well-formed numeral is
#: taken as enough evidence. The junk prefix is capped so this cannot reach
#: into prose, and the numeral is still validated by `_roman`.
_CHAPTER_SALVAGE = re.compile(
    r"^.{0,12}?\b([IVXLCYil|]+)\.\s*[\u2014\u2013-]\s*(.+?)\s*\]$", re.I
)

#: Letter-for-letter confusions a page scanner makes inside a roman numeral.
_NUMERAL_OCR = str.maketrans({"Y": "V", "y": "v", "l": "I", "|": "I"})
#: Runs of I's the scanner fused into ONE lowercase letter (see `_CHAPTER`).
_STACKED_I = str.maketrans({"n": "II", "m": "III"})
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_BARE_NUM = re.compile(r"^\s*\d{1,4}\s*$")
#: The printer's own last line. What follows it is the publisher's catalogue
#: and the library's date-due card (Finney's 1876 Memoirs: nine pages of
#: hymnal advertisements), which would otherwise run on as the last chapter.
_THE_END = re.compile(r"^\s*THE\s+END\.?\s*$")
_HYPHEN_EOL = re.compile(r"([A-Za-z])-$")
_HYPHEN_SPACE = re.compile(r"([a-z])-\s+([a-z])")  # OCR split a compound: "fifty- four"
_WS = re.compile(r"\s+")
_DIGIT = re.compile(r"\d")
_NON_LETTER = re.compile(r"[^A-Za-z]")
#: A lone vertical bar is a column rule the scanner kept, not text — it lands
#: between words ("follow not the ways | | | of those men") or dangling at a
#: line end. Stripped per LINE, before the hyphen-join, so it cannot fuse two
#: words together. Pickering's Sibbes has 52; the other two archive scans have
#: none, so this can only help.
_BAR_RULE = re.compile(r"(?<!\S)\|+(?!\S)|\|+(?=\s*$)")
#: The same margin rule read as an OPENING QUOTE instead of a bar. Pickering's
#: 1838 Sibbes sets no quotation marks at all, yet its text layer opens 209 of
#: the Bruised Reed's lines on `‘` or `“` before a letter (15 of them a
#: capital: "‘Christ", "‘When"); most of the 163 `‘` and 15 `“` #1943 shipped
#: were these. Only visible per LINE (the reflow loses the position), and only
#: safe in a work that closes no double quote, which `chapterize` decides.
#: Dropping it also lets the hyphen-join close a word the scan split on the
#: same mark ("con-" / "‘ceits").
_RULE_QUOTE = re.compile(r"^[‘“](?=[A-Za-z])")
#: A running header with OCR-lowercased letters (see `_is_header`): long enough
#: that a share is meaningful, and still at least this share capitals.
_HEADER_MIN_LETTERS = 12
_HEADER_CAPS_SHARE = 0.8
#: How far below a work's title its first chapter may sit and still count as
#: that title's text (rather than a half-title page or a running header).
_PART_HEADING_GAP = 30
#: How many lines a bracketed chapter heading may wrap onto before we stop
#: looking for its closing bracket.
_HEADING_WRAP = 4


def _norm_heading(text: str) -> str:
    """Compare headings ignoring case, punctuation and OCR's doubled spaces."""
    return _WS.sub(" ", re.sub(r"[^A-Za-z0-9 ]", " ", text)).strip().lower()


def _is_header(line: str) -> bool:
    """A running header — a page number plus the book/chapter title in caps
    ("60  SUSANNA WESLEY.", "TEACHING AND TRAINING.  45"). Requiring a page
    number distinguishes it from a letter's signature ("SUSANNA WESLEY.", no
    number, kept as prose) and from an all-caps opening line (has lowercase, so
    its letters-only core is not upper). Tolerates OCR-mangled page digits
    (leading '‘€•*] junk) since those are exactly what break a naive regex.

    Also tolerates a letter or two the scanner LOWERCASED inside the caps —
    Finney's 1876 Memoirs reads "BIRTH AND EARLY EDUCATIOlf. 3" and "8 MEMOIRS
    or CHARLES G. Fli^NEY.", and a strict `isupper()` left hundreds of them in
    the prose. A long line that is still overwhelmingly capitals is a header;
    a small-caps prose opener ("EARLY in the autumn of 1826") is mostly
    lowercase and stays prose."""
    if not _DIGIT.search(line):
        return False
    letters = _NON_LETTER.sub("", line)  # str.isupper() ignores the dropped chars
    if not letters:
        return False
    if letters.isupper():
        return True
    upper = sum(c.isupper() for c in letters)
    return len(letters) >= _HEADER_MIN_LETTERS and upper / len(letters) >= _HEADER_CAPS_SHARE


_ROMAN_CANON = [
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def _to_roman(value: int) -> str:
    out = ""
    for size, sign in _ROMAN_CANON:
        while value >= size:
            out += sign
            value -= size
    return out


def _roman(numeral: str) -> int | None:
    """Roman numeral to int, or None when it is not a well-formed numeral.

    The round-trip check is the point. "XVIL" — how this scan renders XVII —
    parses happily under the usual subtractive rule and comes out as 34, and
    that wrong-but-plausible value poisoned the restart detection below: the
    next real chapter, XVIII, read as a step BACKWARDS and looked like a
    contents list starting over, so 16 of Sibbes' 26 chapters were discarded.
    Re-rendering and comparing rejects the mangled numeral instead.
    """
    numeral = numeral.translate(_STACKED_I).translate(_NUMERAL_OCR).upper()
    total = prev = 0
    for ch in reversed(numeral):
        if ch not in _ROMAN:
            return None
        value = _ROMAN[ch]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    if not total or _to_roman(total) != numeral:
        return None
    return total


def _marker_value(numeral: str, prev: str | None) -> int | None:
    """A chapter marker's number, reading a final "L" as the "I." it may be.

    The scanner often reads a numeral's last I and its period as one "L":
    Finney's 1876 Memoirs heads chapters "CHAPTEE XXL", "VIIL", "XXXIIL", and
    Foote's *Brand Plucked* has "CHAPTER XL" for XI. Most of those are not
    well-formed numerals, so they were dropped and two chapters silently
    merged; "XL" is well-formed and read as 40. Both readings are tried and the
    one that CONTINUES the sequence from ``prev`` wins — so a genuine fortieth
    chapter after XXXIX still reads 40, and a marker that neither reading
    continues keeps its literal value, exactly as before.
    """
    readings = [numeral]
    if numeral.endswith("L"):
        readings.append(numeral[:-1] + "I")
    values = [v for v in map(_roman, readings) if v is not None]
    if not values:
        return None
    after = _roman(prev) if prev else None
    if after is not None and after + 1 in values:
        return after + 1
    return values[0]


#: A contents line trails dot leaders and a page number ("... . . . 1", ". .113").
_LEADERS = re.compile(r"[\s.,'*\u2019\u2018]*\d*\s*$")


def contents_titles(lines: list[str], markers: list[tuple[int, str, str]]) -> dict[int, str]:
    """Chapter number → the title as the book's own CONTENTS page gives it.

    A body heading is set as a wrapped display line and only its first line is
    captured, so it truncates: Sibbes' chapter I reads "The Text opened and
    divided. What the" in the body and "The Text opened and divided. What the
    Reed is, and what the bruising" in the contents. A contents entry is one
    logical line, so it is the complete one.

    That is the ONLY thing the contents page is reliably better at. It is set in
    smaller type and often OCRs worse — Clarke's contents says "BIKTH AND
    ANCESTRY" where her body says "BIRTH" — which is why the caller prefers it
    on LENGTH alone and never on a tie.
    """
    titles: dict[int, str] = {}
    # The next entry, however the OCR spelled it — Clarke's contents page says
    # "CHAPTEE" for eleven of its sixteen lines, which the marker pattern does
    # not match, so without this the wrap-scan swallowed the rest of the page
    # into chapter one's title.
    looks_like_entry = re.compile(r"^\s*chap\w*\.?\s+[IVXLC]+\b", re.I)
    for i, (line_no, numeral, inline) in enumerate(markers):
        value = _roman(numeral)
        if value is None:
            continue
        parts = [inline] if inline else []
        # A contents title may wrap; take following lines until a blank or the
        # next entry. Bounded so a stray marker cannot swallow the front matter.
        end = markers[i + 1][0] if i + 1 < len(markers) else line_no + 4
        for line in lines[line_no + 1 : min(end, line_no + 4)]:
            if not line.strip() or looks_like_entry.match(line):
                break
            parts.append(line.strip())
        # A contents title wraps mid-word ("bruis'" / "ing"); join those without
        # a space, the way _reflow does for the body.
        text = ""
        for part in parts:
            if text and text.rstrip().endswith(("-", "'", "\u2019")):
                text = text.rstrip().rstrip("-'\u2019") + part
            else:
                text = f"{text} {part}" if text else part
        text = _LEADERS.sub("", _WS.sub(" ", text).strip()).strip()
        # A chapter title is a title, not a paragraph. Anything this long means
        # the scan ran two entries together and neither is usable.
        if text and len(text) <= 90:
            titles[value] = clean_title(text)
    return titles


def _find_part_start(lines: list[str], markers: list[tuple[int, str, str]], part: str) -> int:
    """The line where the work named by ``part`` begins inside a volume.

    A collected-works scan prints the work's title more than once — a half-title
    page, then the title again over the opening text, then as a running header
    on every page after. The one that matters is the one the chapters start
    under, so pick the occurrence with a chapter marker just below it. In
    Grosart's Sibbes that is line 10270 (chapter I at 10277) and not the
    half-title 370 lines earlier.
    """
    wanted = _norm_heading(part)
    first_markers = {m[0] for m in markers}
    best = -1
    for i, line in enumerate(lines):
        if _norm_heading(line) != wanted:
            continue
        if any(j in first_markers for j in range(i + 1, i + 1 + _PART_HEADING_GAP)):
            best = i
    return best


def _book_end(lines: list[str], after: int) -> int:
    """Where the last chapter stops: a "THE END." line, else the end of the scan."""
    for i in range(after + 1, len(lines)):
        if _THE_END.match(lines[i]):
            return i
    return len(lines)


def _find_heading(lines: list[str], heading: str, *, after: int) -> int | None:
    """The first line after ``after`` whose text is ``heading``."""
    wanted = _norm_heading(heading)
    for i in range(after + 1, len(lines)):
        if _norm_heading(lines[i]) == wanted:
            return i
    return None


def markers_in_part(
    markers: list[tuple[int, str, str]], start: int, end: int | None = None
) -> list[tuple[int, str, str]]:
    """The chapter markers belonging to one work.

    ``end`` is the line where the next work's heading appears, and is the
    reliable boundary. Falling back to "the next work numbers from I again"
    works only while every marker survives the scan: Grosart's Sibbes loses
    XXVI and XXVII, so without an end the Bruised Reed ran on through The
    Soul's Conflict and finished with a 93,000-word chapter.
    """
    run = [m for m in markers if m[0] > start and (end is None or m[0] < end)]
    if end is not None:
        return run
    for i, (_, numeral, _) in enumerate(run[1:], start=1):
        if _roman(numeral) == 1:
            return run[:i]
    return run


def better_title(body: str, contents: str, *, body_was_inline: bool) -> str:
    """Whichever of the two headings is the complete one.

    The signal is STRUCTURAL, not a comparison of the strings. Where the body
    title sat decides which source is the trustworthy one:

    * On the marker's own line ("Chap. VI. — Gract is minted with Corruptum")
      it is a wrapped display heading and we captured only its first line, so it
      is truncated AND set in the type that OCRs worst. The contents entry is
      one logical line and wins.
    * On its own line below a bare marker (Clarke's "BIRTH AND ANCESTRY" under
      "CHAPTER I.") it is the display heading in full, set large. It wins — her
      contents page reads "BIKTH AND ANCESTRY", which is exactly the kind of
      damage a length comparison cannot see and this rule never asks about.

    Length was the first attempt and it fails on the case that matters: the
    body's "Gract is minted with Corruptum" and the contents' correct "Grace is
    mingled with Corruption" differ by two characters.
    """
    if body_was_inline and contents:
        return contents
    return body or contents


def split_contents_run(
    markers: list[tuple[int, str, str]],
) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """(body markers, contents markers) — the split `drop_contents_run` makes."""
    body = drop_contents_run(markers)
    return body, markers[: len(markers) - len(body)]


def drop_contents_run(markers: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    """Discard a leading table of contents, by its NUMBERING RESTART.

    A scan's contents list matches any chapter-marker pattern as well as the
    body does — that is what it is a list of — and the importer split Sibbes'
    *Bruised Reed* at its contents, producing one chapter from a 26-chapter
    book while every gate stayed green. Line-gap thresholds get this wrong too:
    the LAST contents entry's gap spans the whole of the front matter and looks
    exactly like a real chapter.

    Numbering is the honest signal. A book's chapters ascend; a contents list
    ends and the body starts over at I. So find the last place the numbering
    goes backwards and keep only what follows it. Markers the OCR mangled past
    parsing are carried along rather than treated as a restart.
    """
    restart = 0
    for i, (_, numeral, _) in enumerate(markers[1:], start=1):
        # Only a return to ONE is a restart. Any other backwards step is an OCR
        # misread or a stray marker in the front matter, and cutting the book
        # there would throw away everything before it.
        if _roman(numeral) == 1:
            restart = i
    return markers[restart:]


def metadata(item_id: str) -> dict:
    """The item's metadata. archive.org publishes this as an API, so unlike
    Gutenberg — whose search page asks not to be scraped — nothing here parses
    HTML."""
    resp = requests.get(
        METADATA_URL.format(item_id=item_id), headers={"User-Agent": USER_AGENT}, timeout=60
    )
    resp.raise_for_status()
    return resp.json()


def printing_year(meta: dict) -> int | None:
    """The year of THIS printing, from whichever date field the item carries."""
    for key in ("year", "date", "publicdate"):
        m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", str(meta.get(key, "")))
        if m:
            return int(m.group(1))
    return None


def public_domain_reason(meta: dict) -> tuple[bool, str]:
    """(is_public_domain, why) — the licence gate, with its reasoning kept.

    Unlike CCEL and Gutenberg, whose whole catalogues are public domain, an
    archive.org identifier can be anything at all, including a book that is
    merely lendable. So this is the one source that needs a gate.

    Three items probed while writing this had three different shapes: an
    explicit NOT_IN_COPYRIGHT status; a CC public-domain licenseurl; and
    Ramabai's 1888 *High-Caste Hindu Woman*, which carries neither and nothing
    but a date. So age has to be an accepted signal or genuinely public-domain
    scans get refused — while an explicit status of anything else has to beat
    age, or a modern edition of an old work slips through on its subject's.
    """
    status = str(meta.get("possible-copyright-status", "")).strip()
    if status and status.upper() != _PD_STATUS:
        return False, f"archive.org records copyright status {status!r}"
    if status.upper() == _PD_STATUS:
        return True, "archive.org records NOT_IN_COPYRIGHT"
    if _PD_LICENCE.search(str(meta.get("licenseurl", ""))):
        return True, f"public-domain licence {meta.get('licenseurl')}"
    year = printing_year(meta)
    if year is None:
        return False, "no printing year on the item, and no explicit status"
    if year <= PD_THROUGH_YEAR:
        return True, f"printed {year}, US public domain (through {PD_THROUGH_YEAR})"
    return False, f"printed {year}, after {PD_THROUGH_YEAR} and with no PD status"


def fetch_text(item_id: str) -> str:
    url = f"https://archive.org/download/{item_id}/{item_id}_djvu.txt"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=90)
    resp.raise_for_status()
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _reflow(lines: list[str], *, rule_quotes: bool = False) -> str:
    """Turn hard-wrapped OCR lines into clean <p>…</p> HTML.

    ``rule_quotes``: drop `_RULE_QUOTE` marks (see there).
    """
    paras: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        text = _WS.sub(" ", buf).strip()
        # Rejoin a hyphenated compound the OCR split with a space ("fifty- four").
        # Lowercase-both-sides only, so a spaced dash used as punctuation is safe.
        text = _HYPHEN_SPACE.sub(r"\1-\2", text)
        if text:
            paras.append(text)
        buf = ""

    for raw in lines:
        line = _BAR_RULE.sub(" ", raw).strip()
        if rule_quotes:
            line = _RULE_QUOTE.sub("", line)
        if not line or _BARE_NUM.match(line) or _is_header(line):
            # Page furniture / blank: end the paragraph only if it reads complete;
            # otherwise it's a page break inside a paragraph — keep accumulating.
            if buf.rstrip().endswith((".", "!", "?", "”", '"', ":", ";")):
                flush()
            continue
        if buf and _HYPHEN_EOL.search(buf.rstrip()):
            buf = _HYPHEN_EOL.sub(r"\1", buf.rstrip()) + line  # join hyphenated word
        else:
            buf = f"{buf} {line}" if buf else line
    flush()
    return "".join(f"<p>{p}</p>" for p in paras)


def chapterize(text: str, part: str = "", part_end: str = "") -> list[tuple[str, str]]:
    """Split the OCR text into (title, body_html) at each CHAPTER marker.

    ``part`` narrows the split to ONE work inside a collected-works volume,
    named by the heading it is printed under. Sibbes, Owen, Manton and Charnock
    are all mainly available that way, and the collected editions are far
    better-produced scans than the standalone printings — Grosart's Sibbes
    prints "All should side with Christ" where the 1878 standalone OCRs it as
    "^// should side with Christ".
    """
    lines = text.split("\n")
    markers: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = _CHAPTER.match(stripped) or _CHAPTER_SALVAGE.match(stripped)
        value = _marker_value(m.group(1), markers[-1][1] if markers else None) if m else None
        if value is not None:
            # A bracketed heading that has not closed by the end of its line
            # continues onto the next: "[CHAPTER I. — The Text opened and
            # divided. What the Reed is, and what" / "the Bruising.]". Take the
            # rest of it, or it reads as the chapter's opening words.
            title = (m.group(2) or "").strip()
            spans = 0
            if stripped.startswith("[") and not stripped.endswith("]"):
                for j in range(i + 1, min(i + 1 + _HEADING_WRAP, len(lines))):
                    nxt = lines[j].strip()
                    # A page break can fall inside the heading, so a blank line
                    # does not end it — chapters I, IX and XXI all wrap across
                    # one. The closing bracket is what ends it.
                    if not nxt:
                        continue
                    if _CHAPTER.match(nxt) or _CHAPTER_SALVAGE.match(nxt):
                        break
                    title = f"{title} {nxt.rstrip(']')}".strip()
                    spans = j - i
                    if nxt.endswith("]"):
                        break
            # The CANONICAL numeral, so every later `_roman` call agrees with
            # the reading `_marker_value` chose.
            markers.append((i + spans, _to_roman(value), _WS.sub(" ", title).strip()))
    if part:
        # Scope to one work first: a volume's other treatises have their own
        # chapter I, which the contents-run rule below would read as a restart.
        start = _find_part_start(lines, markers, part)
        if start < 0:
            raise CommandError(f"part {part!r} is not a heading in this item")
        end = _find_heading(lines, part_end, after=start) if part_end else None
        if part_end and end is None:
            raise CommandError(f"part_end {part_end!r} is not a heading after {part!r}")
        markers, contents = markers_in_part(markers, start, end), []
        part_limit = end
        # Asked of the WORK, not the volume: Pickering's Sibbes closes no quote
        # in the Bruised Reed, and 23 in the preface and treatises around it.
        rule_quotes = "”" not in "\n".join(lines[start:end])
    else:
        markers, contents = split_contents_run(markers)
        part_limit = None
        rule_quotes = "”" not in text
    from_contents = contents_titles(lines, contents)

    sections: list[tuple[str, str]] = []
    for n, (start, numeral, inline_title) in enumerate(markers):
        end = markers[n + 1][0] if n + 1 < len(markers) else (part_limit or _book_end(lines, start))
        block = lines[start + 1 : end]
        if inline_title:
            # "Chap. IV. — Signs of one truly bruised": the title is on the
            # marker line and the body starts immediately.
            title, body_start = clean_title(inline_title), 0
        else:
            # The first non-furniture line after the marker is the chapter title.
            title = ""
            body_start = 0
            for j, line in enumerate(block):
                if line.strip() and not _BARE_NUM.match(line.strip()):
                    title = clean_title(line.strip())
                    body_start = j + 1
                    break
        value = _roman(numeral)
        title = better_title(
            title,
            from_contents.get(value, "") if value else "",
            body_was_inline=bool(inline_title),
        )
        body = _reflow(block[body_start:], rule_quotes=rule_quotes)
        sections.append((title, body))
    return sections


class Command(BaseCommand):
    help = "Import a public-domain book from an Internet Archive OCR text layer."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all archive books).")
        parser.add_argument(
            "--inspect",
            metavar="ITEM_ID",
            help="Print an item's licence verdict and an OCR sample; import nothing.",
        )

    def handle(self, *args, **opts):
        if opts.get("inspect"):
            return self._inspect(opts["inspect"])
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "archive" and (not wanted or b.slug in wanted)]
        unknown = wanted - {b.slug for b in BOOKS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _inspect(self, item_id: str):
        """Read the OCR before trusting it.

        The 1651-versus-1878 difference is invisible in a catalogue entry and
        obvious in three lines of the text itself, so choosing a printing has to
        be a thing someone does with their eyes before an entry is written.
        """
        meta = metadata(item_id).get("metadata", {})
        ok, why = public_domain_reason(meta)
        year = printing_year(meta)
        self.stdout.write(f"  title  : {str(meta.get('title', ''))[:70]}")
        self.stdout.write(f"  creator: {str(meta.get('creator', ''))[:70]}")
        self.stdout.write(f"  printed: {year}")
        self.stdout.write(f"  licence: {'PD' if ok else 'NOT PD'} — {why}")
        if year is not None and year < MIN_PRINTING_YEAR:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ printed {year}, before {MIN_PRINTING_YEAR} — expect pre-modern type "
                "and unusable OCR. Look for a later printing."
            ))
        try:
            body = fetch_text(item_id)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  no OCR text: {exc}"))
            return
        middle = _WS.sub(" ", body[len(body) // 2 : len(body) // 2 + 700]).strip()
        self.stdout.write("  --- OCR sample from the middle of the book ---")
        self.stdout.write("  " + middle[:600])

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (archive:{entry.source_ref})")
        try:
            meta = metadata(entry.source_ref).get("metadata", {})
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  metadata fetch failed: {exc}"))
            return
        if not meta:
            self.stderr.write(self.style.ERROR(f"  no such item: {entry.source_ref}"))
            return
        ok, why = public_domain_reason(meta)
        if not ok:
            self.stderr.write(self.style.ERROR(f"  REFUSED — {why}"))
            return
        year = printing_year(meta)
        if year is not None and year < MIN_PRINTING_YEAR:
            self.stderr.write(self.style.ERROR(
                f"  REFUSED — printed {year}, before the {MIN_PRINTING_YEAR} floor; "
                "pre-modern type does not OCR. Find a later printing."
            ))
            return
        try:
            text = fetch_text(entry.source_ref)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
            return
        sections = [
            (t, b)
            for t, b in chapterize(text, entry.part, entry.part_end)
            if not is_front_matter(t) and word_count(b) >= 120
        ]
        if not sections:
            self.stderr.write(self.style.ERROR("  no chapters found"))
            return
        book = upsert_book(entry, sections)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters  ({why})"))
