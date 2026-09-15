"""Build *The Pilgrim's Progress in Words of One Syllable* (Godolphin, ~1869).

Project Gutenberg #7088 is a clean transcription of "Mary Godolphin"'s (Lucy
Aikin's) retelling of Bunyan, but the 1869 edition carries only two authorial
divisions — PART I and PART II — so a raw import is a 27,000-word allegory in
two endless chapters. Bunyan's story is a sequence of named episodes, though
(Godolphin kept his proper names), so this command splits the two parts into
fourteen reading-sized chapters at those episode boundaries. The wording is
untouched; only where the breaks fall is editorial, as any reading edition of a
continuous allegory must decide.

This is a SEPARATE edition from the full `pilgrims-progress` (Bunyan's 1678
original) — a child-friendly retelling, filed under the same author.

Fixture-driven like every other book: `seed_books` creates it (Bunyan already
lives in authors.json) on the next deploy from
`fixtures/content/books/pilgrims-progress-words-of-one-syllable.en.json`. This
command GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_pilgrims_progress_words
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import content_root, fetch_html
from library.models import Author, Book, Chapter

SLUG = "pilgrims-progress-words-of-one-syllable"
TITLE = "The Pilgrim's Progress in Words of One Syllable"
SUBTITLE = "Bunyan's classic retold for young readers by Mary Godolphin"
AUTHOR_SLUG = "john-bunyan"
GUTENBERG_ID = "7088"
COVER_COLOR = "#99661a"  # warm amber, floored to WCAG AA for the white byline (covers.ink_safe)

# Bunyan already exists (full bio in authors.json); this stub only lets the
# build run on a dev DB that hasn't seeded authors.json yet. seed_books fills
# the real bio from authors.json on deploy.
AUTHOR_STUB = {"name": "John Bunyan", "birth_year": 1628, "death_year": 1688}

DESCRIPTION = (
    "John Bunyan's beloved allegory, retold in the 1860s by “Mary "
    "Godolphin” (Lucy Aikin) using only words of one syllable, so that the "
    "youngest readers can follow Christian on his journey from the City of "
    "Destruction to the Celestial City. The whole story is here — the "
    "Slough of Despond, the Wicket Gate, the Cross, Vanity Fair, Doubting "
    "Castle and the Delectable Mountains — in the simplest of language, "
    "with Christiana's pilgrimage in Part II. A gentle first way into the "
    "greatest of English allegories."
)

ATTRIBUTION = (
    "Public domain. Bunyan's Pilgrim's Progress retold in words of one syllable "
    "by “Mary Godolphin” (Lucy Aikin); text from Project Gutenberg "
    "(ebook 7088). Divided into chapters for reading; the wording is unchanged."
)

# Non-prose divider paragraphs the source carries between/after the parts.
_SKIP = {"end of first part.", "end of second part.", "the end", "the end."}

# Fourteen chapters, each opening at a distinctive phrase from Godolphin's text
# (searched in document order, so a phrase only ever matches at its episode).
# (chapter title, opening-phrase anchor)
CHAPTERS: list[tuple[str, str]] = [
    ("The Man with the Burden", "As I went through the wild waste"),
    ("The Slough of Despond", "just as they had come to an end of"),
    ("The Wicket Gate and the Interpreter's House", "At last there came a great man to the gate"),
    ("The Cross and the Lost Burden", "the high way which Christian"),
    ("The Hill and the House Beautiful", "they all went on till they came to"),
    ("The Valley and the Foul Fiend", "when they had got to the foot"),
    ("Vanity Fair", "the road they took brought them to a town"),
    ("Doubting Castle and Giant Despair", "on the left hand of the road was By-path Meadow"),
    ("The Delectable Mountains", "came to The Delectable Mountains"),
    ("The River and the City of Gold", "Then I slept, and dreamt once more"),
    ("Christiana Sets Out", "Once more I had a dream, and it was this"),
    ("The House of the Interpreter", "Mercy and the four boys had come to the house"),
    ("Mr. Great-heart and the Valley", "Well, my brave boys"),
    ("Home to the City", "Christiana's son James had come of age"),
]


def _paragraphs() -> list[tuple[str, str]]:
    """(inner-html, plain-text) for every content <p>, in document order."""
    root = content_root(fetch_html(GUTENBERG_ID))
    out: list[tuple[str, str]] = []
    for p in root.find_all("p"):
        text = " ".join(p.get_text(" ", strip=True).split())
        if not text or text.lower() in _SKIP:
            continue
        inner = p.decode_contents().strip()
        out.append((inner, text))
    return out


def _chapters() -> list[tuple[str, str]]:
    paras = _paragraphs()
    # Resolve each anchor to a paragraph index, strictly increasing.
    starts: list[int] = []
    search_from = 0
    for title, anchor in CHAPTERS:
        needle = anchor.lower()
        idx = next(
            (i for i in range(search_from, len(paras)) if needle in paras[i][1].lower()),
            None,
        )
        if idx is None:
            raise CommandError(f"anchor for {title!r} not found after paragraph {search_from} — the edition changed.")
        starts.append(idx)
        search_from = idx + 1
    bounds = starts + [len(paras)]
    out: list[tuple[str, str]] = []
    for (title, _), lo, hi in zip(CHAPTERS, bounds, bounds[1:]):
        body = "".join(f"<p>{paras[i][0]}</p>" for i in range(lo, hi))
        out.append((title, body))
    return out


class Command(BaseCommand):
    help = "Build Godolphin's Pilgrim's Progress in Words of One Syllable (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()
        if len(chapters) != len(CHAPTERS):
            raise CommandError(f"built {len(chapters)} chapters, expected {len(CHAPTERS)}.")

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": f"https://www.gutenberg.org/ebooks/{GUTENBERG_ID}",
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
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 400:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        if total < 24000:
            raise CommandError(f"total {total} words — well below the ~27,000 expected; aborting.")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
