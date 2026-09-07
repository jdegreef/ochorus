"""Build E. M. Bounds's *The Possibilities of Prayer* (1923).

The missing volume of the Bounds prayer series — the other six are on CCEL and
already shipped; this one is on neither CCEL nor Gutenberg, only as an Internet
Archive OCR scan (`possibilitiesofp0000boun`, a Baker reprint of the 1923
Fleming H. Revell first edition, which is public domain). The generic
`import_archive` cannot chapter it: the sixteen chapters are headed by a *bare
roman numeral* on its own line, not a "CHAPTER N" marker, and the numerals are
badly mis-scanned ("Ill" for III, a stray "V." beside VI). So this command finds
the sixteen heads structurally — a short roman-ish line immediately above an
ALL-CAPS chapter title that is not the running book-title header — splits on them
in document order, and applies the titles from the book's own Contents.

Each chapter opens with an italic epigraph (usually closing "— Author"), then
small-caps drop-cap prose ("WITHOUT the promise…", "THE ministry…"); chapter I's
ornamental drop cap mis-scanned to "P^HE" for "The". The reflow reuses
`import_archive`, extended (as the Foote build does) to drop the ALL-CAPS running
headers this scan repeats on every page.

Fixture-driven: `seed_books` creates it on the next deploy, resolving the
existing `e-m-bounds` author from `authors.json`. Idempotent. No `catalog.py`
entry — a stray `import_archive` would only re-flatten it.

    DJANGO_DEBUG=true uv run python manage.py build_possibilities
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
from library.quote_marks import convert_work

SLUG = "possibilities-of-prayer"
TITLE = "The Possibilities of Prayer"
SUBTITLE = "How Far Believing Prayer Can Reach"
AUTHOR_SLUG = "e-m-bounds"
ARCHIVE_ID = "possibilitiesofp0000boun"
COVER_COLOR = "#324a6d"  # deep prayer-blue — house-style cover ground

DESCRIPTION = (
    "Bounds's fullest case for what prayer can actually do. Ranging over the "
    "promises of Scripture, the recorded facts of answered prayer, and the "
    "history of God's dealings with praying men, he argues that prayer is no "
    "pious formality but a real force that moves the hand of God — reaching "
    "into providence, working wonders, and shaping the world. The companion "
    "volume to his other books on prayer, and the one most given to proof by "
    "story and instance."
)

ATTRIBUTION = (
    "Public domain — first published 1923 by Fleming H. Revell. Text from the "
    "Internet Archive scan possibilitiesofp0000boun; chapter titles are taken "
    "from the book's own Contents (the scan's running-header titles are "
    "OCR-mangled)."
)

# The sixteen chapters, from the 1923 Contents page. Order IS the reading order.
# V/VI and XI/XII repeat "(Continued)" exactly as the book does — a faithful
# duplicate, like Clement's repeated "Continuation".
TITLES = [
    "The Ministry of Prayer",
    "Prayer and the Promises",
    "Prayer and the Promises (Continued)",
    "Prayer—Its Possibilities",
    "Prayer—Its Possibilities (Continued)",
    "Prayer—Its Possibilities (Continued)",
    "Prayer—Its Wide Range",
    "Prayer—Facts and History",
    "Prayer—Facts and History (Continued)",
    "Answered Prayer",
    "Answered Prayer (Continued)",
    "Answered Prayer (Continued)",
    "Prayer Miracles",
    "Wonders of God Through Prayer",
    "Prayer and Divine Providence",
    "Prayer and Divine Providence (Continued)",
]

#: A body chapter head is a bare roman-ish token on its own line. The numerals
#: are heavily mis-scanned, so this tolerates the misreads too — "o" for a
#: numeral letter, "|"/"." specks, "^" — on top of the case-folded I V X L C.
#: The ALL-CAPS-title test below is what makes it precise, and we split on
#: document order, never the parsed number.
_ROMANISH = re.compile(r"^[IVXLC][IVXLCo|.^]*$", re.I)

#: Lines to skip before the first chapter — the title page and Contents, whose
#: own roman numerals and ALL-CAPS entries would otherwise false-match as heads.
#: Any drift is caught anyway by the head-count guard in `_chapters`.
_FRONT_MATTER_LINES = 250

#: The running book-title header ("12 THE POSSIBILITIES OF PRAYER"), which sits
#: below a stray roman-ish scrap and would otherwise read as a chapter head.
_BOOK_TITLE = "POSSIBILITIES OF PRAYER"

#: The back cover splits the title across two lines ("THE POSSIBILITIES" / "OF
#: PRAYER"); the running header never does. It marks the end of the last chapter.
_BACK_COVER = re.compile(r"^\s*THE\s+POSSIBILITIES\s*$")

#: A leftover heading fragment between a title and its epigraph: "(Continued)"
#: on its own line, with the OCR's brace/paren variants.
_CONTINUED = re.compile(r"^[\s({\[]*continued[\s)}\]]*$", re.I)

#: The prose opener: a small-caps drop-cap word (two or more capitals, caret
#: tolerated for chapter I's mangled "P^HE") followed by a lowercase word.
_OPENER = re.compile(r"^\s*([A-Z][A-Z^]+)\s+[a-z]")

#: The ornamental drop caps the scanner could not read as letters.
_OPENER_FIX = {"P^HE": "The"}

#: Unambiguous OCR misreads, kept as literal PHRASES so a valid "he", "but" or
#: "lie" elsewhere is never touched. The italic epigraphs read 'b' as 'h'
#: ("should he" → "should be"); "socalled" lost its hyphen; and the railway term
#: "six-foot" lost its opening quote, leaving an orphan close-quote.
_OCR_FIXES = [
    ("should he the breath", "should be the breath"),
    ("which may he pleaded", "which may be pleaded"),
    ("meditation may he ousted", "meditation may be ousted"),
    ("nothing hut prayer", "nothing but prayer"),
    ("wisdom, hut trembles", "wisdom, but trembles"),
    ("socalled", "so-called"),
    ("the six-foot” when", "the “six-foot” when"),
    # A closing double-quote the scanner read as "/’" (or "/'"); the comma or
    # period before it is settled by whether a new sentence follows.
    ("Comforter/’ the", "Comforter,” the"),
    ("promises/’ “", "promises,” “"),
    ("utterance/' Prayer", "utterance.” Prayer"),
    ("carefulness/’ the", "carefulness,” the"),
    ("carefulness/’ and", "carefulness,” and"),
    ("whatever/’ “", "whatever,” “"),
    ("anything/’ and", "anything,” and"),
    ("heard/' It might", "heard.” It might"),
    # A leaked lowercase-roman page number, a stray speck, an OCR'd ellipsis,
    # and a space-split word.
    ("We ii need", "We need"),
    ("to prayer.” • There", "to prayer.” There"),
    ("nothing but prayer. • . . The", "nothing but prayer. … The"),
    ("un fainting", "unfainting"),
    # A leaked page number "44" where the opening quote of a Scripture citation
    # belongs ("Ye also helping together…", 2 Cor 1:11).
    ("44 Ye also helping", "“Ye also helping"),
    # "4" read for the opening single-quote of a nested quotation (Wesley's hymn
    # "…cries, 'It shall be done!'"), and "0" read for a vocative "O Lord".
    ("cries, 4 It shall be done", "cries, ‘It shall be done"),
    ("0 Lord send me", "O Lord send me"),
]


def _fix_ocr(html: str) -> str:
    for bad, good in _OCR_FIXES:
        html = html.replace(bad, good)
    return html


def _is_allcaps(line: str) -> bool:
    letters = _NON_LETTER.sub("", line)
    return len(letters) >= 4 and letters.isupper()


def _is_heading(line: str) -> bool:
    """A chapter-title line, allowing a mixed-case trailing "( Continued )"."""
    return _is_allcaps(re.sub(r"\([^)]*\)\s*$", "", line))


def _furniture(line: str) -> bool:
    """Blank/letterless (page numbers, barcodes, ornaments), or an ALL-CAPS
    running header (the repeated title)."""
    if not line or not re.search(r"[A-Za-z]", line):
        return True
    return bool(_BARE_NUM.match(line)) or _is_header(line) or _is_allcaps(line)


def _reflow(lines: list[str]) -> str:
    """`import_archive._reflow`, dropping this scan's ALL-CAPS running headers."""
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
        # This scan sets the end-of-line hyphen as ¬ (U+00AC), which the ASCII
        # _HYPHEN_EOL join can't see — normalise a trailing one so "reason¬" /
        # "able" rejoins to "reasonable".
        if line.endswith("¬"):
            line = line[:-1] + "-"
        if _furniture(line):
            if buf.rstrip().endswith((".", "!", "?", "”", '"', ":", ";")):
                flush()
            continue
        if buf and _HYPHEN_EOL.search(buf.rstrip()):
            buf = _HYPHEN_EOL.sub(r"\1", buf.rstrip()) + line
        else:
            buf = f"{buf} {line}" if buf else line
    flush()
    return "".join(f"<p>{p}</p>" for p in paras)


