"""Build A. B. Simpson's *The Holy Spirit; or, Power from on High* — Part I,
The Old Testament (1895).

The first of the work's two volumes (Part II is `build_power_from_on_high`):
twenty-five chapters tracing the Holy Spirit through the Old Testament, from
the brooding Dove of Genesis to Malachi, which "grew out of a series of Bible
Readings on the Holy Spirit at the Old Orchard Convention of 1894". Public
domain — printed 1895 by the Christian Alliance Publishing Co.

SOURCE. No transcription exists, so this is the OCR of an 1895 copy on the
Internet Archive (`holyspiritorpowe00simp_0`). Its text layer is good but
not clean, and three things are done to it here:

* **Page furniture out, section heads kept.** The book sets running heads in
  capitals with or without a page number ("THE POWER FROM ON HIGH.", "THE HOLY
  SPIRIT IN THE BOOK OF JUDGES. 145"), but it ALSO sets real section heads in
  capitals ("THE MESSAGE OF ELIHU."). A capitals line is furniture when it
  carries a page number, or reads like the book's own title or like one of the
  chapter's repeated heads; otherwise it is a section head and becomes `<h3>`.
* **Chapters split in document order.** The scan misreads two markers
  ("CHHPTER XI.", "CHRPTER XX."), so a marker is any `CH…PTER <numeral>` line
  and the twenty-five are taken in order; titles come from the Contents.
* **OCR repairs from `data/power-from-on-high-old-testament/ocr_fixes.json`**:
  literal `(find, replace)` pairs per chapter, found by aligning this scan with
  a second 1895 copy (`holyspiritorpowe0000simp`) and the Christian
  Publications reprint (`cihm_24365`) — a word two witnesses agree on beats the
  one that differs — then by a full proofread. Held as data beside the command
  because they are editorial, and fetched text must not depend on a scratch
  file (see the book-import skill).

The Preface to Volume I and Stephen Merritt's Introduction (Merritt d. 1917)
open the book, as printed.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/power-from-on-high-old-testament.en.json`, resolving
the existing `a-b-simpson` author. No `catalog.py` entry. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_power_from_on_high_1
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import fetch_text
from library.models import Author, Book, Chapter, Series
from library.titlecase import recase_title

SLUG = "power-from-on-high-old-testament"
AUTHOR_SLUG = "a-b-simpson"
TITLE = "The Holy Spirit, or Power from on High"
SUBTITLE = "Part I: The Old Testament"
PUBLICATION_YEAR = 1895
COVER_COLOR = "#2f4a5a"
ARCHIVE_ID = "holyspiritorpowe00simp_0"
#: The work's two volumes are one ordered series; Part II is position 2.
SERIES_SLUG = "power-from-on-high"
SERIES_POSITION = 1
ATTRIBUTION = (
    "Public domain — Part I first published 1895 by the Christian Alliance "
    "Publishing Co., New York. Text from the Internet Archive scan of an 1895 "
    "copy, checked against a second 1895 copy and the Christian Publications "
    "reprint."
)
DESCRIPTION = (
    "The first volume of Simpson's great study of the Holy Spirit, tracing the "
    "Spirit through the Old Testament in its types, emblems and prophecies — the "
    "brooding Dove, the breath of God, the pillar of cloud and fire, the living "
    "water, the anointing oil — and in the lives of the judges, kings and "
    "prophets, to the last promise of Malachi. Simpson reads every figure as a "
    "picture of what the Holy Spirit longs to be to the believer now. Grew out of "
    "Bible readings at the Old Orchard Convention of 1894."
)

#: The Contents, in order.
CHAPTER_TITLES = [
    "Like a Dove",
    "The Breath of God",
    "The Sword of the Spirit",
    "The Pillar of Cloud and Fire",
    "The Living Water",
    "The Anointing Oil",
    "The Baptism with Fire",
    "The Spirit of Wisdom",
    "The Holy Spirit in the Book of Judges",
    "The Spirit-Filled Man",
    "The Holy Spirit in the Lives of Saul and David",
    "The Holy Spirit in the Book of Proverbs",
    "The Still, Small Voice",
    "The Pot of Oil",
    "The Valley of Ditches",
    "The Spirit of Inspiration",
    "The Holy Spirit in the Book of Joel",
    "The Holy Spirit in the Book of Isaiah",
    "The Holy Spirit in the Life and Testimony of Jeremiah",
    "The Holy Spirit in Ezekiel",
    "The Spirit and the Resurrection",
    "The River of Blessing",
    "The Holy Spirit in the Days of the Restoration",
    "Olive Trees and Golden Lamps",
    "The Last Message of the Holy Ghost to the Old Dispensation",
]

_DATA = Path(__file__).resolve().parent / "data" / SLUG
_MARKER = re.compile(r"^\s*CH\w{1,3}PTER\s+[IVXLY]+\s*[.,]?[\s.]*$")
_BARE_NUM = re.compile(r"^[\s\d.,*•'‘’]*$")
_HYPHEN_EOL = re.compile(r"([A-Za-z])-$")
_WS = re.compile(r"\s+")
_BOOK_HEAD = "THE POWER FROM ON HIGH"
#: A section number printed alone on its line ("III."); OCR reads V as Y.
_NUMERAL = re.compile(r"^\s*([IVXLY]{1,6})\.\s*$")
#: A paragraph whose first word is set in small capitals ("THE use of oil") —
#: the chapter's prose after its verse epigraph, and some section openings.
_SMALL_CAPS_OPEN = re.compile(r"^([A-Z])([A-Z]+)(?=[ ,]+[a-z])")
#: Words set in capitals in their own right, never a small-caps opener: the
#: KJV's LORD/GOD, and section numerals.
_NOT_OPENERS = frozenset({
    "LORD", "GOD", "JEHOVAH", "JAH", "OH", "II", "III", "IV", "VI", "VII", "VIII", "IX",
})
#: 1890s typesetting spaces stops off the word ("picture ; chaos", "wreck !").
_SPACED_STOP = re.compile(r"(?<=[\w”’\)]) +([;:!?])")
#: Library stamps and similar marks the scanner caught on a few pages.
_STAMPS = ("LIBRARY", "UBRAB", "NAZARENE")


def _caps_core(line: str) -> str:
    """The line's letters and spaces, for comparing heads despite OCR noise."""
    return _WS.sub(" ", re.sub(r"[^A-Za-z ]", " ", line)).strip().upper()


