"""Build a volume of *Rooted – 30 Days with God for Youth* from its manuscript.

A house-written devotional series for readers aged 9–12: six books of thirty
days each, every day a BSB Scripture, a short teaching, "Think about it" /
"Try this", and a prayer. Each book also has an Introduction and a Conclusion,
so a volume is 32 chapters: the introduction, Day 1 … Day 30, the conclusion.

The prose is committed as Markdown under ``data/rooted/rooted-<n>.md`` (Ochorus's
own writing, nothing fetched) and converted here, so adding Book 2 is a new
manuscript plus one ``VOLUMES`` entry. The Markdown is a closed subset — the
manuscripts are written to it, so anything else is an error, not a guess:

    ## Heading            starts a chapter (its title)
    ### Heading           a section heading inside a chapter (<h2>)
    > line                a blockquote line; each line is its own <p>
    - item / 1. item      list items
    **bold**, *italic*    inline
    # Heading, ---        structure for the manuscript's reader only; dropped

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/rooted-<n>.en.json``. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_rooted 1
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import convert

DATA_DIR = Path(__file__).resolve().parent / "data" / "rooted"
AUTHOR_SLUG = "ochorus-originals"
DAYS = 30

ATTRIBUTION = (
    "An Ochorus Original, written for young readers. Scripture quotations are "
    "from the Berean Standard Bible (BSB), which is in the public domain."
)

# Per volume: the Book fields. `sort_order` is fixed here rather than taken from
# the dev DB's max, which holds only what has been built locally.
VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 75,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 1",
        "subtitle": "Planted: knowing God, receiving Jesus, and learning to grow",
        # Asserted here, not left to `generate_covers`, so a rebuild in a fresh
        # worktree (empty DB) cannot serialize a fixture with no cover.
        "cover_url": "/covers/rooted-1.svg",
        "cover_color": covers.ink_safe("#3f6b3a"),  # a deep leaf green
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12. Each day opens "
            "with a verse from the Bible, explains what it means for a young "
            "reader’s life, asks one question to think about and one thing to "
            "try, and ends with a prayer. Book 1 plants the roots: who God is, the "
            "good news of Jesus, who you are in Christ, how to pray, and how the "
            "Bible, church and worship help you grow. The first book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its first book. Its picture is a tree: a tree with "
            "deep roots keeps standing when the storms come, and Colossians 2:7 "
            "asks the same of us, to be rooted and built up in Christ. Six books "
            "of thirty days each walk that picture from the roots to the fruit.</p>"
            "<p>Book 1 lays the foundation over five weeks. The first asks who God "
            "is: the Creator who names every star, holy and full of love, and "
            "never changing. The second tells the best news ever, from the garden "
            "to the cross and the empty tomb, and ends with a clear, gentle "
            "invitation to trust Jesus. The third shows a young reader who they "
            "are in Christ: made on purpose, a child of God, forgiven, never "
            "alone. The fourth teaches prayer through the Lord’s Prayer, and the "
            "fifth shows how the Bible, obeying, church and worship make the roots "
            "grow deep.</p>"
            "<p>Every day follows the same short pattern, a few minutes long: a "
            "Scripture from the Berean Standard Bible, a teaching told with a "
            "story or a picture from everyday life, a question to think about, one "
            "thing to try that day, and a prayer to pray. It is written to be read "
            "alone by a young reader, and it works just as well read aloud at "
            "bedtime or around the table, where the questions make good "
            "conversation starters.</p>"
        ),
        "qa": [
            {
                "question": "What is Rooted – 30 Days with God for Youth?",
                "answer": "A series of short daily devotions for readers aged 9 to 12. Each day has a verse from the Bible, a few minutes of teaching about what it means, a question to think about, one thing to try that day, and a prayer. This is Book 1 of six.",
            },
            {
                "question": "What does Book 1 cover?",
                "answer": "It plants the roots of faith over five weeks: who God is, the good news of Jesus from the garden to the empty tomb, who you are in Christ, how to talk with God in prayer, and how the Bible, obeying, church and worship help you grow.",
            },
            {
                "question": "Why is the series called Rooted?",
                "answer": "Because of Colossians 2:6–7, which asks those who have received Christ Jesus as Lord to be “rooted and built up in Him.” A tree with deep roots keeps standing when storms come, and the series helps young readers grow deep roots in Jesus one day at a time.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "Can a parent read it with a child?",
                "answer": "Yes. It is written for young readers to read on their own, but it works just as well read aloud together. The “Think about it” questions make good conversation starters at bedtime or around the table.",
            },
            {
                "question": "What if I miss a day?",
                "answer": "Just pick up where you left off. The book is not a test, and God is not keeping score. What matters is spending time with Him and letting your roots keep growing.",
            },
        ],
    },
}

_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\*(.+?)\*"), r"<em>\1</em>"),
]
_LIST = re.compile(r"^(?:-|\d+\.) (.*)$")
# `quote_marks.convert` sets the double marks; single marks are ours to set. A
# mark after a space, a dash or an opening mark opens a nested quotation;
# everything else is an apostrophe or a closing mark.
_OPEN_SINGLE = re.compile(r"(^|[\s\"“(—])'")


def _single_marks(text: str) -> str:
    return _OPEN_SINGLE.sub(r"\1‘", text).replace("'", "’")


def _inline(text: str) -> str:
    out = html.escape(_single_marks(text), quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def _blocks(lines: list[str]) -> str:
    """One chapter's Markdown lines as HTML."""
    out: list[str] = []
    para: list[str] = []
    quote: list[str] = []
    items: list[str] = []
    list_tag = ""

    def flush():
        nonlocal list_tag
        if para:
            out.append("<p>" + "<br>".join(_inline(x) for x in para) + "</p>")
            para.clear()
        if quote:
            out.append(
                "<blockquote>"
                + "".join(f"<p>{_inline(x)}</p>" for x in quote if x)
                + "</blockquote>"
            )
            quote.clear()
        if items:
            out.append(
                f"<{list_tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items)
                + f"</{list_tag}>"
            )
            items.clear()
            list_tag = ""

    for line in lines:
        line = line.rstrip()
        if line.startswith(">"):
            if para or items:
                flush()
            quote.append(line[1:].strip())
            continue
        m = _LIST.match(line)
        if m:
            tag = "ul" if line.startswith("-") else "ol"
            if para or quote or (items and tag != list_tag):
                flush()
            list_tag = tag
            items.append(m.group(1))
            continue
        if not line.strip() or line.strip() == "---":
            flush()
            continue
        if line.startswith("### "):
            flush()
            out.append(f"<h2>{_inline(line[4:])}</h2>")
            continue
        if line.startswith("#"):
            raise CommandError(f"unexpected heading inside a chapter: {line!r}")
        if quote or items:
            flush()
        para.append(line.strip())
    flush()
    return "".join(out)


