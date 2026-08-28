"""Row-level security on the quotations table.

Same rationale and mechanism as 0043/0045/0065/0076/0079: the Supabase Data API
exposes the public schema to the anon key, and RLS with no policies denies all
access to non-owner roles. Django connects as the table owner and bypasses it,
so the reader and the API are unaffected.

The rows are public content, and that is not the point. The rule is that no
table in the public schema is reachable by the anon key, and this one carries a
`reviewed` flag that is a publication decision: unreviewed quotations are
deliberately not published, and a table anyone can read hands them out anyway —
and a table anyone can WRITE lets a stranger flip the flag, which is the whole
gate. That makes this exactly the case the rule exists for.

Postgres-only; SQLite dev has no RLS concept, which is why the local suite went
green and only `Backend — tests (Postgres, the production search path)` caught
it. Coverage is enforced by accounts/tests_rls.py, which failed on this table
the moment the model landed and named the exact statement below.
"""

from django.db import migrations

TABLE = "library_quote"


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
        ("library", "0082_quote"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
