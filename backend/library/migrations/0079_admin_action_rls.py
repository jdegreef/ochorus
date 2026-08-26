"""Row-level security on the admin action log.

Same rationale and mechanism as 0043/0045/0065/0076: the Supabase Data API
exposes the public schema to the anon key, and RLS with no policies denies all
access to non-owner roles. Django connects as the table owner and bypasses it,
so the app is unaffected.

This table earns it on both sides. Reading it lists the administrators of the
site by email address, along with everything they have done and when. Writing
it is worse: an audit log anyone can append to is not an audit log, and one
anyone can delete from is actively misleading — it would read as "nothing
happened here".

Postgres-only; SQLite dev has no RLS concept. Coverage is enforced by
accounts/tests_rls.py, which failed on this table the moment the model landed
and named the exact statement below.
"""

from django.db import migrations

TABLE = "library_adminaction"


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
        ("library", "0078_admin_action"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
