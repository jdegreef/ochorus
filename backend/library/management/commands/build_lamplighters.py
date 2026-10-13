"""Build a volume of *The Lamplighters of Gloamhaven* — a fantasy series for young readers — from its manuscript.

A house-written adventure series for readers aged 9–12, in six books, set in a
land under a cursed sun. Book 1 is *Fire Against the Dark*: a chimney-sweep
orphan finds a brass lamp that cannot be bought, stolen or earned, only given,
and a city falling to the Hollows learns what that means. The series carries
the shape of the Bible's story — grace, faith, temptation, the cross, mission,
new creation — as story, never as sermon: nothing in it names God or quotes
Scripture, in the manner of the classic Christian fantasies.

The prose is committed as Markdown under
``data/the-lamplighters-of-gloamhaven/<slug>.md`` (Ochorus's own writing,
nothing fetched; ``OUTLINE.md`` beside it is the series bible — world rules,
the lamp's law, the fixed cast, the seeds for later books — which every volume
is written against) in the closed Markdown subset of ``build_rooted.parse``:
one ``## Title`` per chapter, one paragraph per line. A novel has no study
questions, so ``study_questions`` stays empty on every chapter.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<slug>.en.json``. Idempotent. The series row lives in
``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_lamplighters 1
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES = "the-lamplighters-of-gloamhaven"

#: The founder's own series, written with Ochorus: credited jointly, as a byline
#: (``is_imprint``), not as a person with a biography.
AUTHOR_SLUG = "james-degreef-and-ochorus"

ATTRIBUTION = (
    "© James DeGreef and Ochorus. An Ochorus Original, written for young "
    "readers, free to read and share. Book 1 of The Lamplighters of Gloamhaven."
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "slug": "fire-against-the-dark",
        "publication_year": 2026,
        "title": "Fire Against the Dark",
        "subtitle": "The Lamplighters of Gloamhaven, Book One",
        # The cover's byline row is one short line; the Ochorus mark at its foot
        # completes "James DeGreef and Ochorus", the byline everywhere else.
        "cover_byline": "James DeGreef",
        "cover_url": "/covers/fire-against-the-dark.svg",
        "cover_color": covers.ink_safe("#b5651d"),  # an ember in the grey
        "description": (
            "In the smoky city of Emberwick the sun has been pale for three "
            "hundred years, and the lamps on the city wall are failing. Wren "
            "Ashby, a chimney-sweep and a thief who believes nothing in life is "
            "free, finds a battered brass lamp hidden in a sealed chimney. It "
            "burns without oil, it relights itself when she blows it out, and "
            "it keeps coming back however hard she tries to sell it. Soon the "
            "Lamp Guild calls it witch-light, the Warden wants it, a captain in "
            "grey has come to bargain for it, and the Hollows are coming over "
            "the wall. With Tobin, the Warden's son who is secretly afraid of "
            "the dark, and Old Ash, the last true Lamplighter, Wren must learn "
            "the lamp's one law before the last light in Emberwick goes out."
        ),
        "about_html": (
            "<p>Fire Against the Dark is the first book of The Lamplighters of "
            "Gloamhaven, an adventure series by James DeGreef and Ochorus for readers aged "
            "nine to twelve, and a good book to read aloud to younger children "
            "too. It is a story of chimneys and rooftops, a city wall lit by "
            "failing lamps, shadow-creatures that drain the colour out of "
            "everything they touch, a clever ember-fox, a gang of thieving "
            "soot-imps, and two children who have to be braver than they "
            "think they are.</p>"
            "<p>Underneath the adventure it is a story about grace. The lamp at "
            "its heart cannot be bought, stolen or earned, only given, and what "
            "is given grows. Wren has spent her whole life believing that "
            "everything costs, and the book follows her slowly learning to "
            "receive a gift, and then to give one away when giving seems to "
            "cost her everything. Like the classic Christian fantasies it "
            "follows, it never preaches and never names the One it points to; "
            "it lets the story carry the meaning, for children to discover and "
            "for parents to talk about.</p>"
            "<p>The book has fifteen chapters, about the length of a classic "
            "children's fantasy, each one a good evening's reading. Five more "
            "books will follow Wren, Tobin and Old Ash on the long road to the "
            "Bright Mountain, where the Flame began.</p>"
            "<p>© James DeGreef and Ochorus. An Ochorus Original, free to read and share.</p>"
        ),
        "qa": [
            {
                "question": "What age is Fire Against the Dark written for?",
                "answer": (
                    "It is written for readers aged nine to twelve, and it reads "
                    "aloud well to younger children from about seven. The peril "
                    "is real but never gory, and there is plenty of humour."
                ),
            },
            {
                "question": "What is the story about?",
                "answer": (
                    "A chimney-sweep orphan called Wren finds a brass lamp that "
                    "burns without oil and cannot be sold. When the city's wall of "
                    "lamps fails and shadow-creatures called Hollows pour in, she "
                    "and her friends must decide what the lamp is for."
                ),
            },
            {
                "question": "What is the lamp's law?",
                "answer": (
                    "Old Ash teaches it in Chapter 8: it cannot be bought, stolen "
                    "or earned, only given. And its second half: what is given, "
                    "grows."
                ),
            },
            {
                "question": "Is it a Christian book?",
                "answer": (
                    "Yes. Like the classic Christian fantasies, it tells the gospel's "
                    "shape as a story rather than a sermon: grace that cannot be "
                    "earned, a light the darkness cannot put out, and a Lampwright "
                    "whose story readers will recognise. It never names God or "
                    "quotes Scripture directly."
                ),
            },
            {
                "question": "Who are the main characters?",
                "answer": (
                    "Wren Ashby, a quick-tongued sweep and thief; Tobin Harrowgate, "
                    "the Warden's clever son, who is secretly afraid of the dark; "
                    "Old Ash, the last true Lamplighter; and Cinder, his ember-fox, "
                    "who sneezes sparks."
                ),
            },
            {
                "question": "Who is the Lampwright?",
                "answer": (
                    "In the old stories he came down from the Bright Mountain with "
                    "true fire, lit lamps for anyone who asked and never charged, "
                    "and was snuffed out on Cinder Hill, until on the third morning "
                    "the Flame burned again on the mountain. Readers may notice that "
                    "he is closer to the story than anyone thinks."
                ),
            },
            {
                "question": "How long is the book?",
                "answer": (
                    "Fifteen chapters and about forty-eight thousand words, much the "
                    "length of a classic children's fantasy. Each chapter is a good "
                    "evening's reading."
                ),
            },
            {
                "question": "Is it part of a series?",
                "answer": (
                    "Yes. It is the first of six books in The Lamplighters of "
                    "Gloamhaven. Each can be read on its own, and together they "
                    "follow the long road to the Bright Mountain."
                ),
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Build a volume of The Lamplighters of Gloamhaven from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int)

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        if volume not in VOLUMES:
            raise CommandError(f"{SERIES} has no volume {volume}; known: {sorted(VOLUMES)}")
        meta = dict(VOLUMES[volume])
        slug = meta.pop("slug")
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series_row = Series.objects.get(slug=SERIES)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES!r} not found — load series.json first.") from exc

        chapters = parse((DATA_DIR / SERIES / f"{slug}.md").read_text())

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series_row,
            "series_position": volume,
            "sort_order": book_sort_order(slug),
            **meta,
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
            Chapter.objects.create(book=book, order=order, title=title, body_html=body, study_questions=[])
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>5} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
