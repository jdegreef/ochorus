"""Convert stored paragraph-level highlights/notes to text-range marks.

Each highlighted paragraph becomes a full-paragraph range (e = -1 sentinel);
paragraph notes attach to that range. Uses the same converter the API applies
to legacy client payloads, so all paths produce identical marks. Idempotent —
rows that already have marks are left alone.
"""

from django.db import migrations


def convert(apps, schema_editor):
    from reading.marks import from_legacy

    ChapterMarks = apps.get_model("reading", "ChapterMarks")
    for row in ChapterMarks.objects.all().iterator(chunk_size=200):
        if row.marks:
            continue
        marks = from_legacy(row.highlights, row.notes)
        if marks:
            row.marks = marks
            row.save(update_fields=["marks"])


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0002_chaptermarks_marks"),
    ]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
    ]
