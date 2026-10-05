"""Build G. K. Chesterton's *Heretics* (1905), *Orthodoxy* (1908), *St. Francis
of Assisi* (1923) and *The Everlasting Man* (1925).

Three texts come from Standard Ebooks, whose editions are proofread against page
scans and whose own contributions are dedicated to the public domain (CC0). The
source files are each ebook's ``src/epub/text/*.xhtml``, read from the
Standard Ebooks repositories on GitHub (standardebooks.org and gutenberg.org
refuse this environment's egress; the GitHub mirror is the same text).
Standard Ebooks has no *St. Francis*; it comes from Project Gutenberg's HTML
edition instead, read from the GITenberg mirror (see below).

* *Heretics* — Standard Ebooks' edition follows Project Gutenberg #470 and a
  scan of the 1905 printing. The twenty chapters are the chapters.

* *Orthodoxy* — Standard Ebooks' edition follows Project Gutenberg #16769 and
  the 1908 scan; it keeps the italics that the older plain-text etext (#130)
  lost. Chesterton's Preface is the first chapter, then his nine chapters.
* *The Everlasting Man* — Standard Ebooks' edition follows Project Gutenberg
  #65688 (released 2021, when the 1925 text entered the US public domain) and
  the 1925 scan. The Prefatory Note, the Introduction, the two Parts' fourteen
  chapters, the Conclusion and the two Appendices are the chapters; each Part's
  title is set as a heading at the head of its first chapter.
* *St. Francis of Assisi* — Project Gutenberg #63084 (released 2020, after the
  1923 text entered the US public domain), transcribed by Distributed
  Proofreaders from a Hodder and Stoughton printing. Its ten chapters are the
  chapters; the spelling is the printing's own (to-day, civilisation), and
  its straight quotation marks are set curly. The page-number anchors and the
  publisher's advertisements at the back are left out.

Only the author's text is taken: Standard Ebooks' title page, imprint,
colophon and uncopyright pages are left out, as is the dedication (and the
closing "The End"). Their
typography is kept (curly quotes, em dashes); the invisible word-joiners and
hair spaces it uses for line-breaking are removed, and no-break spaces become
plain spaces, as across the library.

Fixture-driven like every other book: ``seed_books`` creates the books (and
the author, from ``authors.json``) on the next deploy from
``fixtures/content/books/<slug>.en.json``. This command GENERATES those
fixtures reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_chesterton [heretics|orthodoxy|st-francis-of-assisi|the-everlasting-man]
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

AUTHOR_SLUG = "g-k-chesterton"
AUTHOR_STUB = {"name": "G. K. Chesterton", "birth_year": 1874, "death_year": 1936}

SE_RAW = "https://raw.githubusercontent.com/standardebooks/{repo}/master/src/epub/text/{name}.xhtml"
# Project Gutenberg's HTML edition, as the GITenberg mirror carries it.
PG_RAW = "https://raw.githubusercontent.com/GITenberg/{repo}/master/{name}"


@dataclass(frozen=True)
class Part:
    """A chapter file, and the title the reader shows for it."""

    name: str  # the xhtml file's stem
    title: str
    heading: str = ""  # a Part title set at the head of this chapter
    min_words: int = 1000


@dataclass(frozen=True)
class Work:
    slug: str
    title: str
    repo: str
    publication_year: int
    cover_color: str
    source_url: str
    description: str
    attribution: str
    parts: tuple[Part, ...]
    # Set for a Project Gutenberg HTML edition (GITenberg repo, file path);
    # `repo` then names the GITenberg repo and each Part's `name` is unused.
    pg_html: str = ""


HERETICS = Work(
    slug="heretics",
    title="Heretics",
    repo="g-k-chesterton_heretics",
    publication_year=1905,
    cover_color=covers.ink_safe("#4a3a64"),
    source_url="https://standardebooks.org/ebooks/g-k-chesterton/heretics",
    description=(
        "The modern world, Chesterton complains, has stopped asking whether a "
        "man's view of the universe is true; it is thought bad manners to have "
        "one at all. In these twenty essays he takes the celebrated thinkers of "
        "his day one by one, Kipling, Shaw, Wells, Moore, Whistler and the rest, "
        "and asks of each the question it is no longer polite to ask: what does "
        "he believe, and is it right? Witty, generous to his opponents and "
        "relentless with their ideas, the book argues that a man who refuses to "
        "have a creed has not escaped dogma but only hidden it, and it is the "
        "challenge to which Orthodoxy, three years later, gave his answer."
    ),
    attribution=(
        "Public domain — G. K. Chesterton's Heretics (1905). Text from the "
        "Standard Ebooks edition (CC0), which follows Project Gutenberg ebook "
        "470 checked against a scan of the 1905 printing, with lightly "
        "modernised spelling. All twenty chapters are complete."
    ),
    parts=(
        Part("chapter-1", "Introductory Remarks on the Importance of Orthodoxy"),
        Part("chapter-2", "On the Negative Spirit"),
        Part("chapter-3", "On Mr. Rudyard Kipling and Making the World Small"),
        Part("chapter-4", "Mr. Bernard Shaw"),
        Part("chapter-5", "Mr. H. G. Wells and the Giants"),
        Part("chapter-6", "Christmas and the Aesthetes"),
        Part("chapter-7", "Omar and the Sacred Vine"),
        Part("chapter-8", "The Mildness of the Yellow Press"),
        Part("chapter-9", "The Moods of Mr. George Moore"),
        Part("chapter-10", "On Sandals and Simplicity"),
        Part("chapter-11", "Science and the Savages"),
        Part("chapter-12", "Paganism and Mr. Lowes Dickinson"),
        Part("chapter-13", "Celts and Celtophiles"),
        Part(
            "chapter-14",
            "On Certain Modern Writers and the Institution of the Family",
        ),
        Part("chapter-15", "On Smart Novelists and the Smart Set"),
        Part("chapter-16", "On Mr. McCabe and a Divine Frivolity"),
        Part("chapter-17", "On the Wit of Whistler"),
        Part("chapter-18", "The Fallacy of the Young Nation"),
        Part("chapter-19", "Slum Novelists and the Slums"),
        Part("chapter-20", "Concluding Remarks on the Importance of Orthodoxy"),
    ),
)

ORTHODOXY = Work(
    slug="orthodoxy",
    title="Orthodoxy",
    repo="g-k-chesterton_orthodoxy",
    publication_year=1908,
    cover_color=covers.ink_safe("#7a2e2a"),
    source_url="https://standardebooks.org/ebooks/g-k-chesterton/orthodoxy",
    description=(
        "When critics of Heretics complained that Chesterton had attacked every "
        "modern philosophy without offering one of his own, he answered with this "
        "book: not an argument for whether the Christian faith can be believed, "
        "but an account of how he personally came to believe it. He tells it as "
        "the story of a man who set out to discover a new truth and found that he "
        "had discovered orthodoxy. With the madman who has lost everything except "
        "his reason, the ethics of elfland learned in the nursery, and the "
        "paradoxes that make the Church a thrilling romance, he shows the old "
        "creed to be the one answer large enough for the riddle of the world."
    ),
    attribution=(
        "Public domain — G. K. Chesterton's Orthodoxy (1908). Text from the "
        "Standard Ebooks edition (CC0), which follows Project Gutenberg ebook "
        "16769 checked against a scan of the 1908 printing, with lightly "
        "modernised spelling. The Preface and the nine chapters are complete."
    ),
    parts=(
        Part("preface", "Preface", min_words=150),
        Part("chapter-1", "Introduction in Defence of Everything Else"),
        Part("chapter-2", "The Maniac"),
        Part("chapter-3", "The Suicide of Thought"),
        Part("chapter-4", "The Ethics of Elfland"),
        Part("chapter-5", "The Flag of the World"),
        Part("chapter-6", "The Paradoxes of Christianity"),
        Part("chapter-7", "The Eternal Revolution"),
        Part("chapter-8", "The Romance of Orthodoxy"),
        Part("chapter-9", "Authority and the Adventurer"),
    ),
)

EVERLASTING_MAN = Work(
    slug="the-everlasting-man",
    title="The Everlasting Man",
    repo="g-k-chesterton_the-everlasting-man",
    publication_year=1925,
    cover_color=covers.ink_safe("#2e4a5a"),
    source_url="https://standardebooks.org/ebooks/g-k-chesterton/the-everlasting-man",
    description=(
        "There are two ways of getting home, Chesterton says, and one of them is "
        "to stay there; the other is to walk round the whole world until we come "
        "back to the same place. This is that second journey. Answering the "
        "popular histories that made man a mere animal and Christ a mere teacher, "
        "he walks the reader through the story of mankind, from the pictures in "
        "the prehistoric cave through the myths, philosophies and empires of the "
        "ancient world, to the child born in a cave at Bethlehem, and shows that "
        "seen freshly, from outside, both man and the Church are as strange and "
        "as unique as the creed has always said."
    ),
    attribution=(
        "Public domain — G. K. Chesterton's The Everlasting Man (1925). Text from "
        "the Standard Ebooks edition (CC0), which follows Project Gutenberg ebook "
        "65688 checked against a scan of the 1925 printing, with lightly "
        "modernised spelling. Complete: the Prefatory Note, the Introduction, both "
        "Parts, the Conclusion and the two Appendices."
    ),
    parts=(
        Part("preface", "Prefatory Note", min_words=150),
        Part("introduction", "Introduction: The Plan of This Book"),
        Part(
            "chapter-1-1",
            "The Man in the Cave",
            heading="Part I: On the Creature Called Man",
        ),
        Part("chapter-1-2", "Professors and Prehistoric Men"),
        Part("chapter-1-3", "The Antiquity of Civilisation"),
        Part("chapter-1-4", "God and Comparative Religion"),
        Part("chapter-1-5", "Man and Mythologies"),
        Part("chapter-1-6", "The Demons and the Philosophers"),
        Part("chapter-1-7", "The War of the Gods and Demons"),
        Part("chapter-1-8", "The End of the World"),
        Part(
            "chapter-2-1",
            "The God in the Cave",
            heading="Part II: On the Man Called Christ",
        ),
        Part("chapter-2-2", "The Riddles of the Gospel"),
        Part("chapter-2-3", "The Strangest Story in the World"),
        Part("chapter-2-4", "The Witness of the Heretics"),
        Part("chapter-2-5", "The Escape from Paganism"),
        Part("chapter-2-6", "The Five Deaths of the Faith"),
        Part("conclusion", "Conclusion: The Summary of This Book"),
        Part("appendix-1", "Appendix I: On Prehistoric Man", min_words=300),
        Part("appendix-2", "Appendix II: On Authority and Accuracy", min_words=300),
    ),
)

ST_FRANCIS = Work(
    slug="st-francis-of-assisi",
    title="St. Francis of Assisi",
    repo="St-Francis-of-Assisi_63084",
    pg_html="63084-h/63084-h.htm",
    publication_year=1923,
    cover_color=covers.ink_safe("#5e4630"),
    source_url="https://www.gutenberg.org/ebooks/63084",
    description=(
        "A life of St. Francis, Chesterton says, can be written as if he were "
        "only a lover of nature and a friend of the birds, or only a saint of "
        "the stained-glass window; he sets out to do something harder, and to "
        "show a modern reader why the man did what he did. Beginning with the "
        "dark world Francis was born into, he follows the young soldier of "
        "Assisi through his conversion, the rebuilding of the ruined church, "
        "the leper he ran to embrace and the joyful poverty of the friars, to "
        "the stigmata and his death, and finds the secret of it all in one "
        "thing: that Francis was a lover, a lover of God and of men."
    ),
    attribution=(
        "Public domain — G. K. Chesterton's St. Francis of Assisi (1923). Text "
        "from Project Gutenberg ebook 63084, transcribed by Distributed "
        "Proofreaders from a Hodder and Stoughton printing, in its original "
        "spelling. All ten chapters are complete."
    ),
    parts=(
        Part("", "The Problem of St. Francis"),
        Part("", "The World St. Francis Found"),
        Part("", "Francis the Fighter"),
        Part("", "Francis the Builder"),
        Part("", "Le Jongleur de Dieu"),
        Part("", "The Little Poor Man"),
        Part("", "The Three Orders"),
        Part("", "The Mirror of Christ"),
        Part("", "Miracles and Death"),
        Part("", "The Testament of St. Francis"),
    ),
)

WORKS = {w.slug: w for w in (HERETICS, ORTHODOXY, ST_FRANCIS, EVERLASTING_MAN)}

# Printer's slips the Standard Ebooks text keeps from its scan, each read
# correctly by the independent Project Gutenberg transcription (#130). A
# word-by-word comparison of the two Orthodoxy texts found these three and
# nothing else beyond spelling modernisation. Each must match exactly once.
FIXES: dict[str, tuple[tuple[str, str], ...]] = {
    "orthodoxy": (
        ("the mystic and the arbitary.", "the mystic and the arbitrary."),
        ("love children, arbitarily,", "love children, arbitrarily,"),
        ("nonresistance of the monastries", "nonresistance of the monasteries"),
    ),
}

# Standard Ebooks' line-breaking aids, invisible on the page: word joiners glue
# an em dash to the word before it, hair spaces part adjacent quote marks
# (‘cow’ ”). Neither is text, and nothing else in the library carries them.
_INVISIBLE = str.maketrans({"\u2060": None, "\u200a": None, "\xa0": " "})
_WS = re.compile(r"\s+")
# Inline elements that carry only semantics (abbr, a title's epub:type span,
# a <time>) — their words stay, the element goes.
_UNWRAP = {"abbr", "span", "time", "a"}
_RENAME = {"i": "em", "b": "strong"}


def _fetch(repo: str, name: str, template: str = SE_RAW) -> str:
    url = template.format(repo=repo, name=name)
    for _attempt in range(4):
        try:
            resp = requests.get(url, timeout=60)
        except requests.RequestException:
            continue
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            return resp.text
    raise CommandError(f"could not fetch {url}")


def _inline(node: Tag) -> str:
    """One block's content as reader HTML: semantic wrappers unwrapped, i→em."""
    out: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            out.append(_escape(str(child)))
        elif isinstance(child, Tag):
            name = child.name
            if name == "br":
                out.append("<br>")
            elif name in _UNWRAP:
                out.append(_inline(child))
            elif name in _RENAME or name in {"em", "strong", "sup"}:
                tag = _RENAME.get(name, name)
                out.append(f"<{tag}>{_inline(child)}</{tag}>")
            else:
                raise CommandError(f"unexpected inline <{name}> in {node.name}")
    return "".join(out)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _block(text: str) -> str:
    """Collapse source indentation; a verse line break eats its whitespace."""
    text = _WS.sub(" ", text.translate(_INVISIBLE))
    return re.sub(r"\s*<br>\s*", "<br>", text).strip()


