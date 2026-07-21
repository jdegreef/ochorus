"""Canonical shape + validation for text-range marks.

A mark highlights a character range inside one paragraph of a chapter:

    {"id": "<group id>", "p": <paragraph index>, "s": <start>, "e": <end>,
     "note": "<optional note text>"}

Offsets index the paragraph's *text content* (concatenated text nodes), which
is layout-independent — ranges survive font-size and column-width changes.
``e == -1`` means "to the end of the paragraph" (used by migrated legacy
paragraph-level marks, resolved against the live text at render time). A
selection spanning paragraphs is stored as one mark per paragraph sharing the
same ``id``, so the group toggles and annotates as a unit.

Legacy shape (pre-range): {"h": [paragraph indices], "n": {index: note}}.
`from_legacy` converts it — a highlighted paragraph becomes a full-paragraph
range, and a paragraph note attaches to that range (or creates one).
"""

from __future__ import annotations

# Highlight colour keys the reader can set (mirrors HIGHLIGHT_COLORS on the
# frontend). Gold is the default and is stored implicitly (absent), but accepted
# here if a client sends it. Anything outside this set is dropped.
_HL_COLORS = {"gold", "blue", "green", "rose"}


def _int(value, default=-1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clean_mark_list(raw) -> list[dict]:
    """Validate/coerce a client-supplied mark list. Drops anything malformed."""
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen: set[tuple] = set()
    for m in raw:
        if not isinstance(m, dict):
            continue
        p = _int(m.get("p"))
        s = _int(m.get("s"), default=0)
        e = _int(m.get("e"))
        if p < 0 or s < 0 or (e != -1 and e <= s):
            continue
        key = (p, s, e)
        if key in seen:
            continue
        seen.add(key)
        mark = {
            "id": str(m.get("id") or f"{p}:{s}:{e}"),
            "p": p,
            "s": s,
            "e": e,
        }
        note = m.get("note")
        if isinstance(note, str) and note.strip():
            mark["note"] = note.strip()
        color = m.get("color")
        if isinstance(color, str) and color in _HL_COLORS:
            mark["color"] = color
        out.append(mark)
    out.sort(key=lambda m: (m["p"], m["s"]))
    return out


def from_legacy(highlights, notes) -> list[dict]:
    """Convert the pre-range shape to marks (full-paragraph ranges)."""
    marks: dict[int, dict] = {}
    for h in highlights or []:
        p = _int(h)
        if p >= 0:
            marks[p] = {"id": f"legacy:{p}", "p": p, "s": 0, "e": -1}
    if isinstance(notes, dict):
        for k, v in notes.items():
            p = _int(k)
            if p < 0 or not isinstance(v, str) or not v.strip():
                continue
            mark = marks.setdefault(p, {"id": f"legacy:{p}", "p": p, "s": 0, "e": -1})
            mark["note"] = v.strip()
    return sorted(marks.values(), key=lambda m: m["p"])


def merge_mark_lists(server: list[dict], incoming: list[dict]) -> list[dict]:
    """Union two mark lists by (p, s, e); on a note collision the longer wins."""
    by_range: dict[tuple, dict] = {(m["p"], m["s"], m["e"]): dict(m) for m in server}
    for m in incoming:
        key = (m["p"], m["s"], m["e"])
        existing = by_range.get(key)
        if not existing:
            by_range[key] = dict(m)
            continue
        note_new = m.get("note", "")
        if len(note_new) > len(existing.get("note", "")):
            existing["note"] = note_new
    merged = sorted(by_range.values(), key=lambda m: (m["p"], m["s"]))
    return merged
