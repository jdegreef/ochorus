"""Populate the stored search vectors and build their GIN indexes.

Postgres-only (SQLite dev keeps NULL columns and its icontains fallback).
Runs once on the already-deployed database; fresh installs get vectors from
the backfill_search_vectors release step instead (loaddata bypasses save()).

The index build caps maintenance_work_mem at 64MB: on the shared small
Postgres instance a bigger setting (e.g. 1GB) gets the backend OOM-killed
mid-CREATE INDEX (learned the hard way on Take Root's trigram index). The
SET is transaction-local to the migration and touches nothing persistent.

Indexes are created with raw SQL rather than Meta GinIndex so the model
state stays backend-neutral (GinIndex in Meta breaks migrate on SQLite).
"""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from library import fts

    fts.backfill(only_null=False)
    schema_editor.execute("SET maintenance_work_mem = '64MB'")
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS library_chapter_search_vector_gin "
        "ON library_chapter USING GIN (search_vector)"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS library_sermon_search_vector_gin "
        "ON library_sermon USING GIN (search_vector)"
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS library_chapter_search_vector_gin")
    schema_editor.execute("DROP INDEX IF EXISTS library_sermon_search_vector_gin")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0040_search_vector_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
