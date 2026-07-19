"""Populate the stored search vectors and build their GIN indexes.

Postgres-only (SQLite dev keeps NULL columns and its icontains fallback).
Runs once on the already-deployed database; fresh installs get vectors from
the backfill_search_vectors release step instead (loaddata bypasses save()).

The SQL here is a FROZEN snapshot of library/fts.py as of this migration —
deliberately not imported, so replaying the chain on an old data-bearing
database never runs tomorrow's fts.py against today's schema. Rows whose
body_text is still empty (a DB migrated before its first release finished
backfill_body_text) are left NULL on purpose: the release backfill fills
them AFTER body_text exists, instead of baking in a body-blind vector that
the NULL-only backfill would never repair.

The index build caps maintenance_work_mem at 64MB (SET LOCAL — scoped to
this migration's transaction): on the shared small Postgres instance a
bigger setting (e.g. 1GB) gets the backend OOM-killed mid-CREATE INDEX
(learned the hard way on Take Root's trigram index).

Indexes are created with raw SQL rather than Meta GinIndex so the model
state stays backend-neutral (GinIndex in Meta breaks migrate on SQLite).
"""

from django.db import migrations

_CONFIGS = {"en": "english", "fr": "french", "es": "spanish", "pt": "portuguese"}

_CHAPTER_SQL = """
UPDATE library_chapter AS t
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(b.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.body_text, '')), 'C')
FROM library_book AS b
JOIN library_author AS a ON a.id = b.author_id
WHERE b.id = t.book_id AND b.language = %(language)s AND t.body_text <> ''
"""

_SERMON_SQL = """
UPDATE library_sermon AS t
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.scripture_ref, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.body_text, '')), 'C')
FROM library_author AS a
WHERE a.id = t.author_id AND t.language = %(language)s AND t.body_text <> ''
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for template, language_table in (
            (_CHAPTER_SQL, "library_book"),
            (_SERMON_SQL, "library_sermon"),
        ):
            cursor.execute(f"SELECT DISTINCT language FROM {language_table}")
            for (language,) in cursor.fetchall():
                cursor.execute(
                    template,
                    {
                        "config": _CONFIGS.get(language, "simple"),
                        "language": language,
                    },
                )
    schema_editor.execute("SET LOCAL maintenance_work_mem = '64MB'")
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
