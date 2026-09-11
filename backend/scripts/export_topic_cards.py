#!/usr/bin/env python3
"""Emit topic share-card content as JSON — read by
``frontend/scripts/generate-topic-og.mjs``.

A topic's reader-facing text (title, description, scripture) lives in
``library/topic_seed.py``, a pure data module (its only import is
``from __future__ import annotations`` — no Django, no DB). The Open Graph
generator runs under Node with neither, so it cannot read Python; this bridges
the two by importing that module and printing

    { "<slug>": {title, description, scripture_ref, scripture_text}, ... }

sorted by slug, to stdout. Deterministic: same ``topic_seed.py`` in, same JSON
out. ``TopicShareCardTests`` recomputes the same strings straight off the
module to catch a card a title/description/scripture edit left stale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The Django-free-script pattern (see scripts/build_cover_assets.py): put the
# backend on the path and import the data module directly — topic_seed.py is
# side-effect-free, and covers.py already reads TOPICS this same way.
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.topic_seed import TOPIC_SCRIPTURE, TOPICS  # noqa: E402


def topic_cards() -> dict[str, dict[str, str]]:
    cards: dict[str, dict[str, str]] = {}
    for slug, title, description, _book_slugs in TOPICS:
        ref, text = TOPIC_SCRIPTURE.get(slug, ("", ""))
        cards[slug] = {
            "title": title,
            "description": description,
            "scripture_ref": ref,
            "scripture_text": text,
        }
    return dict(sorted(cards.items()))


if __name__ == "__main__":
    json.dump(topic_cards(), sys.stdout, ensure_ascii=False, indent="\t")
    sys.stdout.write("\n")