def _body(xhtml: str, where: str) -> str:
    soup = BeautifulSoup(xhtml, "lxml-xml")
    section = soup.find("section")
    if section is None:
        raise CommandError(f"{where}: no <section>.")
    parts: list[str] = []
    for el in section.find_all(recursive=False):
        if el.name in {"hgroup", "header", "h2", "h3"}:
            continue  # the chapter's own heading — the reader shows our title
        if el.name == "p":
            if el.get_text(strip=True) == "The End":
                continue  # Standard Ebooks' closing line, not the author's
            parts.append(f"<p>{_block(_inline(el))}</p>")
        elif el.name == "footer":  # the Preface's signature
            parts.extend(
                f"<p>{_block(_inline(p))}</p>"
                for p in el.find_all("p", recursive=False)
            )
        elif el.name == "blockquote":
            inner = []
            for p in el.find_all("p", recursive=False):
                inner.append(f"<p>{_block(_inline(p))}</p>")
            if not inner:
                raise CommandError(f"{where}: an empty blockquote.")
            parts.append("<blockquote>" + "".join(inner) + "</blockquote>")
        else:
            raise CommandError(f"{where}: unexpected block <{el.name}>.")
    if not parts:
        raise CommandError(f"{where}: no text.")
    return "".join(parts)


