"""Backfill descriptions for 16 EN books imported without one.

Gutenberg/CCEL/biography imports whose sources carried no blurb left
Book.description empty, so their book pages and cards render without any
summary. Descriptions live in data/book_descriptions_en.json (slug -> text).

Guarded: only fills rows whose description is still empty, and no-ops for
books not present (fresh installs seed from the already-patched fixture
after migrate).
"""

import json
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).parent / "data" / "book_descriptions_en.json"


def apply(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    descriptions = json.loads(DATA.read_text(encoding="utf-8"))
    for slug, description in descriptions.items():
        Book.objects.filter(slug=slug, language="en", description="").update(
            description=description
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0031_topic_topicbook_topictranslation"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
