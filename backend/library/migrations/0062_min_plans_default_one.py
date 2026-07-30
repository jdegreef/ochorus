"""Require one translated reading plan by default, and fix the rows that
inherited the wrong default.

Migration 0060 dropped ``min_plans`` to 0 and relaxed every row, on the stated
grounds that "no non-English language has ever had a published reading plan".
That was read off a database on which ``seed_plans`` had not been run. Every
live language has translated plans (lg 5, sw 3, es 2, pt 1), so the bar 0060
called "a bar nothing meets" is in fact met by all four. This restores it.

**Which rows get updated, and why only those.** Thresholds are a workflow-owned
field — an admin tunes them, and the seed is create-only precisely so a deploy
can't walk that back. A live language's bar is therefore history and is left
alone: it has already launched, so the number records what it cleared rather
than a decision still to be made. A DRAFT row still sitting on the old default
has never been launched or tuned, so its number is just the default we shipped
— and that default was wrong.

Today that is Arabic alone. If a draft language's 0 was in fact deliberate this
resets it, and one edit on its admin page puts it back; leaving every unlaunched
language on a default chosen from a false premise is the worse trade.
"""

from django.db import migrations, models


def raise_draft_defaults(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    Language.objects.filter(status="draft", min_plans=0).update(min_plans=1)


def restore_draft_defaults(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    Language.objects.filter(status="draft", min_plans=1).update(min_plans=0)


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0061_language_glossary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="language",
            name="min_plans",
            field=models.PositiveIntegerField(default=1),
        ),
        # Reversible, so a rollback doesn't leave rows carrying a value this
        # migration invented.
        migrations.RunPython(raise_draft_defaults, restore_draft_defaults),
    ]
