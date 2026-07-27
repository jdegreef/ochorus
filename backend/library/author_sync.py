"""Bring an existing Author row up to date with ``content/authors.json``.

Both seed commands create authors with ``get_or_create``, so every author field
was create-only: an author first created by an *import* kept the one-line stub
from ``catalog.py`` forever, and writing their real biography into the fixture
afterwards never reached the live site. See the book-import skill for the full
history (and which migrations had to paper over it).

THE RULE. Blind-syncing the fixture would close that gap and also silently
revert reviewed prose, so this only replaces text we know we generated: a
``bio`` that is empty or still a verbatim catalog stub. Anything else — a hand
edit, an approved translation, a newer deploy — wins. Everything in
``FILL_ONLY_FIELDS`` moves ``""``/``None`` to the fixture's value and never
overwrites. Re-runs are no-ops, so this is safe on every deploy.
"""

from __future__ import annotations

from functools import cache

# Fill-only. `bio` has its own rule above; `name` is not synced at all —
# `upsert_book` already keeps it current, and it is the one field a rename is
# supposed to change from the catalog side.
FILL_ONLY_FIELDS = ("bio_html", "photo_url", "birth_year", "death_year")

# Stub wordings that USED to be in the catalogs. A live row still carrying one
# is just as much a placeholder as a current stub — but string equality can't
# know that, so rewording a stub would strand every row holding the old text,
# permanently (nothing else upgrades a non-empty bio). Retiring a stub means
# moving its exact text here, not deleting it.
RETIRED_STUBS = (
    # sermon_catalog carried its own copies until they were aliased to
    # catalog.AUTHORS; these three are what `import_sermons` planted before that.
    "Canadian-born preacher and founder of the Christian and Missionary "
    'Alliance, whose "Fourfold Gospel" called readers past every '
    "blessing to Christ Himself.",
    "English Baptist preacher, the “Prince of Preachers,” whose sermons "
    "and devotional writings have been read by millions.",
    "American evangelist whose plain, warm gospel addresses reached "
    "millions across America and Britain; founder of the Moody Bible "
    "Institute.",
)


@cache
def catalog_stubs() -> frozenset[str]:
    """Every one-line bio the catalogs can plant on a newly created author."""
    # Imported lazily: `library.catalog` pulls in the whole book shelf, and this
    # module is imported by the seeds at deploy time.
    from library.catalog import AUTHORS
    from library.sermon_catalog import SERMON_AUTHORS

    return frozenset(
        text
        for text in (
            *(e.bio for e in AUTHORS.values()),
            *(e.bio for e in SERMON_AUTHORS.values()),
            *RETIRED_STUBS,
        )
        if text.strip()
    )


def sync_author(author, fields: dict) -> list[str]:
    """Update ``author`` from a fixture author row. Returns the fields changed.

    ``fields`` is the ``"fields"`` dict of a ``library.author`` fixture row.
    Saves only when something actually changed.
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
