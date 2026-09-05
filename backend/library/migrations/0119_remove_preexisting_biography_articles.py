"""Remove three more biography articles from the Articles section.

Continues 0118: biographies belong in the biography section, not `/articles`.
Hudson Taylor, Amy Carmichael and Samuel Ajayi Crowther each already have a
full author-page biography (they author works on the site, so their author
rows exist), and each was ALSO carried as a `/articles` piece — the same
duplication 0118 removed for the five newer ones.

As in 0118: ``seed_articles`` only upserts and never prunes, so deleting the
fixture files alone leaves the live rows published; this migration deletes them
on an already-seeded database, the fixtures are removed in the same commit, and
the migration no-ops on a fresh rebuild. Idempotent; plain no-op reverse.
"""

from __future__ import annotations

from django.db import migrations

RETIRED_SLUGS = (
    "hudson-taylor-trusting-god-for-the-impossible",
    "amy-carmichael-and-the-cost-of-love",
    "samuel-crowther-from-captive-to-bishop",
)


def remove_articles(apps, schema_editor):
    Article = apps.get_model("library", "Article")
    Article.objects.filter(slug__in=RETIRED_SLUGS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0118_remove_new_biography_articles"),
    ]

    operations = [
        migrations.RunPython(remove_articles, migrations.RunPython.noop),
    ]
