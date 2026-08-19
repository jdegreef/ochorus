"""Localized plan prose — one file per language, loaded from ``data/``.

A plan's title and description are the only part of it that is translated: the
days reference books by slug and resolve to that language's book rows at read
time, so a plan translation is prose and nothing else.

**Why one file per language.** This was a single ``PLAN_TRANSLATIONS`` dict in
``seed_plans``, which made every plan job in every language a writer of the same
file. The translation-worker conflict gate had to serialise them all against
each other — and, because a book that backs a plan must add its plan prose in
the same PR (see below), it serialised book jobs against plan jobs too. That
was the subtlest rule in the queue's playbook and the one that had actually bitten.
Splitting by language deletes the cross-language half of it: jobs in different
languages now touch different files and cannot collide.

**The rule that has bitten twice, unchanged by this move.** ``seed_plans``
creates a Plan row per language in which the source books are published, so
shipping a BOOK is what creates the plan. A plan whose language has no entry
here is therefore not merely untranslated — before the guard in ``_prose`` it
took the ENGLISH tuple and published an English-titled card (PR #819 put
"Humility in 12 Days" on the Arabic plans page). So an entry lands in the SAME
PR as the book that would create its row. ``PlanTranslationCoverageTests``
fails any book that would create a row with no prose in its language.

**Entries may ship ahead of their books, and often should.** A curated plan
needs EVERY source book present in the language, so prose written before the
last book arrives sits dormant and correct — and the row cannot appear
English-titled the moment that book lands. Several entries here are deliberately
waiting.

File format, ``data/plan_translations/<language>.json``::

    {
      "<plan slug>": {
        "title": "...",
        "description": "...",
        "note": ["why this wording", "..."]     // optional, any number of paragraphs
      }
    }

``note`` carries the editorial reasoning that used to live in comments beside
each tuple: which shipped book title a card is quoting, which queue job wrote
it, and what a later translator must keep in step. It is data rather than a
comment on purpose — a comment can drift away from the entry it describes, and
one already had (the note for the Swahili ``deeper-life-in-christ`` sat above a
different plan).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "plan_translations"


@lru_cache(maxsize=1)
def raw_plan_translations() -> dict[str, dict[str, dict]]:
    """``{language: {slug: entry}}`` — the files as written, notes included.

    A new language is picked up by dropping in its file; nothing here lists the
    languages, exactly as ``seed_author_translations`` globs its bio dirs. The
    only place that knows the layout, so the CI gate over these files reads them
    through this rather than globbing a second time.
    """
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(DATA_DIR.glob("*.json"))
    }


def plan_translations() -> dict[str, dict[str, tuple[str, str]]]:
    """``{language: {slug: (title, description)}}`` — what ``seed_plans`` needs.

    ``note`` is dropped here: it is editorial reasoning for whoever edits the
    entry next, not something a Plan row carries.
    """
    return {
        lang: {
            slug: (entry["title"], entry["description"])
            for slug, entry in entries.items()
        }
        for lang, entries in raw_plan_translations().items()
    }