def _is_caps(line: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", line)
    return len(letters) >= 3 and letters.isupper()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def _is_furniture(line: str, heads: list[str]) -> bool:
    """A running head, page number or stamp — not text and not a section head."""
    if _BARE_NUM.match(line):
        return True
    if not _is_caps(line):
        return False
    core = _caps_core(line)
    if any(s in core for s in _STAMPS):
        return True
    if re.search(r"\d", line):
        return True
    if _similar(core, _BOOK_HEAD) >= 0.75 or ("POWER" in core and "HIGH" in core):
        return True
    return any(_similar(core, h) >= 0.8 for h in heads)


def _running_heads(lines: list[str], title: str) -> list[str]:
    """The chapter's running heads: its title in capitals, and any capitals
    line it repeats (a running head recurs on every other page; a section head
    is printed once)."""
    counts: dict[str, int] = {}
    for line in lines:
        if _is_caps(line):
            core = _caps_core(re.sub(r"\d", "", line))
            counts[core] = counts.get(core, 0) + 1
    return [_caps_core(title)] + [c for c, n in counts.items() if n >= 2]


def _reflow(lines: list[str], heads: list[str]) -> str:
    """OCR lines → `<p>` paragraphs and `<h3>` section heads."""
    out: list[str] = []
    buf = ""
    head: list[str] = []
    numeral = ""

    def flush() -> None:
        nonlocal buf
        text = _WS.sub(" ", buf).strip()
        if text:
            out.append(f"<p>{text}</p>")
        buf = ""

    def flush_head() -> None:
        nonlocal numeral
        if head:
            text = _WS.sub(" ", " ".join(head)).strip().rstrip(",")
            out.append(f"<h3>{numeral}{text}</h3>" if numeral else f"<h3>{text}</h3>")
            numeral = ""
            head.clear()

    for raw in lines:
        line = raw.strip()
        m = _NUMERAL.match(line)
        if m:
            # Starts a new section: whatever follows (a head or the section's
            # first paragraph) carries the number.
            flush_head()
            flush()
            numeral = m.group(1).replace("Y", "V") + ". "
            continue
        if not line:
            flush_head()
            if buf.rstrip().endswith((".", "!", "?", "”", '"', ":", ";", "’")):
                flush()
            continue
        if _is_furniture(line, heads):
            continue
        if _is_caps(line):
            # A section head (possibly wrapped over two lines). It always starts
            # a block, so a paragraph in progress ends here.
            flush()
            if head and head[-1].endswith("-"):
                head[-1] = head[-1][:-1] + line
            else:
                head.append(line)
            continue
        flush_head()
        sc = _SMALL_CAPS_OPEN.match(line)
        if sc and sc.group(0) not in _NOT_OPENERS:
            # The opening word in small capitals starts the chapter's prose,
            # even where no blank line parts it from the epigraph above.
            flush()
            line = sc.group(1) + sc.group(2).lower() + line[sc.end():]
        if numeral and not buf:
            line = numeral + line
            numeral = ""
        if buf and _HYPHEN_EOL.search(buf.rstrip()):
            buf = _HYPHEN_EOL.sub(r"\1", buf.rstrip()) + line
        else:
            buf = f"{buf} {line}" if buf else line
    flush_head()
    flush()
    return "".join(out)


def _title_case_head(html: str) -> str:
    """Section heads are printed in capitals; set them in title case."""

    def fix(m: re.Match) -> str:
        text = m.group(1).rstrip(".").strip()
        lead = re.match(r"^([IVXL]+\. )?(.*)$", text)
        words = " ".join(w[:1] + w[1:].lower() for w in lead.group(2).split())
        return f"<h3>{lead.group(1) or ''}{recase_title(words)}</h3>"

    return re.sub(r"<h3>(.*?)</h3>", fix, html)


def split_book(text: str) -> list[tuple[str, list[str]]]:
    """(title, raw lines) for the Preface, the Introduction and each chapter."""
    lines = text.split("\n")
    marks = [i for i, line in enumerate(lines) if _MARKER.match(line)]
    if len(marks) != len(CHAPTER_TITLES):
        raise CommandError(f"found {len(marks)} chapter markers, expected {len(CHAPTER_TITLES)}")

    def find(pattern: str, start: int = 0) -> int:
        rx = re.compile(pattern)
        for i in range(start, len(lines)):
            if rx.match(lines[i].strip()):
                return i
        raise CommandError(f"front matter: no line matching {pattern!r}")

    pre = find(r"^PREFACE\s+TO\s+VOLUME")
    intro = find(r"^INTRODUCTION\.?$", pre)
    sign = find(r"^STEPHEN\s+MERRITT\.?$", intro + 2)
    parts = [
        # The Preface's own running head ("PREFACE.") is furniture.
        ("Preface to Volume I", [ln for ln in lines[pre + 1:intro]
                                 if not re.match(r"^PREFACE\.?$", ln.strip())]),
        # Skip the byline under the heading ("BY REV. STEPHEN MERRITT.") and the
        # running head; set the closing signature as a line of text.
        ("Introduction", [
            *(ln for ln in lines[intro + 1:sign]
              if not re.match(r"^(BY\s+REV|INTRODUCTION\.?$)", ln.strip())),
            "", "Stephen Merritt.",
        ]),
    ]
    for n, start in enumerate(marks):
        end = marks[n + 1] if n + 1 < len(marks) else len(lines)
        body = lines[start + 1:end]
        # Drop the heading lines under the marker (the title, in capitals).
        k = 0
        while k < len(body) and (not body[k].strip() or _is_caps(body[k])):
            k += 1
        parts.append((CHAPTER_TITLES[n], body[k:]))
    return parts


def _fixes() -> dict[str, list[list[str]]]:
    path = _DATA / "ocr_fixes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def apply_fixes(order: int, html: str, fixes: dict[str, list[list[str]]]) -> str:
    """The data file's repairs for one chapter. They are written against the
    STORED form of the text — what a proofreader reads — so the caller applies
    them to the settled body, then settles again."""
    for find, replace in fixes.get(str(order), []):
        if html.count(find) != 1:
            raise CommandError(
                f"ch {order}: OCR fix {find!r} matches {html.count(find)} times, not once"
            )
        html = html.replace(find, replace)
    return html


def build_chapters(text: str) -> list[tuple[str, str]]:
    out = []
    for title, raw in split_book(text):
        heads = _running_heads(raw, title)
        html = _title_case_head(_reflow(raw, heads))
        html = _SPACED_STOP.sub(r"\1", html)
        # …and opens and closes quotations off the word too ("“ If", "word ”").
        html = re.sub(r"([“‘]) +(?=\w)", r"\1", html)
        html = re.sub(r"(?<=[\w.,;:!?]) +([”’])(?!\w)", r"\1", html)
        out.append((title, html))
    return out


class Command(BaseCommand):
    help = "Build Simpson's Power from on High, Part I (Old Testament) from the 1895 scan."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        try:
            series = Series.objects.get(slug=SERIES_SLUG)
        except Series.DoesNotExist:
            raise CommandError(
                f"series {SERIES_SLUG!r} not in the DB — loaddata series.json first."
            ) from None

        chapters = build_chapters(fetch_text(ARCHIVE_ID))
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
            "series": series,
            "series_position": SERIES_POSITION,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
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

        fixes = _fixes()
        unknown = set(fixes) - {str(n) for n in range(1, len(chapters) + 1)}
        if unknown:
            raise CommandError(f"ocr_fixes.json names chapters that do not exist: {sorted(unknown)}")
        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            body = settled_chapter_body(SLUG, order, apply_fixes(order, body, fixes))
            wc = word_count(body)
            if order > 2 and wc < 1500:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
