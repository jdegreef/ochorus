"""Build four books by George MacDonald from their Standard Ebooks editions.

* *Phantastes: A Faerie Romance for Men and Women* (1858) — twenty-five
  chapters, untitled in the book (each opens with its epigraphs, and the reader
  names them "Chapter N", as for Bounds's *Purpose in Prayer*).
* *The Diary of an Old Soul* (1880; *A Book of Strife, in the Form of the Diary
  of an Old Soul*) — 366 seven-line stanzas, one for each day of the year,
  folded into twelve month chapters with each day under its own ``<h3>``
  ("January 1"), the shape ``group_daily_entries`` gives a daily devotional.
  MacDonald's dedication opens January. Standard Ebooks prints it inside its
  collected *Poetry*, so the one poem is cut from that file.
* *At the Back of the North Wind* (1871) — thirty-eight titled chapters.
* *The Princess and the Goblin* (1872) — thirty-two titled chapters.

Standard Ebooks' editions are proofread against page scans and their own
contributions are dedicated to the public domain (CC0). Their source files are
read from the Standard Ebooks repositories on GitHub (standardebooks.org and
gutenberg.org refuse this environment's egress), the ``build_chesterton`` route,
and its helpers are reused. Only the author's text is taken: the title pages,
imprint, colophon, uncopyright and endnotes are left out (the one endnote in
the *Diary*, on the blank pages of the first printing, is the editor's), as are
*Phantastes*'s two prefatory epigraphs (Fletcher and Novalis, before the
story) — each chapter's own epigraphs are kept.

How the text is read:

* verse (MacDonald's songs, his chapter epigraphs, the nursery rhymes in *North
  Wind*) keeps its line breaks, one ``<p>`` per stanza inside a
  ``<blockquote>``; an epigraph's source follows it as "— Shelley's Alastor";
* scene breaks are ``<hr>``; the tale of Cosmo that Anodos reads in the fairy
  palace, and the two poems in *North Wind*, are flattened into their chapter,
  the poems keeping their own titles as ``<h3>``;
* Standard Ebooks' invisible line-breaking aids are removed, as in
  ``build_chesterton``. The one figure (the mark on the wise woman's palm,
  *Phantastes* ch. 19) is described in brackets from the edition's own alt
  text, since a chapter body carries no images.

Fixture-driven like every other book: ``seed_books`` creates each book (the
author already lives in ``authors.json``) on the next deploy from
``fixtures/content/books/<slug>.en.json``. This command GENERATES those
fixtures reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_macdonald [slug ...]
"""

from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_chesterton import _block, _fetch, _inline
from library.management.commands.import_gutenberg import _MONTHS
from library.models import Author, Book, Chapter

AUTHOR_SLUG = "george-macdonald"
AUTHOR_STUB = {"name": "George MacDonald", "birth_year": 1824, "death_year": 1905}


@dataclass(frozen=True)
class Work:
    slug: str
    title: str
    subtitle: str
    repo: str
    publication_year: int
    cover_color: str
    source_url: str
    description: str
    attribution: str
    chapters: int  # how many chapter-N.xhtml files (0: the Diary)
    min_words: int = 1000


PHANTASTES = Work(
    slug="phantastes",
    title="Phantastes",
    subtitle="A Faerie Romance for Men and Women",
    repo="george-macdonald_phantastes",
    publication_year=1858,
    cover_color=covers.ink_safe("#35553f"),
    source_url="https://standardebooks.org/ebooks/george-macdonald/phantastes",
    description=(
        "On the morning after his twenty-first birthday, a young man named "
        "Anodos wakes to find the stream from his washbasin running across his "
        "carpet and his bedroom turning into a wood: he has crossed into Fairy "
        "Land. Following a path into the forest, he meets the friendly spirits "
        "of the trees and the treacherous Alder-maiden, opens a forbidden door "
        "and gains a shadow that withers whatever it falls on, reads strange "
        "tales in a palace of the fairies, sings a marble lady to life and loses "
        "her, and learns at last, through failure and death, that the way to "
        "find himself is to lose himself in love. MacDonald's first romance is "
        "the book that a young atheist named C. S. Lewis bought at a railway "
        "bookstall in 1916, and later said had baptized his imagination."
    ),
    attribution=(
        "Public domain — George MacDonald's Phantastes: A Faerie Romance for Men "
        "and Women (1858). Text from the Standard Ebooks edition (CC0), which "
        "follows Project Gutenberg ebook 325 checked against scans of early "
        "printings, with lightly modernised spelling. All twenty-five chapters "
        "are complete with their epigraphs; the two epigraphs before the story "
        "are not included."
    ),
    chapters=25,
    min_words=500,
)

