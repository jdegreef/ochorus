"""Row-level security on the per-quotation review table.

Same rationale and mechanism as 0043/0045/0065/0076/0079/0083: the Supabase Data
API exposes the public schema to the anon key, and RLS with no policies denies
all access to non-owner roles. Django connects as the table owner and bypasses
it, so the reader and the API are unaffected.

This table is exactly the case the rule exists for. Every row is a named
reviewer's judgement about a verse, so a table anyone can READ hands out who
decided what; and a table anyone can WRITE lets a stranger mark the corpus
reviewed, which is the only thing standing between an AI translation and the
removal of its "awaiting native review" badge.

Postgres-only; SQLite dev has no RLS concept, which is why a local suite goes
green regardless. Coverage is enforced by accounts/tests_rls.py, which reads the
live catalogue and names the exact statement below.
"""

from django.db import migrations

TABLE = "library_versereview"


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
        ("library", "0088_versereview"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
