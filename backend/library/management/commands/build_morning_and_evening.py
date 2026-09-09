"""Build Spurgeon's *Morning by Morning* and *Evening by Evening* devotionals.

Spurgeon's *Morning and Evening* is one work with two daily readings per day —
a morning reading and an evening one. It was first published, and is still best
known, as two separate year-books: *Morning by Morning* (1866) and *Evening by
Evening* (1868). Ochorus follows that split, so this one command builds BOTH
books from the single clean CCEL transcription (``spurgeon/morneve``), folding
each half's 366 daily readings into twelve month chapters — the same shape as
A. B. Simpson's *Days of Heaven Upon Earth* (see ``group_daily_entries`` in
``import_gutenberg``, which does this for a Gutenberg-sourced devotional).

Why a bespoke command and not a catalog importer: CCEL serves this work as ~730
per-reading leaves with NO daily→month folding in ``import_ccel``, and one
source yields TWO books — neither fits the single-work, one-book catalog path.
So, like ``build_prayer_anthology`` / ``build_possibilities``, it lives here,
holds its editorial content as module constants, is idempotent (re-running
replaces each book's chapters), and takes NO ``catalog.py`` entry (an
``import_ccel`` run would clobber the grouping). The fixtures it generates are
the deliverable — ``seed_books`` creates both books with their chapters on
deploy straight from ``fixtures/content/books/{morning-by-morning,
evening-by-evening}.en.json``.

    DJANGO_DEBUG=true uv run python manage.py build_morning_and_evening

Both books are attributed to the existing ``charles-h-spurgeon`` author, so no
new author row and no migration.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup, Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

AUTHOR_SLUG = "charles-h-spurgeon"
SOURCE = "https://ccel.org/ccel/spurgeon/morneve/cache/morneve.html3"
SOURCE_WORK = "https://ccel.org/ccel/spurgeon/morneve/"

ATTRIBUTION = (
    "Text of C. H. Spurgeon's Morning and Evening (1866, 1868), transcribed by "
    "the Christian Classics Ethereal Library."
)

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# Each reading section's elements carry an id prefixed `d{MM}{DD}{am|pm}`
# (e.g. `d0101am`). The month-index navigation pages have no such id, so keying
# on this pattern picks up the 732 readings and nothing else.
_KEY = re.compile(r"^d(\d{2})(\d{2})(am|pm)\b")


# (slug, title, subtitle, session key, publication_year, cover_color, description)
BOOKS = [
    (
        "morning-by-morning",
        "Morning by Morning",
        "Daily Readings for the Morning",
        "am",
        1866,
        "#b45309",  # amber — first light
        "Charles Spurgeon's morning devotional: a Scripture text and a short, "
        "warm meditation for every day of the year. The morning half of his "
        "beloved Morning and Evening, written to send the reader out into the "
        "day leaning on Christ. From the Prince of Preachers at his most "
        "pastoral and personal.",
    ),
    (
        "evening-by-evening",
        "Evening by Evening",
        "Daily Readings for the Evening",
        "pm",
        1868,
        "#1e1b4b",  # deep indigo — nightfall
        "Charles Spurgeon's evening devotional: a Scripture text and a short, "
        "searching meditation for the close of every day. The evening half of "
        "his beloved Morning and Evening, written to draw the weary heart back "
        "to Christ before rest. Tender, rich, and unmistakably Spurgeon.",
    ),
]


def _fetch(url: str) -> str:
    resp = requests.get(url, timeout=60, headers={"User-Agent": "ochorus-import/1.0"})
    resp.raise_for_status()
    return resp.text


def _reading_html(tags: list[Tag]) -> str:
    """Render one day's reading from its source elements, in document order.

    Drops the date heading (regenerated per day) and the "Go To …" cross-ref
    nav; folds the verse (``passage``) and its reference (``scripPassage``) into
    one epigraph paragraph like the sibling devotional; keeps prose and poetry
    lines as paragraphs. ``clean_fragment`` (applied by the caller over the whole
    chapter) unwraps the anchors/spans the chapter allowlist doesn't permit.
    """
    parts: list[str] = []
    pending_verse: str | None = None

    def flush_verse(ref: str | None = None) -> None:
        nonlocal pending_verse
        if pending_verse is None:
            if ref:
                parts.append(f"<p>({ref})</p>")
            return
        if ref:
            parts.append(f"<p>{pending_verse} ({ref})</p>")
        else:
            parts.append(f"<p><em>{pending_verse}</em></p>")
        pending_verse = None

    for t in tags:
        classes = t.get("class", [])
        if t.name == "h2":  # "Morning, January 1" — regenerated as <h3>
            continue
        if "crossref" in classes:  # "Go To Evening Reading" nav link
            continue
        if "passage" in classes:  # the verse text (may be <p> or <h3>)
            text = t.get_text(" ", strip=True)
            if text:
                flush_verse()  # a prior verse with no ref stands alone
                pending_verse = text
            continue
        if "scripPassage" in classes:  # the scripture reference
            flush_verse(t.get_text(" ", strip=True))
            continue
        # Prose (`normal`), poetry lines (`l`), and anything else with content.
        inner = t.decode_contents().strip()
        if not inner:
            continue
        flush_verse()  # verse with no following ref → its own italic line
        parts.append(f"<p>{inner}</p>")

    flush_verse()
    return "".join(parts)


class Command(BaseCommand):
    help = (
        "Build Spurgeon's Morning by Morning and Evening by Evening from the "
        "CCEL morneve transcription (dev DB); then serialize the fixtures."
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

        try:
            soup = BeautifulSoup(_fetch(SOURCE), "html.parser")
        except requests.RequestException as exc:
            raise CommandError(f"fetch failed: {exc}") from None

        # Bucket the block-level elements of each reading by its (month, day,
        # session) key. Only block tags — a nested <a>/<span> also carries a
        # matching id (e.g. the cross-ref link, an inline scripRef) and would be
        # re-rendered as its own stray paragraph; leave those inside their
        # parent's inner HTML instead.
        readings: dict[tuple[str, str, str], list[Tag]] = {}
        for tag in soup.find_all(["p", "h2", "h3", "h4", "blockquote"], id=True):
            m = _KEY.match(tag.get("id", ""))
            if m:
                readings.setdefault(m.groups(), []).append(tag)
        if len(readings) < 700:
            raise CommandError(
                f"expected ~732 readings, found {len(readings)} — source layout "
                "changed; inspect morneve.html3 before trusting this."
            )

        next_order = (Book.objects.order_by("-sort_order").first().sort_order or 0) + 1
        for slug, title, subtitle, session, year, color, description in BOOKS:
            self._build_one(
                author, slug, title, subtitle, session, year, color, description,
                readings, next_order,
            )
            next_order += 1

    def _build_one(
        self, author, slug, title, subtitle, session, year, color, description,
        readings, sort_order,
    ):
        content = {
            "author": author,
            "title": title,
            "subtitle": subtitle,
            "description": description,
            "publication_year": year,
            "attribution": ATTRIBUTION,
            "cover_color": color,
            "source_url": SOURCE_WORK,
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
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
        for order, mm in enumerate(f"{i:02d}" for i in range(1, 13)):
            days = sorted(k for k in readings if k[0] == mm and k[2] == session)
            if not days:
                raise CommandError(f"{slug}: no readings for month {mm}")
            month = _MONTHS[order]
            entries = []
            for _, dd, _ in days:
                body = _reading_html(readings[(mm, dd, session)])
                entries.append(f"<h3>{month} {int(dd)}</h3>{body}")
            chapter_html = clean_fragment("".join(entries))
            # The CCEL transcription is uniformly straight-quoted; curl every
            # mark to the corpus's typographic style (English “ ”, so
            # outer_guillemets=False) and bake it in so the rebuild is
            # idempotent and QuoteStyleTests sees one consistent style.
            curled, changed = convert(chapter_html, outer_guillemets=False)
            if changed:
                assert_punctuation_only(chapter_html, curled, f"{slug}.en[{order + 1}]")
            settled = settled_chapter_body(slug, order + 1, curled)
            Chapter.objects.create(
                book=book, order=order + 1, title=month, body_html=settled
            )
            wc = word_count(settled)
            total += wc
            self.stdout.write(f"  {slug} ch{order + 1:2} {month:9} {len(days):2} days {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {title!r} — {book.chapter_count} chapters, {total} words"
            )
        )
