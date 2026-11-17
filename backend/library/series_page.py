"""What a series page shows from inside its books: the plates, and one day.

Two readings of chapter HTML for ``SeriesDetailView``, kept out of views.py
because each is a small parser with rules of its own.

* ``series_plates`` — the illustrations an illustrated series (The
  Lamplighters of Gloamhaven) carries, one per chapter, so the series page
  can show what kind of book this is before a reader opens one. Today they
  appear only inside the reader.
* ``sample_day`` — one day of a daily devotional (Daughters of the King,
  Rooted), split into the parts every day in these books has: the verse, the
  teaching, the prompts ("Think about it:", "Try this:") and the prayer, so
  a parent sees exactly what a day asks of a child.

Both read the stored, sanitized ``body_html`` (``library/sanitize.py``) and
return plain text or site paths, never HTML.
"""

from __future__ import annotations

import html as _html
import re

from django.db.models import F, Value
from django.db.models.functions import StrIndex, Substr

#: The most plates a series page shows from one book, so the row walks the
#: whole series rather than filling up with Book 1.
PLATES_PER_BOOK = 5

#: How much of a chapter, from its first image on, is read for its plate. A
#: book's opening chapter leads with the map and puts its plate after it; one
#: window holds both, and the body past it never leaves the database.
PLATE_WINDOW = 2400

_IMG = re.compile(r"<img\b[^>]*>")
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_TAG = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    return _html.unescape(re.sub(r"\s+", " ", _TAG.sub("", fragment))).strip()


def _is_plate(attrs: dict) -> bool:
    """A full-page plate: a self-hosted picture taller than it is wide. That
    leaves out a book's opening map (landscape, and the series' own section,
    ``Series.map``) and anything the row's portrait frames would crop."""
    try:
        portrait = int(attrs.get("height", 0)) > int(attrs.get("width", 0))
    except ValueError:
        return False
    return attrs.get("src", "").startswith("/illustrations/") and portrait


def _first_plate(window: str) -> dict | None:
    for tag in _IMG.findall(window):
        attrs = dict(_ATTR.findall(tag))
        if _is_plate(attrs):
            return {"src": attrs["src"], "alt": _html.unescape(attrs.get("alt", ""))}
    return None


def series_plates(books) -> list[dict]:
    """``[{src, alt, book, order, chapter}]`` — each illustrated chapter's
    plate, books in the order given, chapters in order, at most
    ``PLATES_PER_BOOK`` from each. ``book`` is the slug, ``chapter`` the chapter's title in
    the edition's language. Empty for a series without pictures.

    Reads a window of each illustrated chapter, from its first ``<img``, rather
    than whole bodies: forty-five chapters of Lamplighters are ~1.3 MB of HTML,
    and the plates sit in the first few hundred bytes of the window.
    """
    from .models import Chapter

    rank = {b.pk: i for i, b in enumerate(books)}
    slug = {b.pk: b.slug for b in books}
    rows = (
        Chapter.objects.filter(book_id__in=rank, body_html__contains="<img")
        .annotate(at=StrIndex("body_html", Value("<img")))
        .annotate(window=Substr("body_html", F("at"), PLATE_WINDOW))
        .values_list("book_id", "order", "title", "window")
    )
    plates, per_book = [], dict.fromkeys(rank, 0)
    for book_id, order, title, window in sorted(rows, key=lambda r: (rank[r[0]], r[1])):
        if per_book[book_id] < PLATES_PER_BOOK and (plate := _first_plate(window)):
            plates.append({**plate, "book": slug[book_id], "order": order, "chapter": title})
            per_book[book_id] += 1
    return plates


_P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
_BLOCKQUOTE = re.compile(r"<blockquote\b[^>]*>(.*?)</blockquote>", re.S)
#: A prompt paragraph: its label in bold, then the prompt ("Think about it:
#: What does…"). The label is the book's own, in the book's own language.
_PROMPT = re.compile(r"^\s*<strong>([^<]{1,40}?)\s*[:：]?\s*</strong>\s*[:：]?\s*(.+)$", re.S)
#: The day's prayer: one paragraph set wholly in italics, last in the chapter.
_PRAYER = re.compile(r"^\s*<em>(.+)</em>\s*$", re.S)


def sample_day(body_html: str) -> dict | None:
    """``{verse: {text, ref}, teaching, prompts: [{label, text}], prayer}``
    from one day's chapter, or None when the chapter is not shaped like a day.

    Every day in the daily series opens on its verse (a blockquote: the text,
    then "— Isaiah 43:1 (BSB)"), teaches in plain paragraphs, then asks in
    bold-labelled prompts and closes on an italic prayer. Read by STRUCTURE,
    not by the English labels, so a translated day ("Piénsalo:", "Inténtalo:")
    splits the same way and keeps its own words.
    """
    quote = _BLOCKQUOTE.search(body_html or "")
    if not quote:
        return None
    lines = [_text(p) for p in _P.findall(quote.group(1))]
    lines = [line for line in lines if line]
    if len(lines) < 2:
        return None
    text = " ".join(lines[:-1])
    ref = re.sub(r"^[—–-]\s*", "", lines[-1])
    rest = _P.findall(body_html[quote.end():])
    if not rest:
        return None
    teaching, prompts, prayer = "", [], ""
    for raw in rest:
        if m := _PROMPT.match(raw):
            prompts.append({"label": _text(m.group(1)), "text": _text(m.group(2))})
        elif not teaching and not prompts:
            teaching = _text(raw)
    if m := _PRAYER.match(rest[-1]):
        prayer = _text(m.group(1))
    if not (teaching and prompts and prayer):
        return None
    return {"verse": {"text": text, "ref": ref}, "teaching": teaching, "prompts": prompts, "prayer": prayer}
