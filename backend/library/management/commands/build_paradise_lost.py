"""Build John Milton's *Paradise Lost* (second edition, 1674: twelve books).

The text is Standard Ebooks' edition, transcribed from page scans in the
HathiTrust Digital Library, whose own contributions are dedicated to the public
domain (CC0). The source files are the ebook's ``src/epub/text/book-N.xhtml``,
read from the Standard Ebooks repository on GitHub (standardebooks.org and
gutenberg.org refuse this environment's egress; the GitHub mirror is the same
text). Its twelve books carry the 1674 line counts (798, 1055, 742, … 649;
10,565 lines in all) and print each book's prose Argument at its head, as the
second edition first did. The edition does not carry Milton's note on "The
Verse", so neither does this book.

One chapter per Book. Each opens with Milton's Argument, set as a quotation
under a "The Argument" heading, and then the poem itself, one ``<p>`` per
verse paragraph with a ``<br>`` at the end of every line: blank verse keeps
its lines and its paragraphs, and is never reflowed into prose. ``<br>`` and
``<p>`` are both in the chapter sanitizer's allowlist, so the lines survive
``clean_fragment`` (``chapters()`` asserts that every line does).

Only Milton's text is taken: Standard Ebooks' title page, imprint, colophon and
uncopyright are left out. Their typography is kept (curly quotes, em dashes) and
so is their spelling, modernised but keeping some of Milton's own forms
("highth"); the invisible word-joiners and hair spaces they use for
line-breaking are removed, as in ``build_chesterton``.

Fixture-driven like every other book: ``seed_books`` creates the book (and the
author, from ``authors.json``) on the next deploy from
``fixtures/content/books/paradise-lost.en.json``. This command GENERATES that
fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_paradise_lost
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_chesterton import _block, _fetch, _inline
from library.models import Author, Book, Chapter

SLUG = "paradise-lost"
REPO = "john-milton_paradise-lost"
AUTHOR_SLUG = "john-milton"
AUTHOR_STUB = {"name": "John Milton", "birth_year": 1608, "death_year": 1674}

ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
# The 1674 edition's line count for each Book: a dropped or doubled line fails
# the build rather than shipping.
LINES = (798, 1055, 742, 1015, 907, 912, 640, 653, 1189, 1104, 901, 649)

BOOK = {
    "title": "Paradise Lost",
    "subtitle": "A Poem in Twelve Books",
    "publication_year": 1674,
    "cover_color": covers.ink_safe("#2e3a55"),
    "source_url": "https://standardebooks.org/ebooks/john-milton/paradise-lost",
    "description": (
        "Of Man’s first disobedience, and the fruit of that forbidden tree: "
        "Milton’s epic sets out to “justify the ways of God to men.” It opens "
        "in Hell, with Satan and his fallen angels roused on the burning lake, "
        "and rises to Heaven, where the Son offers himself for mankind while "
        "all the angels stand silent. It walks in the garden with Adam and Eve "
        "in their innocence, follows the temptation, the fall and their bitter "
        "quarrel through to repentance, and gives them the angel Michael’s "
        "vision of the history to come and of the Redeemer, until the pair go "
        "out from Eden hand in hand, the world all before them, and Providence "
        "their guide."
    ),
    "attribution": (
        "Public domain — John Milton's Paradise Lost, the twelve-book second "
        "edition of 1674. Text from the Standard Ebooks edition (CC0), "
        "transcribed from page scans in the HathiTrust Digital Library, with "
        "its spelling largely modernised. Complete: all twelve Books, each with "
        "Milton's prose Argument; Standard Ebooks does not include his note on "
        "the verse."
    ),
}


def _book(n: int) -> tuple[str, int]:
    """Book ``n`` as reader HTML, and the number of verse lines it holds."""
    where = f"{SLUG}/book-{n}"
    soup = BeautifulSoup(_fetch(REPO, f"book-{n}"), "lxml-xml")
    argument = soup.find("section", id=f"argument-{n}")
    poem = soup.find("section", id=f"poem-{n}")
    if argument is None or poem is None:
        raise CommandError(f"{where}: no Argument or no poem section.")
    if argument.header.get_text(strip=True) != "The Argument":
        raise CommandError(f"{where}: the preamble is not The Argument.")
    prose = argument.find_all("p", recursive=False)
    if len(prose) != 1:
        raise CommandError(f"{where}: expected one Argument paragraph, got {len(prose)}.")
    parts = [
        "<h3>The Argument</h3>",
        f"<blockquote><p>{_block(_inline(prose[0]))}</p></blockquote>",
    ]
    lines = 0
    for el in poem.find_all(recursive=False):
        if el.name != "p":
            raise CommandError(f"{where}: unexpected <{el.name}> in the poem.")
        lines += len(el.find_all("span", recursive=False))
        parts.append(f"<p>{_block(_inline(el))}</p>")
    return "".join(parts), lines


def chapters() -> list[tuple[str, str]]:
    """(title, body_html) per Book, in reading order, each checked line for line."""
    out = []
    for n, (roman, expected) in enumerate(zip(ROMAN, LINES, strict=True), start=1):
        body, lines = _book(n)
        if lines != expected:
            raise CommandError(f"Book {roman}: {lines} lines, the 1674 text has {expected}.")
        # The sanitizer must keep every line break: a verse paragraph of k
        # lines carries k-1 <br/>s, so the whole Book carries lines - paras.
        clean = clean_fragment(body)
        paras = clean.count("<p>") - 1  # less the Argument's
        if clean.count("<br/>") != lines - paras:
            raise CommandError(f"Book {roman}: line breaks lost in sanitizing.")
        out.append((f"Book {roman}", clean))
    return out


class Command(BaseCommand):
    help = "Build Milton's Paradise Lost in the dev DB; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG, defaults=AUTHOR_STUB
        )
        if created_author:
            self.stdout.write(
                f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)"
            )
        content = {"author": author, **BOOK}
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
        for order, (title, body) in enumerate(chapters(), start=1):
            body = settled_chapter_body(SLUG, order, body)
            wc = word_count(body)
            if wc < 4000:
                raise CommandError(f"{title}: only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title:10} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"
            )
        )
