"""Build Julian of Norwich's *Revelations of Divine Love* (the Long Text).

The edition is Grace Warrack's (Methuen, 1901): a version in modernised
spelling from the Sloane manuscript in the British Museum. Warrack died in
1932, and the book has been in the public domain for a long time on both sides
of the Atlantic. The source is Project Gutenberg #52958; www.gutenberg.org
refuses this environment's egress, so the plain text is read from the
GITenberg mirror of the same ebook on GitHub — the route ``build_pensees`` and
``build_unspoken_sermons`` take. GITenberg ships it as ISO-8859-1.

Only Julian is taken: Warrack's notes on the manuscripts, her long
introduction, her contents, the Gutenberg header and licence, and the
scribe's postscript in Middle English spelling are left out — as is the
translator's apparatus in ``build_provincial_letters``.

Eighty-six chapters, one per chapter of the Long Text, so the reader's chapter
number IS Julian's chapter number and "chapter xxvii" can still be cited. Each
is titled with the heading Warrack set above it — a phrase from the chapter
itself, taken out of its quotation marks (several are joined with a dash, and
the few longest are shortened; see `_title`). The sixteen Revelations are kept
visible: the chapter where one begins opens with Warrack's "The First
Revelation" … "The Sixteenth Revelation" as an ``<h3>`` (and chapter xliv with
her "Anent certain points in the foregoing fourteen Revelations"). The shortest
chapter runs to 170 words, so none is folded into another.

Warrack's 357 footnotes are left out with their markers. Nearly all of them
gloss one archaic word ("dearworthy", "homely", "oned"); the rest are
manuscript readings and cross-references. They close each chapter, and a few
run on for paragraphs (ch li, ch lvii), so a chapter's own text ends at its
first note. The words they gloss are explained, in Warrack's own words, by her
Glossary, which follows the eighty-six chapters as an eighty-seventh. Her
square-bracketed insertions in the text ("[Shewing]", "[of]") are hers and
stay.

How the plain text is read:

* ``_underscores_`` are Warrack's italics (the words of the Lord, chiefly),
  ``--`` her dashes;
* every block in a chapter is prose; the text has no verse.

Fixture-driven like every other book: ``seed_books`` creates it (and the
author, from ``authors.json``) on the next deploy from
``fixtures/content/books/revelations-of-divine-love.en.json``. This command
GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_revelations_of_divine_love
"""

from __future__ import annotations

import html
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "revelations-of-divine-love"
TITLE = "Revelations of Divine Love"
SUBTITLE = "Translated by Grace Warrack"
AUTHOR_SLUG = "julian-of-norwich"
GUTENBERG_ID = "52958"
SOURCE_TXT = (
    "https://raw.githubusercontent.com/GITenberg/"
    "Revelations-of-Divine-Love_52958/master/52958-8.txt"
)
PUBLICATION_YEAR = 1901
COVER_COLOR = covers.ink_safe("#6b4a2f")

AUTHOR_STUB = {"name": "Julian of Norwich", "birth_year": 1343}

DESCRIPTION = (
    "In May 1373, at thirty and a half and thought to be dying, a woman of "
    "Norwich saw sixteen “shewings” of the love of God as she gazed on a "
    "crucifix. She recovered, became an anchoress walled into a cell at St "
    "Julian’s church, and spent twenty years and more pondering what she had "
    "seen. This is the fruit: the first book in English known to have been "
    "written by a woman. Here are the hazel-nut that holds all that is made, "
    "the Lord and the servant, Jesus our Mother, and the promise she was given "
    "for a world full of sin and sorrow — “all shall be well, and all shall be "
    "well, and all manner of thing shall be well.”"
)

ATTRIBUTION = (
    "Public domain — Julian of Norwich, Revelations of Divine Love (the Long "
    "Text), in Grace Warrack's version from the Sloane manuscript in the "
    "British Museum (Methuen, 1901); text from Project Gutenberg (ebook 52958). "
    "One chapter for each of the Long Text's eighty-six, under Warrack's "
    "chapter headings, followed by her Glossary. Warrack's introduction, her "
    "footnotes and the scribe's postscript are not included."
)

# The sixteen Revelations, by the chapter each begins in, plus Warrack's
# heading for the chapters (xliv–) that reflect on the first fourteen. Checked
# against the source's own headings, so a changed edition fails loudly.
SECTIONS = {
    4: "The First Revelation",
    10: "The Second Revelation",
    11: "The Third Revelation",
    12: "The Fourth Revelation",
    13: "The Fifth Revelation",
    14: "The Sixth Revelation",
    15: "The Seventh Revelation",
    16: "The Eighth Revelation",
    22: "The Ninth Revelation",
    24: "The Tenth Revelation",
    25: "The Eleventh Revelation",
    26: "The Twelfth Revelation",
    27: "The Thirteenth Revelation",
    41: "The Fourteenth Revelation",
    44: "Anent Certain Points in the Foregoing Fourteen Revelations",
    64: "The Fifteenth Revelation",
    67: "The Sixteenth Revelation",
}
CHAPTERS = 86

