"""The table behind the default cache (settings.CACHES), with RLS on.

The default cache moved from per-process LocMemCache to Django's DatabaseCache
so a worker recycle (gunicorn ``--max-requests``, every ~500 requests) no longer
throws away the full-corpus memos — scripture pages, era presence, the audit
scan — that every prerender crawl leans on.

Created here rather than by ``createcachetable`` in the release step for two
reasons. A migration runs in the test database too, so ``tests_rls`` sees the
table and holds it to the rule. And the RLS must land with the table, not after
it: DatabaseCache stores PICKLED values, so a row an outsider could write is
code the API would run on its next read — far worse than a leak. RLS with no
policies (as in 0003) denies the Data API roles; Django owns the table and
bypasses it.

The table name is spelled out, not read from settings: under ``manage.py test``
the default alias is a dummy, and the table must exist all the same.
"""

from django.core.management.commands.createcachetable import Command as CreateCacheTable
from django.db import migrations

TABLE = "django_cache"


def forwards(apps, schema_editor):
    create = CreateCacheTable()
    create.verbosity = 0  # normally set by handle(), which this bypasses
    create.create_table(schema_editor.connection.alias, TABLE, dry_run=False)
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    schema_editor.execute(f"DROP TABLE IF EXISTS {TABLE}")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_prompttally"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
