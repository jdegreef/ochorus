"""Create the seven new biography-only authors on already-seeded databases.

These authors have no books or sermons yet — they exist for the Biographies
section (``/authors/<slug>``): a short ``bio`` card summary and a long-form
``bio_html``. ``seed_if_empty`` loads them into fresh installs via the fixture,
but production is never re-seeded, so this migration reads that same committed
fixture and creates the missing rows on the live DB. Idempotent — an author
that already exists is left untouched (its bio is synced by ``content_sync``).

New this batch: Amanda Berry Smith, Samuel Ajayi Crowther, Richard Allen, Festo
Kivengere, Simeon Nsibambi, George Müller, and Hudson Taylor.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "launch.json"

NEW_SLUGS = {
    "amanda-berry-smith",
    "samuel-ajayi-crowther",
    "richard-allen",
    "festo-kivengere",
    "simeon-nsibambi",
    "george-muller",
    "hudson-taylor",
}


def create_authors(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Book = apps.get_model("library", "Book")

    # Fresh installs are populated wholesale by ``seed_if_empty`` (keyed on the
    # Book table) right after migrations run; loaddata would then collide with
    # rows we had created here by slug. So only act on an already-seeded DB —
    # i.e. production, where books exist but these new authors do not yet.
    if not Book.objects.exists():
        return

    try:
        rows = json.loads(FIXTURE.read_text())
    except (OSError, ValueError):
        return  # no fixture available — nothing to create

    for row in rows:
        if row.get("model") != "library.author":
            continue
        f = row["fields"]
        slug = f["slug"]
        if slug not in NEW_SLUGS:
            continue
        Author.objects.get_or_create(
            slug=slug,
            defaults={
                "name": f.get("name", ""),
                "bio": f.get("bio", ""),
                "bio_html": f.get("bio_html", ""),
                "photo_url": f.get("photo_url", ""),
                "birth_year": f.get("birth_year"),
                "death_year": f.get("death_year"),
                "original_language": f.get("original_language", "en"),
            },
        )


def remove_authors(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=NEW_SLUGS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0025_sermons_es"),
    ]

    operations = [
        migrations.RunPython(create_authors, remove_authors),
    ]