# Chapter titles: see `_title`. Past this many characters a heading is cut.
_TITLE_MAX = 150
# The phrase of a long multi-phrase heading to keep, where it is not the first:
# ch liii's first phrase is ch xxxvii's title word for word.
TITLE_PART = {32: 1, 53: 1}
# Two headings no rule cuts well. Ch xxvii's is "… — Sin is behovable—[playeth
# a needful part]—; but all shall be well": the phrase is kept, Warrack's
# bracketed gloss dropped as her footnotes are. Ch lviii's is "All our life is
# in three: 'Nature, Mercy, Grace.' The high Might …"; its second sentence,
# which the chapter is read for, is kept.
TITLE_OVERRIDES = {
    27: "Sin is behovable; but all shall be well",
    58: (
        "The high Might of the Trinity is our Father, and the deep Wisdom of the "
        "Trinity is our Mother, and the great Love of the Trinity is our Lord"
    ),
}

# Transcription slips, each unambiguous and each checked to occur exactly the
# given number of times, so a changed edition fails loudly instead of quietly.
SOURCE_FIXES = [
    # Ch xii's heading quotes its own sentence, which the chapter sets as "so
    # verily it is most plenteous" — the heading doubled the "it".
    ("so verily it it most plenteous", "so verily it is most plenteous", 1),
    # Ch lxviii, "Thou shalt not be tempested, thou shalt not be travailed,
    # thou shalt not be afflicted" — as its heading quotes it; the body read
    # "shall" and the OCR "shah" for the last two.
    (
        "thou shall\nnot be travailed, thou shah not be afflicted",
        "thou shalt\nnot be travailed, thou shalt not be afflicted",
        1,
    ),
]

_START = "REVELATIONS OF DIVINE LOVE"
_POSTSCRIPT = "POSTSCRIPT BY A SCRIBE"
_GLOSSARY = "GLOSSARY"
_END = "[THE END.]"
_CHAPTER = re.compile(r"^ +CHAPTER ([IVXL]+)$")
_SECTION = re.compile(r"^ +_([A-Z][A-Z ]+?)\.?_$")
_NOTE_BLOCK = re.compile(r"^\[\d+\] ")
_NOTE_MARK = re.compile(r"\[\d+\]")
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}


def _roman(s: str) -> int:
    total = 0
    for a, b in zip(s, s[1:] + " ", strict=True):
        v = _ROMAN[a]
        total += -v if b != " " and _ROMAN[b] > v else v
    return total


def _source_lines() -> list[str]:
    resp = requests.get(SOURCE_TXT, timeout=60)
    resp.raise_for_status()
    text = resp.content.decode("iso-8859-1").replace("\r\n", "\n")
    for old, new, count in SOURCE_FIXES:
        if text.count(old) != count:
            raise CommandError(f"source fix {old!r}: expected {count}, found {text.count(old)}.")
        text = text.replace(old, new)
    return text.split("\n")


