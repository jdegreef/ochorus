"""Row-level security on the last two reading tables.

0009/0011/0013 covered favorites, reading days and plan progress; these two
were left behind, and they are the most sensitive rows in the application:
`reading_chaptermarks` holds readers' highlights and the text of their private
notes, and `reading_readingprogress` holds what each reader is reading and how
far in.

Mechanism as in 0009: the Supabase Data API exposes the public schema to the
anon key, RLS with no policies denies all non-owner access, and Django connects
as the table owner so it bypasses RLS (no FORCE). Postgres-only; SQLite dev has
no RLS concept.
"""

from django.db import migrations

TABLES = (
    "reading_chaptermarks",
    "reading_readingprogress",
)


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
        ("reading", "0013_planprogress_rls"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
