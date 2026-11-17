"""A Bible book's overview card: who wrote it, when, its key verse and its theme.

The card at the top of each of the 66 Bible book pages (``/books/<slug>/``):
"Paul · c. AD 57 · Key verse Romans 1:16 · The gospel of God's righteousness,
received by faith." The words live with the rest of the book's editorial, as
the ``overview`` of ``data/owb/<CODE>/book.json`` (``build_owb_book``'s
EDITORIAL), keyed by the book's slug:

* ``author`` and ``date`` say what the church has long held, in its own words
  ("Traditionally Moses", "Isaiah son of Amoz"), and say so plainly where
  nobody knows ("Author unknown", "Date unknown") — never a scholarly debate;
* ``key_verse`` is a REFERENCE only. Its text is quoted live from the bundled
  Open Word Bible through ``scripture.lookup``, the verse popover's own source,
  so the card can never drift from the translation the book prints;
* ``theme`` is one plain sentence.

Read at serialize time, so this module and ``data/owb`` are content roots
(``content_sources.json``): editing a theme rebuilds the prerendered page.
English only, as the Bible books are.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .scripture import chapter_of, lookup

DIR = Path(__file__).parent / "data" / "owb"

#: The fields every overview carries.
FIELDS = ("author", "date", "key_verse", "theme")

_QUOTES = '"“”'


@lru_cache(maxsize=1)
def table() -> dict[str, dict[str, str]]:
    """``{book slug: overview}`` from every editorial ``book.json`` that has one."""
    out = {}
    for path in sorted(DIR.glob("*/book.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta.get("overview"):
            out[meta["slug"]] = meta["overview"]
    return out


def _trim_quotes(text: str) -> str:
    """Drop the one quotation mark a verse borrows from its neighbours.

    A speech that opens in the verse before ("…his life as a ransom for
    many.”") or closes in the verse after leaves an unpaired mark at the
    verse's edge, which out of context reads as a typo. Only an unpaired mark,
    and only at an edge: a speech that opens inside the verse and runs on
    (Ruth 1:16) keeps its opening mark, as Bibles print it.
    """
    if sum(text.count(q) for q in _QUOTES) % 2 == 0:
        return text
    if text[:1] in _QUOTES:
        return text[1:]
    if text[-1:] in _QUOTES:
        return text[:-1]
    return text


@lru_cache(maxsize=128)
def key_verse(reference: str) -> dict | None:
    """``{reference, text, chapter, verse}`` for a key verse, or None when the
    Bible lookup cannot resolve it. ``chapter``/``verse`` place it in the
    reader (``/books/<slug>/<n>#v<verse>``)."""
    ref = reference.replace("–", "-")
    found = lookup(ref)
    where = chapter_of(ref)
    if not found or not where:
        return None
    text = " ".join(v["text"] for v in found["verses"])
    return {
        "reference": reference,
        "text": _trim_quotes(text),
        "chapter": where[1],
        "verse": found["verses"][0]["number"],
    }


def overview(slug: str) -> dict | None:
    """The overview card for the Bible book ``slug``, or None when it has none."""
    meta = table().get(slug)
    if not meta:
        return None
    return {
        "author": meta["author"],
        "date": meta["date"],
        "theme": meta["theme"],
        "key_verse": key_verse(meta["key_verse"]),
    }
