"""Row-level security on the bookmarks table.

``reading_bookmark`` holds which paragraphs each reader saved — private per-user
data, like the marks/progress tables 0014 covered. Same mechanism as 0009/0014:
the Supabase Data API exposes the public schema to the anon key, RLS with no
policies denies all non-owner access, and Django connects as the table owner so
it bypasses RLS (no FORCE). Postgres-only; SQLite dev has no RLS concept.

`accounts/tests_rls.py` fails the build for any public table without RLS, so this
is required, not optional.
"""

from django.db import migrations

TABLES = ("reading_bookmark",)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0018_bookmark"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
