"""Build a volume of *A Cloud of Praying Witnesses* from its manuscript.

A house series for adults (Ochorus Originals) on prayer through the whole story
of the church: an Old Testament prelude, Jesus, the apostles, and then the
praying men and women of every century down to today, one volume per era. The
plan of all eleven volumes is ``data/a-cloud-of-praying-witnesses/SERIES-PLAN.md``.

Every volume has the same shape: an Introduction ("Where We Are in the
Story"), its chapters, a Conclusion, and two appendices. Every chapter opens
on a key verse and a story and ends with the same six sections (``REQUIRED``).
Scripture is quoted from the Open Word Bible (OWB), Balanced edition, with the
reader setting that capitalises pronouns for God — the house style of every
other Original; the classic writers are quoted verbatim from their books in
the library.

A volume is three files under ``data/a-cloud-of-praying-witnesses/``:

- ``volume-NN.md``, the manuscript (Ochorus's own writing, nothing fetched), in
  the closed Markdown subset of ``build_rooted.parse``;
- ``volume-NN.chapters.json``, one record per ``##`` section of it: the title
  (checked against the manuscript), the key verse, and the chapter's three
  insights, each under one of the series' ``THEMES``;
- ``volume-NN.appendices.md``, GENERATED here from the other two, never edited:
  Appendix 1 gathers the insights by theme; Appendix 2 indexes every Scripture
  the manuscript cites, in Bible order, read from the prose itself so a verse
  added to a chapter is indexed on the next build. The file is byte-stable, and
  committed so the appendices can be read and reviewed like the chapters.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<slug>.en.json``. Idempotent. The series row lives in
``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_praying_witnesses 2
"""

from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit, scripture
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES_SLUG = "a-cloud-of-praying-witnesses"
SERIES_DIR = DATA_DIR / SERIES_SLUG

ATTRIBUTION = (
    "© Ochorus. An Ochorus Original, free to read and share. Scripture quotations "
    "are from the Open Word Bible (OWB), Balanced edition, which is dedicated to "
    "the public domain (CC0)."
)

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

# A book's heading in the Scripture index where it differs from how a citation
# names it ("Psalm 23:1" sits under "Psalms").
BOOK_HEADINGS = {"Psalm": "Psalms"}

# A citation: "Book C:V", "Book C:V-V", "Book C:V, V" ("1 John 5:14", "1 Kings 8:41, 43").
REF = re.compile(
    r"\b((?:[1-3] )?[A-Z][a-z]+(?: of [A-Z][a-z]+)?) (\d+):(\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)"
)

