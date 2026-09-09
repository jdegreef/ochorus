"""Build F. B. Meyer's *Our Daily Walk* — a daily devotional.

Meyer's 1913 year-book gives a themed reading — a Scripture and a short
meditation (closing in his own prayer) — for each day of the year, arranged by
month. Ochorus stores it in the same shape as the other daily devotionals
(Simpson, Spurgeon, Moody): twelve month chapters, each day an
``<h3>January 1</h3>`` heading + the reading.

Sourcing: *Our Daily Walk* is not on CCEL or Project Gutenberg (Archive/
HathiTrust hold only a 1951 reprint stub), but its full public-domain text —
the work is 1913, PD by first-publication year — is transcribed cleanly on
Precept Austin as twelve per-month pages. There is no single-work importer for
that layout, so, like the other ``build_*`` devotional commands, this one lives
here, holds its editorial content and the month→URL map as constants, is
idempotent, and takes NO ``catalog.py`` entry. The fixture it generates is the
deliverable — ``seed_books`` creates the book on deploy from
``fixtures/content/books/our-daily-walk.en.json``.

    DJANGO_DEBUG=true uv run python manage.py build_our_daily_walk

Attributed to the existing ``frederick-brotherton-meyer`` author, so no new
author row and no migration.
"""

from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment
from library.management.commands.import_gutenberg import _MONTHS
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "our-daily-walk"
TITLE = "Our Daily Walk"
SUBTITLE = "Daily Readings for Every Day of the Year"
AUTHOR_SLUG = "frederick-brotherton-meyer"
PUBLICATION_YEAR = 1913
COVER_COLOR = "#3f6212"  # walking-path green
SORT_ORDER_FALLBACK = 68

ATTRIBUTION = (
    "Text of F. B. Meyer's Our Daily Walk (1913), from the transcription hosted "
    "by Precept Austin (preceptaustin.org)."
)

DESCRIPTION = (
    "F. B. Meyer's beloved daily devotional: for every day of the year, a "
    "Scripture, a short warm meditation on the Christian's daily walk, and a "
    "closing prayer. Arranged by month, from the walk of faith to the walk in "
    "the light — a steady, practical companion for the ordinary day."
)

_BASE = "https://www.preceptaustin.org/"
# The month pages. April sits at the bare slug; the rest carry a suffix, and the
# abbreviations are irregular (june/july/sept spelled long, others clipped), so
# the map is explicit rather than derived.
_MONTH_PAGES = [
    "our_daily_walk_by_f_b_meyer_-_jan",
    "our_daily_walk_by_f_b_meyer_-_feb",
    "our_daily_walk_by_f_b_meyer_-_mar",
    "our_daily_walk",  # April
    "our_daily_walk_by_f_b_meyer_-_may",
    "our_daily_walk_by_f_b_meyer_-_june",
    "our_daily_walk_by_f_b_meyer_-_july",
    "our_daily_walk_by_f_b_meyer_-_aug",
    "our_daily_walk_by_f_b_meyer_-_sept",
    "our_daily_walk_by_f_b_meyer_-_oct",
    "our_daily_walk_by_f_b_meyer_-_nov",
    "our_daily_walk_by_f_b_meyer_-_dec",
]


def _fetch(url: str) -> str:
    resp = requests.get(
        url, timeout=45, headers={"User-Agent": "ochorus-import/1.0 (+devotional PD text)"}
    )
    resp.raise_for_status()
    return resp.text


# Precept's page furniture that trails the last day's reading (the on-page
# search widgets and the empty related-resource notes). Reaching any of these
# closes the current day so the footer can't ride into the last reading. (The
# body-field <div> can't be used to bound the content instead: Precept's markup
# is malformed enough that both html.parser and lxml leave the reading <p>s as
# siblings OUTSIDE that div.)
# The first line of Precept's trailing widget block (a bare `^Search ` would risk
# truncating a day whose meditation opens "Search me, O God…").
_STOP = re.compile(
    r"^(Search for comments|Choose Book of Bible|No topics assigned|No book related)", re.I
)


