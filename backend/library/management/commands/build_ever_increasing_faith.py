"""Build Smith Wigglesworth's *Ever-Increasing Faith* (1924 first edition).

Source: the Library of Congress copyright-deposit copy on the Internet Archive
(`everincreasingfa00wigg_0`) — title page "Copyright Applied for 1924 by Smith
Wigglesworth", deposit stamp "SEP 16 '24" (©C1A801870). First published 1924,
so US public domain (and Wigglesworth died in 1947, so UK public domain too).
The later "updated" editions (Whitaker House, 1971 on) are revised,
copyrighted texts and are NOT this one; the other scan that calls itself 1924,
`everincreasingfa0000smit`, is a Gospel Publishing House REPRINT (its title
page gives "Springfield 1, Missouri" — a postal zone, so 1943 or later — and
it is reset and lightly copy-edited: "drop that mantle!" for the 1924
"drop that mantle."). That reprint is consulted as the second-printing witness
in QA, never as the text.

Why a build command and not `import_archive`: the chapters are marked well
("CHAPTER IV" over a centred title), but three things in this scan defeat the
generic importer —

* its running heads carry NO page number on the same line ("EVER-INCREASING
  FAITH" on every verso, the chapter title on every recto, the folio on a line
  of its own), so `_is_header` keeps them and they land mid-sentence;
* the end-of-line hyphen is `¬` (U+00AC), which `_HYPHEN_EOL` never sees;
* the testimonies closing several addresses sit under their own centred
  headings ("HEALINGS IN NEW ZEALAND"), which a text reflow flattens into prose.

So this reads the scan's `_djvu.xml` rather than `_djvu.txt`: per LINE it has
the page and the left/right coordinates, which make each of those decidable —
furniture is whatever stands in a page's first two lines (or is a bare folio
on its last), a heading is an all-caps line, and a paragraph opens where the
compositor's first-line indent is (~70 units at 300 dpi, against a margin that
drifts ~30 across a page, so the indent is measured against the NEIGHBOURING
lines, not the page). The text dump's blank lines cannot say whether a page
break falls inside a paragraph; the indent can.

Wigglesworth's addresses were taken down as he spoke them and printed rough.
That roughness is the text: only unambiguous extraction/OCR slips are
repaired, as literal pairs in `corrections.BODY_CORRECTIONS`.

Fixture-driven (`seed_books` creates it on deploy, resolving the existing
`smith-wigglesworth` author from `authors.json`), idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_ever_increasing_faith
"""

from __future__ import annotations

import html as _html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, clean_title, word_count
from library.management.commands.import_archive import USER_AGENT
from library.models import Author, Book, Chapter

SLUG = "ever-increasing-faith"
TITLE = "Ever-Increasing Faith"
AUTHOR_SLUG = "smith-wigglesworth"
ARCHIVE_ID = "everincreasingfa00wigg_0"
PUBLICATION_YEAR = 1924
COVER_COLOR = "#9a3b12"  # fire-orange — house-style cover ground
#: Shelf position: after the last book on the shelf when this was added. Not
#: derivable from a dev DB (which may hold only this book), so hardcoded.
SORT_ORDER = 87

DESCRIPTION = (
    "Eighteen addresses by the Bradford plumber turned evangelist, printed in "
    "1924 as he preached them — messages in tongues and interpretation "
    "included. Wigglesworth's one theme is faith that takes God at His word — "
    "“All things are possible if you will believe” — and he presses it "
    "through the name of Jesus, healing, righteousness and life in the "
    "Spirit, then through Paul's list of the gifts of the Spirit in "
    "1 Corinthians 12, one gift at a time. Plain, blunt and full of stories "
    "from his meetings in Belfast, New Zealand, Australia and Scandinavia, it "
    "closes with a charge to ask, and believe."
)

ATTRIBUTION = (
    "Public domain — first published 1924 (copyright deposit copy, Library of "
    "Congress). Text from the Internet Archive scan everincreasingfa00wigg_0; "
    "checked against a later Gospel Publishing House printing "
    "(everincreasingfa0000smit)."
)

