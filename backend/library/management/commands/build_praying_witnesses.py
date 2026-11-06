"""Build a volume of *A Cloud of Praying Witnesses* from its manuscript.

A house series for adults on prayer through the whole story of the church, one
volume to an era; the plan of all eleven is
``data/a-cloud-of-praying-witnesses/SERIES-PLAN.md``. Every volume is an
Introduction, its chapters, a Conclusion and two appendices, and every chapter
ends with the same six sections (``REQUIRED``).

A volume is three files under ``data/a-cloud-of-praying-witnesses/``:

- ``volume-NN.md``, the manuscript (Ochorus's own writing, nothing fetched), in
  the closed Markdown subset of ``build_rooted.parse``;
- ``volume-NN.chapters.json``, one record per ``##`` section, in order: its
  title (checked against the manuscript, so a record cannot slip onto the wrong
  chapter), its key verse (which the chapter must cite) and the theme of each
  of its three key insights, from the series' ``THEMES``; the insights
  themselves are read from the chapter's own "Three key insights" list.
  ``person``, ``era``, ``region``, ``voices`` and ``read_more`` are not read
  here: they are kept for the last volume's timeline and reading list, which
  gather every volume's records;
- ``volume-NN.appendices.md``, GENERATED from the other two and never edited:
  Appendix 1 gathers the insights by theme; Appendix 2 indexes every Scripture
  the chapters cite, read from the prose with ``scripture.extract_citations``
  (the reader's own citation grammar), so a verse added to a chapter is
  indexed on the next build. Committed so it can be reviewed like the
  chapters; ``tests_praying_witnesses`` fails when it is stale.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<slug>.en.json``. Idempotent. The series row lives in
``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_praying_witnesses 2
"""

from __future__ import annotations

import html
import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit, scripture
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_faithful_with_little import ATTRIBUTION
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES_SLUG = "a-cloud-of-praying-witnesses"
SERIES_DIR = DATA_DIR / SERIES_SLUG

# The sections every chapter ends with; a chapter missing one is a broken page.
REQUIRED = (
    "Three key insights",
    "For us today",
    "Try this",
    "A closing prayer",
    "Questions for reflection",
    "Read more on Ochorus",
)

