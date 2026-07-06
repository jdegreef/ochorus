"""Backfill Gareth Evans's biography (and any other new fixture bios) onto
existing databases. Idempotent — see ``library.content_sync``.
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
        ("library", "0010_backfill_more_bios"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
