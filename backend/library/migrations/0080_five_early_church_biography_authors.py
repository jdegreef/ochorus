"""Create five early-church biography-only authors on already-seeded databases.

Clement of Rome, Ignatius of Antioch, Cyprian of Carthage, Athanasius of
Alexandria and John Chrysostom join the Biographies section with a short
``bio`` card summary and a long-form ``bio_html``. They have no books or
sermons yet, so none of the content seeds reach them: ``seed_books`` and
``seed_sermons`` create authors only as a side effect of importing a work,
and ``seed_if_empty`` populates a fresh database only.

Same shape as ``0053_three_new_biography_authors`` (Augustine, Haynes, Law):
read the committed fixture — the source of truth — and create the missing
rows on the live DB.

Two guards, both carried over from 0053:

- Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the
  Book table) right after migrations run, and loaddata would then collide by
  slug with rows created here. So act only on an already-seeded DB.
- ``get_or_create`` means an author that somehow already exists keeps its
  prose untouched; re-runs are no-ops.

Note on ``birth_year``: every date here is approximate, and Clement's is not
known at all — the conventional c. 35 is used because the biographies shelf
buckets writers by birth year (``eras.ts``) and a null lands a first-century
bishop in the "Contemporary" era. The bios say plainly that the dates are the
tradition's estimate.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {
    "clement-of-rome",
    "ignatius-of-antioch",
    "cyprian-of-carthage",
    "athanasius-of-alexandria",
    "john-chrysostom",
}


def create_authors(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Book = apps.get_model("library", "Book")

    # Fresh install → the fixture seeding that follows migrate supplies these
    # rows directly; creating them here first would collide on slug.
    if not Book.objects.exists():
        return

    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return  # fixture missing/unreadable — nothing to create

    for row in rows:
        if row.get("model") != "library.author":
            continue
        f = row["fields"]
        if f.get("slug") not in NEW_SLUGS:
            continue
        Author.objects.get_or_create(
            slug=f["slug"],
            defaults={
                "name": f.get("name", ""),
                "bio": f.get("bio", ""),
                "bio_html": f.get("bio_html", ""),
                "photo_url": f.get("photo_url", ""),
                "birth_year": f.get("birth_year"),
                "death_year": f.get("death_year"),
                "original_language": f.get("original_language", "en"),
                "is_imprint": f.get("is_imprint", False),
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0079_admin_action_rls"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
