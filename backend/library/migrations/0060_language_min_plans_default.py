"""min_plans defaults to 0, and existing rows are corrected to match.

The registry shipped with ``min_plans=1``, which turned out to be a bar nothing
meets: no non-English language has ever had a published reading plan, so every
language — including the four already live — would have read as "not ready" for
a format that has never been part of a launch. A default that flags everything
is a default nobody reads.

The row rewrite is a one-time correction, done here because the readiness UI has
not shipped yet, so no admin has tuned a threshold for this to overwrite. Once it
has, thresholds are the admin's: the seed never touches them.
"""

from django.db import migrations, models


def relax_existing(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    # Only rows still carrying the original default — never a tuned value.
    Language.objects.filter(min_plans=1).update(min_plans=0)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0059_seed_language_registry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="language",
            name="min_plans",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(relax_existing, noop),
    ]
