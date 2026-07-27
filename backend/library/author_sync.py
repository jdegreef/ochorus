"""Bring an existing Author row up to date with ``content/authors.json``.

THE GAP THIS CLOSES. Both seed commands create authors with ``get_or_create``,
so everything about an author is create-only: whatever the row held the first
time it appeared is what production keeps. Nothing else re-asserts the fixture
either — ``content_sync.backfill_bios_and_sermons`` reads the retired
``launch.json`` and no-ops on the natural-key fixture, and migration 0049 fills
only rows whose bio is ``""``. So an author first created by an *import* keeps
the one-line stub from ``catalog.py`` forever, and writing their real biography
into ``authors.json`` afterwards never reaches the live site. Every author bio
that has ever needed correcting in production has therefore shipped as a
hand-written per-author data migration (0049, 0051, 0052, 0053).

WHAT IT WILL AND WON'T OVERWRITE. Blind-syncing the fixture over the row would
close the gap and also silently revert reviewed prose, so this follows the rule
``0052_site_bio_expansions`` established: only replace text we know we
generated ourselves. A short ``bio`` is replaced when the row is empty or still
holds a verbatim ``catalog.py`` stub; anything else — a hand edit, an AI bio
that a native speaker approved, a newer deploy — always wins. The remaining
fields are fill-only: they move ``""``/``None`` to the fixture's value and never
overwrite. Re-runs are no-ops, so this is safe on every deploy.
"""

from __future__ import annotations

# Filled lazily: importing the catalogs at module import time would drag
# `library.catalog` into every consumer of this module.
_STUBS: frozenset[str] | None = None

# Fill-only. `bio` is handled separately (it has the stub rule); `name` is not
# synced at all — `upsert_book` already keeps it current, and it is the one
# field a rename is supposed to change from the catalog side.
FILL_ONLY_FIELDS = ("bio_html", "photo_url", "birth_year", "death_year")


def catalog_stubs() -> frozenset[str]:
    """Every one-line bio the catalogs can plant on a newly created author."""
    global _STUBS
    if _STUBS is None:
        from library.catalog import AUTHORS
        from library.sermon_catalog import SERMON_AUTHORS

        _STUBS = frozenset(
            e.bio.strip()
            for e in (*AUTHORS.values(), *SERMON_AUTHORS.values())
            if e.bio.strip()
        )
    return _STUBS


def sync_author(author, fields: dict) -> list[str]:
    """Update ``author`` from a fixture author row. Returns the fields changed.

    ``author`` is a live model instance (or the historical model inside a
    migration); ``fields`` is the ``"fields"`` dict of a ``library.author``
    fixture row. Saves only when something actually changed.
    """
    changed: list[str] = []

    fixture_bio = (fields.get("bio") or "").strip()
    live_bio = (author.bio or "").strip()
    if fixture_bio and fixture_bio != live_bio:
        # Empty, or still the placeholder an import planted — ours to replace.
        if not live_bio or live_bio in catalog_stubs():
            author.bio = fixture_bio
            changed.append("bio")

    for field in FILL_ONLY_FIELDS:
        value = fields.get(field)
        if value and not getattr(author, field, None):
            setattr(author, field, value)
            changed.append(field)

    if changed:
        author.save(update_fields=changed)
    return changed
