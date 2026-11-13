"""What the Church has said on a verse: a Bible chapter's catena, verse by verse.

A catena (``build_catena``) is a library book that quotes a book of the Bible a
few verses at a time, each block followed by the commentators the catena chose
for those verses. Its chapters are the index: this module reads a shipped
catena chapter back into ``[{verses, their commentators}]`` so the reader of the
Bible book itself (``build_owb_book``'s ``gospel-of-john``) can open, under a
verse, the two or three excerpts the catena gives it, and step into the catena
at that very block.

Nothing is stored twice. The pairing of a Bible book with its catena is the two
editorial folders that share a book code — ``data/owb/<CODE>/book.json`` and
``data/catena/<CODE>/book.json`` — so a catena on Romans is wired to the reader's
Romans the day its fixture ships, with no list to update here. The excerpts are
read from the catena chapter's own HTML, which ``build_catena`` lays out as:

    <h3>passage title</h3>
    <blockquote><p>the verses</p><p>— John 3:14–16</p></blockquote>
    <p><strong>Commentator</strong> · <em>Work</em></p> <p>excerpt…</p> …

English only, as the Bible books and their catenas are.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from django.conf import settings

DATA = Path(settings.BASE_DIR) / "library" / "data"
LANGUAGE = "en"

#: How much of an excerpt (and of the quoted verses) the panel shows, in words:
#: an opening to decide by, not the excerpt — the catena itself is one tap away.
SNIPPET_WORDS = 45
VERSE_WORDS = 40

#: The verse span at the end of a block's citation: "John 3:14–16" -> "3:14–16",
#: "John 7:53–8:11" -> "7:53–8:11".
_SPAN = re.compile(r"(\d+:\d+(?:–\d+(?::\d+)?)?)$")
#: A Bible book's reader chapter is titled with its chapter number ("John 3",
#: "Psalm 23"), as is the catena's chapter on it.
_TRAILING_NUMBER = re.compile(r"\s(\d+)$")


@lru_cache(maxsize=1)
def catena_slugs() -> dict[str, str]:
    """{Bible book slug: its catena's slug}, from the editorial folders that
    share a book code (see the module docstring)."""
    pairs = {}
    root = DATA / "catena"
    for meta in sorted(root.glob("*/book.json")) if root.is_dir() else ():
        bible = DATA / "owb" / meta.parent.name / "book.json"
        if bible.is_file():
            pairs[json.loads(bible.read_text("utf-8"))["slug"]] = json.loads(
                meta.read_text("utf-8")
            )["slug"]
    return pairs


def bible_chapter_number(chapter) -> int | None:
    """The Bible chapter a reader chapter of a Bible book is, or None for its
    introduction and conclusion. ``build_owb_book`` sets reader chapter
    ``order`` as Bible chapter ``order - 1`` and titles it so; both must agree
    (as ``scripture_graph.classics_page`` requires) or nothing is linked."""
    m = _TRAILING_NUMBER.search(chapter.title or "")
    n = int(m.group(1)) if m else None
    return n if n is not None and n == chapter.order - 1 else None


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


@lru_cache(maxsize=64)
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


class CatenaLookup:
    """One Bible book's catena, looked up once for a run of its chapters
    (``serializers.ChapterBatch``) or a single request."""

    def __init__(self, book):
        from .models import Book

        self.book = None
        self._chapters: dict[int, int] = {}
        self._bodies: dict[int, str] = {}
        slug = catena_slugs().get(book.slug) if book.language == LANGUAGE else None
        if not slug:
            return
        self.book = (
            Book.objects.filter(slug=slug, language=LANGUAGE, is_published=True)
            .only("slug", "title")
            .first()
        )
        if self.book is None:
            return
        for order, title in self.book.chapters.values_list("order", "title"):
            m = _TRAILING_NUMBER.search(title or "")
            if m:
                self._chapters.setdefault(int(m.group(1)), order)

    def _order_for(self, chapter) -> int | None:
        if self.book is None:
            return None
        n = bible_chapter_number(chapter)
        return self._chapters.get(n) if n is not None else None

    def prefetch(self, chapters) -> None:
        """Read the catena chapters a run needs in one query."""
        wanted = {o for c in chapters if (o := self._order_for(c)) is not None}
        if wanted:
            self._bodies.update(
                self.book.chapters.filter(order__in=wanted).values_list("order", "body_html")
            )

    def passages(self, chapter) -> tuple[int, tuple[dict, ...]] | None:
        """(the catena's chapter order, its commented blocks) for a reader
        chapter, or None when its catena has nothing on it."""
        order = self._order_for(chapter)
        if order is None:
            return None
        if order not in self._bodies:
            self._bodies[order] = (
                self.book.chapters.filter(order=order).values_list("body_html", flat=True).first()
                or ""
            )
        found = passages(self._bodies[order])
        return (order, found) if found else None

    def summary(self, chapter) -> dict | None:
        """The chapter payload's pointer: which catena, which of its chapters,
        and the spans it comments on (the reader's verse chips). The excerpts
        themselves are fetched when a reader opens one (``ChapterCatenaView``)."""
        found = self.passages(chapter)
        if found is None:
            return None
        order, blocks = found
        return {
            "slug": self.book.slug,
            "title": self.book.title,
            "chapter": order,
            "verses": [b["ref"] for b in blocks],
        }
