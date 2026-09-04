"""Create eight "Men & Women Who Gave Everything" figures as biography-only authors.

William Carey, David Livingstone, Pandita Ramabai, C.T. Studd, John Stott, Helen
Roseveare, Jim Elliot and Elisabeth Elliot each appear as a CHAPTER in
``men-and-women-who-gave-everything-2`` (attributed to ``ochorus-originals`` —
they did not write it), so no content seed reaches them: ``seed_books`` /
``seed_sermons`` create authors only as a side effect of importing a work of
their own, and ``seed_if_empty`` populates a fresh database only. Without this
migration the author pages never exist on a live install.

Same shape and guards as ``0104`` / ``0110_women``: act only on an already-seeded
DB (a fresh install's ``seed_if_empty`` loaddata supplies these rows and would
collide by slug), and ``get_or_create`` so a re-run is a no-op. Re-check the leaf
against origin/main before pushing and COMMIT any rename (see write-biography).
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

NEW_SLUGS = {
    "william-carey",
    "david-livingstone",
    "pandita-ramabai",
    "c-t-studd",
    "john-stott",
    "helen-roseveare",
    "jim-elliot",
    "elisabeth-elliot",
}


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
        ("library", "0110_women_biography_authors"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
