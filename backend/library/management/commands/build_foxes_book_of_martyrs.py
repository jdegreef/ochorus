"""Build *Fox's Book of Martyrs* (John Foxe; William Byron Forbush's edition).

The edition is Forbush's (John C. Winston Co., Philadelphia, 1926), a popular
one-volume abridgement in print ever since. It is NOT only Foxe: Forbush kept
Foxe's history of the martyrs from the apostles to Queen Mary's burnings and
added chapters Foxe never wrote — Wickliffe, Luther, Calvin, the Irish massacre
of 1641, the Quakers, Bunyan, Wesley, the French Protestants of 1814–1820 and
the beginnings of American foreign missions. The byline stays John Foxe (it is
his book, and how every reader knows it) and the subtitle, description and
attribution say plainly that this is Forbush's edition with additions.

Why a build command and not a `catalog.py` BookEntry: Project Gutenberg's only
"Fox's Book of Martyrs" (#22400) is a DIFFERENT book — an undated Winston
reprint of an 1830s American compilation ("compiled from Fox's Book of Martyrs,
and other authentic sources", 23 chapters, a sketch of the French Revolution,
no Forbush anywhere). The Forbush text is on CCEL, but only as its old per-
chapter files (`foxe/martyrs/files/fox1NN.htm`; CCEL's reader has no "reader
compatible version" of this work, so `import_ccel` gets nothing). Those files
open with a masthead + "CHAPTER N" + the title split across headings, and close
with next-chapter/index links — furniture `import_web.extract_page` leaves in.
So each chapter is named here with the literal opening of its first real block
(the third field of `CHAPTERS`), and the page is cut there and at the trailing nav links. No
catalog entry, so a stray importer can't re-import it in another shape.

The wording is untouched. Markup is normalised only: the body's own section
headings step down a level under the chapter title (h2→h3, h3→h4), `<menu>`
lists become paragraphs (their items already carry "1.", "2." …), `<cite>`
becomes italics, `<address>` a blockquote, and the one mid-chapter `<h1>` (a
letter's signature, "RICHARD ROTH.") a paragraph. Text repairs live in
`corrections.py`, applied through `settled_chapter_body`.

Fixture-driven like every other book: `seed_books` creates it (and John Foxe,
from ``authors.json``) on the next deploy from
``fixtures/content/books/foxes-book-of-martyrs.en.json``. This command
GENERATES that fixture's rows reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_foxes_book_of_martyrs
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.catalog import AUTHORS
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_web import fetch
from library.models import Author, Book, Chapter

SLUG = "foxes-book-of-martyrs"
TITLE = "Fox's Book of Martyrs"
SUBTITLE = "Edited by William Byron Forbush (1926), with additions"
AUTHOR_SLUG = "john-foxe"
PUBLICATION_YEAR = 1926
FILES_URL = "https://ccel.org/ccel/f/foxe/martyrs/files/"
SOURCE_URL = FILES_URL + "martyrs.html"
COVER_COLOR = covers.ink_safe("#7a1f1f")  # martyr's crimson, floored to WCAG AA

DESCRIPTION = (
    "For four centuries, after the Bible itself, few books so shaped Protestant "
    "hearts as John Foxe's record of those who died rather than deny Christ. "
    "Here are the apostles and the ten persecutions under the Roman emperors, "
    "the Waldenses and the Inquisition, Huss and Jerome of Prague, William "
    "Tyndale, and the men and women burned under Queen Mary — Rogers, Hooper, "
    "Ridley, Latimer and Cranmer among them — told with passion and "
    "tenderness. This is William Byron Forbush's 1926 edition, which abridges "
    "Foxe and adds chapters he never wrote: the lives of Wickliffe, Luther, "
    "Calvin, Bunyan and Wesley, the Irish massacre of 1641, the Quakers, the "
    "French Protestants of 1814–1820 and the beginnings of American foreign "
    "missions. It describes torture and execution plainly, as the history it is."
)

ATTRIBUTION = (
    "Public domain — John Foxe's Actes and Monuments (1563) in the edition "
    "edited by William Byron Forbush (Philadelphia: John C. Winston Co., 1926), "
    "which abridges Foxe and adds later material he did not write (the chapters "
    "on Wickliffe, Luther, Calvin, Bunyan, Wesley, the French Protestants of "
    "1814–1820 and American foreign missions, among others). Text from the "
    "Christian Classics Ethereal Library; the wording is unchanged."
)

# (chapter title, source file, literal opening of the first kept block). Titles
# are the book's own contents list; where CCEL's index truncates one (XIV) the
# chapter's own heading supplies it.
CHAPTERS: list[tuple[str, str, str]] = [
    ("History of Christian Martyrs to the First General Persecutions Under Nero",
     "fox101", "Christ our Savior, in the Gospel of St. Matthew"),
    ("The Ten Primitive Persecutions",
     "fox102", "The First Persecution, Under Nero"),
    ("Persecutions of the Christians in Persia",
     "fox103", "The Gospel having spread itself into Persia"),
    ("Papal Persecutions",
     "fox104", "Thus far our history of persecution"),
    ("An Account of the Inquisition",
     "fox105", "When the reformed religion began to diffuse"),
    ("An Account of the Persecutions in Italy, Under the Papacy",
     "fox106", "We shall now enter on an account"),
    ("An Account of the Life and Persecutions of John Wickliffe",
     "fox107", "It will not be inappropriate to devote"),
    ("An Account of the Persecutions in Bohemia Under the Papacy",
     "fox108", "The Roman pontiffs having usurped"),
    ("An Account of the Life and Persecutions of Martin Luther",
     "fox109", "This illustrious German divine"),
    ("General Persecutions in Germany",
     "fox110", "The general persecutions in Germany"),
    ("An Account of the Persecutions in the Netherlands",
     "fox111", "The light of the Gospel having successfully spread"),
    ("The Life and Story of the True Servant and Martyr of God, William Tyndale",
     "fox112", "We have now to enter into the story"),
    ("An Account of the Life of John Calvin",
     "fox113", "This reformer was born at Noyon"),
    ("An Account of the Persecutions in Great Britain and Ireland, Prior to the "
     "Reign of Queen Mary I",
     "fox114", "Gildas, the most ancient British writer"),
    ("An Account of the Persecutions in Scotland During the Reign of King Henry VIII",
     "fox115", "Like as there was no place"),
    ("Persecutions in England During the Reign of Queen Mary",
     "fox116", "The premature death of that celebrated young monarch"),
    ("Rise and Progress of the Protestant Religion in Ireland; with an Account of "
     "the Barbarous Massacre of 1641",
     "fox117", "The gloom of popery had overshadowed Ireland"),
    ("The Rise, Progress, Persecutions, and Sufferings of the Quakers",
     "fox118", "In treating of these people"),
    ("An Account of the Life and Persecutions of John Bunyan",
     "fox119", "This great Puritan was born"),
    ("An Account of the Life of John Wesley",
     "fox120", "John Wesley was born on the seventeenth of June"),
    ("Persecutions of the French Protestants in the South of France, During the "
     "Years 1814 and 1820",
     "fox121", "The persecution in this Protestant part of France"),
    ("The Beginnings of American Foreign Missions",
     "fox122", "Samuel J. Mills, when a student in Williams College"),
]

# Chapter XVI, Queen Mary's reign, is ~46,000 words — a book in itself, and
# far past a day's reading. It is split at its own section headings into eight
# parts of ~5–7k words, each opening where one martyr's account begins, so the
# reader's chapter list names who each part is about. (heading text after
# `_join_wrapped_headings`; None = the top of the chapter.)
SPLITS: dict[str, list[tuple[str, str | None]]] = {
    "fox116": [
        ("Under Queen Mary: Lady Jane Grey, John Rogers, Lawrence Saunders and John Hooper",
         None),
        ("Under Queen Mary: Rowland Taylor, Robert Farrar, Rawlins White and Others",
         "The Life and Conduct of Dr. Rowland Taylor of Hadley"),
        ("Under Queen Mary: John Bradford, Bishops Ridley and Latimer, and John Philpot",
         "Rev. John Bradford, and John Leaf, an Apprentice"),
        ("Under Queen Mary: Archbishop Cranmer",
         "Archbishop Cranmer"),
        ("Under Queen Mary: Julius Palmer, Joan Waste, Joyce Lewes and Others",
         "Hugh Laverick and John Aprice"),
        ("Under Queen Mary: Cicely Ormes, John Rough, Cuthbert Symson and Roger Holland",
         "Mrs. Cicely Ormes"),
        ("Under Queen Mary: Mrs. Prest and Others",
         "Mrs. Prest"),
        ("Under Queen Mary: Dr. Sands, the Princess Elizabeth, and God's Judgments",
         "Deliverance of Dr. Sands"),
    ],
}

_WRAPS_AFTER_PERIOD = ("and Reader of St.", "R. Wright and W.")

# A line of dialogue the source set as a heading (Julius Palmer's examination).
_DEMOTED = {'Sir Richard: "How may that be?"'}

# The trailing "Chapter N" / "Back to Index of the Book" links.
_NAV = re.compile(r'<a\s+href="(?:fox1\d\d\.htm|index\.html)"', re.I)


def _cut(html: str, starts: str) -> str:
    """The page between the first real block and the trailing nav links."""
    nav = _NAV.search(html)
    if not nav:
        raise CommandError("trailing nav links not found — the page changed.")
    html = html[: nav.start()]
    phrase = re.compile(r"\s+".join(re.escape(w) for w in starts.split()))
    m = phrase.search(html)
    if not m:
        raise CommandError(f"opening {starts!r} not found — the page changed.")
    tag = html.rfind("<", 0, m.start())  # the block (<P>/<H2>) it opens
    return html[tag:]


def _normalise(html: str) -> str:
    """Reshape the 1990s markup; never touches the words."""
    s = BeautifulSoup(html, "html.parser")
    for h in s.find_all("h3"):
        h.name = "h4"
    for h in s.find_all("h2"):
        h.name = "h3"
    for h in s.find_all("h1"):
        h.name = "p"
    for li in s.find_all("li"):
        li.name = "p"
    for m in s.find_all("menu"):
        m.unwrap()
    for c in s.find_all("cite"):
        c.name = "i"
    for a in s.find_all("address"):
        a.name = "blockquote"
    _join_wrapped_headings(s)
    return str(s)


def _heading_text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _next_block(el):
    sib = el.next_sibling
    while sib is not None and not getattr(sib, "name", None) and not str(sib).strip():
        sib = sib.next_sibling
    return sib


def _join_wrapped_headings(s) -> None:
    """Rejoin a title the source broke across headings.

    CCEL set a long section title one printed line per heading ("John Rogers,
    Vicar of St. Sepulchre's, and Reader of St." / "Paul's, London"), so the
    reader showed two headings where the book has one. A heading that ends
    without terminal punctuation (or in one of `_WRAPS_AFTER_PERIOD`) continues
    into the same-level heading after it — unless that next "heading" is a full
    sentence (ch. XXI sets "This was
    known at Nismes on the thirteenth of April, 1814." under a title), which is
    body prose and becomes a paragraph.
    """
    for h in list(s.find_all(["h3", "h4"])):
        if h.parent is None:
            continue  # already merged into its predecessor
        if _heading_text(h) in _DEMOTED:
            h.name = "p"
            continue
        while True:
            nxt = _next_block(h)
            if nxt is None or getattr(nxt, "name", None) != h.name:
                break
            # Two titles break after an abbreviation or an initial, which
            # reads as a sentence end; they are named, not inferred, so a
            # future title ending in "Dr." or "I." is never glued to the next.
            text_so_far = _heading_text(h)
            if re.search(r"[.!?:;\"”]$", text_so_far) and not text_so_far.endswith(_WRAPS_AFTER_PERIOD):
                break
            text = _heading_text(nxt)
            if text.endswith(".") and len(text.split()) > 8:
                nxt.name = "p"
                break
            h.append(" ")
            for child in list(nxt.contents):
                h.append(child)
            nxt.decompose()


def _split(body: str, parts: list[tuple[str, str | None]]) -> list[tuple[str, str]]:
    """Cut one chapter body at the named section headings."""
    s = BeautifulSoup(body, "html.parser")
    blocks = [b for b in s.contents if getattr(b, "name", None) or str(b).strip()]
    starts = {}
    for i, b in enumerate(blocks):
        if getattr(b, "name", None) in ("h3", "h4"):
            starts.setdefault(_heading_text(b), i)
    cuts = []
    for _title, heading in parts:
        if heading is None:
            cuts.append(0)
        elif heading in starts:
            cuts.append(starts[heading])
        else:
            raise CommandError(f"split heading {heading!r} not found — the page changed.")
    if cuts != sorted(cuts) or len(set(cuts)) != len(cuts):
        raise CommandError("split headings are out of order.")
    out = []
    for n, (title, _) in enumerate(parts):
        end = cuts[n + 1] if n + 1 < len(cuts) else len(blocks)
        out.append((title, "".join(str(b) for b in blocks[cuts[n]:end])))
    return out


def _chapters() -> list[tuple[str, str]]:
    out = []
    for title, name, starts in CHAPTERS:
        raw = fetch(f"{FILES_URL}{name}.htm")
        body = clean_fragment(_normalise(_cut(raw, starts)))
        body = re.sub(r"(?:\s*<hr/>)+\s*$", "", body)  # the closing rule
        if name in SPLITS:
            out.extend(_split(body, SPLITS[name]))
        else:
            out.append((title, body))
    return out


class Command(BaseCommand):
    help = "Build Fox's Book of Martyrs (Forbush ed.) from CCEL (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        stub = AUTHORS[AUTHOR_SLUG]
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG,
            defaults={
                "name": stub.name,
                "birth_year": stub.birth_year,
                "death_year": stub.death_year,
                "bio": stub.bio,
            },
        )
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, body)
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:50]:50} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