def _pg_bodies(html: str, where: str) -> list[str]:
    """Each chapter's body from a Project Gutenberg HTML edition.

    A chapter opens at its ``div.chapter`` (the heading, which the reader
    replaces with our title) and runs to the next one; the publisher's
    advertisements (``div.books``) end the book. The page-number anchors are
    the edition's apparatus, not text.
    """
    soup = BeautifulSoup(html, "lxml")
    for span in soup.select("span.pagenum"):
        span.decompose()
    bodies: list[list[str]] = []
    for el in soup.body.find_all(recursive=False):
        classes = el.get("class") or []
        if el.name == "div" and "chapter" in classes:
            bodies.append([])
        elif el.name == "div" and "books" in classes:
            break
        elif not bodies:
            continue  # front matter and contents
        elif el.name == "p":
            bodies[-1].append(f"<p>{_block(_inline(el))}</p>")
        elif el.name == "div" and "poetry-container" in classes:
            lines = [_block(_inline(v)) for v in el.select("div.verse")]
            if not lines:
                raise CommandError(f"{where}: an empty verse block.")
            bodies[-1].append(
                "<blockquote><p>" + "<br>".join(lines) + "</p></blockquote>"
            )
        else:
            raise CommandError(f"{where}: unexpected block <{el.name} {classes}>.")
    return ["".join(b) for b in bodies]


