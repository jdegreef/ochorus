"""Stored search vectors for books, plans and articles, GIN-indexed.

Search built these three vectors from the raw columns on every request (a
book's title, subtitle, author name and description, re-tokenised for every
published book in the language, twice per keystroke: once for the hits and
once for the counts). They are per-language rows, so like chapters and sermons
(migration 0041) one stored vector per row serves every query.

Columns only — no populate. They land NULL, and the release chain's
backfill_search_vectors step (after migrate, before the new code serves) fills
them; fresh databases get them the same way, since loaddata bypasses save().

Indexes in raw SQL for 0041's reason: GinIndex in Meta breaks migrate on
SQLite. They are small (titling text only), but the maintenance_work_mem cap
is kept for the same shared-instance reason.
"""

import django.contrib.postgres.search
from django.db import migrations

_TABLES = ("library_book", "library_plan", "library_article")


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("SET LOCAL maintenance_work_mem = '64MB'")
    for table in _TABLES:
        schema_editor.execute(
            f"CREATE INDEX IF NOT EXISTS {table}_search_vector_gin "
            f"ON {table} USING GIN (search_vector)"
        )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in _TABLES:
        schema_editor.execute(f"DROP INDEX IF EXISTS {table}_search_vector_gin")


def _vector_field():
    return django.contrib.postgres.search.SearchVectorField(
        editable=False, null=True, serialize=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0206_fix_freedom_of_the_will_titles"),
    ]

    operations = [
        migrations.AddField(
            model_name="article", name="search_vector", field=_vector_field()
        ),
        migrations.AddField(
            model_name="book", name="search_vector", field=_vector_field()
        ),
        migrations.AddField(
            model_name="plan", name="search_vector", field=_vector_field()
        ),
        # base_manager_name, so a lazy FK load defers the new column too
        # (models._DeferredVectorManager). State only — no SQL.
        migrations.AlterModelOptions(
            name="article",
            options={"base_manager_name": "objects", "ordering": ["sort_order", "h1"]},
        ),
        migrations.AlterModelOptions(
            name="book",
            options={"base_manager_name": "objects", "ordering": ["sort_order", "title"]},
        ),
        migrations.AlterModelOptions(
            name="plan",
            options={"base_manager_name": "objects", "ordering": ["sort_order", "title"]},
        ),
        migrations.RunPython(forwards, backwards),
    ]
