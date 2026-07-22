"""Row-level security on favorites.

Same rationale and mechanism as library's 0043/0045 RLS migrations: the
Supabase Data API exposes the public schema to the anon key, and enabling RLS
with no policies denies all non-owner access — favorites are per-user data and
must not be readable or writable through the anon key. Django connects as the
table owner and bypasses RLS. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_favorite ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_favorite DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0008_favorite"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
