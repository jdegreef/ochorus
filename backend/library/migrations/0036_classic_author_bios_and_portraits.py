"""Backfill long-form bios and portraits for the six classic authors.

Bunyan, Watson, Baxter, Edwards, Whitefield and Wesley were added to the
library by an earlier fixture change, but ``seed_books`` only CREATES missing
books and authors — it never updates rows that already exist. Production is
never re-seeded, so their ``bio_html`` and ``photo_url`` would otherwise stay
empty on the live rows while fresh installs (which loaddata the fixture) got
them. This re-applies the fixture's author prose and portraits to the live
rows. Idempotent — see ``library.content_sync``.
"""

from __future__ import annotations

from django.db import migrations


def backfill(apps, schema_editor):
    from library.content_sync import backfill_bios_and_sermons

    backfill_bios_and_sermons(apps)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0035_sermon_source_type"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
