"""Hand-curated life-and-ministry milestones for the author-page timeline.

A first, deliberately small set: an author with milestones gets an event
timeline, everyone else keeps the plain lifespan bar, so this backfills a few
marquee lives without touching all ~90. Seeded by ``seed_author_milestones``
(a release step), which is the single source of truth — the code owns these,
so a deploy re-asserts them (mirrors ``seed_topics`` / ``topic_seed.py``).

Django-free on purpose (no imports of models), so tooling can read it too.

Each entry is ``{"year": int, "label": str, "key"?: bool}``. Dates are
hand-checked canonical facts, NOT derived from the bios — the page's promise is
trustworthy public-domain scholarship. ``key`` marks the turning points the
timeline emphasises. Labels are kept short so they don't collide on the axis;
keep new ones terse and the years comfortably spaced for the same reason.
"""

from __future__ import annotations

AUTHOR_MILESTONES: dict[str, list[dict]] = {
    "andrew-murray": [
        {"year": 1828, "label": "Born", "key": True},
        {"year": 1848, "label": "Ordained", "key": True},
        {"year": 1860, "label": "Revival", "key": True},
        {"year": 1871, "label": "Wellington"},
        {"year": 1917, "label": "Died", "key": True},
    ],
    "a-b-simpson": [
        {"year": 1843, "label": "Born", "key": True},
        {"year": 1865, "label": "Hamilton"},
        {"year": 1881, "label": "Healed", "key": True},
        {"year": 1887, "label": "Alliance", "key": True},
        {"year": 1919, "label": "Died", "key": True},
    ],
    "john-bunyan": [
        {"year": 1628, "label": "Born", "key": True},
        {"year": 1644, "label": "Army"},
        {"year": 1660, "label": "Imprisoned", "key": True},
        {"year": 1678, "label": "Pilgrim's Progress", "key": True},
        {"year": 1688, "label": "Died", "key": True},
    ],
    "george-muller": [
        {"year": 1805, "label": "Born", "key": True},
        {"year": 1836, "label": "Orphan houses", "key": True},
        {"year": 1875, "label": "World tours"},
        {"year": 1898, "label": "Died", "key": True},
    ],
    "a-w-tozer": [
        {"year": 1897, "label": "Born", "key": True},
        {"year": 1919, "label": "Ministry"},
        {"year": 1928, "label": "Chicago", "key": True},
        {"year": 1948, "label": "Pursuit of God", "key": True},
        {"year": 1963, "label": "Died", "key": True},
    ],
}
