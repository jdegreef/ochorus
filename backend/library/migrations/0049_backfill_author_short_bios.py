"""Backfill short author ``bio`` prose onto existing databases.

Fresh installs load the fixture directly via ``seed_if_empty``; production is
never re-seeded, and ``content_sync.backfill_bios_and_sermons`` deliberately
no-ops on the natural-key fixture. So a short bio newly added to
``content/authors.json`` for an author who already exists in prod (here: the
contemporary contributors and R. A. Torrey) would otherwise never reach the
live row. This copies the fixture's short ``bio`` onto any live author whose
bio is still empty — it never overwrites existing prose, so it's safe to run
repeatedly and can't walk back a later hand/AI edit.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)


def backfill(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return
    for row in rows:
        if row.get("model") != "library.author":
            continue
        f = row.get("fields", {})
        bio = (f.get("bio") or "").strip()
        slug = f.get("slug")
        if not bio or not slug:
            continue
        # Fill only — never clobber a bio a later deploy/edit already set.
        Author.objects.filter(slug=slug, bio="").update(bio=bio)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0048_soar_self_hosted_pdf"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
