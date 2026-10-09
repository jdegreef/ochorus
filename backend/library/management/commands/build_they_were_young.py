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
    "© Ochorus. An Ochorus Original, written for teenage readers, free to read and "
    "share. The stories are true; the "
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
            "readers aged 13 to 17. Every person in it was once a teenager, "
            "unsure of God. Its verse is 1 Timothy 4:12: “Let no one despise your "
            "youth.” Each chapter tells one life in full, lingering on the "
            "teenage years, when the story turned, and then follows it to the "
            "end.</p>"
            "<p>Book 1, “Called”, gathers six people who came to faith as "
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
            "ends with the person’s own words, four questions to think through, "
            "and a pointer to read on: their own books and sermons where the "
            "library has them, and their biography where it does not. "
            "They are honest about slavery, racism, grief and pressure, and they "
            "work well for a youth group to read and discuss together.</p>"
        ),
        "qa": [
            {
                "question": "What is They Were Young?",
                "answer": "A series of true stories for readers aged 13 to 17 about people whose faith began, or was tested, while they were teenagers. Each chapter tells one life in full and ends with the person’s own words, questions to think through, and a pointer to their own books and sermons in the library, or to their biography where the library has none of their writing.",
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
                "answer": "Yes. Each chapter can be read in one sitting and ends with four questions written for discussion.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Scripture is quoted from the Berean Standard Bible (BSB), which is in the public domain. Where a story gives the words a person actually heard or read in their own day, such as the verse preached to Spurgeon in 1850, it keeps the wording they heard.",
            },
        ],
    },
    2: {
        "sort_order": 141,
        "publication_year": 2026,
        "title": "They Were Young – Book 2: Tested",
        "subtitle": "Six whose faith was tried before they were grown",
        "cover_url": "/covers/they-were-young-2.svg",
        "cover_color": covers.ink_safe("#7a3a2a"),  # an ember red
        "description": (
            "Six true stories for readers aged 13 to 17 of people whose faith was "
            "tested while they were young: a British teenager kidnapped to Ireland; "
            "a Sudanese girl enslaved as a child who chose freedom before the Italian "
            "authorities; a young mother in Carthage who kept a prison diary; the pages "
            "of a Ugandan king who would not deny Christ; a rebellious sailor saved "
            "in a storm; and a Sikh boy who burned a Bible and then met Jesus. The "
            "second book of They Were Young."
        ),
        "about_html": (
            "<p>They Were Young is an original Ochorus series of true stories for "
            "readers aged 13 to 17 about people whose faith began, or was tested, "
            "while they were young. Book 2, “Tested”, gathers six whose faith was "
            "tried by captivity, persecution, loss and their own rebellion.</p>"
            "<p>Patrick was kidnapped from Britain at sixteen and learned to pray "
            "as a slave in Ireland, then went back to the people who had enslaved "
            "him. Josephine Bakhita was stolen from her home in Sudan as a child "
            "and later, before the Italian authorities, chose to stay free. Perpetua, a young "
            "mother in Carthage, kept a diary in prison before she was martyred in "
            "203. The young pages of Kabaka Mwanga of Buganda refused to deny "
            "Christ and died at Namugongo in 1886. John Newton was forced into the "
            "navy at eighteen and cried out to God in a storm at twenty-two. Sundar "
            "Singh burned a Bible at fifteen and, days later, met Jesus.</p>"
            "<p>The stories are true and told without graphic detail. Where a "
            "tradition is legend rather than history, they say so. Each ends with "
            "the person’s own words where we have them, four questions to think "
            "through, and a pointer to read on in the library. Book 1 is not "
            "required.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 2 of They Were Young about?",
                "answer": "Six true stories of people whose faith was tested while they were young: by kidnapping and slavery, by persecution and martyrdom, and by their own rebellion. Each chapter tells one life in full, lingering on the years when the test came.",
            },
            {
                "question": "Who is in Book 2?",
                "answer": "Patrick of Ireland, Josephine Bakhita, Perpetua of Carthage, the Uganda Martyrs, John Newton and Sadhu Sundar Singh: people from Britain, Sudan, North Africa, Uganda and India across sixteen centuries.",
            },
            {
                "question": "Is it suitable for teenagers?",
                "answer": "Yes. It is written for readers aged 13 to 17. It is honest about slavery, kidnapping and martyrdom but never graphic, and the hardest moments are told with care.",
            },
            {
                "question": "Are the stories true?",
                "answer": "Yes. They are drawn from the people’s own writings, such as Patrick’s Confession, Perpetua’s prison diary and Newton’s narrative, and from the earliest accounts. Later legends, such as Patrick and the snakes, are named as legends.",
            },
            {
                "question": "Do I need to read Book 1 first?",
                "answer": "No. Each book stands on its own. Book 1, Called, tells the stories of six people who came to faith as teenagers.",
            },
            {
                "question": "Can it be used in a youth group?",
                "answer": "Yes. Each chapter can be read in one sitting and ends with four questions written for discussion.",
            },
        ],
    },
    3: {
        "sort_order": 143,
        "publication_year": 2026,
        "title": "They Were Young – Book 3: Questions",
        "subtitle": "Six who wrestled with doubt while they were young",
        "cover_url": "/covers/they-were-young-3.svg",
        "cover_color": covers.ink_safe("#2a5a6a"),  # a thinking teal
        "description": (
            "Six true stories for readers aged 13 to 17 of people who wrestled with "
            "big questions while they were young: a restless teenager in Roman "
            "Africa who stole pears for the thrill of it; a French boy who worked "
            "out geometry for himself; a Dissenter's son who wanted something "
            "better to sing; a college student who hated the doctrine he came to "
            "love; a teenage atheist who learned to argue; and a German boy who "
            "chose the church against his family's doubts. The third book of They "
            "Were Young."
        ),
        "about_html": (
            "<p>They Were Young is an original Ochorus series of true stories for "
            "readers aged 13 to 17 about people whose faith began, or was tested, "
            "while they were young. Book 3, “Questions”, gathers six who wrestled "
            "with doubt and the big questions of faith as teenagers, and found that "
            "following Jesus did not mean switching off their minds.</p>"
            "<p>Augustine chased answers through his teenage years in Carthage "
            "until a voice in a Milan garden said, “Take up and read.” Blaise "
            "Pascal was a mathematical prodigy who found that the God of the "
            "philosophers was not enough. Isaac Watts came to trust Christ at about "
            "fifteen and wrote hymns still sung today. Jonathan Edwards argued "
            "against God’s sovereignty until one verse changed how he saw "
            "everything. C. S. Lewis lost his faith at school and became a "
            "confident teenage atheist before the long road back. Dietrich "
            "Bonhoeffer told his family of scientists at fourteen that he would "
            "study theology, and followed that call all the way to a Nazi "
            "prison.</p>"
            "<p>The stories are true, with no invented scenes or conversations; "
            "where the records are silent or a famous story is only a tradition, "
            "they say so. Each ends with the person’s own words, four questions to "
            "think through, and a pointer to read on in the library. Books 1 and 2 "
            "are not required.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 3 of They Were Young about?",
                "answer": "Six true stories of people who wrestled with doubt and the big questions of faith while they were young, and found that faith and thinking belong together. Each chapter tells one life in full, lingering on the teenage years.",
            },
            {
                "question": "Who is in Book 3?",
                "answer": "Augustine of Hippo, Blaise Pascal, Isaac Watts, Jonathan Edwards, C. S. Lewis and Dietrich Bonhoeffer: thinkers, writers and pastors from North Africa, France, England, America, Ireland and Germany across sixteen centuries.",
            },
            {
                "question": "Is it okay to doubt?",
                "answer": "These stories take doubt seriously. Several of the six lost their faith or fought against God as teenagers, and their questions became the road that brought them to Jesus. But none of them made doubt a place to live: they kept looking for the truth.",
            },
            {
                "question": "Are the stories true?",
                "answer": "Yes. They are drawn from the people’s own writings, such as Augustine’s Confessions, Pascal’s Pensées and Edwards’s Personal Narrative, and from the earliest accounts. Where a famous story is a tradition, such as Watts being told to write better hymns, it says so.",
            },
            {
                "question": "Do I need to read Books 1 and 2 first?",
                "answer": "No. Each book stands on its own. Book 1, Called, tells of six people who came to faith as teenagers, and Book 2, Tested, of six whose faith was tested young.",
            },
            {
                "question": "Can it be used in a youth group?",
                "answer": "Yes. Each chapter can be read in one sitting and ends with four questions written for discussion.",
            },
        ],
    },
}


def check_shape(chapters: list[tuple[str, str]]) -> None:
    """Introduction, then STORIES stories, each a full telling — checked before
    anything is written, so a short story never half-rebuilds a volume."""
    titles = [title for title, _ in chapters]
    if len(titles) != STORIES + 1 or not titles[0].startswith("Introduction"):
        raise CommandError(f"manuscript is not Introduction + {STORIES} stories: {titles}")
    for title, body in chapters[1:]:
        if (wc := word_count(body)) < MIN_STORY_WORDS:
            raise CommandError(f"{title!r}: only {wc} words — aborted.")


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
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