# The series' closed theme list, in the order Appendix 1 prints them. Shared by
# every volume, so the last volume's master index can merge their appendices.
THEMES = (
    "The Father's Love",
    "Learning to Pray",
    "Making Room for Prayer",
    "Asking Boldly",
    "Persistence",
    "Faith",
    "Humility and Mercy",
    "Forgiveness",
    "Thanksgiving",
    "Guidance and Surrender",
    "Prayer in Suffering and Testing",
    "Praying Together",
    "Praying for Others",
    "Christ Who Prays for Us",
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "slug": "the-prayers-jesus-learned",
        "book": {
            "publication_year": 2026,
            "title": "The Prayers Jesus Learned",
            "subtitle": "Prayer in the Old Testament",
            "cover_url": "/covers/art/the-prayers-jesus-learned.jpg",
            "cover_color": covers.ink_safe("#1c1f3d"),  # a starlit indigo
            "description": (
                "Seventeen short chapters on the great prayers of the Old Testament, the "
                "prayers Jesus grew up with: Abraham pleading for a city, Jacob wrestling "
                "through the night, Moses standing in the gap, Hannah pouring out her soul, "
                "David's psalms of longing and repentance, Elijah on Mount Carmel, Jonah in "
                "the deep, Daniel at his open window, Nehemiah before the king, and Habakkuk "
                "rejoicing when the fields are bare."
            ),
            "about_html": (
                "<p>When Jesus prayed on the cross, the words that came to His lips were the "
                "words of the Psalms. He had grown up with them: sung on the road to "
                "Jerusalem at the great feasts, heard every Sabbath in the synagogue at "
                "Nazareth, said morning and evening at home. This book listens to those "
                "prayers. It is Volume 1 of A Cloud of Praying Witnesses, an Ochorus series "
                "that follows the people of God at prayer from the first pages of the Bible "
                "to the church around the world today.</p>"
                "<p>Its seventeen chapters move through four parts of the story: the fathers "
                "of faith, Abraham and Jacob; Moses, who stood in the gap for his people and "
                "asked to see God's glory; the judges and kings, from Hannah and Samuel to "
                "David and Solomon; and the prophets, the exile and the return, from Elijah "
                "and Hezekiah to Daniel, Nehemiah, the psalms of lament and Habakkuk. These "
                "were not perfect people, and their prayers are not the prayers of the "
                "strong, but of the weak who learned that God hears.</p>"
                "<p>Every chapter opens with a key verse and a story, quotes voices from the "
                "past such as E. M. Bounds, Andrew Murray and Charles Spurgeon word for word "
                "from their books in the library, and ends with three key insights, a word "
                "for today, a practice to try, a closing prayer and questions for "
                "reflection. Two appendices gather every insight by theme and every "
                "Scripture in Bible order. Scripture is quoted from the Open Word Bible "
                "(OWB), Balanced edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is The Prayers Jesus Learned about?",
                    "answer": "The great prayers of the Old Testament, in seventeen short chapters: Abraham, Jacob, Moses, Hannah, Samuel, David, Solomon, Elijah, Jehoshaphat, Hezekiah, Jonah, Daniel, Nehemiah, the psalms of lament and Habakkuk. These are the prayers Jesus grew up with, and the book shows how He carried them into His own praying.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. This prelude listens to the Old Testament; Volume 2 sits with Jesus, the Teacher of Prayer; later volumes follow the apostles and then the praying men and women of every century and every part of the world, down to the global church today.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "How is each chapter laid out?",
                    "answer": "Each chapter opens with a key verse and a story, looks at what the passage shows about prayer, quotes a voice from the past, and ends with three key insights, a section called For us today, one practice to try that week, a closing prayer and questions for reflection.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes seventeen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    2: {
        "slug": "jesus-teacher-of-prayer",
        "book": {
            "publication_year": 2026,
            "title": "Jesus, Teacher of Prayer",
            "subtitle": "Lord, teach us to pray",
            "cover_color": covers.ink_safe("#2b3a67"),  # a deep before-dawn blue
            "description": (
                "Twenty short chapters on how Jesus prayed and what He taught about "
                "prayer: rising before dawn, praying all night before great "
                "decisions, the Lord's Prayer, the secret room, asking, seeking and "
                "knocking, persistence, humility, faith, praying together, giving "
                "thanks, and His last prayers in the Upper Room, in Gethsemane and on "
                "the cross. Each chapter has a key verse, voices from Andrew Murray, "
                "E. M. Bounds, Thomas Watson, R. A. Torrey and others, three key "
                "insights, and a practice for the week."
            ),
            "about_html": (
                "<p>The disciples had watched Jesus heal the sick and calm the storm, "
                "but the one thing they asked Him to teach them was how to pray. This "
                "book sits beside them in that school. It is Volume 2 of A Cloud of "
                "Praying Witnesses, an Ochorus series that follows the people of "
                "God at prayer from the Old Testament to the church around the world "
                "today, and it begins where every praying Christian has learned: with "
                "Jesus Himself.</p>"
                "<p>Its twenty chapters follow four movements. We watch Jesus at "
                "prayer, before dawn and all night on a mountain. We walk slowly "
                "through the prayer He taught, and into the secret room. We listen to "
                "His teaching: ask, seek and knock; never give up; humble yourself; "
                "believe; pray together; pray for the harvest; give thanks; ask in His "
                "name. And we stand near Him at His last prayers, for Peter, for the "
                "unity of His people, in Gethsemane and on the cross, and end where He "
                "is now, at the right hand of the Father, always living to pray for "
                "us.</p>"
                "<p>Every chapter opens with a key verse and a story, quotes voices "
                "from the past such as Andrew Murray, E. M. Bounds, Thomas Watson, R. A. "
                "Torrey and George Müller word for word from their books in the "
                "library, and ends with three key insights, a word for today, a "
                "practice to try, a closing prayer and questions for reflection. Two "
                "appendices gather every insight by theme and every Scripture in Bible "
                "order. Scripture is quoted from the Open Word Bible (OWB), Balanced "
                "edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Jesus, Teacher of Prayer about?",
                    "answer": "How Jesus prayed and what He taught about prayer, in twenty short chapters: His early mornings and nights of prayer, the Lord's Prayer, the secret room, His teaching on asking, persistence, humility, faith and praying together, and His last prayers for Peter, for His people, in Gethsemane and on the cross, ending with His prayer for us now in heaven.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. After a prelude on the prayers of the Old Testament, it follows Jesus, the apostles, and then the praying men and women of every century and every part of the world, from the martyrs and the desert fathers to the global church today. This book is Volume 2.",
                },
                {
                    "question": "How is each chapter laid out?",
                    "answer": "Each chapter opens with a key verse and a story, looks at what the passage shows about prayer, quotes a voice from the past, and ends with three key insights, a section called For us today, one practice to try that week, a closing prayer and questions for reflection.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which classic writers does it quote?",
                    "answer": "Andrew Murray and E. M. Bounds most often, then Thomas Watson and R. A. Torrey, with George Müller, Dwight L. Moody and Charles Spurgeon, each quoted exactly from a book you can read in full in the library.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
}


# ── The generated appendices ────────────────────────────────────────────────


def _label(index: int, last: int, title: str) -> str:
    """How the section at ``index`` (of ``0..last``) is named in an index line."""
    if index == 0:
        return "Introduction"
    if index == last:
        return "Conclusion"
    return f"Chapter {index}, *{title}*"


# A chapter's "Three key insights" list: each item opens on its insight in bold.
_INSIGHTS = re.compile(r"<h2>Three key insights</h2><ol>(.*?)</ol>")
_INSIGHT = re.compile(r"<li><strong>(.*?)</strong>")


def _span(ref: str) -> tuple[int, int] | None:
    """A reference's first and last verse ids, or None when it is not one."""
    ids = scripture.reference_verse_ids(ref)
    return (min(ids), max(ids)) if ids else None


def appendices(sections: list[tuple[str, str]], entries: list[dict]) -> str:
    """Both appendices for a volume from its parsed ``(title, html)`` sections."""
    if [title for title, _ in sections] != [e["title"] for e in entries]:
        raise CommandError("volume's chapters.json titles do not match the manuscript's ## headings, in order")
    last = len(entries) - 1
    by_theme: dict[str, list[str]] = {t: [] for t in THEMES}
    refs: dict[tuple[int, int], dict] = {}
    for i, ((title, body), e) in enumerate(zip(sections, entries, strict=True)):
        label = _label(i, last, title)
        found = _INSIGHTS.search(body)
        insights = [html.unescape(x) for x in _INSIGHT.findall(found.group(1))] if found else []
        if len(insights) != len(e["themes"]):
            raise CommandError(f"{title!r}: {len(insights)} key insights in the prose, {len(e['themes'])} themes in chapters.json")
        for text, theme in zip(insights, e["themes"], strict=True):
            if theme not in by_theme:
                raise CommandError(f"{title!r}: unknown theme {theme!r}; add it to THEMES")
            by_theme[theme].append(f"- **{text}** {label} ({e['anchor']})")
        anchor = _span(e["anchor"])
        cited = {(c["start"], c["end"]): c["ref"] for c in scripture.extract_citations(body)}
        if anchor not in cited:
            raise CommandError(f"{title!r}: its key verse {e['anchor']!r} is not cited in the chapter")
        for span, ref in cited.items():
            r = refs.setdefault(span, {"ref": ref, "chapters": []})
            r["chapters"].append(label + (" (key verse)" if span == anchor else ""))

    out = [
        "## Appendix 1: Key Insights",
        "",
        "Every chapter of this book closes with three key insights. Here they are "
        "gathered by theme, each pointing back to the chapter where it is taught "
        "and to that chapter's key verse.",
    ]
    for theme in THEMES:
        if by_theme[theme]:
            out += ["", f"### {theme}", "", *by_theme[theme]]
    out += [
        "",
        "---",
        "",
        "## Appendix 2: Scripture Index",
        "",
        "Every passage of Scripture quoted or referred to in this book, in Bible "
        'order, with the chapters where it appears. "Key verse" marks the '
        "Scripture a chapter is built on.",
    ]
    heading = None
    for _, r in sorted(refs.items()):
        if (book := scripture.book_of(r["ref"])) is None:
            raise CommandError(f"{r['ref']!r} names no book of the Bible")
        if book[0] != heading:
            heading = book[0]
            out += ["", f"### {heading}", ""]
        out.append(f"- **{r['ref']}**: {'; '.join(r['chapters'])}")
    return "\n".join(out) + "\n"


def chapter_rows(volume: int) -> tuple[list[tuple[str, str]], str]:
    """A volume's chapters as they are stored, ``(title, body_html)`` with the
    appendices last, through the same cleaning every Original's text takes; and
    the generated appendices' Markdown."""
    sections, generated = volume_text(volume)
    check_shape(sections)
    rows = []
    for order, (title, body) in enumerate(sections + parse(generated), start=1):
        body, _ = convert(clean_fragment(body), outer_guillemets=False)
        title, _ = convert(title, outer_guillemets=False)
        rows.append((title, settled_chapter_body(VOLUMES[volume]["slug"], order, body)))
    return rows, generated


def volume_text(volume: int) -> tuple[list[tuple[str, str]], str]:
    """A volume's parsed manuscript sections and its generated appendices."""
    stem = SERIES_DIR / f"volume-{volume:02d}"
    sections = parse(stem.with_suffix(".md").read_text())
    entries = json.loads(stem.with_suffix(".chapters.json").read_text())
    return sections, appendices(sections, entries)


# ── The book ────────────────────────────────────────────────────────────────


def check_shape(sections: list[tuple[str, str]]) -> None:
    """Introduction, the chapters, Conclusion — each chapter in full shape."""
    titles = [title for title, _ in sections]
    if not titles[0].startswith("Introduction") or not titles[-1].startswith("Conclusion"):
        raise CommandError(f"manuscript is not Introduction, chapters, Conclusion: {titles}")
    for title, body in sections[1:-1]:
        missing = [label for label in REQUIRED if f"<h2>{label}</h2>" not in body]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build a volume of A Cloud of Praying Witnesses (and its appendices) from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int, choices=sorted(VOLUMES))

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        meta = VOLUMES[volume]
        slug = meta["slug"]
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series = Series.objects.get(slug=SERIES_SLUG)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES_SLUG!r} not found — load series.json first.") from exc

        rows, generated = chapter_rows(volume)
        (SERIES_DIR / f"volume-{volume:02d}.appendices.md").write_text(generated)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series,
            "series_position": volume,
            **meta["book"],
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(slug),
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(rows, start=1):
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:56]:56} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