def _strip_apparatus(html: str) -> str:
    """Remove Precept Austin's own study decoration from Meyer's refs.

    Precept turns each scripture citation into a link to its commentary, so the
    reference text arrives decorated: ``Php 3:13-note``, ``Heb 12:1KJV-note``,
    ``Col 3:3KJV``. Strip the ``-note`` suffix and the ``KJV`` version tag back to
    Meyer's bare reference, then close the space the suffix left before a comma or
    period (``12:1 ,`` → ``12:1,``). The ``-note`` strip is anchored to the ref
    digit before it, so Meyer's own hyphenated prose is safe — ``love-notes``
    stays, only ``21-notes`` / ``3:13-note`` go. Likewise the spacing fix only
    touches a space that follows a digit. (Meyer's own "See …" cross-references
    and his mentions of Spurgeon are prose, not apparatus, and stay.)
    """
    html = re.sub(r"(\d)\s*(?:KJV)?\s*-\s*notes?\b", r"\1", html)
    html = re.sub(r"(?<=\d)KJV\b", "", html)
    return re.sub(r"(\d) +([,.:;])", r"\1\2", html)


def _month_readings(html: str, month: str) -> dict[int, str]:
    """Parse one Precept month page → {day number: reading HTML}.

    A day opens with a "January 1" marker; the marker appears in three shapes
    across the months, so a robust boundary is EITHER an `<a name="january 1">`
    anchor OR any `<b>`/`<p>` whose whole text is exactly "January 1". (Keying on
    the anchor alone lost the days whose anchor Precept omitted — April 2,
    September 22 — while keying on a `<p>` alone lost the months that set the date
    in a bare `<b>`.) The reading is the `<p>`s after the marker until the next
    one: a bold theme, a bold scripture line or two, and the meditation. Leading
    site nav (before the first marker) and trailing search chrome (`_STOP`) are
    dropped, and a `<p>` that is only the date is skipped rather than kept.
    """
    soup = BeautifulSoup(html, "html.parser")
    marker_re = re.compile(rf"^{month}\s+(\d{{1,2}})$", re.I)

    readings: dict[int, list[str]] = {}
    current: int | None = None
    for el in soup.find_all(["a", "b", "p"]):
        if el.name in ("a", "b"):  # boundary only — never collected as content
            label = el.get("name") or el.get("id") or "" if el.name == "a" \
                else el.get_text(" ", strip=True)
            m = marker_re.fullmatch(label)
            if m:
                current = int(m.group(1))
                readings.setdefault(current, [])
            continue
        if current is None:
            continue
        text = el.get_text(" ", strip=True)
        if not text or marker_re.fullmatch(text):  # empty, or a date-only <p>
            continue
        if _STOP.match(text):  # trailing page furniture — end of the readings
            current = None
            continue
        inner = el.decode_contents().strip()
        if inner:
            readings[current].append(f"<p>{inner}</p>")
    return {day: "".join(parts) for day, parts in readings.items()}


class Command(BaseCommand):
    help = (
        "Build F. B. Meyer's Our Daily Walk from Precept Austin's month pages "
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

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "publication_year": PUBLICATION_YEAR,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": _BASE + _MONTH_PAGES[0],
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
        for order, (month, page) in enumerate(zip(_MONTHS, _MONTH_PAGES, strict=True)):
            time.sleep(0.8)  # be polite to the host
            try:
                readings = _month_readings(_fetch(_BASE + page), month)
            except requests.RequestException as exc:
                raise CommandError(f"{month}: fetch failed ({page}): {exc}") from None
            if len(readings) < 27:
                raise CommandError(
                    f"{month}: only {len(readings)} days parsed from {page} — "
                    "layout changed; inspect the page before trusting this."
                )
            entries = [
                f"<h3>{month} {day}</h3>{readings[day]}" for day in sorted(readings)
            ]
            chapter_html = _strip_apparatus(clean_fragment("".join(entries)))
            # Precept's transcription is straight-quoted; curl to the corpus style.
            curled, changed = convert(chapter_html, outer_guillemets=False)
            if changed:
                assert_punctuation_only(chapter_html, curled, f"{SLUG}.en[{order + 1}]")
            settled = settled_chapter_body(SLUG, order + 1, curled)
            chapter = Chapter.objects.create(
                book=book, order=order + 1, title=month, body_html=settled
            )
            total += chapter.word_count
            self.stdout.write(
                f"  ch{order + 1:2} {month:9} {len(readings):2} days {chapter.word_count:>6} words"
            )

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
            )
        )
