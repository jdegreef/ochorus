"""Row-level security on the citation index.

Same rationale and mechanism as 0043_search_log_rls: the Supabase Data API
exposes the public schema to the anon key, and RLS with no policies denies all
non-owner access. The citation data itself is derivable from public chapters,
but an anon-WRITABLE table would let injected rows surface in search results —
so the write path is what this closes. Django connects as the table owner and
bypasses RLS. Postgres-only; SQLite dev has no RLS concept.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_chaptercitation ENABLE ROW LEVEL SECURITY"
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE library_chaptercitation DISABLE ROW LEVEL SECURITY"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0044_chapter_citations_indexed_at_chaptercitation"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
