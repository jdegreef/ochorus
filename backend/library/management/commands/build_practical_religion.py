"""Build J. C. Ryle's *Practical Religion* (1878) from Project Gutenberg #38162.

`import_gutenberg` reads the twenty-one papers cleanly but loses two things,
so this command wraps its fetch and chapter split and mends both:

* **Footnotes.** The etext links Ryle's 23 notes from the text ("[1]") and sets
  them together at the end under FOOTNOTES. The importer drops the links and
  imports the notes as a chapter of their own. Here each mark becomes a
  superscript letter (a, b, c … within its paper — a bare numbered `<sup>` is
  stripped corpus-wide as residue, see `corrections.strip_footnote_markers`)
  and each note is set after its own paper, as *The Saint and His Saviour*
  does.
* **The next paper's opening.** Each paper is preceded by its numeral ("II")
  as a heading of its own; the importer folds that into the paper BEFORE as a
  closing `<h3>` ("II. Strive to enter in … — Luke xiii. 24"), which is cut.

Chapter titles come from the book's Contents, title-cased. Fixture-driven
(`seed_books` creates it on deploy), idempotent, and no `catalog.py` entry, so
a stray `import_gutenberg` can't re-import it without its notes.

    DJANGO_DEBUG=true uv run python manage.py build_practical_religion
"""

from __future__ import annotations

import re
from string import ascii_lowercase

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import extract_chapters, fetch_html
from library.models import Author, Book, Chapter

SLUG = "practical-religion"
TITLE = "Practical Religion"
#: The title page's "Being Plain Papers on the Daily Duties, Experience,
#: Dangers, and Privileges of Professing Christians", shortened to fit a cover.
SUBTITLE = "Plain Papers on the Daily Duties of Professing Christians"
AUTHOR_SLUG = "j-c-ryle"
COVER_COLOR = "#3d5a4f"
EBOOK = "38162"
SOURCE_URL = f"https://www.gutenberg.org/ebooks/{EBOOK}"
PUBLICATION_YEAR = 1878

DESCRIPTION = (
    "Twenty-one plain papers on the Christian’s daily life, written as the "
    "companion to Knots Untied and Old Paths. Ryle begins with self-inquiry and "
    "effort, turns to prayer, Bible-reading, the Lord’s Supper, charity and zeal, "
    "weighs formality, the world, riches and sickness, and ends with the family "
    "of God, heaven and eternity — always pressing the reader to make religion "
    "real and personal."
)

ATTRIBUTION = (
    "Public domain — J. C. Ryle, Practical Religion (1878; preface dated "
    "November 1878). Text from Project Gutenberg ebook #38162."
)

#: The book's Contents, title-cased; the importer's titles must match these
#: (ignoring case and punctuation), so a re-split source fails the build.
TITLES = [
    "Preface",
    "Self-Inquiry",
    "Self-Exertion",
    "Reality",
    "Prayer",
    "Bible-Reading",
    "Going to the Table",
    "Charity",
    "Zeal",
    "Freedom",
    "Happiness",
    "Formality",
    "The World",
    "Riches and Poverty",
    "The Best Friend",
    "Sickness",
    "The Family of God",
    "Our Home!",
    "Heirs of God",
    "The Great Gathering",
    "The Great Separation",
    "Eternity!",
]

#: The etext's note link ("[3]") and the note it points to, which opens "3: ".
_NOTE_LINK = re.compile(r'<a href="#ft_(\d+)" class="pginternal">\[\d+\]</a>')
_NOTE_START = re.compile(r"^(\d+):\s*")
#: Stands in for a link through the importer's cleaning, which drops anchors.
_TOKEN = "⟦fn{}⟧"
_TOKEN_RE = re.compile(r"⟦fn(\d+)⟧")
#: The next paper's numeral and text, folded onto the end of this one — and,
#: after the Preface, the book's half-title.
_NEXT_PAPER = re.compile(
    r"(?:\s*(?:<br\s*/?>\s*)*<h3>\s*(?:[IVXL]+\. [^<]*|Practical Religion)\s*</h3>)+\s*$"
)
#: The etext's transcriber's note, set after the last footnote.
_TRANSCRIBER = re.compile(r"\s*<hr/>\s*<blockquote>Transcribers? note.*$", re.S | re.I)


def _key(title: str) -> str:
    return re.sub(r"[^a-z ]", "", title.lower().replace("-", " "))


def _notes(chapters: list[tuple[str, str]]) -> dict[int, str]:
    """The FOOTNOTES section as note number → note text. Each note's paragraph
    opens "3: "; a paragraph that doesn't continues the note before it."""
    notes: dict[int, list[str]] = {}
    current = None
    # Note 7 is set in a <div>, so its opening paragraph comes through as loose
    # text between blocks: take loose text as a paragraph too.
    body = _TRANSCRIBER.sub("", chapters[-1][1])
    for part in re.split(r"(<p[^>]*>.*?</p>)", body, flags=re.S):
        para = re.sub(r"^<p[^>]*>|</p>$", "", part.strip())
        if not para:
            continue
        m = _NOTE_START.match(para.strip())
        if m:
            current = int(m.group(1))
            notes[current] = [para.strip()[m.end():]]
        elif current is not None:
            notes[current].append(para.strip())
    return {n: "</p><p>".join(parts) for n, parts in notes.items()}


def _chapters(html: str) -> list[tuple[str, str]]:
    html = _NOTE_LINK.sub(lambda m: _TOKEN.format(m.group(1)), html)
    chapters = extract_chapters(html)
    if _key(chapters[-1][0]) != "footnotes":
        raise CommandError(f"last section is {chapters[-1][0]!r}, not the footnotes")
    notes = _notes(chapters)
    chapters = chapters[:-1]
    if [_key(t) for t, _ in chapters] != [_key(t) for t in TITLES]:
        raise CommandError(f"chapters {[t for t, _ in chapters]!r} do not match the Contents")
    out, placed = [], set()
    for title, (_, body) in zip(TITLES, chapters, strict=True):
        body = _NEXT_PAPER.sub("", body)
        order = [int(n) for n in _TOKEN_RE.findall(body)]
        letter = {n: ascii_lowercase[i] for i, n in enumerate(order)}
        body = _TOKEN_RE.sub(lambda m, lt=letter: f"<sup>{lt[int(m.group(1))]}</sup>", body)
        for n in order:
            if n not in notes:
                raise CommandError(f"{title}: note {n} has no text")
            body += f"<p><sup>{letter[n]}</sup> {notes[n]}</p>"
        placed.update(order)
        out.append((title, body))
    if placed != set(notes):
        raise CommandError(f"notes never referenced: {sorted(set(notes) - placed)}")
    return out


class Command(BaseCommand):
    help = "Build J. C. Ryle's Practical Religion from Project Gutenberg (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — seed the library first."
            ) from None

        chapters = _chapters(fetch_html(EBOOK))
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
            "publication_year": PUBLICATION_YEAR,
        }
        book, was_created = Book.objects.update_or_create(
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
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 200:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