#: The eighteen chapters, from the 1924 TABLE OF CONTENTS. Order IS the
#: reading order. The contents titles are used rather than the body's: the
#: body heads chapter XI "What It Means to Be Full of the Spirit" (and its
#: running head agrees), while the contents — the book's own list — says
#: "Holy Ghost"; and chapter XII's body adds "Holy" before "Spirit".
TITLES = [
    "Have Faith in God",
    "Deliverance to the Captives",
    "The Power of the Name",
    "Wilt Thou Be Made Whole?",
    "I Am the Lord That Healeth Thee",
    "Himself Took Our Infirmities",
    "Our Risen Christ",
    "Righteousness",
    "The Words of This Life",
    "Life in the Spirit",
    "What It Means to Be Full of the Holy Ghost",
    "The Bible Evidence of the Baptism of the Spirit",
    "Concerning Spiritual Gifts",
    "The Word of Knowledge, and Faith",
    "Gifts of Healings, and Miracles",
    "The Gift of Prophecy",
    "The Discerning of Spirits",
    "The Gift of Tongues",
]

#: The in-chapter headings the book prints, all caps and centred: the
#: testimonies that close several addresses, and chapter XIII's first gift.
#: Declared rather than inferred so a stray all-caps line (a running head the
#: OCR varied) fails the build instead of shipping as a heading. Kept as
#: printed — "SCANDANAVIA" is the 1924 spelling (checked on the page image).
SUBHEADS = {
    "HEALINGS IN NEW ZEALAND",
    "BLESSINGS IN AUSTRALIA",
    "REVIVALS IN SCANDANAVIA",
    "BLESSING IN AUSTRALIA",
    "A REMARKABLE HEALING",
    "HUSBAND HEALED OF DOUBLE RUPTURE AND OTHER ILLS",
    "THE WORD OF WISDOM",
}

#: Prose lines that happen to be set in capitals (emphasis inside a
#: paragraph), so the heading test must not take them.
CAPS_PROSE = {
    "SANCTIFIED BY FAITH THAT IS IN ME.”",
}

#: The book's last words. What follows on the scan is the rear endpaper and
#: board, which OCR to noise.
LAST_LINE = re.compile(r"you ask, BELIEVE\.$")

#: A line-end hyphen that belongs to the word, not the line break. Everything
#: else hyphenated at a line end is rejoined without its hyphen. Decided per
#: word: "broken-hearted" is hyphenated mid-line eight times in this text and
#: the later printing; the rest are compounds the scanner itself read as a
#: hard "-" rather than its soft "¬", and which close up into non-words
#: ("thirtyeight", "Spiritgiven").
KEEP_HYPHEN = {
    "broken-hearted",
    "hiding-place",
    "old-time",
    "spirit-given",
    "thirty-eight",
    "wheel-chair",
}

_MARKER = re.compile(r"^CHAPTER\s+([IVXL]+)$")
_FOLIO = re.compile(r"^\W{0,2}\d{1,3}\W{0,2}$")
#: The indent that opens a paragraph, in scan units: the compositor's is
#: ~65-75; a line's drift against its neighbours stays under ~15.
_INDENT = 40
_SOFT_HYPHEN = "¬"
_WS = re.compile(r"\s+")
#: A "word" that is only a speck of margin dirt — a mark that cannot open a
#: line of this book. NOT a dash: a line may open "— they are the devil's
#: traps", and measuring from the word after it reads as an indent.
_SPECK = re.compile(r"^[.,’'`•·■°^]+$")
#: The book sets no straight double quote; one opening a line is a margin mark.
_STRAY_DQUOTE = re.compile(r'^"(?=[A-Z])')
#: A library stamp or bleed-through the scanner read as characters
#: ("^j**i**%*&m&$k ■ 8 -" heads page 123). Only these marks are tested, so a
#: line of bare scripture reference ("12:8,9).") is never taken for noise.
_NOISE_MARK = re.compile(r"[\^%&$■]")
#: A footnote at a page's foot opens on its reference mark: "*“If thou shalt
#: confess with thy mouth JESUS AS LORD," under chapter XIII's "make Jesus
#: Lord.*" — the book's only one.
_FOOTNOTE = re.compile(r"^\*[“‘\"A-Za-z]")


