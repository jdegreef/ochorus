"""The split content-fixture layout (Stage 2 of the fixture architecture).

Content lives under ``library/fixtures/content/`` as one file per WORK, in
natural-key format (no integer pks — see Stage 1 / ``tests_fixture``):

    content/
      authors.json                    all Author rows (low churn, shared)
      books/<slug>.<language>.json    one Book row followed by its Chapters
      sermons/<slug>.<language>.json  one Sermon row
      plans.json                      Plan rows, each followed by its PlanDays

Why per work: parallel sessions add content constantly; separate files make
concurrent additions conflict-free by construction and diffs reviewable (a new
translation is one new file, not a 300-line splice into a 50 MB tail).

LOAD ORDER MATTERS. Every FK here is NOT NULL, and Django's forward-reference
deferral cannot bridge that — so ``ordered_fixture_paths()`` is the one source
of truth for ordering (authors first, then books, sermons, plans) and
``seed_if_empty`` passes ALL files to a single ``loaddata`` call in that order.
Within a book file the Book row precedes its Chapters; within plans.json each
Plan precedes its PlanDays.
"""

from __future__ import annotations

import json
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "fixtures" / "content"

AUTHORS_FILE = CONTENT_DIR / "authors.json"
BOOKS_DIR = CONTENT_DIR / "books"
SERMONS_DIR = CONTENT_DIR / "sermons"
PLANS_FILE = CONTENT_DIR / "plans.json"


def work_filename(slug: str, language: str) -> str:
    """``<slug>.<language>.json`` — slugs are [a-z0-9-], so ``.`` is safe."""
    return f"{slug}.{language}.json"


def ordered_fixture_paths() -> list[Path]:
    """Every content fixture file, in the only order loaddata can load them."""
    paths: list[Path] = []
    if AUTHORS_FILE.exists():
        paths.append(AUTHORS_FILE)
    for d in (BOOKS_DIR, SERMONS_DIR):
        if d.is_dir():
            paths.extend(sorted(d.glob("*.json")))
    if PLANS_FILE.exists():
        paths.append(PLANS_FILE)
    return paths


def load_all_rows() -> list[dict]:
    """All content rows across the split layout, in load order.

    The drop-in replacement for ``json.loads(launch.json)`` — the seed commands
    and the CI gate consume this.
    """
    rows: list[dict] = []
    for path in ordered_fixture_paths():
        rows.extend(json.loads(path.read_text()))
    return rows


def rows_by_file() -> dict[Path, list[dict]]:
    """Per-file rows, for checks that validate file-content coherence."""
    return {p: json.loads(p.read_text()) for p in ordered_fixture_paths()}