VOLUMES: dict[int, dict[str, object]] = {
    2: {
        "slug": "jesus-teacher-of-prayer",
        "chapters": 20,
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
                "the cross. Each chapter has a key verse, voices from Murray, Bounds, "
                "Spurgeon and others, three key insights, and a practice for the week."
            ),
            "about_html": (
                "<p>The disciples had watched Jesus heal the sick and calm the storm, "
                "but the one thing they asked Him to teach them was how to pray. This "
                "book sits beside them in that school. It is Volume 2 of <em>A Cloud of "
                "Praying Witnesses</em>, an Ochorus series that follows the people of "
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
                "from the past such as Andrew Murray, E. M. Bounds, Charles Spurgeon, "
                "George Müller and Thomas Watson word for word from their books in the "
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
                    "answer": "Andrew Murray, E. M. Bounds, Charles Spurgeon, George Müller, R. A. Torrey, Dwight L. Moody and Thomas Watson, each quoted exactly from a book you can read in full in the library.",
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


def _label(entry: dict) -> str:
    """How a chapter is named in an index line."""
    if entry["chapter"] == 0:
        return "Introduction"
    if entry["title"].startswith("Conclusion"):
        return "Conclusion"
    return f"Chapter {entry['chapter']}, *{entry['title']}*"


def _sections(manuscript: str) -> list[str]:
    """The manuscript's ``## `` sections, in order (front matter dropped)."""
    return re.split(r"^## ", manuscript, flags=re.M)[1:]


def _citations(section: str) -> list[tuple[str, tuple[int, ...]]]:
    """Each distinct reference a section cites, with its sorted verse ids."""
    seen: dict[str, tuple[int, ...]] = {}
    for book, chap, verses in REF.findall(section):
        for part in verses.split(", "):
            ref = f"{book} {chap}:{part}"
            if ids := tuple(sorted(scripture.reference_verse_ids(ref))):
                seen.setdefault(ref, ids)
    return list(seen.items())


def _appendix_a(entries: list[dict]) -> str:
    by_theme: dict[str, list[str]] = {t: [] for t in THEMES}
    for e in entries:
        for ins in e["insights"]:
            if ins["theme"] not in by_theme:
                raise CommandError(f"chapter {e['chapter']}: unknown theme {ins['theme']!r}; add it to THEMES")
            by_theme[ins["theme"]].append(f"- **{ins['text']}** {_label(e)} ({e['anchor']})")
    out = [
        "## Appendix 1: Key Insights",
        "",
        "Every chapter of this book closes with three key insights. Here they are "
        "gathered by theme, so you can see at a glance what Jesus teaches about each "
        "part of prayer. Each insight points back to the chapter where it is taught "
        "and to that chapter's key verse.",
    ]
    for theme in THEMES:
        if by_theme[theme]:
            out += ["", f"### {theme}", "", *by_theme[theme]]
    return "\n".join(out)


def _appendix_b(entries: list[dict], sections: list[str]) -> str:
    refs: dict[str, dict] = {}
    for e, section in zip(entries, sections, strict=True):
        for ref, ids in _citations(section):
            r = refs.setdefault(ref, {"ids": ids, "chapters": []})
            r["chapters"].append(_label(e) + (" (key verse)" if ref == e["anchor"] else ""))
    out = [
        "## Appendix 2: Scripture Index",
        "",
        "Every passage of Scripture quoted or referred to in this book, in Bible "
        'order, with the chapters where it appears. "Key verse" marks the '
        "Scripture a chapter is built on.",
    ]
    heading = None
    for ref, r in sorted(refs.items(), key=lambda kv: (kv[1]["ids"], kv[0])):
        name, verses = ref.rsplit(" ", 1)
        if name != heading:
            heading = name
            out += ["", f"### {BOOK_HEADINGS.get(name, name)}", ""]
        out.append(f"- **{verses}**: {'; '.join(r['chapters'])}")
    return "\n".join(out)


def appendices(manuscript: str, entries: list[dict]) -> str:
    """Both appendices for a volume, checking its data records against the prose."""
    sections = _sections(manuscript)
    if len(entries) != len(sections):
        raise CommandError(f"{len(entries)} data records but {len(sections)} sections in the manuscript")
    for e, section in zip(entries, sections, strict=True):
        if (title := section.splitlines()[0].strip()) != e["title"]:
            raise CommandError(f"record {e['chapter']} is {e['title']!r} but the manuscript has {title!r}")
    return _appendix_a(entries) + "\n\n---\n\n" + _appendix_b(entries, sections) + "\n"


# ── The book ────────────────────────────────────────────────────────────────


def check_shape(chapters: list[tuple[str, str]], count: int) -> None:
    """Introduction, the chapters, Conclusion, two appendices — each chapter in full shape."""
    titles = [title for title, _ in chapters]
    if (
        len(titles) != count + 4
        or not titles[0].startswith("Introduction")
        or not titles[1 + count].startswith("Conclusion")
        or [t.split(":")[0] for t in titles[2 + count :]] != ["Appendix 1", "Appendix 2"]
    ):
        raise CommandError(f"manuscript is not Introduction, {count} chapters, Conclusion, Appendices 1–2: {titles}")
    for title, html in chapters[1 : 1 + count]:
        missing = [label for label in REQUIRED if f"<h2>{label}</h2>" not in html]
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

        stem = f"volume-{volume:02d}"
        manuscript = (SERIES_DIR / f"{stem}.md").read_text()
        entries = json.loads((SERIES_DIR / f"{stem}.chapters.json").read_text())
        generated = appendices(manuscript, entries)
        (SERIES_DIR / f"{stem}.appendices.md").write_text(generated)

        chapters = parse(manuscript + "\n" + generated)
        check_shape(chapters, meta["chapters"])

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
