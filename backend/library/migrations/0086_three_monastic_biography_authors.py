"""Create three monastic biography-only authors on already-seeded databases.

John Cassian, Anselm of Canterbury and Bernard of Clairvaux join the
Biographies section with a short ``bio`` card summary and a long-form
``bio_html``. They have no books or sermons yet, so none of the content seeds
reach them: ``seed_books`` and ``seed_sermons`` create authors only as a side
effect of importing a work, and ``seed_if_empty`` populates a fresh database
only.

Third in the series after ``0053`` (Augustine, Haynes, Law) and ``0080``
(the five early-church writers); same two guards as both:

- Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the
  Book table) right after migrations run, and loaddata would then collide by
  slug with rows created here. So act only on an already-seeded DB.
- ``get_or_create`` means an author that somehow already exists keeps its
  prose untouched; re-runs are no-ops.

Unlike 0080 this one also carries ``same_as`` (added in ``0081``), so the
Person markup on these pages has its Wikipedia/Wikidata identifiers from the
first deploy rather than needing a later backfill.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {
    "john-cassian",
    "anselm-of-canterbury",
    "bernard-of-clairvaux",
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
                "same_as": f.get("same_as", []),
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0085_rederive_body_text"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
