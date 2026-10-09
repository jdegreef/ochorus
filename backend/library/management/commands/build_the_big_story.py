"""Build *The Big Story* — the whole Bible told as one story for teens — from its manuscript.

A house-written book for readers aged 13–17: an Introduction, thirty chapters
in seven parts that walk through the Bible from creation to new creation, and
a Conclusion. Every chapter names the passage to read ("Read it"), retells it,
shows "Where Jesus is in this", and ends with "Think about it" and "Go deeper"
(one chapter of a classic in the library). The stance is mainstream
evangelical; where faithful Christians differ (Genesis 1, Revelation's
timeline) it says so and takes no side.

The prose is committed as Markdown under ``data/the-big-story/the-big-story.md``
(Ochorus's own writing, nothing fetched) in the same closed Markdown subset as
the 30-day devotionals, and converted by ``build_rooted.parse``.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/the-big-story.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_the_big_story
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter
from library.quote_marks import convert

SLUG = "the-big-story"
CHAPTERS = 30
# The shape every chapter promises; a chapter missing one is a broken page.
REQUIRED = ("Read it:", "Where Jesus is in this", "Think about it:", "Go deeper:")

ATTRIBUTION = (
    "© Ochorus. An Ochorus Original, written for teenage readers, free to read and "
    "share. Scripture quotations are from the Berean Standard Bible (BSB), which "
    "is in the public domain."
)

BOOK: dict[str, object] = {
    "sort_order": 160,
    "publication_year": 2026,
    "title": "The Big Story",
    "subtitle": "The whole Bible for teens, from creation to new creation",
    "cover_url": "/covers/the-big-story.svg",
    "cover_color": covers.ink_safe("#7a5a1a"),  # an old-gold
    "description": "",
    "about_html": "",
    "qa": [],
}


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, thirty chapters, Conclusion — each chapter in full shape."""
    titles = [title for title, _ in chapters]
    if (
        len(titles) != CHAPTERS + 2
        or not titles[0].startswith("Introduction")
        or not titles[-1].startswith("Conclusion")
    ):
        raise CommandError(f"manuscript is not Introduction, {CHAPTERS} chapters, Conclusion: {titles}")
    for title, body in chapters[1:-1]:
        missing = [label for label in REQUIRED if label not in body]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build The Big Story (the whole Bible for teens) from its manuscript (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        chapters = parse((DATA_DIR / SLUG / f"{SLUG}.md").read_text())
        check_shape(chapters)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": None,
            "series_position": None,
            **BOOK,
        }
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body, _ = convert(clean_fragment(body), outer_guillemets=False)
            body = settled_chapter_body(SLUG, order, body)
            title, _ = convert(title, outer_guillemets=False)
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:56]:56} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
