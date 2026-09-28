"""Build Blaise Pascal's *Pensées* in W. F. Trotter's translation.

The source is Project Gutenberg #18269 (a 1958 Dutton printing of Trotter's
translation). www.gutenberg.org refuses this environment's egress, so the
plain-text file is read from the GITenberg mirror of the same ebook on GitHub.
Only the text is taken: the edition's T. S. Eliot introduction (1958, not
public domain), the editor's note, the endnotes and the index are left out, and
the ``[N]`` markers that pointed into those endnotes are removed.

Trotter arranges Pascal's 923 fragments (Brunschvicg's order) into fourteen
sections; each section is one chapter here, and each fragment keeps its number
as a small ``<h3>`` heading so a reader can still cite "Pensée 347". Section
XIV's "Appendix:" label is dropped from its title — the reader numbers it.

Fixture-driven like every other book: ``seed_books`` creates it (and the author,
from ``authors.json``) on the next deploy from
``fixtures/content/books/pensees.en.json``. This command GENERATES that fixture
reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_pensees
"""

from __future__ import annotations

import html
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert
from library.titlecase import recase_title

SLUG = "pensees"
TITLE = "Pensées"
SUBTITLE = "Translated by W. F. Trotter"
AUTHOR_SLUG = "blaise-pascal"
GUTENBERG_ID = "18269"
SOURCE_TXT = (
    "https://raw.githubusercontent.com/GITenberg/Pascal-s-Pens-es_18269/master/18269.txt"
)
PUBLICATION_YEAR = 1670
COVER_COLOR = covers.ink_safe("#3b4a5c")

AUTHOR_STUB = {"name": "Blaise Pascal", "birth_year": 1623, "death_year": 1662}

DESCRIPTION = (
    "When Blaise Pascal died in 1662 at the age of thirty-nine, he left behind "
    "hundreds of notes for a great defence of the Christian faith that he never "
    "finished. His friends at Port-Royal published them in 1670 as the Pensées, "
    "or “Thoughts.” Pascal begins not with proofs from nature but with man "
    "himself: his greatness and his misery, his restlessness, the diversions he "
    "uses to hide from the one question that matters. Here are the thinking "
    "reed, the famous wager, “the heart has its reasons, which reason does not "
    "know,” and the “Mystery of Jesus,” written as if kneeling beside Christ in "
    "Gethsemane."
)

ATTRIBUTION = (
    "Public domain — Blaise Pascal's Pensées (1670), translated by W. F. Trotter; "
    "text from Project Gutenberg (ebook 18269). Trotter's fourteen sections are "
    "the chapters and every fragment keeps its number; the 1958 introduction, the "
    "editor's notes and the index are not included."
)

EXPECTED_SECTIONS = 14
EXPECTED_FRAGMENTS = 923

_SECTION_RE = re.compile(r"^SECTION ([IVXL]+)$")
_NUMBER_RE = re.compile(r"^\d+$")
_NOTE_REF = re.compile(r"\[\d+\]")
# "_History of China._[213]-I believe" — the one fragment title whose dash the
# transcription set as a single hyphen (every other one is "--").
_TITLE_HYPHEN = re.compile(r"(?<=</em>)-(?=[A-Z])")

# Pascal's two little diagrams, which plain text can only draw in ASCII art
# (a brace and a "__|__" tree). Set as short lines instead; the words are his.
DIAGRAMS = {
    "{1600 prophets.": ["2000 {", "1600 prophets.", "400 scattered."],
    "J. C.": ["J. C.", "Heathens | Mahomet", "Ignorance of God."],
}


def _source_lines() -> list[str]:
    resp = requests.get(SOURCE_TXT, timeout=60)
    resp.raise_for_status()
    lines = resp.text.replace("\r\n", "\n").split("\n")
    try:
        start = next(i for i, ln in enumerate(lines) if ln == "SECTION I")
        end = next(i for i, ln in enumerate(lines) if ln == "NOTES" and i > start)
    except StopIteration:
        raise CommandError("section/notes markers not found — the edition changed.") from None
    return lines[start:end]


