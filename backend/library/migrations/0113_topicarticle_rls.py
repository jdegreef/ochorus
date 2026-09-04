"""Row-level security on the topic-article membership table.

Same rationale and mechanism as the other per-table RLS migrations (e.g.
0102_bookperson_rls): the Supabase Data API exposes the public schema to the
anon key, and enabling RLS with no policies denies all non-owner access. This
table holds no per-user data, but the rule is "every public table has RLS"
(accounts/tests_rls enforces it), and Django connects as the table owner and
bypasses RLS anyway. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_topicarticle ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_topicarticle DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0112_topicarticle"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
