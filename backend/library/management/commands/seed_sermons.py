"""Upsert the fixture's sermons into an already-seeded database.

``seed_if_empty`` only populates a *fresh* database, so sermons added to the
committed fixture never reach an existing production DB on their own. This
command reads that same fixture and upserts every sermon row — new sermons are
created, changed ones (e.g. an excerpt replaced by the full text) are updated,
untouched ones are left alone. Runs on every deploy (see the release command);
idempotent, and the fixture stays the single source of truth.

Follows the pattern of migration 0005_backfill_bios_and_sermons, but as a
release step so future sermon batches ship with just a fixture regen — no new
migration each time.
"""

from __future__ import annotations

import datetime
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.author_sync import sync_all_authors
from library.content_fixtures import AUTHORS_FILE, authors_by_slug, iter_work_files
from library.corrections import settled_sermon_body
from library.management.commands.seed_books import require_natural_format
from library.models import Author, Sermon

# `word_count` is deliberately absent: `Sermon.save()` derives it from
# body_html, so a fixture row does not get to assert it. Listing it here made
# the seed compare a derived column against a stored one and "repair" it on
# every deploy — a full-row UPDATE plus a tsvector rebuild for 33 sermons,
# forever, because save() immediately derived the value straight back.
SERMON_FIELDS = (
    "title",
    "scripture_ref",
    "summary",
    # Fixture-owned like `summary` — AI-drafted off-server and shipped in the
    # fixture, no live-DB workflow edits it, so it updates from the fixture on
    # every deploy (not create-only). A plain list, so save() derives nothing.
    "study_questions",
    "body_html",
    "source_type",
    "source_url",
    # Fixture-owned rights/credit note like `summary`; no live-DB workflow edits
    # it, so it updates from the fixture on every deploy (not create-only).
    "attribution",
    "sort_order",
    "is_published",
)

# Seeded when the row is first created, then owned by workflows that act on the
# live DB. approve_sermon_translation flips ai_unreviewed -> ai_reviewed, and an
# urgent unpublish happens directly in the DB; re-asserting the fixture's value
# on every deploy would silently walk either back (re-gating an approved
# translation, or resurrecting a pulled sermon).
CREATE_ONLY_FIELDS = frozenset({"source_type", "is_published"})
UPDATE_FIELDS = tuple(f for f in SERMON_FIELDS if f not in CREATE_ONLY_FIELDS)


def _date(value):
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value or None


def fixture_fields(f: dict) -> dict:
    """One fixture sermon's fields, with ``body_html`` in its settled form.

    The release corrects the stored prose and then runs this seed, so comparing
    the RAW fixture body compared uncorrected against corrected and the two
    steps fought over the same sermon forever — see `corrections.py`, which
    spells it out.

    Correcting here rather than regenerating the fixture closes the class
    instead of the instance: a correction added tomorrow costs one deploy to
    apply and then settles, with no regen needed to stop the churn. The fixture
    stays the source of truth for the prose, `corrections.py` for the repairs.

    Settling is eager here, where `chapter_drift` is lazy: 118 sermons cost 33ms
    a deploy, so the single-expression helper is worth it, while settling 3,218
    chapters up front to answer a report-only question would cost 800ms.
    """
    # `if k in f` guards run through this module for fields an older
    # serialization may predate; keep the same discipline here.
    if "body_html" not in f:
        return f
    return {**f, "body_html": settled_sermon_body(f["slug"], f["body_html"])}


class Command(BaseCommand):
    help = "Upsert the fixture's sermons into an existing DB (deploy step)."

    # Atomic like seed_books: a CommandError on a dangling author reference, or
    # any mid-loop DB error, must not leave prod with a half-synced author set.
    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author_rows = json.loads(AUTHORS_FILE.read_text())
        except OSError:
            self.stdout.write("No content fixtures available — nothing to seed.")
            return
        # A ValueError (corrupt file) propagates: "one file is broken" must abort
        # the deploy, not seed a partial library.

        require_natural_format(author_rows, "seed_sermons")
        # Natural-key join: a sermon's author is referenced as ["slug"].
        author_fields_by_slug = authors_by_slug(author_rows)

        created = updated = 0
        # Stream one work file at a time so peak memory is a single file, not the
        # whole ~170 MB fixture parsed into Python objects at once.
        for _path, rows in iter_work_files():
            require_natural_format(rows, "seed_sermons")
            for row in rows:
                if row.get("model") != "library.sermon":
                    continue
                f = fixture_fields(row["fields"])
                af = author_fields_by_slug.get(f["author"][0])
                if af is None:
                    # Forbidden by the CI integrity test — a corrupt fixture must
                    # abort the deploy, not silently drop the sermon.
                    raise CommandError(
                        f"seed_sermons: sermon {f['slug']!r} references missing "
                        f"author {f['author'][0]!r}"
                    )
                # A sermon may introduce an author with no books yet (e.g. Moody)
                # — create the author from the fixture rather than skipping it.
                author, _ = Author.objects.get_or_create(
                    slug=af["slug"],
                    defaults={
                        "name": af.get("name", ""),
                        "bio": af.get("bio", ""),
                        "bio_html": af.get("bio_html", ""),
                        "photo_url": af.get("photo_url", ""),
                        "birth_year": af.get("birth_year"),
                        "death_year": af.get("death_year"),
                        # Every fixture author is "en" today, so omitting this was
                        # invisible; a non-English author created on prod would
                        # have silently taken the model default and mis-fed
                        # _localized().
                        "original_language": af.get("original_language", "en"),
                        # Carry the flag through — see seed_books for why.
                        "is_imprint": af.get("is_imprint", False),
                    },
                )

                sermon = Sermon.objects.filter(
                    slug=f["slug"], language=f.get("language", "en")
                ).first()
                preached_on = _date(f.get("preached_on"))
                if sermon is None:
                    Sermon.objects.create(
                        author=author,
                        slug=f["slug"],
                        language=f.get("language", "en"),
                        preached_on=preached_on,
                        # Omit fields the fixture row doesn't carry so the model
                        # default applies — e.g. older rows predating source_type.
                        **{k: f[k] for k in SERMON_FIELDS if k in f},
                    )
                    created += 1
                    continue

                changed = [
                    k for k in UPDATE_FIELDS if k in f and getattr(sermon, k) != f[k]
                ]
                if sermon.preached_on != preached_on:
                    sermon.preached_on = preached_on
                    changed.append("preached_on")
                if sermon.author_id != author.id:
                    sermon.author = author
                    changed.append("author")
                if changed:
                    for k in changed:
                        if k in SERMON_FIELDS:
                            setattr(sermon, k, f.get(k))
                    sermon.save()  # save() re-derives body_text and word_count
                    updated += 1

        if created or updated:
            self.stdout.write(
                self.style.SUCCESS(f"Sermons: {created} created, {updated} updated.")
            )
        else:
            self.stdout.write("Sermons already up to date.")

        for line in sync_all_authors(Author, author_rows):
            self.stdout.write(line)