@dataclass
class Line:
    page: int
    index: int  # position on its page
    count: int  # lines on its page
    left: int
    text: str


def fetch_xml(item_id: str) -> str:
    url = f"https://archive.org/download/{item_id}/{item_id}_djvu.xml"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def scan_lines(xml: str) -> list[Line]:
    """Every OCR line of the scan, in reading order, with its page position."""
    root = ET.fromstring(xml)
    out: list[Line] = []
    for page_no, obj in enumerate(root.iter("OBJECT"), start=1):
        rows = []
        for line in obj.iter("LINE"):
            words = [w for w in line.iter("WORD") if (w.text or "").strip()]
            if not words:
                continue
            # Measure the indent from the first real word: a speck the scanner
            # read as "." or "’" in the margin (chapter I's ". These are
            # days") would otherwise pull the line out to the margin and hide
            # the paragraph it opens.
            inked = [w for w in words if not _SPECK.match(w.text.strip())] or words
            left = int(inked[0].get("coords").split(",")[0])
            text = _WS.sub(" ", " ".join(w.text.strip() for w in words)).strip()
            text = _STRAY_DQUOTE.sub("", text)
            rows.append((left, text))
        for i, (left, text) in enumerate(rows):
            out.append(Line(page_no, i, len(rows), left, text))
    return out


def _is_caps(text: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", text)
    return len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) >= 0.8


def _norm(text: str) -> str:
    return _WS.sub(" ", re.sub(r"[^A-Za-z ]", " ", text)).strip().upper()


def _is_furniture(line: Line) -> bool:
    """A folio or a running head (or scanner noise). Both stand at a page's
    top; a chapter's opening page carries its folio at the foot instead."""
    letters = len(re.sub(r"[^A-Za-z]", "", line.text))
    if _NOISE_MARK.search(line.text) and letters < len(line.text.replace(" ", "")) / 2:
        return True
    if _FOLIO.match(line.text):
        # A folio at the foot carries no stop; "1922." ending a testimony's
        # dateline does ("April 15, / 1922."), and must stay prose.
        return line.index <= 1 or (line.index == line.count - 1 and "." not in line.text)
    return line.index <= 1 and _is_caps(line.text)


def _body_markers(lines: list[Line]) -> list[int]:
    """Indices of the eighteen body CHAPTER lines. The contents page lists
    them too ("CHAPTER 1", "CHAPTER II", …) — the body's run is the LAST
    eighteen, and must number I…XVIII in order."""
    marks = [i for i, ln in enumerate(lines) if _MARKER.match(ln.text)]
    body = marks[-len(TITLES):]
    numerals = [_MARKER.match(lines[i].text).group(1) for i in body]
    expected = [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX",
        "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII",
    ]
    if numerals != expected:
        raise CommandError(f"chapter markers read {numerals} — the scan changed.")
    return body


def _join(buf: str, text: str) -> str:
    """Append a line to a paragraph, closing a line-end hyphenation."""
    if not buf:
        return text
    if buf.endswith(_SOFT_HYPHEN) or re.search(r"[A-Za-z]-$", buf):
        head = buf[:-1]
        word = re.search(r"([A-Za-z’']+)$", head)
        tail = re.match(r"([A-Za-z’']+)", text)
        if word and tail and f"{word.group(1)}-{tail.group(1)}".lower() in KEEP_HYPHEN:
            return f"{head}-{text}"
        return head + text
    return f"{buf} {text}"


def _paragraph_starts(block: list[Line]) -> set[int]:
    """Which lines of a chapter open a paragraph, by first-line indent.

    Measured against the nearest lines on the same page (the scan's margin
    drifts ~30 units top to bottom, the indent is ~70): a line opens a
    paragraph when it stands at least `_INDENT` right of the lowest of its
    neighbours. A paragraph's short last line sits AT the margin, so it never
    reads as indented.
    """
    starts: set[int] = set()
    for i, ln in enumerate(block):
        near = [
            o.left
            for o in block[max(0, i - 3) : i + 4]
            if o is not ln and o.page == ln.page
        ]
        if near and ln.left - min(near) >= _INDENT:
            starts.add(i)
    return starts


