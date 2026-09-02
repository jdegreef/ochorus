"""Create Erica Sabiti as a biography-only author on already-seeded databases.

Sabiti (1903–1988), the first African Archbishop of the Church of Uganda and a
leader of the East African Revival, joins the Biographies section with a short
``bio`` card summary and a long-form ``bio_html``.

He appears as a CHAPTER in ``tukutendereza``, but that book is attributed to
``ochorus-originals`` — he did not write it — so no content seed reaches him:
``seed_books``/``seed_sermons`` create authors only as a side effect of
importing a work of their own, and ``seed_if_empty`` populates a fresh database
only. Without this migration the author page never exists on a live install.

Same shape as ``0053_three_new_biography_authors``, and the same two guards:

- Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the
  Book table) right after migrations run, and its loaddata would then collide
  by slug with a row created here. So act only on an already-seeded DB.
- ``get_or_create`` means an author that somehow already exists keeps its prose
  untouched; re-runs are no-ops.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {"erica-sabiti"}


def create_authors(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Book = apps.get_model("library", "Book")

    # Fresh install → the fixture seeding that follows migrate supplies this
    # row directly; creating it here first would collide on slug.
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
        ("library", "0097_contentrevision_rls"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
