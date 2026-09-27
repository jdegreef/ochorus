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

import math
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


def _nearest(text: str, q: str, near: int) -> int:
    """The UTF-16 offset of the occurrence of ``q`` in ``text`` nearest
    ``near``, or -1."""
    best = -1
    i = text.find(q)
    while i != -1:
        u = _to_u16(text, i)
        if best == -1 or abs(u - near) < abs(best - near):
            best = u
        i = text.find(q, i + 1)
    return best


def _find(
    paras: list[str], m: dict, at: int, lo: int = 0, hi: float = math.inf
) -> dict | None:
    """Mark ``m`` looked for around block ``at`` (its own block shifted by its
    group's displacement), within blocks ``lo``..``hi``, nearest its old
    offset (so in place when its anchor still sits there). A short anchor is
    tried at ``at`` and then, if that is not where it was, in its own block.
    Mirrors ``find`` in markAnchor.ts."""
    q = m.get("q")
    if not q:
        return m
    s = m["s"]
    if _u16_len(q) < SHORT_ANCHOR:
        tries = [at] if at == m["p"] else [at, m["p"]]
    else:
        tries = [at + d for d in SEARCH_ORDER]
    for p in tries:
        if not lo <= p <= hi or not 0 <= p < len(paras):
            continue
        start = _nearest(paras[p], q, s)
        if start == -1:
            continue
        if p == m["p"] and start == s:
            return m
        e = m["e"]
        return {**m, "p": p, "s": start, "e": -1 if e == -1 else start + (e - s)}
    return None


def resolve_mark(paras: list[str], m: dict) -> dict | None:
    """Where a single mark sits in ``paras`` now: the mark itself when its
    anchor is still at its offsets (or it has none to check), a moved copy, or
    None when the words are gone. Mirrors ``resolveMark`` in markAnchor.ts."""
    return _find(paras, m, m["p"])


def resolve_group(paras: list[str], segs: list[dict]) -> list[dict | None]:
    """Where one highlight's segments (one per block, sharing an id) sit now,
    as a unit: the longest anchor is placed first and fixes the displacement;
    the segments after it are looked for in reading order and those before it
    in reverse, each where its neighbour nearer the lead puts it and never
    past that neighbour. A segment that can't be found is None. Returned in
    ``segs``'s order. Mirrors ``resolveGroup`` in markAnchor.ts."""
    order = sorted(range(len(segs)), key=lambda i: (segs[i]["p"], segs[i]["s"]))
    lengths = [_u16_len(segs[i].get("q") or "") for i in order]
    li = lengths.index(max(lengths))
    lead = segs[order[li]]
    placed = resolve_mark(paras, lead) if lead.get("q") else None
    out: list[dict | None] = [None] * len(segs)

    def walk(ks: range, forward: bool) -> None:
        shift = placed["p"] - lead["p"] if placed else 0
        bound = placed["p"] if placed else 0
        for k in ks:
            seg = segs[order[k]]
            at = seg["p"] + shift
            m = _find(paras, seg, at, bound) if forward else _find(paras, seg, at, 0, bound)
            out[order[k]] = m
            # An unanchored segment can't be checked, so it says nothing about
            # where the run went.
            if m is not None and seg.get("q"):
                shift = m["p"] - seg["p"]
                bound = m["p"]

    if placed:
        out[order[li]] = placed
        walk(range(li + 1, len(order)), True)
        walk(range(li - 1, -1, -1), False)
    else:
        walk(range(len(order)), True)
    return out


def remap_mark_list(
    marks: list[dict], texts_for: Callable[[str], list[str] | None]
) -> tuple[list[dict], int]:
    """Move each anchored, edition-tagged highlight to where its words are now
    in that edition's text, a multi-block highlight's segments together (see
    ``resolve_group``). Returns (marks, how many segments moved). An untagged
    mark, or one whose edition has no text any more, can't be checked and is
    kept; so is a segment whose words are gone — the reader shows it as
    detached."""
    # A group is its id in one edition — the key placeMarks uses in the reader.
    groups: dict[tuple, list[int]] = {}
    for i, m in enumerate(marks):
        if m.get("lang") and m.get("q"):
            groups.setdefault((m.get("id"), m["lang"]), []).append(i)
    out = list(marks)
    moved = 0
    for (_, lang), idx in groups.items():
        paras = texts_for(lang)
        if not paras:
            continue
        for i, found in zip(idx, resolve_group(paras, [marks[i] for i in idx]), strict=True):
            if found is not None and found is not marks[i]:
                out[i] = found
                moved += 1
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
