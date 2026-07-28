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

# Fill-only. `bio` has its own rule above.
#
# CAVEAT: "empty" is treated as "never set", but an admin CLEARING a field in
# /superepic/ is also a decision — pull a portrait after a rights complaint and
# the next deploy writes the fixture's URL straight back. Clear it in
# `authors.json` too, which is where the fixture-is-source-of-truth rule already
# points. (`seed_books.CREATE_ONLY_FIELDS` protects the analogous unpublish case
# by never re-asserting at all; that is not an option here, since filling a gap
# on an existing row is the whole point of this module.)
#
# `name` is deliberately absent, but NOT because anything else syncs it —
# `upsert_book` does update it, and imports never run on a deploy, so a name
# correction in the fixture still needs a migration. It is excluded because a
# rename is a decision the catalog side owns.
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
        text.strip()
        for text in (
            *(e.bio for e in AUTHORS.values()),
            *(e.bio for e in SERMON_AUTHORS.values()),
            *RETIRED_STUBS,
        )
        if text.strip()
    )


def mark_translations_stale(author) -> list[str]:
    """Flag this author's short-bio translations as describing superseded text.

    Returns the languages flagged. When the English `bio` is replaced, every
    translation of it describes text that no longer exists, and nothing else
    records that.

    Sets `source_stale`, NOT `reviewed=False`. Clearing `reviewed` is the
    obvious-looking move and it destroys data: `seed_author_translations` treats
    `reviewed` as "an approver owns this wording, don't overwrite it", and it
    runs LATER in the same release (`release.py`: seed_books → seed_sermons →
    seed_author_translations). So a re-gated row loses its protection and the
    approver's wording is replaced by the repo's AI text, in the same deploy,
    silently. Verified before this was written. The two facts are independent:
    a translation can be both approved and stale.

    Only rows with a non-empty `bio` are flagged, and already-flagged rows are
    skipped, so re-runs write nothing. Readers see no change; the flag surfaces
    on the founder dashboard and in the deploy log. Nothing re-translates on its
    own — `translate_author` still needs `--force`.

    SCOPE: only the deploy-time sync flags. A bio replaced by a data migration
    or hand-edited in /superepic/ still moves out from under its translations
    unflagged. Deriving staleness rather than asserting it (an md5 of the
    English a translation was made from, per `0052_site_bio_expansions`' anchor
    pattern) would close that too, at the cost of writes in
    translate_author/seed_author_translations.
    """
    from library.models import AuthorTranslation

    stale = AuthorTranslation.objects.filter(
        author=author, source_stale=False
    ).exclude(bio="")
    languages = sorted(stale.values_list("language", flat=True))
    if languages:
        stale.update(source_stale=True)
    return languages


def sync_author(author, fields: dict) -> tuple[list[str], list[str]]:
    """Update ``author`` from a fixture author row.

    Returns ``(fields changed, translation languages flagged stale)``. ``fields`` is
    the ``"fields"`` dict of a ``library.author`` fixture row. Saves only when
    something actually changed.
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

    if not changed:
        return [], []
    author.save(update_fields=changed)
    # Only the short bio has translations keyed to it; filling an empty
    # bio_html/photo_url invalidates nothing.
    stale = mark_translations_stale(author) if "bio" in changed else []
    return changed, stale


def sync_all_authors(Author, rows: list[dict]) -> list[str]:
    """Sync EVERY existing author the fixture describes.

    Returns one ``~ author <slug> (...)`` deploy-log line per author actually
    changed — both seed commands print exactly this, so the wording lives here
    rather than half in each command.

    Deliberately not driven off the book/sermon loops: 9 of the 36 fixture
    authors have neither (the biography-only ones — Augustine, Lemuel Haynes,
    William Law et al., exactly what migration 0053 added), so a per-work sync
    would silently never reach a quarter of the library, which is the same
    "looks green, prod unchanged" failure this module exists to end.

    Only updates rows that already exist — creating a missing author is the
    seeds' job, and doing it here would resurrect one deliberately deleted.
    """
    from library.content_fixtures import authors_by_slug

    fixture = authors_by_slug(rows)
    lines: list[str] = []
    for author in Author.objects.filter(slug__in=fixture).order_by("slug"):
        fields, stale = sync_author(author, fixture[author.slug])
        if not fields:
            continue
        summary = ", ".join(fields)
        if stale:
            # Loud on purpose: nothing re-translates automatically, so this line
            # in the deploy log is the only notice that these languages now
            # describe superseded English.
            summary += f" — {'/'.join(stale)} translation(s) now stale"
        lines.append(f"  ~ author {author.slug} ({summary})")
    return lines
