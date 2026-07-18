"""Backfill long-form author bios (``bio_html``) and sermons into existing DBs.

``seed_if_empty`` only populates a *fresh* database, so the ``bio_html`` and
``Sermon`` rows added to the fixture never reach an already-seeded production DB.
This one-off migration reads that same committed fixture and upserts the rich
bios and sermons onto the live rows, idempotently — the fixture stays the single
source of truth, and fresh installs (which load it directly) are unaffected.

Written generically: every author with a ``bio_html`` and every sermon in the
fixture is applied, so the next batch of bios/sermons ships the same way.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from django.db import migrations

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "launch.json"


def _date(value):
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value or None


def backfill(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Sermon = apps.get_model("library", "Sermon")

    try:
        rows = json.loads(FIXTURE.read_text())
    except (OSError, ValueError):
        return  # no fixture available — nothing to backfill

    if rows and "pk" not in rows[0]:
        # Natural-key-format fixture: this historical backfill's content is
        # already in the fixture the seeds load — no-op (see content_sync).
        print("0005: natural-key fixture detected — historical backfill skipped")
        return

    # Fixture FKs are by pk; map author pk -> slug to resolve the live rows.
    pk_to_slug: dict[int, str] = {}

    for row in rows:
        if row.get("model") != "library.author":
            continue
        f = row["fields"]
        pk_to_slug[row["pk"]] = f["slug"]
        bio = f.get("bio_html") or ""
        if not bio:
            continue
        author = Author.objects.filter(slug=f["slug"]).first()
        if not author:
            continue
        changed = []
        if author.bio_html != bio:
            author.bio_html = bio
            changed.append("bio_html")
        if not author.birth_year and f.get("birth_year"):
            author.birth_year = f["birth_year"]
            changed.append("birth_year")
        if not author.death_year and f.get("death_year"):
            author.death_year = f["death_year"]
            changed.append("death_year")
        if changed:
            author.save(update_fields=changed)

    for row in rows:
        if row.get("model") != "library.sermon":
            continue
        f = row["fields"]
        slug = pk_to_slug.get(f.get("author"))
        author = Author.objects.filter(slug=slug).first() if slug else None
        if not author:
            continue
        Sermon.objects.update_or_create(
            slug=f["slug"],
            language=f.get("language", "en"),
            defaults={
                "author": author,
                "title": f.get("title", ""),
                "scripture_ref": f.get("scripture_ref", ""),
                "preached_on": _date(f.get("preached_on")),
                "body_html": f.get("body_html", ""),
                "word_count": f.get("word_count", 0),
                "source_url": f.get("source_url", ""),
                "sort_order": f.get("sort_order", 0),
                "is_published": f.get("is_published", True),
            },
        )


def noop(apps, schema_editor):
    # Not reversible — we don't retain the prior (empty) bio/sermon state.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0004_author_bio_html_sermon"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
