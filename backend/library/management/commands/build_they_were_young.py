"""Build a volume of *They Were Young* — true stories for teens — from its manuscript.

A house-written collection for readers aged 13–17: each volume an
Introduction and six chapter-length true stories of people whose faith began,
or was tested, while they were teenagers. Each story ends with "In Their Own
Words", "Think It Through" and "Read More on Ochorus". It sits between *Brave
for God* (ages 8–12, a few hundred words a life) and *Portraits of Courage*
(adult, book-length).

The prose is committed as Markdown under ``data/they-were-young/they-were-young-<n>.md``
(Ochorus's own writing, nothing fetched) in the same closed Markdown subset as
the 30-day devotionals, and converted by ``build_rooted.parse``. Adding a
volume is a new manuscript plus one entry in ``VOLUMES``.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/they-were-young-<n>.en.json``. Idempotent. The series
row itself lives in ``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_they_were_young 1
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES = "they-were-young"
STORIES = 6
# A story under this is a sketch, not the chapter-length telling the series
# promises (Brave for God is ~450 words a life).
MIN_STORY_WORDS = 2000

ATTRIBUTION = (
    "An Ochorus Original, written for teenage readers. The stories are true; the "
    "telling is our own. Scripture quotations are from the Berean Standard Bible "
    "(BSB), which is in the public domain, except where a story gives the words a "
    "person heard or read in their own day."
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 139,
        "publication_year": 2026,
        "title": "They Were Young – Book 1: Called",
        "subtitle": "Six who met God as teenagers",
        "cover_url": "/covers/they-were-young-1.svg",
        "cover_color": covers.ink_safe("#7a5a1e"),  # a dawn amber
        "description": (
            "Six true stories for readers aged 13 to 17 of people who met God "
            "before they were grown: a fifteen-year-old in a snowstorm who "
            "wandered into the wrong chapel; a Mohegan teenager in the Great "
            "Awakening; a popular Edinburgh student undone by his brother’s "
            "death; a dairy-farm boy at a tent meeting; a Japanese student "
            "pressured into signing a covenant he didn’t believe; and an "
            "enslaved seventeen-year-old in Delaware. The first book of They "
            "Were Young."
        ),
        "about_html": (
            "<p>They Were Young is an original Ochorus series of true stories for "
            "readers aged 13 to 17. Every person in it was once fifteen and "
            "unsure. Its verse is 1 Timothy 4:12: “Let no one despise your "
            "youth.” Each chapter tells one life in full, lingering on the "
            "teenage years, when the story turned, and then follows it to the "
            "end.</p>"
            "<p>Book 1, <em>Called</em>, gathers six people who came to faith as "
            "teenagers. Charles Spurgeon, aged fifteen, heard a stand-in preacher "
            "in a snowbound chapel in Colchester. Samson Occom, a Mohegan "
            "teenager, heard the preachers of the Great Awakening in Connecticut "
            "and went on to become a minister to his own people. Robert Murray "
            "M’Cheyne, a popular student in Edinburgh, turned after the death of "
            "his older brother. Billy Graham, a farm boy more interested in "
            "baseball, went to a tent meeting in 1934. Kanzo Uchimura was "
            "pressured into signing a covenant of faith at a college in Sapporo "
            "and then found it was true. Richard Allen, enslaved in Delaware, met "
            "Christ at seventeen and went on to found the African Methodist "
            "Episcopal Church.</p>"
            "<p>The stories are true, and we have tried not to add to them. Each "
            "ends with the person’s own words, three questions to think through, "
            "and a pointer to their books and sermons in the Ochorus library. "
            "They are honest about slavery, racism, grief and pressure, and they "
            "work well for a youth group to read and discuss together.</p>"
        ),
        "qa": [
            {
                "question": "What is They Were Young?",
                "answer": "A series of true stories for readers aged 13 to 17 about people whose faith began, or was tested, while they were teenagers. Each chapter tells one life in full and ends with the person’s own words, questions to think through, and a pointer to their writing in the library.",
            },
            {
                "question": "Who is in Book 1?",
                "answer": "Charles Spurgeon, Samson Occom, Robert Murray M’Cheyne, Billy Graham, Kanzo Uchimura and Richard Allen: six people from England, North America, Scotland and Japan who all came to faith before they were twenty.",
            },
            {
                "question": "Are the stories true?",
                "answer": "Yes. They are drawn from the people’s own accounts and the earliest biographies. Where the sources are silent or disagree, the stories say so rather than filling the gap.",
            },
            {
                "question": "How is it different from Brave for God?",
                "answer": "Brave for God tells short stories for readers aged 8 to 12. They Were Young is for teenagers: each story is much longer, spends most of its time on the person’s teenage years, and is honest about doubt, pressure and failure.",
            },
            {
                "question": "Can it be used in a youth group?",
                "answer": "Yes. Each chapter can be read in one sitting and ends with three questions written for discussion.",
            },
        ],
    },
}


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, then STORIES stories — the shape the series promises."""
    titles = [title for title, _ in chapters]
    if len(titles) != STORIES + 1 or not titles[0].startswith("Introduction"):
        raise CommandError(f"manuscript is not Introduction + {STORIES} stories: {titles}")


class Command(BaseCommand):
    help = "Build a volume of They Were Young (true stories for teens) from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int)

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        if volume not in VOLUMES:
            raise CommandError(f"{SERIES} has no volume {volume}; known: {sorted(VOLUMES)}")
        slug = f"{SERIES}-{volume}"
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series_row = Series.objects.get(slug=SERIES)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES!r} not found — load series.json first.") from exc

        chapters = parse((DATA_DIR / SERIES / f"{slug}.md").read_text())
        check_shape(chapters)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series_row,
            "series_position": volume,
            "cover_title": "They Were Young",
            **VOLUMES[volume],
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
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
            body = settled_chapter_body(slug, order, body)
            title, _ = convert(title, outer_guillemets=False)
            wc = word_count(body)
            if order > 1 and wc < MIN_STORY_WORDS:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
