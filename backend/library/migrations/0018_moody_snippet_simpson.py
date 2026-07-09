"""Backfill the expanded Moody snippet (and any other bio/sermon fixture
changes) onto existing databases.

A. B. Simpson himself (author + 3 books + 4 sermons) arrives via the
``seed_books`` / ``seed_sermons`` release steps; this migration covers the
updated fields on EXISTING rows — Moody's three-sentence short bio (the
biographies-page snippet), via ``library.content_sync``, whose short-bio sync
now follows the fixture when values differ (previously only when empty).
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
        ("library", "0017_backfill_moody_bio"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