DIARY = Work(
    slug="diary-of-an-old-soul",
    title="The Diary of an Old Soul",
    subtitle="A Book of Strife",
    repo="george-macdonald_poetry",
    publication_year=1880,
    cover_color=covers.ink_safe("#5a4637"),
    source_url="https://standardebooks.org/ebooks/george-macdonald/poetry",
    description=(
        "In 1880, in years of illness and of grief for children he had lost, "
        "George MacDonald printed for his friends a book of prayer in verse: "
        "one seven-line stanza for every day of the year, with a blank page "
        "facing each for the reader's own. The old soul of the title talks "
        "honestly with God through dullness, doubt, pain and joy, asking not to "
        "be spared the strife but to be made true in it, and learning to rest "
        "in the will of a Father who is nearer than his own heart. Read a "
        "stanza a day, from the first of January to the last of December, it "
        "is one of the most searching devotional poems in English."
    ),
    attribution=(
        "Public domain — George MacDonald's A Book of Strife, in the Form of the "
        "Diary of an Old Soul (1880). Text from the Standard Ebooks edition of "
        "MacDonald's Poetry (CC0), which follows the 1880 printing. All 366 "
        "daily stanzas and the dedication are complete; each month is one "
        "chapter."
    ),
    chapters=0,
)

NORTH_WIND = Work(
    slug="at-the-back-of-the-north-wind",
    title="At the Back of the North Wind",
    subtitle="",
    repo="george-macdonald_at-the-back-of-the-north-wind",
    publication_year=1871,
    cover_color=covers.ink_safe("#2c4763"),
    source_url="https://standardebooks.org/ebooks/george-macdonald/at-the-back-of-the-north-wind",
    description=(
        "Little Diamond, a coachman's son, sleeps in a hayloft over the horses, "
        "and one night the wind that blows through a hole in the boards speaks "
        "to him. She is North Wind, a great and beautiful lady who carries him "
        "through the night on her errands, some of them kind and some of them "
        "terrible, and at last takes him to the strange, quiet country at her "
        "back. Home again in the poor streets of London, Diamond drives his "
        "father's cab, befriends a crossing-sweeper and a drunken cabman's "
        "family, and carries a quiet goodness into every place he goes. "
        "MacDonald's tender, mysterious story for children of every age is "
        "about suffering, trust and a love that is at work even in the dark."
    ),
    attribution=(
        "Public domain — George MacDonald's At the Back of the North Wind (1871). "
        "Text from the Standard Ebooks edition (CC0), which follows Project "
        "Gutenberg ebook 225 checked against a scan of an early printing, with "
        "lightly modernised spelling. All thirty-eight chapters are complete, "
        "with the songs and rhymes that Diamond sings and reads."
    ),
    chapters=38,
    min_words=500,
)

PRINCESS = Work(
    slug="the-princess-and-the-goblin",
    title="The Princess and the Goblin",
    subtitle="",
    repo="george-macdonald_the-princess-and-the-goblin",
    publication_year=1872,
    cover_color=covers.ink_safe("#6a3f63"),
    source_url="https://standardebooks.org/ebooks/george-macdonald/the-princess-and-the-goblin",
    description=(
        "Princess Irene is eight years old and lives in a great house on a "
        "mountainside, under which the goblins dig and plot in the dark. One "
        "rainy day she climbs a forgotten stair and finds, spinning at the top "
        "of the house, a beautiful old lady who says she is her "
        "great-great-grandmother, and whom nobody else believes in. Her gift is "
        "a ring and a thread too fine to see, which will always lead Irene where "
        "she must go; and when Curdie, the brave miner boy who drives the "
        "goblins off with rhymes, is caught inside the mountain, she must trust "
        "the thread to lead her in after him. MacDonald's best-loved fairy tale is a story about faith in "
        "what cannot be seen, and about a child who believes."
    ),
    attribution=(
        "Public domain — George MacDonald's The Princess and the Goblin (1872). "
        "Text from the Standard Ebooks edition (CC0), which follows Project "
        "Gutenberg ebook 708 checked against a scan of the 1872 printing, with "
        "lightly modernised spelling. All thirty-two chapters are complete, with "
        "Curdie's rhymes and the goblins' songs."
    ),
    chapters=32,
    min_words=300,
)

