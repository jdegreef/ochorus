"""Build *Faithful With Little* — money, stewardship and discipleship — from its manuscript.

A house-written book for adults on money and the Christian life: an
Introduction, twenty chapters in five parts (Whose Is It?, The Heart Behind the
Wallet, Wisdom for Everyday Money, Generous Like God, Treasure That Lasts), a
Conclusion and three appendices (a 30-day reading plan, a one-page money plan
and a ten-week group guide). Every chapter opens with a story, sets one of
thirty key verses, teaches, quotes "A voice from the past" from a classic in
the library, and ends with "Practice this week" and "For groups".

Scripture is quoted from the Open Word Bible (OWB), Balanced level, with the
reader setting that capitalises pronouns for God — the house style of every
other Original — and is dedicated to the public domain (CC0). Each quotation was
checked against the OWB text; the classic writers are quoted verbatim from
their books in the library.

The prose is committed as Markdown under
``data/faithful-with-little/faithful-with-little.md`` (Ochorus's own writing,
nothing fetched) in the closed Markdown subset of ``build_rooted.parse``.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/faithful-with-little.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_faithful_with_little
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter
from library.quote_marks import convert

SLUG = "faithful-with-little"
CHAPTERS = 20
APPENDICES = 3
# The shape every chapter promises; a chapter missing one is a broken page.
REQUIRED = ("A voice from the past", "Practice this week", "For groups")

ATTRIBUTION = (
    "© Ochorus. An Ochorus Original, free to read and share. Scripture quotations "
    "are from the Open Word Bible (OWB), Balanced edition, which is dedicated to "
    "the public domain (CC0)."
)

BOOK: dict[str, object] = {
    "publication_year": 2026,
    "title": "Faithful with Little",
    "subtitle": "Money, wisdom, and treasure that lasts",
    # Georges Michel's plowed field (curated_art.CURATED); the page sets the title over it.
    "cover_url": f"/covers/art/{SLUG}.jpg",
    # The PDF lives in the book-pdfs bucket (export_policy.PDF_STORAGE_URL).
    "pdf_url": f"https://eywunobxqijvwymdzlwy.supabase.co/storage/v1/object/public/book-pdfs/{SLUG}.pdf?download={SLUG}.pdf",
    "cover_color": covers.ink_safe("#1f4a3c"),  # a deep ledger green
    "description": (
        "A short, readable guide to money for people who want to follow Jesus "
        "with all of their life. Twenty chapters walk through the whole Bible "
        "around thirty key verses: God owns it all, the heart behind the "
        "wallet, honest work, planning, debt, generous giving, the poor, and "
        "treasure that lasts, with voices from Wesley, Müller, Spurgeon and "
        "Tozer. Each chapter ends with a practice to try and questions for "
        "small groups."
    ),
    "about_html": (
        "<p>Jesus talked about money more than He talked about heaven or hell, "
        "because He knew that where our treasure goes, our hearts follow. "
        "Faithful With Little is an original Ochorus book for anyone who wants "
        "to follow Him in the part of life that pays the bills. It will not "
        "promise that God will make you rich, and it will not shame you for "
        "having money. Its aim is to make you free.</p>"
        "<p>The book has five parts. “Whose Is It?” lays the foundation: God "
        "owns everything and we manage it for Him. “The Heart Behind the "
        "Wallet” looks at covetousness, worry, contentment and the danger of "
        "riches. “Wisdom for Everyday Money” covers honest work, planning, debt "
        "and providing for a family. “Generous Like God” is about firstfruits, "
        "cheerful giving, the poor, and giving all we can. “Treasure That "
        "Lasts” looks ahead to faithfulness in little things, money and the "
        "mission of God, teaching our children, and the day we hear “Well "
        "done.”</p>"
        "<p>Each chapter takes about ten minutes to read. It opens with a story, "
        "sets one of thirty key verses from across the Bible, quotes a voice "
        "from the past, such as John Wesley, George Müller, Charles Spurgeon, "
        "Hudson Taylor or A. W. Tozer, and ends with one thing to practise this "
        "week and questions for a small group. A 30-day reading plan, a "
        "one-page money plan and a ten-week group guide are at the back. "
        "Scripture is quoted from the Open Word Bible (OWB), Balanced edition, "
        "which is dedicated to the public domain.</p>"
    ),
    "qa": [
        {
            "question": "What is Faithful With Little about?",
            "answer": "Money and discipleship. It walks through what the whole Bible teaches about money in twenty short chapters: that God owns everything, what money does to the heart, honest work, planning, debt, providing for a family, generous giving, caring for the poor, and laying up treasure that lasts.",
        },
        {
            "question": "Does it teach that God will make me rich if I give?",
            "answer": "No. It shows that God does bless generosity, but it is clear that His blessing is not always money, and that Jesus Himself was poor. We give because Christ became poor to make us rich, not as an investment scheme.",
        },
        {
            "question": "Do Christians have to tithe?",
            "answer": "Faithful Christians disagree on whether the tithe is still required, and the book says so. It treats a tenth as a good starting line rather than a ceiling, and puts the weight on giving first, regularly, cheerfully and in proportion to what God has given.",
        },
        {
            "question": "Can I use it with a small group?",
            "answer": "Yes. It was written for groups. Every chapter ends with questions to discuss and one thing to practise that week, and Appendix 3 sets out a ten-week plan of two chapters a week, with notes for leaders.",
        },
        {
            "question": "Which classic writers does it quote?",
            "answer": "John Wesley, Susanna Wesley, George Müller, Hudson Taylor, Charles Spurgeon, A. W. Tozer, Thomas Watson, Andrew Murray, E. M. Bounds, F. B. Meyer, Amy Carmichael, William Seymour, Martyn Lloyd-Jones, Thomas à Kempis and others, each quoted exactly from a book you can read in full in the library.",
        },
        {
            "question": "Which Bible translation does it use?",
            "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
        },
    ],
}


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, twenty chapters, Conclusion, three appendices — each chapter in full shape."""
    titles = [title for title, _ in chapters]
    if (
        len(titles) != CHAPTERS + 2 + APPENDICES
        or not titles[0].startswith("Introduction")
        or not titles[1 + CHAPTERS].startswith("Conclusion")
        or not all(t.startswith("Appendix") for t in titles[2 + CHAPTERS :])
    ):
        raise CommandError(f"manuscript is not Introduction, {CHAPTERS} chapters, Conclusion, {APPENDICES} appendices: {titles}")
    for title, html in chapters[1 : 1 + CHAPTERS]:
        missing = [label for label in REQUIRED if f"<h2>{label}</h2>" not in html]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build Faithful With Little (money and discipleship) from its manuscript (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        chapters = parse((DATA_DIR / SLUG / f"{SLUG}.md").read_text())
        # Each chapter's answered questions ("Questions for reflection"), kept
        # beside the manuscript as {order: [{question, answer}, ...]}.
        questions = json.loads((DATA_DIR / SLUG / "questions.json").read_text())
        if set(questions) != {str(n) for n in range(1, len(chapters) + 1)}:
            raise CommandError("questions.json must hold every chapter's questions, and only those.")
        for order, qa in questions.items():
            if not (2 <= len(qa) <= 5) or any(
                set(item) != {"question", "answer"} or not all(str(v).strip() for v in item.values())
                for item in qa
            ):
                raise CommandError(f"questions.json chapter {order}: 2–5 {{question, answer}} pairs, none blank.")
        check_shape(chapters)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
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
                "sort_order": book_sort_order(SLUG),
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
            Chapter.objects.create(
                book=book,
                order=order,
                title=title,
                body_html=body,
                study_questions=questions[str(order)],
            )
            self.stdout.write(f"  ch {order}: {title[:56]:56} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
