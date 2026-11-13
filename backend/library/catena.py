"""What the Church has said on a verse: a Bible chapter's catena, verse by verse.

A catena (``build_catena``) is a library book that quotes a book of the Bible a
few verses at a time, each block followed by the commentators the catena chose
for those verses. Its chapters are the index: this module reads a shipped
catena chapter back into ``[{verses, their commentators}]`` so the reader of the
Bible book itself (``build_owb_book``'s ``gospel-of-john``) can open, under a
verse, the two or three excerpts the catena gives it, and step into the catena
at that very block.

The pairing of a Bible book with its catena is ``CATENAS`` below — here, in a
content root, so a new pairing rebuilds the reader (``tests_catena`` fails when a
shipped catena is missing from it). The excerpts are not stored twice: they are
read from the catena chapter's own HTML, which ``build_catena`` lays out as:

    <h3>passage title</h3>
    <blockquote><p>the verses</p><p>— John 3:14–16</p></blockquote>
    <p><strong>Commentator</strong> · <em>Work</em></p> <p>excerpt…</p> …

English only, as the Bible books and their catenas are.
"""

from __future__ import annotations

import copy
import hashlib
import re
from functools import lru_cache

from bs4 import BeautifulSoup, Tag

from .content_fixtures import content_digest
from .scripture_graph import bible_book_of, bible_chapter_number

LANGUAGE = "en"

#: {canonical number of a book of the Bible: the slug of its catena}. A catena
#: built with ``build_catena`` and shipped as a fixture gets a line here.
CATENAS: dict[int, str] = {
    40: "catena-on-matthew",
    43: "catena-on-john",
    45: "catena-on-romans",
}

#: How much of an excerpt (and of the quoted verses) the panel shows, in words:
#: an opening to decide by, not the excerpt — the catena itself is one tap away.
SNIPPET_WORDS = 45
VERSE_WORDS = 40

#: The verse span at the end of a block's citation: "John 3:14–16" -> "3:14–16",
#: "John 7:53–8:11" -> "7:53–8:11".
_SPAN = re.compile(r"(\d+:\d+(?:–\d+(?::\d+)?)?)$")
#: A catena chapter is titled with the Bible chapter it is on ("John 3").
_CATENA_TITLE = re.compile(r"\s(\d+)$")


def catena_slug(book) -> str | None:
    """The slug of the catena on a library Book, when it is a Bible book that
    has one (``CATENAS``); None for every other book."""
    bible = bible_book_of(book)
    return CATENAS.get(bible.value) if bible is not None else None


@lru_cache(maxsize=16)
def _chapter_map(slug: str, digest: str) -> tuple[str, dict[int, int]] | None:
    """A catena's title and {Bible chapter: its chapter order} — read once per
    deploy (``digest`` is the shipped content's): the titles and layout come
    from the fixture. Whether it is published is asked live, with its bodies."""
    from .models import Book

    book = Book.objects.filter(slug=slug, language=LANGUAGE).only("title").first()
    if book is None:
        return None
    orders: dict[int, int] = {}
    for order, title in book.chapters.order_by("order").values_list("order", "title"):
        m = _CATENA_TITLE.search(title or "")
        if m:
            orders.setdefault(int(m.group(1)), order)
    return book.title, orders


def first_chapter(ref: str) -> int:
    """The Bible chapter a span begins in: "7:53–8:11" -> 7."""
    return int(ref.split(":", 1)[0])


def opening(text: str, words: int) -> str:
    """The first ``words`` of ``text``, marked as cut when it is. Mid-sentence
    on purpose: a sentence-end search stops at "in him." as if it were an
    abbreviation, and the panel only needs enough to decide by."""
    parts = text.split()
    if len(parts) <= words:
        return text
    return " ".join(parts[:words]).rstrip(",;:—– ") + "…"


def _text(el: Tag) -> str:
    return " ".join(el.get_text(" ").split())