def _blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if ln.strip():
            current.append(ln.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _join(lines: list[str]) -> str:
    """Rejoin hard-wrapped lines. A line ending in a dash runs on."""
    out = ""
    for ln in (s.strip() for s in lines):
        if out and not out.endswith("--") and not ln.startswith("--"):
            out += " "
        out += ln
    return re.sub(r" {2,}", " ", out)


def _dashes(text: str) -> str:
    return re.sub(r" ?-{2,} ?", "—", text)


def _italicize(text: str, where: str) -> str:
    """``_…_`` -> ``<em>…</em>``; every span opens and closes in its block."""
    if text.count("_") % 2:
        raise CommandError(f"{where}: an italic span never closes: {text[:80]!r}")
    return re.sub(r"_([^_]+)_", r"<em>\1</em>", text)


def _prose(text: str, where: str) -> str:
    text = _NOTE_MARK.sub("", text)
    return _italicize(_dashes(html.escape(text, quote=False)), where)


def _title(n: int, block: list[str]) -> str:
    """Warrack's heading: one or more quoted phrases, set as a plain title.

    Most headings are one phrase from the chapter, and are taken whole. A few
    string three or four together and run past a line of the contents; those
    keep their first phrase, cut at its first sentence or colon if it is still
    over :data:`_TITLE_MAX` — and :data:`TITLE_PART` picks a later phrase where
    the first is not the one the chapter is remembered by (or repeats another
    chapter's title).
    """
    text = re.sub(r"\s*\([ivxl]+\.\)$", "", _join(block).replace("_", ""))
    parts = re.findall(r'"([^"]+)"', text)
    if not parts or re.sub(r"[\s-]", "", re.sub(r'"[^"]+"', "", text)):
        # A heading that is partly Warrack's own words keeps its quotation marks.
        return _dashes(text.rstrip("."))
    if n in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[n]
    parts = [_unstop(_dashes(p.strip())) for p in parts]
    title = " — ".join(parts)
    if len(title) > _TITLE_MAX:
        title = parts[TITLE_PART.get(n, 0)]
    if len(title) > _TITLE_MAX:
        cut = re.search(r"\.{2,}|\. |: |;—", title)
        if cut:
            title = title[: cut.start()]
    return _unstop(title)


def _unstop(text: str) -> str:
    """A closing full stop is dropped (a title, not a sentence); an ellipsis kept."""
    return text if text.endswith("...") else text.rstrip(".")


def _split(lines: list[str]) -> tuple[list[list[str]], list[str]]:
    """The chapters' lines (from each CHAPTER marker) and the Glossary's."""
    start = next(i for i, ln in enumerate(lines) if ln.strip() == _START)
    post = next(i for i, ln in enumerate(lines) if ln.strip() == _POSTSCRIPT)
    gloss = next(i for i, ln in enumerate(lines) if ln.strip() == _GLOSSARY and i > post)
    end = next(i for i, ln in enumerate(lines) if ln.strip() == _END and i > gloss)
    body = lines[start + 1 : post]
    marks = [i for i, ln in enumerate(body) if _CHAPTER.match(ln)]
    numbers = [_roman(_CHAPTER.match(body[i]).group(1)) for i in marks]
    if numbers != list(range(1, CHAPTERS + 1)):
        raise CommandError(f"chapter markers are not I…LXXXVI in order: {numbers}")
    chapters = []
    for k, i in enumerate(marks):
        stop = marks[k + 1] if k + 1 < len(marks) else len(body)
        chapters.append(body[i:stop])
    # A section heading sits just before its chapter's marker, so it ends up at
    # the tail of the previous chapter's lines; it is read off there.
    return chapters, lines[gloss + 1 : end]


def _chapter(n: int, lines: list[str], next_section: str | None) -> tuple[str, str]:
    blocks = _blocks(lines[1:])
    if next_section is not None:
        tail = _join(blocks.pop())
        m = _SECTION.match("  " + tail)
        if not m or m.group(1).lower() != next_section.lower():
            raise CommandError(f"ch {n}: expected {next_section!r} before the next chapter, found {tail!r}")
    title = _title(n, blocks[0])
    parts = []
    if n in SECTIONS:
        parts.append(f"<h3>{html.escape(SECTIONS[n], quote=False)}</h3>")
    for b in blocks[1:]:
        if _NOTE_BLOCK.match(b[0]):
            # Warrack's notes close the chapter, and the longest run on for
            # paragraphs (ch li's on "Regard", ch lvii's from Hilton), so the
            # first one ends the chapter's own text.
            break
        if min(len(ln) - len(ln.lstrip()) for ln in b) >= 2:
            raise CommandError(f"ch {n}: an indented block — not expected: {b[0]!r}")
        parts.append(f"<p>{_prose(_join(b), f'ch {n}')}</p>")
    return title, "".join(parts)


def _glossary(lines: list[str]) -> str:
    parts = []
    for b in _blocks(lines):
        parts.append(f"<p>{_prose(_join(b), 'glossary')}</p>")
    return "".join(parts)


def _chapters() -> list[tuple[str, str]]:
    chapter_lines, glossary_lines = _split(_source_lines())
    chapters: list[tuple[str, str]] = []
    for n, lines in enumerate(chapter_lines, start=1):
        chapters.append(_chapter(n, lines, SECTIONS.get(n + 1)))
    chapters.append(("Glossary", _glossary(glossary_lines)))

    # Gutenberg's ASCII double quotes -> the corpus's curly ones (apostrophes
    # stay straight, as across the library). Only the marks may move.
    curled = []
    for n, (title, body) in enumerate(chapters, start=1):
        new, _ = convert(body, outer_guillemets=False)
        assert_punctuation_only(body, new, f"{SLUG}[{n}]")
        new_title, _ = convert(title, outer_guillemets=False)
        curled.append((new_title, new))
    return curled


class Command(BaseCommand):
    help = "Build Julian of Norwich's Revelations of Divine Love in the dev DB; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://www.gutenberg.org/ebooks/{GUTENBERG_ID}",
        }
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(SLUG),
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 120:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:60]:60} {wc:>5} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
