"""Row-level security on the email tables.

Same rationale and mechanism as reading/0009_favorite_rls and
accounts/0003_rls_core_tables: the Supabase Data API exposes the public schema
to the anon key, and enabling RLS with no policies denies all non-owner access.
These tables hold recipient addresses, consent, and send logs — none of it
should be reachable through the anon key. Django connects as the table owner and
bypasses RLS. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations

_TABLES = [
    "emails_emailsubscription",
    "emails_broadcast",
    "emails_emailmessage",
    "emails_emailevent",
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
        ("emails", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
