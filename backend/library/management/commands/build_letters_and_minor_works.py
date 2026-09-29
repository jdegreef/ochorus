"""Build Pascal's *Letters and Minor Works* from the Harvard Classics text.

The source is volume 48 of the Harvard Classics (P. F. Collier, 1910) as
transcribed and proofread on English Wikisource: the letters in Mary Louise
Booth's translation and the minor works in Orlando Williams Wight's (1859). It
is read page by page through the MediaWiki API (`library.wikisource`).

What is kept is the devotional and moral Pascal: every letter, the epitaph of
his father, the Prayer in sickness, the Conversion of the Sinner, the
Comparison of early and present Christians, the Discourses on the Condition of
the Great, the Conversation with M. de Saci, and the Art of Persuasion. Left
out: the scientific treatises (the Geometrical Spirit, the two pieces on the
vacuum), which are mathematics rather than devotion, and the Discourse on the
Passion of Love, which modern scholarship does not accept as Pascal's. The
editor's footnotes and the scan's page numbers are dropped.

The letters are grouped into four chapters, each letter under its own
``<h3>``: the 1648 letters to his sisters; the long letter on his father's
death, with the epitaph he wrote for him; the letters to Mlle de Roannez; and
the rest, in date order.

Fixture-driven like every other book: ``seed_books`` creates it on the next
deploy from ``fixtures/content/books/letters-and-minor-works.en.json``. This
command GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_letters_and_minor_works
"""

from __future__ import annotations

import re
from typing import NamedTuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit, wikisource
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert
from library.titlecase import recase_title

SLUG = "letters-and-minor-works"
TITLE = "Letters and Minor Works"
SUBTITLE = "Translated by M. L. Booth and O. W. Wight"
AUTHOR_SLUG = "blaise-pascal"
HOST = "en.wikisource.org"
ROOT = "Blaise Pascal/"
SOURCE_URL = "https://en.wikisource.org/wiki/Blaise_Pascal"
PUBLICATION_YEAR = 1859
COVER_COLOR = covers.ink_safe("#3e4f46")

AUTHOR_STUB = {"name": "Blaise Pascal", "birth_year": 1623, "death_year": 1662}

DESCRIPTION = (
    "Pascal the man, in his own hand. Here are the letters to his sisters in the "
    "first fervour of the family's conversion; the long letter written after his "
    "father's death, one of the great Christian meditations on dying; and the "
    "letters of spiritual counsel to Mademoiselle de Roannez, written in the year "
    "of the Provincial Letters. Beside them stand his shorter works: the Prayer "
    "to ask of God the right use of sickness, composed in the illness that marked "
    "his last years; the Conversion of the Sinner; his comparison of the first "
    "Christians with those of his own day; and his conversation with M. de Saci "
    "on Epictetus and Montaigne, the germ of the Pensées."
)

ATTRIBUTION = (
    "Public domain — Blaise Pascal's letters, translated by Mary Louise Booth, and "
    "minor works, translated by Orlando Williams Wight (1859), as printed in the "
    "Harvard Classics, vol. 48 (1910); text from Wikisource. The scientific "
    "treatises, the doubtful Discourse on the Passion of Love and the editors' "
    "notes are not included."
)


class Piece(NamedTuple):
    page: str  # under ROOT
    heading: str = ""  # the letter's <h3>; "" for a chapter that is one work
    stop: str = ""  # a centred line where the NEXT work begins on the same scan page
    numbered: bool = False  # centred roman numerals divide it (kept as <h3>)


