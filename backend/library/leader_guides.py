"""Printable leader's guides for the young-reader editions.

A leader's guide turns one children's (or teens') edition into a run of weekly
sessions for a church group or a homeschool: one week per chapter, each with a
summary for the leader, a memory verse and a simple activity. It is editorial
copy that sits BESIDE the book, keyed by the slug + language that are the
edition's identity — the same reasoning as ``data/book_meta`` — so it lives in
``data/leader_guides/<slug>.<language>.json`` rather than in new columns.

What the guide does NOT carry is what the chapter row already holds: the
opening verse, the three answered questions and the closing prayer. The page
shows those beside the guide's own text (``chapter_extras``), so they are
written once, in the book, and a correction there reaches the guide too.

Files are read once per process and cached by directory, so a test that points
``DATA_DIR`` somewhere else reads its own files without clearing anything.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

# The body's own tag pattern and plain-text rule, so "markup" and "the text of
# a block" mean here what they mean for body_text.
from .text import _TAG, html_to_text

DATA_DIR = Path(__file__).resolve().parent / "data" / "leader_guides"

#: How many steps an activity may have — enough to follow, few enough for ten minutes.
MIN_STEPS, MAX_STEPS = 3, 5


@lru_cache(maxsize=4)
def _load(directory: str) -> dict[tuple[str, str], dict]:
    out = {}
    for path in sorted(Path(directory).glob("*.json")):
        slug, _, language = path.stem.rpartition(".")
        if slug and language:
            out[(slug, language)] = json.loads(path.read_text(encoding="utf-8"))
    return out


def guides() -> dict[tuple[str, str], dict]:
    """``{(slug, language): guide}`` for every file in ``DATA_DIR``."""
    return _load(str(DATA_DIR))


def guide_for(slug: str, language: str) -> dict | None:
    """The guide written for one edition, or ``None``."""
    return guides().get((slug, language))


def guide_editions() -> set[tuple[str, str]]:
    """Every ``(slug, language)`` that has a guide file."""
    return set(guides())


def chapter_extras(body_html: str) -> dict[str, str]:
    """The opening verse and closing prayer a young-reader chapter carries.

    The convention in these books: the body opens with a ``<blockquote>`` (the
    chapter's verse) and closes with a paragraph wrapped entirely in ``<em>``
    (the prayer). Either is ``""`` when the chapter does not follow it — a
    last paragraph with only an emphasised phrase in it is prose, not a prayer.
    """
    soup = BeautifulSoup(body_html or "", "html.parser")
    blocks = [el for el in soup.contents if getattr(el, "name", None)]
    verse = html_to_text(str(blocks[0])) if blocks and blocks[0].name == "blockquote" else ""
    prayer = ""
    if blocks and blocks[-1].name == "p":
        children = [
            c for c in blocks[-1].contents if getattr(c, "name", None) or str(c).strip()
        ]
        if len(children) == 1 and getattr(children[0], "name", None) == "em":
            prayer = html_to_text(str(children[0]))
    return {"verse": verse, "prayer": prayer}


def _strings(value) -> list[str]:
    """Every string anywhere inside a parsed JSON value."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _filled(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def problems(guide, chapter_orders: list[int]) -> list[str]:
    """What is wrong with one guide against its edition's chapter orders.

    ``[]`` for a guide that covers every chapter exactly once, in order, with
    every field filled and no markup anywhere (the page renders it escaped).
    """
    if not isinstance(guide, dict):
        return ["the file is not a JSON object"]
    out = []
    intro = guide.get("intro")
    if not (isinstance(intro, list) and intro and all(_filled(p) for p in intro)):
        out.append("intro must be a non-empty list of non-empty strings")
    weeks = guide.get("weeks")
    if not isinstance(weeks, list):
        return [*out, "weeks must be a list"]
    orders = [w.get("chapter") if isinstance(w, dict) else None for w in weeks]
    if orders != list(chapter_orders):
        out.append(
            f"weeks cover chapters {orders}, the edition has {list(chapter_orders)}"
        )
    for i, week in enumerate(weeks, 1):
        if not isinstance(week, dict):
            out.append(f"week {i} is not an object")
            continue
        verse = week.get("memory_verse") or {}
        activity = week.get("activity") or {}
        steps = activity.get("steps") if isinstance(activity, dict) else None
        checks = {
            "summary": _filled(week.get("summary")),
            "memory_verse.text": isinstance(verse, dict) and _filled(verse.get("text")),
            "memory_verse.reference": isinstance(verse, dict)
            and _filled(verse.get("reference")),
            "activity.title": isinstance(activity, dict)
            and _filled(activity.get("title")),
            "activity.materials": isinstance(activity, dict)
            and _filled(activity.get("materials")),
            f"activity.steps ({MIN_STEPS}–{MAX_STEPS})": isinstance(steps, list)
            and MIN_STEPS <= len(steps) <= MAX_STEPS
            and all(_filled(s) for s in steps),
        }
        out.extend(
            f"week {i}: {name} missing or empty"
            for name, ok in checks.items()
            if not ok
        )
    tagged = sorted({s[:60] for s in _strings(guide) if _TAG.search(s)})
    out.extend(f"HTML in: {s!r}" for s in tagged)
    return out
