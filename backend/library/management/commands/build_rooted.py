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
    2: {
        "sort_order": 76,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 2",
        "subtitle": "Following Jesus: walking with Jesus from the manger to the empty tomb",
        "cover_url": "/covers/rooted-2.svg",
        "cover_color": covers.ink_safe("#7a4a2a"),  # a rich soil brown
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 that walk "
            "through the life of Jesus, from the manger in Bethlehem to the empty "
            "tomb. Each day opens with a passage from the Gospels, shows what it "
            "reveals about Jesus, asks one question to think about and one thing "
            "to try, and ends with a prayer. The second book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its second book. Book 1 planted the roots: who God "
            "is, the good news, and how to pray and grow. Book 2 turns to the one "
            "those roots grow into, and spends thirty days walking beside Jesus "
            "through His life on earth, drawing on all four Gospels.</p>"
            "<p>The five weeks follow His story in order. Jesus arrives: the "
            "manger, the shepherds, the wise men, and the twelve-year-old in His "
            "Father’s house. Jesus begins: His baptism, His temptation in the "
            "wilderness, and the fishermen He called to follow Him. Jesus’ power: "
            "a storm stilled, a boy’s lunch that fed thousands, a blind beggar "
            "healed and Lazarus called out of the tomb. Jesus’ teaching: the "
            "Beatitudes, salt and light, the lost sheep, the runaway son and the "
            "good Samaritan. And Jesus wins: Zacchaeus, the donkey and the "
            "palm branches, the towel and basin, the cross and the empty tomb, "
            "ending with the Great Commission.</p>"
            "<p>Every day follows the same short pattern: a passage from the "
            "Berean Standard Bible, a teaching that tells the story and asks what "
            "it shows about Jesus, a question to think about, one thing to try "
            "that day, and a prayer. It can be read alone or aloud together, and "
            "it works whether or not a reader has started with Book 1.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 2 of Rooted about?",
                "answer": "It walks young readers through the life of Jesus in thirty short daily devotions, from His birth in Bethlehem to His resurrection and His last command to go and make disciples. Each day has a Bible passage, a short teaching, a question, something to try and a prayer.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. The stories come from all four Gospels, so it also makes a good first walk through the life of Christ.",
            },
            {
                "question": "Do I need to read Book 1 first?",
                "answer": "No. Book 2 stands on its own, and its introduction explains how each day works. Book 1 lays the foundation (who God is, the good news of Jesus and how to pray), so reading it first helps, but you can start right here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "How does it handle the crucifixion?",
                "answer": "Honestly but gently. Week 5 tells the story of Jesus’ arrest, the cross and the empty tomb in words suited to young readers, focusing on why Jesus died and what His resurrection means.",
            },
            {
                "question": "What comes after Book 2?",
                "answer": "Book 3, which is about growing fruit: how staying connected to Jesus, the vine, grows love, joy, peace, kindness and self-control, and shapes the words we say and the habits we build.",
            },
        ],
    },
    3: {
        "sort_order": 77,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 3",
        "subtitle": "Growing Fruit: the fruit of the Spirit, the words we say, and the habits of the heart",
        "cover_url": "/covers/rooted-3.svg",
        "cover_color": covers.ink_safe("#5a3a6e"),  # a ripe-grape purple
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about the "
            "fruit God grows in those who stay connected to Jesus, the Vine: "
            "love, joy, peace, patience, kindness and more, the words we say, the "
            "habits of the heart, and being wise and honest. Each day has a Bible "
            "verse, a short teaching, a question, something to try and a prayer. "
            "The third book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its third book. Book 1 planted the roots and Book "
            "2 walked with Jesus through His life. Book 3 asks what grows on a "
            "tree that is rooted in Him, and its answer begins where Jesus did: "
            "“I am the vine and you are the branches.” Good fruit is not glued on "
            "by trying harder. It grows from staying connected to the Vine.</p>"
            "<p>The first two weeks take the fruit of the Spirit one at a time, "
            "from love, joy and peace to gentleness and self-control, with a day "
            "on humility as the soil the rest grow in. The third week is about "
            "words: the tiny spark of the tongue, telling the truth, words that "
            "build, grumbling, gossip and listening. The fourth turns to habits of "
            "the heart: respect, thankfulness, working as for the Lord, "
            "contentment, generosity and guarding the heart. The fifth is about "
            "being pure and wise: asking for wisdom, what we think about and "
            "watch, integrity when no one is looking, and the fall that pride "
            "brings.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching with a Bible story or a picture "
            "from everyday life, a question to think about, one thing to try, and "
            "a prayer. It is written to keep character rooted in grace, pointing "
            "young readers back to Jesus and His Spirit rather than to "
            "self-improvement, and it can be read alone or aloud together.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 3 of Rooted about?",
                "answer": "Growing fruit. Over thirty short daily devotions it looks at the fruit of the Spirit, the words we say, the habits of the heart, and being wise and honest, always starting from Jesus’ words: “I am the vine and you are the branches.”",
            },
            {
                "question": "Is it just a list of rules for being good?",
                "answer": "No. Its main point is that you cannot grow good fruit by trying harder on your own. Fruit grows by staying connected to Jesus, as His Spirit works in you. Every day points back to Him.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. The week on words and the day on screens make especially good family conversations.",
            },
            {
                "question": "Do I need to read Books 1 and 2 first?",
                "answer": "No. Each book stands on its own, and the introduction explains how each day works. The earlier books lay the foundation and walk through the life of Jesus, so reading them first helps, but you can start here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 3?",
                "answer": "Book 4, about standing strong in the storms of life: fear, worry, sadness, temptation and unfairness, with Bible heroes like David, Daniel, Joseph and Esther, and the promise that nothing can separate us from God’s love.",
            },
        ],
    },
    4: {
        "sort_order": 78,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 4",
        "subtitle": "Strong in the Storm: courage for when you’re afraid, sad, tempted or treated unfairly",
        "cover_url": "/covers/rooted-4.svg",
        "cover_color": covers.ink_safe("#34495e"),  # a storm-cloud slate
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about standing "
            "strong in the storms of life: fear, worry, sadness and grief, "
            "temptation, and times when life isn’t fair. With David, Joseph, "
            "Daniel, his three friends and Esther, and the armor of God. Each day "
            "has a Bible verse, a short teaching, a question, something to try "
            "and a prayer. The fourth book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its fourth book. It begins with Jesus’ story of "
            "two builders: the storm hit both houses, and the one on the rock "
            "stood. Storms come to everyone, and Book 4 is about the foundation "
            "that holds when they do.</p>"
            "<p>The first week is about fear, with David’s trust, the Shepherd "
            "of Psalm 23, Joshua’s courage, Goliath, and sleeping in peace. The "
            "second is about worry and sadness: casting cares on God, praying "
            "instead of worrying, Jesus weeping, grieving with hope when someone "
            "dies, and God as Father when home is hard. The third faces "
            "temptation with Joseph and Daniel, and teaches how to get back up "
            "after a fall. The fourth puts on the armor of God and stands with "
            "Shadrach, Meshach and Abednego, Daniel in the lions’ den, and "
            "Esther. The fifth holds on to hope: Joseph’s “God intended it for "
            "good,” God’s higher ways, wings like eagles, grace that is enough, "
            "and the love nothing can separate us from.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. The days on grief and on a hard home "
            "are written gently and point readers to a trusted adult, and "
            "several days remind them to tell a trusted adult if anyone is "
            "hurting them.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 4 of Rooted about?",
                "answer": "Standing strong in the storms of life. Over thirty short daily devotions it helps young readers face fear, worry, sadness, temptation and unfairness by trusting God, with stories of David, Joseph, Daniel, his three friends and Esther.",
            },
            {
                "question": "Does it talk about hard things like death or trouble at home?",
                "answer": "Yes, gently. Day 10 is about grieving with hope when someone dies, and Day 11 is about when home is hard. Both encourage readers to talk with a trusted adult, and parents may want to read those days together with their child.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. It is especially helpful for a child who is going through something scary or sad.",
            },
            {
                "question": "Do I need to read the earlier books first?",
                "answer": "No. Each book of Rooted stands on its own, and the introduction explains how each day works. The earlier books help, but you can start here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 4?",
                "answer": "Book 5, about how God’s love reaches out through us: loving family, being a true friend, forgiving, belonging to God’s family at church, and caring about people all over the world.",
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
# mark after a space, a dash or an OPENING double mark opens a nested
# quotation; everything else is an apostrophe or a closing mark — including
# one after a closing double mark (`…of God."'"`).
_OPEN_SINGLE = re.compile(r"(^\"|(?<=\s)\"|^|[\s“(—])'")


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
