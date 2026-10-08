"""Build a volume of *Real Questions* — honest answers for teens — from its manuscript.

A house-written series for readers aged 13–17: each volume an Introduction,
thirty questions (in three parts) and a Conclusion. Every chapter opens with
"The short answer", gives the longer answer, and ends with "Think about it" and
"Go deeper" (one chapter of a classic in the library). The stance is
mainstream evangelical: core doctrine answered plainly, and the questions on
which faithful Christians differ set out fairly without taking a side.

The prose is committed as Markdown under ``data/real-questions/real-questions-<n>.md``
(Ochorus's own writing, nothing fetched) in the same closed Markdown subset as
the 30-day devotionals, and converted by ``build_rooted.parse``. Adding a
volume is a new manuscript plus one entry in ``VOLUMES``.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/real-questions-<n>.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_real_questions 1
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

SERIES = "real-questions"
QUESTIONS = 30
# The shape every answer promises; a chapter missing one is a broken page.
REQUIRED = ("The short answer:", "Think about it:", "Go deeper:")

ATTRIBUTION = (
    "An Ochorus Original, written for teenage readers. Scripture quotations are "
    "from the Berean Standard Bible (BSB), which is in the public domain."
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 151,
        "publication_year": 2026,
        "title": "Real Questions – Book 1",
        "subtitle": "Honest answers to the questions teens actually ask",
        "cover_url": "/covers/real-questions-1.svg",
        "cover_color": covers.ink_safe("#4a3a7a"),  # a question-mark violet
        "description": (
            "Thirty honest answers for readers aged 13 to 17 to the questions "
            "teenagers actually ask: Isn't God just wishful thinking? What about "
            "dinosaurs? Is hell fair? Aren't all religions the same? What does the "
            "Bible really say about sex, sexuality and gender? Each answer starts "
            "short, then goes deeper, is clear where Christians agree and fair "
            "where they differ, and points to a classic in the library. The first "
            "book of Real Questions."
        ),
        "about_html": (
            "<p>Real Questions is an original Ochorus series for readers aged 13 to "
            "17. It takes the questions teenagers type into a search bar at "
            "midnight and answers them honestly, in plain words, without "
            "slogans.</p>"
            "<p>Book 1 has thirty questions in three parts. “God and the Bible” "
            "asks about wishful thinking, science, dinosaurs, contradictions, Old "
            "Testament violence, grief, doubt, unanswered prayer and miracles. "
            "“Jesus and Other Beliefs” asks whether Jesus was just a good teacher, "
            "whether He really rose, what happens to people who never hear, "
            "whether all religions are the same, about hell, church, death, "
            "assurance and the end of the world. “Life, Sex and Me” asks about sex, "
            "same-sex attraction, gender, women in ministry, drinking and vaping, "
            "money, dating, depression, God’s will and sharing your faith.</p>"
            "<p>Every chapter opens with a short answer and then goes deeper. On "
            "the core of the faith it answers plainly, as most evangelical "
            "churches do, and always with compassion. Where faithful Christians "
            "genuinely disagree, it sets out the main views fairly and says so. "
            "Each chapter ends with a question to think about and a chapter of a "
            "classic to read next. Scripture is quoted from the Berean Standard "
            "Bible.</p>"
        ),
        "qa": [
            {
                "question": "What is Real Questions?",
                "answer": "A series of honest, short answers for readers aged 13 to 17 to the questions teenagers ask about God, the Bible, Jesus, other beliefs, and life. Each chapter starts with a short answer, then goes deeper, and ends with a question to think about and a classic to read next.",
            },
            {
                "question": "What questions does Book 1 answer?",
                "answer": "Thirty, in three parts: God and the Bible (science, dinosaurs, contradictions, suffering, doubt, prayer, miracles), Jesus and Other Beliefs (the resurrection, other religions, hell, church, death, the end of the world), and Life, Sex and Me (sex, sexuality, gender, women in ministry, drinking and vaping, money, dating, depression, God’s will and sharing your faith).",
            },
            {
                "question": "Does it take sides where Christians disagree?",
                "answer": "No. On questions where faithful Christians genuinely differ, such as the age of the earth, whether you can lose your salvation, women as pastors and the timeline of the end, it sets out the main views fairly and says what they all agree on.",
            },
            {
                "question": "What does it say about sexuality and gender?",
                "answer": "It teaches the historic Christian view that sex belongs in marriage between a man and a woman and that God made humanity male and female. It speaks with deep kindness to readers who are struggling, says that feelings and attractions are not themselves sin, and that no one should ever be bullied or shamed.",
            },
            {
                "question": "Do I have to read it in order?",
                "answer": "No. Each chapter stands on its own, so you can start with the question you care about most.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
        ],
    },
}


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, thirty questions, Conclusion — each question in full shape."""
    titles = [title for title, _ in chapters]
    if (
        len(titles) != QUESTIONS + 2
        or not titles[0].startswith("Introduction")
        or not titles[-1].startswith("Conclusion")
    ):
        raise CommandError(f"manuscript is not Introduction, {QUESTIONS} questions, Conclusion: {titles}")
    for title, body in chapters[1:-1]:
        if not title.endswith("?"):
            raise CommandError(f"{title!r}: a question chapter's title must be a question.")
        missing = [label for label in REQUIRED if label not in body]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build a volume of Real Questions (honest answers for teens) from its manuscript (dev DB); then serialize the fixture."

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
            "cover_title": "Real Questions",
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
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:56]:56} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
