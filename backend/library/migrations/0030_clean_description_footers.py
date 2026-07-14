"""Clean scraped site-footer noise out of 30 remaining EN book descriptions.

Same junk 0029 removed from Prayer – The Pulse of Life: the importer captured
WordPress footer boilerplate ("Back Ochorus ‍We identify great Christian
books… Explore About Us Books Biographies Contact") after the genuine text,
plus an often-empty "Contents" heading. Genuine contents lists are kept
(normalised to "Contents: …"); the-inner-chamber's list was a scrape error
(it belongs to stepping-stones-2) and is dropped.

Cleaned strings live in data/clean_description_footers.json. Guarded no-op
per book when the junk isn't present (fresh installs seed from the
already-clean fixture after migrate).
"""

import json
from pathlib import Path

from django.db import migrations

DATA_FILE = Path(__file__).parent / "data" / "clean_description_footers.json"


def apply(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    cleaned = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for slug, description in cleaned.items():
        Book.objects.filter(
            slug=slug,
            language="en",
            description__contains="Explore About Us",
        ).update(description=description)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0029_clean_pulse_description"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
