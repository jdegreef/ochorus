"""Build *The Treatises of Cyprian* from CCEL's Ante-Nicene Fathers, Vol. 5.

Cyprian's treatises sit inside the ANF volume `schaff/anf05` under the section
stem `iv.v`; a plain `import_ccel` with `part="iv.v"` over-splits into 205
per-paragraph leaves, and `group_parts=True` fixes that (13 chapters, one per
treatise) but keeps two things we don't want: the ANF editor's **"Elucidations"**
(scholarly notes, not Cyprian), and a redundant `<p>Treatise N.</p><p>Title.</p>`
restated at the head of every chapter (the reader already shows the title). So
this command reuses `import_ccel`'s crawl (`toc_parts` + `extract_body`), drops
Elucidations, and strips the redundant heading — leaving the ANF "Argument"
summary that genuinely opens each treatise.

Translation: the public-domain Ante-Nicene Fathers (Robert Ernest Wallis, 1868).
Fixture-driven; `seed_books` creates the book (and the author, from
`authors.json`) on the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_cyprian_treatises
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, clean_title, is_front_matter, word_count
from library.management.commands.import_ccel import (
    extract_body,
    fetch,
    toc_parts,
)
from library.models import Author, Book, Chapter

SLUG = "treatises-of-cyprian"
TITLE = "The Treatises of Cyprian"
SUBTITLE = "On the Lord's Prayer, the Mortality, Works and Alms, and More"
AUTHOR_SLUG = "cyprian-of-carthage"
SOURCE_REF = "schaff/anf05"
PART = "iv.v"
COVER_COLOR = "#7d2b34"  # deep martyr's red — house-style cover ground

AUTHOR_STUB = {"name": "Cyprian of Carthage", "birth_year": 200, "death_year": 258}

DESCRIPTION = (
    "The pastoral writings of the bishop-martyr of Carthage. Cyprian led the "
    "North African church through plague and persecution in the third century, "
    "and these treatises show why he was so loved: a tender exposition of the "
    "Lord's Prayer, a steadying word on facing death in <em>On the Mortality</em>, "
    "a plea for generosity in <em>On Works and Alms</em>, and searching counsel on "
    "unity, patience, and envy. Plain, warm, and bracing — the voice of a shepherd "
    "who would soon give his own life for the flock."
)

ATTRIBUTION = (
    "Public domain — translated by Robert Ernest Wallis for the Ante-Nicene "
    "Fathers (Vol. 5, 1868), from the Christian Classics Ethereal Library. The "
    "editor's appended “Elucidations” are omitted."
)

# The redundant head each ANF treatise opens with: "<p>Treatise IV.</p>
# <p>On the Lord's Prayer.</p>", restating what the chapter title already shows.
# The "Argument" summary that follows is kept.
_HEAD_RE = re.compile(r"\s*<p>\s*Treatise\s+[IVXLC]+\.\s*</p>\s*<p>[^<]+</p>", re.I)

# The ANF gives Treatise VI a sentence-long descriptive title; the reader shows
# the chapter name, so shorten it to the work's short name.
_TITLE_OVERRIDES = {
    "On the Vanity of Idols: Showing that the Idols are Not Gods, and that God is "
    "One, and that Through Christ Salvation is Given to Believers": "On the Vanity of Idols",
}


def _chapters() -> list[tuple[str, str]]:
    parts = toc_parts(SOURCE_REF, PART)
    if not parts:
        raise CommandError("no sections found in the ANF05 TOC under iv.v")
    out: list[tuple[str, str]] = []
    for part_title, leaves in parts:
        if is_front_matter(part_title) or "elucidation" in part_title.lower():
            continue
        pieces: list[str] = []
        for url, leaf_title in leaves:
            if is_front_matter(leaf_title):
                continue
            body = extract_body(fetch(url), clean_title(leaf_title), TITLE, True)
            if body:
                pieces.append(f"<h3>{clean_title(leaf_title)}</h3>{body}" if len(leaves) > 1 else body)
        if not pieces:
            continue
        body = _HEAD_RE.sub("", "".join(pieces), count=1).lstrip()
        title = clean_title(part_title)
        out.append((_TITLE_OVERRIDES.get(title, title), body))
    return out


class Command(BaseCommand):
    help = "Build The Treatises of Cyprian from CCEL ANF05 (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()
        if len(chapters) < 10:
            raise CommandError(f"only {len(chapters)} treatises found — expected 12; aborting.")

        content = {
            "author": author, "title": TITLE, "subtitle": SUBTITLE,
            "description": DESCRIPTION, "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR, "source_url": "https://ccel.org/ccel/schaff/anf05",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=SLUG, language="en", defaults=content,
            create_defaults={**content, "source_type": Book.SourceType.PUBLIC_DOMAIN,
                             "is_published": True, "sort_order": next_order},
        )
        book.chapters.all().delete()

        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 500:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:46]:46} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
