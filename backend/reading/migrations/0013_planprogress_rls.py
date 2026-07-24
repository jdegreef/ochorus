"""Row-level security on plan progress.

Same rationale and mechanism as favorites' 0009 and reading-activity's 0011:
the Supabase Data API exposes the public schema to the anon key, and enabling
RLS with no policies denies all non-owner access — a reader's plan progress is
per-user data and must not be readable or writable through the anon key. Django
connects as the table owner and bypasses RLS. Postgres-only; SQLite dev has no
RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_planprogress ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE reading_planprogress DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0012_plan_progress"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