# (chapter title, pieces). A letter chapter gives each letter its own heading.
CHAPTERS: list[tuple[str, list[Piece], bool]] = [
    (
        "Letters to His Sisters",
        [
            Piece("Letters/To His Sister Jacqueline", "To His Sister Jacqueline"),
            Piece("Letters/To Mme. Perier", "Pascal and Jacqueline to Madame Périer"),
            Piece("Letters/To Mme. Perier (2)", "To Madame Périer"),
        ],
        True,
    ),
    (
        "On the Death of His Father",
        [
            Piece("Letters/To Mme. and M. Perier", "To Madame and Monsieur Périer"),
            Piece("Epitaph of M. Pascal, Pere", "Epitaph of His Father"),
        ],
        True,
    ),
    (
        "Letters to Mademoiselle de Roannez",
        [Piece("Letters/To Mlle. de Roannez", numbered=True)],
        True,
    ),
    (
        "Other Letters",
        [
            Piece("Letters/To Mme. Perier (4)", "To Madame Périer, from Rouen"),
            Piece("Letters/To Mme. Perier (5)", "To Madame Périer, at Clermont"),
            Piece("Letters/To Queen Christina", "To Queen Christina"),
            Piece("Letters/To M. Perier", "To Monsieur Périer, on Jacqueline's Profession"),
            Piece("Letters/To Mme. Perier (3)", "To Madame Périer, on Her Daughter's Vocation"),
            Piece("Letters/To the Marchioness de Sable", "To the Marquise de Sablé"),
            Piece("Letters/To M. Perier (2)", "To Monsieur Périer"),
        ],
        True,
    ),
    (
        "Prayer to Ask of God the Right Use of Sickness",
        [Piece("Prayer, to Ask of God the Proper Use of Sickness")],
        False,
    ),
    ("On the Conversion of the Sinner", [Piece("On the Conversion of the Sinner")], False),
    (
        "Comparison Between Christians of Early Times and Those of To-Day",
        [Piece("Comparison Between Christians of Early Times and Those of To-Day")],
        False,
    ),
    (
        "Discourses on the Condition of the Great",
        [Piece("Discourses on the Condition of the Great", numbered=True)],
        False,
    ),
    (
        "Conversation with M. de Saci on Epictetus and Montaigne",
        [Piece("Conversation on Epictetus and Montaigne")],
        False,
    ),
    ("The Art of Persuasion", [Piece("The Art of Persuasion", stop="DISCOURSE")], False),
]

_ROMAN = re.compile(r"^[ivxlc]+\.?$", re.I)

# Transcription slips, each checked against the text around it. Every pair must
# match exactly once, so a corrected source fails the build instead of drifting.
FIXES = [
    # A page break swallowed "con-": the line reads "afflicted and soled".
    ("afflicted and soled like Christians", "afflicted and consoled like Christians"),
    # A stray note marker ("1*") with no note behind it.
    ("write to us. 1*. I do not remember", "write to us. I do not remember"),
    ("In early times. Christians were", "In early times, Christians were"),
]


def _piece_html(piece: Piece, is_letter: bool) -> str:
    where = f"{ROOT}{piece.page}"
    blocks = wikisource.blocks(wikisource.fetch(HOST, where))
    if piece.stop:
        cut = next((i for i, b in enumerate(blocks) if b.kind == "center" and b.text == piece.stop), None)
        if cut is None:
            raise CommandError(f"{where}: stop line {piece.stop!r} not found.")
        blocks = blocks[:cut]

    out: list[str] = [f"<h3>{piece.heading}</h3>"] if piece.heading else []
    leading = True
    for b in blocks:
        numeral = b.kind == "center" and _ROMAN.match(b.text)
        if piece.numbered and numeral:
            out.append(f"<h3>{b.text.rstrip('.').upper()}</h3>")
            leading = False
            continue
        if leading and b.kind == "center" and not b.text.startswith("("):
            continue  # the work's printed title (the chapter or <h3> carries it)
        leading = False
        if b.kind == "p":
            out.append(f"<p>{b.html}</p>")
        elif b.kind == "right" or (b.kind == "center" and (is_letter or b.text.startswith("("))):
            # A dateline, a superscription or a signature.
            dated = b.kind == "right" and re.search(r"\d", b.text)
            out.append(f"<p><em>{b.html}</em></p>" if dated or b.text.startswith("(") else f"<p>{b.html}</p>")
        else:
            out.append(f"<h3>{recase_title(b.text)}</h3>")  # a section heading
    if len(out) <= (1 if piece.heading else 0):
        raise CommandError(f"{where}: no text.")
    return "".join(out)


def _chapters() -> list[tuple[str, str]]:
    chapters = []
    applied: set[str] = set()
    for n, (title, pieces, is_letter) in enumerate(CHAPTERS, start=1):
        body = "".join(_piece_html(p, is_letter) for p in pieces)
        for bad, good in FIXES:
            if bad in body:
                if body.count(bad) != 1:
                    raise CommandError(f"fix {bad!r} matches {body.count(bad)} times.")
                body = body.replace(bad, good)
                applied.add(bad)
        # Wikisource's straight double quotes -> the corpus's curly ones
        # (apostrophes stay straight, as across the library). Only marks move.
        curled, _ = convert(body, outer_guillemets=False)
        assert_punctuation_only(body, curled, f"{SLUG}[{n}]")
        chapters.append((recase_title(title), curled))
    if missed := [bad for bad, _ in FIXES if bad not in applied]:
        raise CommandError(f"fixes no longer match the source: {missed}")
    return chapters


class Command(BaseCommand):
    help = "Build Pascal's Letters and Minor Works in the dev DB; then serialize the fixture."

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
            "source_url": SOURCE_URL,
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
            if wc < 1000:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:52]:52} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
