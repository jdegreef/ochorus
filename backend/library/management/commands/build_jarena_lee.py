"""Build *Religious Experience and Journal of Mrs. Jarena Lee* (1849).

Project Gutenberg #66953 is a clean transcription, but the 1849 edition carries
only three authorial section headings — and the third runs unbroken through her
entire travelling journal (1821–1843), a single 44,000-word chapter that no phone
reader wants. So this command keeps the two short opening sections and her third
heading, then splits the long journal that follows into readable, numbered
chapters at block boundaries (paragraphs and the hymns she quotes alike). The
text itself is untouched — only where the breaks fall is editorial, the way any
reading edition of a long diary must decide.

Fixture-driven like every other book: `seed_books` creates it (and the author,
from `authors.json`) on the next deploy from
`fixtures/content/books/religious-experience-and-journal.en.json`. This command
GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_jarena_lee
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import extract_chapters, fetch_html
from library.models import Author, Book, Chapter

SLUG = "religious-experience-and-journal"
TITLE = "Religious Experience and Journal"
SUBTITLE = "Giving an Account of Her Call to Preach the Gospel"
AUTHOR_SLUG = "jarena-lee"
GUTENBERG_ID = "66953"
COVER_COLOR = "#6d3a5d"  # muted plum — house-style cover ground

# Author fallback for a dev DB that hasn't seeded authors.json yet. authors.json
# is the source of truth (seed_books fills the full bio from it); this only lets
# the build run before that row exists.
AUTHOR_STUB = {
    "name": "Jarena Lee",
    "birth_year": 1783,
    "death_year": 1864,
}

DESCRIPTION = (
    "The first woman authorized to preach in the African Methodist Episcopal "
    "Church tells her own story: her conversion under Richard Allen, the long "
    "struggle to be allowed to preach, and then decades of travelling thousands "
    "of miles on foot and by wagon to carry the gospel. Her 1849 journal is a "
    "record of holy boldness — a Black woman claiming a pulpit the age denied "
    "her, and finding God meet her at every turn."
)

ATTRIBUTION = (
    "Public domain — first published 1836, expanded 1849. Text from Project "
    "Gutenberg (ebook 66953). The long journal is split into chapters by period "
    "for reading; the wording is unchanged."
)

# Split any section longer than this into ~this-sized chapters at paragraph
# boundaries. A short trailing remnant is folded back into the previous chapter.
_TARGET_WORDS = 7000
_MIN_TAIL = 2500


def _roman(n: int) -> str:
    numerals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for value, sym in numerals:
        while n >= value:
            out += sym
            n -= value
    return out


def _split_blocks(body_html: str) -> list[str]:
    """Group a long body's TOP-LEVEL blocks into ~_TARGET_WORDS chunks.

    Iterates every block (``<p>``, ``<blockquote>``, …), not just paragraphs, so
    her quoted hymns and verse are carried through rather than dropped.
    """
    from bs4 import BeautifulSoup

    blocks = [
        str(el)
        for el in BeautifulSoup(body_html, "html.parser").children
        if getattr(el, "name", None)
    ]
    chunks: list[list[str]] = []
    cur: list[str] = []
    words = 0
    for b in blocks:
        cur.append(b)
        words += word_count(b)
        if words >= _TARGET_WORDS:
            chunks.append(cur)
            cur, words = [], 0
    if cur:
        if chunks and words < _MIN_TAIL:
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return ["".join(c) for c in chunks]


def _chapters() -> list[tuple[str, str]]:
    sections = extract_chapters(fetch_html(GUTENBERG_ID))
    if len(sections) != 3:
        raise CommandError(f"expected 3 source sections, got {len(sections)} — the edition changed.")
    out: list[tuple[str, str]] = []
    for title, body in sections:
        if word_count(body) <= _TARGET_WORDS * 1.5:
            out.append((title, body))
            continue
        # The long third section: keep its heading for the first chunk, then
        # number the journal chunks. Her entries run out of strict chronological
        # order (she recounts past and future years within a single entry), so a
        # year-range title would misrepresent them — Part N is the honest label.
        parts = _split_blocks(body)
        for j, part in enumerate(parts):
            out.append((title if j == 0 else f"The Journal, Part {_roman(j)}", part))
    return out


class Command(BaseCommand):
    help = "Build Jarena Lee's Religious Experience and Journal (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG, defaults=AUTHOR_STUB
        )
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
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

        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 500:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
