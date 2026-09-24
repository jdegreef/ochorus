"""Bring an existing Author row up to date with ``content/authors.json``.

Both seed commands create authors with ``get_or_create``, so every author field
was create-only: an author first created by an *import* kept the one-line stub
from ``catalog.py`` forever, and writing their real biography into the fixture
afterwards never reached the live site. See the book-import skill for the full
history (and which migrations had to paper over it).

THE RULE. The fixture is the source of truth for the English prose: a
non-empty ``bio`` or ``bio_html`` that differs from the live row replaces it
(``FIXTURE_WINS_TEXT``). Until 2026-09-23 both were fill-only — replaced only
when empty or a catalog stub, to protect hand edits in /superepic/ — and 29
authors' fixture fixes never shipped (#1920's card trims, #1855's "Holy
Spirit"). Edit a bio in ``authors.json``, never in the admin: the next deploy
writes the fixture back. A fixture that omits or empties either field leaves
the row alone (the seeds never blank prose). ``FILL_ONLY_FIELDS`` still move
``""``/``None`` to the fixture's value and never overwrite. Re-runs are
no-ops, so this is safe on every deploy.
"""

from __future__ import annotations

# Fixture-wins when the fixture carries text; never blanked (see THE RULE).
FIXTURE_WINS_TEXT = ("bio", "bio_html")

# Fill-only.
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
FILL_ONLY_FIELDS = ("photo_url", "birth_year", "death_year")

# Fixture-wins, unlike everything above, and the difference is deliberate.
#
# Fill-only exists to protect a human decision made in the admin. `same_as` has
# no such workflow — the identifiers are researched into `authors.json` and
# nothing else writes them — so the only thing fill-only would protect is a
# value already in the row, including a WRONG one. An identifier pointing at
# the wrong person is the failure this field has to be able to recover from,
# and a correction to the fixture has to reach production on the next deploy
# rather than needing a migration. So the fixture is the source of truth here,
# including when it clears the list.
#
# `faq` sits here for the same reason: the Q&A is researched into `authors.json`
# and nothing else writes it, so fill-only would only ever protect a value
# already in the row — including a thin or wrong one shipped in an earlier batch.
# During the roll-out we want a corrected or expanded set to reach production on
# the next deploy, and a row that OMITS the key (an author with no Q&A yet) is
# left untouched by the `field in fields` guard below, so nothing forces an empty
# list onto the ~85 authors without a set. If an admin Q&A editor is ever added,
# revisit this the way the fill-only caveat above describes.
SYNCED_FIELDS = ("same_as", "faq")

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

    for field in FIXTURE_WINS_TEXT:
        value = (fields.get(field) or "").strip()
        if value and value != (getattr(author, field, None) or "").strip():
            setattr(author, field, value)
            changed.append(field)

    for field in FILL_ONLY_FIELDS:
        value = fields.get(field)
        if value and not getattr(author, field, None):
            setattr(author, field, value)
            changed.append(field)

    for field in SYNCED_FIELDS:
        # `in fields` rather than a truth test: a fixture row that OMITS the key
        # (an older serialization) must be left alone, while one that carries an
        # empty list is deliberately clearing it.
        if field in fields and fields[field] != getattr(author, field, None):
            setattr(author, field, fields[field])
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
