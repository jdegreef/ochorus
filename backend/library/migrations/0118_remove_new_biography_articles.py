"""Remove five biography articles from the Articles section.

Biographies belong in the biography section — each of these five people
(George Müller, Charles Spurgeon, John Newton, William Carey, Corrie ten Boom)
already has a full author-page biography (their ``authors.json`` bio, rendered
at ``/authors/<slug>``; the bio-only three are created by the
``*_biography_authors`` migrations). The article-form retellings duplicated
that content in a second section, so they are being retired.

``seed_articles`` only upserts and never prunes, and ``is_published`` is
create-only there, so deleting the fixture files alone would leave the live
rows published. This migration deletes the rows on an already-seeded database;
the matching fixture files are removed in the same commit, so a fresh install's
``seed_if_empty`` never recreates them and this migration no-ops on a rebuild
(nothing to delete). Same shape as the ``*_biography_authors`` data migrations,
in reverse: idempotent, and a plain no-op reverse.
"""

from __future__ import annotations

from django.db import migrations

RETIRED_SLUGS = (
    "george-mueller-and-the-god-who-answers-prayer",
    "charles-spurgeon-the-prince-of-preachers",
    "john-newton-from-slave-trader-to-amazing-grace",
    "william-carey-father-of-modern-missions",
    "corrie-ten-boom-forgiveness-in-the-darkness",
)


def remove_articles(apps, schema_editor):
    Article = apps.get_model("library", "Article")
    Article.objects.filter(slug__in=RETIRED_SLUGS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0117_fix_whitefield_bio_word_count"),
    ]

    operations = [
        migrations.RunPython(remove_articles, migrations.RunPython.noop),
    ]
