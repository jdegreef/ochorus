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

The parallel to :mod:`emails.lifecycle` (``candidate_profiles`` / ``send_due`` /
``_send`` / the command) is deliberate but duplicated: the two sweeps differ on
four axes (candidate query, idempotency axis, per-profile context, static vs.
dynamic render), so a shared base isn't worth it yet. A THIRD event-triggered
email (e.g. "plan finished") is the signal to extract one — not before.
"""

from __future__ import annotations

from datetime import timedelta
from typing import NamedTuple

from django.conf import settings
from django.utils import timezone

from accounts.models import UserProfile
from library.models import Book
from reading.models import ReadingProgress, WorkKind

from .lifecycle import MIN_GAP, last_lifecycle_sent_at
from .models import (
    EmailKind,
    EmailMessage,
    EmailSubscription,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import render_series_nudge
from .sending import deliver

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


def _book_path(slug: str, language: str) -> str:
    """The reader-site path for a book, locale-prefixed and slash-terminated so it
    lands on the prerendered page (English is unprefixed)."""
    path = f"books/{slug}/"
    return path if language == "en" else f"{language}/{path}"


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
    started = {(r["book_slug"], r["language"]) for r in rows}
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
        if nxt is None or (nxt.slug, language) in started:
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
        cta_path=_book_path(next_book.slug, next_book.language),
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
        locale=next_book.language,
        lifecycle_step=FINISH_SERIES_STEP,
    )


def send_due(profile) -> EmailMessage | None:
    """Send the finish-the-series nudge this reader is due, if any.

    ``None`` when the reader is opted out / suppressed, was mailed too recently,
    has no next volume to recommend, or has no deliverable address.
    """
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants(EmailKind.LIFECYCLE, FINISH_SERIES_STEP):
        return None
    now = timezone.now()
    last_sent = last_lifecycle_sent_at(profile)
    if last_sent is not None and now - last_sent < MIN_GAP:
        return None
    pick = next_series_volume(profile)
    if pick is None:
        return None
    return _send(profile, subscription, *pick)


def candidate_profiles(cutoff):
    """Readers who finished a book on/after ``cutoff`` — the only ones who could
    have a fresh series to continue. Idempotency keeps a nudge from repeating, so
    the window only bounds the scan; it doesn't decide who has been nudged."""
    finisher_ids = (
        ReadingProgress.objects.filter(
            kind=WorkKind.BOOK, finished_at__isnull=False, finished_at__gte=cutoff
        )
        .values_list("profile_id", flat=True)
        .distinct()
    )
    return UserProfile.objects.filter(id__in=finisher_ids).order_by("id")


def lookback_cutoff():
    """The default 'finished since' cutoff from settings (days before now)."""
    days = getattr(settings, "EMAIL_SERIES_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS)
    return timezone.now() - timedelta(days=days)
