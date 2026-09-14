"""Row-level security on ``accounts_admingrant``.

Like every other table in the public schema, this one is exposed to the anon key
by the Supabase Data API, and it is *especially* sensitive — it is the table that
decides who holds which admin capability. RLS with no policies denies all
non-owner access; Django connects as the table owner and bypasses it (no FORCE).
Postgres-only; SQLite dev has no RLS concept. Guarded by ``accounts.tests_rls``.
"""

from django.db import migrations

TABLE = "accounts_admingrant"


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_admingrant"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
