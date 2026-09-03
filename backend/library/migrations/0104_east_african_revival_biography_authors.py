"""Create seven East African Revival figures as biography-only authors.

Joe Church, Yosiya Kinuka, Blasio Kigozi, William Nagenda, Yona Kanamuzeyi,
Janani Luwum and Lawrence Barham each appear as a CHAPTER in the anthology
``tukutendereza`` (and some in ``men-who-moved-heaven`` / ``a-hidden-fire``), but
those books are attributed to ``ochorus-originals`` — they did not write them —
so no content seed reaches them: ``seed_books``/``seed_sermons`` create authors
only as a side effect of importing a work of their own, and ``seed_if_empty``
populates a fresh database only. Without this migration the author pages never
exist on a live install.

Same shape and guards as ``0100_erica_sabiti_biography_author`` (another Revival
figure created this way):

- Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the Book
  table) right after migrations run, and its loaddata would then collide by slug
  with a row created here. So act only on an already-seeded DB.
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

NEW_SLUGS = {
    "joe-church",
    "yosiya-kinuka",
    "blasio-kigozi",
    "william-nagenda",
    "yona-kanamuzeyi",
    "janani-luwum",
    "lawrence-barham",
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
        ("library", "0103_enchiridion_strip_duplicate_section_titles"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
