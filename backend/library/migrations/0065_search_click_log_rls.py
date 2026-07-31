"""Row-level security on the search-click log.

Same rationale and mechanism as 0043 did for the query log: the Supabase Data
API exposes the public schema to the anon key, and RLS is what gates it
(backend/CLAUDE.md: "one reachable by the anon key without RLS is a data
leak"). RLS with no policies denies all access to non-owner roles — right for
an analytics table only Django should touch. Django connects as the table
owner and bypasses RLS (no FORCE), so the app is unaffected. Postgres-only;
SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_searchclicklog ENABLE ROW LEVEL SECURITY"
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_searchclicklog DISABLE ROW LEVEL SECURITY"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0064_searchclicklog"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
