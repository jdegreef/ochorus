"""The reverse scripture index — which passages in the library cite a verse.

Search has answered this since citations were indexed: type "Romans 8:28" and
you get the chapters that treat it. What it has never had is a URL. This module
is that same question given a public address, and it deliberately re-exposes
the SELECTOR search already uses rather than ranking afresh — one definition of
"which chapters cite this", used by both.

ENGLISH ONLY, and not as an oversight. `extract_citations` validates against
pythonbible's English book names, so "Juan 3:16" and "Yohana 3:16" parse as
nothing: measured over the fixture, Spanish yields 43 citations across 270
chapters, Swahili 6, Luganda 13 — all residual English strings, not coverage.
Publishing localized verse pages off that would advertise near-empty pages in
the very locales the multilingual moat depends on. Teaching the extractor
target-language book names is its own project; until then these pages are
English and say so by existing only there.

THE FLOOR IS THE POINT. A verse cited once yields a page with one excerpt,
which is a thin page, and thousands of them are the doorway pattern that gets a
domain classified rather than ranked. `qualifying_*` is the single place that
decides what deserves a URL — the API, the prerender entry generator and the
sitemap all read it, so the three can never disagree about which pages exist.
"""

from __future__ import annotations

import re
from functools import lru_cache

import pythonbible as bible

from .models import Chapter, ChapterCitation
from .scripture import VERSION, reference_verse_ids

#: A page needs this many DISTINCT citing chapters to exist. Measured over the
#: English corpus (9,318 citations across 904 of 1,264 chapters): at 3+, 609
#: Bible chapters and 1,124 verses qualify; the verse count collapses to 384 at
#: 5+ while the chapter count barely moves (464). That asymmetry is the whole
#: argument for the two different floors below — a Bible-chapter page aggregates
#: many verses and stays substantial under a strict floor, a verse page does not.
CHAPTER_FLOOR = 3
VERSE_FLOOR = 5

#: How many citing passages one page lists. Past this the page stops being a
#: reading list and becomes a wall; the rest stay reachable through search.
MAX_PASSAGES = 40


def book_slug(book: bible.Book) -> str:
    """``Book.ROMANS`` → ``"romans"``, ``1 Corinthians`` → ``"1-corinthians"``.

    The URL is the readable name, not the USFM code: people search "romans 8",
    never "ROM 8", and the slug is the one part of this page a reader sees
    before they click it. Verified collision-free across all 72 books.
    """
    return re.sub(r"[^a-z0-9]+", "-", book.title.lower()).strip("-")


@lru_cache(maxsize=1)
def _books_by_slug() -> dict[str, bible.Book]:
    return {book_slug(b): b for b in bible.Book}


def book_from_slug(slug: str) -> bible.Book | None:
    return _books_by_slug().get(slug.lower())


def verse_ids_for(book: bible.Book, chapter: int, verse: int | None) -> list[int]:
    """The ASV verse ids a page covers — one verse, or a whole Bible chapter.

    Empty when the reference doesn't exist (Romans 99, or an apocryphal book
    the bundled ASV doesn't carry), which is how the views tell a real page
    from an invented URL.
    """
    ref = bible.NormalizedReference(
        book=book,
        start_chapter=chapter,
        start_verse=verse or 1,
        end_chapter=chapter,
        end_verse=verse if verse is not None else _last_verse(book, chapter),
        end_book=book,
    )
    try:
        return list(bible.convert_reference_to_verse_ids(ref))
    except Exception:
        return []


def _last_verse(book: bible.Book, chapter: int) -> int:
    try:
        return bible.get_number_of_verses(book, chapter)
    except Exception:
        return 1


def verse_text(verse_id: int) -> str:
    """ASV text for one verse id, or "" — bundled, so this needs no network."""
    try:
        return bible.get_verse_text(verse_id, version=VERSION) or ""
    except Exception:
        return ""


def reference_label(book: bible.Book, chapter: int, verse: int | None) -> str:
    return f"{book.title} {chapter}" + (f":{verse}" if verse is not None else "")


