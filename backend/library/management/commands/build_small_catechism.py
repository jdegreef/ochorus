"""Build Martin Luther's *Small Catechism* (1529) from Project Gutenberg #1670.

Robert E. Smith's translation for Project Wittenberg (1994, revised 2004) from
the German of the *Triglot Concordia* (1921), which he placed in the public
domain. The etext sets everything as plain paragraphs, so this command splits
it on its six parts and three appendices and sets the rest as Luther did: each
commandment, article and request as a subheading, and the catechism's
questions ("What does this mean?") in bold above their answers. The etext's
credits, revision note and Project Wittenberg colophon are left out.

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry.

    DJANGO_DEBUG=true uv run python manage.py build_small_catechism
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

SLUG = "small-catechism"
TITLE = "The Small Catechism"
SUBTITLE = "Luther’s Little Instruction Book"
AUTHOR_SLUG = "martin-luther"
COVER_COLOR = "#2f4b3a"
EBOOK = "1670"
SOURCE_URL = f"https://www.gutenberg.org/ebooks/{EBOOK}"
PUBLICATION_YEAR = 1529

DESCRIPTION = (
    "Luther’s little instruction book for the household (1529): the Ten "
    "Commandments, the Creed, the Lord’s Prayer, Baptism, Confession and the "
    "Lord’s Supper, each set out with the question “What does this mean?” and a "
    "short answer for a father to teach his family — with morning and evening "
    "prayers, grace at meals and the household’s duties from Scripture."
)
ATTRIBUTION = (
    "Martin Luther, The Small Catechism (1529), translated by Robert E. Smith for "
    "Project Wittenberg (1994, revised 2004) and placed by him in the public "
    "domain. Text from Project Gutenberg ebook #1670."
)

#: (chapter title, the line that opens it in the etext).
CHAPTERS = [
    ("The Ten Commandments", r"I\. The Ten Commandments .*"),
    ("The Creed", r"II\. The Creed .*"),
    ("The Lord’s Prayer", r"III\. The Our Father .*"),
    ("The Sacrament of Holy Baptism", r"IV\. The Sacrament of Holy Baptism .*"),
    ("How the Uneducated Should Be Taught to Confess", r"V\. How You Should Teach the Uneducated to Confess"),
    ("The Sacrament of the Altar", r"VI\. The Sacrament of the Altar .*"),
    ("Morning and Evening Devotions", r"Appendix I How a Father .*"),
    ("Grace at Meals", r"Appendix II How a Father .*"),
    ("The Home Chart", r"Appendix III The Home Chart .*"),
]
#: The opening line's subtitle, kept as the chapter's first line.
_SUBTITLE = re.compile(r"^(?:[IVX]+\.|Appendix [IVX]+) .*?(The Simple Way .*|How a Father .*|A number of .*)$")
_SUBHEAD = re.compile(
    r"^(?:The (?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth) "
    r"(?:Commandment|Request|Article\b.*)|The Conclusion to the Commandments|Introduction"
    r"|Morning Devotions|Evening Devotions|The Blessing|Thanking God)$"
)
_END = "____"
#: A Home Chart line: who it is for, then the passages ("1 Tim. 3:2-4 Titus 1: 6").
_CHART_LINE = re.compile(r"^((?:For|What Hearers) .*?) ((?:[1-3] )?[A-Z][a-z]+\.? ?\d+: ?\d.*)$")


def _blocks(html: str) -> list[tuple[str, str]]:
    body = html[html.index("*** START") : html.index("*** END")]
    out = []
    for el in BeautifulSoup(body, "html.parser").find_all("p"):
        text = re.sub(r"\s+", " ", el.get_text(" ")).strip()
        if text.startswith(_END):
            break
        if text:
            out.append((text, re.sub(r"\s+", " ", el.decode_contents()).strip()))
    return out


def _chapters(html: str) -> list[tuple[str, str]]:
    blocks = _blocks(html)
    starts = []
    for title, pattern in CHAPTERS:
        hits = [i for i, (t, _) in enumerate(blocks) if re.fullmatch(pattern, t)]
        if len(hits) != 1:
            raise CommandError(f"{title}: {len(hits)} lines match {pattern!r}")
        starts.append(hits[0])
    if starts != sorted(starts):
        raise CommandError("the chapter lines are out of order")
    chapters = []
    for n, (title, _) in enumerate(CHAPTERS):
        first = blocks[starts[n]][0]
        sub = _SUBTITLE.match(first)
        parts = [f"<p><i>{escape(sub.group(1), quote=False)}</i></p>"] if sub else []
        end = starts[n + 1] if n + 1 < len(starts) else len(blocks)
        for text, block in blocks[starts[n] + 1 : end]:
            if _SUBHEAD.match(text):
                parts.append(f"<h3>{escape(text, quote=False)}</h3>")
            elif chart := _CHART_LINE.match(text):
                # the Home Chart's "For Husbands 1 Peter 3:7 …": the station, then its texts
                parts.append(f"<p><b>{escape(chart.group(1).rstrip(':'), quote=False)}:</b> {chart.group(2)}</p>")
            elif text.endswith("?") and len(text) < 90:
                parts.append(f"<p><b>{block}</b></p>")
            else:
                parts.append(f"<p>{block}</p>")
        chapters.append((title, "".join(parts)))
    return chapters


class Command(BaseCommand):
    help = "Build Luther's Small Catechism from Project Gutenberg (dev DB)."

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
            if wc < 100:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