def _title_line(lines: list[str], i: int) -> str | None:
    """The first real (non-blank, non-punctuation) line below a roman-ish scrap."""
    for j in range(i + 1, min(i + 6, len(lines))):
        t = lines[j].strip()
        if t and re.search(r"[A-Za-z]", t):
            return t
    return None


def _heads(lines: list[str]) -> list[int]:
    """Indices of the sixteen bare-roman chapter heads, in document order."""
    heads: list[int] = []
    for i, raw in enumerate(lines):
        if i < _FRONT_MATTER_LINES:
            continue
        token = _WS.sub("", raw)
        if not (1 <= len(token) <= 5 and _ROMANISH.match(token)):
            continue
        title = _title_line(lines, i)
        if not title or not _is_heading(title):
            continue
        norm = _WS.sub(" ", re.sub(r"[^A-Za-z ]", " ", title)).strip().upper()
        # Reject the running book-title header (bare or with a page number).
        if _BOOK_TITLE in norm or re.match(r"^\s*\d", title):
            continue
        heads.append(i)
    return heads


def _italic(html: str) -> str:
    """Wrap each reflowed epigraph paragraph in <i>, as the sibling books do."""
    return html.replace("<p>", "<p><i>").replace("</p>", "</i></p>")


def _fix_dropcap(prose_html: str) -> str:
    """Turn the small-caps drop-cap opener into a normal word."""
    def repl(m: re.Match) -> str:
        word = m.group(2)
        return m.group(1) + _OPENER_FIX.get(word, word.capitalize())

    return re.sub(r"^(<p>)([A-Z^]{2,})", repl, prose_html, count=1)


