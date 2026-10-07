#!/usr/bin/env python3
"""Export the painting credits the home hero shows under its framed picture.

    cd backend && python scripts/export_art_credits.py

The hero (frontend ``HomeHero.svelte``) hangs a painting from ``/covers/art/``
— the reader's current book's ground, or the season's — and labels it on the
mat like a gallery print: artist, title, year. Those words live in
``library/curated_art.py`` (verbatim from each museum, see the note above
``CURATED``), which the static frontend cannot read. So this writes them out
twice, the same bytes:

- ``library/data/art_credits.json`` — the backend's copy, which
  ``ArtCreditExportTests`` re-derives and compares, so an edit to an entry
  that forgot this script fails the backend suite;
- ``frontend/static/covers/art/credits.json`` — the served copy the hero
  fetches, which ``artCredits.test.ts`` holds byte-for-byte to the first.

Every curated entry with a known source is exported, in both tiers: a ground
is the same museum object under the same licence (``credit()`` says why).
``credit`` is ``credit()``'s line exactly, so the hero's tooltip and the book
page's credit never disagree. Django-free, like ``export_topic_cards.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.curated_art import CURATED, CURATED_GROUND, SOURCES, credit  # noqa: E402

OUT = BACKEND / "library" / "data" / "art_credits.json"
SERVED = BACKEND.parent / "frontend" / "static" / "covers" / "art" / "credits.json"


def art_credits() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for slug, art in {**CURATED, **CURATED_GROUND}.items():
        line = credit(slug)
        if art.source not in SOURCES or line is None:
            continue
        out[slug] = {
            "artist": art.artist,
            "title": art.title,
            "year": art.year,
            "credit": line,
        }
    return dict(sorted(out.items()))


def render() -> str:
    return json.dumps(art_credits(), ensure_ascii=False, indent="\t") + "\n"


if __name__ == "__main__":
    text = render()
    for path in (OUT, SERVED):
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(art_credits())} credits to {OUT} and {SERVED}")
