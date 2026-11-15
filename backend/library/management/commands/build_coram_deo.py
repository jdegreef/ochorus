"""Build *Coram Deo: Living Every Day Before the Face of God* from its manuscript.

A teaching book for every Christian, from new believers to those who have
walked with God for decades, written from James DeGreef's outline: an
Introduction, twenty-seven chapters in five parts (Foundations, Walking with
God, Becoming Like Christ, Living as God's People, Living for God's Purposes), a
Conclusion and an appendix on unity in essentials. Every chapter opens with a
key Scripture, teaches from the Bible, tells the story of one man or woman of
God in depth, and ends with "Questions for reflection" and "A step for this
week".

Scripture is quoted from the Open Word Bible (OWB), Balanced level, with the
reader setting that capitalises pronouns for God — the house style of the other
Originals — and is dedicated to the public domain (CC0). The classic writers are
quoted verbatim from their books in the library.

The prose is committed as Markdown under ``data/coram-deo/`` — one file per
chapter, ``NN.md`` (00 the Introduction … 29 the appendix), each opening with its
``## Title``, in the closed Markdown subset of ``build_rooted.parse`` — with
each chapter's answered questions beside it as ``NN.questions.json``.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/coram-deo.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_coram_deo
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import DATA_DIR, parse
from library.models import Author, Book, Chapter
from library.quote_marks import convert

SLUG = "coram-deo"
#: The founder's outline, written with Ochorus: credited jointly, as a byline.
AUTHOR_SLUG = "james-degreef-and-ochorus"
CHAPTERS = 27
APPENDICES = 1
#: How every chapter (and the Conclusion) ends; a chapter missing one is a broken page.
REQUIRED = ("Questions for reflection", "A step for this week")

ATTRIBUTION = (
    "© James DeGreef and Ochorus. An Ochorus Original, free to read and share. "
    "Scripture quotations are from the Open Word Bible (OWB), Balanced edition, "
    "which is dedicated to the public domain (CC0)."
)

BOOK: dict[str, object] = {
    "publication_year": 2026,
    "title": "Coram Deo",
    "subtitle": "Living every day before the face of God",
    # The joint byline doesn't fit a cover's line; the founder's name does (as on The Lamplighters).
    "cover_byline": "James DeGreef",
    # Sanford Robinson Gifford's Haverstraw Bay (curated_art.CURATED); the page sets the title over it.
    "cover_url": f"/covers/art/{SLUG}.jpg",
    "description": (
        "Coram Deo is Latin for “before the face of God.” This teaching book "
        "for every Christian, from new believers to those who have walked with "
        "God for decades, shows how all of life is lived in His presence: "
        "knowing Father, Son and Holy Spirit; meeting Him daily in the Word, "
        "prayer and the morning watch; becoming like Christ; marriage, family, "
        "work and church; and mission, stewardship and the hope of glory. Each "
        "chapter tells the story of a man or woman of God and ends with "
        "questions and a step for the week."
    ),
    "about_html": (
        "<p>Every one of us lives before someone’s face: parents, employers, "
        "neighbours, the crowd. The Reformers had a phrase for a different way "
        "to live: <em>coram Deo</em>, “before the face of God.” This book is "
        "about that face, and what it means to live every day in His presence. "
        "It is not about earning God’s favour. We walk with Him because, in "
        "Christ, He has already accepted us.</p>"
        "<p>The book moves in five parts. <em>Foundations</em> asks who God is: "
        "Father, Son and Holy Spirit. <em>Walking with God</em> begins with love "
        "and shows how we meet Him daily, in His Word, in prayer, in the morning "
        "watch, in abiding in Christ and in the spiritual disciplines. "
        "<em>Becoming Like Christ</em> covers discipleship, the Sermon on the "
        "Mount, faith, holiness, the healing of the soul, spiritual warfare and "
        "suffering. <em>Living as God’s People</em> turns to marriage and "
        "singleness, children, work, the Church, its ministries and gifts, and "
        "serving one another. <em>Living for God’s Purposes</em> looks to the "
        "Great Commission, stewardship, finishing well and the new heavens and "
        "new earth.</p>"
        "<p>Each chapter opens with Scripture, teaches from the Bible, tells the "
        "story of one man or woman of God, from Augustine of North Africa and "
        "Martin Luther to George Müller, Amy Carmichael, Andrew Murray and Festo "
        "Kivengere of Uganda, and ends with questions for reflection and one "
        "practical step for the week ahead. Where faithful Christians differ, "
        "the book sets out the main views fairly; an appendix explains how to "
        "hold firm on the essentials and extend grace on the rest. Scripture is "
        "quoted from the Open Word Bible (OWB), Balanced edition, which is "
        "dedicated to the public domain.</p>"
    ),
    # The five parts head the contents; the Introduction stands before them.
    "parts": [
        {"title": "Part One: Foundations", "first_chapter": 2},
        {"title": "Part Two: Walking with God", "first_chapter": 5},
        {"title": "Part Three: Becoming Like Christ", "first_chapter": 11},
        {"title": "Part Four: Living as God’s People", "first_chapter": 18},
        {"title": "Part Five: Living for God’s Purposes", "first_chapter": 25},
        {"title": "Appendix", "first_chapter": 30},
    ],
    "qa": [
        {
            "question": "What does Coram Deo mean?",
            "answer": "It is Latin for “before the face of God,” a phrase the Reformers used for living first before God rather than before people. The book takes it as its central idea: every part of life, from the morning watch to work, family, church and mission, is lived in God’s presence.",
        },
        {
            "question": "Who is Coram Deo written for?",
            "answer": "For every Christian: new believers taking their first steps, believers who hold the right beliefs but feel far from God or have grown dry, and those who have walked with God for decades and want to finish well. It was written with the fast-growing churches of Africa, Asia and Latin America in mind.",
        },
        {
            "question": "How is each chapter laid out?",
            "answer": "Each chapter opens with a key Scripture, teaches from the Bible with several passages woven through it, tells in depth the story of one man or woman of God from church history, and ends with questions for reflection and one practical step to take in the week ahead.",
        },
        {
            "question": "Which men and women of God does Coram Deo tell about?",
            "answer": "Witnesses from every century and continent: Augustine, Athanasius and Cyprian of North Africa, Polycarp, Martin Luther, Brother Lawrence, Susanna and John Wesley, George Müller, Hudson Taylor, Andrew Murray, Pandita Ramabai, Sadhu Sundar Singh, Bakht Singh, Watchman Nee, Wang Mingdao, Toyohiko Kagawa, Corrie ten Boom and Alexander Mackay of Uganda, among others. Many of their own books are in the Ochorus library.",
        },
        {
            "question": "How does the book handle questions on which Christians disagree?",
            "answer": "Where faithful Christians differ, on baptism in the Spirit, the gifts of the Spirit or the Sabbath for example, it presents the main positions fairly and then lands on the common ground all share. Where it takes a view of its own it says so plainly, and the Appendix explains how to tell primary beliefs from secondary and tertiary ones.",
        },
        {
            "question": "Which Bible translation does it use?",
            "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
        },
    ],
}


def manuscript() -> tuple[str, dict[str, list]]:
    """The chapter files joined in order, and every chapter's questions by order."""
    folder = DATA_DIR / SLUG
    files = sorted(folder.glob("[0-9][0-9].md"))
    want = [f"{n:02d}.md" for n in range(CHAPTERS + 2 + APPENDICES)]
    if [f.name for f in files] != want:
        raise CommandError(f"data/{SLUG}/ must hold exactly {want[0]}…{want[-1]}: {[f.name for f in files]}")
    questions: dict[str, list] = {}
    for order, f in enumerate(files, start=1):
        qa = json.loads(f.with_suffix(".questions.json").read_text())
        if not (2 <= len(qa) <= 5) or any(
            set(item) != {"question", "answer"} or not all(str(v).strip() for v in item.values())
            for item in qa
        ):
            raise CommandError(f"{f.stem}.questions.json: 2–5 {{question, answer}} pairs, none blank.")
        questions[str(order)] = qa
    return "\n\n".join(f.read_text() for f in files), questions


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, twenty-seven chapters, Conclusion, the appendix — each chapter in full shape."""
    titles = [title for title, _ in chapters]
    if (
        len(titles) != CHAPTERS + 2 + APPENDICES
        or not titles[0].startswith("Introduction")
        or not titles[1 + CHAPTERS].startswith("Conclusion")
        or not all(t.startswith("Appendix") for t in titles[2 + CHAPTERS :])
    ):
        raise CommandError(f"manuscript is not Introduction, {CHAPTERS} chapters, Conclusion, {APPENDICES} appendix: {titles}")
    for title, html in chapters[: 2 + CHAPTERS]:
        missing = [label for label in REQUIRED if f"<h2>{label}</h2>" not in html]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build Coram Deo from its manuscript (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        text, questions = manuscript()
        chapters = parse(text)
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
