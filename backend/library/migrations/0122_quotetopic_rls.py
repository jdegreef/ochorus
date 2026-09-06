"""Row-level security on the quote-topic table and its membership join.

Same rationale and mechanism as the other per-table RLS migrations (e.g.
0113_topicarticle_rls): the Supabase Data API exposes the public schema to the
anon key, and enabling RLS with no policies denies all non-owner access. Neither
table holds per-user data, but the rule is "every public table has RLS"
(accounts/tests_rls enforces it), and Django connects as the table owner and
bypasses RLS anyway. Both the ``QuoteTopic`` table and the auto-created
``Quote.topics`` M2M join are public tables, so both are covered. Postgres-only;
SQLite dev has no RLS concept.
"""

from django.db import migrations

TABLES = ("library_quotetopic", "library_quote_topics")


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0121_quotetopic_quote_topics"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