def _chapter_body(block: list[str]) -> str:
    """One chapter's block → epigraph (italic) + drop-cap-fixed prose."""
    # The prose begins at the small-caps drop-cap line; everything above it,
    # once the title and running headers are dropped, is the epigraph.
    prose_at = next(
        (
            j
            for j, ln in enumerate(block)
            if (s := ln.strip()) and not _furniture(s) and _OPENER.match(s)
        ),
        0,
    )
    epi_lines = [
        ln
        for ln in block[:prose_at]
        if not _is_heading(s := ln.strip()) and not _CONTINUED.match(s)
    ]
    epigraph = _italic(_reflow(epi_lines)) if epi_lines else ""
    prose = _fix_dropcap(_reflow(block[prose_at:]))
    return epigraph + prose


def _chapters() -> list[tuple[str, str]]:
    lines = fetch_text(ARCHIVE_ID).split("\n")
    heads = _heads(lines)
    if len(heads) != len(TITLES):
        raise CommandError(
            f"found {len(heads)} chapter heads, expected {len(TITLES)} — the scan changed."
        )
    # The last chapter stops at the back cover, not the end of the OCR dump.
    # Fail loud rather than fall back to end-of-file: without this marker the
    # last chapter would swallow the reprint's back-cover blurb (real prose the
    # furniture filter and the word-count floor don't catch).
    back = next(
        (i for i in range(heads[-1] + 1, len(lines)) if _BACK_COVER.match(lines[i])),
        None,
    )
    if back is None:
        raise CommandError("back-cover marker not found — the scan changed.")
    out: list[tuple[str, str]] = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else back
        out.append((TITLES[n], _chapter_body(lines[start + 1 : end])))
    return out


class Command(BaseCommand):
    help = "Build Bounds's The Possibilities of Prayer (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — seed the library first."
            ) from exc

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
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

        # The OCR mixes straight and curly quotes; normalise to curly (the
        # corpus target) with the same context-sensitive logic migration 0084
        # uses, so QuoteStyleTests passes and a rebuild stays idempotent.
        bodies = [
            settled_chapter_body(SLUG, order, clean_fragment(_fix_ocr(body)))
            for order, (_, body) in enumerate(chapters, start=1)
        ]
        bodies, _ = convert_work(bodies, f"{SLUG}.en.json")

        for order, ((title, _), body) in enumerate(zip(chapters, bodies, strict=True), start=1):
            wc = word_count(body)
            if wc < 200:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
