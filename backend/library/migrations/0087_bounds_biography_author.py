"""Create E. M. Bounds as a biography-only author on already-seeded databases.

Edward McKendree Bounds (1835–1913) joins the Biographies section with a short
``bio`` card summary and a long-form ``bio_html``. His one catalogued work,
``power-through-prayer``, is declared in ``library/catalog.py`` but has not been
imported yet, so no content seed reaches him: ``seed_books`` and
``seed_sermons`` create authors only as a side effect of importing a work, and
``seed_if_empty`` populates a fresh database only.

Fourth in the series after ``0053`` (Augustine, Haynes, Law), ``0080`` (the
five early-church writers) and ``0086`` (the three monastics); same two guards,
and it carries ``same_as`` as 0086 does so the Person markup has its
Wikipedia/Wikidata identifiers from the first deploy:

- Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the
  Book table) right after migrations run, and loaddata would then collide by
  slug with rows created here. So act only on an already-seeded DB.
- ``get_or_create`` means an author that somehow already exists keeps its
  prose untouched; re-runs are no-ops. That also makes this a no-op once
  Power Through Prayer is imported and ``seed_books`` creates the row itself.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {
    "e-m-bounds",
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
        ("library", "0086_three_monastic_biography_authors"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