WORKS = {w.slug: w for w in (PHANTASTES, DIARY, NORTH_WIND, PRINCESS)}

# Unambiguous slips, each checked to occur exactly the given number of times in
# the built chapter bodies (book-wide), so a changed edition fails loudly.
SOURCE_FIXES: dict[str, tuple[tuple[str, str, int], ...]] = {}

# The one figure in the four books: the wise woman's palm, Phantastes ch. 19.
_PALM_MARK = "[a wavy line above a bowl-shaped line]"


def _prepare(node: Tag) -> None:
    """Rewrite what ``_inline`` does not take: q, img, and editors' note refs."""
    for ref in node.select('a[epub|type="noteref"]', namespaces={"epub": "http://www.idpf.org/2007/ops"}):
        ref.decompose()
    for q in node.find_all("q"):
        # The one <q> (North Wind ch. 25) is a rhyme quoted inside speech.
        q.insert_before("‘")
        q.insert_after("’")
        q.unwrap()
    for img in node.find_all("img"):
        if "palm" not in img.get("src", ""):
            raise CommandError(f"unexpected figure {img.get('src')!r}")
        img.replace_with(_PALM_MARK)


def _p(el: Tag) -> str:
    return f"<p>{_block(_inline(el))}</p>"


def _quote(bq: Tag, where: str) -> str:
    """A blockquote: verse or prose, then its source as '— …'."""
    inner: list[str] = []
    for el in bq.find_all(recursive=False):
        if el.name == "p":
            inner.append(_p(el))
        elif el.name == "header":  # a song's numbered part, "I", "II"
            inner.extend(_p(p) for p in el.find_all("p", recursive=False))
        elif el.name == "cite":
            inner.append(f"<p>— {_block(_inline(el))}</p>")
        elif el.name == "table":  # Lyly's dialogue, Phantastes ch. 15
            for tr in el.find_all("tr"):
                who, said = tr.find_all("td", recursive=False)
                speech = " ".join(_block(_inline(p)) for p in said.find_all("p"))
                inner.append(f"<p><em>{_block(_inline(who))}.</em> {speech}</p>")
        else:
            raise CommandError(f"{where}: unexpected <{el.name}> in a blockquote.")
    if not inner:
        raise CommandError(f"{where}: an empty blockquote.")
    return "<blockquote>" + "".join(inner) + "</blockquote>"


def _parts(container: Tag, where: str) -> list[str]:
    parts: list[str] = []
    for el in container.find_all(recursive=False):
        name = el.name
        if name in {"hgroup", "h2"}:
            continue  # the chapter's own heading — the reader shows our title
        if name == "header":  # chapter heading plus its epigraphs
            for sub in el.find_all(recursive=False):
                if sub.name == "blockquote":
                    parts.append(_quote(sub, where))
                elif sub.name not in {"h2", "hgroup"}:
                    raise CommandError(f"{where}: unexpected <{sub.name}> in the header.")
        elif name == "p":
            parts.append(_p(el))
        elif name == "blockquote":
            parts.append(_quote(el, where))
        elif name == "hr":
            parts.append("<hr>")
        elif name == "h3":
            parts.append(f"<h3>{_block(_inline(el))}</h3>")
        elif name == "section":  # a tale or poem set inside the chapter
            inner = _parts(el, where)
            if inner and inner[0].startswith("<h3>"):  # a titled poem: quote its stanzas
                inner = [inner[0], "<blockquote>" + "".join(inner[1:]) + "</blockquote>"]
            parts.extend(inner)
        else:
            raise CommandError(f"{where}: unexpected block <{name}>.")
    return parts


