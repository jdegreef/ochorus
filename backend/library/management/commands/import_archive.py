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

# NB: the chapter-marker and running-header patterns below are tuned to the one
# archive book in the catalogue (Clarke's Susanna Wesley). They are provisional,
# not settled infrastructure — a future archive book with spelled-out or numeric
# chapter headings, or a different header style, will need them revisited (or a
# per-book config on BookEntry). The _reflow logic, by contrast, is general.
_CHAPTER = re.compile(r"^\s*CHAPTER\s+[IVXLC]+\.?\s*$", re.I)
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
    starts = [i for i, l in enumerate(lines) if _CHAPTER.match(l)]
    sections: list[tuple[str, str]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start + 1 : end]
        # The first non-furniture line after the marker is the chapter title.
        title = ""
        body_start = 0
        for j, l in enumerate(block):
            if l.strip() and not _BARE_NUM.match(l.strip()):
                title = clean_title(l.strip())
                body_start = j + 1
                break
        body = _reflow(block[body_start:])
        sections.append((title, body))
    return sections


class Command(BaseCommand):
    help = "Import a public-domain book from an Internet Archive OCR text layer."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all archive books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "archive" and (not wanted or b.slug in wanted)]
        unknown = wanted - {b.slug for b in BOOKS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (archive:{entry.source_ref})")
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
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
