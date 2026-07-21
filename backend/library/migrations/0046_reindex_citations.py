"""Force a one-time citation reindex on deploy.

The extraction fix for "Book. C:V" citations (a period after a full book name
previously indexed as a whole-book span) changes what existing rows should
contain. Clearing every stamp makes the same deploy's index_citations release
step rescan the full corpus (~3s). One UPDATE, reversible as a no-op.
"""

from django.db import migrations


def clear_stamps(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    Chapter.objects.update(citations_indexed_at=None)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0045_chaptercitation_rls"),
    ]

    operations = [
        migrations.RunPython(clear_stamps, migrations.RunPython.noop),
    ]
