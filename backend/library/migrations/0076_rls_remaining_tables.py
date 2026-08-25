"""Row-level security on every remaining library table.

Same rationale and mechanism as 0043/0045/0065, applied to the tables those
three left uncovered: the Supabase Data API exposes the public schema to the
anon key, and RLS with no policies denies all access to non-owner roles
(backend/CLAUDE.md: "one reachable by the anon key without RLS is a data
leak"). Django connects as the table owner and bypasses RLS (no FORCE), so the
app is unaffected — the six tables already carrying RLS in production prove
that assumption holds for this deployment.

Content tables are public to READ through the API, so the exposure closed here
is the WRITE side, and it is the serious one: an anon-writable
`library_chapter` is stored XSS, because the reader renders `body_html` with
`{@html}`. An anon-writable `library_language` fakes a launch. Read matters
too for the rows that are not reader-visible: unpublished drafts
(`is_published=False`), review state, and translation notes.

Postgres-only; SQLite dev has no RLS concept.

Coverage is enforced from here on by accounts/tests_rls.py, which fails on any
public table without RLS — the per-table migrations were previously guarded by
nothing, which is how nineteen tables came to be missed.
"""

from django.db import migrations

TABLES = (
    "library_author",
    "library_authortranslation",
    "library_book",
    "library_chapter",
    "library_language",
    "library_plan",
    "library_planday",
    "library_reviewoutcome",
    "library_sermon",
    "library_topic",
    "library_topicbook",
    "library_topicsermon",
    "library_topictranslation",
    "library_translationnote",
)


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
        ("library", "0075_repair_reference_defects"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