def citing_rows(verse_ids, chapters=None):
    """Citation rows overlapping ``verse_ids``, best row per chapter.

    THE SELECTOR, lifted out of ``search._scripture_chapter_hits`` so the page
    and the search result rank the same way — narrowest span first (the most
    specific treatment of the passage), then most-repeated. Both callers pass a
    pre-filtered chapter queryset rather than letting this widen the scope.

    The verse-id range filter is only a PREFILTER: a span brackets everything
    numerically between its ends, so rows are re-checked against the exact id
    set before ranking, the same contract search relies on.
    """
    if not verse_ids:
        return []
    target = frozenset(verse_ids)
    rows = ChapterCitation.objects.filter(
        start_verse_id__lte=max(target),
        end_verse_id__gte=min(target),
    )
    if chapters is not None:
        rows = rows.filter(chapter__in=chapters.values("pk"))
    rows = rows.values("chapter_id", "start_verse_id", "end_verse_id", "count", "ref_text")
    matches = [
        r
        for r in rows
        if not target.isdisjoint(range(r["start_verse_id"], r["end_verse_id"] + 1))
    ]
    best: dict[int, dict] = {}
    for r in sorted(
        matches, key=lambda r: (r["end_verse_id"] - r["start_verse_id"], -r["count"])
    ):
        best.setdefault(r["chapter_id"], r)
    return list(best.values())


def english_chapters():
    """The chapters these pages may cite — published, English, bodies deferred.

    ``defer`` is not incidental: dragging ``body_html`` and the tsvector through
    the join cost a measured 40 MB on a broad query and is part of what caused
    the 2026-08-14 OOM. The excerpt needs ``body_text`` and nothing else.
    """
    return Chapter.objects.filter(
        book__language="en", book__is_published=True
    ).defer("body_html", "search_vector")


#: A span wider than this counts toward its Bible CHAPTER but not toward each
#: verse inside it. "Matthew 5:1-7:29" is a real citation of the Sermon on the
#: Mount; letting it vote for all 111 verses individually would manufacture a
#: hundred verse pages out of one general reference. Mirrors the cap
#: ``scripture._MAX_VERSES`` already puts on a popover lookup.
VERSE_SPAN_CAP = 25

#: Guard against a pathological span (a mis-parse, or a citation crossing many
#: chapters) walking the whole Bible while we bucket it. Well above any real
#: citation; it bounds the loop, it does not shape the data.
_SPAN_GUARD = 400


def english_citation_rows():
    """The citation rows a page may be built from: English, published."""
    return ChapterCitation.objects.filter(
        chapter__book__language="en", chapter__book__is_published=True
    ).values_list("chapter_id", "start_verse_id", "end_verse_id")


