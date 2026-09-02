"""Row-level security on the book-people membership table.

Same rationale and mechanism as the other per-table RLS migrations (e.g.
0097_contentrevision_rls): the Supabase Data API exposes the public schema to the
anon key, and enabling RLS with no policies denies all non-owner access. This
table holds no per-user data, but the rule is "every public table has RLS"
(accounts/tests_rls enforces it), and Django connects as the table owner and
bypasses RLS anyway. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_bookperson ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_bookperson DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0101_bookperson"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
