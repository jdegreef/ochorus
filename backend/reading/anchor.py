"""Keeping saved highlights and bookmarks on their words when a text is repaired.

The server half of ``frontend/src/lib/markAnchor.ts``. The reader already finds
a moved highlight at render time by its anchor text ``q``; this moves the
STORED copy to match (the ``remap_marks`` release step), so every device, the
notebook and any later export agree on where it is, and bookmarks — which carry
no anchor, only the opening words of their paragraph — are found again too.

The rules are the reader's, kept identical so the two never disagree: a mark
whose anchor still sits at its offsets is left alone; one whose anchor moved is
looked for in its own block and up to three either side, nearest first, and
taken to the occurrence nearest its old offset; an anchor shorter than
``SHORT_ANCHOR`` is only looked for in its own block; one found nowhere is left
exactly as stored (the reader shows it as detached rather than guess).

Offsets count UTF-16 code units, because that is what the browser's string
indices count; a Python ``str`` counts code points, so the two only differ for
characters beyond the BMP — converted at the edges here.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from lxml import etree
from lxml import html as lxml_html

# Mirrors markAnchor.ts — change both together.
SHORT_ANCHOR = 12
SEARCH_ORDER = (0, -1, 1, -2, 2, -3, 3)

_ASTRAL = re.compile("[\U00010000-\U0010ffff]")
_SPACE = re.compile(r"\s+")


def block_texts(body_html: str) -> list[str]:
    """The text of each top-level block of a stored body — what the reader
    indexes a mark's ``p`` into (``body.children[p].textContent``)."""
    if not body_html or not body_html.strip():
        return []
    try:
        nodes = lxml_html.fragments_fromstring(body_html)
    except (etree.ParserError, ValueError):
        return []
    # A leading bare string and comments are not element children in the DOM.
    return [
        str(n.text_content())
        for n in nodes
        if not isinstance(n, str) and isinstance(n.tag, str)
    ]


def _u16_len(text: str) -> int:
    return len(text) + len(_ASTRAL.findall(text))


def _to_u16(text: str, i: int) -> int:
    """A code-point index into ``text`` as a UTF-16 offset."""
    return i + len(_ASTRAL.findall(text, 0, i))


def _from_u16(text: str, u: int) -> int | None:
    """A UTF-16 offset as a code-point index, or None when it falls inside a
    surrogate pair or past the end."""
    if not _ASTRAL.search(text):
        return u if 0 <= u <= len(text) else None
    n = 0
    for i, ch in enumerate(text):
        if n == u:
            return i
        if n > u:
            return None
        n += 2 if ord(ch) > 0xFFFF else 1
    return len(text) if n == u else None


def resolve_mark(paras: list[str], m: dict) -> dict | None:
    """Where a mark sits in ``paras`` now: the mark itself when its anchor is
    still at its offsets (or it has none to check), a moved copy, or None when
    the words are gone. Mirrors ``resolveMark`` in markAnchor.ts."""
    q = m.get("q")
    p, s = m["p"], m["s"]
    if not q:
        return m
    if 0 <= p < len(paras):
        at = _from_u16(paras[p], s)
        if at is not None and paras[p].startswith(q, at):
            return m
    for d in (0,) if _u16_len(q) < SHORT_ANCHOR else SEARCH_ORDER:
        if not 0 <= p + d < len(paras):
            continue
        text = paras[p + d]
        best = -1
        i = text.find(q)
        while i != -1:
            u = _to_u16(text, i)
            if best == -1 or abs(u - s) < abs(best - s):
                best = u
            i = text.find(q, i + 1)
        if best != -1:
            e = m["e"]
            return {**m, "p": p + d, "s": best, "e": -1 if e == -1 else best + (e - s)}
    return None


def remap_mark_list(
    marks: list[dict], texts_for: Callable[[str], list[str] | None]
) -> tuple[list[dict], int]:
    """Move each anchored, edition-tagged mark to where its words are now in
    that edition's text. Returns (marks, how many moved). An untagged mark, or
    one whose edition has no text any more, can't be checked and is kept; so is
    one whose words are gone — the reader shows it as detached."""
    out: list[dict] = []
    moved = 0
    for m in marks:
        lang = m.get("lang")
        paras = texts_for(lang) if lang and m.get("q") else None
        found = resolve_mark(paras, m) if paras else None
        if found is not None and found is not m:
            moved += 1
            m = found
        out.append(m)
    if moved:
        out.sort(key=lambda m: (m["p"], m["s"]))
    return out, moved


def _squash(text: str) -> str:
    # innerText (what a snippet was cut from) and textContent differ in their
    # whitespace — a <br> is a newline in one and nothing in the other — so
    # compare with all of it removed.
    return _SPACE.sub("", text)


def refind_bookmark(editions: list[list[str]], p: int, snippet: str) -> int | None:
    """The block a bookmark's paragraph moved to, or None when it hasn't moved
    (or can't be found, or its snippet is too short to be sure of).

    A bookmark carries no edition, so every edition of the text is tried: it
    stays when its paragraph still opens with the snippet in any of them, and
    moves only to the nearest block that does."""
    target = _squash(snippet)
    if len(target) < SHORT_ANCHOR:
        return None

    def opens(i: int) -> bool:
        return any(0 <= i < len(t) and _squash(t[i]).startswith(target) for t in editions)

    if opens(p):
        return None
    return next((p + d for d in SEARCH_ORDER[1:] if opens(p + d)), None)
