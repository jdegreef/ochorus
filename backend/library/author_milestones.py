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
    "charles-h-spurgeon": [
        {"year": 1834, "label": "Born", "key": True},
        {"year": 1850, "label": "Converted"},
        {"year": 1861, "label": "Tabernacle", "key": True},
        {"year": 1892, "label": "Died", "key": True},
    ],
    "j-c-ryle": [
        {"year": 1816, "label": "Born", "key": True},
        {"year": 1841, "label": "Ordained"},
        {"year": 1880, "label": "Bishop", "key": True},
        {"year": 1900, "label": "Died", "key": True},
    ],
    "dwight-l-moody": [
        {"year": 1837, "label": "Born", "key": True},
        {"year": 1855, "label": "Converted"},
        {"year": 1873, "label": "Britain tours"},
        {"year": 1889, "label": "Bible Institute", "key": True},
        {"year": 1899, "label": "Died", "key": True},
    ],
    "george-whitefield": [
        {"year": 1714, "label": "Born", "key": True},
        {"year": 1739, "label": "Field preaching", "key": True},
        {"year": 1770, "label": "Died", "key": True},
    ],
    "hudson-taylor": [
        {"year": 1832, "label": "Born", "key": True},
        {"year": 1854, "label": "To China"},
        {"year": 1865, "label": "Founds CIM", "key": True},
        {"year": 1905, "label": "Died", "key": True},
    ],
    "william-carey": [
        {"year": 1761, "label": "Born", "key": True},
        {"year": 1793, "label": "To India", "key": True},
        {"year": 1834, "label": "Died", "key": True},
    ],
    "amy-carmichael": [
        {"year": 1867, "label": "Born", "key": True},
        {"year": 1895, "label": "To India"},
        {"year": 1901, "label": "Dohnavur", "key": True},
        {"year": 1951, "label": "Died", "key": True},
    ],
    "charles-finney": [
        {"year": 1792, "label": "Born", "key": True},
        {"year": 1821, "label": "Converted"},
        {"year": 1830, "label": "Revival", "key": True},
        {"year": 1851, "label": "Oberlin"},
        {"year": 1875, "label": "Died", "key": True},
    ],
}
