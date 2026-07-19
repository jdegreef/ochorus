"""Row-level security on the search log.

The Supabase Data API exposes the public schema to the anon key; RLS is what
gates it (backend/CLAUDE.md: "one reachable by the anon key without RLS is a
data leak"). Enabling RLS with no policies denies all access to non-owner
roles — exactly right for an analytics table only Django should touch.
Django connects as the table owner, which bypasses RLS (no FORCE), so the
app is unaffected. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_searchquerylog ENABLE ROW LEVEL SECURITY"
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_searchquerylog DISABLE ROW LEVEL SECURITY"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0042_search_query_log"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