def bucket(rows) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """(verse id → citing chapter ids, BBBCCC → citing chapter ids).

    THE RULE THAT DECIDES WHAT EXISTS, in one place. `qualifying_pages` runs it
    over the whole corpus to build the page list, and `pages_for` runs it over a
    handful of rows to tell a chapter page which of its references may be
    linked. Two copies of this would drift, and the drift would be silent until
    a chapter page linked somewhere the page list never built — a 404 for the
    reader and a dead internal link for the crawler.

    Sets, not counters: the floor is about how many DISTINCT chapters treat a
    passage — one book returning to a verse ten times is one voice, and counting
    it ten times is how a single author's favourite text would manufacture a
    page nobody else cites.
    """
    by_verse: dict[int, set[int]] = {}
    by_chapter: dict[int, set[int]] = {}
    for cid, start, end in rows:
        end = min(end, start + _SPAN_GUARD)
        if end - start < VERSE_SPAN_CAP:
            for vid in range(start, end + 1):
                by_verse.setdefault(vid, set()).add(cid)
        for vid in range(start, end + 1):
            by_chapter.setdefault(vid // 1000, set()).add(cid)
    return by_verse, by_chapter


def _tally() -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """`bucket` over the whole English corpus — the page list's input."""
    return bucket(english_citation_rows().iterator(chunk_size=2000))


def _page(bcv: int, verse: bool) -> dict | None:
    """A verse id (or BBBCCC key) as the page identity, or None if unreal."""
    book = bible.Book(bcv // 1000000 if verse else bcv // 1000)
    chapter = (bcv // 1000) % 1000 if verse else bcv % 1000
    number = bcv % 1000 if verse else None
    if not chapter:
        return None
    return {
        "book": book_slug(book),
        "book_title": book.title,
        "book_order": book.value,
        "chapter": chapter,
        "verse": number,
    }


def qualifying_pages() -> list[dict]:
    """Every scripture page that has earned a URL, in canonical Bible order.

    THE ONE LIST. The detail views answer only for a page named here, the
    prerender entry generator builds from it, and the sitemap section lists it —
    so a page cannot be advertised without being built, or built without being
    reachable. Three places computing "does this qualify" independently is
    exactly how a sitemap ends up promising pages that render `noindex`.
    """
    by_verse, by_chapter = _tally()
    pages: list[dict] = []
    for key, cids in by_chapter.items():
        if len(cids) < CHAPTER_FLOOR:
            continue
        page = _page(key, verse=False)
        if page is None:
            continue
        # A chapter page's verse text comes from the bundled ASV; a book it
        # doesn't carry (the apocrypha) can be cited but cannot be rendered.
        if not verse_text(key * 1000 + 1):
            continue
        pages.append({**page, "citing_count": len(cids)})
    for vid, cids in by_verse.items():
        if len(cids) < VERSE_FLOOR:
            continue
        page = _page(vid, verse=True)
        if page is None or not verse_text(vid):
            continue
        pages.append({**page, "citing_count": len(cids)})
    pages.sort(key=lambda p: (p["book_order"], p["chapter"], p["verse"] or 0))
    return pages


def pages_for(refs: list[str]) -> dict[str, dict | None]:
    """Which of ``refs`` have a scripture page, as ``{ref: page or None}``.

    What the chapter page's scripture chips need: a chip may link to a page only
    if that page was built, or it is a 404 for the reader and a dead internal
    link for the crawler. The answer uses `bucket` — the same rule
    `qualifying_pages` uses — so the two cannot disagree about what exists.

    ONE QUERY, not one per reference. The obvious implementation asks per
    reference, and at up to eight references across a build of 1,264 chapter
    pages that is ten thousand queries to render a row of chips. Instead every
    reference's Bible chapter becomes one range predicate, OR'd into a single
    filter: the rows come back together and are bucketed in memory.

    A reference resolves to its VERSE page when it names one verse that clears
    the verse floor, otherwise to its Bible-chapter page, otherwise to nothing —
    the same order of preference a reader would want, most specific first.
    """
    from django.db.models import Q

    parsed: dict[str, tuple] = {}
    keys: set[int] = set()
    for ref in refs:
        ids = sorted(reference_verse_ids(ref))
        if not ids:
            continue
        # The Bible chapter this reference sits in. A reference spanning two
        # chapters is keyed by its first — the page it most belongs to.
        key = ids[0] // 1000
        parsed[ref] = (ids, key)
        keys.add(key)
    if not keys:
        return {}

    span = Q()
    for key in keys:
        span |= Q(start_verse_id__lte=key * 1000 + 999, end_verse_id__gte=key * 1000)
    by_verse, by_chapter = bucket(english_citation_rows().filter(span))

    out: dict[str, dict | None] = {}
    for ref, (ids, key) in parsed.items():
        book = bible.Book(key // 1000)
        chapter = key % 1000
        verse = ids[0] % 1000 if len(ids) == 1 else None
        if verse is not None and len(by_verse.get(ids[0], ())) >= VERSE_FLOOR:
            out[ref] = {"book": book_slug(book), "chapter": chapter, "verse": verse}
        elif len(by_chapter.get(key, ())) >= CHAPTER_FLOOR:
            out[ref] = {"book": book_slug(book), "chapter": chapter, "verse": None}
        else:
            out[ref] = None
    return out
