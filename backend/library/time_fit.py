"""'How long do you have?' — a sermon and a chapter that fit the reader's time.

The /today page's time picker asks for something to read in 5, 15, 30 or 60
minutes. The sermons shelf payload could answer the sermon half, but it is
~570 KB of cards to choose one; chapters have no list endpoint at all. So this
is a small read that answers both with two cards.

The client turns minutes into words at the reader's OWN pace (``readingPace``,
the figure every printed "N min read" uses) and sends the window, so the
server never guesses a pace and a suggestion agrees with the time printed on
it. ``seed`` is the reader's local day (or any integer): the same window shows
the same picks all day and moves on tomorrow, as Sermon of the Day does.

The chapter prefers a book the reader is in the middle of — ``reading`` carries
their local "Continue reading" places, ``slug:order`` pairs, newest first — and
otherwise starts a well-known book (the shelf's featured order, its opening
chapters), so a newcomer is not dropped into chapter 17.
"""

from __future__ import annotations

import re

from rest_framework.response import Response
from rest_framework.views import APIView

from common.params import clamp_int

from .cover_face import cover_face
from .daily_books import DATED_BOOKS
from .http_cache import PublicContentCacheMixin
from .localization import language_from_request
from .models import SERMON_CARD_DEFER, Book, Chapter, Sermon
from .serializers import EDITION_SUFFIXES, SermonListSerializer

#: The longest window anyone can ask for (a 60-minute pick at a slow pace,
#: with room): bounds the integers before they reach the database.
MAX_WORDS = 50_000
#: In-progress books considered, newest first — a "Continue reading" list's worth.
MAX_READING = 3
#: Featured books a fallback chapter may come from, and how deep into one.
KNOWN_BOOKS = 12
OPENING_CHAPTERS = 3
#: When nothing lands in the window, the longest works under its top.
NEAREST = 5

#: Front matter a book can open on — not where to start reading (English
#: titles; elsewhere the opening chapters simply all qualify).
#: (No ``\b``: Postgres reads it as a backspace — hence the explicit end.)
FRONT_MATTER = r"^\s*(the\s+)?(author.?s\s+)?(preface|foreword|introduction|contents|to the reader)([^a-z]|$)"

_PLACE = re.compile(r"^([a-z0-9-]{1,160}):(\d{1,4})$")


def parse_reading(raw: str) -> list[tuple[str, int]]:
    """``"slug:order,slug:order"`` → pairs, malformed parts dropped, capped."""
    places = []
    for part in (raw or "").split(","):
        m = _PLACE.match(part.strip())
        if m and int(m.group(2)) >= 1:
            places.append((m.group(1), int(m.group(2))))
        if len(places) == MAX_READING:
            break
    return places


def _pick(items: list, seed: int):
    return items[seed % len(items)] if items else None


def fitting_sermon(language: str, lo: int, hi: int, seed: int):
    """A published sermon of ``lo``–``hi`` words, else one of the longest under
    ``hi``; None when every sermon runs longer than the time there is."""
    shelf = Sermon.objects.filter(
        is_published=True, language=language, word_count__gt=0
    )
    pks = list(
        shelf.filter(word_count__gte=lo, word_count__lte=hi)
        .order_by("slug")
        .values_list("pk", flat=True)
    )
    if not pks:
        pks = list(
            shelf.filter(word_count__lte=hi)
            .order_by("-word_count", "slug")
            .values_list("pk", flat=True)[:NEAREST]
        )
    pk = _pick(pks, seed)
    if pk is None:
        return None
    return (
        Sermon.objects.select_related("author")
        .prefetch_related("author__translations")
        .defer(*SERMON_CARD_DEFER)
        .get(pk=pk)
    )


def _chapters():
    return Chapter.objects.select_related("book__author").only(
        "order",
        "title",
        "word_count",
        *(
            f"book__{f}"
            for f in (
                "slug",
                "language",
                "title",
                "subtitle",
                "cover_title",
                "cover_byline",
                "cover_url",
                "cover_color",
                "series_position",
            )
        ),
        "book__author__slug",
        "book__author__name",
        "book__author__birth_year",
    )


def continuing_chapter(language: str, reading: list[tuple[str, int]], hi: int):
    """The reader's place (or the chapter after it) in the newest book they are
    reading where it fits ``hi`` words — however short: carrying on beats
    starting something new."""
    for slug, order in reading:
        ch = (
            _chapters()
            .filter(
                book__slug=slug,
                book__language=language,
                book__is_published=True,
                order__in=(order, order + 1),
                word_count__gt=0,
                word_count__lte=hi,
            )
            .order_by("order")
            .first()
        )
        if ch:
            return ch
    return None


def opening_chapter(language: str, lo: int, hi: int, seed: int, exclude=()):
    """An opening chapter of a well-known book (featured order) that fits."""
    books = list(
        Book.objects.filter(is_published=True, language=language)
        .exclude(slug__in=[*DATED_BOOKS, *exclude])
        .exclude(author__is_imprint=True)
        .order_by("sort_order", "title")
        .values_list("pk", "slug")
    )
    known = [pk for pk, slug in books if not slug.endswith(EDITION_SUFFIXES)][
        :KNOWN_BOOKS
    ]
    fits = (
        _chapters()
        .filter(book_id__in=known, word_count__gte=lo, word_count__lte=hi)
        .exclude(title__iregex=FRONT_MATTER)
    )
    picks = list(
        fits.filter(order__lte=OPENING_CHAPTERS).order_by(
            "book__sort_order", "book__slug", "order"
        )
    )
    # One chapter per book, so a book with three short openers is not three
    # times as likely; the earliest of each.
    seen, first = set(), []
    for ch in picks:
        if ch.book_id not in seen:
            seen.add(ch.book_id)
            first.append(ch)
    return _pick(first, seed)


def chapter_card(ch, continuing: bool) -> dict:
    return {
        "book": cover_face(ch.book),
        "order": ch.order,
        "title": ch.title,
        "word_count": ch.word_count,
        "continuing": continuing,
    }


class TimeFitView(PublicContentCacheMixin, APIView):
    """``GET /api/library/fit/?language=&min_words=&max_words=&seed=&reading=``
    → ``{"sermon": SermonSummary | null, "chapter": FitChapter | null}``."""

    # A new response shape: key the ETag to the release as well.
    etag_tracks_release = True

    def get(self, request):
        q = request.query_params
        language = language_from_request(request)
        hi = clamp_int(q.get("max_words"), default=1000, low=1, high=MAX_WORDS)
        lo = min(clamp_int(q.get("min_words"), default=0, low=0, high=MAX_WORDS), hi)
        seed = clamp_int(q.get("seed"), default=0, low=0, high=10**9)
        reading = parse_reading(q.get("reading", ""))

        sermon = fitting_sermon(language, lo, hi, seed)
        chapter = continuing_chapter(language, reading, hi)
        continuing = chapter is not None
        if chapter is None:
            chapter = opening_chapter(
                language, lo, hi, seed, exclude=[s for s, _ in reading]
            )
        ctx = {"request": request, "sermon_topics": {}}
        return Response(
            {
                "sermon": SermonListSerializer(sermon, context=ctx).data
                if sermon
                else None,
                "chapter": chapter_card(chapter, continuing) if chapter else None,
            }
        )