def chapters(work: Work) -> list[tuple[str, str, int]]:
    """(title, body_html, min_words) per chapter, in reading order."""
    out = []
    if work.pg_html:
        bodies = _pg_bodies(_fetch(work.repo, work.pg_html, PG_RAW), work.slug)
        if len(bodies) != len(work.parts):
            raise CommandError(
                f"{work.slug}: {len(bodies)} chapters in the edition, "
                f"{len(work.parts)} expected — the edition changed."
            )
    else:
        bodies = [
            _body(_fetch(work.repo, part.name), f"{work.slug}/{part.name}")
            for part in work.parts
        ]
    for n, (part, body) in enumerate(zip(work.parts, bodies, strict=True), 1):
        if work.pg_html:
            # Gutenberg's straight quotes, set curly like the Standard Ebooks
            # texts beside it; only the marks may move.
            curled, _ = convert(body, outer_guillemets=False)
            assert_punctuation_only(body, curled, f"{work.slug}[{n}]")
            body = curled
        if part.heading:
            body = f"<h2>{_escape(part.heading)}</h2>" + body
        out.append([part.title, body, part.min_words])
    for wrong, right in FIXES.get(work.slug, ()):
        hits = [row for row in out if wrong in row[1]]
        if len(hits) != 1 or hits[0][1].count(wrong) != 1:
            raise CommandError(
                f"{work.slug}: fix {wrong!r} should match once — the edition changed."
            )
        hits[0][1] = hits[0][1].replace(wrong, right)
    return [tuple(row) for row in out]


class Command(BaseCommand):
    help = "Build Chesterton's books in the dev DB; then serialize the fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "slugs", nargs="*", choices=list(WORKS), help="default: all"
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG, defaults=AUTHOR_STUB
        )
        if created_author:
            self.stdout.write(
                f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)"
            )

        # book_sort_order reads the COMMITTED fixtures, so two works new in the
        # same run would both get max+1; the second one steps past the first.
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
            "subtitle": "",
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
        for order, (title, body, min_words) in enumerate(chapters(work), start=1):
            body = settled_chapter_body(work.slug, order, clean_fragment(body))
            wc = word_count(body)
            if wc < min_words:
                raise CommandError(
                    f"{work.slug} ch {order} ({title!r}): only {wc} words — aborted."
                )
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:48]:48} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {work.title!r} — {book.chapter_count} chapters, {total} words"
            )
        )
