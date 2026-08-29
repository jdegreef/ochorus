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

# Bounds on one chapter's stored marks. A ChapterMarks row's `marks` JSON is
# returned in full on every /state and /merge, so an unbounded list (or a
# multi-megabyte note) would balloon every sync for that account. Generous — no
# honest reader annotates one chapter 500 times or writes a 5,000-char note.
MAX_MARKS_PER_CHAPTER = 500
MAX_NOTE_LEN = 5000
MAX_ID_LEN = 64
# A mark's edition tag ("en", "es", "en-modern"). Matches ChapterMarks.language.
MAX_LANG_LEN = 10

# Deletions are recorded as tombstones — {group_id: deleted_at_ms} — so a mark
# removed on one device stays removed everywhere: a stale device that still holds
# it and re-pushes the whole list can't resurrect it (the live PUT unions instead
# of replacing, so absence alone no longer means "deleted"). Bounded like marks,
# and pruned by age: a tombstone only needs to outlive the slowest un-synced
# device, after which dropping it just risks re-importing a months-offline edit.
MAX_TOMBSTONES_PER_CHAPTER = 500
TOMBSTONE_TTL_MS = 1000 * 60 * 60 * 24 * 180  # 180 days


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
        if len(out) >= MAX_MARKS_PER_CHAPTER:
            break  # bound the accepted list (and the work) on an oversized payload
        if not isinstance(m, dict):
            continue
        p = _int(m.get("p"))
        s = _int(m.get("s"), default=0)
        e = _int(m.get("e"))
        if p < 0 or s < 0 or (e != -1 and e <= s):
            continue
        lang = m.get("lang")
        lang = lang[:MAX_LANG_LEN] if isinstance(lang, str) and lang else None
        # The edition is part of a mark's identity, not decoration. A chapter's
        # editions share one row (same kind/slug/order) but not one text, so two
        # marks at identical offsets in different editions are two different
        # highlights — deduping them on offsets alone silently ate one.
        key = (p, s, e, lang)
        if key in seen:
            continue
        seen.add(key)
        mark = {
            "id": str(m.get("id") or f"{p}:{s}:{e}")[:MAX_ID_LEN],
            "p": p,
            "s": s,
            "e": e,
        }
        if lang:
            mark["lang"] = lang
        note = m.get("note")
        if isinstance(note, str) and note.strip():
            mark["note"] = note.strip()[:MAX_NOTE_LEN]
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


def _range_key(m: dict) -> tuple:
    """A mark's identity: its offsets AND the edition they were measured in."""
    return (m["p"], m["s"], m["e"], m.get("lang"))


def merge_mark_lists(server: list[dict], incoming: list[dict]) -> list[dict]:
    """Union two mark lists by (p, s, e, lang); on a note collision the longer
    wins. Untagged marks (written before editions were tagged) keep merging with
    each other, so nothing already on the server is duplicated by this change."""
    by_range: dict[tuple, dict] = {_range_key(m): dict(m) for m in server}
    for m in incoming:
        key = _range_key(m)
        existing = by_range.get(key)
        if not existing:
            by_range[key] = dict(m)
            continue
        note_new = m.get("note", "")
        if len(note_new) > len(existing.get("note", "")):
            existing["note"] = note_new
    merged = sorted(by_range.values(), key=lambda m: (m["p"], m["s"]))
    # The union of two already-capped lists can reach 2× the cap. Hold the line at
    # the per-chapter bound: the union is lossless for any realistic chapter (no
    # reader makes 500 distinct highlights in one chapter), and only in
    # abuse territory — beyond the cap — are the trailing ranges dropped. That
    # anti-abuse ceiling is deliberately preferred over an unbounded stored blob.
    return merged[:MAX_MARKS_PER_CHAPTER]


def clean_tombstones(raw) -> dict[str, int]:
    """A client-supplied deletion set → ``{group_id: deleted_at_ms}``.

    Accepts a dict ``{id: at}``, a list of ids, or a list of ``{"id", "at"}``.
    Anything malformed is dropped; a missing/invalid ``at`` becomes 0 (treated as
    "long ago", so it prunes first). Bounded like the mark list.
    """
    items: list[tuple] = []
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, str):
                items.append((entry, 0))
            elif isinstance(entry, dict):
                items.append((entry.get("id"), entry.get("at")))
    out: dict[str, int] = {}
    for key, at in items:
        if not isinstance(key, str) or not key:
            continue
        out[key[:MAX_ID_LEN]] = max(0, _int(at, default=0))
        if len(out) >= MAX_TOMBSTONES_PER_CHAPTER:
            break
    return out


def merge_tombstones(server: dict[str, int], incoming: dict[str, int]) -> dict[str, int]:
    """Union two tombstone sets, keeping the newer ``deleted_at`` per id."""
    out = dict(server)
    for key, at in incoming.items():
        if key not in out or at > out[key]:
            out[key] = at
    return out


def prune_tombstones(tombs: dict[str, int], now_ms: int) -> dict[str, int]:
    """Drop tombstones past the TTL, then cap to the newest MAX (keeps the set
    from growing without bound under repeated highlight/delete churn)."""
    live = {k: v for k, v in tombs.items() if v == 0 or now_ms - v < TOMBSTONE_TTL_MS}
    if len(live) > MAX_TOMBSTONES_PER_CHAPTER:
        newest = sorted(live.items(), key=lambda kv: kv[1], reverse=True)
        live = dict(newest[:MAX_TOMBSTONES_PER_CHAPTER])
    return live


def reconcile_marks(
    server_marks: list[dict],
    server_tombs: dict[str, int],
    incoming_marks: list[dict],
    incoming_tombs: dict[str, int],
    now_ms: int,
) -> tuple[list[dict], dict[str, int]]:
    """Tombstone-aware merge of one chapter's marks. Returns (marks, tombstones).

    1. This push's own deletions remove the matching server marks first, so a
       delete + re-highlight of the same range in one payload keeps the re-add.
    2. Union the (remaining) server marks with the incoming ones by range —
       nothing either side still holds is dropped (the cross-device fix).
    3. Suppress any mark whose group id is tombstoned by EITHER side, so a stale
       device re-pushing a mark someone else deleted can't resurrect it.
    """
    tombs = merge_tombstones(server_tombs, incoming_tombs)
    kept_server = [m for m in server_marks if m.get("id") not in incoming_tombs]
    merged = merge_mark_lists(kept_server, incoming_marks)
    merged = [m for m in merged if m.get("id") not in tombs]
    return merged, prune_tombstones(tombs, now_ms)
