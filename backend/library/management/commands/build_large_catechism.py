"""Build Martin Luther's *Large Catechism* (1529) from Project Gutenberg #1722.

F. Bente and W. H. T. Dau's translation from the *Triglot Concordia* (St. Louis:
Concordia, 1921), as keyed for Project Wittenberg. The etext marks its divisions
with plain paragraphs ("The First Commandment.") rather than headings, so
`import_gutenberg` cannot chapter it; this command splits it on those lines:
the two prefaces, each of the Ten Commandments and their conclusion, then the
Creed, the Lord's Prayer, Baptism and the Sacrament of the Altar, each one
chapter with its articles or petitions as subheadings. The etext's opening
credits and closing Project Wittenberg note are left out, and its stray spaces
before stops ("such ?") closed up. Bracketed words are
the translators' additions from the German, kept as printed.

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry.

    DJANGO_DEBUG=true uv run python manage.py build_large_catechism
"""

from __future__ import annotations

import re
from html import escape

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import fetch_html
from library.models import Author, Book, Chapter

SLUG = "large-catechism"
TITLE = "The Large Catechism"
SUBTITLE = "Translated by F. Bente and W. H. T. Dau"
AUTHOR_SLUG = "martin-luther"
COVER_COLOR = "#3e4a2a"
EBOOK = "1722"
SOURCE_URL = f"https://www.gutenberg.org/ebooks/{EBOOK}"
PUBLICATION_YEAR = 1529

DESCRIPTION = (
    "Luther’s catechism for pastors and heads of households (1529): a plain, "
    "searching exposition of the Ten Commandments, the Creed and the Lord’s "
    "Prayer, followed by Baptism and the Lord’s Supper — the five chief parts of "
    "Christian teaching, which he says even a doctor of theology must keep "
    "learning daily."
)
ATTRIBUTION = (
    "Public domain — Martin Luther, The Large Catechism (1529), translated by "
    "F. Bente and W. H. T. Dau in the Triglot Concordia (St. Louis: Concordia "
    "Publishing House, 1921). Text from Project Gutenberg ebook #1722."
)

#: (chapter title, the line that opens it). A line that opens a subheading
#: within the chapter is listed under SUBHEADS instead.
CHAPTERS = [
    ("Preface", r"Preface"),
    ("Short Preface", r"SHORT PREFACE OF DR\. MARTIN LUTHER\."),
    ("The First Commandment", r"Part First\. The Ten Commandments\."),
    ("The Second Commandment", r"The Second Commandment\."),
    ("The Third Commandment", r"The Third Commandment\."),
    ("The Fourth Commandment", r"The Fourth Commandment\."),
    ("The Fifth Commandment", r"The Fifth Commandment\."),
    ("The Sixth Commandment", r"The Sixth Commandment\."),
    ("The Seventh Commandment", r"The Seventh Commandment\."),
    ("The Eighth Commandment", r"The Eighth Commandment\."),
    ("The Ninth and Tenth Commandments", r"The Ninth and Tenth Commandments"),
    ("Conclusion of the Ten Commandments", r"Conclusion of the Ten Commandments\."),
    ("The Creed", r"Part Second\. OF THE CREED\."),
    ("The Lord’s Prayer", r"Part Third\. OF PRAYER\."),
    ("Baptism", r"Part Fourth\."),
    ("The Sacrament of the Altar", r"OF THE SACRAMENT OF THE ALTAR\."),
]
#: Lines kept inside a chapter as subheadings, and lines dropped as redundant
#: with the chapter title.
SUBHEADS = re.compile(
    r"^(?:Article I{1,3}\.|The (?:First|Second|Third|Fourth|Fifth|Sixth) Petition\."
    r"|The Seventh and Last Petition\.|Conclusion)$"
)
DROP = re.compile(r"^(?:The First Commandment\.|The Lord's Prayer\.|OF BAPTISM\.)$")
#: Where the book proper begins and ends in the etext.
START = "A Christian, Profitable, and Necessary Preface"
END = "This text was converted to ASCII format for Project Wittenberg"


def _blocks(html: str) -> list[str]:
    """The book's blocks (paragraphs and headings) as text-bearing HTML, in order."""
    body = html[html.index("*** START") : html.index("*** END")]
    soup = BeautifulSoup(body, "html.parser")
    out, started = [], False
    for el in soup.find_all(["p", "h3", "h4", "h5"]):
        text = re.sub(r"\s+", " ", el.get_text(" ")).strip()
        if not started:
            if not text.startswith(START):
                if text == "Preface":
                    out = ["Preface"]
                continue
            started = True
        if text.startswith(END):
            break
        if text:
            block = re.sub(r"\s+", " ", el.decode_contents()).strip()
            # the etext's stray space before a stop: "such ?", "damned ."
            out.append(re.sub(r"(?<=[\w)\]]) +(?=[?.!;:,](?:\s|$|<))", "", block))
    if not started:
        raise CommandError("the Preface was not found")
    return out


def _chapters(html: str) -> list[tuple[str, str]]:
    blocks = _blocks(html)
    plain = [re.sub(r"<[^>]+>", "", b).strip() for b in blocks]
    starts = []
    for title, pattern in CHAPTERS:
        hits = [i for i, t in enumerate(plain) if re.fullmatch(pattern, t)]
        if len(hits) != 1:
            raise CommandError(f"{title}: {len(hits)} lines match {pattern!r}")
        starts.append(hits[0])
    if starts != sorted(starts):
        raise CommandError("the chapter lines are out of order")
    chapters = []
    for n, (title, _) in enumerate(CHAPTERS):
        a, b = starts[n] + 1, starts[n + 1] if n + 1 < len(starts) else len(blocks)
        parts = []
        for block, text in zip(blocks[a:b], plain[a:b], strict=True):
            if DROP.match(text):
                continue
            if SUBHEADS.match(text):
                parts.append(f"<h3>{escape(text.rstrip('.'), quote=False)}</h3>")
            else:
                parts.append(f"<p>{block}</p>")
        chapters.append((title, "".join(parts)))
    return chapters


class Command(BaseCommand):
    help = "Build Luther's Large Catechism from Project Gutenberg (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(f"author {AUTHOR_SLUG!r} not in the DB — seed the library first.") from None

        chapters = _chapters(fetch_html(EBOOK))
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
            "publication_year": PUBLICATION_YEAR,
        }
        book, was_created = Book.objects.update_or_create(
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
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