def _chapter(work: Work, n: int) -> tuple[str, str]:
    where = f"{work.slug}/chapter-{n}"
    soup = BeautifulSoup(_fetch(work.repo, f"chapter-{n}"), "lxml-xml")
    section = soup.find("section")
    if section is None:
        raise CommandError(f"{where}: no <section>.")
    _prepare(section)
    title_el = section.find("p", attrs={"epub:type": "title"})
    title = _block(_inline(title_el)) if title_el else ""
    body = "".join(_parts(section, where))
    if not body:
        raise CommandError(f"{where}: no text.")
    return title, body


def _stanza(div: Tag) -> str:
    return _p(div.find("p", recursive=False))


def _diary_chapters() -> list[tuple[str, str]]:
    soup = BeautifulSoup(_fetch(DIARY.repo, "poetry"), "lxml-xml")
    poem = soup.find("article", id="the-diary-of-an-old-soul")
    if poem is None:
        raise CommandError("the Diary of an Old Soul is missing from Poetry.")
    _prepare(poem)
    dedication = poem.find("section", id="the-diary-of-an-old-soul-dedication")
    signature = dedication.find("footer").find("p")
    opening = (
        "<h3>Dedication</h3>"
        + _stanza(dedication).replace("<p>", "<blockquote><p>", 1)
        + "</blockquote>"
        + _p(signature)
    )
    chapters: list[tuple[str, str]] = []
    days = 0
    for month in _MONTHS:
        sec = poem.find("section", id=f"the-diary-of-an-old-soul-{month.lower()}")
        heading = sec.find("h3").get_text(strip=True)
        if heading != month:
            raise CommandError(f"Diary: month {month!r} headed {heading!r}.")
        parts = [opening] if month == "January" else []
        for expect, div in enumerate(sec.find_all("div", recursive=False), start=1):
            day = div.find("header").get_text(strip=True)
            if day != str(expect):
                raise CommandError(f"Diary: {month} day {expect} labelled {day!r}.")
            stanza = _stanza(div)
            if stanza.count("<br>") != 6:
                raise CommandError(f"Diary: {month} {day} is not seven lines.")
            parts.append(f"<h3>{month} {day}</h3>{stanza}")
            days += 1
        chapters.append((month, "".join(parts)))
    if days != 366:
        raise CommandError(f"Diary: {days} stanzas, expected 366.")
    return chapters


def chapters(work: Work) -> list[list[str]]:
    """[title, body_html] per chapter, in reading order, fixes applied."""
    if work is DIARY:
        out = [list(c) for c in _diary_chapters()]
    else:
        out = [list(_chapter(work, n)) for n in range(1, work.chapters + 1)]
    for wrong, right, count in SOURCE_FIXES.get(work.slug, ()):
        found = sum(row[1].count(wrong) for row in out)
        if found != count:
            raise CommandError(f"{work.slug}: fix {wrong!r} expected {count}, found {found}.")
        for row in out:
            row[1] = row[1].replace(wrong, right)
    return out


class Command(BaseCommand):
    help = "Build four George MacDonald books in the dev DB; then serialize the fixtures."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", choices=list(WORKS), help="default: all four")

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        # book_sort_order reads the COMMITTED fixtures, so works new in the same
        # run would all get max+1; each later one steps past the one before.
        taken: set[int] = set()
        for slug in opts["slugs"] or list(WORKS):
            order = book_sort_order(slug)
            while order in taken:
                order += 1
            taken.add(order)
            self._build(WORKS[slug], author, order)

    def _build(self, work: Work, author: Author, sort_order: int) -> None:
        content = {
            "author": author,
            "title": work.title,
            "subtitle": work.subtitle,
            "description": work.description,
            "attribution": work.attribution,
            "publication_year": work.publication_year,
            "cover_color": work.cover_color,
            "source_url": work.source_url,
        }
        book, created = Book.objects.update_or_create(
            slug=work.slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": sort_order,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters(work), start=1):
            body = settled_chapter_body(work.slug, order, clean_fragment(body))
            wc = word_count(body)
            if wc < work.min_words:
                raise CommandError(f"{work.slug} ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:48]:48} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {work.title!r} — {book.chapter_count} chapters, {total} words")
        )

