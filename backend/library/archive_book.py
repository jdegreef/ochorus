"""The shared half of a `build_<name>` command over an Internet Archive scan.

`library.archive_hocr` turns a scan's hOCR into paragraphs; this module holds
what such a command does around that — the typesetting the scan adds, the
small capitals a chapter opens on, the per-chapter OCR repairs kept in
`management/commands/data/<slug>/ocr_fixes.json`, and the save. A command
subclasses `ArchiveBookCommand`, sets the book's metadata, and supplies only
what is particular to its print: `build_chapters`, which finds the furniture
and the chapters.

Used by `build_reality_and_religion` and `build_with_and_without_christ`.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.archive_hocr import Line, fetch_hocr, parse
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter

_DATA = Path(__file__).resolve().parent / "management" / "commands" / "data"
#: The print's spaced stops ("depends !", "hand ?") — its typesetting, not text.
_SPACED_STOP = re.compile(r"(?<=[\w”’)]) +([;:!?])")
#: A paragraph's opening word(s), after an optional thought number ("3. ").
_FIRST_WORD = re.compile(r"^((?:\d+|[IVX]+)\. )?([A-Za-z]+)(?: ([A-Za-z]+))?")
#: Below this a chapter is a failed split, not a chapter.
_MIN_WORDS = 150


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def small_caps(para: str) -> str:
    """A chapter's opening word is set in small capitals ("THERE are", "A
    cHILD may", "WirHout faith"): set it, and a one-letter word's partner, as
    ordinary words. Misreads the case fold cannot mend are in the fixes."""
    m = _FIRST_WORD.match(para)
    if not m:
        return para
    num, first, second = m.group(1) or "", m.group(2), m.group(3)
    words = first[0].upper() + first[1:].lower()
    if len(first) == 1 and second:
        words += " " + second.lower()
    elif second:
        words += " " + second
    return num + words + para[m.end():]


def typeset(para: str) -> str:
    """A paragraph as HTML text, without the scan's spacing: stops closed up
    to their word, and quotation marks to the words they set off ("the
    “ Prince of Peace”")."""
    para = _SPACED_STOP.sub(r"\1", para)
    para = re.sub(r"([“‘]) +(?=\w)", r"\1", para)
    para = re.sub(r"(?<=[\w.,;:!?]) +([”’])(?!\w)", r"\1", para)
    return escape(para, quote=False)


def load_fixes(slug: str) -> dict[str, list[list[str]]]:
    path = _DATA / slug / "ocr_fixes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def apply_fixes(order: int, html: str, fixes: dict[str, list[list[str]]]) -> str:
    """The data file's repairs for one chapter, each matching exactly once."""
    for find, replace in fixes.get(str(order), []):
        if html.count(find) != 1:
            raise CommandError(
                f"ch {order}: OCR fix {find!r} matches {html.count(find)} times, not once"
            )
        html = html.replace(find, replace)
    return html


class ArchiveBookCommand(BaseCommand):
    """Build one book from an Archive scan: fetch, chapter, repair, save.

    Fixture-driven like every other book — `seed_books` creates it on deploy
    from the serialized fixture; this rebuilds the dev DB's rows. Idempotent.
    """

    SLUG: str
    AUTHOR_SLUG: str
    TITLE: str
    SUBTITLE: str
    PUBLICATION_YEAR: int
    COVER_COLOR: str
    ARCHIVE_ID: str
    ATTRIBUTION: str
    DESCRIPTION: str

    def build_chapters(self, lines: list[Line]) -> list[tuple[str, str]]:
        """The scan's lines → `(title, body_html)` per chapter, in order."""
        raise NotImplementedError

    def add_arguments(self, parser):
        parser.add_argument(
            "--hocr",
            help="Read the scan's hOCR from this local file instead of archive.org.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=self.AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {self.AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        if opts.get("hocr"):
            hocr = Path(opts["hocr"]).read_text(encoding="utf-8")
        else:
            hocr = fetch_hocr(self.ARCHIVE_ID)
        chapters = self.build_chapters(parse(hocr))
        content = {
            "author": author,
            "title": self.TITLE,
            "subtitle": self.SUBTITLE,
            "description": self.DESCRIPTION,
            "attribution": self.ATTRIBUTION,
            "publication_year": self.PUBLICATION_YEAR,
            "cover_color": self.COVER_COLOR,
            "source_url": f"https://archive.org/details/{self.ARCHIVE_ID}",
        }
        book, was_created = Book.objects.update_or_create(
            slug=self.SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(self.SLUG),
            },
        )
        book.chapters.all().delete()

        fixes = load_fixes(self.SLUG)
        unknown = set(fixes) - {str(n) for n in range(1, len(chapters) + 1)}
        if unknown:
            raise CommandError(f"ocr_fixes.json names chapters that do not exist: {sorted(unknown)}")
        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = apply_fixes(order, clean_fragment(body), fixes)
            body = settled_chapter_body(self.SLUG, order, body)
            wc = word_count(body)
            if wc < _MIN_WORDS:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {self.TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
