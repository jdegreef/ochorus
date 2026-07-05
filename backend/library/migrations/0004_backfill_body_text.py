"""Backfill Chapter.body_text on databases that already have content.

Freshly seeded databases get body_text via the release command's
backfill_body_text step; this migration covers DBs (production) whose chapters
predate the column.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    # Use the real helper so the derivation matches save()/the command exactly.
    from library.text import html_to_text

    Chapter = apps.get_model("library", "Chapter")
    for chapter in Chapter.objects.filter(body_text="").iterator(chunk_size=200):
        Chapter.objects.filter(pk=chapter.pk).update(
            body_text=html_to_text(chapter.body_html)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0003_chapter_body_text"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
