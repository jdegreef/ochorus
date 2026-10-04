"""Finish-the-series nudges — an event-triggered email, not an age-based drip.

When a reader FINISHES a book that belongs to an ordered series and the next
published volume exists in their language and they haven't opened it yet, nudge
them toward it. Unlike the onboarding drip (:mod:`emails.lifecycle`), this fires
for ANY reader on a behavioural trigger — "you just finished a volume" — not only
for new accounts in a cohort window. So it has its own sweep rather than a step
in the age-gated ``STEPS`` registry.

One email per (reader, next volume): the idempotency key carries the next
volume's slug, so each rung of a series can nudge once as the reader climbs it,
and a re-run never repeats a nudge. The nudge still shares everything else with
the drip — the ``deliver`` choke point, the 20h min-gap (so a reader never gets a
drip email and a series nudge in the same window), and the preference center
(its own "series" stream, so it can be silenced without losing onboarding tips).

The mechanical shell this shares with the other finish-a-book email (the
milestone cards) now lives in :mod:`emails.sweeps` — the candidate query
(``recent_book_finishers``), the 20h min-gap gate (``eligible_subscription``),
and the send/skip/fail tally (``run_sweep``). This module keeps only what is its
own: the pick logic (``next_series_volume``), the per-volume idempotency axis,
the dynamic title-filled render, and its consent stream.
"""

from __future__ import annotations

from datetime import timedelta
from typing import NamedTuple

from django.conf import settings
from django.utils import timezone

from library.models import Book
from reading.models import ReadingProgress, WorkKind

from . import links
from .models import (
    EmailKind,
    EmailMessage,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import email_language, render_series_nudge
from .sending import deliver
from .sweeps import eligible_subscription

#: The lifecycle_step recorded on the message (groups the metric); the per-volume
#: idempotency discriminator is ``finish_series:<next-slug>``.
FINISH_SERIES_STEP = "finish_series"

#: Default look-back: only readers who finished a series book within this many
#: days are candidates. Bounds the scan and stops a first run nudging the whole
#: back catalogue (overridable with --days / EMAIL_SERIES_LOOKBACK_DAYS).
DEFAULT_LOOKBACK_DAYS = 30


class _Finished(NamedTuple):
    """A series volume the reader finished, and when."""

    finished_at: object
    book: Book


class _Candidate(NamedTuple):
    """A recommendable (finished → next) pair, ranked by how recent the finish is."""

    finished_at: object
    finished_book: Book
    next_book: Book


def next_series_volume(profile) -> tuple[Book, Book] | None:
    """The single best ``(finished_book, next_book)`` to nudge ``profile`` toward.

    Across every series the reader has finished a volume in, find the next
    published volume after their furthest-finished one *in the same language*,
    skip any they've already opened, and return the pair for the series they
    finished most recently. ``None`` when there's nothing to recommend.
    """
    rows = list(
        ReadingProgress.objects.filter(
            profile=profile, kind=WorkKind.BOOK
        ).values("book_slug", "language", "finished_at")
    )
    # Reading progress is one row per (profile, book_slug) — a volume, whatever
    # language it was read in. So "already opened" is a slug question (skip a
    # volume read in ANY language); "finished in this edition" keeps the language
    # (it must match the Book row to read its series position).
    started_slugs = {r["book_slug"] for r in rows}
    finished = {
        (r["book_slug"], r["language"]): r["finished_at"]
        for r in rows
        if r["finished_at"] is not None
    }
    if not finished:
        return None

    # The finished books that belong to an ordered series (a numbered volume).
    series_books = Book.objects.filter(
        slug__in={slug for slug, _ in finished},
        series__isnull=False,
        series_position__isnull=False,
    ).only("slug", "language", "title", "series_id", "series_position")

    # Per (series, language): the furthest-finished volume and when it was finished.
    furthest: dict[tuple[int, str], _Finished] = {}
    for book in series_books:
        finished_at = finished.get((book.slug, book.language))
        if finished_at is None:
            continue  # a different language's edition of this slug, not finished
        key = (book.series_id, book.language)
        current = furthest.get(key)
        if current is None or book.series_position > current.book.series_position:
            furthest[key] = _Finished(finished_at, book)

    # The next published, unopened volume per series; keep the most recent finish.
    # The ">position, published, same language, lowest position" rule mirrors
    # library.serializers.series_block()'s `next` — keep the two in step.
    best: _Candidate | None = None
    for (series_id, language), found in furthest.items():
        nxt = (
            Book.objects.filter(
                series_id=series_id,
                language=language,
                is_published=True,
                series_position__gt=found.book.series_position,
            )
            .order_by("series_position")
            .only("slug", "language", "title")
            .first()
        )
        if nxt is None or nxt.slug in started_slugs:
            continue
        if best is None or found.finished_at > best.finished_at:
            best = _Candidate(found.finished_at, found.book, nxt)

    if best is None:
        return None
    return best.finished_book, best.next_book


def _send(profile, subscription, finished_book: Book, next_book: Book) -> EmailMessage | None:
    to_email = verified_email(profile)
    if not to_email:
        return None
    rendered = render_series_nudge(
        profile,
        subscription,
        finished_title=finished_book.title,
        next_title=next_book.title,
        cta_path=links.reader_path("books", next_book.slug, next_book.language),
    )
    return deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=idempotency_key(
            EmailKind.LIFECYCLE, f"{FINISH_SERIES_STEP}:{next_book.slug}", profile
        ),
        to_email=to_email,
        # The language the email is actually rendered in (the reader's), which
        # may differ from the next volume's language.
        locale=email_language(profile, subscription),
        lifecycle_step=FINISH_SERIES_STEP,
    )


def send_due(profile) -> EmailMessage | None:
    """Send the finish-the-series nudge this reader is due, if any.

    ``None`` when the reader is opted out / suppressed, was mailed too recently,
    has no next volume to recommend, or has no deliverable address.
    """
    subscription = eligible_subscription(profile, FINISH_SERIES_STEP)
    if subscription is None:
        return None
    pick = next_series_volume(profile)
    if pick is None:
        return None
    return _send(profile, subscription, *pick)


def lookback_cutoff():
    """The default 'finished since' cutoff from settings (days before now)."""
    days = getattr(settings, "EMAIL_SERIES_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS)
    return timezone.now() - timedelta(days=days)
