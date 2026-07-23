"""Row-level security on the reading-activity log.

Same rationale and mechanism as favorites' 0009 (and library's 0043/0045): the
Supabase Data API exposes the public schema to the anon key, and enabling RLS
with no policies denies all non-owner access — a reader's activity days are
per-user data and must not be readable or writable through the anon key. Django
connects as the table owner and bypasses RLS. Postgres-only; SQLite dev has no
RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_readingday ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_readingday DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0010_readingday"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
