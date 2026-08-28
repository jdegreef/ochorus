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
    r"^\s*chap(?:ter)?\.?\s+([IVXLC]+)\.?\s*(?:[\u2014\u2013-]\s*(.*))?$", re.I
)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_BARE_NUM = re.compile(r"^\s*\d{1,4}\s*$")
_HYPHEN_EOL = re.compile(r"([A-Za-z])-$")
_HYPHEN_SPACE = re.compile(r"([a-z])-\s+([a-z])")  # OCR split a compound: "fifty- four"
_WS = re.compile(r"\s+")
_DIGIT = re.compile(r"\d")
_NON_LETTER = re.compile(r"[^A-Za-z]")


def _is_header(line: str) -> bool:
    """A running header — a page number plus the book/chapter title in caps
    ("60  SUSANNA WESLEY.", "TEACHING AND TRAINING.  45"). Requiring a page
    number distinguishes it from a letter's signature ("SUSANNA WESLEY.", no
    number, kept as prose) and from an all-caps opening line (has lowercase, so
    its letters-only core is not upper). Tolerates OCR-mangled page digits
    (leading '‘€•*] junk) since those are exactly what break a naive regex."""
    if not _DIGIT.search(line):
        return False
    letters = _NON_LETTER.sub("", line)  # str.isupper() ignores the dropped chars
    return bool(letters) and letters.isupper()


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
    numeral = numeral.upper()
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


def _reflow(lines: list[str]) -> str:
    """Turn hard-wrapped OCR lines into clean <p>…</p> HTML."""
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
        line = raw.strip()
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


def chapterize(text: str) -> list[tuple[str, str]]:
    """Split the OCR text into (title, body_html) at each CHAPTER marker."""
    lines = text.split("\n")
    markers: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        m = _CHAPTER.match(line.strip())
        if m:
            markers.append((i, m.group(1), (m.group(2) or "").strip()))
    markers = drop_contents_run(markers)

    sections: list[tuple[str, str]] = []
    for n, (start, _, inline_title) in enumerate(markers):
        end = markers[n + 1][0] if n + 1 < len(markers) else len(lines)
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
        body = _reflow(block[body_start:])
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
            for t, b in chapterize(text)
            if not is_front_matter(t) and word_count(b) >= 120
        ]
        if not sections:
            self.stderr.write(self.style.ERROR("  no chapters found"))
            return
        book = upsert_book(entry, sections)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters  ({why})"))
