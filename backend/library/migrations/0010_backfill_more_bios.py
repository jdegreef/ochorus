"""Backfill the next batch of author biographies (and any new sermons) onto
existing databases from the committed fixture.

Fresh installs load the fixture directly via ``seed_if_empty``; production is
never re-seeded, so this re-applies the fixture's ``bio_html`` + sermons to the
live rows. Idempotent — see ``library.content_sync``.
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
        ("library", "0009_rechapterize_bio_collections"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
