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
from pathlib import Path

from django.core.management.base import BaseCommand

from library.models import Author, Sermon

FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "launch.json"

SERMON_FIELDS = (
    "title",
    "scripture_ref",
    "body_html",
    "word_count",
    "source_url",
    "sort_order",
    "is_published",
)


def _date(value):
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value or None


class Command(BaseCommand):
    help = "Upsert the fixture's sermons into an existing DB (deploy step)."

    def handle(self, *args, **opts):
        try:
            rows = json.loads(FIXTURE.read_text())
        except (OSError, ValueError):
            self.stdout.write("No fixture available — nothing to seed.")
            return

        author_fields_by_pk = {
            r["pk"]: r["fields"]
            for r in rows
            if r.get("model") == "library.author"
        }

        created = updated = 0
        for row in rows:
            if row.get("model") != "library.sermon":
                continue
            f = row["fields"]
            af = author_fields_by_pk.get(f["author"])
            if af is None:
                continue
            # A sermon may introduce an author with no books yet (e.g. Moody) —
            # create the author from the fixture rather than skipping the sermon.
            author, _ = Author.objects.get_or_create(
                slug=af["slug"],
                defaults={
                    "name": af.get("name", ""),
                    "bio": af.get("bio", ""),
                    "bio_html": af.get("bio_html", ""),
                    "birth_year": af.get("birth_year"),
                    "death_year": af.get("death_year"),
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
                    **{k: f.get(k) for k in SERMON_FIELDS},
                )
                created += 1
                continue

            changed = [
                k for k in SERMON_FIELDS if getattr(sermon, k) != f.get(k)
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
                sermon.save()  # save() re-derives body_text
                updated += 1

        if created or updated:
            self.stdout.write(
                self.style.SUCCESS(f"Sermons: {created} created, {updated} updated.")
            )
        else:
            self.stdout.write("Sermons already up to date.")
