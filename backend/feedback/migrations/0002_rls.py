"""Row-level security on the feedback table.

Same rationale and mechanism as emails/0002_rls and accounts/0003_rls_core_tables:
the Supabase Data API exposes the public schema to the anon key, and enabling RLS
with no policies denies all non-owner access. This table holds a submitter's
email and free-text feedback — reachable only through Django (the table owner,
which bypasses RLS), never the anon key. Postgres-only; SQLite dev has no RLS
concept. The ``tests_rls`` coverage test fails CI for any public table without
this.
"""

from django.db import migrations

_TABLES = [
    "feedback_feedback",
]


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in _TABLES:
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in _TABLES:
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("feedback", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
