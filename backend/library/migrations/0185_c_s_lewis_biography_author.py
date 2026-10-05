"""Create C. S. Lewis as a biography-only author.

Lewis's own books are still in copyright, so no content seed reaches him:
``seed_books`` / ``seed_sermons`` create authors only as a side effect of
importing a work of their own, and the Ochorus companions about him are by
``ochorus-originals``. Without this migration his author page never exists on a
live install.

Same shape and guards as ``0115_prayer_moderns_biography_authors``: act only on
an already-seeded DB (a fresh install's ``seed_if_empty`` loaddata supplies the
row and would collide by slug), and ``get_or_create`` so a re-run is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {"c-s-lewis"}


def create_authors(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Book = apps.get_model("library", "Book")

    if not Book.objects.exists():
        return

    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return

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
        ("library", "0184_adminaction_email_translation"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
