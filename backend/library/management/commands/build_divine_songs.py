"""Build Isaac Watts's *Divine Songs for Children* (1715).

Project Gutenberg #13439 is a clean transcription, but Watts's songs are not
marked as headings — each is a ``<p>Song N.<i>Title</i></p>`` line followed by
its stanzas (``<p>`` per stanza, lines separated by ``<br>``). So this command
splits on those song markers, groups the 28 Divine Songs into two reading
chapters, and adds the two genuine Moral Songs ("The Sluggard", "Innocent
Play") as a third. It stops before this edition's CCEL *addendum* of later moral
songs (which are not Watts's original text). The verse is preserved line for
line; only where the chapters fall is editorial.

Fixture-driven like every other book: ``seed_books`` creates it (and the author,
from ``authors.json``) on the next deploy from
``fixtures/content/books/divine-songs-for-children.en.json``. This command
GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_divine_songs
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import content_root, fetch_html
from library.models import Author, Book, Chapter

SLUG = "divine-songs-for-children"
TITLE = "Divine Songs for Children"
SUBTITLE = "Attempted in easy language for the use of children"
AUTHOR_SLUG = "isaac-watts"
GUTENBERG_ID = "13439"
COVER_COLOR = covers.ink_safe("#3a6ea5")  # a young-readers blue, floored to WCAG AA

AUTHOR_STUB = {"name": "Isaac Watts", "birth_year": 1674, "death_year": 1748}

DESCRIPTION = (
    "The father of English hymnody wrote these little songs in 1715 so that the "
    "youngest children could sing the great truths of the faith in words of one "
    "or two syllables. Praise and creation, the love of God, the shortness of "
    "life, kindness and honesty and the sin of idleness — all set to simple "
    "verse a child can learn by heart. For over a century they were the most "
    "widely learned poems in the English language; “How doth the little "
    "busy bee” and “’Tis the voice of the sluggard” began "
    "here."
)

ATTRIBUTION = (
    "Public domain — Isaac Watts's Divine Songs (1715); text from Project "
    "Gutenberg (ebook 13439). The 28 Divine Songs are grouped into two reading "
    "chapters and joined by Watts's two original Moral Songs; the wording is "
    "unchanged."
)

_SONG_RE = re.compile(r"^Song\s+(\d+)\.")


def _text(p) -> str:
    return " ".join(p.get_text(" ", strip=True).split())


def _title_of(p) -> str:
    it = p.find("i")
    t = " ".join(it.get_text(" ", strip=True).split()) if it else _text(p)
    return t.rstrip(". ")


def _is_addendum(t: str) -> bool:
    tl = t.lower()
    return "addendum" in tl or "ccel" in tl or "added later" in tl


def _render(songs: list[tuple[str, list]]) -> str:
    """(title, [stanza <p> nodes]) -> chapter HTML, each song an <h3> + its verse."""
    parts: list[str] = []
    for title, stanzas in songs:
        parts.append(f"<h3>{title}</h3>")
        parts.append("".join(str(s) for s in stanzas))
    return "".join(parts)


def _chapters() -> list[tuple[str, str]]:
    ps = content_root(fetch_html(GUTENBERG_ID)).find_all("p")

    specimen = next(
        (i for i, p in enumerate(ps) if _text(p).lower().startswith("a slight specimen of moral songs")),
        None,
    )
    if specimen is None:
        raise CommandError("Moral Songs specimen header not found — the edition changed.")

    # Divine Songs: sequential "Song N." markers before the Moral specimen.
    divine: list[tuple[str, list]] = []
    i = 0
    while i < specimen:
        if _SONG_RE.match(_text(ps[i])):
            title = _title_of(ps[i])
            j = i + 1
            stanzas = []
            while j < specimen and not _SONG_RE.match(_text(ps[j])):
                stanzas.append(ps[j])
                j += 1
            divine.append((title, stanzas))
            i = j
        else:
            i += 1
    if len(divine) != 28:
        raise CommandError(f"expected 28 Divine Songs, found {len(divine)}.")

    # Moral Songs: the two genuine ones, up to the CCEL addendum note.
    addendum = next((i for i in range(specimen, len(ps)) if _is_addendum(_text(ps[i]))), len(ps))
    moral: list[tuple[str, list]] = []
    i = specimen + 1
    while i < addendum:
        p = ps[i]
        words = _text(p).split()
        is_verse = p.find("br") is not None
        if p.find("i") and not is_verse and 1 <= len(words) <= 6 and not words[0][0].isdigit():
            title = _title_of(p)
            j = i + 1
            stanzas = []
            while j < addendum and (ps[j].find("br") is not None or _text(ps[j])[:1].isdigit()):
                stanzas.append(ps[j])
                j += 1
            if stanzas:
                moral.append((title, stanzas))
            i = j
        else:
            i += 1
    if len(moral) != 2:
        raise CommandError(f"expected 2 Moral Songs, found {len(moral)}.")

    return [
        ("Divine Songs, Part One", _render(divine[:14])),
        ("Divine Songs, Part Two", _render(divine[14:])),
        ("Two Moral Songs", _render(moral)),
    ]


class Command(BaseCommand):
    help = "Build Isaac Watts's Divine Songs for Children (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

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
            if wc < 150:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:40]:40} {wc:>5} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
