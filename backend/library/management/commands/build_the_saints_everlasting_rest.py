"""Build Richard Baxter's *The Saints' Everlasting Rest* from Project Gutenberg #58135.

Baxter's treatise of 1650 in Benjamin Fawcett's abridgement (1759), the form it
has been read in since, as printed at Charlestown, Massachusetts, in 1811.
`import_gutenberg` reads its sixteen chapters cleanly; this command wraps its
fetch and chapter split for three things it would lose or get wrong:

* **The references.** The etext links 397 footnotes from the text, all but one
  a bare Scripture reference ("Hebrews iv, 1."), set in boxes after the
  paragraph that cites them. The importer drops both the links and the boxes.
  Here each reference is set in the text at its mark, in parentheses —
  "… through our own unbelief or negligence! (Hebrews iv, 1.)" — as Baxter's
  own editions and most since print them, rather than as 25 footnotes a
  chapter.
* **The summaries.** Each chapter opens with Fawcett's summary of its sections
  ("§ 1. The important design of the apostle …"); it is set in italics so it
  reads as the summary, not the chapter's first paragraph.
* **The back matter.** The 1811 printing closes with a note by the Trustees of
  Phillips Academy about their distribution of it, which is left out.

Chapter titles are the book's own ("the Saint's Rest", as this printing
spells it), without "CHAP. I." Fixture-driven
(`seed_books` creates it on deploy), idempotent, and no `catalog.py` entry, so
a stray `import_gutenberg` can't re-import it without its references.

    DJANGO_DEBUG=true uv run python manage.py build_the_saints_everlasting_rest
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import extract_chapters, fetch_html
from library.models import Author, Book, Chapter

SLUG = "the-saints-everlasting-rest"
TITLE = "The Saints’ Everlasting Rest"
SUBTITLE = "Abridged by Benjamin Fawcett"
AUTHOR_SLUG = "richard-baxter"
COVER_COLOR = "#4b3f5e"
EBOOK = "58135"
SOURCE_URL = f"https://www.gutenberg.org/ebooks/{EBOOK}"
PUBLICATION_YEAR = 1650

DESCRIPTION = (
    "Baxter’s great treatise on heaven, written when he thought himself dying, "
    "in Fawcett’s classic abridgement. He sets out what the saints’ rest is, its "
    "excellencies, for whom it is meant and the misery of those who lose it, "
    "then presses the duty of seeking it, and closes with his method of "
    "heavenly meditation — how to keep the heart on heaven in the middle of "
    "ordinary life."
)

ATTRIBUTION = (
    "Public domain — Richard Baxter, The Saints’ Everlasting Rest (1650), "
    "abridged by Benjamin Fawcett (1759). Text from the Charlestown, Mass., "
    "printing of 1811, Project Gutenberg ebook #58135."
)

#: The book's sections as the importer splits them, and the title each takes.
TITLES = [
    "Dedication",
    "Preface",
    "The Introduction to the Work, with Some Account of the Nature of the Saint’s Rest",
    "The Great Preparatives to the Saint’s Rest",
    "The Excellencies of the Saint’s Rest",
    "The Character of the Persons for Whom This Rest Is Designed",
    "The Misery of Those Who Lose the Saint’s Rest",
    "The Misery of Those Who, Besides Losing the Saint’s Rest, Lose the Enjoyments "
    "of Time, and Suffer the Torments of Hell",
    "The Necessity of Diligently Seeking the Saint’s Rest",
    "How to Discern Our Title to the Saint’s Rest",
    "The Duty of the People of God to Excite Others to Seek This Rest",
    "The Saint’s Rest Is Not to Be Expected on Earth",
    "The Importance of Leading a Heavenly Life upon Earth",
    "Directions How to Lead a Heavenly Life upon Earth",
    "The Nature of Heavenly Contemplation; with the Time, Place, and Temper Fittest for It",
    "What Use Heavenly Contemplation Makes of Consideration, Affections, Soliloquy, and Prayer",
    "Heavenly Contemplation Assisted by Sensible Objects, and Guarded Against a Treacherous Heart",
    "Heavenly Contemplation Exemplified, and the Whole Work Concluded",
]
#: The importer's title for each section, which must match: a re-split source
#: fails the build rather than misplacing a title.
_SOURCE_TITLES = ["dedication", "the preface", *[f"chap {n}" for n in range(1, 17)]]
_ROMAN = {r: i for i, r in enumerate(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI"], start=1)}

#: The etext's link to a note, and the note itself ("[3] Matthew ix, 12.").
_NOTE_LINK = re.compile(
    r'<span class="fnanchor"><a href="#Foot_(\d+)" id="Ref_\d+" class="pginternal">\[\d+\]</a></span>'
)
_NOTE = re.compile(
    r'<p[^>]*><a href="#Ref_(\d+)" id="Foot_\d+" class="pginternal">\[\d+\]</a>(.*?)</p>', re.S
)
_NOTE_BOX = re.compile(r'<div class="footnote">.*?</div>', re.S)
#: Stands in for a link through the importer's cleaning, which drops anchors.
_TOKEN = "⟦fn{}⟧"
_TOKEN_RE = re.compile(r"\s*⟦fn(\d+)⟧")
_SUMMARY = re.compile(r'(<p class="summary">)(.*?)(</p>)', re.S)
_BACK_MATTER = "NOTE BY THE TRUSTEES OF PHILLIPS ACADEMY"


def _key(title: str) -> str:
    title = re.sub(r"[^a-z ]", "", title.lower()).strip()
    m = re.match(r"chap ([ivx]+)\b", title)
    return f"chap {_ROMAN[m.group(1).upper()]}" if m else title


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


def _chapters(html: str) -> list[tuple[str, str]]:
    notes = {int(n): _text(body) for n, body in _NOTE.findall(html)}
    html = _NOTE_BOX.sub("", html)
    html = _NOTE_LINK.sub(lambda m: _TOKEN.format(m.group(1)), html)
    html = _SUMMARY.sub(lambda m: f"{m.group(1)}<i>{m.group(2)}</i>{m.group(3)}", html)
    chapters = extract_chapters(html)
    if chapters and _key(chapters[-1][0]) == _key(_BACK_MATTER):
        for n in _TOKEN_RE.findall(chapters[-1][1]):  # its own reference goes with it
            notes.pop(int(n), None)
        chapters = chapters[:-1]
    if [_key(t) for t, _ in chapters] != _SOURCE_TITLES:
        raise CommandError(f"sections {[t for t, _ in chapters]!r} do not match the Contents")
    out, placed = [], set()
    for title, (_, body) in zip(TITLES, chapters, strict=True):

        def reference(m, title=title):
            n = int(m.group(1))
            if n not in notes:
                raise CommandError(f"{title}: note {n} has no text")
            placed.add(n)
            return f" ({notes[n]})"

        out.append((title, _TOKEN_RE.sub(reference, body)))
    if placed != set(notes):
        raise CommandError(f"notes never referenced: {sorted(set(notes) - placed)}")
    return out


class Command(BaseCommand):
    help = "Build Baxter's The Saints' Everlasting Rest from Project Gutenberg (dev DB)."

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
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