def _block_text(lines: list[str]) -> str:
    """One blank-line-delimited block -> escaped text, before italics.

    Trotter's prose is hard-wrapped, so its lines are rejoined with spaces. A
    block with a short line before its last is set line by line (a numbered
    list, or one of the DIAGRAMS) and keeps its breaks.
    """
    stripped = [ln.strip() for ln in lines]
    stripped = DIAGRAMS.get(stripped[0], stripped)
    set_by_line = len(stripped) > 1 and any(len(ln) < 45 for ln in stripped[:-1])
    sep = "<br>" if set_by_line else " "
    text = sep.join(html.escape(s, quote=False) for s in stripped)
    return _NOTE_REF.sub("", text).replace("--", "—")


def _italicize(blocks: list[str], where: str) -> list[str]:
    """Turn ``_…_`` into ``<em>``, carrying an open span across paragraphs.

    Pascal's Latin citations are italic for several paragraphs at a time, so a
    span opened in one block can close blocks later; each paragraph closes and
    reopens it so the markup stays well formed.
    """
    out: list[str] = []
    open_em = False
    for text in blocks:
        pieces = text.split("_")
        html_ = "<em>" if open_em else ""
        for n, piece in enumerate(pieces):
            if n:
                open_em = not open_em
                html_ += "<em>" if open_em else "</em>"
            html_ += piece
        if open_em:
            html_ += "</em>"
        out.append(html_.replace("<em></em>", ""))
    if open_em:
        raise CommandError(f"{where}: an italic span never closes.")
    return out


def _fragment_html(number: int, lines: list[str]) -> str:
    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if ln.strip():
            current.append(ln)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    if not blocks:
        raise CommandError(f"fragment {number} is empty.")
    paras = _italicize([_block_text(b) for b in blocks], f"fragment {number}")
    return f"<h3>{number}</h3>" + "".join(
        f"<p>{_TITLE_HYPHEN.sub('—', p)}</p>" for p in paras
    )


def _chapters() -> list[tuple[str, str]]:
    lines = _source_lines()

    # Split into sections: "SECTION N", a blank, then the ALL-CAPS title.
    sections: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        if _SECTION_RE.match(lines[i]):
            j = i + 1
            while not lines[j].strip():
                j += 1
            title = lines[j].strip()
            k = j + 1
            while k < len(lines) and not _SECTION_RE.match(lines[k]):
                k += 1
            sections.append((title, lines[j + 1 : k]))
            i = k
        else:
            i += 1
    if len(sections) != EXPECTED_SECTIONS:
        raise CommandError(f"expected {EXPECTED_SECTIONS} sections, found {len(sections)}.")

    chapters: list[tuple[str, str]] = []
    expected = 1
    for raw_title, body in sections:
        title = recase_title(raw_title.removeprefix("APPENDIX:").strip().title())
        parts: list[str] = []
        k = 0
        # A fragment number is a bare numeral on its own unindented line.
        starts = [n for n, ln in enumerate(body) if _NUMBER_RE.match(ln)]
        if not starts or any(ln.strip() for ln in body[: starts[0]]):
            raise CommandError(f"section {title!r}: text before its first fragment.")
        for k, start in enumerate(starts):
            number = int(body[start])
            if number != expected:
                raise CommandError(f"fragment {expected} expected, found {number}.")
            stop = starts[k + 1] if k + 1 < len(starts) else len(body)
            parts.append(_fragment_html(number, body[start + 1 : stop]))
            expected += 1
        chapters.append((title, "".join(parts)))
    if expected - 1 != EXPECTED_FRAGMENTS:
        raise CommandError(f"expected {EXPECTED_FRAGMENTS} fragments, found {expected - 1}.")

    # Gutenberg's ASCII quotes -> the corpus's curly double quotes (apostrophes
    # stay straight, as across the library). Only the marks may move.
    curled = []
    for n, (title, body) in enumerate(chapters, start=1):
        new, _ = convert(body, outer_guillemets=False)
        assert_punctuation_only(body, new, f"{SLUG}[{n}]")
        curled.append((title, new))
    return curled


class Command(BaseCommand):
    help = "Build Pascal's Pensées (Trotter) in the dev DB; then serialize the fixture."

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

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 1000:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
