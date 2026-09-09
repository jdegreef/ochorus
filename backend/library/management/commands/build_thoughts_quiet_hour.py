"""Build D. L. Moody's *Thoughts for the Quiet Hour* — a daily devotional.

Moody's 1900 year-book gives a passage of Scripture and a short comment by a
devotional writer for each day of the year. Like Spurgeon's *Morning and
Evening*, it is a calendar devotional, so Ochorus stores it in the same shape as
Simpson's *Days of Heaven Upon Earth*: twelve month chapters, each day an
``<h3>January 1</h3>`` heading + verse + comment.

Why a bespoke command and not a plain ``import_gutenberg`` catalog entry: the
Gutenberg source (#37292) marks each day with ``<div class="date">January
1st.</div>`` — an ordinal date in a plain div, NOT a heading tag — so
``import_gutenberg``'s heading-splitter (and its ``group_daily_entries``, which
matches a ``January 1``-style heading *title*) can't chapter it. This command
reuses that importer's Gutenberg fetch + boilerplate strip, then splits on the
date divs itself. Like the other ``build_*`` commands it lives here, holds its
editorial content as constants, is idempotent, and takes NO ``catalog.py`` entry.
The fixture it generates is the deliverable — ``seed_books`` creates the book on
deploy from ``fixtures/content/books/thoughts-for-the-quiet-hour.en.json``.

    DJANGO_DEBUG=true uv run python manage.py build_thoughts_quiet_hour

Attributed to the existing ``dwight-l-moody`` author (as the volume's editor), so
no new author row and no migration.
"""

from __future__ import annotations

import re
from collections import defaultdict
from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment
from library.management.commands.import_gutenberg import (
    _MONTHS,
    content_root,
    fetch_html,
)
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "thoughts-for-the-quiet-hour"
TITLE = "Thoughts for the Quiet Hour"
SUBTITLE = "A Scripture and a Comment for Every Day of the Year"
AUTHOR_SLUG = "dwight-l-moody"
GUTENBERG_ID = "37292"
PUBLICATION_YEAR = 1900
COVER_COLOR = "#0f5257"  # quiet teal — twilight stillness
SORT_ORDER_FALLBACK = 67

ATTRIBUTION = (
    "Edited by D. L. Moody (Fleming H. Revell, 1900) — a passage of Scripture "
    "with a comment by a devotional writer for each day of the year. Transcribed "
    "by Project Gutenberg (#37292)."
)

DESCRIPTION = (
    "A short daily devotional gathered by D. L. Moody: for every day of the "
    "year, a passage of Scripture and a brief comment drawn from the great "
    "devotional writers Moody loved to read. A quiet, varied companion for the "
    "morning or evening hour, ranging across the whole church from the Puritans "
    "to Moody's own contemporaries."
)

# Each day is `<div class="date">June 3rd.</div>` — a month name, an ordinal
# day, a trailing period. The ordinal includes the old-style bare "d" the source
# uses for some days ("May 3d.", "February 23d." = 3rd, 23rd).
_DATE = re.compile(
    rf"^({'|'.join(_MONTHS)})\s+(\d{{1,2}})(?:st|nd|rd|th|d)?\.?$", re.I
)
_MONTH_INDEX = {name.lower(): i for i, name in enumerate(_MONTHS)}

# OCR misreads in #37292's date markers, corrected before matching. (October 3rd
# is simply absent from this edition — its marker jumps 2nd → 4th — and is left
# so rather than invented.)
_DATE_TYPOS = (("Match ", "March "),)


class Command(BaseCommand):
    help = (
        "Build D. L. Moody's Thoughts for the Quiet Hour from Gutenberg #37292 "
        "(dev DB); then serialize the fixture."
    )

    @transaction.atomic  # a mid-run abort rolls back, never a partial book
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"Author {AUTHOR_SLUG!r} is not in this database — run "
                "`manage.py seed_if_empty` first."
            ) from None

        root = content_root(fetch_html(GUTENBERG_ID))

        # Walk the body in document order, opening a new day at each date div and
        # gathering its verse (`blockquot`) and comment (top-level `<p>`s, plus
        # the occasional `<div class="poem">` verse-form comment) until the next
        # date div. A `<p>` inside the blockquot is the verse itself — rendered
        # from the blockquot — so skip it as a standalone paragraph. The trailing
        # `tnote` (Gutenberg transcriber's note) ends the readings: closing the
        # current day so the note can't ride into December 31. Front matter (title
        # page, copyright, the Scripture index) all precedes the first date div,
        # so `current is None` drops it; decorative figure divs carry no text.
        readings: dict[tuple[int, int], list[str]] = {}
        current: tuple[int, int] | None = None
        for el in root.find_all(["div", "p"]):
            classes = el.get("class", [])
            if "date" in classes:
                raw = el.get_text(" ", strip=True)
                for wrong, right in _DATE_TYPOS:
                    if raw.startswith(wrong):
                        raw = right + raw[len(wrong):]
                m = _DATE.match(raw)
                if m:
                    current = (_MONTH_INDEX[m.group(1).lower()], int(m.group(2)))
                    readings[current] = []
                else:
                    current = None
                continue
            if "tnote" in classes:  # trailing transcriber's note — end of book
                current = None
                continue
            if current is None:
                continue
            if "blockquot" in classes:  # the scripture epigraph
                verse = el.get_text(" ", strip=True)
                if verse:
                    readings[current].append(f"<p><em>{escape(verse)}</em></p>")
                continue
            if "poem" in classes:  # a verse-form comment (kept as one paragraph)
                inner = el.decode_contents().strip()
                if inner:
                    readings[current].append(f"<p>{inner}</p>")
                continue
            if el.name == "p" and not el.find_parent("div", class_="blockquot"):
                inner = el.decode_contents().strip()
                if inner:
                    readings[current].append(f"<p>{inner}</p>")

        if len(readings) < 360:
            raise CommandError(
                f"expected ~365 daily readings, found {len(readings)} — source "
                f"layout changed; inspect pg{GUTENBERG_ID} before trusting this."
            )

        by_month: dict[int, list[int]] = defaultdict(list)
        for month_i, day in readings:
            by_month[month_i].append(day)

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "publication_year": PUBLICATION_YEAR,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": f"https://www.gutenberg.org/ebooks/{GUTENBERG_ID}",
        }
        sort_order = (Book.objects.order_by("-sort_order").first().sort_order
                      or SORT_ORDER_FALLBACK - 1) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
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
        for order, month in enumerate(_MONTHS):
            days = by_month.get(order)
            if not days:
                raise CommandError(f"{SLUG}: no readings for {month}")
            entries = []
            for day in sorted(days):
                body = "".join(readings[(order, day)])
                entries.append(f"<h3>{month} {day}</h3>{body}")
            chapter_html = clean_fragment("".join(entries))
            # Gutenberg #37292 is uniformly straight-quoted; curl to the corpus
            # style (English “ ”) and bake it in so the rebuild is idempotent.
            curled, changed = convert(chapter_html, outer_guillemets=False)
            if changed:
                assert_punctuation_only(chapter_html, curled, f"{SLUG}.en[{order + 1}]")
            settled = settled_chapter_body(SLUG, order + 1, curled)
            chapter = Chapter.objects.create(
                book=book, order=order + 1, title=month, body_html=settled
            )
            total += chapter.word_count
            self.stdout.write(
                f"  ch{order + 1:2} {month:9} {len(days):2} days {chapter.word_count:>6} words"
            )

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
            )
        )
