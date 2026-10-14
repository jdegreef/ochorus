"""Create twelve biography-only authors: a second batch of voices of colour.

Phillis Wheatley, Old Elizabeth, Catherine Ferguson, Mary Prince, Nancy
Prince, Harriet Tubman, Tiyo Soga, Pastor Hsi, Virginia W. Broughton,
Krupabai Satthianadhan, Dora Yu and Mary Stone arrive with a biography but no
work of their own yet. ``seed_books`` / ``seed_sermons`` create authors only as
a side effect of importing a work, so without this migration their pages never
exist on a live install.

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

NEW_SLUGS = {
    "phillis-wheatley",
    "old-elizabeth",
    "catherine-ferguson",
    "mary-prince",
    "nancy-prince",
    "harriet-tubman",
    "tiyo-soga",
    "pastor-hsi",
    "virginia-broughton",
    "krupabai-satthianadhan",
    "dora-yu",
    "mary-stone",
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
        ("library", "0200_remove_the_marriage_tie"),
    ]

    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]
