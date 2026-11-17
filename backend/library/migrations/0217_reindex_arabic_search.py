"""Re-index Arabic search vectors under Postgres's `arabic` config.

`fts.FTS_CONFIGS` now maps `ar` to `arabic` (stemming: a search for a word
also matches its other forms). Every Arabic vector already stored was built
with `simple`, and a query is built with the reader's config, so the two would
not meet. NULL them here; the release chain's last content step,
backfill_search_vectors, rebuilds every NULL vector with the current config.

Raw SQL on the tables as they stand at this migration, not `library.fts`: a
migration replays on every fresh database, and live code may come to reference
columns that do not exist yet at this point in the chain. On a fresh database
the tables are empty here (the fixture loads after migrate), so this is a no-op.
"""

from django.db import migrations

_NULL_ARABIC = (
    "UPDATE library_chapter SET search_vector = NULL WHERE book_id IN "
    "(SELECT id FROM library_book WHERE language = 'ar')",
    "UPDATE library_sermon SET search_vector = NULL WHERE language = 'ar'",
    "UPDATE library_book SET search_vector = NULL WHERE language = 'ar'",
    "UPDATE library_plan SET search_vector = NULL WHERE language = 'ar'",
    "UPDATE library_article SET search_vector = NULL WHERE language = 'ar'",
)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for sql in _NULL_ARABIC:
        schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0216_article_qa"),
    ]

    operations = [
        # Backwards is a no-op: NULL vectors are what backfill fills, in
        # whichever config the code then names.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