def parse(manuscript: str) -> list[tuple[str, str]]:
    """``(title, body_html)`` per chapter, in order."""
    chapters: list[tuple[str, list[str]]] = []
    for line in manuscript.splitlines():
        if line.startswith("## "):
            chapters.append((_single_marks(line[3:].strip()), []))
        elif line.startswith("# "):
            continue  # the book title and week dividers
        elif chapters:
            chapters[-1][1].append(line)
    return [(title, _blocks(lines)) for title, lines in chapters]


def check_shape(titles: list[str]) -> None:
    """Introduction, Day 1 … Day 30, Conclusion — the shape the plan relies on."""
    want = [f"Day {n} " for n in range(1, DAYS + 1)]
    days = titles[1:-1]
    if (
        len(titles) != DAYS + 2
        or not titles[0].startswith("Introduction")
        or not titles[-1].startswith("Conclusion")
        or any(not t.startswith(w) for t, w in zip(days, want, strict=True))
    ):
        raise CommandError(f"manuscript is not Introduction, Day 1–{DAYS}, Conclusion: {titles}")


class Command(BaseCommand):
    help = "Build a volume of 'Rooted – 30 Days with God for Youth' from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int, choices=sorted(VOLUMES))

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        meta = VOLUMES[volume]
        slug = f"rooted-{volume}"
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        chapters = parse((DATA_DIR / f"{slug}.md").read_text())
        check_shape([title for title, _ in chapters])

        content = {"author": author, "attribution": ATTRIBUTION, "source_url": "", **meta}
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
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