def _p(text: str) -> str:
    # A soft hyphen still standing is one no following line closed (the
    # paragraph's last line) — print it as the hyphen it is.
    return f"<p>{_html.escape(text.replace(_SOFT_HYPHEN, '-'), quote=False)}</p>"


def chapter_html(block: list[Line]) -> str:
    """One chapter's lines (title already removed) as sanitizer-ready HTML."""
    block = [ln for ln in block if not _is_furniture(ln)]
    # A footnote runs from its marked line to the foot of its page. It is set
    # after the paragraph the page break interrupts, as a reader expects —
    # left in place it would split that paragraph mid-sentence ("through him.
    # I" / "*If thou shalt confess…" / "have gone to many places").
    notes: dict[int, list[Line]] = {}
    for ln in block:
        if ln.page in notes:
            notes[ln.page].append(ln)
        elif ln.index > 1 and _FOOTNOTE.match(ln.text):
            notes[ln.page] = [ln]
    noted = {id(ln) for lines in notes.values() for ln in lines}
    block = [ln for ln in block if id(ln) not in noted]
    starts = _paragraph_starts(block)
    out: list[str] = []
    buf = ""
    heading: list[str] = []
    pending: list[str] = []

    def paragraphs(lines: list[Line]) -> list[str]:
        paras: list[str] = []
        begins = _paragraph_starts(lines)
        text = ""
        for i, ln in enumerate(lines):
            if i in begins and text:
                paras.append(text)
                text = ""
            text = _join(text, ln.text)
        return [*paras, text] if text else paras

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(_p(buf))
            out.extend(pending)
            pending.clear()
        buf = ""

    def flush_heading() -> None:
        if heading:
            text = " ".join(heading)
            if _norm(text) not in SUBHEADS:
                raise CommandError(f"undeclared heading {text!r} — add it to SUBHEADS or CAPS_PROSE")
            out.append(f"<h3>{_html.escape(clean_title(text), quote=False)}</h3>")
            heading.clear()

    last_page = None
    for i, ln in enumerate(block):
        if ln.page != last_page and last_page in notes:
            pending.extend(map(_p, paragraphs(notes[last_page])))
        last_page = ln.page
        if _is_caps(ln.text) and ln.text not in CAPS_PROSE and not LAST_LINE.search(ln.text):
            flush()
            heading.append(ln.text)
            continue
        flush_heading()
        if i in starts:
            flush()
        buf = _join(buf, ln.text)
    if last_page in notes:
        pending.extend(map(_p, paragraphs(notes[last_page])))
    flush()
    flush_heading()
    out.extend(pending)
    return "".join(out)


def chapters(lines: list[Line]) -> list[tuple[str, str]]:
    marks = _body_markers(lines)
    end = next(
        (i for i in range(marks[-1], len(lines)) if LAST_LINE.search(lines[i].text)), None
    )
    if end is None:
        raise CommandError("the book's last line was not found — the scan changed.")
    out: list[tuple[str, str]] = []
    for n, start in enumerate(marks):
        stop = marks[n + 1] if n + 1 < len(marks) else end + 1
        block = lines[start + 1 : stop]
        # The chapter's own title: the caps lines standing directly under the
        # marker (chapter XII's wraps onto a second line, "HOLY SPIRIT").
        # Chapter XIII's "THE WORD OF WISDOM" is a heading, not title.
        k = 0
        while k < len(block) and _is_caps(block[k].text) and _norm(block[k].text) not in SUBHEADS:
            k += 1
        if k == 0:
            raise CommandError(f"chapter {n + 1}: no title under the marker.")
        out.append((TITLES[n], chapter_html(block[k:])))
    return out


class Command(BaseCommand):
    help = "Build Wigglesworth's Ever-Increasing Faith (1924) from the LoC scan (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — "
                "`manage.py loaddata library/fixtures/content/authors.json` first."
            ) from None

        built = chapters(scan_lines(fetch_xml(ARCHIVE_ID)))

        content = {
            "author": author,
            "title": TITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "publication_year": PUBLICATION_YEAR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
        }
        book, was_created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": SORT_ORDER,
            },
        )
        book.chapters.all().delete()

        for order, (title, body) in enumerate(built, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 800:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:48]:48} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
