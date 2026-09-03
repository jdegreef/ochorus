"""Row-level security on the articles table.

Same rationale and mechanism as the other per-table RLS migrations (e.g.
0102_bookperson_rls): the Supabase Data API exposes the public schema to the
anon key, and enabling RLS with no policies denies all non-owner access. Articles
hold no per-user data and are public content, but the rule is "every public table
has RLS" (accounts/tests_rls enforces it), and Django connects as the table owner
and bypasses RLS anyway. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_article ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_article DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0106_article"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