def passages(body_html: str) -> tuple[dict, ...]:
    """A catena chapter's blocks that carry commentary, in order: each the span
    it quotes, the opening of its verses, ``p`` (the block's index among the
    body's top-level elements — the reader's ``?p=`` deep link) and its
    excerpts' openings. A block no excerpt follows (the tail of a passage, or
    the half of a block a disputed-passage note split) is left out."""
    soup = BeautifulSoup(body_html or "", "html.parser")
    out: list[dict] = []
    current = excerpt = None
    for index, el in enumerate(c for c in soup.children if isinstance(c, Tag)):
        if el.name == "blockquote":
            paras = el.find_all("p", recursive=False)
            m = _SPAN.search(_text(paras[-1])) if paras else None
            current = excerpt = None
            if m:
                cite = _text(paras[-1]).lstrip("— ").strip()
                verses = " ".join(_text(p) for p in paras[:-1])
                current = {
                    "ref": m.group(1),
                    "reference": cite,
                    "text": opening(verses, VERSE_WORDS),
                    "p": index,
                    "excerpts": [],
                }
                out.append(current)
        elif el.name != "p":  # a passage heading ends the block before it
            current = excerpt = None
        elif current is None:
            continue
        elif el.find("strong", recursive=False) and el.find("em", recursive=False):
            excerpt = {
                "author": _text(el.strong),
                "work": _text(el.em),
                "text": "",
            }
            current["excerpts"].append(excerpt)
        elif excerpt is not None and not excerpt["text"]:
            excerpt["text"] = opening(_text(el), SNIPPET_WORDS)
        elif el.em is not None and _text(el) == _text(el.em):
            excerpt = None  # an editorial note in italics, not commentary
    return tuple(p for p in out if p["excerpts"])


#: Parsed catena chapters, keyed by (slug, order, a hash of the body) — so an
#: edited body is parsed afresh, and the cache holds no body text.
_PARSED: dict[tuple[str, int, str], tuple[dict, ...]] = {}
_PARSED_MAX = 256


def _parsed(slug: str, order: int, body_html: str) -> tuple[dict, ...]:
    key = (slug, order, hashlib.sha256(body_html.encode()).hexdigest())
    if key not in _PARSED:
        if len(_PARSED) >= _PARSED_MAX:
            _PARSED.clear()
        _PARSED[key] = passages(body_html)
    return _PARSED[key]


class CatenaLookup:
    """One Bible book's catena, for a run of its chapters
    (``serializers.ChapterBatch``) or a single request: at most one query,
    for the catena chapters the run needs (the chapter map is per deploy).

    A span belongs to the reader chapter its first verse is in, wherever the
    catena put it: John 7:53–8:11 sits in the catena's "John 8" (most of its
    verses are there) but is a chip under the reader's John 7, and its link
    opens the catena's John 8 at that block. So a reader chapter reads the
    catena's chapters on it and on either side.
    """

    def __init__(self, book):
        self.slug = catena_slug(book) if book.language == LANGUAGE else None
        found = _chapter_map(self.slug, content_digest()) if self.slug else None
        self.title, self._orders = found or ("", {})
        self._bodies: dict[int, str] = {}
        self._fetched: set[int] = set()

    def _candidates(self, chapter) -> list[int]:
        n = bible_chapter_number(chapter) if self._orders else None
        if n is None:
            return []
        return [self._orders[k] for k in (n - 1, n, n + 1) if k in self._orders]

    def prefetch(self, chapters) -> None:
        """Read the catena chapters a run needs, in one query."""
        wanted = {o for c in chapters for o in self._candidates(c)} - self._fetched
        if not wanted:
            return
        from .models import Chapter

        self._bodies.update(
            Chapter.objects.filter(
                book__slug=self.slug,
                book__language=LANGUAGE,
                book__is_published=True,
                order__in=wanted,
            ).values_list("order", "body_html")
        )
        self._fetched |= wanted

    def passages(self, chapter) -> tuple[int, list[dict]] | None:
        """(the catena's chapter on this one, the spans that begin in it —
        each a fresh dict carrying the catena ``chapter`` it is in) for a
        reader chapter, or None when its catena has nothing on it."""
        candidates = self._candidates(chapter)
        if not candidates:
            return None
        self.prefetch([chapter])
        n = bible_chapter_number(chapter)
        found = [
            {**copy.deepcopy(block), "chapter": order}
            for order in candidates
            if order in self._bodies
            for block in _parsed(self.slug, order, self._bodies[order])
            if first_chapter(block["ref"]) == n
        ]
        if not found:
            return None
        return self._orders.get(n, found[0]["chapter"]), found

    def summary(self, chapter) -> dict | None:
        """The chapter payload's pointer: which catena, its chapter on this
        one, and the spans it comments on (the reader's verse chips). The
        excerpts are fetched when a reader opens one (``ChapterCatenaView``)."""
        found = self.passages(chapter)
        if found is None:
            return None
        order, blocks = found
        return {
            "slug": self.slug,
            "title": self.title,
            "chapter": order,
            "verses": [b["ref"] for b in blocks],
        }
