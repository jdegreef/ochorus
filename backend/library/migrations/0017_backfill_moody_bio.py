"""Backfill D. L. Moody's long-form biography onto existing databases.

Fresh installs load the fixture directly via ``seed_if_empty``; production is
never re-seeded, so this re-applies the fixture's ``bio_html`` (+ any sermon
changes) to the live rows. Idempotent — see ``library.content_sync``.
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
        ("library", "0016_gareth_portrait"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
